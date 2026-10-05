"""
sitebuild.py - erzeugt die statischen Teile von schamborski.com aus data/.

Eine einzige Quelle: data/content.json (Eintraege, samt CV-Zeilen im Feld
"cv") und data/site.json (Statement, Auswahl, Kontakt). Daraus entstehen:

    index.html            Statement, ausgewaehlte Arbeiten, Person-JSON-LD
    pages/cv.html         alle CV-Abschnitte, Person-JSON-LD
    works/<id>.html       eine Seite je Arbeit (Kategorie "works")
    assets/thumbs/        Vorschaubilder fuer Raster und Startseite
    assets/og/preview.jpg Vorschaubild fuer soziale Netzwerke, 1200 x 630
    sitemap.xml, robots.txt, Favicons, site.webmanifest

In index.html und pages/cv.html wird nur zwischen Markierungen der Form
<!-- build:name --> ... <!-- /build:name --> geschrieben. Alles andere bleibt
von Hand pflegbar. works/ ist vollstaendig generiert.

Aufgerufen wird das ueber:  python3 tools/website.py build
"""

import html
import json
import os
import re
import unicodedata
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "data", "site.json")
THUMB_DIR = os.path.join(ROOT, "assets", "thumbs")
THUMB_MANIFEST = os.path.join(THUMB_DIR, "manifest.json")
OG_IMAGE = "assets/og/preview.jpg"
WORKS_DIR = os.path.join(ROOT, "works")
THUMB_EDGE = 1000

# Die Schriften liegen in assets/fonts, damit kein Besuch Daten an Google schickt.
FONTS = '<link rel="stylesheet" href="../css/fonts.css?v=20261008">'


def icons(prefix):
    return (f'<link rel="icon" type="image/svg+xml" href="{prefix}favicon.svg">\n'
            f'    <link rel="icon" type="image/png" sizes="32x32" href="{prefix}favicon-32x32.png">\n'
            f'    <link rel="icon" type="image/png" sizes="16x16" href="{prefix}favicon-16x16.png">\n'
            f'    <link rel="apple-touch-icon" sizes="180x180" href="{prefix}apple-touch-icon.png">\n'
            f'    <link rel="manifest" href="{prefix}site.webmanifest">')


# ------------------------------------------------------------ Hilfsmittel

def load_site():
    with open(SITE, encoding="utf-8") as fh:
        return json.load(fh)


def esc(text):
    return html.escape(str(text or ""), quote=True)


def inline(text):
    """Escaped Text, **fett** wird zu <strong>."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(text))


def paragraphs(text):
    parts = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return "\n".join(f"<p>{esc(p).replace(chr(10), '<br>')}</p>" for p in parts)


def years(value):
    """Alle Jahreszahlen in einem Datums- oder Jahresfeld."""
    return [int(y) for y in re.findall(r"(?<!\d)(19\d\d|20\d\d)(?!\d)", str(value or ""))]


def year_range(item):
    ys = years(item.get("year"))
    return (min(ys), max(ys)) if ys else (None, None)


def fs_path(path):
    """content.json-Pfad (evtl. %20, NFC/NFD) -> Datei auf der Platte oder None."""
    if not path or path.startswith("http"):
        return None
    for cand in dict.fromkeys([path, urllib.parse.unquote(path)]):
        for form in ("NFC", "NFD"):
            full = os.path.join(ROOT, unicodedata.normalize(form, cand))
            if os.path.exists(full):
                return full
    return None


def url_path(path):
    """Dateipfad -> URL-sicherer Pfad (Leerzeichen, #, Umlaute)."""
    return urllib.parse.quote(urllib.parse.unquote(path), safe="/")


def article(word):
    return "an" if word[:1].lower() in "aeiou" else "a"


def lower_first(text):
    """'Interactive Object, Edition of 5' -> 'interactive object, edition of 5'.
    Woerter in Grossbuchstaben (VR, LCD) bleiben stehen."""
    return " ".join(w.lower() if w[:1].isupper() and not w[1:2].isupper() else w
                    for w in (text or "").split(" "))


def is_work(item):
    return "works" in (item.get("categories") or [])


def local_images(item):
    out = []
    for p in ([item.get("image")] if item.get("image") else []) + list(item.get("images") or []):
        if p and not p.startswith("http") and p not in out:
            out.append(p)
    return out


def shown_at(item, by_id):
    """Ausstellungen einer Arbeit, aus beiden Richtungen der Querverweise."""
    ids = list(item.get("exhibited_at") or [])
    for other in by_id.values():
        if item["id"] in (other.get("exhibited_works") or []) and other["id"] not in ids:
            ids.append(other["id"])
    return [by_id[i] for i in ids if i in by_id]


def write_if_changed(path, content, written):
    old = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            old = fh.read()
    if old != content:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        written.append(os.path.relpath(path, ROOT))


def replace_block(text, name, content, path):
    pattern = re.compile(
        rf"(<!-- build:{name} -->)(.*?)(\s*<!-- /build:{name} -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"Markierung build:{name} fehlt in {os.path.relpath(path, ROOT)}")
    return pattern.sub(lambda m: m.group(1) + "\n" + content + m.group(3), text)


# ------------------------------------------------------------ Bilder

def thumb_rel(item_id):
    return f"assets/thumbs/{item_id}.jpg"


def load_manifest():
    try:
        with open(THUMB_MANIFEST, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def expected_thumbs(items):
    """id -> Titelbildpfad fuer alle Eintraege mit lokalem Titelbild."""
    out = {}
    for item in items:
        img = item.get("image")
        if img and not img.startswith("http") and fs_path(img):
            out[item["id"]] = img
    return out


def build_thumbs(items, written):
    from PIL import Image, ImageOps
    manifest = load_manifest()
    want = expected_thumbs(items)
    os.makedirs(THUMB_DIR, exist_ok=True)
    for iid, src in want.items():
        dest = os.path.join(ROOT, thumb_rel(iid))
        entry = manifest.get(iid) or {}
        if entry.get("src") == src and os.path.exists(dest):
            continue
        im = Image.open(fs_path(src))
        im.draft("RGB", (THUMB_EDGE * 2, THUMB_EDGE * 2))
        im = ImageOps.exif_transpose(im)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        im.thumbnail((THUMB_EDGE, THUMB_EDGE), Image.LANCZOS)
        im.save(dest, "JPEG", quality=82, optimize=True, progressive=True)
        manifest[iid] = {"src": src, "w": im.width, "h": im.height}
        written.append(os.path.relpath(dest, ROOT))
    for iid in list(manifest):
        if iid not in want:
            stale = os.path.join(ROOT, thumb_rel(iid))
            if os.path.exists(stale):
                os.remove(stale)
            del manifest[iid]
            written.append(f"entfernt: {thumb_rel(iid)}")
    write_if_changed(THUMB_MANIFEST,
                     json.dumps(dict(sorted(manifest.items())), indent=1, ensure_ascii=False) + "\n",
                     written)
    return manifest


def build_og_image(site, written):
    from PIL import Image, ImageOps
    dest = os.path.join(ROOT, OG_IMAGE)
    marker = dest + ".src"
    src = site.get("og_image_source")
    if os.path.exists(dest) and os.path.exists(marker) and open(marker).read() == src:
        return
    im = ImageOps.exif_transpose(Image.open(fs_path(src))).convert("RGB")
    im = ImageOps.fit(im, (1200, 630), Image.LANCZOS)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    im.save(dest, "JPEG", quality=85, optimize=True)
    with open(marker, "w") as fh:
        fh.write(src)
    written.append(OG_IMAGE)


def build_icons(site, written):
    """Favicons einmalig anlegen: magentafarbenes N auf Weiss."""
    from PIL import Image, ImageDraw, ImageFont
    magenta = "#C026D3"
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
           '<rect width="64" height="64" rx="10" fill="#fff"/>'
           f'<text x="32" y="47" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" '
           f'font-size="44" font-weight="300" fill="{magenta}">N</text></svg>\n')
    write_if_changed(os.path.join(ROOT, "favicon.svg"), svg, written)
    fonts = ["/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc"]

    def draw(size):
        im = Image.new("RGB", (size, size), "white")
        d = ImageDraw.Draw(im)
        font = None
        for f in fonts:
            if os.path.exists(f):
                font = ImageFont.truetype(f, int(size * 0.72))
                break
        font = font or ImageFont.load_default()
        box = d.textbbox((0, 0), "N", font=font)
        x = (size - (box[2] - box[0])) / 2 - box[0]
        y = (size - (box[3] - box[1])) / 2 - box[1]
        d.text((x, y), "N", fill=magenta, font=font)
        return im

    targets = {"favicon-16x16.png": 16, "favicon-32x32.png": 32, "apple-touch-icon.png": 180,
               "android-chrome-192x192.png": 192, "android-chrome-512x512.png": 512}
    for name, size in targets.items():
        dest = os.path.join(ROOT, name)
        if not os.path.exists(dest):
            draw(size).save(dest)
            written.append(name)
    ico = os.path.join(ROOT, "favicon.ico")
    if not os.path.exists(ico):
        draw(64).save(ico, sizes=[(16, 16), (32, 32), (48, 48)])
        written.append("favicon.ico")
    manifest = {
        "name": site["name"],
        "short_name": site["name"],
        "icons": [
            {"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png"},
        ],
        "theme_color": "#ffffff",
        "background_color": "#ffffff",
        "display": "browser",
    }
    write_if_changed(os.path.join(ROOT, "site.webmanifest"),
                     json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", written)


# ------------------------------------------------------------ Rendering

def cv_rows(items, section):
    rows = []
    for item in items:
        for row in item.get("cv") or []:
            if row.get("section") == section:
                rows.append((row.get("order", 0), row, item))
    rows.sort(key=lambda r: r[0])
    return rows


def render_cv(items, site):
    out = []
    for key, title in site["cv_sections"]:
        rows = cv_rows(items, key)
        if not rows:
            continue
        out.append(f'            <section class="cv-section" id="cv-{key}">')
        out.append(f"                <h2>{esc(title)}</h2>")
        for _, row, item in rows:
            details = "<br>\n                        ".join(inline(l) for l in row["lines"])
            out.append(f'                <div class="cv-item" data-id="{esc(item["id"])}">')
            out.append(f'                    <div class="cv-year">{esc(row["date"])}</div>')
            out.append(f'                    <div class="cv-details">\n                        {details}\n                    </div>')
            out.append("                </div>")
        out.append("            </section>")
        out.append("")
    return "\n".join(out).rstrip()


def plain(lines):
    return re.sub(r"\*\*", "", " ".join(lines)).replace("( ", "(").strip()


def person_jsonld(items, site):
    base = site["base_url"]
    awards = [f"{plain(row['lines'])} ({row['date']})"
              for _, row, _ in cv_rows(items, "recognition")]
    by_id = {i["id"]: i for i in items}
    works = []
    for iid in site.get("featured") or []:
        w = by_id.get(iid)
        if w:
            works.append({"@type": "VisualArtwork", "name": w["title"],
                          "dateCreated": str(year_range(w)[0]),
                          "artform": w.get("type") or None,
                          "url": f"{base}/works/{iid}.html"})
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": site["name"],
        "url": base + "/",
        "image": f"{base}/{OG_IMAGE}",
        "email": site["email"],
        "jobTitle": site["job_title"],
        "description": site["meta_description"],
        "sameAs": [site["instagram"]],
        "affiliation": {"@type": "CollegeOrUniversity", "name": site["affiliation"]},
        "alumniOf": [{"@type": "CollegeOrUniversity", "name": n,
                      "address": {"@type": "PostalAddress", "addressCountry": c}}
                     for n, c in site["alumni_of"]],
        "award": awards,
        "workExample": works,
    }
    body = json.dumps(data, indent=2, ensure_ascii=False)
    return ('    <script type="application/ld+json">\n' + body + "\n    </script>")


def render_statement(site):
    return "\n".join(f"            <p>{esc(p)}</p>" for p in site["statement"])


def render_featured(items, site, manifest):
    by_id = {i["id"]: i for i in items}
    out = []
    for iid in site.get("featured") or []:
        w = by_id.get(iid)
        if not w:
            continue
        t = manifest.get(iid) or {}
        size = f' width="{t["w"]}" height="{t["h"]}"' if t else ""
        year = esc(w["year"])
        out.append(
            f'                <li>\n'
            f'                    <a href="works/{esc(iid)}.html">\n'
            f'                        <img src="{thumb_rel(iid)}" alt="{esc(w["title"])}, '
            f'{esc(lower_first(w.get("type") or "work"))} by Nickii Schamborski, {year}" '
            f'loading="lazy" decoding="async"{size}>\n'
            f'                        <span class="work-caption"><span class="work-title">{esc(w["title"])}</span>'
            f'<span class="work-meta">{year} · {esc(w.get("type") or "")}</span></span>\n'
            f'                    </a>\n'
            f'                </li>')
    return "\n".join(out)


def summary(item, by_id):
    kind = lower_first(item.get("type") or "work")
    text = f"{item['title']} is {article(kind)} {kind} by Nickii Schamborski, {item['year'].replace('/', '–')}."
    shows = shown_at(item, by_id)
    if shows:
        text += " Shown at " + "; ".join(
            f"{s['title']} ({s['year']})" for s in shows) + "."
    return text


def work_jsonld(item, by_id, site):
    base = site["base_url"]
    imgs = [f"{base}/{url_path(p)}" for p in local_images(item)]
    data = {
        "@context": "https://schema.org",
        "@type": "VisualArtwork",
        "name": item["title"],
        "url": f"{base}/works/{item['id']}.html",
        "creator": {"@type": "Person", "name": site["name"], "url": base + "/"},
        "dateCreated": str(year_range(item)[0]),
        "artform": item.get("type") or None,
        "description": item.get("description") or summary(item, by_id),
        "image": imgs or None,
    }
    if item.get("collaborators"):
        data["contributor"] = [{"@type": "Person", "name": c["name"]} for c in item["collaborators"]]
    if item.get("video_link"):
        data["sameAs"] = [item["video_link"]]
    data = {k: v for k, v in data.items() if v}
    return json.dumps(data, indent=2, ensure_ascii=False)


def render_work(item, by_id, site, prev_next):
    base = site["base_url"]
    iid = item["id"]
    title = item["title"]
    summ = summary(item, by_id)
    imgs = local_images(item)
    n = len(imgs)
    credit = item.get("image_credit")
    figures = []
    for i, p in enumerate(imgs, start=1):
        # Beschreibt das Bild, wo es eine Beschreibung gibt, sonst nennt es nur das Werk
        alt = f"{title} ({item['year']}), {lower_first(item.get('type') or 'work')} by Nickii Schamborski, image {i} of {n}"
        if (item.get("image_alts") or {}).get(p):
            alt = f"{item['image_alts'][p]} {title} ({item['year']}) by Nickii Schamborski."
        cap = f"Image {i} of {n}" + (f" · {credit}" if credit else "")
        loading = 'fetchpriority="high"' if i == 1 else 'loading="lazy"'
        figures.append(
            f'            <figure class="work-figure{" is-lead" if i == 1 else ""}">\n'
            f'                <img src="../{url_path(p)}" alt="{esc(alt)}" {loading} decoding="async">\n'
            f'                <figcaption>{esc(cap)}</figcaption>\n'
            f'            </figure>')
    facts = [("Year", item["year"].replace("/", "–")), ("Type", item.get("type")),
             ("Specs", item.get("specs")), ("Institution / place", item.get("institution"))]
    if item.get("collaborators"):
        facts.append(("Collaborators", "; ".join(
            c["name"] + (f" ({c['role']})" if c.get("role") else "") for c in item["collaborators"])))
    for role, name in (item.get("credits") or {}).items():
        if name:
            facts.append((role.replace("_", " ").capitalize(), name))
    fact_html = "\n".join(
        f"                <dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in facts if v)
    shows = shown_at(item, by_id)
    shows_html = ""
    if shows:
        lis = "\n".join(
            f'                <li><a href="../pages/all.html?item={esc(s["id"])}">{esc(s["title"])}</a>'
            f', {esc(s.get("institution") or "")} ({esc(s["year"])})</li>' for s in shows)
        shows_html = f'        <section class="work-shows">\n            <h2>Shown at</h2>\n            <ul>\n{lis}\n            </ul>\n        </section>\n'
    links = []
    if item.get("video_link"):
        links.append(f'<a href="{esc(item["video_link"])}" rel="noopener">Watch / project site ↗</a>')
    if item.get("link") and item.get("link") != item.get("video_link") and item["link"].startswith("http"):
        links.append(f'<a href="{esc(item["link"])}" rel="noopener">Link ↗</a>')
    links_html = ("        <p class=\"work-links\">" + " · ".join(links) + "</p>\n") if links else ""
    desc = ""
    if item.get("description"):
        desc += f'        <section class="work-text" lang="en">\n            <h2>About the work</h2>\n{paragraphs(item["description"])}\n        </section>\n'
    if item.get("description_de"):
        desc += f'        <section class="work-text" lang="de">\n            <h2>Zur Arbeit</h2>\n{paragraphs(item["description_de"])}\n        </section>\n'
    prev, nxt = prev_next
    pager = '        <nav class="work-pager" aria-label="More works">\n'
    if prev:
        pager += f'            <a href="{esc(prev["id"])}.html" rel="prev">← {esc(prev["title"])}</a>\n'
    pager += '            <a href="../pages/all.html?filter=works">All works</a>\n'
    if nxt:
        pager += f'            <a href="{esc(nxt["id"])}.html" rel="next">{esc(nxt["title"])} →</a>\n'
    pager += "        </nav>\n"
    og = f"{base}/{url_path(imgs[0])}" if imgs else f"{base}/{OG_IMAGE}"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Generiert von tools/website.py build aus data/content.json. Nicht von Hand aendern. -->
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title)} ({esc(item['year'])}) - Nickii Schamborski</title>
    <meta name="description" content="{esc(summ)}">
    <link rel="canonical" href="{base}/works/{esc(iid)}.html">
    <meta property="og:title" content="{esc(title)} - Nickii Schamborski">
    <meta property="og:description" content="{esc(summ)}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{base}/works/{esc(iid)}.html">
    <meta property="og:image" content="{esc(og)}">
    <meta name="twitter:card" content="summary_large_image">
    {FONTS}
    {icons('../')}
    <link rel="stylesheet" href="../css/style.css?v=20261008">
    <link rel="stylesheet" href="../css/work.css?v=20261008">
    <script type="application/ld+json">
{work_jsonld(item, by_id, site)}
    </script>
</head>
<body class="work-page">
    <a class="skip-link" href="#main">Skip to content</a>
    <div class="construction-notice" role="note">
        <span class="construction-icon" aria-hidden="true">🚧</span>
        Website under construction | <a href="../assets/pdfs/Nickii-Schamborski-Portfolio-02-2025-hq.pdf">Portfolio PDF (19 MB)</a>
    </div>
    <header class="work-header">
        <p class="site-name"><a href="../index.html">Nickii Schamborski</a></p>
        <nav class="work-nav" aria-label="Main">
            <a href="../pages/all.html?filter=works">Works</a>
            <a href="../pages/all.html?filter=all">Archive</a>
            <a href="../pages/cv.html">CV</a>
        </nav>
    </header>
    <main id="main" class="work-main">
        <h1>{esc(title)}</h1>
        <p class="work-kicker">{esc(item['year'].replace('/', '–'))} · {esc(item.get('type') or '')}</p>
        <p class="work-summary">{esc(summ)}</p>
        <div class="work-gallery">
{chr(10).join(figures)}
        </div>
{desc}        <section class="work-facts">
            <h2>Details</h2>
            <dl>
{fact_html}
            </dl>
        </section>
{shows_html}{links_html}{pager}    </main>
    <footer>
        <a href="../newsletter/">Newsletter</a> |
        <a href="../impressum.html">Impressum</a> |
        <a href="../datenschutz.html">Datenschutz</a> |
        <a href="mailto:{esc(site['email'])}">Contact</a>
    </footer>
</body>
</html>
"""


def sort_key(item):
    y = year_range(item)[0] or 0
    return (y, item.get("sort_date") or f"{y}-00")


def works_in_order(items):
    return sorted([i for i in items if is_work(i)], key=sort_key, reverse=True)


def render_sitemap(items, site):
    base = site["base_url"]
    urls = ["/", "/pages/all.html", "/pages/cv.html", "/newsletter/",
            "/impressum.html", "/datenschutz.html"]
    urls += [f"/works/{w['id']}.html" for w in works_in_order(items)]
    body = "\n".join(f"  <url><loc>{base}{u}</loc></url>" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{body}\n</urlset>\n")


def render_robots(site):
    return f"User-agent: *\nAllow: /\n\nSitemap: {site['base_url']}/sitemap.xml\n"


# ------------------------------------------------------------ Gesamtlauf

def outputs(items, site, manifest):
    """Alle Textausgaben als {pfad: inhalt}. Dient build und check."""
    out = {}
    by_id = {i["id"]: i for i in items}
    idx_path = os.path.join(ROOT, "index.html")
    with open(idx_path, encoding="utf-8") as fh:
        idx = fh.read()
    idx = replace_block(idx, "jsonld", person_jsonld(items, site), idx_path)
    idx = replace_block(idx, "statement", render_statement(site), idx_path)
    idx = replace_block(idx, "featured", render_featured(items, site, manifest), idx_path)
    out[idx_path] = idx

    cv_path = os.path.join(ROOT, "pages", "cv.html")
    with open(cv_path, encoding="utf-8") as fh:
        cv = fh.read()
    cv = replace_block(cv, "jsonld", person_jsonld(items, site), cv_path)
    cv = replace_block(cv, "cv", render_cv(items, site), cv_path)
    out[cv_path] = cv

    works = works_in_order(items)
    for n, w in enumerate(works):
        prev = works[n - 1] if n > 0 else None
        nxt = works[n + 1] if n + 1 < len(works) else None
        out[os.path.join(WORKS_DIR, f"{w['id']}.html")] = render_work(w, by_id, site, (prev, nxt))
    out[os.path.join(ROOT, "sitemap.xml")] = render_sitemap(items, site)
    out[os.path.join(ROOT, "robots.txt")] = render_robots(site)
    return out


def build(items):
    site = load_site()
    written = []
    manifest = build_thumbs(items, written)
    build_og_image(site, written)
    build_icons(site, written)
    outs = outputs(items, site, manifest)
    for path, content in outs.items():
        write_if_changed(path, content, written)
    if os.path.isdir(WORKS_DIR):
        for f in os.listdir(WORKS_DIR):
            full = os.path.join(WORKS_DIR, f)
            if f.endswith(".html") and full not in outs:
                os.remove(full)
                written.append(f"entfernt: works/{f}")
    return written


def stale_outputs(items):
    """Pfade, deren Inhalt nicht mehr zu data/ passt. Fuer check."""
    site = load_site()
    manifest = load_manifest()
    stale = []
    for path, content in outputs(items, site, manifest).items():
        try:
            with open(path, encoding="utf-8") as fh:
                if fh.read() != content:
                    stale.append(os.path.relpath(path, ROOT))
        except OSError:
            stale.append(os.path.relpath(path, ROOT) + " (fehlt)")
    want = expected_thumbs(items)
    for iid, src in want.items():
        entry = manifest.get(iid)
        if not entry or entry.get("src") != src or not os.path.exists(os.path.join(ROOT, thumb_rel(iid))):
            stale.append(thumb_rel(iid))
    for iid in manifest:
        if iid not in want:
            stale.append(f"{thumb_rel(iid)} (verwaist)")
    return stale
