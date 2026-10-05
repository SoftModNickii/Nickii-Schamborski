"""
archiv.py - was ein vollstaendiger Archiveintrag braucht.

Die Website zeigt nur einen Teil dessen, was ein Archiv festhalten sollte.
Dieses Modul beschreibt je Art von Eintrag (Arbeit, Ausstellung, Vortrag,
Auszeichnung, Taetigkeit, Presse) die Angaben, die dazugehoeren, und misst
an data/content.json, was davon schon da ist.

    python3 tools/website.py archiv          Stand des Archivs, groesste Luecken
    python3 tools/website.py archiv <id>     Karteikarte eines Eintrags

Das Aufgabenheft baut seine Karteikarten aus denselben Feldern. Kommt ein
neuer Eintrag dazu oder waechst das Schema, entstehen die Aufgaben von
selbst.

Jedes Feld hat einen Zustaendigen:
    nickii   kann nur Nickii wissen, landet auf der Karteikarte im Heft
    aufgabe  hat im Heft eine eigene Aufgabe (Texte, Bilder, Themen)
    claude   laesst sich recherchieren oder aus vorhandenen Angaben ableiten

Texte, die Claude formuliert hat, bekommen "text_status": "entwurf". Erst
wenn Nickii sie im Heft bestaetigt oder umgeschrieben hat, wird das Feld
entfernt. Nickiis eigene Texte tragen das Feld nicht.

Weiss Nickii etwas nicht oder gibt es etwas nicht, kommt der Schluessel des
Felds in die Liste "archive_na" des Eintrags. Dann zaehlt das Feld als
geklaert und wird nicht wieder gefragt.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "data", "content.json")
SITE = os.path.join(ROOT, "data", "site.json")

ARTEN = {
    "arbeit": "Arbeiten",
    "ausstellung": "Ausstellungen und Festivals",
    "vortrag": "Vorträge und Workshops",
    "auszeichnung": "Stipendien und Preise",
    "taetigkeit": "Tätigkeiten und Ausbildung",
    "presse": "Presse und Publikationen",
}


def kartenart(item):
    cats = item.get("categories") or []
    if "works" in cats:
        return "arbeit"
    if "press" in cats:
        return "presse"
    if item.get("type") in ("Lecture", "Workshop"):
        return "vortrag"
    if "shows" in cats:
        return "ausstellung"
    if "fellowships" in cats:
        return "auszeichnung"
    return "taetigkeit"


# ------------------------------------------------------------------ Pruefer

def hat(key):
    return lambda item, ctx: bool(item.get(key))


def text_ab(key, laenge):
    return lambda item, ctx: len(item.get(key) or "") >= laenge


def ist_video(item, ctx=None):
    return "video" in (item.get("type") or "").lower() or "video" in (item.get("specs") or "").lower()


def hat_dauer(item, ctx):
    return bool(item.get("duration") or re.search(r"\d{1,3}:\d{2}", item.get("specs") or ""))


def hat_sprache(item, ctx):
    return bool(item.get("language") or re.search(
        r"english|german|deutsch|englisch|no dialogue|ohne sprache|subtitle", item.get("specs") or "", re.I))


def hat_mitwirkende(item, ctx):
    specs = item.get("specs") or ""
    return bool(item.get("credits") or item.get("collaborators")
                or re.search(r"[a-zäöü]: ", specs) or "collaboration" in specs.lower())


def hat_auflage(item, ctx):
    return bool(item.get("edition") or "edition" in f"{item.get('type')} {item.get('specs')}".lower())


def arbeit_gezeigt(item, ctx):
    return "shows" in (item.get("categories") or []) or item["id"] in ctx["gezeigt"]


def schau_verbunden(item, ctx):
    return item["id"] in ctx["verbunden"]


def hat_fundstelle(item, ctx):
    return bool(item.get("link") or item.get("pdfs"))


def hat_autor(item, ctx):
    return bool(item.get("author") or (item.get("csl") or {}).get("author"))


def hat_archivkopie(item, ctx):
    return bool(item.get("archive_url") or item.get("pdfs"))


def nicht_solo(item, ctx=None):
    return "solo" not in (item.get("type") or "").lower()


def keine_vermittlung(item, ctx=None):
    return item.get("type") != "Mediation"


def kein_profil(item, ctx=None):
    return item.get("press_group") != "institutional_profile" and item.get("type") != "Catalog"


# ------------------------------------------------------------------- Schema
# (schluessel, bezeichnung, hilfe, gewicht, wer, pruefer, bedingung)

def F(key, label, hilfe, gewicht, wer, test, wenn=None):
    return {"key": key, "label": label, "hilfe": hilfe, "gewicht": gewicht,
            "wer": wer, "test": test, "wenn": wenn}


INTERN = ("Steht nicht auf der Webseite, aber im öffentlichen GitHub-Repository. "
          "Also keine Adressen und keine Passwörter.")

SCHEMA = {
    "arbeit": [
        F("description", "Werktext Englisch", "", 3, "aufgabe", text_ab("description", 150)),
        F("description_de", "Werktext Deutsch", "", 2, "aufgabe", hat("description_de")),
        F("image", "Titelbild", "", 3, "aufgabe", hat("image")),
        F("images", "Mindestens drei Bilder", "", 1, "aufgabe",
          lambda i, c: len(i.get("images") or []) >= 3),
        F("image_alt", "Bildbeschreibung des Titelbilds", "", 1, "aufgabe", hat("image_alt")),
        F("image_alts", "Bildbeschreibung jedes Bilds", "", 1, "claude",
          lambda i, c: all(p in (i.get("image_alts") or {}) for p in i.get("images") or [])),
        F("tags", "Themen", "", 1, "aufgabe", hat("tags")),
        F("specs", "Technische Angaben", "Medium, Format, Maße, Material.", 2, "nickii", hat("specs")),
        F("duration", "Dauer", "In Minuten und Sekunden, zum Beispiel 13:24. Bei Loops: 'Loop'.",
          2, "nickii", hat_dauer, ist_video),
        F("language", "Sprache", "Gesprochene Sprache und Untertitel. Oder: 'ohne Sprache'.",
          1, "nickii", hat_sprache, ist_video),
        F("video_link", "Link zum Ansehen",
          "Vimeo oder YouTube. Ein Passwort bitte nicht hier hinschreiben, nur 'mit Passwort'.",
          2, "nickii", hat("video_link"), ist_video),
        F("credits", "Mitwirkende",
          "Kamera, Ton, Darsteller:innen, Bau, Hilfe. Je Zeile: Aufgabe, Name. Oder: 'allein gemacht'.",
          1, "nickii", hat_mitwirkende),
        F("exhibited_at", "Ausstellungsgeschichte",
          "Wo war die Arbeit zu sehen? Je Zeile: Ort, Titel der Ausstellung, Jahr. "
          "Auch Stationen, die noch nicht im Archiv sind. Oder: 'noch nie gezeigt'.",
          3, "nickii", arbeit_gezeigt),
        F("image_credit", "Bildnachweis",
          "Wer hat die Bilder gemacht? 'eigene Stills', 'eigene Fotos' oder Name je Bild.",
          2, "nickii", hat("image_credit"), hat("image")),
        F("edition", "Auflage und Verbleib",
          "Zum Beispiel 'Auflage 5 + 2 AP', 'Unikat, im Atelier', 'Sammlung …', 'zerstört'.",
          1, "nickii", hat_auflage),
        F("archive_location", "Wo liegt das Original?",
          "Masterdatei oder Objekt: welche Festplatte, welcher Ordner, welches Lager. " + INTERN,
          1, "nickii", hat("archive_location")),
    ],
    "ausstellung": [
        F("institution", "Ort / Institution", "Name des Hauses oder Festivals.", 3, "nickii", hat("institution")),
        F("date_start", "Zeitraum", "Von–bis, so genau du es weißt, zum Beispiel 08.08.–29.08.2021.",
          2, "nickii", hat("date_start")),
        F("city", "Stadt und Land", "", 1, "claude", hat("city")),
        F("exhibited_works", "Gezeigte Arbeiten",
          "Welche deiner Arbeiten waren zu sehen? Alle nennen, gern mit einem Satz, wie sie gezeigt wurden.",
          3, "nickii", schau_verbunden, keine_vermittlung),
        F("curators", "Kuratiert von", "Namen, oder 'weiß nicht'.", 1, "nickii", hat("curators")),
        F("co_artists", "Mit ausgestellt",
          "Andere Künstler:innen. Bei großen Festivals reicht 'viele'.", 1, "nickii",
          hat("co_artists"), nicht_solo),
        F("link", "Webseite der Ausstellung", "Adresse, oder 'gibt es nicht (mehr)'.", 1, "nickii", hat("link")),
        F("description", "Kurzbeschreibung",
          "Ein, zwei Sätze: Was war das für eine Ausstellung, worum ging es?",
          1, "nickii", text_ab("description", 120)),
        F("image", "Bild", "", 2, "aufgabe", hat("image")),
        F("image_credit", "Bildnachweis", "Wer hat fotografiert? Oder: 'eigenes Foto', 'Plakat der Institution'.",
          1, "nickii", hat("image_credit"), hat("image")),
    ],
    "vortrag": [
        F("institution", "Ort / Institution", "Wo fand es statt?", 3, "nickii", hat("institution")),
        F("date_start", "Datum", "Tag oder Zeitraum, so genau du es weißt.", 2, "nickii", hat("date_start")),
        F("host", "Rahmen", "In welchem Kurs oder Programm, auf wessen Einladung, für wen?",
          1, "nickii", hat("host")),
        F("description", "Inhalt", "", 2, "aufgabe", text_ab("description", 150)),
        F("materials", "Folien, Leseliste oder Aufnahme", "", 1, "aufgabe",
          lambda i, c: bool(i.get("materials") or i.get("pdfs"))),
        F("image", "Bild", "", 1, "aufgabe", hat("image")),
    ],
    "auszeichnung": [
        F("institution", "Vergeben von", "Stiftung, Ministerium, Hochschule.", 3, "nickii", hat("institution")),
        F("date_start", "Zeitraum", "Laufzeit von–bis oder Datum der Verleihung.", 1, "nickii", hat("date_start")),
        F("description", "Wofür",
          "Ein Satz: Wofür gab es die Förderung, und was hat sie ermöglicht?",
          1, "nickii", text_ab("description", 100)),
        F("link", "Webseite", "", 1, "claude", hat("link")),
        F("image", "Bild", "", 1, "aufgabe", hat("image")),
    ],
    "taetigkeit": [
        F("institution", "Ort / Institution", "Wo?", 3, "nickii", hat("institution")),
        F("date_start", "Zeitraum", "Monat und Jahr von–bis.", 1, "nickii", hat("date_start")),
        F("description", "Was hast du dort gemacht?",
          "Zwei, drei Sätze: Aufgabe, mit wem, was daraus entstanden ist.",
          2, "nickii", text_ab("description", 120)),
        F("link", "Webseite", "", 1, "claude", hat("link")),
        F("image", "Bild", "", 1, "aufgabe", hat("image")),
    ],
    "presse": [
        F("link", "Fundstelle", "", 3, "claude", hat_fundstelle),
        F("author", "Autor:in", "", 2, "claude", hat_autor, kein_profil),
        F("sort_date", "Erscheinungsdatum", "", 1, "claude", hat("sort_date")),
        F("archive_url", "Archivkopie", "Wayback Machine oder PDF, falls die Seite verschwindet.",
          2, "claude", hat_archivkopie),
    ],
}


# Gilt fuer jede Art von Eintrag: Texte, die Claude geschrieben hat, tragen
# "text_status": "entwurf", bis Nickii sie gegengelesen hat.
for _felder in SCHEMA.values():
    _felder.append(F("text_status", "Text von Nickii gegengelesen", "", 1, "aufgabe",
                     lambda i, c: i.get("text_status") != "entwurf"))


# ------------------------------------------------------------------ Messung

def lade():
    with open(CONTENT, encoding="utf-8") as fh:
        items = json.load(fh)
    with open(SITE, encoding="utf-8") as fh:
        site = json.load(fh)
    return items, site


def kontext(items):
    """Verbindungen zwischen Arbeiten und Ausstellungen, in beide Richtungen."""
    gezeigt, verbunden = set(), set()
    for i in items:
        if i.get("exhibited_at"):
            gezeigt.add(i["id"])
            verbunden.update(i["exhibited_at"])
        if i.get("exhibited_works"):
            verbunden.add(i["id"])
            gezeigt.update(i["exhibited_works"])
    return {"gezeigt": gezeigt, "verbunden": verbunden}


def karte(item, ctx):
    """Alle Felder des Eintrags mit ihrem Zustand."""
    geklaert = set(item.get("archive_na") or [])
    zeilen = []
    for f in SCHEMA[kartenart(item)]:
        if f["wenn"] and not f["wenn"](item, ctx):
            continue
        zeilen.append({**f, "da": f["test"](item, ctx) or f["key"] in geklaert,
                       "entfaellt": f["key"] in geklaert})
    return zeilen


def stand(items=None):
    """Je Eintrag: Art, Gewicht gesamt und vorhanden, fehlende Felder."""
    if items is None:
        items, _ = lade()
    ctx = kontext(items)
    out = {}
    for i in items:
        zeilen = karte(i, ctx)
        out[i["id"]] = {
            "art": kartenart(i),
            "voll": sum(z["gewicht"] for z in zeilen),
            "da": sum(z["gewicht"] for z in zeilen if z["da"]),
            "fehlt": [z for z in zeilen if not z["da"]],
            "zeilen": zeilen,
        }
    return out


def anteil(st, ids=None):
    voll = sum(v["voll"] for k, v in st.items() if ids is None or k in ids)
    da = sum(v["da"] for k, v in st.items() if ids is None or k in ids)
    return da / voll if voll else 1.0


# ------------------------------------------------------------------- Befehl

def cmd_archiv(argv):
    items, site = lade()
    by_id = {i["id"]: i for i in items}
    st = stand(items)

    if argv and not argv[0].startswith("-"):
        item = by_id.get(argv[0])
        if not item:
            print(f"Den Eintrag '{argv[0]}' gibt es nicht.")
            return 1
        s = st[item["id"]]
        print(f"{item['title']} ({item['year']})  ·  {ARTEN[s['art']]}  ·  "
              f"{round(100 * s['da'] / s['voll'])} % vollständig\n")
        for z in s["zeilen"]:
            zeichen = "–" if z["entfaellt"] else "✓" if z["da"] else " "
            wer = "" if z["da"] else f"   ({z['wer']})"
            print(f"  [{zeichen}] {z['label']}{wer}")
        return 0

    print(f"Archiv zu {round(100 * anteil(st))} % vollständig, {len(items)} Einträge.\n")
    for art, name in ARTEN.items():
        ids = {k for k, v in st.items() if v["art"] == art}
        fertig = sum(1 for k in ids if not st[k]["fehlt"])
        print(f"  {round(100 * anteil(st, ids)):3d} %  {name}: {len(ids)} Einträge, {fertig} vollständig")

    print("\nWas am häufigsten fehlt:")
    zaehler = {}
    for v in st.values():
        for z in v["fehlt"]:
            key = (ARTEN[v["art"]], z["label"], z["wer"])
            zaehler[key] = zaehler.get(key, 0) + 1
    for (art, label, wer), n in sorted(zaehler.items(), key=lambda kv: -kv[1])[:14]:
        print(f"  {n:3d} x  {label}  ({art}, {wer})")

    print("\nDie zehn Einträge mit den größten Lücken:")
    schwach = sorted(st.items(), key=lambda kv: kv[1]["da"] / kv[1]["voll"])[:10]
    for iid, v in schwach:
        fehlt = ", ".join(z["label"] for z in v["fehlt"])
        print(f"  {round(100 * v['da'] / v['voll']):3d} %  {by_id[iid]['title']} ({by_id[iid]['year']}): {fehlt}")

    claude = {}
    for iid, v in st.items():
        for z in v["fehlt"]:
            if z["wer"] == "claude":
                claude.setdefault(z["label"], []).append(iid)
    if claude:
        print("\nOhne Nickii zu klären (Recherche, Ableitung):")
        for label, ids in sorted(claude.items(), key=lambda kv: -len(kv[1])):
            print(f"  {len(ids):3d} x  {label}")
    print("\nEin einzelner Eintrag: python3 tools/website.py archiv <id>")
    return 0
