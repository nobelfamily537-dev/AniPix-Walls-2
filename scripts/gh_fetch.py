#!/usr/bin/env python3
"""Fetch anime wallpapers from per-series GitHub repos.

GitHub is the one image host the sandbox can reach. Big generic wallpaper repos
are flat and unlabelled, but searching "<series> wallpaper" turns up small repos
named after the series itself - so the series name comes from the search term
and no image recognition is needed.

Skips repos that are apps rather than image dumps (low image-to-file ratio).
"""
import os, io, json, time, hashlib, subprocess, urllib.request, urllib.error
from PIL import Image, ImageOps

SERIES = [s.strip() for s in os.environ.get("SERIES", "").split(",") if s.strip()]
PER = int(os.environ.get("PER_SERIES", "6"))
UA = {"User-Agent": "AniPixBot/1.0"}
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
OUT = "staging"
os.makedirs(OUT, exist_ok=True)


def gh(*a):
    r = subprocess.run(["gh", "api"] + list(a), capture_output=True, text=True)
    return r.stdout


def search_repos(term):
    q = urllib.request.quote(f"{term} wallpaper")
    out = gh(f"search/repositories?q={q}&sort=stars&per_page=8")
    try:
        return json.loads(out).get("items", [])
    except Exception:
        return []


def image_files(repo, branch):
    out = gh(f"repos/{repo}/git/trees/{branch}?recursive=1")
    try:
        tree = json.loads(out).get("tree", [])
    except Exception:
        return []
    blobs = [t["path"] for t in tree if t.get("type") == "blob"]
    if not blobs:
        return []
    imgs = [p for p in blobs if p.lower().endswith(IMG_EXT)]
    if len(imgs) < 4:
        return []
    # skip app repos: images must be most of the tree
    if len(imgs) / len(blobs) < 0.5:
        return []
    return imgs


def process(url, term, seen):
    wid = "wg" + hashlib.md5(url.encode()).hexdigest()[:9]
    if wid in seen:
        return None
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 40000:
        return None
    im = Image.open(io.BytesIO(data)).convert("RGB")
    if im.width < 700 or im.height < 1000:
        return None
    full = ImageOps.fit(im, (1080, 1920), method=Image.LANCZOS, centering=(0.5, 0.36))
    full.save(f"{OUT}/{wid}.webp", "WEBP", quality=85, method=6)
    full.resize((360, 640), Image.LANCZOS).save(f"{OUT}/{wid}_thumb.webp", "WEBP", quality=80, method=6)
    seen.add(wid)
    return {"id": wid, "series": term,
            "tags": [term.lower(), "anime", "portrait", "wallpaper"]}


manifest = []
seen = set()
for term in SERIES:
    got = 0
    repos = search_repos(term)
    print(f"\n{term!r}: {len(repos)} repos found")
    for rp in repos:
        if got >= PER:
            break
        name, branch = rp["full_name"], rp.get("default_branch", "main")
        imgs = image_files(name, branch)
        if not imgs:
            print(f"   skip {name} (not an image repo)")
            continue
        print(f"   using {name} ({len(imgs)} images)")
        for p in imgs:
            if got >= PER:
                break
            url = f"https://raw.githubusercontent.com/{name}/{branch}/{urllib.request.quote(p)}"
            try:
                e = process(url, term, seen)
                if e:
                    e["repo"] = name
                    manifest.append(e)
                    got += 1
            except Exception as ex:
                pass
            time.sleep(0.05)
    print(f"   -> kept {got}")

json.dump(manifest, open(f"{OUT}/manifest.json", "w"), indent=1)
print(f"\nTOTAL: {len(manifest)}")
