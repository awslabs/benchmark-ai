;;  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
;;
;;  Licensed under the Apache License, Version 2.0 (the "License").
;;  You may not use this file except in compliance with the License.
;;  A copy of the License is located at
;;
;;      http://www.apache.org/licenses/LICENSE-2.0
;;
;;  or in the "license" file accompanying this file. This file is distributed
;;  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
;;  express or implied. See the License for the specific language governing
;;  permissions and limitations under the License.
(ns bai-bff.utils.log-index
  (:require [environ.core :refer [env]]
            [taoensso.timbre :as log]
            [bai-bff.utils.parsers :as parsers]
            [clojurewerkz.elastisch.rest          :as esr]
            [clojurewerkz.elastisch.rest.document :as esd]
            [clojurewerkz.elastisch.rest.response :as esrsp]
            [clojure.pprint :as pp]))

(defn fetch-logs [client-id action-id]
  ;; performs a term query using a convenience function
  (log/trace "get-fetch-logs - client-id ["client-id"] action-id ["action-id"]")
  (let [conn (esr/connect (str "http://"(env :elasticsearch-endpoint)":"(env :elastic-search-endpoint-port "80")) {:content-type :json})
        res  (esd/search conn "logstash*" "fluentd" {:_source ["log"]
                                                     :query {:bool
                                                             {:must [{:match {:kubernetes.labels.client-id client-id}}
                                                                     {:match {:kubernetes.labels.action-id action-id}}
                                                                     {:match {:kubernetes.container_name "benchmark"}}]}}
                                                     :sort [{(keyword "@timestamp") {:order "asc"}}]
                                                     :size (parsers/parse-int (env :results-page-size "500"))})
        n    (esrsp/total-hits res)
        hits (esrsp/hits-from res)]
    (log/debug (format "Total hits: %d" n))
    (log/debug (pp/pprint hits))
    hits))
