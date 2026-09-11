---
description: Σταματά το akou (τον listener φωνής)
allowed-tools: Bash
---

Σταμάτα τον listener του akou.

Εντόπισε το PID και τερμάτισε:
`wmic process where "name='python.exe' and commandline like '%listener.py%'" get processid`
και μετά `taskkill /F /PID <pid>` (ομοίως για `pythonw.exe`).

Αν τον είχες ξεκινήσει ως background task σε αυτή τη συνεδρία, προτίμησε το εργαλείο
διαχείρισης background tasks. Επιβεβαίωσε στον χρήστη ότι σταμάτησε.
