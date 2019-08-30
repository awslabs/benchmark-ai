(ns bai-bff.utils.persistence
  "This namespace handles the communication with the backing store"
  (:require [amazonica.aws.dynamodbv2 :as ddb]
            [environ.core :refer [env]]
            [taoensso.timbre :as log])
  (:import [com.amazonaws.services.dynamodbv2.model 
              ResourceInUseException]))


(def events-table (env :ddb-events-table-name))
(def jobs-table (env :ddb-jobs-table-name))
(def query-limit 30)

(defn save-event [client-id action-id event]
 "Stores an event in the event table. The action-id is used
  as the partition key. To guarantee order and uniqueness, a composite key
  tstamp:message_id is used as the sort key. The action-id is set explicitly 
  (rather than taken directly from the event) to allow the flexibility of storing
  an event against a target action_id. For instance, we would like to log the 
  outcome of a cancel command against its target action_id."
 (let [item {
   :action_id action-id
   :skey (str (event :tstamp) ":" (event :message_id))
   :client_id client-id
   :event event
  }]
   (log/trace "Saving event with client_id: " (:client_id item) " and action_id: " (:action_id item))
   (ddb/put-item :table-name events-table :item item)))

(defn get-events
 "Queries the event table for events against the supplied client_id and action_id.
  An optional last-evaluated-key can be passed in, for pagination. Will return a dynamodb query response.
  If it includes a last-evaluated-key, the next set of rows is retrieved."
  [client-id action-id & {:keys [from-sort-key]
                          :or { from-sort-key "0" } }]
  (let [
    from-sort-key-str (str from-sort-key)
    status-query (partial ddb/query 
     :table-name events-table 
     :limit query-limit 
     :key-conditions { 
      :action_id { 
       :attribute-value-list [action-id] 
       :comparison-operator "EQ"
      }
      :skey {
       :attribute-value-list [from-sort-key-str]
       :comparison-operator "GE"
      }
     }
     ;; it's theoretically possible that two actions with
     ;; the same ids are generated for two different clients.
     ;; Although, the probability is *really* small.
     ;; The client_id filter here just to guard against murphy's law.
     :expression-attribute-names {
      "#cid" "client_id"
     }
     :expression-attribute-values {
      ":cid" client-id
     }
     :filter-expression "#cid = :cid")]
   (log/trace (str "Querying events for client_id: " client-id " and action_id: " action-id))
   (map :event (:items (if (= from-sort-key-str "0") 
    (status-query)
    (status-query :exclusive-start-key { :action_id action-id :skey from-sort-key-str }))))))

(defn save-job [benchmark-creation-event]
 "Stores the action_ids of submitted benchmarks to the benchmark table"
 (let [item {
   :action_id (benchmark-creation-event :action_id)
   :skey (str (benchmark-creation-event :tstamp) ":" (benchmark-creation-event :action_id))
   :client_id (benchmark-creation-event :client_id)
   :timestamp (benchmark-creation-event :tstamp)
  }]
   (log/trace "Saving job with client_id: " (:client_id item) " and action_id: " (:action_id item))
   (ddb/put-item :table-name jobs-table :item item)))

(defn get-jobs
 "Queries the jobs table for action ids against the supplied client_id.
  An optional last-evaluated-key can be passed in, for pagination. Will return a dynamodb query response.
  If it includes a last-evaluated-key, the next set of rows is retrieved.
  An optional timestamp can be passed in to filter the benchmarks by submission time."
  [client-id & {:keys [from-sort-key]
                :or { from-sort-key "0" }}]
  (let [
    from-sort-key-str (str from-sort-key)
    jobs-query (partial ddb/query 
     :table-name jobs-table 
     :limit query-limit 
     :key-conditions { 
      :client_id { 
       :attribute-value-list [client-id] 
       :comparison-operator "EQ"
      }
      :skey {
       :attribute-value-list [from-sort-key-str]
       :comparison-operator "GE"
      }
     })]

   (log/trace (str "Querying jobs for client_id: " client-id))
   (map #(select-keys % [:action_id :timestamp]) (:items (if (= from-sort-key-str "0") 
    (jobs-query)
    (jobs-query :exclusive-start-key { :client_id client-id :skey from-sort-key-str }))))))
