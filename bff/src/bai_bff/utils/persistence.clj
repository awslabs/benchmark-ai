(ns bai-bff.utils.persistence
  "This namespace handles the communication with the backing store"
  (:require [amazonica.aws.dynamodbv2 :as ddb]
            [environ.core :refer [env]]
            [taoensso.timbre :as log])
  (:import [com.amazonaws.services.dynamodbv2.model
            ResourceInUseException]))


(def client-job-status-table (env :ddb-client-job-status-table-name))
(def client-jobs-table (env :ddb-client-jobs-table-name))
(def query-limit 100)

(defn make-client-job-status-table-sort-key [event]
  (str (event :tstamp) ":" (event :message_id)))

(defn make-client-job-table-sort-key [event]
  (str (event :tstamp) ":" (event :action_id)))

(defn save-client-job-status
  "Stores an event in the event table. The action-id is used
  as the partition key. To guarantee order and uniqueness, a composite key
  tstamp:message_id is used as the sort key. The action-id is set explicitly
  (rather than taken directly from the event) to allow the flexibility of storing
  an event against a target action_id. For instance, we would like to log the
  outcome of a cancel command against its target action_id."
  [client-id action-id status-event]
  (let [item {:ActionId action-id
              :TimestampMessageId (make-client-job-status-table-sort-key status-event)
              :ClientId client-id
              :Event status-event}]
    (log/trace "Saving job status with client_id: " (:ClientId item) " and action_id: " (:ActionId item))
    (try
      (ddb/put-item :table-name client-job-status-table :item item)
      (catch Exception ex
        (log/error ex "Error inserting client job status")
        (log/error "Client job status: " (str item))))))

(defn get-client-job-status
  "Queries the client job status table for status events against the supplied client_id and action_id.
  An optional last-evaluated-key can be passed in, for pagination. Will return a dynamodb query response.
  If it includes a last-evaluated-key, the next set of rows is retrieved."
  [client-id action-id & {:keys [from-sort-key]
                          :or { from-sort-key "0" } }]
  (let [
        from-sort-key-str (str from-sort-key)
        client-job-status-query (partial ddb/query
                                         :table-name client-job-status-table
                                         :limit query-limit
                                         :key-conditions {:ActionId {:attribute-value-list [action-id]
                                                                     :comparison-operator "EQ"}
                                                          :TimestampMessageId {:attribute-value-list [from-sort-key-str]
                                                                               :comparison-operator "GE"}}
                                         ;; it's theoretically possible that two actions with
                                         ;; the same ids are generated for two different clients.
                                         ;; Although, the probability is *really* small.
                                         ;; The client_id filter here just to guard against murphy's law.
                                         :expression-attribute-names  {"#cid" "ClientId"}
                                         :expression-attribute-values {":cid" client-id}
                                         :filter-expression "#cid = :cid")]
    (log/trace (str "Querying events for client_id: " client-id " and action_id: " action-id))
    (map :Event (:items (if (= from-sort-key-str "0")
                          (client-job-status-query)
                          (client-job-status-query :exclusive-start-key { :ActionId action-id :TimestampMessageId from-sort-key-str }))))))

(defn save-client-job
  "Stores the action_ids of submitted benchmarks to the benchmark table"
  [client-job-submission-event]
  (let [item {:ActionId (client-job-submission-event :action_id)
              :TimestampActionId (make-client-job-table-sort-key client-job-submission-event)
              :ClientId (client-job-submission-event :client_id)
              :Timestamp (client-job-submission-event :tstamp)}]
    (log/trace "Saving job with client_id: " (:ClientId item) " and action_id: " (:ActionId item))
    (try
      (ddb/put-item :table-name client-jobs-table :item item)
      (catch Exception ex
        (log/error ex "Error saving client job")
        (log/error "Client job: " (str item))))))

(defn get-client-jobs
  "Queries the jobs table for action ids against the supplied client_id.
  An optional last-evaluated-key can be passed in, for pagination. Will return a dynamodb query response.
  If it includes a last-evaluated-key, the next set of rows is retrieved.
  An optional timestamp can be passed in to filter the benchmarks by submission time."
  [client-id & {:keys [from-sort-key]
                :or { from-sort-key "0" }}]
  (let [from-sort-key-str (str from-sort-key)
        client-jobs-query (partial ddb/query
                                   :table-name client-jobs-table
                                   :limit query-limit
                                   :key-conditions {:ClientId {:attribute-value-list [client-id]
                                                               :comparison-operator "EQ"}
                                                    :TimestampActionId {:attribute-value-list [from-sort-key-str]
                                                                        :comparison-operator "GE"}})]
    (log/trace (str "Querying jobs for client_id: " client-id))
    (map (fn [item] {:action_id (:ActionId item) :timestamp (:Timestamp item)})
         (map #(select-keys % [:ActionId :Timestamp])
              (:items (if (= from-sort-key-str "0")
                        (client-jobs-query)
                        (client-jobs-query :exclusive-start-key { :ClientId client-id :TimestampActionId from-sort-key-str })))))))
