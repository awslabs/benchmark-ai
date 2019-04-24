(ns bai-bff.services.endpoints
  (:require [bai-bff.services :refer [RunService]]
            [bai-bff.http-api :as http-api]
            [clojure.pprint :refer :all]
            [environ.core :refer [env]]
            [ring.adapter.jetty :as ring]
            [taoensso.timbre :as log])
  (:import (org.eclipse.jetty.server Server)
           (org.eclipse.jetty.util.thread QueuedThreadPool)))

(def endpoints-required-keys #{:endpoints-port})

;;TODO - come and take a look a this... apparently this ain't a thing anymore???
(defn jetty-configurator-provider [config]
  (fn [^Server server]
    (let [^QueuedThreadPool threadPool (QueuedThreadPool. (Integer/valueOf (:thread-pool-size config)))]
      (.setMaxQueued threadPool (Integer/valueOf (:max-queue-size config)))
      (.setSendServerVersion server false)
      (.setThreadPool server threadPool))))

(defrecord EndpointsServer [config int-server]
  RunService
  (start! [this]
    (locking this
      (pprint config)
      (log/info (str "starting endpoints server component... port["(:endpoints-port config)"]"))
      (pprint (type (:endpoints-port config)))
      (.assert-configured! config endpoints-required-keys)
      (let [handler (http-api/create-application-routes config)
            base-options {:port  (Integer/valueOf (:endpoints-port config "8085"))
                          :join? false}
            ;; :configurator (jetty-configurator-provider config) ;;TODO - see above
            ssl-options {:ssl? true
                         :ssl-port "443"
                         :keystore (env :keystore "keystore.jks")
                         :key-password (env :keystore-password "changeit")
                         :truststore (env :truststore "truststore.jks")
                         :trust-password (env :truststore-password "changeit")}]

        (reset! int-server (ring/run-jetty handler (merge base-options #_ssl-options))))))
  (stop! [this]
    (locking this
      (when @int-server
        (.stop @int-server))))
  Object
  (toString [_] "<EndpointsServer>"))

(defmethod print-method EndpointsServer [v ^java.io.Writer w]
  (.write w "<EndpointsServer>"))

(defn create-endpoints-service [config]
  (->EndpointsServer config
                     (atom nil)))
