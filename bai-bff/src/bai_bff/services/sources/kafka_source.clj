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
(ns bai-bff.services.sources.kafka-source
  (:require [bai-bff.services :refer [RunService]] ;Source
            [bai-bff.services.eventbus :refer [receive-events-channel-atom]]
            [bai-bff.utils.utils :refer [assert-configured!]]
            [bai-bff.utils.kafka :refer :all]
            [environ.core :refer [env]]
            [clojure.string :as s]
            [cheshire.core :as json]
            [taoensso.timbre :as log])
  (:import  [org.apache.kafka.clients.consumer KafkaConsumer]
            [java.time Duration]))

(def kafka-keys
  #{:kafka-bootstrap-servers
    :kafka-consumer-group-id
    :kafka-source-topics
    :kafka-poll-interval-ms})

(defn- records->events
  "Uses the Kafka records object to retrieve the values from individual
  records' values, for the specified topic, and convert them to JSON.
  The result is a seq of events.  Please not that you are not allowed
  to use the records object in a multi-threaded environment (I don't
  believe). See:
  https://kafka.apache.org/11/javadoc/org/apache/kafka/clients/consumer/ConsumerRecords.html#records-java.lang.String-"
  [records topic]
  (remove nil? (map (fn [record]
                      (try
                        ;; XXX: do this with a value.deserializer (as a speed optimization so you xfer from binary once)
                        (json/decode (.value record) true)
                        (catch Exception e
                          (log/warn (str "Could not decode ingress message because... <"(.getMessage e)">, ignored and skipping..."))
                          nil))) ;<-- TODO instrument to prometheus for example
                    (.records records topic))))

    ; XXX: We need to create a mechanism to propagate failure here as
    ; worker-thread deaths will go unnoticed :/
(defrecord KafkaSourceService [topic->process-fn-map worker-thread shutdown? started?]
  RunService
  (start! [this]
    (locking this
      (when-not @started?
        (log/info "Starting kafka consumer! (source)")
        (assert-configured! kafka-keys)
        (let [kafka-source-topics (set (s/split (env :kafka-source-topics) #",|:"))]
          (create-kafka-topics kafka-source-topics)
          (log/trace "Kicking off consumer thread...")
          (reset! worker-thread
                  (Thread. (fn []
                             (let [consumer (KafkaConsumer. (doto (java.util.Properties.)
                                        ; XXX: Implement DNS service discovery
                                                              (.put "bootstrap.servers"  (env :kafka-bootstrap-servers))
                                                              (.put "group.id",          (env :kafka-consumer-group-id))
                                                              (.put "auto.offset.reset"  (env :kafka-auto-offset-reset "latest"))
                                                              (.put "max.poll.interval.ms" (Integer/parseInt (env :kafka-max-poll-interval-ms "300000")))
                                                              (.put "session.timeout.ms"   (Integer/parseInt (env :kafka-session-timeout-ms "10000")))
                                                              (.put "key.deserializer",  (env :kafka-key-deserializer   "org.apache.kafka.common.serialization.StringDeserializer"))
                                                              (.put "value.deserializer" (env :kafka-value-deserializer "org.apache.kafka.common.serialization.StringDeserializer"))))]
                               (log/info (str "Configuring to consume from ["(count kafka-source-topics)"] topics: "(env :kafka-source-topics)))
                               (reset! topic->process-fn-map
                                       (merge (zipmap kafka-source-topics (repeatedly #(fn [event] (log/warn "No handler implementation for this event <"event">")))) @topic->process-fn-map))
                               (.subscribe consumer kafka-source-topics)
                               (while @started?
                                 (let [poll-interval (Duration/ofMillis(Integer/parseInt (env :kafka-poll-interval-ms)))
                                       records (.poll consumer poll-interval)]
                                   (when (every? true? (map (fn [topic]
                                                              ((get @topic->process-fn-map topic) (records->events records topic))) kafka-source-topics))
                                     ;; XXX: Add telemetry here - or even better write HOF around the process functions that produce metrics!
                                     (.commitSync consumer))))
                               (log/info "Shutdown kafka consumer (source)")
                               (.close consumer)
                               (reset! shutdown? true))))))
        (log/info "Kafka services started")
        (reset! started? true)
        (.start @worker-thread))))
  (stop! [this]
    (when @started?
      (locking this
        (reset! started? false)
        (while (not @shutdown?)
          (Thread/sleep 5))
        (.interrupt @worker-thread)
        (while (.isAlive @worker-thread)
          (Thread/sleep 5)))))
  Object
  (toString [_] "<KafkaSourceService>"))

(defmethod print-method KafkaSourceService [v ^java.io.Writer w]
  (.write w "<KafkaSourceService>"))


(defn create-kafka-source-service [topic->process-fn-map]
  (KafkaSourceService. (atom topic->process-fn-map)
                       (atom nil)
                       (atom false)
                       (atom false)))
