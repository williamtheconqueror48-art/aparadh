#!/usr/bin/env python3
"""
APARADH — parse NCRB "Crime in India 2024" state/UT tables.

Sources (public, no access controls bypassed):
  Vol I : https://www.ncrb.gov.in/uploads/files/1CrimeinIndia2024-VolumeI.pdf
  Vol II: https://www.ncrb.gov.in/uploads/files/2CrimeinIndia2024-VolumeII.pdf

Parses the "State/UT-wise - 2022-2024" summary tables plus selected
crime-head column groups of TABLE 1A.4. Every value traces to a table id.
State sums are cross-checked against NCRB's own TOTAL rows.

Output: data/aparadh_2024.json
"""
import json, re, datetime
import pdfplumber

RAW = "data/raw"
OUT = "data/aparadh_2024.json"
VOL1 = f"{RAW}/CII2024-Vol-I.pdf"
VOL2 = f"{RAW}/CII2024-Vol-II.pdf"

CANON = {
    "A&N Islands": "Andaman and Nicobar Islands",
    "D&N Haveli and Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu",
    "Jammu & Kashmir": "Jammu and Kashmir",
}

def canon(name):
    return CANON.get(re.sub(r"\s+", " ", name).strip(),
                     re.sub(r"\s+", " ", name).strip())

def num(tok):
    tok = tok.replace(",", "").strip()
    if tok in ("-", "--", "NA", ""):
        return None
    try:
        return int(tok) if re.fullmatch(r"-?\d+", tok) else float(tok)
    except ValueError:
        return None

def is_numish(tok):
    return tok in ("-", "--", "NA") or num(tok) is not None

def trailing_nums(toks, counts):
    """Return (n, values) for the first matching trailing numeric block size."""
    for n in counts:
        if len(toks) >= n and all(is_numish(t) for t in toks[-n:]):
            return n, [num(t) for t in toks[-n:]]
    return 0, []

def total_label(line):
    toks = line.split()
    return " ".join(t for t in toks if not is_numish(t))

def total_vals(line):
    return [num(t) for t in line.split() if is_numish(t)]

# (key, label, table_id, pdf, page, rate_base, colspec)
# colspec: "std" = 2022,2023,2024,pop,rate[,chr]; "ipc_bns_split" = 2022,2023,ipc,bns,total,pop,rate,chr
SUMMARY_TABLES = [
    ("total",            "Total cognizable crimes (IPC/BNS + SLL)", "1A.3", VOL1, 47,  "per lakh population", "std"),
    ("ipc_bns",          "IPC/BNS crimes",                          "1A.1", VOL1, 45,  "per lakh population", "ipc_bns_split"),
    ("sll",              "SLL crimes",                              "1A.2", VOL1, 46,  "per lakh population", "std"),
    ("murder",           "Murder",                                  "2A.1", VOL1, 273, "per lakh population", "std"),
    ("kidnapping",       "Kidnapping & abduction",                  "2C.1", VOL1, 297, "per lakh population", "std"),
    ("women",            "Crime against women",                     "3A.1", VOL1, 329, "per lakh women population", "std"),
    ("children",         "Crime against children",                  "4A.1", VOL1, 463, "per lakh children population", "std"),
    ("senior_citizens",  "Crime against senior citizens (60+)",     "6A.1", VOL2, 73,  "per lakh senior-citizen population", "std"),
    ("sc",               "Crime/atrocities against SCs",            "7A.1", VOL2, 143, "per lakh SC population", "std"),
    ("st",               "Crime/atrocities against STs",             "7C.1", VOL2, 253, "per lakh ST population", "std"),
    ("economic",         "Economic offences",                       "8A.1", VOL2, 365, "per lakh population", "std"),
    ("cyber",            "Cyber crimes",                            "9A.1", VOL2, 421, "per lakh population", "std"),
    ("against_state",    "Offences against the state",              "10A.1", VOL2, 521, "per lakh population", "std"),
]

# (pdf page, head_index 0|1, key, label) within TABLE 1A.4 (Vol I), 2024 only
HEAD_TABLES = [
    (48,  0, "rape",           "Rape"),
    (48,  1, "attempt_rape",   "Attempt to commit rape"),
    (56,  0, "dowry_death",    "Dowry death"),
    (56,  1, "cruelty",        "Cruelty by husband or relatives"),
    (88,  0, "rioting",        "Rioting"),
    (99,  1, "theft",          "Theft"),
    (104, 0, "extortion",      "Extortion"),
    (104, 1, "robbery",        "Robbery"),
    (105, 0, "dacoity",        "Dacoity"),
    (109, 0, "burglary",       "Burglary"),
    (113, 1, "cheating_fraud", "Forgery, cheating & fraud"),
]

ROW_RE = re.compile(r"^(\d+)\s+(.*)$")
SECTION_MARKERS = ("STATES:", "States/UTs")

def get_text(pdf_path, page_no):
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[page_no - 1].extract_text() or ""
    # NCRB wraps "D&N Haveli and Daman & Diu" across lines in several ways:
    #   "D&N Haveli and\n31 <nums>\nDaman & Diu"
    #   "D&N Haveli and Daman &\n31 <nums>\nDiu"
    #   "D&N Haveli and Daman\n31 <nums>\n& Diu"
    # Join all variants into one clean row line before parsing.
    text = re.sub(
        r"D&N Haveli and(?: Daman)?(?: &)?\s*\n\s*31\s+([^\n]*?)\s*\n\s*(?:Daman & Diu|& Diu|Diu)?(?=\n)",
        lambda m: "31 D&N Haveli and Daman & Diu " + m.group(1),
        text)
    return text

def parse_state_rows(text, table_id, n_nums, page_no):
    """Generic state/UT row parser. Returns (rows, totals)."""
    lines = [l.strip() for l in text.split("\n")]
    try:
        s0 = next(i for i, l in enumerate(lines) if l in SECTION_MARKERS)
    except StopIteration:
        raise AssertionError(f"{table_id}: section marker missing p.{page_no}")
    rows, totals = [], {}
    in_data, pending, last = False, "", None
    for l in lines[s0 + 1:]:
        if not l:
            continue
        if l.startswith("TOTAL"):
            totals[total_label(l)] = total_vals(l)
            in_data = False
            pending = ""
            if "ALL INDIA" in l:
                break
            continue
        if l == "UNION TERRITORIES:":
            in_data = True
            pending = ""
            continue
        m = ROW_RE.match(l)
        if m:
            sl = int(m.group(1))
            if not in_data:
                if sl == 1:
                    in_data = True
                else:
                    continue
            toks = m.group(2).split()
            n, vals = trailing_nums(toks, n_nums)
            if n == 0:
                raise AssertionError(f"{table_id}: unparseable row p.{page_no}: {l!r}")
            name = " ".join(toks[:-n])
            if pending:
                name = (pending + " " + name).strip()
                pending = ""
            last = {"sl": sl, "state": canon(name), "ut": sl >= 29, "vals": vals}
            rows.append(last)
        elif in_data:
            # name fragment of the following row (the only wrapped name is
            # handled by get_text surgery; anything else prepends to next row)
            pending = (pending + " " + l).strip()
    return rows, totals

def main():
    states = {}
    india = {}
    skipped, notes = [], []

    for key, label, tid, pdf_path, page, rate_base, colspec in SUMMARY_TABLES:
        text = get_text(pdf_path, page)
        if f"TABLE {tid}" not in text:
            skipped.append({"table": tid, "key": key, "reason": f"header not on p.{page}"})
            continue
        try:
            rows, totals = parse_state_rows(text, tid, (8, 6, 5), page)
        except AssertionError as e:
            skipped.append({"table": tid, "key": key, "reason": str(e)})
            continue
        if len(rows) != 36:
            notes.append(f"{tid}: parsed {len(rows)} rows (expected 36)")
        for r in rows:
            st = states.setdefault(r["state"], {"heads": {}})
            v = r["vals"]
            if colspec == "ipc_bns_split":
                # 2022, 2023, ipc2024, bns2024, total2024, pop, rate[, chr]
                entry = {"c2022": v[0], "c2023": v[1], "ipc_2024": v[2],
                         "bns_2024": v[3], "c2024": v[4], "pop_lakh_2024": v[5],
                         "rate_2024": v[6]}
                if len(v) == 8:
                    entry["chargesheet_rate_2024"] = v[7]
            else:
                entry = {"c2022": v[0], "c2023": v[1], "c2024": v[2],
                         "pop_lakh_2024": v[3], "rate_2024": v[4]}
                if len(v) == 6:
                    entry["chargesheet_rate_2024"] = v[5]
            st["heads"][key] = entry
            if key == "total":
                st["pop_lakh_2024"] = entry["pop_lakh_2024"]
                st["sl"] = r["sl"]
        # integrity checks
        def ssum(pred, idx):
            return sum(r["vals"][idx] for r in rows if pred(r) and r["vals"][idx] is not None)
        cidx = 4 if colspec == "ipc_bns_split" else 2
        checks = [
            (lambda r: not r["ut"], "TOTAL STATE(S)"),
            (lambda r: r["ut"], "TOTAL UT(S)"),
            (lambda r: True, "TOTAL ALL INDIA"),
        ]
        for pred, tlabel in checks:
            tv = totals.get(tlabel)
            if tv and len(tv) > cidx and tv[cidx] is not None:
                s = ssum(pred, cidx)
                if abs(s - tv[cidx]) > 0:
                    notes.append(f"{tid}: {tlabel} check failed: rows sum {s} != {tv[cidx]}")
        ai = totals.get("TOTAL ALL INDIA", [])
        india[key] = {"label": label, "table": tid, "rate_base": rate_base,
                      "c2022": ai[0] if len(ai) > 0 else None,
                      "c2023": ai[1] if len(ai) > 1 else None,
                      "c2024": ai[cidx] if len(ai) > cidx else None,
                      "rate_2024": ai[cidx + 2] if len(ai) > cidx + 2 else None}

    # ---- TABLE 1A.4 crime heads (2024 only) ----
    for page, hidx, key, label in HEAD_TABLES:
        text = get_text(VOL1, page)
        if "TABLE 1A.4" not in text:
            skipped.append({"table": "1A.4", "key": key, "reason": f"header not on p.{page}"})
            continue
        try:
            rows, totals = parse_state_rows(text, "1A.4", (10,), page)
        except AssertionError as e:
            skipped.append({"table": "1A.4", "key": key, "reason": str(e)})
            continue
        if len(rows) != 36:
            notes.append(f"1A.4/{key}: parsed {len(rows)} rows (expected 36)")
        off = hidx * 5
        for r in rows:
            st = states.setdefault(r["state"], {"heads": {}})
            v = r["vals"]
            st["heads"][key] = {"c2024": v[off + 2], "rate_2024": v[off + 4],
                                "ipc_2024": v[off], "bns_2024": v[off + 1]}
        for pred, tlabel in [(lambda r: not r["ut"], "TOTAL STATE(S)"),
                             (lambda r: r["ut"], "TOTAL UT(S)"),
                             (lambda r: True, "TOTAL ALL INDIA")]:
            tv = totals.get(tlabel)
            if tv and len(tv) > off + 2 and tv[off + 2] is not None:
                s = sum(r["vals"][off + 2] for r in rows
                        if pred(r) and r["vals"][off + 2] is not None)
                if abs(s - tv[off + 2]) > 0:
                    notes.append(f"1A.4/{key}: {tlabel} check failed: {s} != {tv[off+2]}")
        ai = totals.get("TOTAL ALL INDIA", [])
        india[key] = {"label": label, "table": "1A.4",
                      "rate_base": "per lakh population",
                      "c2024": ai[off + 2] if len(ai) > off + 2 else None,
                      "rate_2024": ai[off + 4] if len(ai) > off + 4 else None}

    UT = {"Andaman and Nicobar Islands", "Chandigarh",
          "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
          "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"}
    state_list = []
    for name in sorted(states):
        s = states[name]
        s["name"] = name
        s["type"] = "UT" if name in UT else "State"
        state_list.append(s)

    heads_meta = {}
    for k, lbl, tid, _, _, rb, _ in SUMMARY_TABLES:
        heads_meta[k] = {"label": lbl, "table": tid, "rate_base": rb}
    for _, _, k, lbl in [(p, h, k, l) for p, h, k, l in HEAD_TABLES]:
        heads_meta[k] = {"label": lbl, "table": "1A.4",
                         "rate_base": "per lakh population"}

    out = {
        "meta": {
            "title": "APARADH — Crime in India 2024, state/UT explorer dataset",
            "source": "National Crime Records Bureau (Ministry of Home Affairs), Government of India",
            "report": "Crime in India 2024, Volumes I & II (state/UT tables)",
            "report_urls": [
                "https://www.ncrb.gov.in/uploads/files/1CrimeinIndia2024-VolumeI.pdf",
                "https://www.ncrb.gov.in/uploads/files/2CrimeinIndia2024-VolumeII.pdf",
            ],
            "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
            "method": "Parsed with pdfplumber from official NCRB PDFs; every value traces to a "
                      "table id. State sums cross-checked against NCRB's own TOTAL rows.",
            "cautions": [
                "NCRB follows the Principal Offence Rule: in one FIR only the most heinous offence is counted.",
                "Only police-recorded cases are captured; reported crime is not actual crime.",
                "2024 uses BNS classifications; simple 'hurt' became non-cognizable, depressing total counts vs 2023.",
                "State/UT rates use 2024 mid-year projected population (2011 census base).",
            ],
            "skipped": skipped,
            "parse_notes": notes,
        },
        "heads": heads_meta,
        "states": state_list,
        "india": india,
    }
    with open(OUT, "w") as f:
        json.dump(out, f, ensure_ascii=False)
    n_vals = sum(len(s["heads"]) for s in state_list)
    print(f"states: {len(state_list)}, heads: {len(heads_meta)}, state-head values: {n_vals}")
    print(f"skipped: {len(skipped)}")
    for s in skipped:
        print("  SKIP:", s)
    for n in notes:
        print("  NOTE:", n)
    print("wrote", OUT)

if __name__ == "__main__":
    main()
