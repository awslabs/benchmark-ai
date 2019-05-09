(ns bai-client.utils)

;; Resources...
;; (format "Smile! %c" (int 0x1F64C))
;; (format "Smile! %c" (int 128516))
;; (format "Smile! %s" (apply str (Character/toChars 128516)))
;; https://emojipedia.org/
;; https://www.quackit.com/character_sets/emoji/emoji_v3.0/unicode_emoji_v3.0_characters_smileys_and_people.cfm
;; https://stackoverflow.com/questions/23902953/using-emoji-literals-in-clojure-source

(def smile (apply str (Character/toChars 129315)))

(def starting (apply str (Character/toChars 129315)))
(def okay     (apply str (Character/toChars 0x2705)))
(def fail     (apply str (Character/toChars 0x1F4A3)))
(def error    (apply str (Character/toChars 0x1F525)))
(def warning  (apply str (Character/toChars 0x1F525)))

;; BFF
(def connected    (apply str (Character/toChars 129315)))
(def disconnected (apply str (Character/toChars 129315)))
(def submitted    (apply str (Character/toChars 129315)))
(def received     (apply str (Character/toChars 129315)))
(def rejected     (apply str (Character/toChars 0x274C)))
(def action-id    (apply str (Character/toChars 129315)))

;; Fetcher
(def got_info    (apply str (Character/toChars 0x1F44D)))
(def fetching    (apply str (Character/toChars 0x1F436)))
(def downloading (apply str (Character/toChars 129315)))
(def completed   (apply str (Character/toChars 0x1F44D)))

;; Executor
(def executing   (apply str (Character/toChars 129315)))
(def in-progress (apply str (Character/toChars 0x1F3C3)))
(def exec-done   (apply str (Character/toChars 0x2705)))

(defn unicode-to-string
  "Turns a hex unicode symbol into a string.
  Deals with such long numbers as 0x1F535 for example."
  [code]
  (-> code Character/toChars String.))
