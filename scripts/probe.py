#!/usr/bin/env python3
import json, time, requests
UA = {"User-Agent": "AniPixWallpaperBot/1.0 (wallpaper indexing; contact nobelfamily537@gmail.com)"}
TAGS = {
 "akira": ["akira_(film)","akira_(manga)","kaneda_shotarou","shima_tetsuo"],
 "hajime no ippo": ["hajime_no_ippo"],
 "dorohedoro": ["dorohedoro"],
 "nier automata": ["nier:automata"],
 "samurai champloo": ["samurai_champloo"],
 "shokugeki no soma": ["shokugeki_no_souma"],
 "tales from earthsea": ["ged_senki","tales_from_earthsea"],
 "fruits basket": ["fruits_basket"],
 "love live": ["love_live!","love_live!_school_idol_project"],
 "parasyte": ["kiseijuu"],
}
def db(tag):
    try:
        r = requests.get("https://danbooru.donmai.us/posts.json",
            params={"tags": f"{tag} rating:general width:>=1080 height:>=1920", "limit": 100,
                    "only": "id,width,height,file_url,tag_string_character,tag_string_copyright"},
            headers=UA, timeout=60)
        if r.status_code != 200: return f"HTTP{r.status_code}", []
        return "ok", r.json()
    except Exception as e:
        return f"ERR {e}", []
def kona(tag):
    t = tag.replace("_", " ").replace(":", ":")
    try:
        r = requests.get("https://konachan.net/post.json",
            params={"tags": f"{t} rating:safe width:>=1080 height:>=1920", "limit": 100},
            headers=UA, timeout=60)
        if r.status_code != 200: return f"HTTP{r.status_code}", []
        return "ok", r.json()
    except Exception as e:
        return f"ERR {e}", []
def sb(tag):
    t = tag.replace("_", " ")
    try:
        r = requests.get("https://safebooru.org/index.php",
            params={"page":"dapi","s":"post","q":"index","json":1,"limit":100,"tags":f"{t} rating:safe"},
            headers=UA, timeout=60)
        if r.status_code != 200: return f"HTTP{r.status_code}", []
        j = r.json()
        return "ok", [p for p in j if int(p["width"])>=1080 and int(p["height"])>=1920 and int(p["height"])>int(p["width"])]
    except Exception as e:
        return f"ERR {e}", []
for s, cands in TAGS.items():
    print("####", s)
    for tag in cands:
        st, d = db(tag)
        print(f"  DB {tag}: {st} n={len(d)}")
        for p in d[:3]:
            print("    ", p["id"], f"{p['width']}x{p['height']}", (p.get("tag_string_character") or "")[:60], "|", (p.get("tag_string_copyright") or "")[:40])
        time.sleep(1.2)
        st, k = kona(tag)
        k = [x for x in k if x["height"]>x["width"]]
        print(f"  KONA {tag}: {st} n={len(k)}")
        time.sleep(1.2)
        st, b = sb(tag)
        print(f"  SB {tag}: {st} n={len(b)}")
        time.sleep(1.2)
