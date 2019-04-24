(ns bai-bff.services.configuration
  (:require [bai-bff.services :refer [RunService]]
            [clojure.pprint :refer :all]
            [clojure.java.io :as io]
            [clojure.set :refer [difference]]
            [taoensso.timbre :as log]))

(defn- get-env-config
  "Load a map of paramters from the environment keys are lowercased,
   substitute '_' with '-' and converted to keywords."
  []
  (->> (System/getenv)
       (map (fn [[env-key env-value]]
              (when-let [key (some-> env-key
                                     (clojure.string/lower-case)
                                     (clojure.string/replace "_" "-")
                                     (keyword))]
                {key env-value})))
       (filter (complement nil?))
       (apply merge)))

(defprotocol IAssertConfigured
  (assert-configured! [_ key-set]))

(deftype Configuration [overrides config started?]
  RunService
  (start! [_]
    (when-not @started?
      (let [env-config  (get-env-config)
            merged-config (merge-with merge
                                      env-config
                                      overrides)]
        (log/info "Configuring from overrides:" overrides)
        (reset! config merged-config)
        (reset! started? true))))
  (stop! [_]
    (when @started?
      (reset! started? false)))
  IAssertConfigured
  (assert-configured! [_ required-keys]
    (let [missing (difference required-keys
                              (into #{} (filter #(not (empty? (str (@config %))))
                                                (keys @config))))]
      (when-not (empty? missing)
        (throw (AssertionError. (str "Configuration missing:" missing))))))
  clojure.lang.ILookup
  (valAt [_ k]
    (if @started?
      (get @config k)
      (throw (IllegalStateException. "config not started"))))
  (valAt [_ k not-found]
    (if @started?
      (get @config k not-found)
      (throw (IllegalStateException. "config not started"))))
  clojure.lang.ISeq
  (next [_]
    (if @started?
      (next @config)
      (throw (IllegalStateException. "config not started"))))
  (first [_]
    (if @started?
      (first @config)
      (throw (IllegalStateException. "config not started"))))
  (cons [_ obj]
    (if @started?
      (swap! config cons obj)
      (throw (IllegalStateException. "config not started"))))
  (more [this] (if-let [n (next this)] n '()))
  (count [_]
    (if @started?
      (count @config)
      (throw (IllegalStateException. "config not started"))))
  (empty [_] (Configuration. {}
                             (atom {})
                             (atom false)))
  (equiv [_ obj] (= @config obj))
  clojure.lang.Seqable
  (seq [this] this)
  Object
  (toString [_] (str @config))
  (equals [this that]
    (= (.hashCode this)
       (.hashCode that)))
  (hashCode [_]
    (.hashCode @config)))

(defmethod clojure.core/print-method Configuration
  [config writer]
  (let [output (str config)]
    (.write writer output 0 (count output))))

(defn create-configuration-service
  ([] (create-configuration-service {}))
  ([overrides]
   (Configuration. overrides
                   (atom {})
                   (atom false))))
