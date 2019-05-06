(ns bai-bff.core
  (:require [clojure.java.io :as io])
  (:import (java.util Properties)))

(defn get-version
  [dep]
  (let [path (str "META-INF/maven/" (or (namespace dep) (name dep))
                  "/" (name dep) "/pom.properties")
        props (io/resource path)]
    (when props
      (with-open [stream (io/input-stream props)]
        (let [props (doto (Properties.) (.load stream))]
          (.getProperty props "version"))))))

(def VERSION
  (or (get-version 'bai-bff) ; for jars
      (System/getProperty "bai-bff.version"))) ;for lein
