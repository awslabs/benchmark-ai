(ns bai-client.app
  (:require [clojure.tools.cli :refer [parse-opts]])
  (:gen-class))

(def cli-options
  [["-p" "--port PORT" "PORT NUMBER"
    :default 80
    :parse-fn #(Integer/parseInt %)
    :validate [#(< 0 0x10000) "Must be between 0 and 65536"]]
   ["-v" nil "Verbosity Level"
    :id :verbosity
    :default 0
    :update-fn inc]
   ["-h" "--help"]])

(defn -main [& args]
  (parse-opts args cli-options)
  )
