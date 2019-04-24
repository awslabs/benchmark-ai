(ns bai-bff.utils.srv
  (:require [clj-dnssrv.core :as srv]))

(def my-resolver (srv/resolver {:cache-lookups true
                                :lookup-timeout-ms 10000
                                :metered true
                                :retain-data true}))

(defn csv-str-if-srv
  "If the hostname value also has a specified port
  (ex: \"kafka.broker.prod.bia-bff.db.srv.aws.com:9092\" That
  input hostname gets returned back to the caller. If there is no
  port value on the hostname, then we will begin to use it as input to
  a dns srv recored lookup.  The result is a single string that is a
  csv list of the constituent hosts of the srv record"
  [^String hostname]
  (try
    (if-let [[_ host port] (re-find #"([^:]+):([^:]+)" hostname)]
      hostname
      (clojure.string/join "," (map (fn [{:keys [host port]}]
                                      (str (subs host 0 (dec(count host)))":"port))
                                    (srv/lookup my-resolver hostname))))
    (catch Exception ex (.printStackTrace ex) hostname)))
