(ns bai-bff.utils.persistence
  "This namespace handles the communication with the backing store"
  (:require [amazonica.aws.dynamodbv2 :as ddb]
            [taoensso.timbre :as log])
  (:import [com.amazonaws.services.dynamodbv2.model 
  												ResourceInUseException]))


(def events-table "AnubisEvents")
(def jobs-table "AnubisJobs")
(def query-limit 25)

(defn create-events-table []
 "Creates the events table.
  Fails silently in case table already exists"
 (try
		(ddb/create-table 
			:table-name events-table
			:attribute-definitions [
				{:attribute-name "action_id" :attribute-type "S"}
				;; sortkey will be timestamp:message_id
				{:attribute-name "skey" :attribute-type "S"}
			]
			:key-schema [
				{:attribute-name "action_id" :key-type "HASH"}
				{:attribute-name "skey" :key-type "RANGE"}
			]
			:billing-mode "PROVISIONED"
			:provisioned-throughput {
				:read-capacity-units 10
				:write-capacity-units 10
		 })
		(catch ResourceInUseException e (log/debug events-table "table already exists...")))
 true)

(defn create-jobs-table []
 "Creates the jobs table used to register jobs submitted to the bff"
 (try
		(ddb/create-table 
			:table-name jobs-table
			:attribute-definitions [
				{:attribute-name "client_id" :attribute-type "S"}
				;; sort key will be timetamp:action_id
				{:attribute-name "skey" :attribute-type "S"}
			]
			:key-schema [
				{:attribute-name "client_id" :key-type "HASH"}
				{:attribute-name "skey" :key-type "RANGE"}
			]
			:billing-mode "PROVISIONED"
			:provisioned-throughput {
				:read-capacity-units 10
				:write-capacity-units 10
		 })
		(catch ResourceInUseException e (log/debug jobs-table "table already exists...")))
 true)

(defn initialize []
	"Initializes the persistence layer - creates tables, etc."
	(create-events-table)
	(create-jobs-table)
	true)

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
			:timestamp (event :tstamp)
			:event event
		}]
			(log/trace "Saving event with client_id: " (:client_id item) " and action_id: " (:action_id item))
			(ddb/put-item :table-name events-table :item item)))


(defn query-events-table
	"Queries the event table for events against the supplied client_id and action_id.
  An optional last-evaluated-key can be passed in, for pagination. Will return a dynamodb query response.
  If it includes a last-evaluated-key, the next set of rows is retrieved."
  [client-id action-id & {:keys [timestamp last-evaluated-key]
  																								:or {timestamp 0
  																									    last-evaluated-key nil}}]
		(let [status-query (partial ddb/query 
				:table-name events-table 
				:limit query-limit 
				:key-conditions { 
					:action_id { 
						:attribute-value-list [action-id] 
						:comparison-operator "EQ"
					}
					:skey {
						:attribute-value-list [(str timestamp)]
						:comparison-operator "GT"
					}
				}
				;; it's theoretically possible that two actions with
				;; the same ids are generated for two different clients.
				;; Although, the probability is *really* small.
				;; The client_id filter here just to guard against murphy's law.
				:expression-attribute-names {
					"#cid" "client_id"
					"#ts" "timestamp"
				}
				:expression-attribute-values {
					":cid" client-id
					":ts" timestamp
				}
				:filter-expression "#cid = :cid AND #ts > :ts")]
		 (log/trace (str "Querying events for client_id: " client-id " and action_id: " action-id))
	 	(if (nil? last-evaluated-key)
				(status-query)
				(status-query :exclusive-start-key last-evaluated-key))))

(defn get-all-events 
	"Returns a list containing all events for a particular action-id and client-id
	 an optional timestamp parameter to restrict the starting time of the events returned"
	([client-id action-id] (get-all-events client-id action-id 0))
	([client-id action-id timestamp]
	 (log/trace (str "Getting all events for client_id: " client-id " and action_id: " action-id " from timestamp " timestamp))
	 (loop [resp (query-events-table client-id action-id :timestamp timestamp)
	        events []]
	        (if (and (not (nil? resp)) (:last-evaluated-key resp))
	        	(recur (query-events-table client-id action-id :last-evaluated-key (:last-evaluated-key resp) :timestamp timestamp)
	        	       (concat (map :event (:items resp)) events))
	        	(concat (map :event (:items resp)) events)))))

(defn query-jobs-table
	"Queries the jobs table for action ids against the supplied client_id.
  An optional last-evaluated-key can be passed in, for pagination. Will return a dynamodb query response.
  If it includes a last-evaluated-key, the next set of rows is retrieved.
  An optional timestamp can be passed in to filter the benchmarks by submission time."
  [client-id & {:keys [timestamp last-evaluated-key]
  																								:or {timestamp 0
  																									    last-evaluated-key nil}}]
		(let [jobs-query (partial ddb/query 
				:table-name jobs-table 
				:limit query-limit 
				:key-conditions { 
					:client_id { 
						:attribute-value-list [client-id] 
						:comparison-operator "EQ"
					}
					:skey {
						:attribute-value-list [(str timestamp)]
						:comparison-operator "GT"
					}
				}
				:expression-attribute-names {
					"#ts" "timestamp"
				}
				:expression-attribute-values {
					":ts" timestamp
				}
				:filter-expression "#ts > :ts")]
		 (log/trace (str "Querying jobs for client_id: " client-id))
	 	(if (nil? last-evaluated-key)
				(jobs-query)
				(jobs-query :exclusive-start-key last-evaluated-key))))

(defn get-all-jobs 
	"Returns a list containing all action ids of jobs submitted by the given client-id
	 an optional timestamp parameter to restrict the submission time of the jobs"
	([client-id] (get-all-jobs client-id 0))
	([client-id timestamp]
	 (log/trace (str "Getting all jobs for client_id: " client-id " from timestamp " timestamp))
	 (loop [resp (query-jobs-table client-id :timestamp timestamp)
	        jobs []]
	        (if (and (not (nil? resp)) (:last-evaluated-key resp))
	        	(recur (query-jobs-table client-id :last-evaluated-key (:last-evaluated-key resp) :timestamp timestamp)
	        	       (concat (map :action_id (:items resp)) jobs))
	        	(concat (map :action_id (:items resp)) jobs)))))

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
