(ns bai-bff.utils.log-index
  (:require [environ.core :refer [env]]
            [taoensso.timbre :as log]
            [clojurewerkz.elastisch.rest          :as esr]
            [clojurewerkz.elastisch.rest.document :as esd]
            [clojurewerkz.elastisch.rest.response :as esrsp]
            [clojure.pprint :as pp]))

(defn fetch-logs [client-id action-id]
  ;; performs a term query using a convenience function
  (log/trace "get-fetch-logs - client-id ["client-id"] action-id ["action-id"]")
  (let [conn (esr/connect (str "http://"(env :elasticsearch-endpoint)":80") {:content-type :json})
        res  (esd/search conn "logstash*" "fluentd" {:_source ["log"]
                                                     :query {:bool
                                                             {:must [{:match {:kubernetes.labels.client-id client-id}}
                                                                     {:match {:kubernetes.labels.action-id action-id}}
                                                                     {:match {:kubernetes.container_name "benchmark"}}]}}
                                                     :sort [{(keyword "@timestamp") {:order "asc"}}]
                                                     :size 500})
        n    (esrsp/total-hits res)
        hits (esrsp/hits-from res)]
    (log/debug (format "Total hits: %d" n))
    (log/debug (pp/pprint hits))
    hits))
