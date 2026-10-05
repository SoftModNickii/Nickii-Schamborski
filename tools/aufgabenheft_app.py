"""
aufgabenheft_app.py - die Heftseite im Browser.

Ein kleiner Server nur fuer diesen Rechner (127.0.0.1:8787). Er zeigt die
Aufgabe des Tages mit allem, was im Archiv dazu steht: Text, Bilder, Link
zur Seite. Die Antwort wird direkt dort geschrieben und in
_aufgabenheft/antworten/<id>.md gespeichert, genau wie vorher.

    python3 tools/website.py heft                Server starten, Browser oeffnen
    python3 tools/website.py heft --hintergrund  dasselbe, ohne Terminal offen zu halten
"""

import io
import json
import mimetypes
import os
import subprocess
import sys
import threading
import unicodedata
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import aufgabenheft as H

ROOT = H.ROOT
PORT = 8787
URL = f"http://127.0.0.1:{PORT}/"
SEITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aufgabenheft.html")
BILD_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff", ".heic"}
_cache = {}
_lock = threading.Lock()


def repo_pfad(rel):
    """Pfad aus content.json oder Aufgabe -> Datei im Repo, nie ausserhalb."""
    if not rel:
        return None
    rel = urllib.parse.unquote(rel)
    for form in ("NFC", "NFD"):
        full = os.path.realpath(os.path.join(ROOT, unicodedata.normalize(form, rel)))
        if full.startswith(os.path.realpath(ROOT) + os.sep) and os.path.isfile(full):
            return full
    return None


def lade_json(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as fh:
        return json.load(fh)


def datei_info(rel):
    ext = os.path.splitext(rel)[1].lower()
    art = "bild" if ext in BILD_EXT else "video" if ext in (".mp4", ".mov") else "datei"
    return {"pfad": rel, "art": art, "name": os.path.basename(urllib.parse.unquote(rel)),
            "da": repo_pfad(rel) is not None}


def kontext(a):
    """Was im Archiv zu dieser Aufgabe steht."""
    k = {"hinweis": a.get("kontext") or "", "dateien": [datei_info(d) for d in a.get("dateien") or []]}
    site = lade_json("site.json")
    items = lade_json("content.json")
    by_id = {i["id"]: i for i in items}
    if a["id"] == "audit-statement":
        k["statement"] = site["statement"]
        k["seite"] = "/site/index.html"
    if a["id"] == "audit-auswahl":
        k["auswahl"] = [{"titel": by_id[i]["title"], "jahr": by_id[i]["year"],
                         "bild": by_id[i].get("image")} for i in site["featured"] if i in by_id]
        k["seite"] = "/site/index.html"
    item = by_id.get(a.get("eintrag") or "")
    if item:
        bilder = []
        for p in [item.get("image")] + list(item.get("images") or []):
            if p and not p.startswith("http") and p not in bilder:
                bilder.append(p)
        k["eintrag"] = {
            "titel": item["title"],
            "jahr": item.get("year"),
            "typ": item.get("type"),
            "specs": item.get("specs"),
            "ort": item.get("institution"),
            "text_en": item.get("description"),
            "text_de": item.get("description_de"),
            "bilder": bilder[:9],
            "mehr_bilder": max(0, len(bilder) - 9),
        }
        if "works" in (item.get("categories") or []):
            k["seite"] = f"/site/works/{item['id']}.html"
        else:
            k["seite"] = f"/site/pages/all.html?item={urllib.parse.quote(item['id'])}"
    return k


def aufgabe_json(aufgaben, f, a):
    if a is None:
        return {"fertig": True, "status": H.status(aufgaben, f)}
    st = f["aufgaben"].get(a["id"], {})
    return {
        "aufgabe": {**a, "art_name": H.ARTEN[a["art"]], "nummer": aufgaben.index(a) + 1},
        "kontext": kontext(a),
        "antwort": H.antwort_text(a),
        "geloest": bool(st.get("geloest")),
        "eingearbeitet": bool(st.get("eingearbeitet")),
        "status": H.status(aufgaben, f),
    }


def vorschau(pfad, breite):
    key = (pfad, breite)
    with _lock:
        if key in _cache:
            return _cache[key]
    from PIL import Image, ImageOps
    im = Image.open(pfad)
    im.draft("RGB", (breite * 2, breite * 2))
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((breite, breite))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    data = buf.getvalue()
    with _lock:
        if len(_cache) > 300:
            _cache.clear()
        _cache[key] = data
    return data


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def senden(self, code, body, typ="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        try:
            if url.path in ("/", "/index.html"):
                with open(SEITE, encoding="utf-8") as fh:
                    return self.senden(200, fh.read(), "text/html; charset=utf-8")
            if url.path == "/api/ping":
                return self.senden(200, '"aufgabenheft"')
            if url.path == "/api/heute":
                aufgaben, f, a = H.heutige_aufgabe(bonus="bonus" in q)
                return self.senden(200, aufgabe_json(aufgaben, f, a))
            if url.path == "/api/aufgabe":
                aufgaben = H.alle_aufgaben()
                f = H.aktualisiere(aufgaben, H.lade_fortschritt())
                a = next((x for x in aufgaben if x["id"] == q.get("id", [""])[0]), None)
                if a is None:
                    return self.senden(404, {"fehler": "Aufgabe nicht gefunden"})
                return self.senden(200, aufgabe_json(aufgaben, f, a))
            if url.path == "/api/heft":
                aufgaben = H.alle_aufgaben()
                f = H.aktualisiere(aufgaben, H.lade_fortschritt())
                heute = f.get("heute", {})
                liste = [{"id": a["id"], "nummer": n, "titel": a["titel"], "art": a["art"],
                          "art_name": H.ARTEN[a["art"]], "sterne": a["sterne"],
                          "geloest": bool(f["aufgaben"].get(a["id"], {}).get("geloest")),
                          "heute": a["id"] in heute.values()}
                         for n, a in enumerate(aufgaben, start=1)]
                return self.senden(200, {"aufgaben": liste, "status": H.status(aufgaben, f)})
            if url.path == "/bild":
                pfad = repo_pfad(q.get("pfad", [""])[0])
                if not pfad:
                    return self.senden(404, {"fehler": "Bild fehlt"})
                breite = min(int(q.get("w", ["900"])[0]), 2400)
                return self.senden(200, vorschau(pfad, breite), "image/jpeg")
            if url.path == "/datei" or url.path.startswith("/site/"):
                rel = q.get("pfad", [""])[0] if url.path == "/datei" else url.path[len("/site/"):]
                if rel == "" or rel.endswith("/"):
                    rel += "index.html"
                pfad = repo_pfad(rel)
                if not pfad:
                    return self.senden(404, "Nicht gefunden", "text/plain; charset=utf-8")
                typ = mimetypes.guess_type(pfad)[0] or "application/octet-stream"
                with open(pfad, "rb") as fh:
                    return self.senden(200, fh.read(), typ)
            return self.senden(404, {"fehler": "unbekannt"})
        except Exception as e:  # die Seite soll einen Fehler anzeigen, nicht haengen
            return self.senden(500, {"fehler": str(e)})

    def do_POST(self):
        if self.path != "/api/antwort":
            return self.senden(404, {"fehler": "unbekannt"})
        try:
            laenge = int(self.headers.get("Content-Length", 0))
            daten = json.loads(self.rfile.read(laenge) or b"{}")
            aid, text = daten.get("id", ""), daten.get("text", "")
            if not text.strip():
                return self.senden(400, {"fehler": "Die Antwort ist noch leer."})
            aufgaben = H.alle_aufgaben()
            vorher = H.lade_fortschritt()
            vorher_punkte = H.punkte(vorher)
            vorher_stufe = H.stufe(vorher_punkte)[0]
            war_geloest = bool(vorher["aufgaben"].get(aid, {}).get("geloest"))
            f = H.speichere_antwort(aid, text)
            st = H.status(aufgaben, f)
            return self.senden(200, {
                "status": st,
                "neu": not war_geloest,
                "plus": st["punkte"] - vorher_punkte,
                "aufgestiegen": st["stufe"] != vorher_stufe,
            })
        except KeyError:
            return self.senden(404, {"fehler": "Aufgabe nicht gefunden"})
        except Exception as e:
            return self.senden(500, {"fehler": str(e)})


def laeuft_schon():
    """Antwortet auf dem Port wirklich das Heft, nicht irgendein Server?"""
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/ping", timeout=0.7) as r:
            return r.read() == b'"aufgabenheft"'
    except (OSError, ValueError):
        return False


def cmd_heft(argv):
    if laeuft_schon():
        webbrowser.open(URL)
        print(f"Das Heft ist schon offen: {URL}")
        return 0
    if "--hintergrund" in argv:
        # Losgeloest vom Terminal weiterlaufen, damit das Fenster zugehen kann
        log = open(os.path.join(H.HEFT, "server.log"), "a")
        subprocess.Popen([sys.executable, os.path.abspath(__file__)], cwd=ROOT,
                         stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                         start_new_session=True)
        for _ in range(40):
            if laeuft_schon():
                break
            threading.Event().wait(0.1)
        webbrowser.open(URL)
        print(f"Aufgabenheft laeuft: {URL}")
        return 0
    return serve(open_browser=True)


def serve(open_browser=False):
    os.makedirs(H.HEFT, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(URL)).start()
        print(f"Aufgabenheft: {URL}  (Beenden mit Strg+C)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(serve())
