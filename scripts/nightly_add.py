#!/usr/bin/env python3
"""Fetch clean portrait anime art for under-covered series, normalise to
1080x1920 WebP + 360x640 thumbs, write into this repo (volume 2) and emit
batch.json describing what was added. No deletions: only new files."""
import io, json, os, re, sys, time, hashlib, colorsys
import requests
from PIL import Image

UA = {"User-Agent": "AniPixWallpaperBot/1.0 (wallpaper indexing; nobelfamily537@gmail.com)"}
CAT_DIR = {"anime": "anime", "game": "game"}

SPECS = {
 "akira": ("anime", ["akira_(manga)", "akira_(film)", "akira", "kaneda_shotarou"]),
 "hajime no ippo": ("anime", ["hajime_no_ippo", "makunouchi_ippo", "takamura_mamoru"]),
 "dorohedoro": ("anime", ["dorohedoro", "caiman_(dorohedoro)", "nikkaido"]),
 "nier automata": ("game", ["nier:automata", "2b_(nier:automata)", "yorha_no.2_type_b"]),
 "samurai champloo": ("anime", ["samurai_champloo", "mugen_(samurai_champloo)", "jin_(samurai_champloo)"]),
 "shokugeki no soma": ("anime", ["shokugeki_no_souma", "nakiri_erina", "yukihira_souma"]),
 "tales from earthsea": ("anime", ["ged_senki", "tales_from_earthsea", "therru"]),
 "fruits basket": ("anime", ["fruits_basket", "honda_tohru", "sohma_kyou"]),
 "love live": ("anime", ["love_live!", "love_live!_school_idol_project", "nishikino_maki", "yazawa_nico"]),
 "parasyte": ("anime", ["kiseijuu", "izumi_shinichi", "migi_(parasyte)"]),
}
TARGET = 15          # aim per series
MIN_PER_SERIES = 8   # below this we skip the series
EXCL = ("-text -english_text -watermark -web_address -logo -signature -artist_name "
        "-comic -4koma -multiple_views -border -translated -commentary -character_request "
        "-sketch -monochrome -greyscale")
BAD_GENERAL = {"highres","absurdres","commentary","commentary_request","translation_request",
               "bad_id","bad_pixiv_id","bad_twitter_id","bad_link","artist_name","web_address",
               "text","english_text","watermark","logo","signature","border","letterboxed",
               "comic","4koma","multiple_views","sketch","monochrome","greyscale","censored",
               "bar_censor","mosaic_censoring","official_art","revision","edit","third-party_edit",
               "twitter_username","patreon_username","1boy","male_focus","photo","realistic"}
STYLE = ["anime art","phone wallpaper","vertical wallpaper","digital art","illustration"]

def api(tags, limit=100, page=1):
    r = requests.get("https://danbooru.donmai.us/posts.json",
                     params={"tags": tags, "limit": limit, "page": page},
                     headers=UA, timeout=90)
    if r.status_code == 429:
        time.sleep(8); return None
    if r.status_code != 200:
        print("  api http", r.status_code, r.text[:160].replace("\n", " ")); return []
    try: return r.json()
    except Exception: return []

def colour_name(im):
    small = im.resize((48, 84))
    hh = {}
    for r, g, b in small.convert("RGB").getdata():
        h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
        if l < 0.10: k = "black"
        elif l > 0.92 and s < 0.12: k = "white"
        elif s < 0.12: k = "grey"
        else:
            deg = h*360
            k = ("red" if deg < 15 or deg >= 345 else "orange" if deg < 45 else "yellow" if deg < 70
                 else "green" if deg < 165 else "teal" if deg < 195 else "cyan" if deg < 215
                 else "blue" if deg < 255 else "purple" if deg < 290 else "magenta" if deg < 320
                 else "pink")
            if k in ("red","orange","yellow") and l < 0.30: k = "dark " + k
        hh[k] = hh.get(k, 0) + 1
    return max(hh, key=hh.get) if hh else "colourful"

def process(raw):
    im = Image.open(io.BytesIO(raw))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (0, 0, 0))
        bg.paste(im, mask=im.split()[-1]); im = bg
    else:
        im = im.convert("RGB")
    w, h = im.size
    if w < 900 or h < 1600 or h <= w: return None
    if not (0.46 <= w/h <= 0.74): return None
    tw = int(round(h * 9 / 16))
    if w >= tw:
        left = (w - tw)//2; im = im.crop((left, 0, left + tw, h))
    else:
        th = int(round(w * 16 / 9)); top = (h - th)//2
        if th < 1: return None
        im = im.crop((0, top, w, top + th))
    im = im.resize((1080, 1920), Image.LANCZOS)
    full = io.BytesIO(); im.save(full, "WEBP", quality=85, method=6)
    thumb = im.resize((360, 640), Image.LANCZOS)
    th = io.BytesIO(); thumb.save(th, "WEBP", quality=80, method=6)
    return full.getvalue(), th.getvalue(), im

def ocr_has_text(im):
    try:
        import pytesseract
        txt = pytesseract.image_to_string(im, config="--psm 11")
        clean = re.sub(r"[^A-Za-z0-9]", "", txt or "")
        return len(clean) >= 14
    except Exception:
        return False

def main():
    existing = set(os.listdir("anime")) | set(os.listdir("game")) if os.path.isdir("anime") else set()
    seen_md5 = set()
    batch, skipped = [], {}
    for series, (cat, cands) in SPECS.items():
        d = CAT_DIR[cat]; os.makedirs(d, exist_ok=True)
        got, tried_tags = 0, []
        for tag in cands:
            if got >= TARGET: break
            q = f"{tag} rating:general width:>=1080 height:>=1920 order:score {EXCL}"
            posts = api(q) or []
            time.sleep(1.2)
            if not posts:
                q2 = f"{tag} rating:general width:>=1080 height:>=1920 {EXCL}"
                posts = api(q2) or []
                time.sleep(1.2)
            posts = [p for p in posts if p.get("file_url") and p.get("width") and p.get("height")]
            print(f"  {series} :: {tag} -> {len(posts)} candidates")
            tried_tags.append((tag, len(posts)))
            for p in posts:
                if got >= TARGET: break
                if p["md5"] in seen_md5: continue
                try:
                    r = requests.get(p["file_url"], headers=UA, timeout=120)
                    if r.status_code != 200 or len(r.content) < 40000: continue
                except Exception:
                    continue
                try:
                    out = process(r.content)
                except Exception:
                    out = None
                if not out: continue
                full, th, im = out
                if ocr_has_text(im):
                    print("    skip (text)", p["id"]); continue
                wid = "wpx" + hashlib.sha1(full).hexdigest()[:10]
                if f"{wid}.webp" in existing or f"{wid}_thumb.webp" in existing: continue
                open(f"{d}/{wid}.webp", "wb").write(full)
                open(f"{d}/{wid}_thumb.webp", "wb").write(th)
                existing.add(f"{wid}.webp"); existing.add(f"{wid}_thumb.webp")
                seen_md5.add(p["md5"])
                chars = [c.replace("_", " ") for c in (p.get("tag_string_character") or "").split() if c][:1]
                gen = []
                for g in (p.get("tag_string_general") or "").split():
                    g2 = g.replace("_", " ")
                    if g in BAD_GENERAL or g2 in BAD_GENERAL: continue
                    if g.startswith("-") or len(g2) < 3 or len(g2) > 26: continue
                    if g2 not in gen: gen.append(g2)
                    if len(gen) >= 6: break
                tags = []
                for t in chars + [series] + gen + [colour_name(im)] + STYLE:
                    t = t.strip().lower()
                    if t and t not in tags: tags.append(t)
                tags = tags[:15]
                while len(tags) < 10:
                    for extra in ("solo","portrait","aesthetic","character art","wallpaper"):
                        if extra not in tags: tags.append(extra)
                        if len(tags) >= 10: break
                batch.append({"id": wid, "category": d, "series": series, "tags": ",".join(tags),
                              "src": p["id"], "dims": f"{p['width']}x{p['height']}"})
                got += 1
                time.sleep(0.4)
        print(f"SERIES RESULT {series}: {got}")
        if got < MIN_PER_SERIES:
            for e in [b for b in batch if b["series"] == series]:
                for f in (f"{CAT_DIR[cat]}/{e['id']}.webp", f"{CAT_DIR[cat]}/{e['id']}_thumb.webp"):
                    if os.path.exists(f): os.remove(f)
            batch = [b for b in batch if b["series"] != series]
            skipped[series] = got
    json.dump({"date": "2026-11-24", "count": len(batch), "entries": batch,
               "skipped": skipped}, open("batch.json", "w"), indent=1)
    print("TOTAL", len(batch), "skipped:", skipped)
    for s in SPECS:
        print("  per-series", s, sum(1 for b in batch if b["series"] == s))

main()
