(ns bai-bff.utils.utils
  (:require [clojure.set :refer [difference]]
            [environ.core :refer [env]]))

(defn assert-configured! [required-keys]
  (let [missing (difference required-keys (set(keys env)))]
    (when (seq missing)
      (throw (AssertionError. (str "Configuration missing:" missing))))))

(defn generate-s3-uri
  "Create the full S3 *URI* for the passed in filename"
  [filename]
  (str "s3://"(env :scripts-exchange-s3-bucket-name)"/anubis0/"filename))

(defn generate-s3-path
  "Create the full S3 path for the passed in filename"
  [filename]
  (str "anubis0/"filename))
