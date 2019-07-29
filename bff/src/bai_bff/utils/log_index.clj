(ns bai-bff.utils.log-index
  (:require [environ.core :refer [env]]
            [taoensso.timbre :as log]
            [clojurewerkz.elastisch.rest          :as esr]
            [clojurewerkz.elastisch.rest.document :as esd]
            [clojurewerkz.elastisch.query         :as q]
            [clojurewerkz.elastisch.rest.response :as esrsp]
            [clojure.pprint :as pp]))

(defn fetch-logs [client-id action-id]
  ;; performs a term query using a convenience function
  (log/trace "get-job-results - client-id ["client-id"] action-id ["action-id"]")
  (let [conn (esr/connect (str "http://"(env :es-endpoint)":80"))
        res  (esd/search conn "logstash*" "fluentd" :query {:match {:kubernetes.labels.action-id action-id}} :sort [{(keyword "@timestamp") {:order "asc"}}])
        n    (esrsp/total-hits res)
        hits (esrsp/hits-from res)]
    (log/debug (format "Total hits: %d" n))
    (log/report (pp/pprint hits))
    (pp/pprint hits)))
