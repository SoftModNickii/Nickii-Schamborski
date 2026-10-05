#!/bin/bash
# Oeffnet das Aufgabenheft im Browser. Geht per Doppelklick und wird
# taeglich um 10 Uhr ueber ~/Library/LaunchAgents/com.schamborski.aufgabenheft.plist
# gestartet. Das Terminal wird nur gebraucht, weil nur es auf den Ordner
# Dokumente zugreifen darf. Es startet das Heft im Hintergrund und schliesst sich.
cd "$(dirname "$0")/.." || exit 1
PY=/opt/homebrew/bin/python3
[ -x "$PY" ] || PY=/usr/bin/python3
"$PY" tools/website.py heft --hintergrund
osascript -e 'tell application "Terminal" to close (every window whose name contains "aufgabe.command")' >/dev/null 2>&1 &
exit 0
