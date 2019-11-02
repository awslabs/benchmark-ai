;;  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
;;
;;  Licensed under the Apache License, Version 2.0 (the "License").
;;  You may not use this file except in compliance with the License.
;;  A copy of the License is located at
;;
;;      http://www.apache.org/licenses/LICENSE-2.0
;;
;;  or in the "license" file accompanying this file. This file is distributed
;;  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
;;  express or implied. See the License for the specific language governing
;;  permissions and limitations under the License.
(ns bai-bff.services.eventbus
  "This namespace handles the creation and closing of channels that
  faciliate 'conveyance' of information throughout this system.  We
  continue the use of the 'component' model for the sake of
  consistency as we are indeed managing 'state' of the channels.<p>

  (Note from author: I am aware that this is very very OO code in a
  functional language.  I went down this road when I decided to use a
  Stuart Sierra-esque compoent model for this project.  So anywhere
  there is state I manage it in this way. Oh well.)"
  (:require [bai-bff.core :refer :all]
            [bai-bff.services :refer [RunService]]
            [bai-bff.utils.parsers :refer [parse-long]]
            [bai-bff.utils.persistence :as db]
            [bai-bff.utils.utils :as utils]
            [bai-bff.utils.log-index :as log-index]
            [environ.core :refer [env]]
            [amazonica.aws.s3 :as s3]
            [amazonica.aws.s3transfer :as s3tfr]
            [taoensso.timbre :as log]
            [clojure.java.io :as io]
            [clojure.pprint :refer :all]
            [clojure.core.async :as a :refer [>! <! >!! <!! go chan buffer close! thread
                                              alts! alts!! timeout]]))

(def send-event-channel-atom     (atom nil))  ;;output channel
(def receive-events-channel-atom (atom nil))  ;;input channel

;;TODO add a stop function that closes channels and allows to drain.
(defrecord EventbusService [send-channel receive-channel]
  RunService
  (start! [this]
    (log/info (str "starting eventbus service component..."))
    (reset! send-event-channel-atom send-channel)
    (reset! receive-events-channel-atom receive-channel))
  (stop! [this]
    (locking this
      (log/info (str "stopping eventbus service component... (closing channels)"))
      (a/close! @send-event-channel-atom)
      (a/close! @receive-events-channel-atom)))
  Object
  (toString [_] "<Eventbus>"))

(defmethod print-method EventbusService [v ^java.io.Writer w]
  (.write w "<EventbusService>"))

(defn create-eventbus-service []
  (map->EventbusService {:send-channel    (chan 1000)
                         :receive-channel (chan 1000)}))


;;----------------------------------------------------------
;; Event Processing
;;----------------------------------------------------------

;; The "database"
(def stored-scripts (atom #{}))

(defn update-status-store
  "Stores an event (map) in the event in a {k{k[v]}} database based on
  client-id -> action-id -> events : Using a map as an indexed event
  store, this function updates the store. The store is built as map of
  maps of vectors that hold the trail of events.  In this case status
  messages.

  *Developer insight:*
  The spirit of this function is that you pass it an event and
  fuggedaboutdit.  The function will index and store the event
  appropriately.  There are times when we want to override / usurp the
  secondary index field (the action-id) with another value.  On those
  occasions use the keyword arg `:usurping-index` to inject a
  different secondary index to be used.

  Indeed, this function is opinionated with a bias toward enforcing
  the structure of the event (it must have a client-id and action-id,
  at the top level).  It makes the choice for using another indexing
  value as an explicit call - further enforcing the explicit
  cognizance of this action by use of keyword arg.  The specific use
  case that motivated this functionality is when a command return
  event is encountered, we want that command return event to be in the
  same index bucket as the target action it was affecting.  This way
  you can get a more clear lineage of events as associated with a
  particular action. Get it? Gyot it? Good. :-)

  Caveat - there is no dedupping or sorting (by time) in the event
  vector.  This is a TODO item, which means that since atomic calls
  can be re-run at anytime, we should make sure this function is pure
  and right now it is not - not without sorting and dedupping."
  [event]
  (log/trace "update-status-store called...")
  (if (nil? event)
    false
    (let [{:keys [client_id action_id]} event
          [client-key action-key] (mapv keyword [client_id action_id])]
      (if (and client-key action-key)
       (db/save-client-job-status client-key action-key event)
       (throw (Exception. "Could not insert event"))))))

(defn process-status-records
  "Implementation of the callback function passed to the Kafka
  source (consumer) where collection of events (maps) are passed in
  here.  Each record is put in the datastore - status-db.  See
  comments for update-status-store regarding pureness and operations"
  [events]
  (when (seq events)
    (log/trace (str "Processing "(count events)" status events"))
    (doseq [event events]
      (if-not (nil? event) (update-status-store event))))
  true)

(defn process-cmd-return-records
  "Implementation of the callback function passed to the Kafka
  source (consumer) where collection of events (maps) are passed in
  here.  Each record is put in the datastore - status-db.  See
  comments for update-status-store regarding pureness and operations"
  [events]
  (when (seq events)
    (log/trace (str "Processing "(count events)" command events"))
    (doseq [event events] ; <- I should do this loop with recursion and then only have a single call to swap! at the end... meh.
      (if-not (nil? event) (update-status-store event))))
  true)

(defn get-client-jobs
  "Returns a list of (action id, submission timestamp) tuples 
  of submissions made by a client. The maximum number of items returned 
  per query is governed by the underlying persistence layer.
  Not all action_ids will necessarily be returned in a query. 
  The *since* optional parameter can be used to paginate the query.

  The rows are lexicographically sorted by a range key with the 
  format <timestamp>:<action_id>. Therefore, the *since* parameter can be 
  *any* string, however either a timestamp (e.g. 1567070046827)
  or a range key in the above format should be used 
  (e.g. 1567070046827:61e76d4d-2f31-4259-8bcb-84ab424d9d16).
  Using just the timestamp will return all action ids created from 
  that timestamp (inclusive), using the sort key in the appropriate format will 
  return every action_id created after the specified sort key.
  "
  ([client-id] (get-client-jobs client-id "0"))
  ([client-id since]
   (log/trace "get-all-client-jobs called...")
   (let [since-tstamp (or since "0")]
     (log/trace (str "since... " since-tstamp))
     { :action_ids (db/get-client-jobs client-id :from-sort-key since-tstamp) })))

(defn get-client-job-status-for-action
  "Gets all the events associated with a particular client and this
   particular action (job). The number of items returned in the list 
   is governed by the underlying persistence layer.
   However, not all events will be necessarily be returned. 
   The *since* optional parameter can be used to paginate the query.

   The rows are lexicographically sorted by a range key with 
   the format <timestamp>:<message_id>. Therefore, the *since* parameter 
   can be *any* string. However, either a timestamp (e.g. 1567070046827) or 
   a range key in the above format should be used 
   (e.g. 1567079110254:fd708459-2c73-4602-91ce-dff8f1d90bcf).
   Using just the timestamp will return all events (for action_id created) 
   from that timestamp (inclusive), using the sort key in the appropriate 
   format will return every event (for the action_id) created _after_ the 
   specified sort key.
   "
  [client-id action-id since]
  (log/trace "get-client-job-status-for-action called...")
  (let [since-tstamp (or since "0")]
    (log/trace (str "since... " since-tstamp))
    (db/get-client-job-status client-id action-id :from-sort-key since-tstamp)))

(defn get-job-results [client-id action-id]
  (log/trace "get-job-results - client-id ["client-id"] action-id ["action-id"]")
  (log-index/fetch-logs client-id action-id))

;;----------------------------------------------------------
;; Scripts Persistence
;;----------------------------------------------------------

(defn scripts->s3
  "Takes a script, represented by a map and writes it down to S3
  Then returns the fully qualified s3 path to the resource

  Ex:
  \"script\" {:filename \"00af189027c5050b408de8fee8449a75973b52d6.tar\",
              :content-type \"application/octet-stream\",
              :tempfile #object[java.io.File 0x68f3a6f8 \"/tmp/ring-multipart-3564663405138357266.tmp\"],
              :size 10240}

  (Bucket name is in environment variable: SCRIPTS_EXCHANGE_S3_BUCKET_NAME)

   See bai-bff.utils.utils/generate-s3-path for how to turn a filename into an s3 path in this system

  "
  [script-map]
  (log/trace "scripts->s3 "script-map)
  (s3/put-object (env :scripts-exchange-s3-bucket-name) (utils/generate-s3-path (:filename script-map)) (:tempfile script-map))
  (swap! stored-scripts conj (:filename script-map))
  (io/delete-file (:tempfile script-map)))

(defn has-file? [filename]
  (contains? @stored-scripts filename))
