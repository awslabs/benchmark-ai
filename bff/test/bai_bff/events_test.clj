(ns bai-bff.core-test
  (:require [clojure.test :refer :all]
            [bai-bff.core :refer :all]))

(def request-body {:ssl-client-cert nil,
                   :protocol "HTTP/1.1",
                   :remote-addr "0:0:0:0:0:0:0:1",
                   :params {},
                   :route-params {},
                   :headers
                   {"user-agent" "curl/7.54.0",
                    "host" "localhost:8080",
                    "accept" "*/*",
                    "content-length" "1548",
                    "expect" "100-continue"},
                   :server-port 8080,
                   :content-length 1548,
                   :compojure/route [:post "/descriptor"],
                   :content-type nil,
                   :path-info "/descriptor",
                   :character-encoding nil,
                   :context "/api/job",
                   :uri "/api/job/descriptor",
                   :server-name "localhost",
                   :query-string nil,
                   :body "stream",
                   :scheme :http,
                   :request-method :post})

(def example-body {:message_id "F11BE378-95F1-4FAE-87AC-A4709C29E6FB",
                   :client_id "3304008612b1e138830bb11e11ff0ad34ff58e0b",
                   :client_version "0.1.0-481dad2",
                   :client_sha1 "3613f13cd102769c24623ab55bf4ba80ccd08961",
                   :client_username "cue",
                   :date "Fri Apr 19 19:33:28 UTC 2019",
                   :visited
                   [{:svc "baictl-client",
                     :tstamp "@@TSTAMP@@",
                     :version "0.1.0-481dad2"}],
                   :payload
                   {:toml
                    {:descriptor_filename "example_descriptor.toml",
                     :sha1 "fd3e9c0450e55f1cb3cf382a1ae53cb717c1420c",
                     :doc
                     "IyBCZW5jaG1hcmtBSSBtZXRhCnNwZWNfdmVyc2lvbiA9ICIwLjEuMCIKCiMgVGhlc2UgZmllbGRzIGRvbid0IGhhdmUgYW55IGltcGFjdCBvbiB0aGUgam9iIHRvIHJ1biwgdGhleSBjb250YWluCiMgbWVyZWx5IGluZm9ybWF0aXZlIGRhdGEgc28gdGhlIGJlbmNobWFyayBjYW4gYmUgY2F0ZWdvcml6ZWQgd2hlbiBkaXNwbGF5ZWQKIyBpbiB0aGUgZGFzaGJvYXJkLgpbaW5mb10KdGFza19uYW1lID0gIkhlbGxvIHdvcmxkIgpkZXNjcmlwdGlvbiA9ICIiIiBcCiAgICBBIGhlbGxvIHdvcmxkIGV4YW1wbGUgb2YgdXNpbmcgQmVuY2htYXJrIEFJXAogICAgIiIiCgojIDEuIEhhcmR3YXJlCltoYXJkd2FyZV0KaW5zdGFuY2VfdHlwZSA9ICJ0My5zbWFsbCIKc3RyYXRlZ3kgPSAic2luZ2xlX25vZGUiCgojIDIuIEVudmlyb25tZW50CltlbnZdCiMgRG9ja2VyIGh1YiA8aHViLXVzZXI+LzxyZXBvLW5hbWU+Ojx0YWc+IApkb2NrZXJfaW1hZ2UgPSAiZWRpc29uZ3VzdGF2by9iYWktYmVuY2htYXJrcy1oZWxsby13b3JsZDpsYXRlc3QiCgojIDMuIE1hY2hpbmUgbGVhcm5pbmcgcmVsYXRlZCBzZXR0aW5nczogCiMgZGF0YXNldCwgYmVuY2htYXJrIGNvZGUgYW5kIHBhcmFtZXRlcnMgaXQgdGFrZXMKW21sXQpiZW5jaG1hcmtfY29kZSA9ICJweXRob24zIGhlbGxvLXdvcmxkLnB5IgoKIyA0LiBPdXRwdXQKW291dHB1dF0KIyBEZWZpbmUgd2hpY2ggbWV0cmljcyB3aWxsIGJlIHRyYWNrZWQgaW4gdGhpcyBiZW5jaG1hcmsKbWV0cmljcyA9IFsidGhyb3VnaHB1dCIsICJ0aW1lIl0K"}}})

(defn uuid [] (str (java.util.UUID/randomUUID)))
(defn time-millis [] (System/currentTimeMillis))

(def status-event {
                   :message_id (uuid)
                   :client_id  "062fa85c-06fa-43ae-9ccf-e2aa6dd22562-"
                   :action_id  "b3e3be6e-c6da-487c-9ba9-f500c255ec7c"
                   :date (time-millis)
                   :visited [{:svc "baictl", :tstamp "1554901873677", :version "v0.1.0-481dad1"}],
                   :payload {
                             :message "some string of status"
                             },
                   })

(def status-event2 {
                    :message_id (uuid)
                    :client_id  "062fa85c-06fa-43ae-9ccf-e2aa6dd22562"
                    :action_id  "b3e3be6e-c6da-487c-9ba9-f500c255ec7c"
                    :date (time-millis)
                    :visited [{:svc "baictl", :tstamp "1554901873677", :version "v0.1.0-481dad1"}],
                    :payload {
                              :message "some string of status, son"
                              },
                    })

(def status-event-bad {
                       :message_id (uuid)
                       :action_id  "b3e3be6e-c6da-487c-9ba9-f500c255ec7c"
                       :date (time-millis)
                       :visited [{:svc "baictl", :tstamp "1554901873677", :version "v0.1.0-481dad1"}],
                       :payload {
                                 :message "some string of status, son"
                                 },
                       })

(def store-entry {
                  :client_id "062fa85c-06fa-43ae-9ccf-e2aa6dd22562"
                  :action_id  "b3e3be6e-c6da-487c-9ba9-f500c255ec7c"
                  :status [{
                            :message_id (uuid)
                            :client_id  "062fa85c-06fa-43ae-9ccf-e2aa6dd22562"
                            :action_id  "b3e3be6e-c6da-487c-9ba9-f500c255ec7c"
                            :date (time-millis)
                            :visited [{:svc "baictl", :tstamp "1554901873677", :version "v0.1.0-481dad1"}],
                            :payload {
                                      :message "some string of status"
                                      },
                            },
                           {
                            :message_id (uuid)
                            :client_id "062fa85c-06fa-43ae-9ccf-e2aa6dd22562"
                            :action_id  "b3e3be6e-c6da-487c-9ba9-f500c255ec7c"
                            :date (time-millis)
                            :visited [{:svc "baictl", :tstamp "1554901873677", :version "v0.1.0-481dad1"}],
                            :payload {
                                      :message "some string of status, son"
                                      },
                            }
                           ]
                  })

(defn store-status [store event]
  (let [{:keys [client_id action_id]} event]
    (if (not-any? nil? '(client_id action_id))
      (assoc-in store (mapv keyword [client_id action_id]) (into [] (remove nil? (conj [] (some-> store (get (keyword client_id)) (get (keyword action_id))) event))))
      store)))

(defn update-status-store [store event]
  (if (nil? event)
    store
    (let [{:keys [client_id action_id]} event
          [client-key action-key] (mapv keyword [client_id action_id])]
      (if (every? identity '(client-key action-key))
        (try
          (assoc-in store [client-key action-key] (into [] (flatten (remove nil? (conj [] (some-> store client-key action-key) event)))))
          (catch NullPointerException e
            (.getMessage e)
            store))
        store))))




(deftest a-test
  (testing "FIXME, I fail."
    (is (not= 0 1))))
