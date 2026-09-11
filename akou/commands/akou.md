---
description: Ξεκινά το akou — μιλάς την εντολή, στέλνεται, και ακούς την απάντηση
argument-hint: "[πλήκτρο, π.χ. f8]"
allowed-tools: Bash
---

Ξεκίνα το akou (προσβάσιμη φωνητική λειτουργία) ΣΤΟ ΠΑΡΑΣΚΗΝΙΟ.

Βήματα:
1. Εγκατάστησε εξαρτήσεις μία φορά (αθόρυβα):
   `python -m pip install --quiet -r "${CLAUDE_PLUGIN_ROOT}/requirements.txt"`
2. Ξεκίνα τον listener στο παρασκήνιο (run_in_background), από τον φάκελο του project
   ώστε να διαβάσει το `.env` με το GROQ_API_KEY:
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/listener.py" --key "${ARGUMENTS:-f9}"`
3. Περίμενε ~2s και διάβασε το output για να επιβεβαιώσεις «Έτοιμο» (ή σφάλμα:
   λείπει κλειδί / χρειάζεται admin για το hotkey).
4. Πες στον χρήστη με ΑΠΛΑ λόγια: «Κράτα [πλήκτρο], πες την εντολή, άσε το πλήκτρο.
   Θα σταλεί μόνο του και θα ακούσεις την απάντηση.»

Η εκφώνηση της απάντησης γίνεται από το Stop hook (speak_response.py), που φορτώνεται
όταν το plugin είναι εγκατεστημένο στο Claude Code. Αν λείπει κλειδί, πες να βάλει
`GROQ_API_KEY=gsk_...` στο `.env` (δωρεάν: https://console.groq.com/keys).
