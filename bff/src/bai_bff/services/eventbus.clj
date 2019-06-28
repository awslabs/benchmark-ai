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
            [bai-bff.utils.utils :as utils]
            [environ.core :refer [env]]
            [amazonica.aws.s3 :as s3]
            [amazonica.aws.s3transfer :as s3tfr]
            [taoensso.timbre :as log]
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
(def status-db (atom {}))

(defn update-status-store
  "client-id -> action-id -> [events] : Using a map as an indexed event
  store, this function updates the store. The store is built as map of
  maps of vectors that hold the trail of events.  In this case status
  messages.

  Semantically
  - use client id and transform that value into a keyword to index on.
  - use target_action_id iff set, otherwise use action_id; and transform that into a keyword to index on.
    (the second case it to support commands that have their own, different action_id but will carry the action id that their action is targeted for as target_action_id.  We want the commands to be indexed into the same bucket [technically map] as the action they were intended to affect.) Get it? Gyot it?

  Caveat - there is no dedupping or sorting (by time) in the event
  vector.  This is a TODO item, which means that since atomic calls
  can be re-run at anytime, we should make sure this function is pure
  and right now it is not - not without sorting and dedupping."
  [store event]
  (log/trace "update-status-store called...")
  (if (nil? event)
    store
    (let [{:keys [client_id action_id target_action_id] :or {target_action_id nil}} event
          [client-key action-key] (mapv keyword [client_id (if target_action_id target_action_id action_id)])]
      (if (and client-key action-key)
        (try
          (assoc-in store [client-key action-key] (vec (remove nil? (flatten (vector (some-> store client-key action-key) event)))))
          (catch NullPointerException e
            (.getMessage e)
            store))
        store))))

(defn process-status-records
  "Implementation of the callback function passed to the Kafka
  source (consumer) where collection of events (maps) are passed in
  here.  Each record is put in the datastore - status-db.  See
  comments for update-status-store regarding pureness and operations"
  [events]
  (when (seq events)
    (log/trace (str "Processing "(count events)" status events"))
    (doseq [event events] ; <- I should do this loop with recursion and then only have a single call to swap! at the end... meh.
      (if-not (nil? event) (swap! status-db update-status-store event))))
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
      (if-not (nil? event) (swap! status-db update-status-store event))))
  true)

(defn get-all-jobs
  "Show the full map database of all the status messages received by the
  BFF"
  []
  (log/trace "get-all-jobs called...")
  @status-db)

(defn get-all-client-jobs
  "Get the maps of jobs, in this internal context we call them actions,
  for a given client"
  [client-id]
  (log/trace "get-all-client-jobs called...")
  (let [client-key (keyword client-id)]
    (get @status-db client-key)))

(defn get-all-client-jobs-for-action
  "Gets all the events associated with a particular client and this
  particular action (job)"
  [client-id action-id since]
  (log/trace "get-all-client-jobs-for-action called...")
  (let [client-key (keyword client-id)
        action-key (keyword action-id)
        since-tstamp (or (parse-long since) 0)]
    (log/trace (str "since... "since-tstamp))
    (filterv #(< since-tstamp (:tstamp (peek (:visited %)))) (get-in @status-db [client-key action-key] {}))))

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
  (s3/put-object (env :scripts-exchange-s3-bucket-name) (:filename script-map) (:tempfile script-map)))
