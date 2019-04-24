(ns bai-bff.services.endpoints
  (:require [bai-bff.services :refer [RunService]]
            [bai-bff.http-api :as http-api]
            [bai-bff.utils.utils :refer [assert-configured!]]
            [clojure.pprint :refer :all]
            [environ.core :refer [env]]
            [ring.adapter.jetty :as ring]
            [taoensso.timbre :as log])
  (:import (org.eclipse.jetty.server Server)
           (org.eclipse.jetty.util.thread QueuedThreadPool)))

(def endpoints-required-keys #{:endpoints-port})

;;TODO - come and take a look a this... apparently this ain't a thing anymore???
(defn jetty-configurator-provider []
  (fn [^Server server]
    (let [^QueuedThreadPool threadPool (QueuedThreadPool. (Integer/valueOf (env :thread-pool-size)))]
      (.setMaxQueued threadPool (Integer/valueOf (env :max-queue-size)))
      (.setSendServerVersion server false)
      (.setThreadPool server threadPool))))

(defrecord EndpointsServer [int-server]
  RunService
  (start! [this]
    (locking this
      (log/info (str "starting endpoints server component... port["(env :endpoints-port)"]"))
      (pprint (type (env :endpoints-port)))
      (assert-configured! endpoints-required-keys)
      (let [handler (http-api/create-application-routes)
            base-options {:port  (Integer/valueOf (env :endpoints-port "8085"))
                          :join? false}
            ;; :configurator (jetty-configurator-provider) ;;TODO - see above
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

(defn create-endpoints-service []
  (->EndpointsServer (atom nil)))
