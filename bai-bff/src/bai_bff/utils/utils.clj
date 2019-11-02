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
