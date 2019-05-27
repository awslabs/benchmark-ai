(ns bai-bff.services.sinks.kafka-sink
  (:require [bai-bff.services :refer [RunService Sink]]
            [bai-bff.services.eventbus :refer [send-event-channel-atom]]
            [bai-bff.utils.utils :refer [assert-configured!]]
            [cheshire.core :as json]
            [taoensso.timbre :as log]
            [environ.core :refer [env]]
            [clojure.string :as s]
            [clojure.set :refer [difference]]
            [clojure.core.async :as a :refer [>! <! >!! <!! go chan buffer close! thread
                                              alts! alts!! timeout]])
  (:import (org.apache.kafka.clients CommonClientConfigs)
           (org.apache.kafka.clients.producer KafkaProducer ProducerRecord)
           (org.apache.kafka.clients.admin AdminClient AdminClientConfig NewTopic CreateTopicsResult)))

(def kafka-keys
  #{:kafka-bootstrap-servers
    :kafka-sink-topics})

    ;NOTE: You should set "max.in.flight.requests.per.connection" to 1, esp. if "retries" is > 0 if you want to preserve order!

(defn- create-kafka-topics [set-of-topic-names]
  (log/trace "create-kafka-topics  ["set-of-topic-names"]")
  (let [^AdminClient admin-client (AdminClient/create (doto (java.util.Properties.)
                                                        (.put AdminClientConfig/BOOTSTRAP_SERVERS_CONFIG, (env :kafka-bootstrap-servers))))
        num-partitions     3 ;;TODO how can we not hard code them? config-map? environment?
        replication-factor 3 ;;TODO how can we not hard code them? config-map? environment?
        all-existing-topic-names (.get (.names (.listTopics admin-client)))] ;; <-- block here on future until realized
    (log/trace "Listing of all current topics: "all-existing-topic-names)
    (when-let [missing-topics (seq (difference set-of-topic-names all-existing-topic-names))]
      (log/trace "Missing topics to be created... "missing-topics)
      (let [^CreateTopicsResult result (.createTopics admin-client (mapv #(NewTopic. % num-partitions replication-factor) missing-topics))]
        (doseq [entry (.values result)]
          (try
            (.get (.getValue entry))  ;; <-- block here on future until realized
            (log/info (format "topic [%s] has been successfully created!" (.getKey entry)))
            (catch Exception e (log/warn (format "Problem creating topic [%s]: Perhaps, it has already been created "(.getKey entry))))))))
    (.close admin-client)))

(defrecord KafkaSinkService [producer worker-thread started?]
  RunService
  (start! [this]
    (locking this
      (when (and (Boolean/valueOf (env :send-kafka true))
                 (not @started?))
        (log/info "Starting kafka producer! (sink)")
        (assert-configured! kafka-keys)
        (let [allowed-kafka-sink-topics (set (s/split (env :kafka-sink-topics) #",|:"))]
          (create-kafka-topics allowed-kafka-sink-topics)
          (log/trace "Kicking off producer thread...")
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
                                                  (.put "key.serializer"    (env :kafka-key-serializer   "org.apache.kafka.common.serialization.StringSerializer"))
                                                  (.put "value.serializer"  (env :kafka-value-serializer "org.apache.kafka.common.serialization.StringSerializer")))]
                               (log/info (str "Allowed to dispatch to ["(count allowed-kafka-sink-topics)"] topics: "(env :kafka-sink-topics)))
                               (reset! producer (KafkaProducer. kafka-config))
                               (while @started?
                                 (let [[client-id-key event] (<!! @send-event-channel-atom)]
                                   (if (allowed-kafka-sink-topics (:type event)) (.send @producer (ProducerRecord. (:type event) (str client-id-key) (str(json/generate-string event))))
                                       (log/warn (str "This topic ["(:type event)"] is not present in the set of permitted topics; skipping...")))))
                               (log/info "Shutdown Kafka producer (sender/sink)")
                               (.close @producer)
                               )))))
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
