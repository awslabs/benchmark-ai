(ns bai-bff.services.sinks.kafka-sink
  (:require [bai-bff.services :refer [RunService Sink]]
            [bai-bff.services.eventbus :refer [send-event-channel-atom]]
            [bai-bff.utils.utils :refer [assert-configured!]]
            [cheshire.core :as json]
            [taoensso.timbre :as log]
            [environ.core :refer [env]]
            [clojure.core.async :as a :refer [>! <! >!! <!! go chan buffer close! thread
                                              alts! alts!! timeout]])
  (:import (org.apache.kafka.clients.producer KafkaProducer
                                              ProducerRecord)
           (org.apache.kafka.clients CommonClientConfigs)))

(def kafka-keys
  #{:kafka-bootstrap-servers
    :kafka-sink-topic
    ;:send-kafka  ; <-- this code's own flag for turning on and off kafka sending entirely
    ;:kafka-acks
    ;:kafka-retries
    ;:kafka-max-in-flight-requests-per-connection
    ;:kafka-batch-size
    ;:kafka-linger-ms
    ;:kafka-buffer-memory
    ;:kafka-compression-type
    ;:kafka-key-serializer
    ;:kafka-value-serializer
    })

    ;NOTE: You should set "max.in.flight.requests.per.connection" to 1, esp. if "retries" is > 0 if you want to preserve order!

(defrecord KafkaSinkService [producer worker-thread started?]
  RunService
  (start! [this]
    (locking this
      (when (and (Boolean/valueOf (env :send-kafka true))
                 (not @started?))
        (log/info "Starting kafka producer! (sink)")
        (assert-configured! kafka-keys)
        (reset! worker-thread
                (Thread. (fn []
                           (let [kafka-config (doto (java.util.Properties.)
                                                (.put "bootstrap.servers" (env :kafka-bootstrap-servers))
                                                (.put "acks"              (env :kafka-acks "all"))
                                                (.put "retries"           (Integer/valueOf  (env :kafka-retries 0)))
                                                (.put "max.in.flight.requests.per.connection"     (Integer/valueOf  (env :kafka-max-in-flight-requests-per-connection 5)))
                                                (.put "batch.size"        (Integer/valueOf  (env :kafka-batch-size 16384)))
                                                (.put "linger.ms"         (Integer/valueOf  (env :kafka-linger-ms 0)))
                                                (.put "buffer.memory"     (Integer/valueOf  (env :kafka-buffer-memory 33554432)))
                                                (.put "compression.type"  (env :kafka-compression-type "none"))
                                                (.put "key.serializer"    (env :kafka-key-serializer   "org.apache.kafka.common.serialization.StringDeserializer"))
                                                (.put "value.serializer"  (env :kafka-value-serializer "org.apache.kafka.common.serialization.StringDeserializer")))]

                             (reset! producer (KafkaProducer. kafka-config))
                             (while @started?
                               (.send @producer (ProducerRecord. (env :kafka-sink-topic) (str(<!! @send-event-channel-atom)))))
                             (log/info "Shutdown Kafka producer (sender/sink)")
                             (.close @producer)
                             ))))
        (log/info "Kafka Sink Service started...")
        (reset! started? true)
        (.start @worker-thread))))
  (stop! [_]
    (when @started?
      (reset! started? false)))
  Sink
  (send! [_ message]
    (log/info "<this is a no-op - remove me ["message"]>")) ; TODO use sink as a marker interface don't need this call directly.
  Object
  (toString [_] "<KafkaSinkService>"))

(defmethod print-method KafkaSinkService [v ^java.io.Writer w]
  (.write w "<KafkaSinkService>"))

(defn create-kafka-sink-service []
  (KafkaSinkService. (atom nil) (atom nil) (atom false)))
