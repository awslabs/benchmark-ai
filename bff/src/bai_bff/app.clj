(ns bai-bff.app
  "This is the entry point namespace that kicks off this application.
  The constituent services are instantiated here and dependencies are
  injected to build the full structure of this application.  A bit of
  nomenclature... a \"service\" here is a namespace where there is
  managed state through lifecycle start/stop functions.  This closely
  follows the philosophy of Stuart Sierra Component framework.
  Basically Objects ain't all bad :-) "
  (:require [bai-bff.core :refer :all]
            [bai-bff.services.configuration :refer [create-configuration-service]]
            [bai-bff.services.endpoints :refer [create-endpoints-service]]
            [taoensso.timbre :as log])
  (:gen-class))

(defn create-services
  ([] (create-services {}))
  ([{:keys [config-fn
            endpoints-fn]
     :or {config-fn     create-configuration-service
          endpoints-fn  create-endpoints-service}}]
   (let [configuration  (config-fn)
         endpoints      (endpoints-fn configuration)]
     {:configuration configuration
      :endpoints endpoints})))

(defn stop [services]
  (let [services (reverse services)]
    (doseq [service services]
      (println "Stopping service: " service)
      (.stop! service))))

(defn start
  "Start application services"
  ([] (start (create-services)))
  ([services]
   (let [services (map services [:configuration
                                 :endpoints])]
     (doseq [service services]
       (println "Starting service: " service)
       (.start! service))
     services)))

(defn -main [& args]
  (log/info (str "Starting bai-bff v" VERSION))
  (let [services (start)]
    (.addShutdownHook (Runtime/getRuntime)
                      (Thread. (fn []
                                 (log/info "Initiating shutdown process")
                                 (stop services)))))
  :started)
