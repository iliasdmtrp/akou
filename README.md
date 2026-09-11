# akou 🔊🇬🇷 (άκου)

**Προσβάσιμος φωνητικός βοηθός για τυφλούς** στο [Claude Code](https://claude.com/claude-code).
Πλήρης φωνητικός κύκλος στα ελληνικά: πατάς ένα πλήκτρο, **λες την εντολή**, στέλνεται
αυτόματα, και **η απάντηση του Claude διαβάζεται φωναχτά**. Καμία ανάγκη για οθόνη.

- 🎤 **STT:** Groq / OpenAI Whisper (large-v3) — άριστα ελληνικά
- 🔊 **TTS:** edge-tts — δωρεάν ελληνικές νευρωνικές φωνές (`el-GR-AthinaNeural`, `el-GR-NestorasNeural`)
- ⌨️ Πλήρως hands-free: hotkey → ομιλία → auto-submit → εκφώνηση απάντησης

> Accessible Greek voice assistant for blind users on Claude Code: speak your command,
> it's sent automatically, and Claude's answer is read aloud. Whisper STT + edge-tts.

## Πώς δουλεύει

1. Κρατάς το **F9**, λες την εντολή σου, αφήνεις το F9.
2. Το κείμενο γράφεται στο chat και **στέλνεται αυτόματα** (auto-submit).
3. Μόλις απαντήσει το Claude, ένα **Stop hook** διαβάζει την απάντηση **φωναχτά**.

Ηχητικές ενδείξεις (μπιπ) δείχνουν πότε ηχογραφεί, αφού δεν χρειάζεται οθόνη.

## Εγκατάσταση

```bash
git clone https://github.com/iliasdmtrp/akou.git
pip install -r akou/akou/requirements.txt
```

Κλειδί στο `.env` (δωρεάν Groq — **BYOK**, βάζεις το δικό σου):
```
GROQ_API_KEY=gsk_...
```
Δωρεάν κλειδί: https://console.groq.com/keys (σύνδεση, Create API Key, αντιγραφή).

Ως Claude Code plugin (interactive `claude`) — **χρειάζεται για να δουλέψει ο Stop hook**:
```
/plugin marketplace add ./akou
/plugin install akou@akou
```
Μετά την εγκατάσταση, **επανεκκίνησε** τη συνεδρία ώστε να φορτωθεί ο hook.

## Εντολές

| Εντολή | Τι κάνει |
|---|---|
| `/akou` | ξεκινά τον φωνητικό βοηθό (F9 → μιλάς → στέλνεται → ακούς) |
| `/akou-stop` | σταματά τον listener |
| `/akou-config` | ρυθμίσεις (πλήκτρο, φωνή, γλώσσα, μοντέλο…) |

Ή απευθείας: `python akou/akou/scripts/listener.py`

## Ρυθμίσεις (`akou/scripts/config.json`)

Προεπιλογές: `speak_responses: true`, `auto_submit: true` (πλήρως hands-free).
Άλλαξε φωνή με `tts_voice`, πλήκτρο με `key`, γλώσσα με `language` (ή `auto`).

## Σημειώσεις

- Windows. Το auto-start (Startup folder, χωρίς admin): `scripts/autostart.ps1 install`.
- Ο listener είναι τοπικός — δεν καταναλώνει Claude credits από μόνος του· το Groq (free)
  χρεώνεται μόνο ανά εκφώνηση, το edge-tts είναι δωρεάν.
- Αν το global hotkey δεν πιάνει, τρέξε ως administrator.

## Άδεια

MIT
