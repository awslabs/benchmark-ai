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

(deftest a-test
  (testing "FIXME, I fail."
    (is (= 0 1))))
