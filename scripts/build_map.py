#!/usr/bin/env python3
"""
APARADH — build a lightweight clickable India SVG map dataset.

Source geometry: geoBoundaries IND-ADM1 (DataMeet India community / ECI,
CC BY 2.5 IN) — Survey-of-India-based outline showing the official
Indian boundary (PoK within J&K, Ladakh as UT).

Output: data/india-map.json { paths, outer, markers, viewBox }
Paths are Douglas-Peucker simplified + quantized for web weight.
"""
import json, math, unicodedata

SRC = "data/raw/gb_ind_adm1_simp.geojson"
SRC_ADM0 = "data/raw/gb_ind_adm0.geojson"
OUT = "data/india-map.json"

def strip_diacritics(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def rings_of(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    if geom["type"] == "MultiPolygon":
        return [ring for poly in geom["coordinates"] for ring in poly]
    raise ValueError(geom["type"])

def perp_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == 0 and dy == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))

def douglas_peucker(pts, tol):
    if len(pts) <= 2:
        return pts
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = perp_dist(pts[i], pts[0], pts[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        left = douglas_peucker(pts[:idx + 1], tol)
        right = douglas_peucker(pts[idx:], tol)
        return left[:-1] + right
    return [pts[0], pts[-1]]

def main():
    d = json.load(open(SRC))
    # project: equirectangular centred on India
    lon0, lat0 = 78.0, 22.0
    kx = math.cos(math.radians(lat0))

    def proj(lon, lat):
        # SVG y grows downward: north (higher lat) must map to smaller y
        return ((lon - lon0) * kx, lat0 - lat)

    feats = []
    for f in d["features"]:
        name = strip_diacritics(f["properties"]["shapeName"])
        feats.append((name, rings_of(f["geometry"])))

    # fit viewBox
    xs, ys = [], []
    for _, rings in feats:
        for ring in rings:
            for lon, lat in ring:
                x, y = proj(lon, lat)
                xs.append(x); ys.append(y)
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    W, H, PAD = 1000, 920, 30
    sx = (W - 2 * PAD) / (maxx - minx)
    sy = (H - 2 * PAD) / (maxy - miny)
    s = min(sx, sy)
    ox = PAD - minx * s + ((W - 2 * PAD) - (maxx - minx) * s) / 2
    oy = PAD - miny * s + ((H - 2 * PAD) - (maxy - miny) * s) / 2

    def X(x): return round(x * s + ox, 1)
    def Y(y): return round(y * s + oy, 1)

    TOL = 1.6  # pixels; light touch — source is already simplified
    paths, centroids = {}, {}
    for name, rings in feats:
        parts, cx, cy, cn = [], 0.0, 0.0, 0
        for ring in rings:
            pts = [(X(x), Y(y)) for x, y in (proj(lon, lat) for lon, lat in ring)]
            simp = douglas_peucker(pts, TOL)
            if len(simp) < 3:
                continue
            parts.append("M" + "L".join(f"{x},{y}" for x, y in simp) + "Z")
            for (x, y) in simp:
                cx += x; cy += y; cn += 1
        paths[name] = "".join(parts)
        centroids[name] = [round(cx / cn, 1), round(cy / cn, 1)] if cn else [0, 0]

    # Outer boundary: geoBoundaries IND-ADM0 polygon (same official outline as
    # the ADM1 tiles — bbox verified identical). Project + lightly simplify.
    outer_paths = []
    a0 = json.load(open(SRC_ADM0))
    for f in a0["features"]:
        for ring in rings_of(f["geometry"]):
            pts = [(X(px), Y(py)) for px, py in (proj(lon, lat) for lon, lat in ring)]
            simp = douglas_peucker(pts, TOL)
            if len(simp) > 2:
                outer_paths.append("M" + "L".join(f"{x},{y}" for x, y in simp) + "Z")

    # markers for tiny UTs (true polygons kept too, markers aid clicking)
    tiny = ["Lakshadweep", "Puducherry", "Chandigarh",
            "Dadra and Nagar Haveli and Daman and Diu",
            "Andaman and Nicobar Islands"]
    markers = {n: centroids[n] for n in tiny if n in centroids}

    out = {"viewBox": f"0 0 {W} {H}", "paths": paths,
           "outer": "".join(outer_paths), "markers": markers,
           "names": sorted(paths)}
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    import os
    print(f"units: {len(paths)}, outer subpaths: {len(outer_paths)}, "
          f"size: {os.path.getsize(OUT)//1024} KB")

if __name__ == "__main__":
    main()
