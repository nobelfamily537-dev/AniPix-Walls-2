#!/usr/bin/env python3
"""Fetch clean portrait anime art for under-covered series, normalise to
1080x1920 WebP + 360x640 thumbs, write new files into this repo (volume 2)
and emit batch.json describing them. Never deletes anything."""
import io, json, os, re, time, hashlib, colorsys
import requests
from PIL import Image

UA = {"User-Agent": "AniPixWallpaperBot/1.0 (wallpaper indexing; nobelfamily537@gmail.com)"}

SPECS = {
 "akira": ("anime", ["akira_(manga)", "akira_(film)", "kaneda_shoutarou_(akira)", "shima_tetsuo",
                    "kei_(akira)", "akira"]),
 "hajime no ippo": ("anime", ["hajime_no_ippo", "makunouchi_ippo", "takamura_mamoru",
                              "kumi_mashiba", "aoki_masaru"]),
 "dorohedoro": ("anime", ["dorohedoro", "nikaidou", "caiman_(dorohedoro)", "noi_(dorohedoro)",
                          "shin_(dorohedoro)", "ebisu_(dorohedoro)"]),
 "nier automata": ("game", ["nier_(series)", "yorha_no.2_type_b", "nier_automata",
                            "yorha_no.9_type_s", "kaine_(nier)", "devola_and_popola"]),
 "samurai champloo": ("anime", ["samurai_champloo", "mugen_(samurai_champloo)", "jin_(samurai_champloo)",
                                "fuu_(samurai_champloo)"]),
 "shokugeki no soma": ("anime", ["shokugeki_no_souma", "nakiri_erina", "yukihira_souma",
                                 "tadokoro_megumi", "nakiri_alice"]),
 "tales from earthsea": ("anime", ["ged_senki", "tales_from_earthsea", "therru", "arren_(earthsea)"]),
 "fruits basket": ("anime", ["fruits_basket", "honda_tohru", "sohma_kyou", "sohma_yuki", "sohma_shigure"]),
 "love live": ("anime", ["love_live!", "love_live!_school_idol_project", "yazawa_nico", "nishikino_maki",
                         "kousaka_honoka", "minami_kotori", "sonoda_umi", "ayase_eli"]),
 "parasyte": ("anime", ["kiseijuu", "izumi_shinichi", "migi_(parasyte)", "murano_satomi"]),
}
TARGET = 20
MIN_PER_SERIES = 8

BLOCK = {"text","english_text","watermark","web_address","logo","signature","artist_name",
         "comic","4koma","multiple_views","border","letterboxed","translated",
         "commentary","commentary_request","translation_request","character_request",
         "censored","bar_censor","mosaic_censoring","photo","realistic","screencap",
         "reference_sheet","character_sheet","chart","diagram","map","text_focus",
         "speech_bubble","thought_bubble","nameplate","magazine_(object)",
         "album_cover","movie_poster","title_screen","parody","meme"}
STYLE = ["anime art", "phone wallpaper", "vertical wallpaper", "digital art", "illustration"]
NSFW_TAGS = {"breasts","large_breasts","huge_breasts","cleavage","nipples","panties","ass","thighs",
             "bare_legs","underwear","bra","lingerie","navel","midriff","bikini","swimsuit","leotard",
             "sweat","wet","see-through","revealing_clothes","spread_legs","lying","on_back",
             "1girl","1boy","2girls","2boys","multiple_boys","multiple_girls","male_focus","female",
             "solo_focus","cowboy_shot","from_behind","from_side","from_above","from_below",
             "highres","absurdres","lowres","commentary","translation_request","official_art"}

def api(tags, page=1):
    for attempt in range(3):
        try:
            r = requests.get("https://danbooru.donmai.us/posts.json",
                             params={"tags": tags, "limit": 100, "page": page},
                             headers=UA, timeout=90)
        except Exception as e:
            print("  net err", e); time.sleep(5); continue
        if r.status_code == 200:
            try: return r.json()
            except Exception: return []
        if r.status_code == 429:
            time.sleep(10); continue
        print("  api", r.status_code, r.text[:110].replace("\n", " "))
        return []
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
            if k in ("red","orange","yellow") and l < 0.32: k = "dark " + k
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
        th = int(round(w*16/9))
        if th < 1: return None
        top = (h-th)//2; im = im.crop((0, top, w, top+th))
    im = im.resize((1080, 1920), Image.LANCZOS)
    full = io.BytesIO(); im.save(full, "WEBP", quality=85, method=6)
    thumb = io.BytesIO(); im.resize((360, 640), Image.LANCZOS).save(thumb, "WEBP", quality=80, method=6)
    return full.getvalue(), thumb.getvalue(), im

def has_text(im):
    try:
        import pytesseract
        t = pytesseract.image_to_string(im, config="--psm 11")
        return len(re.sub(r"[^A-Za-z0-9]", "", t or "")) >= 16
    except Exception:
        return False

def main():
    existing = set()
    for d in ("anime", "game"):
        if os.path.isdir(d): existing |= set(os.listdir(d))
    seen = set(); batch = []; skipped = {}; why = {}
    for series, (cat, cands) in SPECS.items():
        os.makedirs(cat, exist_ok=True)
        got = 0
        for tag in cands:
            if got >= TARGET: break
            posts = []
            for q in (f"{tag} solo rating:general width:>=1080 height:>=1920 order:score",
                      f"{tag} rating:general width:>=1080 height:>=1920 order:score",
                      f"{tag} rating:general width:>=900 height:>=1500 order:score"):
                more = api(q) or []
                time.sleep(1.5)
                if len(more) >= 20 and len(posts) < 40:
                    more += api(q, page=2) or []
                    time.sleep(1.5)
                have = {x.get("id") for x in posts}
                posts += [x for x in more if x.get("id") not in have]
                if len(posts) >= 60: break
            ok = []
            for p in posts:
                if not p.get("file_url"): continue
                if p.get("rating") not in (None, "g"): continue
                if p.get("file_ext") not in ("jpg", "jpeg", "png", "webp"): continue
                w = p.get("image_width") or 0; h = p.get("image_height") or 0
                if w < 900 or h < 1500 or h <= w: continue
                if not (0.46 <= w / h <= 0.74): continue
                if (p.get("tag_count_character") or 0) > 6: continue
                gen = set((p.get("tag_string_general") or "").split())
                hit = gen & BLOCK
                if hit:
                    k = ",".join(sorted(hit))[:40]; why[k] = why.get(k, 0) + 1; continue
                ok.append(p)
            print(f"  {series} :: {tag} -> {len(posts)} raw, {len(ok)} usable")
            if why: print("    blocked:", sorted(why.items(), key=lambda x: -x[1])[:6])
            for p in ok:
                if got >= TARGET: break
                if p.get("md5") in seen: continue
                try:
                    r = requests.get(p["file_url"], headers=UA, timeout=120)
                    if r.status_code != 200 or len(r.content) < 40000: continue
                except Exception: continue
                try: out = process(r.content)
                except Exception: out = None
                if not out: continue
                full, th, im = out
                if has_text(im):
                    print("    skip(text)", p["id"]); continue
                wid = "wpx" + hashlib.sha1(full).hexdigest()[:10]
                if f"{wid}.webp" in existing: continue
                open(f"{cat}/{wid}.webp", "wb").write(full)
                open(f"{cat}/{wid}_thumb.webp", "wb").write(th)
                existing |= {f"{wid}.webp", f"{wid}_thumb.webp"}
                seen.add(p.get("md5"))
                chars = [c.replace("_"," ") for c in (p.get("tag_string_character") or "").split()][:1]
                gen = []
                for g in (p.get("tag_string_general") or "").split():
                    g2 = g.replace("_"," ")
                    if g in BLOCK or g in NSFW_TAGS or g2 in NSFW_TAGS or g.startswith("-"): continue
                    if not (3 <= len(g2) <= 26) or g2 in gen: continue
                    gen.append(g2)
                    if len(gen) >= 6: break
                tags = []
                for t in chars + [series] + gen + [colour_name(im)] + STYLE:
                    t = t.strip().lower()
                    if t and t not in tags: tags.append(t)
                tags = tags[:15]
                for extra in ("solo","portrait","aesthetic","character art","wallpaper","detailed"):
                    if len(tags) >= 10: break
                    if extra not in tags: tags.append(extra)
                batch.append({"id": wid, "category": cat, "series": series,
                              "tags": ",".join(tags[:15]), "src": str(p["id"]),
                              "dims": f"{p.get('image_width')}x{p.get('image_height')}"})
                got += 1
                time.sleep(0.5)
        print(f"SERIES RESULT {series}: {got}")
        if got < MIN_PER_SERIES:
            for e in [b for b in batch if b["series"] == series]:
                for f in (f"{e['category']}/{e['id']}.webp", f"{e['category']}/{e['id']}_thumb.webp"):
                    if os.path.exists(f): os.remove(f)
            batch = [b for b in batch if b["series"] != series]
            skipped[series] = got
    json.dump({"date": "2026-11-24", "count": len(batch), "entries": batch, "skipped": skipped},
              open("batch.json", "w"), indent=1)
    print("TOTAL", len(batch), "skipped:", skipped)
    for s in SPECS: print("  per-series", s, sum(1 for b in batch if b["series"] == s))

main()
