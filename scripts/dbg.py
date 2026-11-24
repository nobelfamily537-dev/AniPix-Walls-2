import json, requests
UA = {"User-Agent": "AniPixWallpaperBot/1.0 (nobelfamily537@gmail.com)"}
r = requests.get("https://danbooru.donmai.us/posts.json",
    params={"tags": "akira_(manga) rating:general width:>=1080 height:>=1920 order:score", "limit": 5},
    headers=UA, timeout=60)
print("status", r.status_code)
d = r.json()
print("n", len(d))
if d:
    print("KEYS", sorted(d[0].keys()))
    for p in d[:4]:
        print({k: p.get(k) for k in ("id","width","height","rating","file_url","file_ext","md5","has_large_file","large_file_url","tag_string_character")})
