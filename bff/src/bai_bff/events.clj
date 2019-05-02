(ns bai-bff.events
  (:require [bai-bff.core :refer :all]
            [clojure.pprint :refer :all]
            [clojure.java.io :as io]
            [clojure.data.codec.base64 :as b64]
            [digest]
            [toml.core :as toml]
            [java-time :refer [instant]]
            [taoensso.timbre :as timbre :refer [log  trace  debug  info  warn  error  fatal  report
                                                logf tracef debugf infof warnf errorf fatalf reportf
                                                spy get-env]]))

(defn uuid [] (str (java.util.UUID/randomUUID)))

(defn verify-doc-hash [event]
  (= (some-> event :payload :toml :sha1)
     (digest/sha1(b64/decode (.getBytes (some-> event :payload :toml :doc))))))

(defn decode-document [event]
  "Takes an event and decodes the base64 encoded descriptor
  document (that is in TOML format), and transforms the information
  into a map under the \"contents\" key.  It also verifies that the
  SHA1 posted does indeed match the descriptor document posted."
  (let [decoded-bytes (b64/decode (.getBytes (some-> event :payload :toml :doc)))
        verified?     (= (digest/sha1 decoded-bytes)
                         (some-> event :payload :toml :sha1))
        toml-document (String. decoded-bytes)
        toml->map     (toml/read toml-document :keywordize)]

    (-> event
        (assoc-in [:payload :toml :verified] verified?)
        (assoc-in [:payload :toml :contents] toml->map))))

(defn glean-dataset-info
  "Pulls out the dataset information out of the toml and raises it in the \"payload\" map.
  <p> <i>This begs the question, why not just have this information
  retrieved directly from the TOML contents section?  This is a good
  question and would be viable, however, the argument against that
  would be to keep the TOML contents representation \"immutable\" and
  not do any in place changes, such as when these data sources are
  fetched and augmented with additional information.</i>"
  [event]
  (-> event
      (assoc-in [:payload :datasets] (some-> event :payload :toml :contents :data :sources))))

(defn add-my-visited-entry
  "Adds the entry for this service at the end of the event's vector of
  visited services.  Note that the timestamp \"tstamp\" is when this
  entry is written ~= when this event has been encountered.  The
  event's \"date\" field is of the client's submission."
  [event]
  (let [svc "bai-bff"]
    (-> event
        (assoc-in [:visited] (conj (get-in event [:visited]) {:svc svc :tstamp (:tstamp event) :version VERSION})))))

(defn message->event
  "Takes a \"message\" from the client (as a keyword map), from the wild
  outside world, and turns it into a proper \"event\" that is
  augmented and dispatched through to the next hop in the system.
  Note because of the exposure to the wilds of the internet, it is NOT
  a \"tolerant\" reader.  Every field that is forwarded from the
  client is explicitly assigned as a part of the construction of the
  *new* event. This code will have to be modified along with client
  code if there are event changes."
  [req message-body]
  (let [tstamp (System/currentTimeMillis)
        authenticated false] ;NOTE auth should have been taken care of by middleware.
    (->
     {:message_id      (uuid)                                     ; <--
      :client_id       (some-> message-body :client_id)
      :action_id       (uuid)                                     ; <--
      :client_version  (some-> message-body :client_version)
      :client_sha1     (some-> message-body :client_sha1)
      :client_username (some-> message-body :client_username)
      :date            (some-> message-body :date)
      :authenticated   authenticated                              ; <--
      :tstamp          tstamp
      :visited         (some-> message-body :visited)             ; <--
      :payload         (some-> message-body :payload)}
     (decode-document)
     (glean-dataset-info)
     (add-my-visited-entry))))
