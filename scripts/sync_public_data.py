#!/usr/bin/env python3
"""APARADH — sync built data into public/ for the static site."""
import json, shutil, os

os.makedirs("public/data", exist_ok=True)

d = json.load(open("data/aparadh_2024.json"))
with open("public/data/aparadh_2024.json", "w") as f:
    json.dump(d, f, separators=(",", ":"))
shutil.copy("data/india-map.json", "public/data/india-map.json")

for p in ["public/data/aparadh_2024.json", "public/data/india-map.json"]:
    print(p, os.path.getsize(p) // 1024, "KB")
