#!/usr/bin/env python3
"""Strict fetch for Akira: must carry the akira copyright tag, no parody,
crossover or cosplay, at most 2 characters."""
import io, json, os, re, time, hashlib, colorsys
import requests
from PIL import Image

UA = {"User-Agent": "AniPixWallpaperBot/1.0 (wallpaper indexing; nobelfamily537@gmail.com)"}
COPY = {"akira_(manga)", "akira_(film)"}
QUERIES = ["akira_(manga) solo", "akira_(film) solo", "kaneda_shoutarou_(akira)",
           "shima_tetsuo", "kei_(akira)", "akira_(manga)", "akira_(film)"]
BLOCK = {"text","english_text","watermark","web_address","logo","signature","artist_name",
         "comic","4koma","multiple_views","border","translated","commentary","translation_request",
         "parody","crossover","cosplay","akira_slide","reference","meme","screencap","photo",
         "realistic","furry","pokemon","hatsune_miku","vocaloid","jojo_no_kimyou_na_bouken",
         "bad_anatomy","bad_hands","chibi_inset","multiple_views","character_sheet"}
STYLE = ["anime art","phone wallpaper","vertical wallpaper","digital art","illustration"]
SERIES = "akira"

def api(tags, page=1):
    for _ in range(3):
        try:
            r = requests.get("https://danbooru.donmai.us/posts.json",
                             params={"tags": tags, "limit": 100, "page": page},
                             headers=UA, timeout=90)
        except Exception:
            time.sleep(5); continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            time.sleep(10); continue
        print("  api", r.status_code, r.text[:120]); return []
    return []

def colour_name(im):
    small = im.resize((48, 84)); hh = {}
    for r, g, b in small.convert("RGB").getdata():
        h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
        if l < 0.10: k = "black"
        elif l > 0.92 and s < 0.12: k = "white"
        elif s < 0.12: k = "grey"
        else:
            deg = h*360
            k = ("red" if deg < 15 or deg >= 345 else "orange" if deg < 45 else "yellow" if deg < 70
                 else "green" if deg < 165 else "teal" if deg < 195 else "cyan" if deg < 215
                 else "blue" if deg < 255 else "purple" if deg < 290 else "magenta" if deg < 320 else "pink")
        hh[k] = hh.get(k, 0) + 1
    return max(hh, key=hh.get) if hh else "colourful"

def process(raw):
    im = Image.open(io.BytesIO(raw))
    if im.mode in ("RGBA","LA","P"):
        im = im.convert("RGBA"); bg = Image.new("RGB", im.size, (0,0,0))
        bg.paste(im, mask=im.split()[-1]); im = bg
    else:
        im = im.convert("RGB")
    w, h = im.size
    if w < 900 or h < 1500 or h <= w: return None
    if not (0.46 <= w/h <= 0.74): return None
    tw = int(round(h*9/16))
    if w >= tw:
        left = (w-tw)//2; im = im.crop((left, 0, left+tw, h))
    else:
        th = int(round(w*16/9)); top = (h-th)//2; im = im.crop((0, top, w, top+th))
    im = im.resize((1080, 1920), Image.LANCZOS)
    full = io.BytesIO(); im.save(full, "WEBP", quality=85, method=6)
    th = io.BytesIO(); im.resize((360, 640), Image.LANCZOS).save(th, "WEBP", quality=80, method=6)
    return full.getvalue(), th.getvalue(), im

def has_text(im):
    try:
        import pytesseract
        return len(re.sub(r"[^A-Za-z0-9]", "", pytesseract.image_to_string(im, config="--psm 11") or "")) >= 16
    except Exception:
        return False

existing = set(os.listdir("anime"))
seen, batch, got = set(), [], 0
for q in QUERIES:
    if got >= 20: break
    posts = api(f"{q} rating:general width:>=1080 height:>=1920 order:score")
    time.sleep(1.5)
    posts += [p for p in (api(f"{q} rating:general width:>=900 height:>=1500 order:score") or [])
              if p.get("id") not in {x.get("id") for x in posts}]
    time.sleep(1.5)
    ok = []
    for p in posts:
        if not p.get("file_url") or p.get("rating") != "g": continue
        if p.get("file_ext") not in ("jpg","jpeg","png","webp"): continue
        if not (set((p.get("tag_string_copyright") or "").split()) & COPY): continue
        if (p.get("tag_count_character") or 0) > 2: continue
        w, h = p.get("image_width") or 0, p.get("image_height") or 0
        if w < 900 or h < 1500 or h <= w: continue
        if not (0.46 <= w/h <= 0.74): continue
        gen = set((p.get("tag_string_general") or "").split())
        if gen & BLOCK: continue
        ok.append(p)
    print(f"  {q} -> {len(posts)} raw, {len(ok)} usable")
    for p in ok:
        if got >= 20: break
        if p["md5"] in seen: continue
        try:
            r = requests.get(p["file_url"], headers=UA, timeout=120)
            if r.status_code != 200 or len(r.content) < 40000: continue
        except Exception: continue
        try: out = process(r.content)
        except Exception: out = None
        if not out: continue
        full, th, im = out
        if has_text(im): print("    skip(text)", p["id"]); continue
        wid = "wpx" + hashlib.sha1(full).hexdigest()[:10]
        if f"{wid}.webp" in existing: continue
        open(f"anime/{wid}.webp","wb").write(full)
        open(f"anime/{wid}_thumb.webp","wb").write(th)
        existing |= {f"{wid}.webp", f"{wid}_thumb.webp"}
        seen.add(p["md5"])
        chars = [c.replace("_"," ") for c in (p.get("tag_string_character") or "").split()][:1]
        gen = []
        for g in (p.get("tag_string_general") or "").split():
            g2 = g.replace("_"," ")
            if g in BLOCK or g.startswith("-") or not (3 <= len(g2) <= 26) or g2 in gen: continue
            gen.append(g2)
            if len(gen) >= 6: break
        tags = []
        for t in chars + [SERIES] + gen + [colour_name(im)] + STYLE:
            t = t.strip().lower()
            if t and t not in tags: tags.append(t)
        batch.append({"id": wid, "category": "anime", "series": SERIES,
                      "tags": ",".join(tags[:15]), "src": str(p["id"]),
                      "dims": f"{w}x{h}", "copyright": p.get("tag_string_copyright")})
        got += 1
        time.sleep(0.5)
json.dump({"date": "2026-11-24", "count": len(batch), "entries": batch}, open("akira.json","w"), indent=1)
print("AKIRA TOTAL", len(batch))
