# APARADH — Crime in India 2024, on the map

**अपराध.** A brutalist, dark, serif explorer of the National Crime Records Bureau's *Crime in India 2024* — every cognizable crime in the country, mapped state-by-state on the official Indian outline.

**Live:** https://aparadh.vercel.app

## What it is

- **State-clickable SVG map of India** (official outline — PoK within J&K, Ladakh as UT) with choropleth by crime *rate* for any of **24 crime heads**
- **National dashboard**: 58,85,867 total crimes, 2022–2024 trend, biggest year-on-year movers
- **State profiles**: cases, rate (with correct per-head denominator), all-India rank, 2022→2024 trend, IPC-vs-BNS split for 2024, all 24 heads
- **Sortable all-states table**, shareable deep links (`?head=cyber&state=Rajasthan`)
- **Methodology page** tracing every figure to its NCRB table and PDF page

## The data

**864 verified figures** — 24 crime heads × 36 states/UTs — parsed from NCRB *Crime in India 2024* (released 6 May 2026):

| Heads | NCRB tables |
|---|---|
| All cognizable crimes, IPC/BNS, SLL | 1A.3, 1A.1, 1A.2 (Vol I) |
| Murder; Kidnapping & abduction | 2A.1, 2C.1 (Vol I) |
| Crimes vs women, children | 3A.1, 4A.1 (Vol I) |
| Crimes vs senior citizens, SCs, STs | 6A.1, 7A.1, 7C.1 (Vol II) |
| Economic offences, Cybercrime, Offences vs state | 8A.1, 9A.1, 10A.1 (Vol II) |
| Rape, attempt to rape, dowry deaths, cruelty, rioting, theft, extortion, robbery, dacoity, burglary, cheating & fraud | 1A.4 (Vol I) |

**Zero fabricated data.** Every table was integrity-checked: parsed state rows sum to the NCRB's own TOTAL rows — all 24 tables pass, zero rows dropped. Spot-checked against published national figures (27,049 murders; 4,41,534 crimes vs women; 1,01,928 cybercrimes…).

Source PDFs (public, direct download, no login):
- https://www.ncrb.gov.in/uploads/files/1CrimeinIndia2024-VolumeI.pdf
- https://www.ncrb.gov.in/uploads/files/2CrimeinIndia2024-VolumeII.pdf

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install pdfplumber
# download the two PDFs above into data/raw/ as CII2024-Vol-I.pdf / CII2024-Vol-II.pdf
.venv/bin/python scripts/parse_cii2024.py      # → data/aparadh_2024.json
.venv/bin/python scripts/build_map.py          # → data/india-map.json
.venv/bin/python scripts/sync_public_data.py   # → public/data/
```

Map geometry: geoBoundaries IND-ADM1 (DataMeet India / ECI), country outline IND-ADM0 — CC BY 2.5 IN.

## Design

Strict anti-AI brutalism: dark warm-black, off-white ink, slab serif (Alfa Slab One + Zilla Slab), flat discrete choropleth fills, 3px borders, sharp corners. No gradients, no glass, no glow, no Inter/Space Grotesk/Plex.

## Layout

```
public/            # the static site (deployed to Vercel as-is, no build step)
  index.html app.js style.css methodology.html favicon.svg
  data/aparadh_2024.json data/india-map.json
scripts/           # parser, map builder, data sync
data/              # built datasets (raw PDFs excluded — download via URLs above)
```

Not an official government website.
