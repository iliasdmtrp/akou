---
description: Δείχνει/αλλάζει τις ρυθμίσεις του akou (config.json)
argument-hint: "[π.χ. key=f8 tts_voice=el-GR-NestorasNeural speak_responses=false]"
allowed-tools: Bash, Read, Edit
---

Διαχειρίσου το `config.json` του akou (`${CLAUDE_PLUGIN_ROOT}/scripts/config.json`).

- Χωρίς όρισμα: δείξε τις τρέχουσες ρυθμίσεις σε πίνακα με σύντομη εξήγηση.
- Με `κλειδί=τιμή`: ενημέρωσε ΜΟΝΟ αυτά, κράτα έγκυρο JSON.

Πεδία:
- `key` : πλήκτρο (π.χ. "f9")
- `mode` : "ptt" (κράτα) / "toggle"
- `language` : "el" / άλλος κωδικός / "auto"
- `model` : "whisper-large-v3" (ακρίβεια) / "whisper-large-v3-turbo" (ταχύτητα)
- `speak_responses` : true/false — εκφώνηση απαντήσεων
- `auto_submit` : true/false — αυτόματο Enter μετά την υπαγόρευση
- `tts_voice` : "el-GR-AthinaNeural" / "el-GR-NestorasNeural"
- `tts_max_chars` : μέγιστοι χαρακτήρες εκφώνησης
- `beep`, `auto_paste`, `lead_trim_sec`, `tail_wait_sec`

Τα `language`/`model`/`speak_responses`/`tts_voice`/`auto_paste` ισχύουν ανά χρήση·
τα `key`/`mode`/`auto_submit`/`beep`/χρόνοι θέλουν επανεκκίνηση του listener.
