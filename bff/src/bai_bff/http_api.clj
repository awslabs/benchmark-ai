(ns bai-bff.http-api
  (:require [bai-bff.core :refer :all]
            [bai-bff.events :as events]
            [bai-bff.services.eventbus :as eventbus]
            [clojure.pprint :refer :all]
            [clojure.java.io :as io]
            [ring.adapter.jetty :refer :all]
            [ring.util.response :refer :all]
            [compojure.core :refer :all]
            [compojure.route :as route]
            [compojure.middleware :refer [wrap-canonical-redirect]]
            [ring.middleware.json :refer [wrap-json-response wrap-json-body wrap-json-params]]
            [ring.middleware.keyword-params :refer [wrap-keyword-params]]
            [ring.middleware.params :refer [wrap-params]]
            [ring.middleware.multipart-params :refer [wrap-multipart-params]]
            [ring.middleware.reload :refer [wrap-reload]]
            [cheshire.core :as json]
            [taoensso.timbre :as log]
            [clojure.core.async :as a :refer [>!!]]))

;;----
;; To post a descriptor file do the following at the command line
;; %>curl --data-binary "@testfile.toml" http://localhost:8080/api/job/descriptor?name=gavin

;;----------------------
;; Action Functions
;;----------------------

(defn dispatch-submit-job [request body]
  (try
    (let [message-body (json/parse-string body true)]
      (log/debug "Printing request")
      (log/debug request)
      (log/debug "message body is now an event...")
      (let [event (events/message->submit-descriptor-event request message-body)
            status-event (partial events/status-event event)]
        (log/debug event)
        (log/info (json/generate-string event {:pretty true}))
        (>!! @eventbus/send-event-channel-atom [(status-event :bai-bff.events/submitted (str "Submission has been successfully received..."))])
        (>!! @eventbus/send-event-channel-atom [event])
        (:action_id event)))
    (catch Exception e
      (log/error "Could Not Parse Descriptor Input:" (.getMessage e))
      (bad-request "Could Not Parse Submitted Descriptor"))))

(defn dispatch-delete-job [request body action-id]
  (try
    (let [body-string (slurp body)]
      (log/debug "Printing request")
      (log/debug request)
      (log/debug "Body received is")
      (log/debug body-string)
      (log/debug "message body is now an event...")
      (let [event (events/message->cmd-event
                   request
                   (json/parse-string body-string true))
            status-event (partial events/status-event event)]
        (log/debug event)
        (log/info (json/generate-string event {:pretty true}))
        (>!! @eventbus/send-event-channel-atom [(status-event :bai-bff.events/submitted (str "Action received, dispatching delete for <"action-id">"))])
        (>!! @eventbus/send-event-channel-atom [event])
        (:action_id event)))
    (catch Exception e
      (log/error "Could Not Parse Descriptor Input")
      (bad-request "Could Not Parse Submitted Descriptor"))))

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
             (GET  "/" [] (response (eventbus/get-all-jobs))) ;;TODO - remove this in production...? implement me
             (POST "/" {body :body :as request} (post-proc-results (log/info (pprint request)) #_(create-job body)));TODO - implement me
             (POST "/descriptor" {{body :submit-event} :params :as request} (response (dispatch-submit-job request body)))
             (context "/:client-id" [client-id]
                      (defroutes client-routes
                        (GET    "/" [] (post-proc-results (eventbus/get-all-client-jobs client-id)))
                        (DELETE "/" [] (post-proc-results (log/info "delete-client-jobs... [NOT]") #_(delete-job action-id))))
                      (context "/:action-id" [action-id]
                               (defroutes action-routes
                                 (GET    "/" {{:keys[since] :or {since 0}} :params :as req} (post-proc-results (eventbus/get-all-client-jobs-for-action client-id action-id since)))
                                 (DELETE "/" {body :body :as request} (response (dispatch-delete-job request body action-id)))))))) ;
  (ANY "*" []
       (route/not-found (slurp (io/resource "404.html")))))

(def core-routes
  (routes info-routes k8s-routes api-routes))

(defn create-application-routes[]
  (-> #'core-routes
      (wrap-reload)
      (wrap-canonical-redirect)
      (wrap-json-response)
      (wrap-json-body {:keywords? true :bigdecimals? true})
      (wrap-keyword-params)
      (wrap-params)
      (wrap-multipart-params)
      (wrap-json-params)))
