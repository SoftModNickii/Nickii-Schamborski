# Website pflegen

Kurzanleitung fuer schamborski.com. Alle Befehle von der Repo-Wurzel aus.

## Der Ablauf in fuenf Schritten

```
python3 tools/website.py needs     # Was fehlt? Legt die Ablageordner an
                                   # -> Fotos in _inbox/<id>/ legen
python3 tools/website.py intake    # Bilder umbenennen, einsortieren, eintragen
python3 tools/website.py build     # Startseite, CV, Werkseiten, Vorschaubilder
python3 tools/website.py check     # Muss "FEHLER (0)" melden
python3 tools/website.py serve     # http://localhost:8000 im Browser pruefen
```

Erst wenn `check` null Fehler meldet und die Vorschau stimmt, wird gepusht.
Neue Dateien aus `build` (Vorschaubilder, Werkseiten) mit `git add` aufnehmen.

## Eine Quelle fuer alles

- `data/content.json`: alle Eintraege. Das Raster liest sie direkt.
- Feld `cv` an einem Eintrag: seine Zeile(n) im CV. `build` schreibt daraus
  `pages/cv.html`. Den CV nie direkt in der HTML-Datei aendern, das
  ueberschreibt der naechste `build`.
- `data/site.json`: Statement und ausgewaehlte Arbeiten der Startseite,
  Vorschaubild fuer soziale Netzwerke, Kontakt.
- `works/<id>.html`: eine Seite je Eintrag mit Kategorie `works`, vollstaendig
  generiert.
- `assets/thumbs/`: Vorschaubilder fuer Raster und Startseite, generiert.
- `data/asset-sources.json`: welche Webfassung aus welchem Original entstand.

In `index.html` und `pages/cv.html` schreibt `build` nur zwischen
`<!-- build:name -->` und `<!-- /build:name -->`. Der Rest bleibt von Hand
pflegbar.

Eine CV-Zeile sieht so aus, `**fett**` wird fett gesetzt:

```json
"cv": [
  {"section": "experience", "order": 30, "date": "2026",
   "lines": ["**Teaching Assistant**, Performance Studies",
             "School of the Art Institute of Chicago, USA"]}
]
```

Abschnitte: `education`, `recognition`, `exhibitions`, `workshops`,
`publishing`, `experience`. `order` bestimmt die Reihenfolge im Abschnitt.

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
- Jeder lokale Verweis in allen HTML- und CSS-Dateien existiert, auch
  Favicons, Vorschaubild und Adressen auf schamborski.com.
- JSON-LD ist gueltiges JSON.
- CV-Zeilen passen zum Jahr ihres Eintrags, Ausbildung und Auszeichnungen
  fehlen nicht im CV.
- Generierte Dateien sind aktuell, sonst: `build` ausfuehren.
- TIFF, PSD und HEIC in Galerien, `[object Object]`, Links auf Bilddateien,
  Titelbild ausserhalb der Galerie, nicht sprechende ids.
- Dateien unter `assets/`, die nirgends verwendet werden
  (einzeln mit `check --details`).
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

Eintraege ohne eigenes Bild werden als typografische Karte gerendert,
Presseeintraege mit `link` zusaetzlich mit Favicon. Das ist Absicht, kein Fehler.

Offene inhaltliche Fragen stehen in `CONTENT-AUDIT.md`.

## Sicherung

Jedes Schreiben sichert den vorherigen Stand nach `data/.backups/`
(zehn Staende, nicht in Git). Zuruecknehmen:

```
cp data/.backups/content-<stempel>.json data/content.json

# oder ganz zurueck auf den letzten Commit:
git checkout data/content.json
```

## Aufgabenheft

Jeden Tag um 10 Uhr oeffnet sich ein Terminalfenster mit der Aufgabe des
Tages, und die Antwortdatei geht in TextEdit auf. Antwort unter
"Deine Antwort" schreiben, speichern, fertig. Die Aufgaben kommen aus den
Luecken im Archiv: offene Fragen aus `CONTENT-AUDIT.md`, Ausstellungen ohne
Werkangabe, fehlende Texte, Bildbeschreibungen, Dateien ohne Zuordnung.

```
python3 tools/website.py aufgabe            # Aufgabe des Tages
python3 tools/website.py aufgabe --bonus    # noch eine
python3 tools/website.py aufgabe --heft     # Ueberblick, Punkte, Stufe, Serie
python3 tools/website.py aufgabe --eingang  # geloest, noch nicht eingearbeitet
python3 tools/website.py links              # prueft alle externen Links (braucht Netz)
python3 tools/website.py archiv             # wie vollstaendig das Archiv ist, was am haeufigsten fehlt
python3 tools/website.py archiv <id>        # Karteikarte eines Eintrags
python3 tools/website.py cv-pdf             # CV als PDF, nach jeder CV-Aenderung neu erzeugen
```

Per Doppelklick geht es auch: `tools/aufgabe.command`. Antworten liegen in
`_aufgabenheft/antworten/`. Eingearbeitet werden sie gemeinsam mit Claude:
"Arbeite die Antworten aus dem Aufgabenheft ein."

Taeglicher Ausloeser abschalten:

```
launchctl bootout gui/$(id -u)/com.schamborski.aufgabenheft
rm ~/Library/LaunchAgents/com.schamborski.aufgabenheft.plist
```

## Archivregeln

- Jahr eines Eintrags ist das Jahr, in dem die Ausstellung aufgebaut wurde.
  Der genaue Zeitraum steht in `date_start` und `date_end` (JJJJ-MM-TT).
- Welche Angaben zu welcher Art von Eintrag gehoeren, steht in
  `tools/archiv.py`. Das Aufgabenheft baut daraus je Eintrag eine Karteikarte.
- Weiss Nickii etwas nicht oder gibt es etwas nicht, kommt der Schluessel des
  Felds in `archive_na` des Eintrags. Dann wird nicht wieder gefragt.
- `build` braucht Pillow: `/opt/homebrew/bin/python3 tools/website.py build`.
- Schwere Bilder bekommen eine Webfassung (`…-web.jpg`, hoechstens 2400 px),
  das Original bleibt liegen und steht in `data/asset-sources.json`.
- Das Repository ist oeffentlich. Was in `_aufgabenheft/` oder `data/` steht,
  ist auf GitHub lesbar, auch wenn die Webseite es nicht zeigt.
- Bildbeschreibungen stehen je Bild in `image_alts` (Pfad -> Satz, Englisch).
  Neue Bilder brauchen eine, `archiv` meldet fehlende.

## Erscheinungsbild

Alles steht in `css/fonts.css`, der einzigen Datei, die jede Seite laedt.

- Zwei Schriften wie in Nickiis Portfolio: `--font-data` (Fredoka) fuer Name,
  Navigation, Titel und Angaben, `--font-text` (ABeeZee) fuer Lesetexte.
- Ton: zurueckhaltend. Angaben klein, in Versalien, weit gesperrt
  (`--track-data`). Titel leicht (Gewicht 300), in Versalien (`--track-title`).
- Farbe: Schwarz (`--ink`), Pink (`--accent`) nur fuer den Namen, kleine
  Rubriken und Hover.
- Keine runden Ecken, keine Schatten, keine Emojis, keine blauen Links.
- Gilt ueberall gleich: Startseite, Raster, Werkseiten, CV, CV-PDF,
  Newsletter, Impressum, Datenschutz, Fehlerseite.
- In den Stylesheets nie einen Schriftnamen oder eine neue Farbe schreiben,
  immer die Variablen. Neue Seiten nehmen `.ci-title` und `.ci-label`.
- Nach Aenderungen am CV oder am Stil: `python3 tools/website.py cv-pdf`.
