(ns bai-bff.services.eventbus
  "This namespace handles the creation and closing of channels that
  faciliate 'conveyance' of information throughout this system.  We
  continue the use of the 'component' model for the sake of
  consistency as we are indeed managing 'state' of the channels.<p>

  (Note from author: I am aware that this is very very OO code in a
  functional language.  I went down this road when I decided to use a
  Stuart Sierra-esque compoent model for this project.  So anywhere
  there is state I manage it in this way. Oh well.)"
  (:require [bai-bff.core :refer :all]
            [bai-bff.services :refer [RunService]]
            [bai-bff.services.configuration :refer :all]
            [taoensso.timbre :as log]
            [clojure.pprint :refer :all]
            [clojure.core.async :as a :refer [>! <! >!! <!! go chan buffer close! thread
                                              alts! alts!! timeout]]))

(def send-event-channel-atom     (atom nil))  ;;output channel
(def receive-events-channel-atom (atom nil))  ;;input channel

;;TODO add a stop function that closes channels and allows to drain.
(defrecord EventbusService [send-channel receive-channel]
  RunService
  (start! [this]
    (log/info (str "starting eventbus service component..."))
    (reset! send-event-channel-atom send-channel)
    (reset! receive-events-channel-atom receive-channel))
  (stop! [this]
    (locking this
      (log/info (str "stopping eventbus service component... (closing channels)"))
      (a/close! @send-event-channel-atom)
      (a/close! @receive-events-channel-atom)))
  Object
  (toString [_] "<Eventbus>"))

(defmethod print-method EventbusService [v ^java.io.Writer w]
  (.write w "<EventbusService>"))

(defn create-eventbus-service []
  (map->EventbusService {:send-channel    (chan 1000)
                         :receive-channel (chan 1000)}))
