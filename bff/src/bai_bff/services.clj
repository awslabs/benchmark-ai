(ns bai-bff.services
  (:refer-clojure :exclude [name send]))

(defprotocol RunService
  (start! [this])
  (stop!  [this]))

(defprotocol Sink   (send! [_ message]))
;(defprotocol Source (read! [_ message])) ; <-- das lieben is kein ponyhof
