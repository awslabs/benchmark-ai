(ns bai-bff.services.sources.kafka-source
  (:require [bai-bff.services :refer [RunService]] ;Source
            [cheshire.core :as json]
            [bai-bff.utils.srv :refer :all]
            [taoensso.timbre :as log])
  (:import  [org.apache.kafka.clients.consumer KafkaConsumer]))

(def kafka-keys
  #{:kafka-bootstrap-servers
    :kafka-group-id
    :kafka-source-topic
    :kafka-poll-interval-ms
    ;:kafka-auto-offset-reset
    ;:kafka-session-timeout-ms
    })

    ; XXX: We need to create a mechanism to propagate failure here as
    ; worker-thread deaths will go unnoticed :/
(defrecord KafkaSourceService [process-records-fn config worker-thread shutdown? started?]
  RunService
  (start! [this]
    (locking this
      (when-not @started?
        (log/info "Starting kafka consumer! (source)")
        (.assert-configured! config kafka-keys)
        (reset! worker-thread
                (Thread. (fn []
                           (let [consumer (KafkaConsumer. (doto (java.util.Properties.)
                                        ; XXX: Implement DNS service discovery
                                                            (.put "bootstrap.servers"  (get config :kafka-bootstrap-servers))
                                                            (.put "group.id",          (get config :kafka-group-id))
                                                            (.put "auto.offset.reset"  (get config :kafka-auto-offset-reset "latest"))
                                                            (.put "session.timeout.ms" (Integer/parseInt (get config :kafka-session-timeout-ms 10000)))
                                                            (.put "key.deserializer",  (get config :kafka-key-serializer   "org.apache.kafka.common.serialization.StringDeserializer"))
                                                            (.put "value.deserializer" (get config :kafka-value-serializer "org.apache.kafka.common.serialization.StringDeserializer"))))]
                             (.subscribe consumer [(get config :kafka-source-topic)])
                             (while @started?
                               (let [poll-interval (Integer/parseInt (get config :kafka-poll-interval-ms))
                                     records (.poll consumer poll-interval)
                                     events (map (fn [record]
                                                   (json/decode (.value record) true))
                                                 (.records records (get config :kafka-source-topic)))]
                                        ; XXX: do this with a value.deserializer
                                 (when-not (= false (process-records-fn events))
                                        ; XXX: Add telemetry
                                   (.commitSync consumer))))
                             (log/info "Shutdown kafka consumer (source)")
                             (.close consumer)
                             (reset! shutdown? true)))))
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


(defn create-kafka-source-service [process-records-fn config]
  (KafkaSourceService. process-records-fn
                       config
                       (atom nil)
                       (atom false)
                       (atom false)))
