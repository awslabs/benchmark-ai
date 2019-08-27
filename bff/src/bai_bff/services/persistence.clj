(ns bai-bff.services.persistence
  "This namespace handles the communication with the backing store"
  (:require [amazonica.aws.dynamodbv2 :as ddb]
            [taoensso.timbre :as log])
  (:import [com.amazonaws.services.dynamodbv2.model 
  												ResourceInUseException]))


(def events-table "AnubisStatus")
(def query-limit 25)

(defn create-events-table []
 "Creates the events table.
  Fails silently in case table already exists"
 (try
		(ddb/create-table 
			:table-name events-table
			:attribute-definitions [
				{:attribute-name "action_id" :attribute-type "S"}
				{:attribute-name "skey" :attribute-type "S"}
			]
			:key-schema [
				{:attribute-name "action_id" :key-type "HASH"}
				{:attribute-name "skey" :key-type "RANGE"}
			]
			:billing-mode "PROVISIONED"
			:provisioned-throughput {
				:read-capacity-units 30
				:write-capacity-units 30
		 })
		(catch ResourceInUseException e (log/debug events-table " already exists ")))
 true)

(defn initialize []
	"Initializes the persistence layer - creates tables, etc."
	(create-events-table)
	true)

(defn save-event [client_id action_id event]
 "Stores an event in the event table. The action_id is used
  as the partition key. To guarantee order and uniqueness, a composite key
  tstamp:message_id is used as the sort key. The action_id is set explicitly 
  (rather than taken directly from the event) to allow the flexibility of storing
  an event against a target action_id. For instance, we would like to log the 
  outcome of a cancel command against its target action_id."
	(let [item {
			:action_id action_id
			:skey (str (event :tstamp) ":" (event :message_id))
			:client_id client_id
			:event event
		}]
			(log/trace "Saving event with client_id: " (:client_id event) " and action_id: " (:action_id event))
			(ddb/put-item :table-name events-table :item item)))


(defn query-events-table
	"Queries the event table for events against the supplied client_id and action_id.
  An optional last_evaluated_key can be passed in, for pagination. Will return a dynamodb query response.
  If it includes a last_evaluated_key, the next set of rows is retrieved."
  [client_id action_id & {:keys [timestamp last_evaluated_key]
  																								:or {timestamp 0
  																									    last_evaluated_key nil}}]
		(let [status-query (partial ddb/query 
				:table-name events-table 
				:limit query-limit 
				:key-conditions { 
					:action_id { 
						:attribute-value-list [action_id] 
						:comparison-operator "EQ"
					}
					:skey {
						:attribute-value-list [(str timestamp)]
						:comparison-operator "GE"
					}
				}
				:expression-attribute-names {
					"#cid" "client_id"
				}
				:expression-attribute-values {
					":cid" client_id
				}
				:filter-expression "#cid = :cid")]
		 (log/trace (str "Querying events for client_id: " client_id " and action_id: " action_id))
	 	(if (nil? last_evaluated_key)
				(status-query)
				(status-query :exclusive-start-key last_evaluated_key))))

(defn get-all-events 
	"Returns a list containing all events for a particular action_id and client_id
	 an optional timestamp parameter to restrict the starting time of the events returned"
	([client_id action_id] (get-all-events client_id action_id 0))
	([client_id action_id timestamp]
	 (log/trace (str "Getting all events for client_id: " client_id " and action_id: " action_id " from timestamp " timestamp))
	 (loop [resp (query-events-table client_id action_id :timestamp timestamp)
	        events []]
	        (println events)
	        (if (and (not (nil? resp)) (:last-evaluated-key resp))
	        	(recur (query-events-table client_id action_id :last_evaluated_key (:last-evaluated-key resp) :timestamp timestamp)
	        	       (concat (map :event (:items resp)) events))
	        	(concat (map :event (:items resp)) events)))))
