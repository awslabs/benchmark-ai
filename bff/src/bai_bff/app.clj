(ns bai-bff.app
  "This is the entry point namespace that kicks off this application.
  The constituent services are instantiated here and dependencies are
  injected to build the full structure of this application.  A bit of
  nomenclature... a \"service\" here is a namespace where there is
  managed state through lifecycle start/stop functions.  This closely
  follows the philosophy of Stuart Sierra Component framework.
  Basically Objects ain't all bad :-) "
  (:require [bai-bff.core :refer :all]
            [bai-bff.services.sinks.kafka-sink     :refer [create-kafka-sink-service]]
            [bai-bff.services.sources.kafka-source :refer [create-kafka-source-service]]
            [bai-bff.services.eventbus   :as bus   :refer [create-eventbus-service]]
            [bai-bff.services.endpoints            :refer [create-endpoints-service]]
            [environ.core :refer [env]]
            [clojure.string :refer [trim]]
            [taoensso.timbre :as log])
  (:gen-class))

;; #{:trace :debug :info :warn :error :fatal :report}
(log/set-level! (keyword (trim ^String(env :logging-level "info"))))

(defn create-services
  ([] (create-services {}))
  ([{:keys [eventbus-fn
            kafka-sink-fn
            kafka-source-fn
            endpoints-fn]
     :or {eventbus-fn     create-eventbus-service
          kafka-sink-fn   create-kafka-sink-service
          kafka-source-fn create-kafka-source-service
          endpoints-fn    create-endpoints-service}}]
   (let [eventbus       (eventbus-fn)
         kafka-sink     (kafka-sink-fn)
         kafka-source   (kafka-source-fn {"BAI_APP_STATUS" bus/process-status-records
                                          "CMD_RETURN"     bus/process-cmd-return-records}) ; <-- TODO: story for event reception TBD <= here to be annoyingly obvious
         endpoints      (endpoints-fn)]
     {:eventbus      eventbus
      :kafka-sink    kafka-sink
      :kafka-source  kafka-source
      :endpoints     endpoints})))

(defn stop [services]
  (let [services (reverse services)]
    (doseq [service services]
      (log/report "Stopping service: " service)
      (.stop! service))))

(defn start
  "Start application services"
  ([] (start (create-services)))
  ([services]
   (let [services (map services [:eventbus
                                 :kafka-sink
                                 :kafka-source
                                 :endpoints])]
     ;; start services
     (doseq [service services]
       (log/report "Starting service: " service)
       (.start! service))
     services)))

(defn -main [& args]
  (log/report (str "Starting bai-bff v" VERSION))
  (let [services (start)]
    (.addShutdownHook (Runtime/getRuntime)
                      (Thread. (fn []
                                 (log/info "Initiating shutdown process")
                                 (stop services)))))
  :started)
