#!/usr/bin/env python3
"""Download one product mockup per artwork+format from Printful.

Printful generates a mockup for every synced variant. We only need one per
artwork+format — a 12x16 canvas and an 18x24 canvas photograph identically —
so this takes the first variant that has one and reuses it across that
format's three sizes. That keeps 70 images instead of 210.

    export PRINTFUL_TOKEN=...          # never commit this
    python3 tools/fetch-mockups.py

Writes Images/mockups/<artwork-slug>-<format>.webp, sized to match the buy
dialog. Re-run after changing artwork in Printful; it skips files that already
exist unless --force is given.

The token needs read access to the store. Create one at
Printful -> Settings -> Developers -> Add API key.
"""

import argparse
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import unicodedata

STORE_ID = "18521974"          # Miles2Walk
API = "https://api.printful.com"
REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "Images" / "mockups"

# Printful sync-product name suffix -> the format key used in shop-data.js
FORMATS = {
    "Poster": "poster",
    "Framed Poster": "framed-poster",
    "Canvas": "canvas",
    "Framed Canvas": "framed-canvas",
    "Metal": "metal",
}

# Printful item name -> the slug used in shop.html's data-art. See the same
# table in build-shop-data.py; keep them in step.
SLUG_ALIASES = {"naeglins-bakery": "naegelins-bakery"}

# Longest edge, and WebP quality. Measured against the site's existing
# derivatives — don't change without re-measuring.
MAX_EDGE = 700
QUALITY = 80


def slugify(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def api(token, path):
    r = subprocess.run(
        ["curl", "-sSf", "--max-time", "60",
         "-H", f"Authorization: Bearer {token}",
         "-H", f"X-PF-Store-Id: {STORE_ID}",
         f"{API}{path}"],
        capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"Printful API failed on {path}: {r.stderr.strip()}")
    return json.loads(r.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="re-download even if the .webp already exists")
    args = ap.parse_args()

    token = os.environ.get("PRINTFUL_TOKEN")
    if not token:
        sys.exit("set PRINTFUL_TOKEN in the environment (see the docstring)")

    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow required. On this Mac it lives in /usr/local/bin/python3 "
                 "— run that interpreter, not /usr/bin/python3.")

    OUT.mkdir(parents=True, exist_ok=True)
    listing = api(token, "/sync/products?limit=100")["result"]
    print(f"{len(listing)} sync products")

    written = skipped = 0
    missing = []
    for i, prod in enumerate(listing, 1):
        name = prod["name"]
        try:
            art, fmt = name.rsplit(" - ", 1)
            key = FORMATS[fmt.strip()]
        except (ValueError, KeyError):
            missing.append(f"{name} (unrecognised name)")
            continue

        slug = slugify(art)
        slug = SLUG_ALIASES.get(slug, slug)
        dest = OUT / f"{slug}-{key}.webp"
        if dest.exists() and not args.force:
            skipped += 1
            continue

        detail = api(token, f"/sync/products/{prod['id']}")["result"]
        url = next((f["preview_url"]
                    for v in detail["sync_variants"]
                    for f in v.get("files", [])
                    if f.get("type") == "preview" and f.get("preview_url")), None)
        if not url:
            missing.append(f"{name} (no mockup generated)")
            continue

        raw = subprocess.run(["curl", "-sSf", "--max-time", "60", "-L", url],
                             capture_output=True)
        if raw.returncode:
            missing.append(f"{name} (download failed)")
            continue

        im = Image.open(io.BytesIO(raw.stdout)).convert("RGB")
        im.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
        im.save(dest, "WEBP", quality=QUALITY, method=6)
        written += 1
        time.sleep(0.45)          # Printful allows 120 calls/min
        if i % 20 == 0:
            print(f"  {i}/{len(listing)}")

    total = sum(f.stat().st_size for f in OUT.glob("*.webp"))
    count = len(list(OUT.glob("*.webp")))
    print(f"\nwrote {written}, skipped {skipped} existing")
    print(f"{count} mockups, {total/1e6:.2f} MB "
          f"({total/count/1024:.0f} KB average)" if count else "no mockups")
    if missing:
        print("\nno mockup for:", file=sys.stderr)
        for m in missing:
            print(f"    {m}", file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
