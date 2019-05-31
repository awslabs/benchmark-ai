(ns bai-bff.utils.utils
  (:require [clojure.set :refer [difference]]
            [environ.core :refer [env]]))

(defn assert-configured! [required-keys]
  (let [missing (difference required-keys (set(keys env)))]
    (when (seq missing)
      (throw (AssertionError. (str "Configuration missing:" missing))))))
