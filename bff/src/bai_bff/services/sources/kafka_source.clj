(ns bai-bff.services.sources.kafka-source
  (:require [bai-bff.services :refer [RunService]] ;Source
            [bai-bff.services.eventbus :refer [receive-events-channel-atom]]
            [bai-bff.utils.utils :refer [assert-configured!]]
            [environ.core :refer [env]]
            [cheshire.core :as json]
            [taoensso.timbre :as log])
  (:import  [org.apache.kafka.clients.consumer KafkaConsumer]))

(def kafka-keys
  #{:kafka-bootstrap-servers
    :kafka-consumer-group-id
    :kafka-source-topic
    :kafka-poll-interval-ms
    ;:kafka-auto-offset-reset
    ;:kafka-session-timeout-ms
    })

    ; XXX: We need to create a mechanism to propagate failure here as
    ; worker-thread deaths will go unnoticed :/
(defrecord KafkaSourceService [process-records-fn worker-thread shutdown? started?]
  RunService
  (start! [this]
    (locking this
      (when-not @started?
        (log/info "Starting kafka consumer! (source)")
        (assert-configured! kafka-keys)
        (reset! worker-thread
                (Thread. (fn []
                           (let [consumer (KafkaConsumer. (doto (java.util.Properties.)
                                        ; XXX: Implement DNS service discovery
                                                            (.put "bootstrap.servers"  (env :kafka-bootstrap-servers))
                                                            (.put "group.id",          (env :kafka-consumer-group-id))
                                                            (.put "auto.offset.reset"  (env :kafka-auto-offset-reset "latest"))
                                                            (.put "session.timeout.ms" (Integer/parseInt (env :kafka-session-timeout-ms 10000)))
                                                            (.put "key.deserializer",  (env :kafka-key-serializer   "org.apache.kafka.common.serialization.StringDeserializer"))
                                                            (.put "value.deserializer" (env :kafka-value-serializer "org.apache.kafka.common.serialization.StringDeserializer"))))]
                             (.subscribe consumer [(env :kafka-source-topic)])
                             (while @started?
                               (let [poll-interval (Integer/parseInt (env :kafka-poll-interval-ms))
                                     records (.poll consumer poll-interval)
                                     events (map (fn [record]
                                                   (json/decode (.value record) true))
                                                 (.records records (env :kafka-source-topic)))]
                                        ; XXX: do this with a value.deserializer
                                 (when-not (false? (process-records-fn events)) ;;TODO; (zoiks) - replace this process-records-fn with putting events on the @receive-events-channel-atom channel
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


(defn create-kafka-source-service [process-records-fn]
  (KafkaSourceService. process-records-fn
                       (atom nil)
                       (atom false)
                       (atom false)))
