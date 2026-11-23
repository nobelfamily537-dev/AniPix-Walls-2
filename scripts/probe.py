#!/usr/bin/env python3
"""Probe wallhaven for clean portrait anime art for target series."""
import json, time, requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

QUERIES = {
 "akira": ["akira anime", "shotaro kaneda", "tetsuo shima"],
 "hajime no ippo": ["hajime no ippo", "ippo makunouchi", "takamura mamoru"],
 "dorohedoro": ["dorohedoro", "caiman dorohedoro", "nikkaido"],
 "nier automata": ["nier automata", "2b nier automata", "yorha"],
 "samurai champloo": ["samurai champloo", "mugen samurai champloo", "jin samurai champloo"],
 "shokugeki no soma": ["shokugeki no soma", "souma yukihira", "erina nakiri"],
 "tales from earthsea": ["tales from earthsea", "ged tales from earthsea"],
 "fruits basket": ["fruits basket", "tohru honda", "kyo sohma"],
 "love live": ["love live", "honoka kosaka", "maki nishikino", "nico yazawa"],
 "parasyte": ["parasyte", "shinichi izumi", "migi parasyte"],
}

def search(q):
    params = {"q": q, "categories": "010", "purity": "100",
              "sorting": "relevance", "order": "desc", "page": "1"}
    r = requests.get("https://wallhaven.cc/api/v1/search", params=params,
                     headers=UA, timeout=60)
    if r.status_code != 200:
        print("HTTP", r.status_code, q)
        return []
    return r.json().get("data", [])

for series, qs in QUERIES.items():
    print("#### SERIES:", series)
    for q in qs:
        try:
            items = search(q)
        except Exception as e:
            print("  ERR", q, e); continue
        print(f"  == {q!r} hits={len(items)}")
        for it in items[:8]:
            tags = ",".join(t["name"] for t in it.get("tags", []))
            print(f"    {it['id']} {it['dimension_x']}x{it['dimension_y']} | {tags[:120]}")
        time.sleep(2)
