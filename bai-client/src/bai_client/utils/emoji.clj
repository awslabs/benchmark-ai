(ns bai-client.utils.emoji)

;; Resources...
;; (format "Smile! %c" (int 0x1F64C))
;; (format "Smile! %c" (int 128516))
;; (format "Smile! %s" (apply str (Character/toChars 128516)))
;; https://emojipedia.org/
;; https://www.quackit.com/character_sets/emoji/emoji_v3.0/unicode_emoji_v3.0_characters_smileys_and_people.cfm
;; https://stackoverflow.com/questions/23902953/using-emoji-literals-in-clojure-source

(def smile (apply str (Character/toChars 129315)))

(def emoji-starting (apply str (Character/toChars 129315)))
(def emoji-okay     (apply str (Character/toChars 0x2705)))
(def emoji-fail     (apply str (Character/toChars 0x1F4A3)))
(def emoji-error    (apply str (Character/toChars 0x1F525)))
(def emoji-warning  (apply str (Character/toChars 0x1F525)))

;; BFF
(def emoji-connected    (apply str (Character/toChars 129315)))
(def emoji-disconnected (apply str (Character/toChars 129315)))
(def emoji-submitted    (apply str (Character/toChars 129315)))
(def emoji-received     (apply str (Character/toChars 129315)))
(def emoji-rejected     (apply str (Character/toChars 0x274C)))
(def emoji-action-id    (apply str (Character/toChars 129315)))

;; Fetcher
(def emoji-got-info    (apply str (Character/toChars 0x1F44D)))
(def emoji-fetching    (apply str (Character/toChars 0x1F436)))
(def emoji-downloading (apply str (Character/toChars 129315)))
(def emoji-completed   (apply str (Character/toChars 0x1F44D)))

;; Executor
(def emoji-executing   (apply str (Character/toChars 129315)))
(def emoji-in-progress (apply str (Character/toChars 0x1F3C3)))
(def emoji-exec-done   (apply str (Character/toChars 0x2705)))

(defn unicode-to-string
  "Turns a hex unicode symbol into a string.
  Deals with such long numbers as 0x1F535 for example."
  [code]
  (-> code Character/toChars String.))
