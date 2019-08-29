(ns bai-bff.utils.persistence
  "This namespace handles the communication with the backing store"
  (:require [amazonica.aws.dynamodbv2 :as ddb]
            [taoensso.timbre :as log])
  (:import [com.amazonaws.services.dynamodbv2.model 
  												ResourceInUseException]))


(def events-table "AnubisEvents")
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
			(log/trace "Saving event with client_id: " (:client_id event) " and action_id: " (:action_id event))
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
						:comparison-operator "GE"
					}
				}
				:expression-attribute-names {
					"#cid" "client_id"
				}
				:expression-attribute-values {
					":cid" client-id
				}
				:filter-expression "#cid = :cid")]
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
	        (println events)
	        (if (and (not (nil? resp)) (:last-evaluated-key resp))
	        	(recur (query-events-table client-id action-id :last_evaluated_key (:last-evaluated-key resp) :timestamp timestamp)
	        	       (concat (map :event (:items resp)) events))
	        	(concat (map :event (:items resp)) events)))))
