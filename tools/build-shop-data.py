#!/usr/bin/env python3
"""Generate shop-data.js from the live Square Online sitemap.

The shop page's buy dialog needs, per artwork, a Square product URL for each
format. Those URLs contain Square-generated ids that can't be guessed, and they
CHANGE whenever an item is recreated — so this is generated, never hand-written.

    python3 tools/build-shop-data.py            # writes ../shop-data.js
    python3 tools/build-shop-data.py --check    # report only, write nothing

Two things worth knowing before you edit this:

* A Square product is only listed in the sitemap once it has a price. An
  unpriced item is invisible to the storefront, so a format missing here almost
  always means "nobody set a price", not "the product doesn't exist".
* Artwork titles on the site and item names in Square drift apart. SLUG_ALIASES
  maps the Square spelling onto the site spelling. Add a line when they diverge
  rather than renaming anything on the site.
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys
import unicodedata
import urllib.request

SITEMAP = "https://miles2walk.square.site/sitemap.xml"
REPO = pathlib.Path(__file__).resolve().parent.parent

# Retail ladder: Printful base cost x2, plus a $12 flat shipping buffer carried
# by every item, rounded up to the next $5. Shipping is baked into the price,
# so Square's own shipping must stay at $0 or buyers pay it twice.
FORMATS = [
    {
        "key": "poster",
        "label": "Fine Art Poster",
        "blurb": "Museum-quality matte paper, 189 g/m² and 10.3 mil thick, "
                 "at 94% opacity. No glare, deep blacks, ready to frame however "
                 "you like.",
        "sizes": [{"size": "6x8", "price": 25},
                  {"size": "12x16", "price": 35},
                  {"size": "18x24", "price": 40}],
    },
    {
        "key": "framed-poster",
        "label": "Framed Poster",
        "blurb": "The same matte print, set in a 0.75″ ayous wood frame from "
                 "renewable forests, behind an acrylite front protector. "
                 "Hanging hardware included.",
        "sizes": [{"size": "8x10", "price": 55},
                  {"size": "12x16", "price": 80},
                  {"size": "18x24", "price": 105}],
    },
    {
        "key": "canvas",
        "label": "Gallery Canvas",
        "blurb": "1.25″ thick poly-cotton canvas, hand-stretched over solid "
                 "wood stretcher bars with mounting brackets fitted. Fade-"
                 "resistant, and it arrives ready to hang.",
        "sizes": [{"size": "9x12", "price": 45},
                  {"size": "12x16", "price": 60},
                  {"size": "18x24", "price": 80}],
    },
    {
        "key": "framed-canvas",
        "label": "Framed Canvas",
        "blurb": "Canvas set in a 1.25″ pine frame with an open back, which "
                 "gives the piece a floating effect. Rubber pads and wall mount "
                 "fitted.",
        "sizes": [{"size": "9x12", "price": 75},
                  {"size": "12x16", "price": 115},
                  {"size": "18x24", "price": 155}],
    },
    {
        "key": "metal",
        "label": "Metal Print",
        "blurb": "Aluminium on an MDF wood frame, hanging half an inch off the "
                 "wall. Scratch- and fade-resistant, and luminescent against "
                 "the wall.",
        "sizes": [{"size": "8x10", "price": 90},
                  {"size": "11x14", "price": 120},
                  {"size": "16x20", "price": 170}],
    },
]

# Square item name slug -> slug used in shop.html's data-art attribute.
SLUG_ALIASES = {
    # Square says "Naeglin's Bakery"; the site, the real New Braunfels bakery,
    # and the sign painted in the artwork all say "Naegelin's". Square also
    # turns the apostrophe into a dash in the URL, hence "naeglin-s".
    "naeglin-s-bakery": "naegelins-bakery",
    "naeglins-bakery": "naegelins-bakery",
}

# Longest first, so "framed-canvas" wins over "canvas".
FORMAT_SUFFIXES = sorted((f["key"] for f in FORMATS), key=len, reverse=True)


def fetch(url):
    """Fetch over curl rather than urllib.

    The python.org build ships no CA bundle, so urllib fails SSL verification
    on a clean Mac. curl uses the system trust store and is always present.
    """
    try:
        return subprocess.run(
            ["curl", "-sSf", "--max-time", "60", url],
            check=True, capture_output=True, text=True).stdout
    except FileNotFoundError:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.read().decode()
    except subprocess.CalledProcessError as e:
        sys.exit(f"failed to fetch {url}: {e.stderr.strip() or e}")


def slugify(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_cards(html):
    """Pull artwork title, kind and thumbnail out of each catalog card."""
    cards = {}
    pattern = re.compile(
        r'<a class="glightbox print-thumb" href="(?P<full>[^"]+)".*?'
        r'<img src="(?P<thumb>[^"]+)".*?'
        r'<h3 class="print-title">(?P<title>.*?)</h3>\s*'
        r'<p class="print-kind">(?P<kind>.*?)</p>.*?'
        r'data-art="(?P<slug>[^"]+)"',
        re.S)
    for m in pattern.finditer(html):
        cards[m.group("slug")] = {
            "title": m.group("title").strip(),
            "kind": re.sub(r"\s*&middot;\s*", " · ", m.group("kind").strip()),
            "thumb": m.group("thumb"),
            "products": {},
        }
    return cards


def parse_sitemap(xml):
    """URL -> (square_slug, format_key) for every product listing."""
    out = []
    for loc in re.findall(r"<loc>([^<]+)</loc>", xml):
        if "/product/" not in loc:
            continue
        slug = loc.split("/product/", 1)[1].split("/")[0]
        for suffix in FORMAT_SUFFIXES:
            if slug.endswith("-" + suffix):
                out.append((loc, slug[: -(len(suffix) + 1)], suffix))
                break
        else:
            print(f"  ! unrecognised format in URL: {loc}", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report coverage without writing shop-data.js")
    args = ap.parse_args()

    shop_html = (REPO / "shop.html").read_text()
    cards = parse_cards(shop_html)
    print(f"shop.html: {len(cards)} catalog cards")

    xml = fetch(SITEMAP)
    listings = parse_sitemap(xml)
    print(f"sitemap:   {len(listings)} product listings")

    unmatched = set()
    for url, square_slug, fmt in listings:
        slug = SLUG_ALIASES.get(square_slug, square_slug)
        if slug not in cards:
            unmatched.add(square_slug)
            continue
        cards[slug]["products"][fmt] = url

    if unmatched:
        print("\n! in Square but not on the shop page "
              "(add to SLUG_ALIASES, or add the card):", file=sys.stderr)
        for s in sorted(unmatched):
            print(f"    {s}", file=sys.stderr)

    # Per-format mockups, downloaded from Printful by tools/fetch-mockups.py.
    # One image per artwork+format, deliberately reused across that format's
    # three sizes — a 12x16 and an 18x24 canvas photograph identically.
    mockup_dir = REPO / "Images" / "mockups"
    for slug, art in cards.items():
        art["mockups"] = {}
        for f in FORMATS:
            rel = f"Images/mockups/{slug}-{f['key']}.webp"
            if (REPO / rel).exists():
                art["mockups"][f["key"]] = rel
    have = sum(len(a["mockups"]) for a in cards.values())
    print(f"mockups:   {have} found in {mockup_dir.relative_to(REPO)}")

    print("\ncoverage:")
    gaps = 0
    for slug, art in sorted(cards.items()):
        missing = [f["key"] for f in FORMATS if f["key"] not in art["products"]]
        nomock = [f["key"] for f in FORMATS if f["key"] not in art["mockups"]]
        gaps += len(missing)
        status = "all 5" if not missing else f"MISSING {', '.join(missing)}"
        if nomock:
            status += f"  [no mockup: {', '.join(nomock)}]"
        print(f"  {art['title']:<22} {len(art['products'])}/5  {status}")
    print(f"\n{gaps} missing listing(s) "
          f"— each is an unpriced product, invisible to the storefront.")

    if args.check:
        return 0 if gaps == 0 else 1

    payload = {"formats": FORMATS, "art": cards}
    body = json.dumps(payload, indent=1, ensure_ascii=False)
    out = (REPO / "shop-data.js")
    out.write_text(
        "/* GENERATED by tools/build-shop-data.py -- do not edit by hand.\n"
        "   Re-run after any price or product change in Square. */\n"
        f"window.PRINT_SHOP = {body};\n")
    print(f"\nwrote {out.relative_to(REPO)} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
