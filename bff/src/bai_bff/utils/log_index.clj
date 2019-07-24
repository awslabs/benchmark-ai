(ns bai-bff.utils.log-index
  (:require [environ.core :refer [env]]
            [taoensso.timbre :as log]
            [clojurewerkz.elastisch.native          :as es]
            [clojurewerkz.elastisch.native.document :as esd]
            [clojurewerkz.elastisch.query           :as q]
            [clojurewerkz.elastisch.native.response :as esrsp]
            [clojure.pprint :as pp]))

(defn fetch-logs [client-id action-id]
  ;; performs a term query using a convenience function
  (let [conn (es/connect [[(env :es-endpoint) 443]] {"cluster.name" "logs"})
        res  (esd/search conn "kubernetes.la*" "fluentd" :query {:match {:kubernetes.labels.action-id action-id}} :sort [{(keyword "@timestamp") {:order "asc"}}])
        n    (esrsp/total-hits res)
        hits (esrsp/hits-from res)]
    (log/debug (format "Total hits: %d" n))
    (pp/pprint hits)))
