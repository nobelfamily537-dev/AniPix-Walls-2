#!/usr/bin/env python3
"""Fetch anime wallpapers from the Wallhaven API and stage them as WebP.

Runs on GitHub Actions, not in the agent sandbox: the sandbox egress policy
blocks wallhaven.cc, pinterest.com, danbooru and most other image hosts, so
this is the only place the fetch can happen.

Writes into staging/ and a staging/manifest.json that the caller uses to append
index entries. Does not touch wallpapers.json - that lives in AniPix-Walls and
is updated separately.

Env:
  SERIES      comma-separated search terms (required)
  PER_SERIES  max wallpapers per term (default 8)
  MAX_TOTAL   hard cap for the whole run (default 120)
"""
import os, sys, json, io, time, hashlib, re
import requests
from PIL import Image, ImageOps

SERIES = [s.strip() for s in os.environ.get("SERIES", "").split(",") if s.strip()]
PER = int(os.environ.get("PER_SERIES", "8"))
MAXT = int(os.environ.get("MAX_TOTAL", "120"))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
API = "https://wallhaven.cc/api/v1/search"

if not SERIES:
    sys.exit("SERIES is empty")

os.makedirs("staging", exist_ok=True)
manifest = []
seen_ids = set()

# skip anything already in the index
existing = set()
if os.path.exists("existing_ids.json"):
    existing = set(json.load(open("existing_ids.json")))

BAD_TAG = re.compile(r"\b(?:text|watermark|logo|signature|scan|sketch|monochrome|greyscale|grayscale)\b", re.I)


def search(term, atleast):
    params = {"q": term, "categories": "010", "purity": "100",
              "sorting": "relevance", "order": "desc", "page": "1"}
    if atleast:
        params["atleast"] = atleast
    r = requests.get(API, params=params, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json().get("data", [])


def process(item, term):
    """Download, crop to 9:16, save WebP full + thumb. Returns entry or None."""
    wid = "w2" + hashlib.md5(item["id"].encode()).hexdigest()[:9]
    if wid in existing or wid in seen_ids:
        return None
    resp = requests.get(item["path"], headers=UA, timeout=90)
    resp.raise_for_status()
    if len(resp.content) < 40000:
        return None
    im = Image.open(io.BytesIO(resp.content)).convert("RGB")
    if im.width < 700 or im.height < 1000:
        return None

    full = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS, centering=(0.5, 0.36))
    full.save(f"staging/{wid}.webp", "WEBP", quality=85, method=6)
    full.resize((360, 640), Image.LANCZOS).save(
        f"staging/{wid}_thumb.webp", "WEBP", quality=80, method=6)

    tags = []
    for t in item.get("tags", []):
        n = (t.get("name") or "").strip().lower()
        if not n or BAD_TAG.search(n):
            continue
        n = n.replace("_", " ")
        if len(n) > 2 and n not in tags:
            tags.append(n)
    tags = tags[:10]
    series_tag = term.lower()
    if series_tag not in tags:
        tags.insert(0, series_tag)

    seen_ids.add(wid)
    return {"id": wid, "series": term, "wallhaven": item["id"],
            "res": f'{item.get("dimension_x")}x{item.get("dimension_y")}',
            "tags": tags, "src_page": item.get("url", "")}


for term in SERIES:
    if len(manifest) >= MAXT:
        break
    items = []
    for atleast in ("1200x1800", "800x1200", ""):
        try:
            items = search(term, atleast)
        except Exception as e:
            print(f"  APIERR {term!r}: {e}")
            items = []
        print(f"  {term!r} atleast={atleast!r} hits={len(items)}")
        if len(items) >= 3:
            break
        time.sleep(1)

    got = 0
    for it in items:
        if got >= PER or len(manifest) >= MAXT:
            break
        try:
            entry = process(it, term)
            if entry:
                manifest.append(entry)
                got += 1
        except Exception as e:
            print(f"  IMGERR {it.get('id')}: {e}")
        time.sleep(0.3)
    print(f"QUERY {term!r}: kept={got}")

json.dump(manifest, open("staging/manifest.json", "w"), indent=1)
print(f"TOTAL staged: {len(manifest)}")
