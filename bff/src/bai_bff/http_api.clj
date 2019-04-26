(ns bai-bff.http-api
  (:require [bai-bff.core :refer :all]
            [bai-bff.events :refer :all]
            [clojure.pprint :refer :all]
            [clojure.java.io :as io]
            [ring.adapter.jetty :refer :all]
            [ring.util.response :refer :all]
            [compojure.core :refer :all]
            [compojure.route :as route]
            [compojure.middleware :refer [wrap-canonical-redirect]]
            [ring.middleware.json :refer [wrap-json-response wrap-json-body wrap-json-params]]
            [ring.middleware.keyword-params :refer [wrap-keyword-params]]
            [ring.middleware.reload :refer [wrap-reload]]
            [cheshire.core :as json]
            [taoensso.timbre :as log]))

;;----
;; To post a descriptor file do the following at the command line
;; %>curl --data-binary "@testfile.toml" http://localhost:8080/api/job/descriptor?name=gavin



;;----------------------
;; Misc Helper functions...
;;----------------------
;; Handle post processing "presentation"
(defn post-proc-results [results]
  (cond
    (nil? results) {:status 404}
    (empty? results) {:status 404}
    :else (response results)))


;;----------------------
;; REST API routing...
;;----------------------
(defroutes info-routes
  (GET "/" req
       (str "<hr><CENTER><h1>Welcome To The BAI-BFF Service (v"VERSION")</h1><a href=\"https://github.com/MXNetEdge/benchmark-ai/\">https://github.com/MXNetEdge/benchmark-ai</a></CENTER><hr><p>")))

;; Kubernetes Liveliness and Readiness endpoints
(defroutes k8s-routes
  (GET "/ready" req
       {:status 200
        :headers {"Content-Type" "text/html"}
        :body "sure am ready"})
  (GET "/lively" req
       {:status 200
        :headers {"Content-Type" "text/html"}
        :body "sure am lively"}))

;; API for BFF to post and query data
(defroutes api-routes
  (GET "/api" []
       (str "<hr><CENTER><h1> BAI-BFF HTTP Service API (v"VERSION")</h1><a href=\"http://foobar.com/api\">docs</a></CENTER><hr>"))
  (context "/api/job" []
           (defroutes job-routes
             (GET  "/" [] (response nil #_(get-all-jobs))) ;;TODO - remove this in production...? implement me
             (POST "/" {body :body :as request} (post-proc-results (log/info (pprint request)) #_(create-job body)));TODO - implement me
             (POST "/descriptor" {body :body :as request} ((fn [request body]
                                                             (try
                                                               (let [body-string (slurp body)]
                                                                 (println "Printing request")
                                                                 (pprint request)
                                                                 (println "Body recieved is")
                                                                 (pprint body-string)
                                                                 (println "message body is now an event...")
                                                                 (let [event (message->event
                                                                              request
                                                                              (json/parse-string body-string true))]
                                                                   (println (json/generate-string event {:pretty true}))
                                        ;(eventbus/dispatch-submit event) ; TODO - implement me!
                                                                   (response (:action_id event))))
                                                               (catch IllegalStateException e
                                                                 (log/error "Could Not Parse Descriptor Input")
                                                                 (response {:status 500
                                                                            :headers {"Content-Type" "text/html"}
                                                                            :body "Could Not Parse Submitted Descriptor"})))) request body))
             (context "/:action-id" [action-id]
                      (defroutes job-routes
                        (GET    "/status" [] (post-proc-results  (log/info "/status") #_(get-job-status action-id))) ;TODO - implement me
                        (DELETE "/" [] (post-proc-results (log/info "delete-job") #_(delete-job action-id)))))))        ;TODO - implement me
  (ANY "*" []
       (route/not-found (slurp (io/resource "404.html")))))

(def core-routes
  (routes info-routes k8s-routes api-routes))

(defn create-application-routes[config]
  (-> #'core-routes
      (wrap-reload)
      (wrap-canonical-redirect)
      (wrap-json-response)
      (wrap-json-body {:keywords? true :bigdecimals? true})
      (wrap-keyword-params)
      (wrap-json-params)))
