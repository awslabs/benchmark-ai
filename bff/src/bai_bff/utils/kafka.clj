(ns bai-bff.utils.kafka
  (:require [taoensso.timbre :as log]
            [environ.core :refer [env]]
            [clojure.set  :refer [difference]])
  (:import (org.apache.kafka.clients.admin AdminClient AdminClientConfig NewTopic CreateTopicsResult)
           (org.apache.kafka.common.errors TopicExistsException)
           (java.lang InterruptedException)
           (java.util.concurrent ExecutionException)))

(defn create-kafka-topics [set-of-topic-names]
  (log/trace "create-kafka-topics  ["set-of-topic-names"]")
  (let [^AdminClient admin-client (AdminClient/create (doto (java.util.Properties.)
                                                        (.put AdminClientConfig/BOOTSTRAP_SERVERS_CONFIG, (env :kafka-bootstrap-servers))))
        num-partitions     (Integer/valueOf (env :kafka-default-num-partitions "1") )
        replication-factor (Integer/valueOf (env :kafka-default-replication-factor "1" ))
        all-existing-topic-names (.get (.names (.listTopics admin-client)))] ;; <-- block here on future until realized
    (log/trace "Listing of all current topics: "all-existing-topic-names)
    (when-let [missing-topics (seq (difference set-of-topic-names all-existing-topic-names))]
      (log/trace "Missing topics to be created... "missing-topics)
      (let [^CreateTopicsResult result (.createTopics admin-client (mapv #(NewTopic. % num-partitions replication-factor) missing-topics))]
        (doseq [entry (.values result)]
          (try
            (.get (.getValue entry))  ;; <-- block here on future until realized
            (log/info (format "topic [%s] has been successfully created!" (.getKey entry)))
            (catch InterruptedException e (log/warn (format "Problem creating topic [%s]: Perhaps, it has already been created "(.getKey entry)))
                   (when-not(instance? TopicExistsException (.getCause e))
                     (throw (RuntimeException. (str "I can't seem to create a Kafka topic for some crazy reason: "(.getMessage e)) e))))
            (catch ExecutionException e   (log/warn (format "Problem creating topic [%s]: Perhaps, it has already been created "(.getKey entry)))
                   (when-not(instance? TopicExistsException (.getCause e))
                     (throw (RuntimeException. (str "I can't seem to create a Kafka topic for some crazy reason: "(.getMessage e)) e)))) ))))
    (.close admin-client)))
