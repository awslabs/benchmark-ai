;;  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
;;
;;  Licensed under the Apache License, Version 2.0 (the "License").
;;  You may not use this file except in compliance with the License.
;;  A copy of the License is located at
;;
;;      http://www.apache.org/licenses/LICENSE-2.0
;;
;;  or in the "license" file accompanying this file. This file is distributed
;;  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
;;  express or implied. See the License for the specific language governing
;;  permissions and limitations under the License.
(ns bai-bff.utils.parsers
  "Provides string->numeric parsers which ensure the string has the
   right format to extract integers, longs and floats. All parsers
   return either the proper type or nil and unparsable"
  (:require [clj-cron-parse.core :refer [next-date]]
            [clj-time.core :as t]))

(defn parse-int [potential-int]
  (when-let [str-int (re-find #"^\d+$" (str potential-int))]
    (Integer/parseInt str-int)))

(defn parse-long [potential-long]
  (when-let [str-long (re-find #"^\d+$" (str potential-long))]
    (Long/parseLong str-long)))

(defn parse-float [potential-float]
  (when-let [str-float (re-find #"^\d+.\d*$" (str potential-float))]
    (Float/parseFloat str-float)))

(defn parse-long-from-urn [urn]
  (when-let [str-id (re-find #"\d+$" urn)]
    (parse-long str-id)))

(defn valid-crontab?
  "validates traditional crontab strings to make sure they are legal.
  Interestingly enough the crontab string supported here has 6 fields
  instead of the usual 5.  The first field being the seconds.  The
  crontab string we support in this project has the usual 5 fields, so
  here we prepend the * for the seconds. Returns boolean true if valid
  or false if invalid. Passing nil will return false.
  (see:
  https://support.acquia.com/hc/en-us/articles/360004224494-Cron-time-string-format)"
  [crontab-string]
  (let [now (t/now)]
    (some? (next-date now (str "* " crontab-string)))))
