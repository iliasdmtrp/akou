"""
dictate.py — Ελληνικό speech-to-text (πυρήνας του greek-voice plugin).

Ηχογράφηση μικροφώνου -> Whisper (Groq/OpenAI) -> κείμενο.
Χρησιμοποιείται είτε αυτόνομα είτε από το voice_hotkey.py.

Κλειδί από .env (cwd ή δίπλα στο script) ή environment:
    GROQ_API_KEY    -> Groq whisper-large-v3-turbo  (ΔΩΡΕΑΝ, γρήγορο, άριστα ελληνικά)
    OPENAI_API_KEY  -> OpenAI whisper-1
Δωρεάν Groq key: https://console.groq.com/keys
"""
import argparse
import json
import os
import queue
import re
import sys
import tempfile
import threading
import wave

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
LANG = "el"

# «Λεξιλόγιο» που βοηθά το Whisper να κρατά ελληνικά και να πιάνει σωστά τους όρους.
# Άλλαξέ το ελεύθερα ή όρισε PROMPT μέσω μεταβλητής περιβάλλοντος WHISPER_PROMPT.
PROMPT = (
    "Ελληνική υπαγόρευση για χρηματιστηριακό agent. Όροι: μετοχή, μετοχές, αγόρασε, "
    "πούλησε, θέση, χαρτοφυλάκιο, απόδοση, ποσοστό, τοις εκατό, ευρώ, δολάρια, "
    "stop-loss, take-profit, bracket, ticker, Trading212, StockAgent, "
    "AAPL, NVDA, TSLA, MSFT, SSRM, TTMI."
)


DEFAULT_CONFIG = {
    "key": "f9",
    "mode": "ptt",
    "language": "el",      # "auto" = αυτόματη ανίχνευση γλώσσας
    "model": "whisper-large-v3",
    "beep": True,
    "auto_paste": True,
    "auto_submit": True,        # μετά το paste πάτα Enter (hands-free) — προεπιλογή ON για akou
    "speak_responses": True,    # διάβασε φωναχτά τις απαντήσεις (Stop hook) — ON για akou
    "tts_voice": "el-GR-AthinaNeural",
    "tts_max_chars": 1200,
    "lead_trim_sec": 0.18,
    "tail_wait_sec": 0.25,
}


def load_config():
    """Διαβάζει config.json (δίπλα στο script ή στο cwd) πάνω από τα defaults."""
    cfg = dict(DEFAULT_CONFIG)
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(here, "config.json"), os.path.join(os.getcwd(), "config.json")):
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    cfg.update(json.load(f))
            except Exception as e:
                print(f"⚠️  Πρόβλημα στο config.json: {e}", file=sys.stderr)
            break
    return cfg


def _load_env():
    """Φορτώνει KEY=VALUE από .env: πρώτα cwd, μετά δίπλα στο script."""
    here = os.path.dirname(os.path.abspath(__file__))
    for env_path in (os.path.join(os.getcwd(), ".env"), os.path.join(here, ".env")):
        if not os.path.exists(env_path):
            continue
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def record_until_enter():
    q = queue.Queue()
    stop = threading.Event()

    def cb(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    print("🔴 Ηχογράφηση... μίλα τώρα. Πάτα Enter για τερματισμό.")
    frames = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                        dtype="int16", callback=cb):
        threading.Thread(target=lambda: (input(), stop.set()), daemon=True).start()
        while not stop.is_set():
            try:
                frames.append(q.get(timeout=0.1))
            except queue.Empty:
                pass
    return b"".join(f.tobytes() for f in frames)


def record_fixed(seconds):
    print(f"🔴 Ηχογράφηση {seconds}s... μίλα τώρα.")
    audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=CHANNELS, dtype="int16")
    sd.wait()
    return audio.tobytes()


def save_wav(pcm_bytes, path):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_bytes)


# Γνωστά «παραμιλητά» του Whisper πάνω σε σιωπή (credits υποτίτλων κ.λπ.)
_HALLUCINATIONS = re.compile(
    r"(υπότιτλοι[^\n.]*|υποτιτλισμός[^\n.]*|authorwave|amara\.org|"
    r"subtitles by[^\n.]*|thanks for watching[^\n.]*|"
    r"επιμέλεια[^\n.]*|μετάφραση[^\n.]*υπότιτλ[^\n.]*)",
    re.IGNORECASE,
)


def _load_vocab():
    """Διαβάζει vocab.txt (δίπλα στο script ή στο cwd).
    Επιστρέφει (extra_prompt_terms:list, corrections:list[(wrong,right)])."""
    here = os.path.dirname(os.path.abspath(__file__))
    terms, corr = [], []
    for path in (os.path.join(here, "vocab.txt"), os.path.join(os.getcwd(), "vocab.txt")):
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=>" in line:
                    w, r = line.split("=>", 1)
                    w, r = w.strip(), r.strip()
                    if w:
                        corr.append((w, r))
                else:
                    terms.append(line)
        break  # χρησιμοποίησε το πρώτο που θα βρεις
    return terms, corr


def _apply_corrections(text, corrections):
    for wrong, right in corrections:
        text = re.sub(r"\b" + re.escape(wrong) + r"\b", right, text,
                      flags=re.IGNORECASE)
    return text


def _dedupe(text):
    """Κόβει επαναλήψεις που βάζει το Whisper (κολλημένες ή με κενό)."""
    # 1) πλήρης διπλασιασμός ολόκληρου του string: "ΑΒΓΑΒΓ" -> "ΑΒΓ"
    for _ in range(4):
        n = len(text)
        if n >= 6 and n % 2 == 0 and text[: n // 2] == text[n // 2:]:
            text = text[: n // 2]
        else:
            break
    # 2) επαναλαμβανόμενη ίδια λέξη στη σειρά: "τεστ τεστ τεστ" -> "τεστ"
    text = re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", text, flags=re.IGNORECASE)
    return text


def _clean(text, corrections=None):
    """Αφαιρεί artifacts, επαναλήψεις και εφαρμόζει διορθώσεις λεξιλογίου."""
    text = _HALLUCINATIONS.sub("", text)
    text = _dedupe(text.strip())
    if corrections:
        text = _apply_corrections(text, corrections)
    text = re.sub(r"\s{2,}", " ", text).strip(" .·-\n\t")
    return text


def transcribe(wav_path, cfg=None):
    cfg = cfg or load_config()
    groq = os.environ.get("GROQ_API_KEY")
    openai = os.environ.get("OPENAI_API_KEY")
    if groq:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        # config.model (default large-v3)· env WHISPER_MODEL υπερισχύει.
        model = os.environ.get("WHISPER_MODEL", cfg.get("model", "whisper-large-v3"))
        key = groq
    elif openai:
        url = "https://api.openai.com/v1/audio/transcriptions"
        model, key = "whisper-1", openai
    else:
        sys.exit(
            "❌ Δεν βρέθηκε κλειδί. Πάρε ΔΩΡΕΑΝ Groq key από "
            "https://console.groq.com/keys και βάλ' το στο .env:\n"
            "   GROQ_API_KEY=gsk_...."
        )
    lang = cfg.get("language", LANG)
    extra_terms, corrections = _load_vocab()
    # Το ελληνικό PROMPT μόνο όταν γλώσσα = ελληνικά· αλλιώς μόνο οι όροι λεξιλογίου.
    prompt = (os.environ.get("WHISPER_PROMPT", PROMPT) if lang == "el" else "")
    if extra_terms:
        joiner = " " if not prompt else " Επιπλέον όροι: "
        prompt = (prompt + joiner + ", ".join(extra_terms) + ".")[:900]
    data = {"model": model, "temperature": "0", "prompt": prompt}
    if lang and lang != "auto":
        data["language"] = lang  # "auto" -> παράλειψη = αυτόματη ανίχνευση
    with open(wav_path, "rb") as f:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {key}"},
            files={"file": ("audio.wav", f, "audio/wav")},
            data=data,
            timeout=120,
        )
    if r.status_code != 200:
        sys.exit(f"❌ Σφάλμα API ({r.status_code}): {r.text[:300]}")
    return _clean(r.json().get("text", "").strip(), corrections)


def to_clipboard(text):
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False


def main():
    _load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--seconds", type=float, default=None,
                    help="σταθερή διάρκεια ηχογράφησης σε δευτερόλεπτα")
    args = ap.parse_args()

    pcm = record_fixed(args.seconds) if args.seconds else record_until_enter()
    if not pcm:
        sys.exit("❌ Δεν ηχογραφήθηκε ήχος.")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    try:
        save_wav(pcm, wav_path)
        print("⏳ Μεταγραφή...")
        text = transcribe(wav_path)
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass

    if not text:
        print("(κενό — δεν αναγνωρίστηκε ομιλία)")
        return
    print("\n📝 " + text + "\n")
    if to_clipboard(text):
        print("✅ Αντιγράφηκε στο clipboard — Ctrl+V όπου γράφεις.")
    else:
        print("(χειροκίνητη αντιγραφή)")


if __name__ == "__main__":
    main()
