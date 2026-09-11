"""
listener.py — Global hotkey φωνητικής υπαγόρευσης (akou plugin, για τυφλούς).

Τρέχει στο παρασκήνιο, γράφει ΜΕΣΑ στο ενεργό πλαίσιο και (με auto_submit) το στέλνει.
Η απάντηση διαβάζεται φωναχτά από το speak_response.py (Stop hook).

    F9  = κράτα για ομιλία (ptt) ή πάτα/ξαναπάτα (toggle)
    Esc = έξοδος

Backend: GROQ_API_KEY / OPENAI_API_KEY (βλ. core.py). Ρυθμίσεις: config.json.
"""
import argparse
import os
import sys
import tempfile
import threading
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # για import dictate

import keyboard
import pyperclip
import core as dictate  # ο πυρήνας του akou (STT/config/vocab)


_beep_enabled = True
_auto_paste = True
_auto_submit = True


def _beep(*tones):
    """Ηχητική ένδειξη κατάστασης (μη μπλοκάρει). tones = [(freq, ms), ...]."""
    if not _beep_enabled:
        return
    def run():
        try:
            import winsound
            for freq, ms in tones:
                winsound.Beep(freq, ms)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


_recording = False
_frames = []
_stream = None
_lock = threading.Lock()


LEAD_TRIM_SEC = 0.18   # πετάμε την αρχή (ήχος μπιπ / πλήκτρου) — δεν καθυστερεί την έναρξη
TAIL_WAIT_SEC = 0.25   # μικρή ουρά για να μην κοπεί η τελευταία λέξη


def _start():
    global _recording, _frames, _stream
    import sounddevice as sd

    _frames = []

    def cb(indata, frames, t, status):
        _frames.append(indata.copy())

    # Άνοιξε το μικρόφωνο ΑΜΕΣΩΣ (μηδενική καθυστέρηση)...
    _stream = sd.InputStream(samplerate=dictate.SAMPLE_RATE,
                             channels=dictate.CHANNELS, dtype="int16",
                             callback=cb)
    _stream.start()
    _recording = True
    _beep((1100, 70))  # ...και το μπιπ παίζει παράλληλα (θα κοπεί από το LEAD_TRIM)
    print("🔴 Ηχογράφηση...", flush=True)


def _stop_and_type():
    global _recording, _stream
    time.sleep(TAIL_WAIT_SEC)  # πιάσε και την τελευταία λέξη πριν κλείσει το μικρόφωνο
    _stream.stop()
    _stream.close()
    _recording = False
    _beep((587, 140))  # ▼ ένα χαμηλό μπιπ = ΣΤΑΜΑΤΗΣΕ / μεταγράφει
    pcm = b"".join(f.tobytes() for f in _frames)
    trim = int(dictate.SAMPLE_RATE * LEAD_TRIM_SEC) * 2  # bytes (int16 mono)
    pcm = pcm[trim:]  # πέτα την αρχή με τον ήχο του μπιπ
    if not pcm:
        print("(κενό)", flush=True)
        return
    print("⏳ Μεταγραφή...", flush=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = tmp.name
    try:
        dictate.save_wav(pcm, wav)
        text = dictate.transcribe(wav)
    finally:
        try:
            os.remove(wav)
        except OSError:
            pass
    if not text:
        print("(δεν αναγνωρίστηκε ομιλία)", flush=True)
        return
    print("📝 " + text, flush=True)
    prev = None
    try:
        prev = pyperclip.paste()
    except Exception:
        pass
    pyperclip.copy(text)
    if not _auto_paste:
        _beep((1319, 90))
        print("📋 Στο clipboard (auto_paste=false) — Ctrl+V όπου θες.", flush=True)
        return  # μην κάνεις paste, μην επαναφέρεις το clipboard
    time.sleep(0.05)
    keyboard.send("ctrl+v")
    _beep((1319, 90))  # ✓ σύντομο μπιπ = γράφτηκε το κείμενο
    time.sleep(0.15)
    if _auto_submit:
        keyboard.send("enter")  # hands-free: στείλε το μήνυμα
    if prev is not None:
        try:
            pyperclip.copy(prev)
        except Exception:
            pass


def _announce(text, voice):
    """Εκφωνεί ένα σύντομο μήνυμα (π.χ. χαιρετισμό εκκίνησης) μέσω edge-tts."""
    try:
        import asyncio, os, tempfile
        import speak_response as sr
        out = os.path.join(tempfile.gettempdir(), "akou_announce.mp3")
        asyncio.run(sr._tts(text, voice, out))
        sr._play_mp3(out)
        try:
            os.remove(out)
        except OSError:
            pass
    except Exception as e:
        print(f"announce error: {e}", file=sys.stderr)


def _toggle():
    with _lock:
        _start() if not _recording else _stop_and_type()


def _ptt_press():
    # Το κράτημα πλήκτρου στέλνει επαναλαμβανόμενα press· ξεκίνα μόνο την 1η φορά.
    with _lock:
        if not _recording:
            _start()


def _ptt_release():
    with _lock:
        if _recording:
            _stop_and_type()


def main():
    global _beep_enabled, _auto_paste, _auto_submit, LEAD_TRIM_SEC, TAIL_WAIT_SEC
    cfg = dictate.load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=None, help="hotkey (υπερισχύει του config)")
    ap.add_argument("--mode", choices=["ptt", "toggle"], default=None,
                    help="ptt = κράτα για ομιλία · toggle = πάτα/ξαναπάτα")
    args = ap.parse_args()

    key = args.key or cfg.get("key", "f9")
    mode = args.mode or cfg.get("mode", "ptt")
    _beep_enabled = bool(cfg.get("beep", True))
    _auto_paste = bool(cfg.get("auto_paste", True))
    _auto_submit = bool(cfg.get("auto_submit", True))
    LEAD_TRIM_SEC = float(cfg.get("lead_trim_sec", LEAD_TRIM_SEC))
    TAIL_WAIT_SEC = float(cfg.get("tail_wait_sec", TAIL_WAIT_SEC))

    dictate._load_env()
    if not (os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        sys.exit("❌ Λείπει GROQ_API_KEY/OPENAI_API_KEY στο .env")

    if mode == "ptt":
        keyboard.on_press_key(key, lambda e: _ptt_press())
        keyboard.on_release_key(key, lambda e: _ptt_release())
        how = f"ΚΡΑΤΑ {key.upper()} όσο μιλάς, άφησέ το για μεταγραφή"
    else:
        keyboard.add_hotkey(key, _toggle)
        how = f"πάτα {key.upper()} για έναρξη/τερματισμό"
    lang = cfg.get("language", "el")
    print(f"🎙️  Έτοιμο [{mode}, γλώσσα={lang}]. Κέρσορας στο chat, {how}. "
          f"(Esc για έξοδο.)", flush=True)

    # Φωνητικός χαιρετισμός εκκίνησης — ώστε ένας τυφλός χρήστης να ξέρει ακουστικά
    # ότι το akou είναι έτοιμο.
    if cfg.get("startup_announce", True):
        _announce(cfg.get(
            "startup_message",
            f"Το άκου είναι έτοιμο. Κράτα το πλήκτρο, πες την εντολή σου, "
            f"και θα ακούσεις την απάντηση."
        ), cfg.get("tts_voice", "el-GR-AthinaNeural"))

    keyboard.wait("esc", suppress=False)


if __name__ == "__main__":
    main()
