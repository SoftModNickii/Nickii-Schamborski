"""
aufgabenheft.py - jeden Tag eine Aufgabe fuer das Archiv.

Das Heft sammelt alle Luecken des Archivs. Jeden Tag kommt eine davon dran.

Woher die Aufgaben kommen:
    dringend    Freigaben, Rueckfragen, sichtbar Kaputtes (fest im Code)
    audit       offene Fragen aus CONTENT-AUDIT.md (fest im Code)
    technik     Konten, DNS, Entscheidungen zur Seite (fest im Code)
    pflege      jeden Monat "Was ist neu?", jedes Quartal eine Durchsicht
    text        Texte, die Claude geschrieben hat und Nickii noch nicht
                gegengelesen hat ("text_status": "entwurf" im Eintrag)
    karte       eine Karteikarte je Eintrag, erzeugt aus dem Schema in
                tools/archiv.py: alle Angaben, die nur Nickii wissen kann
    daten       Texte, Bilder, Material, erzeugt aus data/content.json
    datei       Dateien im Repo ohne Eintrag

Der Fortschrittsbalken misst nicht geloeste Aufgaben, sondern wie
vollstaendig die Daten sind (tools/archiv.py). Neue Eintraege und neue
Felder im Schema erzeugen ihre Aufgaben von selbst.

    python3 tools/website.py aufgabe            Aufgabe des Tages
    python3 tools/website.py aufgabe --bonus    Noch eine, wenn du Lust hast
    python3 tools/website.py aufgabe --heft     Ueberblick mit allen Aufgaben
    python3 tools/website.py aufgabe --eingang  Geloest, aber noch nicht eingearbeitet
    python3 tools/website.py aufgabe --eingearbeitet <id>   als erledigt markieren

Geloest wird in einer Datei je Aufgabe unter _aufgabenheft/antworten/.
Sobald unter "Deine Antwort" etwas steht, zaehlt die Aufgabe als geloest.
Eingearbeitet in content.json werden die Antworten danach gemeinsam mit
Claude ("arbeite die Antworten aus dem Aufgabenheft ein").

Der Ordner beginnt mit einem Unterstrich. GitHub Pages liefert ihn daher
nicht aus, er ist nur im Repository sichtbar.
"""

import datetime
import json
import os
import re

import archiv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEFT = os.path.join(ROOT, "_aufgabenheft")
ANTWORTEN = os.path.join(HEFT, "antworten")
FORTSCHRITT = os.path.join(HEFT, "fortschritt.json")
UEBERBLICK = os.path.join(HEFT, "AUFGABENHEFT.md")
CONTENT = os.path.join(ROOT, "data", "content.json")
SITE = os.path.join(ROOT, "data", "site.json")

MARKE = "## Deine Antwort"
HINWEIS_ZEILE = "<!-- Schreib unter diese Zeile."

STUFEN = [
    (0, "Praktikant:in im eigenen Archiv"),
    (8, "Archivassistenz"),
    (20, "Registrar:in"),
    (40, "Sammlungskurator:in"),
    (80, "Chefkurator:in"),
    (140, "Direktor:in des Archivs"),
    (220, "Lebendes Archiv"),
]

ARTEN = {
    "bestaetigen": "Bestätigen",
    "verbinden": "Verbinden",
    "beschreiben": "Beschreiben",
    "schreiben": "Schreiben",
    "zuordnen": "Zuordnen",
    "fotografieren": "Fotografieren",
    "erinnern": "Erinnern",
    "erledigen": "Erledigen",
    "karteikarte": "Karteikarte",
    "gegenlesen": "Gegenlesen",
}

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]


# ------------------------------------------------------------ feste Aufgaben
# Aus CONTENT-AUDIT.md. Die ids bleiben stabil, damit Antworten ihre
# Aufgabe behalten, auch wenn sich die Liste spaeter aendert.

# Welcher Archiveintrag zu einer Audit-Frage gehoert. Die Heftseite zeigt
# dessen aktuellen Stand neben der Frage.
AUDIT_EINTRAG = {
    "audit-freitag": "freitag-article-2020",
    "audit-anastasiia": "untitled-resilience-2024",
    "audit-on-desire": "on-desire-2020",
    "audit-nickii-ai": "nickii-ai-2026",
    "audit-ars-electronica": "at-sp-ars-electronica-campus-exhibition-2026",
    "audit-daad": "daad-graduate-2025",
    "audit-vortrag-titel": "saic-lecture-2025",
    "audit-caa": "caa-114th-annual-conference-volunteer-2025",
    "audit-ai-ta-cv": "saic-ta-ai-2026",
    "audit-matara": "matara-festival-2024",
    "audit-kassel-pdf": "kassel-doc-fest-catalog-2020",
    "audit-represent-uebersetzung": "represent-2022",
}


def audit_aufgaben():
    A = []

    def add(aid, art, sterne, titel, frage, kontext="", dateien=(), format_="", eintrag=None):
        A.append({"id": aid, "art": art, "sterne": sterne, "titel": titel,
                  "frage": frage, "kontext": kontext, "dateien": list(dateien),
                  "format": format_, "prio": 1,
                  "eintrag": eintrag or AUDIT_EINTRAG.get(aid)})

    add("audit-statement", "schreiben", 2, "Dein Statement auf der Startseite",
        "Lies das Statement auf der Startseite. Stimmt es so? Streich, was nicht passt, "
        "und ergänze, was fehlt. Es soll kurz bleiben, höchstens vier Sätze.",
        "Der Entwurf ist nur aus deinen eigenen Werktexten und dem CV zusammengesetzt.",
        ["data/site.json"],
        "Entweder 'passt so' oder deine überarbeitete Fassung.")
    add("audit-auswahl", "bestaetigen", 1, "Die acht ausgewählten Arbeiten",
        "Auf der Startseite stehen acht Arbeiten: CyberCindy, Nickii AI, Funke, "
        "Anastasiia, Among Us, Testing Trixi, Denied Refuge, Familycare. "
        "Sind das die richtigen, in der richtigen Reihenfolge?",
        format_="'passt so' oder deine Liste in Wunschreihenfolge.")
    add("audit-freitag", "bestaetigen", 1, "Wer hat den Freitag-Text geschrieben?",
        "Der Artikel 'Wer kennt diesen bedeutenden Philosophen?' im Freitag: Die "
        "Zitierangabe nennt Peter Nowak als Autor, dein CV führt ihn als deinen Text. "
        "Wer hat ihn geschrieben, und wo ist er erschienen?",
        "Im Repo liegt dein Manuskript 'Amo Afer Guinea Kunstverein Braunschweig.pdf'.",
        ["assets/images/Amo Afer Guinea Kunstverein Braunschweig.pdf"],
        "Autor:in, und ob das Manuskript auf der Seite verlinkt werden darf.")
    add("audit-anastasiia", "bestaetigen", 1, "Anastasiia oder Untitled Resilience?",
        "Die Kachel heißt 'Anastasiia', der Werktext und die Videoseite heißen "
        "'Untitled Resilience'. Welcher Titel gilt, und aus welchem Jahr ist die Arbeit?")
    add("audit-on-desire", "bestaetigen", 1, "on_desire: 2019 oder 2020?",
        "Das Plakat nennt 29.11.2019 bis 12.01.2020, Raster und CV sagen 2020. Welche "
        "Jahreszahl soll stehen? Und schreibt sich die Galerie 'Galerie' oder 'Gallerie' "
        "vom Zufall und vom Glück?",
        dateien=["assets/images/on-desire-2020/on-desire-2020-poster.jpg"])
    add("audit-nickii-ai", "bestaetigen", 1, "Nickii AI bei Ars Electronica?",
        "Bei Nickii AI steht 'Exhibited at Ars Electronica 2026'. Stimmt das? Wann ist "
        "die Performance entstanden, 2025 oder 2026? Und wo wurde sie sonst gezeigt?",
        format_="Ja/nein, Jahr, Orte mit Datum.")
    add("audit-ars-electronica", "erinnern", 2, "Wie war Ars Electronica?",
        "Der Eintrag nennt jetzt CyberCindy und Nickii AI und steht im CV. Es fehlen "
        "die genauen Tage in Linz und ein paar Sätze, wie es war.",
        format_="Datum von bis, zwei bis drei Sätze.")
    add("audit-daad", "bestaetigen", 1, "DAAD bis 2027 oder 2028?",
        "Beim DAAD-Stipendium und bei der New Society Scholarship steht einmal 2025–2027, "
        "einmal 2025–2028. Was ist richtig?")
    add("audit-vortrag-titel", "bestaetigen", 1, "Wie hieß dein Vortrag an der SAIC?",
        "Das Raster sagt 'The Politics of AI Aesthetics', der CV 'The Politics of AI "
        "Images'. Welcher Titel ist richtig?")
    add("audit-caa", "bestaetigen", 1, "Wann war die CAA-Konferenz?",
        "Die 114. CAA-Konferenz in Chicago, bei der du geholfen hast: Eintrag und CV "
        "sagen 2025. War es nicht Februar 2026?")
    add("audit-ai-ta-cv", "bestaetigen", 1, "TA Artificial Intelligence im CV?",
        "Deine zweite Runde als Teaching Assistant bei Doug Rosman (Fall 2026) steht im "
        "Raster, aber nicht im CV. Soll sie in den CV?")
    add("audit-matara", "bestaetigen", 1, "Matara 2023 oder 2024?",
        "Die Fotos heißen 'Matara2023…', Eintrag und CV sagen 2024. Welches Jahr stimmt?",
        dateien=["assets/images/Matara20231.JPG"])
    add("audit-kassel-pdf", "zuordnen", 1, "Welche Katalogseite ist das?",
        "Am Dokfest-Katalog hängt das PDF 'IMG_20201117_0001.pdf'. Darin steht "
        "'Kunstverein 153, Testing Trixi, Braunschweig 2020'. Zu welcher Ausstellung "
        "gehört es? War Testing Trixi 2020 im Kunstverein Braunschweig zu sehen?",
        dateien=["assets/pdfs/IMG_20201117_0001.pdf", "assets/images/IMG_20201117_0002.pdf"])
    add("audit-represent-uebersetzung", "bestaetigen", 1, "Represent auf Englisch",
        "Represent hatte nur einen deutschen Text. Die englische Fassung ist eine "
        "Übersetzung davon. Lies sie gegen.",
        dateien=["works/represent-2022.html"],
        format_="'passt so' oder deine Korrekturen.")
    add("audit-arbeitsdateien", "bestaetigen", 1, "Sollen Arbeitsdateien öffentlich bleiben?",
        "Im Repo liegen .docx, .odt und .psd-Dateien und der Brief 'Für ein Ende der "
        "Transfeindlichkeit auf Youtube!' (25 MB). Alles davon ist unter schamborski.com "
        "abrufbar. Was soll bleiben, was soll raus?",
        "Liste in CONTENT-AUDIT.md, Abschnitt 5.")
    add("audit-portfolio", "bestaetigen", 1, "Gibt es ein neueres Portfolio-PDF?",
        "Verlinkt ist 'Nickii-Schamborski-Portfolio-02-2025-hq.pdf' (19 MB). Gibt es eine "
        "neuere Fassung? Soll es auch eine leichtere Version zum Mailen geben?")
    return A


def dringend_aufgaben():
    """Was vor allem anderen kommt: die Freigabe der neuen Fassung, Rueckfragen
    zu schon gegebenen Antworten und alles, was auf der Seite sichtbar kaputt ist."""
    A = []

    def add(aid, art, sterne, titel, frage, kontext="", dateien=(), format_="", eintrag=None):
        A.append({"id": aid, "art": art, "sterne": sterne, "titel": titel,
                  "frage": frage, "kontext": kontext, "dateien": list(dateien),
                  "format": format_, "prio": 0, "eintrag": eintrag})

    add("freigabe-neue-fassung", "bestaetigen", 2, "Die neue Fassung ansehen und freigeben",
        "Die umgebaute Seite liegt seit dem 29.09. nur auf deinem Rechner. Online steht noch "
        "die alte Fassung, mit Angaben, die dein CV nicht deckt (zum Beispiel 'Exhibited at "
        "ZKM Karlsruhe' und vier Wohnorte). Schau dir die neue Fassung lokal an. Darf sie "
        "online gehen, auch wenn noch Fragen im Heft offen sind?",
        "Ansehen mit: python3 tools/website.py serve, dann http://localhost:8000. Die offenen "
        "Fragen betreffen einzelne Einträge und lassen sich danach Stück für Stück nachziehen.",
        format_="'ja, online stellen' oder was vorher noch geändert werden muss.")
    add("rueckfrage-statement", "bestaetigen", 1, "Dein Statement, gegengelesen",
        "Dein neuer Text steht jetzt auf der Startseite. Korrigiert sind nur Tippfehler und "
        "Satzzeichen. Drei Stellen habe ich gedeutet: 'lores communication devices' als LoRa, "
        "'self holding' als 'self-sustaining', und die offene Klammer als '(like Angels "
        "Tutorial or CyberCindy)'. Stimmt das so?",
        "Der Text ist länger als die geplanten vier Sätze. Wenn du magst, markier den einen "
        "Absatz, der auch allein stehen könnte, etwa für Vorschauen in Suchmaschinen.",
        ["data/site.json"], "'passt so' oder deine Korrekturen.")
    add("freigabe-online", "bestaetigen", 1, "Darf die neue Fassung online gehen?",
        "Du hast recht: Du hast nie im ZKM ausgestellt, dort war dein Artist Internship. Genau "
        "dieser Fehler steht aber noch auf der Seite, die gerade online ist. In der neuen "
        "Fassung auf deinem Rechner ist er raus. Darf ich die neue Fassung online stellen? "
        "Die Texte, die du noch gegenlesen willst, lassen sich danach weiter ändern.",
        "Ansehen: http://localhost:8000 (läuft, solange die Vorschau gestartet ist).",
        format_="'ja, online stellen' oder was vorher noch geändert werden muss.")
    add("statement-vorschlag", "gegenlesen", 1, "Statement: eine aufgeräumte Fassung",
        "Du findest das Statement unordentlich. Unten steht ein Vorschlag mit denselben "
        "Gedanken in derselben Reihenfolge, nur gestrafft. Auf der Seite steht weiter deine "
        "Fassung, bis du dich entscheidest.",
        "Thank you for passing by.\n\n"
        "This site collects most of what I do. I started as a video and performance artist "
        "looking for meaning in existence, working as a fictional documentarist and "
        "manipulating images with the tools of commercial VFX production. From there I turned "
        "to films that happen inside screens, on phones and other devices, to question our "
        "digital environments and their consequences, as in Angels Tutorial or CyberCindy.\n\n"
        "Gadgets that narrate digital autonomy have interested me since the Instrument of "
        "Public Critique. The same interest now drives the LoRa devices I build: communication "
        "networks that sustain themselves, independent of outside control. What holds my work "
        "together is a fixation on systems, of interaction and political power, on circuit "
        "boards and in cities, and on what those systems ask of us at a time when the ideas in "
        "our heads and the images on our screens merge into one.\n\n"
        "Around the works you will find what happens between them: field trips, exhibitions I "
        "organized, events I volunteered at. A collection of affiliations, achievements and "
        "creations.",
        ["data/site.json"], "'nimm den Vorschlag', 'lass meine Fassung' oder deine Änderungen.")
    add("schrift-entscheidung", "bestaetigen", 1, "Das Erscheinungsbild: edel genug?",
        "Die ganze Seite hat jetzt ein Erscheinungsbild: Fredoka und ABeeZee aus deinem "
        "Portfolio, Titel leicht und in gesperrten Großbuchstaben, Angaben klein und weit "
        "gesperrt, Schwarz mit Pink nur als Akzent, keine runden Ecken, keine Schatten. Das "
        "gilt auch für CV-PDF, Newsletter, Impressum und Datenschutz. Schau alle Seiten an, "
        "auch auf dem Telefon.",
        format_="'passt so' oder was dich stört, am besten mit der Seite dazu.")
    add("rueckfrage-auswahl", "bestaetigen", 1, "Mehr Arbeiten auf der Startseite: welche?",
        "Du schreibst, du hast noch viel mehr Arbeiten und willst sie sehen. Die acht stehen "
        "jetzt streng nach Datum, die neueste zuerst. Was meinst du mit mehr: (a) alle 20 "
        "Arbeiten aus dem Archiv auf die Startseite, (b) eine größere Auswahl, oder (c) "
        "Arbeiten, die noch gar nicht im Archiv sind?",
        format_="a, b mit Titeln, oder c mit Titel und Jahr der fehlenden Arbeiten.")
    add("rueckfrage-freitag-manuskript", "bestaetigen", 1, "Darf das Amo-Manuskript verlinkt werden?",
        "Der Freitag-Text läuft jetzt unter deinem Namen, mit dem Hinweis, dass er mit "
        "Unterstützung von Peter Nowak auf dessen Freitag-Seite erschienen ist. Offen ist "
        "noch: Darf dein Manuskript als PDF auf der Seite verlinkt werden? Und passt die "
        "Formulierung zu Peter Nowak?",
        dateien=["assets/images/Amo Afer Guinea Kunstverein Braunschweig.pdf"],
        format_="ja/nein zum PDF, und wie Peter Nowak genannt werden soll.",
        eintrag="freitag-article-2020")
    add("rueckfrage-jahresregel", "bestaetigen", 1, "Die Jahresregel und die Bundeskunsthalle",
        "Deine Regel gilt jetzt: Es zählt das Jahr, in dem die Ausstellung aufgebaut wurde. "
        "on_desire steht damit unter 2019, der Zeitraum 29.11.2019 bis 12.01.2020 ist "
        "gespeichert. Nach derselben Regel wäre die Ausstellung zum Bundespreis in der "
        "Bundeskunsthalle 2021 statt 2022, sie lief vom 12.11.2021 bis 30.01.2022. Im CV und "
        "im Raster steht 2022. Soll ich das auf 2021 ändern?",
        format_="'ja, 2021' oder 'bleibt 2022'.", eintrag="bundeskunsthalle-2022")
    add("technik-videoseiten", "erledigen", 2, "Die Videoseiten sind nicht erreichbar",
        "Sechs Arbeiten verlinken auf eigene Videoseiten, und alle sechs zeigen 'Site not "
        "found': cybercindy, untitledresilience, amongus, testingtrixi, systemchange und "
        "familycare, jeweils .schamborski.com. Wer auf 'Watch' klickt, landet im Leeren. "
        "Wo liegen die Videos heute? Gibt es Vimeo- oder YouTube-Links, mit oder ohne Passwort?",
        "Die Adressen zeigen auf GitHub Pages, dort gibt es aber keine Seite mehr dazu. "
        "Entweder gibt es die alten Repositories noch und sie lassen sich wieder anschließen, "
        "oder wir verlinken direkt auf die Videos.",
        format_="Je Arbeit ein Link, oder 'Repos gibt es noch' mit Namen. Sonst: 'Link vorerst raus'.")
    return A


def technik_aufgaben():
    """Was nur Nickii erledigen kann: Konten, DNS, Entscheidungen zur Seite."""
    A = []

    def add(aid, art, sterne, titel, frage, kontext="", dateien=(), format_="", eintrag=None):
        A.append({"id": aid, "art": art, "sterne": sterne, "titel": titel,
                  "frage": frage, "kontext": kontext, "dateien": list(dateien),
                  "format": format_, "prio": 1, "eintrag": eintrag})

    add("technik-tote-links", "bestaetigen", 1, "Vier Links führen ins Leere",
        "Diese Adressen gibt es nicht mehr: die HBK-Meldung zum Bundespreis "
        "(imperia.hbk-bs.de, bei zwei Einträgen), die SAIC-Seite zur Student Government und "
        "die SAIC-Seite zum Low-Residency MFA. Kennst du die neuen Adressen, oder sollen die "
        "Links raus?",
        "Prüfen lässt sich das jederzeit mit: python3 tools/website.py links",
        format_="Neue Adresse je Link, oder 'raus'.")
    add("technik-baustelle", "bestaetigen", 1, "Soll das Baustellen-Banner weg?",
        "Oben auf der Startseite steht 'Website under construction'. Mit der neuen Fassung "
        "ist die Seite vollständig. Soll das Banner beim nächsten Online-Stellen verschwinden? "
        "Der Link zum Portfolio-PDF bliebe erhalten.",
        format_="'weg' oder 'bleibt'.")
    add("technik-mailjet-domain", "erledigen", 1, "Mailjet: Domain bestätigen",
        "Für den Newsletter: In Mailjet unter 'Meine Domain validieren' bei Option 1 auf "
        "Prüfen klicken. Die Prüfdatei liegt schon auf der Seite und ist erreichbar.",
        format_="'erledigt', dann lösche ich die Prüfdatei.")
    add("technik-dns", "erledigen", 2, "Mailjet: vier DNS-Einträge bei df.eu",
        "Im Kundenmenü von df.eu, damit Newsletter nicht im Spam landen: SPF um "
        "'include:spf.mailjet.com' ergänzen, DKIM als 'mailjet._domainkey' anlegen (Wert "
        "steht in Mailjet), den Wildcard-TXT-Eintrag löschen, DMARC mit 'p=none' anlegen.",
        "Stand 04.10.2026: Der Wildcard-Eintrag antwortet noch auf jede Subdomain mit dem "
        "SPF-Text, DKIM und DMARC fehlen. Solange der Wildcard-Eintrag steht, kann DMARC "
        "nicht funktionieren.",
        format_="'erledigt', dann prüfe ich die Einträge von außen nach.")
    add("technik-mailjet-formular", "erledigen", 1, "Mailjet: Anmeldeformular holen",
        "In Mailjet unter Kontakte > Formulare ein Anmeldeformular anlegen, Double-Opt-in "
        "einschalten, und den Einbettungscode hier einfügen. Dann ersetzt das Formular den "
        "E-Mail-Link auf der Newsletter-Seite, und die Datenschutzerklärung bekommt den "
        "Mailjet-Absatz.",
        format_="Den Code aus Mailjet hier einfügen.")
    add("technik-mailjet-schluessel", "erledigen", 1, "Mailjet: geheimen Schlüssel erneuern",
        "Der geheime API-Schlüssel von Mailjet war in einem Screenshot zu sehen. In Mailjet "
        "unter Kontoeinstellungen > API-Schlüssel einen neuen erzeugen. Bitte den Schlüssel "
        "selbst nirgends hinschreiben, auch nicht hier.",
        format_="'erledigt'.")
    add("bio", "schreiben", 2, "Deine Kurzbiografie",
        "Kuratorinnen, Kuratoren und Presse brauchen eine Kurzbio zum Kopieren, in der "
        "dritten Person: wer du bist, womit du arbeitest, Ausbildung, zwei bis drei wichtige "
        "Stationen. Die Seite hat bisher nur Statement und CV. Schreib sie oder gib "
        "Stichpunkte, dann formuliere ich einen Entwurf nur aus deinem CV.",
        format_="80 bis 120 Wörter, Deutsch oder Englisch. Oder: 'mach einen Entwurf'.")
    add("portraet", "fotografieren", 2, "Ein Porträtfoto für Presse und Bio",
        "Zur Kurzbio gehört ein Porträt, das Institutionen übernehmen dürfen. Das bisherige "
        "ist nur 450 Pixel breit. Hast du ein aktuelles in voller Auflösung?",
        format_="Bild in _inbox/portraet/ legen und hier nennen, wer fotografiert hat.")
    return A


# Dateien ohne Eintrag. Jede ist eine kleine Detektivaufgabe.
UNBEKANNT = [
    ("datei-eurofighter", "assets/images/GermanEurofighter/140_german_eurofighter_45min_loop_prores_proxy-1.tiffcc.jpg",
     "Kampfjets über einem Gebäude, ein 45-Minuten-Loop"),
    ("datei-supportyourlocalfascist", "assets/images/supportyourlocalfascist/supportyourlocalfascist.jpeg",
     "Schriftzug www.supportyourlocalfascist.com"),
    ("datei-organic-anarchy", "assets/images/OrganicanarchyStill1.0.jpg", "Schriftzug 'organic anarchy'"),
    ("datei-renderings", "assets/images/militär0001.tif",
     "3D-Renderings: militär0001, nazizombi1000, veins0399, violentforce1000"),
    ("datei-hopfen", "assets/images/Hopfenmitschild.tif", "Hopfenpflanze mit Verkehrsschild"),
    ("datei-goldencube", "assets/images/goldencube-6.mp4", "Video 'goldencube-6'"),
    ("datei-bild2stripe", "assets/images/Bild2Stripecc.jpg", "schmaler Bildstreifen mit Himmel"),
    ("datei-studio", "assets/images/DSC03112cc.jpg",
     "Studio mit Greenscreen, auch DSC03120cc_1ohnevignette.jpg"),
    ("datei-fullsize", "assets/images/FullSizeRender.jpeg", "Person am Schreibtisch vor Bildschirmen"),
    ("datei-nickii-ai-raum", "assets/images/Nickii_AI/IMG_1827CC.png", "Ausstellungsraum mit drei Bildschirmen"),
    ("datei-idoek", "assets/images/IDÖK4.pdf", "PDF, vermutlich Instrument der öffentlichen Kritik"),
    ("datei-dokfest-pdf", "assets/images/dokfest.pdf", "PDF mit Namen aus dem Kasseler Dokfest"),
]


# ------------------------------------------------------------ aus den Daten

def daten_aufgaben():
    with open(CONTENT, encoding="utf-8") as fh:
        items = json.load(fh)
    with open(SITE, encoding="utf-8") as fh:
        site = json.load(fh)
    by_id = {i["id"]: i for i in items}
    A = []

    def add(aid, art, sterne, titel, frage, kontext="", dateien=(), format_="", prio=2):
        # Die id endet auf die id des Eintrags, wo es einen gibt
        eintrag = next((iid for iid in by_id if aid.endswith("-" + iid)), None)
        A.append({"id": aid, "art": art, "sterne": sterne, "titel": titel,
                  "frage": frage, "kontext": kontext, "dateien": list(dateien),
                  "format": format_, "prio": prio, "eintrag": eintrag})

    # Arbeiten ohne Text in einer der beiden Sprachen
    for i in items:
        if "works" not in (i.get("categories") or []):
            continue
        if not i.get("description"):
            add(f"text-en-{i['id']}", "schreiben", 3, f"Werktext zu {i['title']}",
                f"Zu {i['title']} gibt es keinen englischen Werktext. Worum geht es in der "
                "Arbeit, was sieht man, was ist die Frage dahinter?",
                format_="Drei bis sechs Sätze. Deutsch geht auch, dann übersetzen wir.")
        if not i.get("description_de"):
            add(f"text-de-{i['id']}", "schreiben", 2, f"{i['title']} auf Deutsch",
                f"Zu {i['title']} fehlt der deutsche Text. Der englische steht unten.",
                i.get("description", ""), format_="Deine deutsche Fassung.")

    # Konzepttexte zu den Geraetearbeiten, die bisher nur Technik beschreiben
    for iid in ("g-spirit-2026", "funke-2026", "grain-management-2026"):
        if iid in by_id:
            add(f"konzept-{iid}", "schreiben", 3, f"Das Warum von {by_id[iid]['title']}",
                f"Der Text zu {by_id[iid]['title']} beschreibt, wie das Gerät gebaut ist. "
                "Was fehlt, ist warum: Was willst du mit dem Objekt auslösen, was passiert "
                "zwischen den Menschen, die es benutzen?",
                by_id[iid].get("description", ""),
                format_="Drei bis fünf Sätze, gern in deinen eigenen Worten.")

    # Bildbeschreibungen fuer die ausgewaehlten Arbeiten
    for iid in site.get("featured") or []:
        i = by_id.get(iid)
        if i and i.get("image") and not i.get("image_alt"):
            add(f"bild-{iid}", "beschreiben", 1, f"Was zeigt das Titelbild von {i['title']}?",
                f"Beschreib das Titelbild von {i['title']} in einem Satz, so als würdest du es "
                "jemandem am Telefon erklären. Das wird der Alt-Text für Menschen, die nicht "
                "sehen, und hilft der Bildersuche.",
                dateien=[i["image"]],
                format_="Ein Satz, zum Beispiel: 'Ein Kind in lila Rüstung reitet auf einem Dinosaurier.'")

    # Vortraege und Workshops: Material fuer das Archiv
    for i in items:
        if i.get("type") in ("Lecture", "Workshop"):
            add(f"material-{i['id']}", "erinnern", 2, f"Material zu {i['title']}",
                f"Gibt es zu '{i['title']}' ({i['year']}) Folien, Stichpunkte, eine Leseliste "
                "oder eine Aufnahme? Und was waren die zwei, drei Kernthesen?",
                i.get("description", ""),
                format_="Kernthesen in Stichpunkten. Dateien bitte in _inbox/ legen und hier nennen.")

    # Eintraege ohne Bild
    for i in items:
        img = i.get("image")
        cats = i.get("categories") or []
        if not img and not ("press" in cats and i.get("link")):
            add(f"foto-{i['id']}", "fotografieren", 2, f"Ein Bild für {i['title']}",
                f"'{i['title']}' ({i['year']}) hat kein Bild. Hast du ein Foto, ein Dokument "
                "oder einen Screenshot, der es zeigt?",
                format_=f"Bild in _inbox/{i['id']}/ legen und hier kurz sagen, was drauf ist.")

    # Themen: kuratorische Entscheidung, deshalb eine eigene Aufgabe
    add("themen", "zuordnen", 3, "Deine Themen",
        "Das Archiv lässt sich bisher nach Medium filtern. Nach welchen Themen würdest du "
        "deine Arbeiten gruppieren? Nenn drei bis sechs Themen und ordne die Arbeiten zu.",
        "Beispiele aus einer externen Analyse: Hardware & Mesh Networks, Post-Colonial "
        "Critique, Video & Performance. Das sind nur Vorschläge.",
        format_="Thema: Arbeit, Arbeit, Arbeit", prio=3)
    return A


# Reihenfolge der Karteikarten: was Besucher:innen zuerst ansehen, kommt zuerst
KARTEN_PRIO = {"arbeit": 3, "ausstellung": 4, "vortrag": 5, "auszeichnung": 6, "taetigkeit": 7}


def karten_aufgaben():
    """Eine Karteikarte je Eintrag: alle Angaben, die im Archiv fehlen und
    die nur Nickii wissen kann, auf einmal statt in zehn Einzelfragen."""
    items, site = archiv.lade()
    featured = set(site.get("featured") or [])
    st = archiv.stand(items)
    A = []
    for item in items:
        s = st[item["id"]]
        felder = [{"key": z["key"], "label": z["label"], "hilfe": z["hilfe"]}
                  for z in s["fehlt"] if z["wer"] == "nickii"]
        if not felder:
            continue
        n = len(felder)
        liste = ", ".join(f["label"] for f in felder)
        A.append({
            "id": f"karte-{item['id']}", "art": "karteikarte",
            "sterne": 1 if n <= 2 else 2 if n <= 4 else 3,
            "titel": f"Karteikarte: {item['title']} ({item['year']})",
            "frage": (f"Zu diesem Eintrag {'fehlt noch eine Angabe' if n == 1 else f'fehlen noch {n} Angaben'}: "
                      f"{liste}. Füll aus, was du weißt. Wo du etwas nicht weißt oder es etwas "
                      "nicht gibt, schreib genau das hin. Dann ist es geklärt und ich frage nicht wieder."),
            "kontext": "", "dateien": [], "felder": felder,
            "format": "Stichpunkte reichen. 'weiß nicht' und 'gibt es nicht' sind gültige Antworten.",
            "prio": 2 if item["id"] in featured else KARTEN_PRIO[s["art"]],
            "eintrag": item["id"],
        })
    return A


def text_aufgaben():
    """Texte, die nicht von Nickii stammen. Laengere einzeln, kurze
    Sachzeilen gebuendelt, damit nicht siebzig Einzelaufgaben entstehen."""
    items, site = archiv.lade()
    featured = set(site.get("featured") or [])
    A, kurz = [], {}
    for item in items:
        if item.get("text_status") != "entwurf" or not item.get("description"):
            continue
        text = item["description"]
        art = archiv.kartenart(item)
        if len(text) < 170 and text.count(". ") < 1:
            kurz.setdefault(art, []).append(item)
            continue
        A.append({
            "id": f"text-pruefen-{item['id']}", "art": "gegenlesen", "sterne": 1,
            "titel": f"Text gegenlesen: {item['title']} ({item['year']})",
            "frage": "Diesen Text habe ich geschrieben, nicht du. Stimmt jeder Satz? Klingt er nach "
                     "dir? Streich, was nicht stimmt oder nichtssagend ist, und schreib um, was du "
                     "anders sagen würdest. Wenn der Eintrag gar keinen Text braucht: 'Text weg'.",
            "kontext": "", "dateien": [],
            "format": "'passt so', deine Fassung, einzelne Korrekturen oder 'Text weg'.",
            "prio": 2 if item["id"] in featured or art == "arbeit" else KARTEN_PRIO.get(art, 6),
            "eintrag": item["id"],
        })
    for art, gruppe in kurz.items():
        for n in range(0, len(gruppe), 8):
            teil = gruppe[n:n + 8]
            zeilen = "\n\n".join(f"{k}. {i['title']} ({i['year']}): {i['description']}"
                                 for k, i in enumerate(teil, start=1))
            A.append({
                "id": f"text-pruefen-kurz-{art}-{n // 8 + 1}", "art": "gegenlesen",
                "sterne": 1,
                "titel": f"Kurztexte gegenlesen: {archiv.ARTEN[art]} ({n // 8 + 1})",
                "frage": f"{len(teil)} kurze Sachzeilen, die ich geschrieben habe. Stimmen sie? "
                         "Nenn die Nummer, wo etwas falsch ist oder fehlt.",
                "kontext": zeilen, "dateien": [],
                "format": "'passt alles' oder zum Beispiel '3: war im Mai, nicht April'.",
                "prio": KARTEN_PRIO.get(art, 7) + 1, "eintrag": None,
                "eintraege": [i["id"] for i in teil],
            })
    return A


def unbekannt_aufgaben():
    return [{"id": aid, "art": "zuordnen", "sterne": 1,
             "titel": f"Detektivarbeit: {beschreibung}",
             "frage": "Diese Datei liegt im Archiv, gehört aber zu keinem Eintrag. "
                      "Was ist das? Welche Arbeit, welches Jahr, wo gezeigt?",
             "kontext": beschreibung, "dateien": [pfad],
             "format": "Titel, Jahr, Medium, wo gezeigt. Oder: 'weg damit'.", "prio": 2,
             "eintrag": None}
            for aid, pfad, beschreibung in UNBEKANNT]


def pflege_aufgaben():
    """Haelt das Archiv aktuell, auch wenn alle Luecken geschlossen sind.
    Die ids tragen Monat und Quartal, so entsteht jede Aufgabe von selbst neu."""
    heute = datetime.date.today()
    monat = f"{MONATE[heute.month - 1]} {heute.year}"
    quartal = (heute.month - 1) // 3 + 1
    A = [{"id": f"neu-{heute:%Y-%m}", "art": "erinnern", "sterne": 1,
          "titel": f"Was ist neu im {monat}?",
          "frage": "Was ist seit dem letzten Mal dazugekommen? Ausstellungen, Screenings, "
                   "Vorträge, Presse, Stipendien, neue Arbeiten, auch Zusagen für später. "
                   "Und: Ist etwas auf der Seite nicht mehr aktuell?",
          "kontext": "Jede Zusage, die du hier nennst, bekommt einen Eintrag und danach "
                     "von selbst eine Karteikarte.",
          "dateien": [],
          "format": "Stichpunkte mit Datum und Ort. Oder: 'nichts Neues'.",
          "prio": 1, "eintrag": None},
         {"id": f"durchsicht-{heute.year}-q{quartal}", "art": "bestaetigen", "sterne": 1,
          "titel": f"Durchsicht {quartal}. Quartal {heute.year}",
          "frage": "Einmal im Quartal: Stimmen Statement, Kurzbio, Kontaktadresse und "
                   "Portfolio-PDF noch? Passt die Auswahl auf der Startseite zu dem, woran du "
                   "gerade arbeitest? Stimmt im CV die letzte Zeile jeder Rubrik?",
          "kontext": "Ich prüfe parallel alle externen Links und melde, was verschwunden ist.",
          "dateien": ["data/site.json"],
          "format": "'passt alles' oder was sich ändern soll.",
          "prio": 1, "eintrag": None}]

    # Angekuendigtes, dessen Datum vorbei ist
    with open(CONTENT, encoding="utf-8") as fh:
        items = json.load(fh)
    for i in items:
        datum = str(i.get("sort_date") or "")
        if (i["title"].lower().startswith("upcoming") and datum and datum[:7] < f"{heute:%Y-%m}"
                and i["id"] not in AUDIT_EINTRAG.values()):
            A.append({"id": f"veraltet-{i['id']}", "art": "erinnern", "sterne": 1,
                      "titel": f"Vorbei: {i['title']}",
                      "frage": f"'{i['title']}' ist noch als Ankündigung eingetragen, das Datum ist "
                               "vorbei. Wie war es? Was wurde gezeigt, an welchen Tagen?",
                      "kontext": "", "dateien": [],
                      "format": "Titel der Arbeit, Datum, zwei bis drei Sätze.",
                      "prio": 1, "eintrag": i["id"]})
    return A


def alle_aufgaben():
    """Mischt die Aufgaben: erst was die Seite sichtbar betrifft und den
    naechsten Push aufhaelt, dann abwechselnd leichte und aufwendige."""
    audit = dringend_aufgaben() + audit_aufgaben() + technik_aufgaben() + pflege_aufgaben()
    rest = sorted(text_aufgaben() + karten_aufgaben() + daten_aufgaben() + unbekannt_aufgaben(), key=lambda a: a["prio"])
    leicht = [a for a in rest if a["sterne"] == 1]
    mittel = [a for a in rest if a["sterne"] == 2]
    schwer = [a for a in rest if a["sterne"] == 3]
    gemischt = []
    muster = ["leicht", "mittel", "leicht", "schwer"]
    quellen = {"leicht": leicht, "mittel": mittel, "schwer": schwer}
    while leicht or mittel or schwer:
        for m in muster:
            q = quellen[m] or leicht or mittel or schwer
            if q:
                gemischt.append(q.pop(0))
    seen, out = set(), []
    for a in audit + gemischt:
        if a["id"] not in seen:
            seen.add(a["id"])
            out.append(a)
    return out


# ------------------------------------------------------------ Fortschritt

def lade_fortschritt():
    try:
        with open(FORTSCHRITT, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"aufgaben": {}, "tage": {}}


def speichere_fortschritt(f):
    os.makedirs(HEFT, exist_ok=True)
    with open(FORTSCHRITT, "w", encoding="utf-8") as fh:
        json.dump(f, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def antwort_pfad(a):
    return os.path.join(ANTWORTEN, f"{a['id']}.md")


def antwort_text(a):
    try:
        with open(antwort_pfad(a), encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return ""
    if MARKE not in text:
        return ""
    teil = text.split(MARKE, 1)[1]
    teil = re.sub(r"<!--.*?-->", "", teil, flags=re.S)
    return teil.strip()


def aktualisiere(aufgaben, f):
    """Traegt neu geloeste Aufgaben mit Datum ein."""
    heute = datetime.date.today().isoformat()
    for a in aufgaben:
        st = f["aufgaben"].setdefault(a["id"], {})
        if antwort_text(a) and not st.get("geloest"):
            st["geloest"] = heute
            st["punkte"] = a["sterne"]
            f["tage"].setdefault(heute, []).append(a["id"])
    return f


def punkte(f):
    return sum(v.get("punkte", 0) for v in f["aufgaben"].values() if v.get("geloest"))


def stufe(p):
    name, naechste = STUFEN[0][1], None
    for grenze, titel in STUFEN:
        if p >= grenze:
            name = titel
        elif naechste is None:
            naechste = (grenze, titel)
    return name, naechste


def serie(f):
    """Tage am Stueck mit mindestens einer geloesten Aufgabe, bis heute
    oder gestern (heute darf noch offen sein)."""
    tage = {datetime.date.fromisoformat(t) for t, ids in f["tage"].items() if ids}
    d = datetime.date.today()
    if d not in tage:
        d -= datetime.timedelta(days=1)
    n = 0
    while d in tage:
        n += 1
        d -= datetime.timedelta(days=1)
    return n


def fortschritt_anteil(aufgaben, f):
    """Wie vollstaendig das Archiv ist, gemessen an den Daten (archiv.py).
    Abgegebene, noch nicht eingearbeitete Antworten zaehlen schon mit,
    damit sich der Balken beim Abgeben bewegt."""
    st = archiv.stand()
    voll = sum(v["voll"] for v in st.values())
    da = sum(v["da"] for v in st.values())
    for a in aufgaben:
        zustand = f["aufgaben"].get(a["id"], {})
        if not zustand.get("geloest") or zustand.get("eingearbeitet"):
            continue
        s = st.get(a.get("eintrag") or "")
        if not s:
            continue
        if a["art"] == "karteikarte":
            da += sum(z["gewicht"] for z in s["fehlt"] if z["wer"] == "nickii")
        else:
            da += min(a["sterne"], s["voll"] - s["da"])
    return min(da / voll, 1.0) if voll else 1.0


def balken(anteil, breite=24):
    voll = round(anteil * breite)
    return "█" * voll + "░" * (breite - voll)


# ------------------------------------------------------------ Dateien

def schreibe_antwortdatei(a, nummer, gesamt):
    pfad = antwort_pfad(a)
    if os.path.exists(pfad):
        return pfad
    os.makedirs(ANTWORTEN, exist_ok=True)
    sterne = "★" * a["sterne"] + "☆" * (3 - a["sterne"])
    zeilen = [
        f"# Aufgabe {nummer} von {gesamt} · {sterne} · {ARTEN[a['art']]}",
        "",
        f"## {a['titel']}",
        "",
        a["frage"],
        "",
    ]
    if a.get("kontext"):
        zeilen += ["**Was im Archiv steht:**", "", "> " + a["kontext"].replace("\n", "\n> "), ""]
    if a.get("dateien"):
        zeilen += ["**Zum Ansehen:**", ""]
        zeilen += [f"- `{d}`" for d in a["dateien"]]
        zeilen += [""]
    if a.get("felder"):
        zeilen += ["**Was fehlt:**", ""]
        zeilen += [f"- **{fd['label']}:** {fd['hilfe']}" for fd in a["felder"]]
        zeilen += [""]
    if a.get("format"):
        zeilen += [f"**So reicht es:** {a['format']}", ""]
    zeilen += [
        "---",
        "",
        MARKE,
        "",
        f"{HINWEIS_ZEILE} Stichpunkte reichen, Deutsch oder Englisch. Speichern genügt. -->",
        "",
        "",
    ]
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write("\n".join(zeilen))
    return pfad


def schreibe_ueberblick(aufgaben, f):
    p = punkte(f)
    anteil = fortschritt_anteil(aufgaben, f)
    moeglich = p + sum(a["sterne"] for a in aufgaben
                       if not f["aufgaben"].get(a["id"], {}).get("geloest"))
    geloest = [a for a in aufgaben if f["aufgaben"].get(a["id"], {}).get("geloest")]
    name, naechste = stufe(p)
    z = [
        "# Aufgabenheft Archiv schamborski.com",
        "",
        "Jeden Tag eine Aufgabe. Erzeugt von `python3 tools/website.py aufgabe`, "
        "nicht von Hand ändern.",
        "",
        f"**Archiv vollständig:** `{balken(anteil)}` {round(100 * anteil)} %",
        "",
        f"**Stufe:** {name} · **Punkte:** {p} von {moeglich} · "
        f"**Serie:** {serie(f)} Tage · **Gelöst:** {len(geloest)} von {len(aufgaben)}",
        "",
    ]
    if naechste:
        z += [f"Noch {naechste[0] - p} Punkte bis *{naechste[1]}*.", ""]
    z += ["## Aufgaben", ""]
    for n, a in enumerate(aufgaben, start=1):
        st = f["aufgaben"].get(a["id"], {})
        haken = "x" if st.get("geloest") else " "
        extra = " · eingearbeitet" if st.get("eingearbeitet") else ""
        z.append(f"- [{haken}] {n}. {'★' * a['sterne']} {a['titel']} "
                 f"({ARTEN[a['art']]}){extra}")
    with open(UEBERBLICK, "w", encoding="utf-8") as fh:
        fh.write("\n".join(z) + "\n")


def status(aufgaben, f):
    p = punkte(f)
    name, naechste = stufe(p)
    geloest = sum(1 for a in aufgaben if f["aufgaben"].get(a["id"], {}).get("geloest"))
    return {
        "punkte": p,
        "anteil": fortschritt_anteil(aufgaben, f),
        "stufe": name,
        "naechste_stufe": naechste[1] if naechste else None,
        "punkte_bis": (naechste[0] - p) if naechste else 0,
        "serie": serie(f),
        "geloest": geloest,
        "gesamt": len(aufgaben),
    }


def speichere_antwort(aid, text):
    """Schreibt die Antwort unter die Marke der Aufgabendatei."""
    aufgaben = alle_aufgaben()
    a = next((x for x in aufgaben if x["id"] == aid), None)
    if a is None:
        raise KeyError(aid)
    pfad = schreibe_antwortdatei(a, aufgaben.index(a) + 1, len(aufgaben))
    with open(pfad, encoding="utf-8") as fh:
        kopf = fh.read().split(MARKE, 1)[0]
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write(kopf + MARKE + "\n\n" + text.strip() + "\n")
    f = aktualisiere(aufgaben, lade_fortschritt())
    speichere_fortschritt(f)
    schreibe_ueberblick(aufgaben, f)
    return f


def heutige_aufgabe(bonus=False):
    """Aufgabe des Tages, einmal pro Tag festgelegt. Mit bonus die naechste
    offene, wenn die heutige schon geloest ist."""
    aufgaben = alle_aufgaben()
    f = aktualisiere(aufgaben, lade_fortschritt())
    heute = datetime.date.today().isoformat()
    heute_id = f.setdefault("heute", {}).get(heute)
    a = next((x for x in aufgaben if x["id"] == heute_id), None)
    if a is None or (bonus and f["aufgaben"].get(a["id"], {}).get("geloest")):
        _, a = naechste_offene(aufgaben, f)
        if a is not None:
            f["heute"] = {heute: a["id"]}
    speichere_fortschritt(f)
    schreibe_ueberblick(aufgaben, f)
    return aufgaben, f, a


# ------------------------------------------------------------ Befehl

def naechste_offene(aufgaben, f, ausser=()):
    for n, a in enumerate(aufgaben, start=1):
        if not f["aufgaben"].get(a["id"], {}).get("geloest") and a["id"] not in ausser:
            return n, a
    return None, None


def cmd_aufgabe(argv):
    aufgaben = alle_aufgaben()
    f = aktualisiere(aufgaben, lade_fortschritt())
    heute = datetime.date.today().isoformat()
    gesamt = len(aufgaben)

    if "--eingearbeitet" in argv:
        try:
            aid = argv[argv.index("--eingearbeitet") + 1]
        except IndexError:
            print("Welche Aufgabe? Beispiel: aufgabe --eingearbeitet audit-daad")
            return 1
        f["aufgaben"].setdefault(aid, {})["eingearbeitet"] = heute
        speichere_fortschritt(f)
        schreibe_ueberblick(aufgaben, f)
        print(f"{aid} als eingearbeitet markiert.")
        return 0

    if "--eingang" in argv:
        offen = [a for a in aufgaben
                 if f["aufgaben"].get(a["id"], {}).get("geloest")
                 and not f["aufgaben"][a["id"]].get("eingearbeitet")]
        speichere_fortschritt(f)
        if not offen:
            print("Nichts im Eingang. Alle Antworten sind eingearbeitet.")
            return 0
        print(f"{len(offen)} Antworten warten darauf, eingearbeitet zu werden:\n")
        for a in offen:
            print(f"- {a['id']}: {a['titel']}")
            print(f"  {os.path.relpath(antwort_pfad(a), ROOT)}")
        return 0

    speichere_fortschritt(f)
    schreibe_ueberblick(aufgaben, f)
    if "--heft" in argv:
        with open(UEBERBLICK, encoding="utf-8") as fh:
            print(fh.read())
        return 0

    # Aufgabe des Tages: einmal pro Tag festgelegt, damit sie nicht
    # wechselt, wenn der Befehl mehrfach laeuft.
    heute_id = f.setdefault("heute", {}).get(heute)
    bonus = "--bonus" in argv
    aufgabe = next((a for a in aufgaben if a["id"] == heute_id), None)
    if aufgabe is None or bonus and f["aufgaben"].get(aufgabe["id"], {}).get("geloest"):
        n, aufgabe = naechste_offene(aufgaben, f)
        if aufgabe is None:
            print("Das Heft ist leer. Das Archiv ist vollständig. 🎉")
            return 0
        f["heute"] = {heute: aufgabe["id"]}
        speichere_fortschritt(f)
    n = aufgaben.index(aufgabe) + 1
    pfad = schreibe_antwortdatei(aufgabe, n, gesamt)

    p = punkte(f)
    anteil = fortschritt_anteil(aufgaben, f)
    name, naechste = stufe(p)
    geloest_heute = bool(f["aufgaben"].get(aufgabe["id"], {}).get("geloest"))

    print(f"Archiv  {balken(anteil)}  {round(100 * anteil)} %")
    print(f"Stufe   {name}  ·  {p} Punkte  ·  Serie {serie(f)} Tage")
    if naechste:
        print(f"        noch {naechste[0] - p} Punkte bis {naechste[1]}")
    print()
    if geloest_heute:
        print(f"Heute schon gelöst: {aufgabe['titel']}  ✓")
        print("Lust auf mehr?  python3 tools/website.py aufgabe --bonus")
        return 0
    sterne = "★" * aufgabe["sterne"] + "☆" * (3 - aufgabe["sterne"])
    print(f"Aufgabe {n} von {gesamt}  {sterne}  {ARTEN[aufgabe['art']]}")
    print(f"  {aufgabe['titel']}")
    print()
    print(f"  {aufgabe['frage']}")
    print()
    print(f"Antworten in: {os.path.relpath(pfad, ROOT)}")
    return 0


def heutige_datei():
    """Fuer den taeglichen Ausloeser: Pfad und Titel der heutigen Aufgabe."""
    aufgaben = alle_aufgaben()
    f = aktualisiere(aufgaben, lade_fortschritt())
    heute = datetime.date.today().isoformat()
    heute_id = f.get("heute", {}).get(heute)
    a = next((x for x in aufgaben if x["id"] == heute_id), None)
    if a is None:
        _, a = naechste_offene(aufgaben, f)
        if a is None:
            return None, None
        f["heute"] = {heute: a["id"]}
    speichere_fortschritt(f)
    schreibe_ueberblick(aufgaben, f)
    return schreibe_antwortdatei(a, aufgaben.index(a) + 1, len(aufgaben)), a["titel"]
