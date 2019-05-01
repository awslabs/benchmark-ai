(ns bai-bff.services.sinks.kafka-sink
  (:require [bai-bff.services :refer [RunService Sink]]
            [bai-bff.utils.srv :refer :all]
            [bai-bff.services.eventbus :refer [send-event-channel-atom]]
            [cheshire.core :as json]
            [taoensso.timbre :as log]
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

(defrecord KafkaSinkService [config producer worker-thread started?]
  RunService
  (start! [this]
    (locking this
      (when (and (Boolean/valueOf (get config :send-kafka true))
                 (not @started?))
        (log/info "Starting kafka producer! (sink)")
        (.assert-configured! config kafka-keys)
        (reset! worker-thread
                (Thread. (fn []
                           (let [kafka-config (doto (java.util.Properties.)
                                                (.put "bootstrap.servers" (get config :kafka-bootstrap-servers))
                                                (.put "acks"              (get config :kafka-acks "all"))
                                                (.put "retries"           (Integer/valueOf  (get config :kafka-retries 0)))
                                                (.put "max.in.flight.requests.per.connection"     (Integer/valueOf  (get config :kafka-max-in-flight-requests-per-connection 5)))
                                                (.put "batch.size"        (Integer/valueOf  (get config :kafka-batch-size 16384)))
                                                (.put "linger.ms"         (Integer/valueOf  (get config :kafka-linger-ms 0)))
                                                (.put "buffer.memory"     (Integer/valueOf  (get config :kafka-buffer-memory 33554432)))
                                                (.put "compression.type"  (get config :kafka-compression-type "none"))
                                                (.put "key.serializer"    (get config :kafka-key-serializer   "org.apache.kafka.common.serialization.StringDeserializer"))
                                                (.put "value.serializer"  (get config :kafka-value-serializer "org.apache.kafka.common.serialization.StringDeserializer")))]

                             (reset! producer (KafkaProducer. kafka-config))
                             (while @started?
                               (.send @producer (ProducerRecord. (get config :kafka-sink-topic) (str(<!! @send-event-channel-atom)))))
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


(defn create-kafka-sink-service [config]
  (KafkaSinkService. config (atom nil) (atom nil) (atom false)))
