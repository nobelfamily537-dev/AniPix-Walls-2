#!/usr/bin/env python3
import json, time, requests
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
Q = {
 "akira": ["akira","shotaro kaneda","tetsuo shima","akira neo tokyo"],
 "hajime no ippo": ["hajime no ippo","ippo","takamura","boxing anime"],
 "dorohedoro": ["dorohedoro","caiman","nikkaido","noi dorohedoro"],
 "nier automata": ["nier automata","2b","yorha","nier"],
 "samurai champloo": ["samurai champloo","mugen","jin samurai","fuu champloo"],
 "shokugeki no soma": ["shokugeki no soma","erina nakiri","souma","food wars"],
 "tales from earthsea": ["tales from earthsea","ged","therru","earthsea"],
 "fruits basket": ["fruits basket","tohru honda","kyo sohma","yuki sohma"],
 "love live": ["love live","maki nishikino","nico yazawa","honoka"],
 "parasyte": ["parasyte","shinichi izumi","migi","parasyt"],
}
def search(q, atleast, ratios="9x16"):
    p = {"q": q, "categories": "010", "purity": "100", "sorting": "relevance",
         "order": "desc", "page": "1", "ratios": ratios}
    if atleast: p["atleast"] = atleast
    r = requests.get("https://wallhaven.cc/api/v1/search", params=p, headers=UA, timeout=60)
    if r.status_code != 200: return None
    return r.json().get("data", [])
for s, qs in Q.items():
    tot = set()
    print("#### ", s)
    for q in qs:
        for atl in ("1080x1920", ""):
            d = search(q, atl)
            if d is None:
                print("   ERR", q); continue
            d = [x for x in d if x["dimension_y"] > x["dimension_x"] and x["dimension_y"] >= 1100]
            if atl == "":
                d = [x for x in d if x["id"] not in tot]
            print(f"   {q!r} atleast={atl or '-'} portrait={len(d)} " + " ".join(f"{x['id']}:{x['dimension_x']}x{x['dimension_y']}" for x in d[:12]))
            for x in d: tot.add(x["id"])
            time.sleep(1.5)
    print("   TOTAL UNIQUE:", len(tot))
