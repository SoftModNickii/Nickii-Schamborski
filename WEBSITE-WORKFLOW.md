# Website pflegen

Kurzanleitung fuer schamborski.com. Alle Befehle von der Repo-Wurzel aus.

## Der Ablauf in vier Schritten

```
python3 tools/website.py needs     # Was fehlt? Legt die Ablageordner an
                                   # -> Fotos in _inbox/<id>/ legen
python3 tools/website.py intake    # Bilder umbenennen, einsortieren, eintragen
python3 tools/website.py check     # Muss "FEHLER (0)" melden
python3 tools/website.py serve     # http://localhost:8000 im Browser pruefen
```

Erst wenn `check` null Fehler meldet und die Vorschau stimmt, wird gepusht.

## Bilder uebergeben

`needs` legt fuer jeden Eintrag ohne Bild einen beschrifteten Ordner unter
`_inbox/` an. Fotos dort hineinlegen, die Dateinamen sind egal. Die Reihenfolge
steuert eine fuehrende Zahl:

```
_inbox/funke-2-2026/1-hero.jpg
_inbox/funke-2-2026/2-detail.jpg
_inbox/funke-2-2026/3-install.jpg
```

`intake` benennt sie in `funke-2-2026-01.jpg` und so weiter um, verschiebt sie
nach `assets/images/funke-2-2026/` und traegt sie in `content.json` ein. Das
erste Bild wird das Titelbild der Kachel. `_inbox/` selbst liegt nicht in Git.

Probelauf ohne Aenderung: `python3 tools/website.py intake --dry-run`

## Was `check` prueft

- Jeder Bild- und PDF-Pfad in `content.json` existiert wirklich.
- Jede Datei ist in Git eingecheckt. Was nur lokal liegt, ist live ein 404.
- Die Gross- und Kleinschreibung stimmt exakt. macOS ist hier nachlaessig,
  der Server von GitHub nicht. `TA-SAIC.JPG` und `ta-saic.jpg` sind live
  zwei verschiedene Dateien.
- Pflichtfelder, doppelte ids, unbekannte Kategorien, leere Kategorien.
- `year` ist sortierbar und passt zu `sort_year`.
- Querverweise in `exhibited_at` und `exhibited_works` zeigen auf echte ids.

FEHLER heisst: auf der Seite sichtbar kaputt. HINWEIS heisst: unvollstaendig,
aber die Seite laeuft.

## Einen Eintrag von Hand anlegen

`content.json` ist eine flache Liste. Ein Eintrag braucht mindestens:

```json
{
  "id": "kurz-und-mit-jahr-2026",
  "title": "Titel",
  "year": "2026",
  "sort_year": 2026,
  "categories": ["works"],
  "type": "Installation",
  "specs": "Material, Masse, Dauer",
  "institution": "Ort oder Haus",
  "link": null,
  "image": null,
  "images": [],
  "related_links": []
}
```

Erlaubte Kategorien: `works`, `shows`, `practice`, `education`, `fellowships`,
`press`. Ein Eintrag ohne Kategorie taucht nur unter "All" auf.

Sortiert wird im Raster nach `year`, nicht nach `sort_year`. Bei Zeitraeumen
`"2026/2027"` schreiben, gewertet wird die erste Jahreszahl.

`description_de` wird nur angezeigt, wenn `categories` auch `works` enthaelt.

Presseeintraege mit `link` und ohne `image` werden als Link-Vorschaukachel mit
Favicon gerendert. Das ist Absicht, kein Fehler.

## Sicherung

Jedes Schreiben sichert den vorherigen Stand nach `data/.backups/`
(zehn Staende, nicht in Git). Zuruecknehmen:

```
cp data/.backups/content-<stempel>.json data/content.json

# oder ganz zurueck auf den letzten Commit:
git checkout data/content.json
```
