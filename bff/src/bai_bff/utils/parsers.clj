(ns bai-bff.utils.parsers
  "Provides string->numeric parsers which ensure the string has the
   right format to extract integers, longs and floats. All parsers
   return either the proper type or nil and unparsable")

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
