#!/usr/bin/env python3
"""
website.py - Wartungswerkzeug fuer schamborski.com

Alle Befehle sind von der Repo-Wurzel aus zu starten:

    python3 tools/website.py check      Prueft content.json und alle Bildpfade
    python3 tools/website.py needs      Schreibt IMAGES-NEEDED.md (Bilder-Checkliste)
    python3 tools/website.py albums     Legt in Fotos je Eintrag ein Album mit der Auswahl an
    python3 tools/website.py originals  Ersetzt Fotos-Vorschauen durch die Originale
    python3 tools/website.py intake     Holt Bilder aus _inbox/<slug>/ in die Seite
    python3 tools/website.py serve      Startet lokale Vorschau auf Port 8000

"intake" ist der Bilder-Workflow: Ordner _inbox/<item-id>/ anlegen, Fotos
hineinlegen (beliebige Namen), Befehl starten. Die Bilder werden umbenannt,
nach assets/images/<item-id>/ verschoben und in content.json eingetragen.
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "data", "content.json")
BACKUP_DIR = os.path.join(ROOT, "data", ".backups")
INBOX = os.path.join(ROOT, "_inbox")
IMAGE_ROOT = os.path.join(ROOT, "assets", "images")
NEEDS_FILE = os.path.join(ROOT, "IMAGES-NEEDED.md")
VENV_OSXPHOTOS = os.path.join(ROOT, "tools", ".venv", "bin", "osxphotos")

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
# Was direkt aus Fotos vom iPhone kommt. Wird beim Einlesen zu JPEG gewandelt,
# weil Browser HEIC nicht zuverlaessig anzeigen.
# Auch Rohdaten aus der Kamera. sips wandelt sie, Browser koennen sie nicht.
CONVERT_EXT = {".heic", ".heif", ".arw", ".cr2", ".cr3", ".nef", ".dng", ".raf", ".orf"}
INBOX_EXT = IMAGE_EXT | CONVERT_EXT
# Breite, auf die grosse Aufnahmen heruntergerechnet werden.
MAX_WIDTH = 2400
# Kuerzeste zulaessige lange Kante. Wer in Fotos ein Bild einfach herauszieht,
# bekommt haeufig nur eine Vorschau von 360 bis 1024 Pixel statt des Originals.
# Solche Dateien sehen auf der Seite matschig aus und werden abgewiesen.
MIN_LONG_EDGE = 1400
KNOWN_CATEGORIES = {"works", "shows", "practice", "education", "fellowships", "press"}

# Felder, die jedes Item laut bestehendem Schema hat.
REQUIRED_FIELDS = [
    "id", "title", "year", "sort_year", "categories", "type",
    "specs", "institution", "link", "image", "images", "related_links",
]


# ---------------------------------------------------------------- Hilfsmittel

def load():
    with open(CONTENT, encoding="utf-8") as fh:
        return json.load(fh)


def save(items):
    """Schreibt content.json atomar und legt vorher eine Sicherung an.

    Die Sicherungen liegen in data/.backups/ und damit ausserhalb von Git,
    damit sie den Diff eines Commits nicht aufblaehen.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(CONTENT, os.path.join(BACKUP_DIR, f"content-{stamp}.json"))
    # nur die letzten zehn Staende aufheben
    old_backups = sorted(f for f in os.listdir(BACKUP_DIR) if f.endswith(".json"))
    for stale in old_backups[:-10]:
        os.remove(os.path.join(BACKUP_DIR, stale))
    tmp = CONTENT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(items, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    json.load(open(tmp, encoding="utf-8"))  # Gegenprobe vor dem Ersetzen
    os.replace(tmp, CONTENT)


def resolve(path):
    """Findet die Datei zu einem content.json-Pfad.

    Beruecksichtigt URL-Encoding (%20) und die beiden Unicode-Formen, in
    denen macOS und Git Umlaute ablegen. Gibt den Pfad auf der Platte
    zurueck oder None.
    """
    if not path or path.startswith("http"):
        return path
    for cand in dict.fromkeys([path, urllib.parse.unquote(path)]):
        for form in ("NFC", "NFD"):
            full = os.path.join(ROOT, unicodedata.normalize(form, cand))
            if os.path.exists(full):
                return cand
    return None


def asset_paths(item):
    """Alle Datei-Referenzen eines Items als (feldname, pfad)."""
    out = []
    if item.get("image"):
        out.append(("image", item["image"]))
    for i, p in enumerate(item.get("images") or []):
        out.append((f"images[{i}]", p))
    for i, p in enumerate(item.get("pdfs") or []):
        out.append((f"pdfs[{i}]", p))
    return out


def long_edge(path):
    """Laengste Bildkante in Pixeln, oder None wenn nicht ermittelbar."""
    if not shutil.which("sips"):
        return None
    try:
        out = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
            capture_output=True, text=True, check=True,
        ).stdout
    except Exception:
        return None
    w = h = None
    for line in out.splitlines():
        if "pixelWidth:" in line:
            w = int(line.split(":")[1].strip())
        elif "pixelHeight:" in line:
            h = int(line.split(":")[1].strip())
    return max(w, h) if w and h else None


def prepare_image(src, dest):
    """Legt src als web-taugliches Bild unter dest ab.

    HEIC wird zu JPEG gewandelt, zu breite Aufnahmen werden verkleinert.
    Beides erledigt sips, das auf jedem Mac vorhanden ist. Fehlt sips oder
    schlaegt es fehl, wird die Datei unveraendert verschoben.
    """
    ext = os.path.splitext(src)[1].lower()
    needs_convert = ext in CONVERT_EXT
    if not shutil.which("sips"):
        shutil.move(src, dest)
        return "unveraendert (sips nicht gefunden)"

    width = None
    try:
        out = subprocess.run(
            ["sips", "-g", "pixelWidth", src],
            capture_output=True, text=True, check=True,
        ).stdout
        for line in out.splitlines():
            if "pixelWidth:" in line:
                width = int(line.split(":")[1].strip())
    except Exception:
        pass

    cmd = ["sips"]
    note = []
    if needs_convert:
        cmd += ["-s", "format", "jpeg", "-s", "formatOptions", "85"]
        note.append("HEIC zu JPEG")
    if width and width > MAX_WIDTH:
        cmd += ["--resampleWidth", str(MAX_WIDTH)]
        note.append(f"{width} auf {MAX_WIDTH} px verkleinert")

    if not note:
        shutil.move(src, dest)
        return "unveraendert"

    cmd += [src, "--out", dest]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        os.remove(src)
        return ", ".join(note)
    except Exception:
        shutil.move(src, dest)
        return "unveraendert (sips fehlgeschlagen)"


def slugify(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text


# -------------------------------------------------------------------- check

def tracked_files():
    """Pfade, wie Git sie speichert. Genau die liefert GitHub Pages aus."""
    try:
        out = subprocess.run(
            ["git", "-C", ROOT, "ls-files", "-z"],
            capture_output=True, check=True,
        ).stdout
    except Exception:
        return None
    return {
        unicodedata.normalize("NFC", p.decode("utf-8"))
        for p in out.split(b"\0") if p
    }


def cmd_check(argv):
    items = load()
    errors, warnings = [], []

    # Der Abgleich gegen Git faengt zwei Fallen, die lokal unsichtbar bleiben:
    # macOS ignoriert Gross- und Kleinschreibung, der Server von GitHub nicht,
    # und eine Datei, die nie eingecheckt wurde, existiert live schlicht nicht.
    tracked = tracked_files()
    lower = {t.lower(): t for t in tracked} if tracked else {}
    ids = Counter(i.get("id") for i in items)

    for dupe, n in ids.items():
        if n > 1:
            errors.append(f"Doppelte id '{dupe}' ({n}x)")

    known_ids = set(ids)

    for item in items:
        iid = item.get("id", "<ohne id>")

        for field in REQUIRED_FIELDS:
            if field not in item:
                errors.append(f"{iid}: Feld '{field}' fehlt")

        # Typen, auf die sich all.html ungeprueft verlaesst. Ein String statt
        # einer Liste laesst die Galerie ueber die Buchstaben laufen.
        for field in ("categories", "images", "related_links", "pdfs",
                      "tags", "exhibited_at", "exhibited_works"):
            val = item.get(field)
            if val is not None and not isinstance(val, list):
                errors.append(
                    f"{iid}: '{field}' muss eine Liste sein, ist aber "
                    f"{type(val).__name__} ({val!r})"
                )
        if not isinstance(item.get("year"), str):
            errors.append(f"{iid}: 'year' muss ein String sein, ist {item.get('year')!r}")

        for field, path in asset_paths(item):
            if resolve(path) is None:
                errors.append(f"{iid}: {field} zeigt ins Leere -> {path}")
            elif tracked is not None and not path.startswith("http"):
                real = unicodedata.normalize("NFC", urllib.parse.unquote(path))
                if real not in tracked:
                    if real.lower() in lower:
                        errors.append(
                            f"{iid}: {field} Gross-/Kleinschreibung weicht ab, "
                            f"live ein 404 -> {path} statt {lower[real.lower()]}"
                        )
                    else:
                        errors.append(
                            f"{iid}: {field} liegt lokal, ist aber nicht in Git, "
                            f"live ein 404 -> {path}"
                        )

        cats = item.get("categories") or []
        if not cats:
            warnings.append(f"{iid}: keine Kategorie, taucht nur unter 'All' auf")
        for cat in cats:
            if cat not in KNOWN_CATEGORIES:
                warnings.append(f"{iid}: unbekannte Kategorie '{cat}'")

        # Presseeintraege mit Link und ohne Bild sind Absicht: all.html rendert
        # sie als Link-Vorschaukachel mit Favicon statt als Bildkachel.
        is_link_preview = "press" in cats and item.get("link") and not item.get("image")
        if not item.get("image") and not is_link_preview:
            warnings.append(f"{iid}: kein Titelbild, Kachel bleibt leer")
        if not (item.get("description") or "").strip():
            warnings.append(f"{iid}: keine Beschreibung")
        if not (item.get("type") or "").strip():
            warnings.append(f"{iid}: kein Typ")

        # Das Raster sortiert nach 'year'. Weicht sort_year davon ab,
        # steht das Item an einer anderen Stelle als erwartet.
        year = str(item.get("year") or "")
        head = year.split("/")[0].split("-")[0]
        if head.isdigit() and item.get("sort_year") not in (None, int(head)):
            warnings.append(
                f"{iid}: sort_year {item['sort_year']} passt nicht zu year {year}"
            )
        if not head.isdigit():
            errors.append(f"{iid}: year '{year}' ist nicht sortierbar")

        for field in ("exhibited_at", "exhibited_works", "related_works"):
            for ref in item.get(field) or []:
                if ref not in known_ids:
                    warnings.append(f"{iid}: {field} verweist auf unbekanntes '{ref}'")

    # Bildordner ohne zugehoeriges Item
    used_dirs = set()
    for item in items:
        for _, path in asset_paths(item):
            r = resolve(path)
            if r and not r.startswith("http"):
                used_dirs.add(os.path.dirname(urllib.parse.unquote(r)))
    if os.path.isdir(IMAGE_ROOT):
        for name in sorted(os.listdir(IMAGE_ROOT)):
            d = os.path.join(IMAGE_ROOT, name)
            rel = os.path.relpath(d, ROOT)
            if not os.path.isdir(d):
                continue
            has_images = any(
                os.path.splitext(f)[1].lower() in IMAGE_EXT for f in os.listdir(d)
            )
            if not has_images:
                continue
            if name in known_ids and rel not in used_dirs:
                warnings.append(f"Ordner '{rel}' gehoert zu '{name}', wird aber nicht verlinkt")
            elif name.startswith("new-entry-") and name not in known_ids:
                warnings.append(f"Ordner '{rel}' gehoert zu keinem Eintrag mehr")

    print(f"{len(items)} Eintraege geprueft.")
    print(f"\nFEHLER ({len(errors)}) - bricht die Seite sichtbar:")
    for e in errors or ["  keine"]:
        print(f"  {e}" if e != "  keine" else e)
    print(f"\nHINWEISE ({len(warnings)}) - unvollstaendig, aber nicht kaputt:")
    for w in warnings or ["  keine"]:
        print(f"  {w}" if w != "  keine" else w)
    return 1 if errors else 0


# -------------------------------------------------------------------- needs

def cmd_needs(argv):
    """Schreibt eine Checkliste: welches Item braucht noch welche Bilder."""
    items = load()
    by_id = {i["id"]: i for i in items}

    lines = [
        "# Bilder-Checkliste",
        "",
        "Automatisch erzeugt mit `python3 tools/website.py needs`. Nicht von Hand pflegen.",
        "",
        "## So laeuft die Uebergabe",
        "",
        "1. Ordner `_inbox/<item-id>/` anlegen (die id steht unten bei jedem Punkt).",
        "2. Fotos hineinlegen. Die Dateinamen sind egal.",
        "3. Die gewuenschte Reihenfolge ueber eine fuehrende Zahl steuern:",
        "   `1-hero.jpg`, `2-detail.jpg`, `3-install.jpg`.",
        "4. `python3 tools/website.py intake` starten.",
        "5. `python3 tools/website.py check` starten und das Ergebnis pruefen.",
        "",
        "Das erste Bild eines Items wird zum Titelbild der Kachel.",
        "",
    ]

    def gallery_size(item):
        """Zahl der tatsaechlich vorhandenen, verschiedenen Bilder."""
        seen = set()
        for field, path in asset_paths(item):
            if field.startswith("pdfs"):
                continue
            r = resolve(path)
            if r and not r.startswith("http"):
                seen.add(os.path.normpath(urllib.parse.unquote(r)))
        return len(seen)

    def needs_own_image(item):
        """Presseeintraege mit Link rendern als Link-Vorschau und brauchen keins."""
        cats = item.get("categories") or []
        if "press" in cats and item.get("link"):
            return False
        return True

    # 1. Items ohne jedes Bild
    no_image = [i for i in items if not i.get("image") and needs_own_image(i)]
    # 2. Items mit kaputten Referenzen
    broken = defaultdict(list)
    for item in items:
        for field, path in asset_paths(item):
            if resolve(path) is None:
                broken[item["id"]].append(path)
    # 3. Items mit genau einem Bild - Galerie waere besser
    thin = [i for i in items if gallery_size(i) == 1 and needs_own_image(i)]

    def block(title, entries, hint):
        lines.append(f"## {title}")
        lines.append("")
        if not entries:
            lines.append("Nichts offen.")
            lines.append("")
            return
        lines.append(hint)
        lines.append("")
        for item in entries:
            lines.append(f"- [ ] **{item['title']}** ({item['year']})")
            lines.append(f"      Ablage: `_inbox/{item['id']}/`")
            if broken.get(item["id"]):
                for p in broken[item["id"]]:
                    lines.append(f"      fehlt bisher: `{p}`")
            lines.append("")

    block(
        "Ohne Titelbild",
        no_image,
        "Diese Kacheln bleiben im Raster grau. Jeweils mindestens ein Bild noetig.",
    )
    block(
        "Mit kaputten Verweisen",
        [by_id[k] for k in broken if by_id[k].get("image")],
        "Hier verweist content.json auf Dateien, die es nicht gibt.",
    )
    block(
        "Nur ein einziges Bild",
        thin,
        "Funktioniert, aber die Detailansicht zeigt keine Galerie. Weitere Bilder waeren gut.",
    )

    # Bilder, die schon im Repo liegen, aber von keinem Eintrag verlinkt werden
    used = set()
    for item in items:
        for _, path in asset_paths(item):
            r = resolve(path)
            if r and not r.startswith("http"):
                used.add(os.path.normpath(urllib.parse.unquote(r)))
    unused = defaultdict(list)
    for dirpath, _dirs, files in os.walk(IMAGE_ROOT):
        for f in files:
            if os.path.splitext(f)[1].lower() not in IMAGE_EXT:
                continue
            rel = os.path.relpath(os.path.join(dirpath, f), ROOT)
            if os.path.normpath(rel) not in used:
                unused[os.path.relpath(dirpath, ROOT)].append(f)

    lines.append("## Schon im Repo, aber nirgends eingebunden")
    lines.append("")
    if not unused:
        lines.append("Nichts.")
        lines.append("")
    else:
        lines.append(
            "Diese Dateien liegen bereits im Repo, werden aber von keinem Eintrag "
            "verlinkt. Entweder einbinden oder loeschen."
        )
        lines.append("")
        for folder in sorted(unused):
            lines.append(f"- `{folder}/` ({len(unused[folder])} Dateien)")
        lines.append("")

    # Leere Ablageordner entfernen, die zu keinem Eintrag mehr passen,
    # etwa nachdem eine id umbenannt wurde.
    stale = []
    if os.path.isdir(INBOX):
        for name in sorted(os.listdir(INBOX)):
            d = os.path.join(INBOX, name)
            if not os.path.isdir(d) or name.startswith("."):
                continue
            if name in by_id and any(i["id"] == name for i in no_image):
                continue
            leftovers = [f for f in os.listdir(d) if not f.startswith(".")]
            if leftovers:
                continue  # nie etwas wegwerfen, worin noch Dateien liegen
            os.rmdir(d)
            stale.append(name)

    # Beschriftete Ablageordner vorbereiten, damit die Uebergabe eindeutig ist
    prepared = []
    for item in no_image:
        d = os.path.join(INBOX, item["id"])
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
            prepared.append(item["id"])

    with open(NEEDS_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"Geschrieben: {os.path.relpath(NEEDS_FILE, ROOT)}")
    print(f"  ohne Titelbild: {len(no_image)}")
    print(f"  kaputte Verweise: {len(broken)}")
    print(f"  nur ein Bild: {len(thin)}")
    print(f"  ungenutzte Dateien im Repo: {sum(len(v) for v in unused.values())}")
    if stale:
        print(f"  leere Altordner entfernt: {', '.join(stale)}")
    if prepared:
        print(f"\nAblageordner angelegt unter {os.path.relpath(INBOX, ROOT)}/:")
        for pid in prepared:
            print(f"  _inbox/{pid}/")
        print("Fotos dort hineinlegen, dann: python3 tools/website.py intake")
    return 0


# ------------------------------------------------------------------- intake

def cmd_intake(argv):
    """Uebernimmt Bilder aus _inbox/<item-id>/ in die Seite."""
    dry = "--dry-run" in argv
    items = load()
    by_id = {i["id"]: i for i in items}

    if not os.path.isdir(INBOX):
        os.makedirs(INBOX, exist_ok=True)
        print(f"Ordner {os.path.relpath(INBOX, ROOT)}/ angelegt. Er ist noch leer.")
        print("Lege darin einen Unterordner je Eintrag an, zum Beispiel:")
        print("  _inbox/funke-2-geist-2026/")
        return 0

    folders = sorted(
        d for d in os.listdir(INBOX)
        if os.path.isdir(os.path.join(INBOX, d)) and not d.startswith(".")
    )
    if not folders:
        print(f"{os.path.relpath(INBOX, ROOT)}/ enthaelt keine Unterordner.")
        print("Erwartet wird ein Ordner je Eintrag, benannt wie die id in content.json.")
        return 0

    touched = False
    for folder in folders:
        src_dir = os.path.join(INBOX, folder)
        files = sorted(
            f for f in os.listdir(src_dir)
            if os.path.splitext(f)[1].lower() in INBOX_EXT and not f.startswith(".")
        )
        skipped = [
            f for f in os.listdir(src_dir)
            if not f.startswith(".")
            and os.path.splitext(f)[1].lower() not in INBOX_EXT
            and os.path.isfile(os.path.join(src_dir, f))
        ]
        for f in skipped:
            print(f"[{folder}] uebergangen, kein Bild: {f}")
        if not files:
            print(f"[{folder}] leer, uebersprungen")
            continue
        if folder not in by_id:
            print(f"[{folder}] KEIN Eintrag mit dieser id in content.json - uebersprungen")
            print(f"          vorhandene ids beginnen z.B. mit: "
                  f"{', '.join(sorted(by_id)[:3])} ...")
            continue

        item = by_id[folder]

        # Zu kleine Aufnahmen bleiben liegen, damit sie nicht unbemerkt
        # auf der Seite landen.
        too_small = []
        for fname in list(files):
            edge = long_edge(os.path.join(src_dir, fname))
            if edge is not None and edge < MIN_LONG_EDGE:
                too_small.append((fname, edge))
                files.remove(fname)
        for fname, edge in too_small:
            print(f"[{folder}] ZU KLEIN, bleibt liegen: {fname} "
                  f"({edge} px, gebraucht werden {MIN_LONG_EDGE})")
        if too_small and not files:
            print(f"[{folder}] alle {len(too_small)} Dateien zu klein, "
                  f"nichts uebernommen")
            continue

        dest_dir = os.path.join(IMAGE_ROOT, folder)
        existing = []
        if os.path.isdir(dest_dir):
            existing = sorted(
                f for f in os.listdir(dest_dir)
                if os.path.splitext(f)[1].lower() in IMAGE_EXT
            )
        start = len(existing) + 1

        added = []
        for n, fname in enumerate(files, start=start):
            ext = os.path.splitext(fname)[1].lower()
            if ext in CONVERT_EXT or ext == ".jpeg":
                ext = ".jpg"
            new_name = f"{folder}-{n:02d}{ext}"
            rel = f"assets/images/{folder}/{new_name}"
            if dry:
                print(f"[{folder}] {fname}  ->  {rel}")
            else:
                os.makedirs(dest_dir, exist_ok=True)
                note = prepare_image(
                    os.path.join(src_dir, fname), os.path.join(dest_dir, new_name)
                )
                size = os.path.getsize(os.path.join(dest_dir, new_name)) // 1024
                print(f"[{folder}] {fname}  ->  {rel}  [{note}, {size} kB]")
            added.append(rel)

        if not dry and added:
            gallery = list(item.get("images") or [])
            for rel in added:
                if rel not in gallery:
                    gallery.append(rel)
            item["images"] = gallery
            if not item.get("image"):
                item["image"] = gallery[0]
                print(f"[{folder}] Titelbild gesetzt: {gallery[0]}")
            touched = True

        if not dry and not os.listdir(src_dir):
            os.rmdir(src_dir)

    if dry:
        print("\nProbelauf, nichts veraendert.")
        return 0
    if touched:
        save(items)
        print("\ncontent.json aktualisiert, vorheriger Stand in data/.backups/.")
        print("Jetzt pruefen mit: python3 tools/website.py check")
    else:
        print("\nNichts zu tun.")
    return 0


# -------------------------------------------------------------------- serve

def cmd_serve(argv):
    port = argv[0] if argv else "8000"
    print(f"Vorschau auf http://localhost:{port}/  (Abbruch mit Strg+C)")
    os.chdir(ROOT)
    subprocess.call([sys.executable, "-m", "http.server", port])
    return 0


def find_osxphotos():
    return shutil.which("osxphotos") or (
        VENV_OSXPHOTOS if os.path.exists(VENV_OSXPHOTOS) else None
    )


def inbox_uuids():
    """Je Ablageordner die Asset-Kennungen der abgelegten Vorschauen."""
    uuid_re = re.compile(
        r"^([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}"
        r"-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})_"
    )
    out = {}
    if not os.path.isdir(INBOX):
        return out
    for folder in sorted(os.listdir(INBOX)):
        d = os.path.join(INBOX, folder)
        if not os.path.isdir(d) or folder.startswith("."):
            continue
        found = {}
        for f in os.listdir(d):
            m = uuid_re.match(f)
            if m:
                found[m.group(1)] = f
        if found:
            out[folder] = found
    return out


def cmd_albums(argv):
    """Legt in Fotos je Eintrag ein Album mit der getroffenen Auswahl an.

    Der Weg ueber osxphotos scheitert, solange die Originale nur in iCloud
    liegen: --download-missing benutzt intern den AppleScript-Export, der
    nichts schreibt. Photos selbst laedt die Originale aber herunter,
    sobald man sie ueber das Menu exportiert. Damit die richtigen Bilder
    dafuer beisammen sind, wandert jede Auswahl in ein eigenes Album.
    """
    groups = inbox_uuids()
    if not groups:
        print("Keine Vorschauen in _inbox gefunden.")
        return 1

    # Filme aussortieren. Die Galerie zeigt nur Bilder, und gerade Videos
    # machen den Loewenanteil der Datenmenge aus, die sonst aus iCloud
    # geladen werden muesste.
    movies = set()
    tool = find_osxphotos()
    if tool:
        every = sorted({u for found in groups.values() for u in found})
        listing = os.path.join(tempfile.gettempdir(), "website-uuids.txt")
        with open(listing, "w") as fh:
            fh.write("\n".join(every))
        res = subprocess.run(
            [tool, "query", "--uuid-from-file", listing, "--json"],
            capture_output=True, text=True,
        )
        if res.returncode == 0:
            try:
                for photo in json.loads(res.stdout):
                    if photo.get("ismovie"):
                        movies.add(photo["uuid"])
            except ValueError:
                pass
        os.remove(listing)
    if movies:
        print(f"{len(movies)} Filme werden uebergangen, die Galerie zeigt nur Bilder.")
        for folder in groups:
            groups[folder] = {
                u: f for u, f in groups[folder].items() if u not in movies
            }
        groups = {f: v for f, v in groups.items() if v}

    script = ['tell application "Photos"', "  set report to \"\"" ]
    for folder, found in groups.items():
        name = f"WEB {folder}"
        script.append(f'  try')
        script.append(f'    delete album "{name}"')
        script.append(f'  end try')
        script.append(f'  set a to make new album named "{name}"')
        script.append(f'  set picked to {{}}')
        for uuid in found:
            script.append(f'  try')
            script.append(f'    set end of picked to media item id "{uuid}/L0/001"')
            script.append(f'  end try')
        script.append(f'  if (count of picked) > 0 then add picked to a')
        script.append(
            f'  set report to report & "{name}: " & (count of media items of a) '
            f'& " von {len(found)}" & linefeed')
    script.append("  return report")
    script.append("end tell")

    res = subprocess.run(
        ["osascript", "-e", "\n".join(script)],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        print("Fotos meldet einen Fehler:")
        print(res.stderr.strip())
        return 1
    print(res.stdout.strip())
    print()
    print("In Fotos liegen jetzt Alben mit dem Praefix WEB. Fuer jedes:")
    print("  1. Album oeffnen, Befehl-A")
    print("  2. Ablage > Exportieren > Originale exportieren fuer X Fotos")
    print("  3. Unterordner-Format: Keine")
    print("  4. Ziel: der gleichnamige Ordner unter _inbox/")
    print()
    print("Photos laedt die Originale dabei selbst aus iCloud.")
    print("Danach: python3 tools/website.py intake")
    return 0


def cmd_originals(argv):
    """Ersetzt die Vorschauen in _inbox durch die Originale aus Fotos.

    Zieht man ein Bild aus Fotos heraus, bekommt man haeufig nur eine
    Vorschau von 360 bis 1024 Pixel. Ihr Dateiname traegt aber die
    Asset-Kennung des Originals, etwa

        183DCF16-02C5-4921-A8B6-D07EE92FBC6E_1_105_c.jpeg

    Der vordere Teil ist die Kennung. Ueber sie holt osxphotos das
    Original aus der Mediathek und die Vorschau wird geloescht.
    """
    dry = "--dry-run" in argv
    tool = find_osxphotos()
    if not tool:
        print("osxphotos nicht gefunden. Einrichten mit:")
        print("  python3 -m venv tools/.venv")
        print("  tools/.venv/bin/pip install osxphotos")
        return 1

    if not os.path.isdir(INBOX):
        print("_inbox/ existiert nicht. Erst: python3 tools/website.py needs")
        return 1

    uuid_re = re.compile(
        r"^([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}"
        r"-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})_"
    )
    total_found = total_done = 0
    for folder in sorted(os.listdir(INBOX)):
        src_dir = os.path.join(INBOX, folder)
        if not os.path.isdir(src_dir) or folder.startswith("."):
            continue
        previews = {}
        for f in os.listdir(src_dir):
            m = uuid_re.match(f)
            if m:
                previews[m.group(1)] = f
        if not previews:
            continue
        total_found += len(previews)
        print(f"[{folder}] {len(previews)} Vorschauen erkannt")
        if dry:
            for u, f in previews.items():
                print(f"    {u}  <-  {f}")
            continue

        # In einen Zwischenordner exportieren, damit osxphotos seine
        # Zustandsdatei nicht in der Ablage hinterlaesst. Der
        # Originaldateiname ist die Vorgabe, deshalb kein eigener Schalter.
        stage = tempfile.mkdtemp(prefix="originals-")
        try:
            # --use-photokit ist noetig, weil die Originale in iCloud liegen
            # und nur lokale Vorschauen vorhanden sind. PhotoKit laedt sie
            # nach, verlangt dafuer aber die Fotos-Freigabe der aufrufenden
            # Anwendung.
            cmd = [tool, "export", stage, "--download-missing",
                   "--use-photokit", "--skip-original-if-edited"]
            for u in previews:
                cmd += ["--uuid", u]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                head = (res.stderr or res.stdout).strip().splitlines()
                print(f"[{folder}] osxphotos meldet einen Fehler:")
                for line in head[:6]:
                    print(f"    {line}")
                if any("Error copying" in l or "Operation not permitted" in l
                       for l in head):
                    print("    Es fehlt der Festplattenvollzugriff.")
                if any("authorization" in l or "Privacy" in l for l in head):
                    print("    Es fehlt die Fotos-Freigabe.")
                print("    Beides braucht dieselbe Anwendung. Am einfachsten in")
                print("    Terminal.app: dort ist die Fotos-Freigabe schon erteilt,")
                print("    der Festplattenvollzugriff muss nur eingeschaltet werden.")
                return 1

            got = [
                f for f in sorted(os.listdir(stage))
                if not f.startswith(".")
                and os.path.splitext(f)[1].lower() in INBOX_EXT
            ]
            if not got:
                print(f"[{folder}] osxphotos lieferte keine Datei, Vorschauen bleiben")
                if "missing:" in res.stdout:
                    for line in res.stdout.splitlines():
                        if "missing:" in line:
                            print(f"    {line.strip()}")
                    print("    Die Originale liegen in iCloud, nicht auf dem Mac.")
                    print("    Dafuer wird die Fotos-Freigabe gebraucht.")
                continue

            for f in got:
                dest = os.path.join(src_dir, f)
                if os.path.exists(dest):
                    os.remove(dest)
                shutil.move(os.path.join(stage, f), dest)
            for preview in previews.values():
                pp = os.path.join(src_dir, preview)
                if os.path.exists(pp):
                    os.remove(pp)
                    total_done += 1
            print(f"[{folder}] {len(got)} Originale geholt, "
                  f"{len(previews)} Vorschauen entfernt")
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    if dry:
        print(f"\nProbelauf: {total_found} Vorschauen gefunden.")
    else:
        print(f"\n{total_done} Vorschauen durch Originale ersetzt.")
        print("Weiter mit: python3 tools/website.py intake")
    return 0


COMMANDS = {
    "check": cmd_check,
    "originals": cmd_originals,
    "albums": cmd_albums,
    "needs": cmd_needs,
    "intake": cmd_intake,
    "serve": cmd_serve,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return 1
    return COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
