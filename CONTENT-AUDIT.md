# Content-Audit September 2026

Stand: 29.09.2026. Alle 92 Einträge und alle Ordner unter `assets/` wurden
geprüft. Nichts ist committet, gepusht oder veröffentlicht. Neue Dateien sind
nur mit `git add` vorgemerkt, damit `check` sie als Teil der Seite erkennt.

Grundsatz: Der CV ist die Referenz. Wo Raster und CV sich widersprachen und
der CV eindeutig war, gilt der CV. Wo er nichts sagt, bleibt der Eintrag wie
er war und die Frage steht unten. Originaldateien wurden nicht gelöscht.

## 1. Bitte bestätigen oder korrigieren

Diese Punkte sind nicht entschieden. Die Seite zeigt überall den bisherigen
Stand, außer wo "geändert" steht.

| # | Eintrag | Widerspruch | Was jetzt gilt |
|---|---------|-------------|----------------|
| 1 | Statement und "Selected works" auf der Startseite | Neu geschrieben, nur aus deinen eigenen Werktexten und dem CV zusammengesetzt | **Entwurf.** Text und Auswahl stehen in `data/site.json` und lassen sich dort ändern |
| 2 | `bundeskunstpreis-2021` | Titel "24th", Jahr 2020, sort_year 2021, Link und Bild vom 25. Preis. CV: Nominierung 24. Preis 2018, 25. Preis 2021 | **Geändert nach CV:** aufgeteilt in `bundeskunstpreis-nomination-2018` (ohne Bild) und `bundeskunstpreis-2021` (Preis, Bild der Verleihung). `bundeskunsthalle-2022` ist jetzt nur die Ausstellung |
| 3 | `freitag-article-2020` | Verwies auf `amo-exhibition-2020`, einen Eintrag, den es nie gab. Außerdem nennt die Zitierangabe Peter Nowak als Autor, der Eintrag steht aber unter "Written by", und der CV führt den Text unter deinen Veröffentlichungen | Verweis entfernt, Ausstellungstitel aus deinem Manuskript in die Beschreibung übernommen. **Autorschaft bitte klären** |
| 4 | `on-desire-2020` | Das Plakat (bisher verwaistes Bild) nennt 29.11.2019 bis 12.01.2020, Raster und CV sagen 2020. Galerie heißt auf dem Plakat "Galerie vom Zufall und vom Glück", im CV "Gallerie" | Jahr bleibt 2020, Plakat ist jetzt Titelbild. **Jahr und Schreibweise bitte bestätigen** |
| 5 | `matara-festival-2024` | Dateinamen heißen `Matara2023…`, Eintrag und CV sagen 2024 | Bleibt 2024 |
| 6 | `untitled-resilience-2024` | Kachel heißt "Anastasiia", Text und Videoseite heißen "Untitled Resilience". Das alte JSON-LD nannte 2021 | Bleibt "Anastasiia", 2024. **Welcher Titel ist richtig?** |
| 7 | `nickii-ai-2026` (vorher `Nickii-AI`) | Specs sagen "Exhibited at Ars Electronica 2026", das steht nicht im CV. Altes JSON-LD nannte 2025 als Entstehungsjahr | Bleibt im Raster, **nicht mehr im JSON-LD**. Bitte bestätigen oder in den CV aufnehmen |
| 8 | `at-sp-ars-electronica-campus-exhibition-2026` | Titel beginnt mit "Upcoming:", das Festival ist vorbei | Unverändert. Tippfehler "UpAT/SP" in der Beschreibung behoben |
| 9 | `daad-graduate-2025`, `new-society-scholarship-2025` | Beschreibung sagt 2025–2027, Specs und CV-MFA sagen 2025–2028 | Unverändert |
| 10 | `saic-lecture-2025` | Raster: "The Politics of AI Aesthetics", CV: "The Politics of AI Images" | Beide unverändert |
| 11 | `caa-114th-annual-conference-volunteer-2025` | Die 114. CAA-Konferenz in Chicago fand meines Wissens im Februar 2026 statt, Eintrag und CV sagen 2025 | Unverändert |
| 12 | `saic-ta-ai-2026` | Steht im Raster, fehlt im CV | Nicht in den CV aufgenommen. Soll er rein? |
| 13 | `kassel-doc-fest-catalog-2020` | Das angehängte PDF `IMG_20201117_0001.pdf` ist laut Text eine Seite "Kunstverein 153, Testing Trixi, Braunschweig 2020", nicht der Dokfest-Katalog | Unverändert. Die neu zugeordnete Katalogseite `Texte/schamborski_katalogtext_37dokfest.jpg` zeigt den Dokfest-Text zu Testing Trixi |
| 14 | `saic-ta-2025` | Die Galerie enthält ein Ausstellungsfoto von Among Us (`UnterUns_amoungUs_bundeskunsthalle4.jpg`, identisch mit "Nickii Teaching Position SAIC cover photo.jpg") | Unverändert, vermutlich Absicht |
| 15 | `familycare-solo-metavier-2021` | Titelbild war dasselbe Still wie beim Werk Familycare | **Geändert:** Titelbild ist jetzt eine Ausstellungsansicht aus dem Ordner `Scope/` (Fenster mit "familycare"-Schriftzug) |
| 16 | `funplastic-2017` | Institution schreibt "Alvar-Alto-House" | Im Feld unverändert, in der neuen Beschreibung "Alvar Aalto House" |
| 17 | `represent-2022` | Hatte nur einen deutschen Text | Englische Beschreibung als **Übersetzung deines deutschen Texts** ergänzt, bitte gegenlesen |
| 18 | `kunstdienst-2022`, `scope-biennale-2021` | Kein Werk- bzw. Ausstellungstext vorhanden. Bei S.C.O.P.E. ist unklar, welche Arbeit gezeigt wurde | Nur eine sachliche Zeile aus Specs bzw. CV. Ein echter Text fehlt |
| 19 | Portfolio-PDF | Funktioniert live (19 MB). `.gitignore` schließt aber `*-hq.pdf` aus, ein neues Portfolio mit gleichem Namensmuster würde stillschweigend nicht mitgehen | Link jetzt mit Größenangabe. Für ein neues PDF die Regel anpassen oder einen anderen Namen wählen |

## 2. Was geändert wurde

**Eine Quelle für CV und Raster.** Jede CV-Zeile hängt jetzt als Feld `cv` am
passenden Eintrag in `data/content.json`. `python3 tools/website.py build`
schreibt daraus `pages/cv.html`. Der Wortlaut des CV ist unverändert, bis auf
"fuer" zu "für" in zwei Zeilen. `check` meldet, wenn eine CV-Zeile und das
Jahr im Raster auseinanderlaufen oder eine Auszeichnung im CV fehlt.

**Einträge.** 94 statt 92:
- neu `bundeskunstpreis-nomination-2018` (siehe Punkt 2)
- neu `freelance-artistic-producer-2015-2020`, die einzige CV-Zeile ohne Eintrag

Sprechende ids statt generischer:

| alt | neu |
|-----|-----|
| `new-entry-1778952939730` | `we-stay-home-2017` |
| `new-entry-1778952795758` | `monuments-patch-of-grass-wolfsburg-2018` |
| `new-entry-1778952221338` | `funplastic-2017` |
| `Nickii-AI` | `nickii-ai-2026` |
| Ordner `new-entry-1778953439573` | `on-desire-2020` |

Die drei ehemaligen new-entry-Einträge haben den Typ "Exhibition" und eine
Beschreibung aus Ort und Monat. Mehr gaben die Daten nicht her.

Neue Beschreibungen aus dem CV: `open-studios-saic-2025`,
`hbk-lecture-exhibition-2023`, `hbk-workshop-discrimination-2023`,
`udk-berlin-2023`.

**Datenmüll entfernt.** Achtmal `"[object Object]"` in `related_links`.
Zwei `link`-Felder zeigten auf Bilddateien (`nickii-ai-2026`,
`biff-braunschweig-2017`), sodass "Visit Link" ein Bild öffnete. Beim
Deutschlandstipendium zeigte die Galerie das DAAD-Bild (Reichstag) statt des
Titelbilds.

**TIFF-Dateien.** Fünf Galeriebilder waren TIFF und in Chrome und Firefox
unsichtbar (Familycare 4x, Unused Capacity 1x). Sie haben jetzt JPEG-Webfassungen.

**Seitenweite Verweise.** Favicon-32, Favicon-16, Apple-Touch-Icon und
`site.webmanifest` lieferten live 404. Sie existieren jetzt, dazu `favicon.svg`
und `favicon.ico`. Das Vorschaubild für soziale Netzwerke war mit 1200 x 630
angegeben, hatte aber 450 x 675 und war dein Porträt. Neu ist
`assets/og/preview.jpg` in echten 1200 x 630 aus dem CyberCindy-Titelbild,
einstellbar in `data/site.json`. Alle Adressen zeigen auf `www.schamborski.com`,
die Domain ohne www leitet ohnehin dorthin um.

## 3. SEO und strukturierte Daten

Das alte JSON-LD der Startseite enthielt Behauptungen, die der CV nicht deckt.
Entfernt:

- "based in Kiel, Braunschweig, Chicago and Berlin"
- Mitgliedschaft bei ZKM und transmediale (laut CV Praktikum bzw. Volunteer)
- "Exhibited at ZKM Karlsruhe" und "Exhibited at Ars Electronica 2026"
- Abschlussarbeit "The Politics of AI Aesthetics / Technofictation"
- `alumniOf` SAIC, das Studium läuft noch. Jetzt `affiliation`
- `worksFor` SAIC
- Schlagworte wie "TESCREAL Critique" oder "Algorithmic Violence" in
  `knowsAbout` und in den Keywords

Das neue Person-JSON-LD wird aus dem CV erzeugt: Auszeichnungen aus dem
Abschnitt Recognition, Abschlüsse HBK und ITB, Affiliation SAIC, die
ausgewählten Arbeiten. Jede Arbeit hat eine eigene Seite unter `works/` mit
`VisualArtwork`-Daten, Alt-Texten, Bildunterschriften und einem Satz
Zusammenfassung aus Typ, Jahr und Ausstellungen. Dazu kommen `sitemap.xml`
und `robots.txt`.

## 4. Neu zugeordnete Bilder

Nur wo Ordnername, Dateiname oder Bildinhalt eindeutig waren. Große
Originale wurden auf 2400 Pixel verkleinert in den Eintragsordner kopiert,
die Zuordnung steht in `data/asset-sources.json`.

| Datei(en) | Eintrag | Grund |
|-----------|---------|-------|
| `bundeskunsthalle-2022/` (9) | bundeskunsthalle-2022 | Ordner hieß wie der Eintrag |
| `bundeskunstpreis-catalog-2022/` (2 von 3, eins doppelt) | bundeskunstpreis-catalog-2022 | Ordner hieß wie der Eintrag |
| `Scope/I3B*.jpg` (3) | familycare-solo-metavier-2021 | Schriftzug "familycare" im Bild |
| `new-entry-1778953439573/…` | on-desire-2020 | Plakat "auf_begehren // on_desire" |
| `represent/` (6 weitere) | represent-2022 | Ordnername, Shirley im Bild |
| `matara/Matara20234`, `…6` | matara-festival-2024 | Ordnername. 3, 5 und 7 sind unscharf oder zeigen nur den Hof |
| `Emaf-2018.jpg` | emaf-experience-2018 | Dateiname |
| `emaf_social-media_motiv-03.jpg` | emaf-2022 | Festivalmotiv mit 20.04.–24.04. |
| `kombi-5-2017.jpg` | kombi-5-exhibition-2017 | Dateiname |
| `createyoursurrounding/_MG_0337cccc.jpg` | create-your-surrounding-2017 | Monitorinstallation wie im Still |
| `Nickii_AI/DSC00552CC.png` | nickii-ai-2026 | Ordner, Nickii-AI-Oberfläche im Bild |
| `Texte/schamborski_katalogtext_37dokfest.jpg` | kassel-doc-fest-catalog-2020 | Katalogseite 37. Dokfest |
| `HBK-BS_2021_Schamborski_001.jpg` | hbk-diploma-2014-2021 | Serie wie das bisherige Titelbild |
| `Saic_Studio2.jpeg` | saic-mfa-2025-2028 | Gegenstück zu `SAIC_Studio.jpeg` |
| `SAICOpenStudios.jpeg` | open-studios-saic-2025 | Dateiname |
| `IMG_9814.JPG` | entangled-responsibility-2016 | Papierkarten mit Farblegende |
| `flyer#3.jpg` | instrument-public-critique-2018 | "Werkzeug der öffentlichen Kritik", 22.6.–28.6.2018 |
| `Festivals/Biennials/soft power pic.jpg` | soft-power-2020 | Schaufenster Kasseler Dokfest |
| `Untitled-6.jpg` | documenta-fifteen-2022 | Fridericianum mit documenta-fifteen-Banner |

## 5. Ungenutzte Dateien zur Durchsicht

`python3 tools/website.py check --details` listet alle einzeln.
Nichts davon wurde gelöscht.

**Vermutlich eigene Arbeiten ohne Eintrag.** Welche Titel und Jahre?
- `GermanEurofighter/140_german_eurofighter_45min_loop…jpg`
- `supportyourlocalfascist/` (Bild und PSD)
- `OrganicanarchyStill1.0.jpg` (Schriftzug "organic anarchy")
- `militär0001.tif`, `nazizombi1000.tif`, `veins0399.tif`, `violentforce1000.tif` (3D-Renderings)
- `Hopfenmitschild.tif`, `Bild2Stripecc.jpg`
- `goldencube-6.mp4`

**Zuordnung wahrscheinlich, aber nicht sicher.**
- `Nickii_AI/IMG_1827CC.png`: Ausstellungsraum mit Bildschirmen, CyberCindy oder Nickii AI?
- `DSC03112cc.jpg`, `DSC03120cc_1ohnevignette.jpg`, `FullSizeRender.jpeg`: Studio- und Drehsituationen
- `IDÖK4.pdf`: vermutlich Instrument der öffentlichen Kritik
- `IMG_20201117_0002.pdf`, `dokfest.pdf`: Katalogseiten, siehe Punkt 13
- `Amo Afer Guinea Kunstverein Braunschweig.pdf`: dein Manuskript zum Freitag-Text. Soll es öffentlich verlinkt werden?
- `UnterUns_amoungUs_bundeskunsthallemitAIerweiterung.png`: KI-erweiterte Ausstellungsansicht, bewusst nicht verwendet
- `Arbeiten/AmongUs_UnterUns/Untitled_3.4.1.png`, `WorkingtitletoxicStill1.png`: Among Us
- `Untitled Resilience/` (32 Stills), `StillsUntitledResilience/` (4): der Eintrag hat schon 5 ausgewählte Stills
- `matara/Matara20233`, `…5`, `…7`, `Festivals/Biennials/images.jpeg` (Voltaje-Plakat, nur 225 px)

**Duplikate** (gleicher Inhalt, andere Stelle): `Emaf-2018.jpg` = `IMG_2307.jpg`,
`preview.jpg` = `nick_schamborski_450.jpg`, `Matara20231/2` doppelt, der
komplette Ordner `Arbeiten/` spiegelt `Texte/`, `AmongUs_UnterUns/` und
andere, drei Dateien in `funplastic-2017/`, je eine in
`germany-scholarship-2019/` und `bundeskunstpreis-catalog-2022/`.

**Kaputt oder leer:** `Still00.png` (0 Byte). `hbk-logo.png`,
`saic-logo.png`, `saic-building.jpg`, `hbk-building.jpg`, `itb-bandung.jpg`,
`zkm-building.jpg`, `zkm-logo.jpg`, `documenta-logo.png`,
`bundeskunsthalle*.jpg` sind keine lesbaren Bilder.

**Alte Vorschauen** (rund 820 px, aus einem früheren Portfolio):
`*-still-1.jpeg`, `*-still-2.jpeg` und die Hochformate direkt unter
`assets/images/`. Für jede Arbeit gibt es bessere Fassungen.

**Arbeitsdateien, die öffentlich ausgeliefert werden:** `.docx`, `.odt`,
`.psd` und der Brief `Für ein Ende der Transfeindlichkeit auf Youtube! …pdf`
(25 MB) liegen in Git und sind damit unter schamborski.com abrufbar. Bitte
entscheiden, ob sie dort bleiben sollen.

## 6. Hinweise aus der externen Analyse

Umgesetzt:
- Startseite mit Statement und acht ausgewählten Arbeiten statt einer reinen Linkliste
- eigene, indexierbare Seite je Arbeit mit `VisualArtwork`-Daten, Galerie und Alt-Texten
- Person-JSON-LD, Sitemap, kanonische Adressen
- Unterfilter nach Medium unter "Works" (Video, Installation & Objects,
  Performance, Photography), abgeleitet aus dem Feld `type`
- Einträge ohne Titelbild erscheinen als Textkarte statt als graue Fläche

Die Analyse geht von einzelnen "Full Details"-Unterseiten für jedes
Ehrenamt aus. Die gab es nie, alles lag in einem Dialog. Seiten gibt es jetzt
nur für Arbeiten, Ehrenämter bekommen bewusst keine.

Braucht Material von dir:
- thematische Gruppen wie "Post-Colonial Critique" oder "Hardware & Mesh
  Networks". Das ist eine kuratorische Entscheidung, das Feld `tags` ist dafür da
- Konzepttexte für G-Spirit, Funke und Grain Management
- Transkripte, Folien oder Leselisten zu Vorträgen und Workshops
- Videodokumentation und Detailfotos der Geräte
- Beschreibende Bildunterschriften je Foto. Die Alt-Texte nennen bisher Titel,
  Jahr, Typ und Bildnummer, nicht den Bildinhalt
