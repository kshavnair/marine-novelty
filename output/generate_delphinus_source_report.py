import csv
import json
import os
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from urllib import error, parse, request

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "delphinus_sources_2026_04_20")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PREDICT_URL = "http://localhost:8000/predict"
BASE_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
BASE_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

ZIP_PATH = os.path.join(PROJECT_ROOT, "ncbi_dataset.zip")
WORKSPACE_FASTA = os.path.join(PROJECT_ROOT, "_ncbi_extract", "ncbi_dataset", "data", "gene.fna")
BACKEND_MAIN = os.path.join(PROJECT_ROOT, "marine-species-discovery", "backend", "main.py")

COI_PAT = re.compile(r"(?:\\bcoi\\b|\\bcox1\\b|\\bco1\\b|mt[-_ ]?co1|cytochrome c oxidase subunit i)", re.I)


@dataclass
class SequenceSample:
    source_group: str
    source_name: str
    label_hint: str
    seq: str
    accession: str = ""
    header: str = ""


def clean_sequence(raw: str) -> str:
    lines = raw.strip().splitlines()
    seq = []
    for line in lines:
        if line.startswith(">"):
            continue
        seq.append("".join(c for c in line.upper() if c in "ATCGN"))
    return "".join(seq)


def to_atcg(seq: str) -> str:
    return re.sub(r"[^ATCG]", "", seq.upper())


def http_request(url: str, method: str = "GET", data: bytes | None = None, headers: dict | None = None, retries: int = 3, timeout: int = 40) -> str:
    last_err = None
    for _ in range(retries):
        try:
            req = request.Request(url, data=data, headers=headers or {}, method=method)
            with request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            last_err = exc
            if exc.code in (429, 500, 502, 503, 504):
                continue
            break
        except Exception as exc:
            last_err = exc
            continue
    raise last_err


def parse_fasta_records(text: str) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header = None
    chunks: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records.append((header, to_atcg("".join(chunks))))
            header = line[1:].strip()
            chunks = []
        else:
            chunks.append(line)
    if header is not None:
        records.append((header, to_atcg("".join(chunks))))
    return records


def parse_genbank(text: str):
    acc = ""
    m_acc = re.search(r"^ACCESSION\\s+(\\S+)", text, re.M)
    if m_acc:
        acc = m_acc.group(1)

    m_origin = re.search(r"^ORIGIN\\s*$([\\s\\S]*?)^//\\s*$", text, re.M)
    if not m_origin:
        return acc, "", []
    full_seq = re.sub(r"[^A-Za-z]", "", m_origin.group(1)).upper()

    m_feat = re.search(r"^FEATURES\\s+Location/Qualifiers\\s*$([\\s\\S]*?)^ORIGIN\\s*$", text, re.M)
    feat_block = m_feat.group(1) if m_feat else ""

    entries = []
    cur = None
    for line in feat_block.splitlines():
        if re.match(r"^ {5}\\S", line):
            if cur:
                entries.append(cur)
            cur = {"key": line[5:21].strip(), "loc": line[21:].strip(), "lines": [line]}
        elif cur is not None:
            cur["lines"].append(line)
            if re.match(r"^ {21}(?!/)(\\S.*)$", line):
                cur["loc"] += line[21:].strip()
    if cur:
        entries.append(cur)

    return acc, full_seq, entries


def revcomp(seq: str) -> str:
    return seq.translate(str.maketrans("ATCGN", "TAGCN"))[::-1]


def split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in text:
        if ch == "," and depth == 0:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        buf.append(ch)
    part = "".join(buf).strip()
    if part:
        parts.append(part)
    return parts


def parse_segment(seg: str, full_seq: str) -> str:
    seg = seg.strip()
    local_comp = False
    if seg.startswith("complement(") and seg.endswith(")"):
        local_comp = True
        seg = seg[len("complement(") : -1].strip()

    m_range = re.match(r"[<>]?(\\d+)\\.\\.[<>]?(\\d+)$", seg)
    m_single = re.match(r"[<>]?(\\d+)$", seg)

    piece = ""
    if m_range:
        a, b = int(m_range.group(1)), int(m_range.group(2))
        if a > b:
            a, b = b, a
        piece = full_seq[a - 1 : b]
    elif m_single:
        a = int(m_single.group(1))
        piece = full_seq[a - 1 : a]

    if local_comp:
        piece = revcomp(piece)
    return piece


def extract_by_location(loc: str, full_seq: str) -> str:
    loc = re.sub(r"\\s+", "", loc)
    global_comp = False
    if loc.startswith("complement(") and loc.endswith(")"):
        global_comp = True
        loc = loc[len("complement(") : -1]

    if loc.startswith("join(") and loc.endswith(")"):
        inner = loc[len("join(") : -1]
        seq = "".join(parse_segment(seg, full_seq) for seg in split_top_level(inner))
    else:
        seq = parse_segment(loc, full_seq)

    if global_comp:
        seq = revcomp(seq)

    return to_atcg(seq)


def pick_coi_from_genbank(gb_text: str) -> tuple[str, str]:
    acc, full_seq, entries = parse_genbank(gb_text)
    if not full_seq or not entries:
        return acc, ""

    for entry in entries:
        key = entry["key"].lower()
        blob = "\n".join(entry["lines"]).lower()
        if key in ("cds", "gene") and COI_PAT.search(blob):
            seq = extract_by_location(entry["loc"], full_seq)
            if seq:
                return acc, seq
    return acc, ""


def load_zip_delphinus_samples() -> list[SequenceSample]:
    samples: list[SequenceSample] = []
    if not os.path.exists(ZIP_PATH):
        return samples

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        fasta_name = None
        for name in zf.namelist():
            if name.lower().endswith("gene.fna"):
                fasta_name = name
                break
        if fasta_name is None:
            return samples

        text = zf.read(fasta_name).decode("utf-8", errors="replace")
        for header, seq in parse_fasta_records(text):
            h = header.lower()
            if "delphinus" not in h:
                continue
            if len(seq) < 120:
                continue
            label = "Delphinus delphis" if "delphis" in h else "Delphinus sp."
            samples.append(
                SequenceSample(
                    source_group="uploaded_zip",
                    source_name="ncbi_dataset.zip:gene.fna",
                    label_hint=label,
                    seq=seq,
                    header=header,
                )
            )
            if len(samples) >= 8:
                break
    return samples


def load_workspace_delphinus_samples() -> list[SequenceSample]:
    samples: list[SequenceSample] = []
    if not os.path.exists(WORKSPACE_FASTA):
        return samples

    with open(WORKSPACE_FASTA, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    for header, seq in parse_fasta_records(text):
        h = header.lower()
        if "delphinus" not in h:
            continue
        if len(seq) < 120:
            continue
        label = "Delphinus delphis" if "delphis" in h else "Delphinus sp."
        samples.append(
            SequenceSample(
                source_group="workspace_extract",
                source_name="_ncbi_extract/ncbi_dataset/data/gene.fna",
                label_hint=label,
                seq=seq,
                header=header,
            )
        )
        if len(samples) >= 8:
            break

    return samples


def fetch_by_accession(accession: str, hint: str) -> SequenceSample | None:
    gb_params = parse.urlencode({"db": "nuccore", "id": accession, "rettype": "gb", "retmode": "text"})
    try:
        gb_text = http_request(f"{BASE_EFETCH}?{gb_params}", timeout=40)
        acc, seq = pick_coi_from_genbank(gb_text)
        seq = to_atcg(seq)
        if len(seq) >= 250:
            return SequenceSample(
                source_group="ncbi_accession",
                source_name=f"NCBI accession {accession} (GenBank COI)",
                label_hint=hint,
                seq=seq,
                accession=acc or accession,
            )
    except Exception:
        pass

    fa_params = parse.urlencode({"db": "nuccore", "id": accession, "rettype": "fasta", "retmode": "text"})
    try:
        fa_text = http_request(f"{BASE_EFETCH}?{fa_params}", timeout=40)
        records = parse_fasta_records(fa_text)
        if records:
            header, seq = records[0]
            if len(seq) >= 250:
                return SequenceSample(
                    source_group="ncbi_accession",
                    source_name=f"NCBI accession {accession} (FASTA)",
                    label_hint=hint,
                    seq=seq,
                    accession=accession,
                    header=header,
                )
    except Exception:
        pass
    return None


def fetch_esearch_samples(species: str, label_hint: str, max_take: int = 3) -> list[SequenceSample]:
    term = (
        f'("{species}"[Organism]) AND '
        '(mitochondrion[filter] OR mitochondrion[All Fields]) AND '
        '(COI[All Fields] OR CO1[All Fields] OR COX1[All Fields] OR MT-CO1[All Fields] '
        'OR "cytochrome c oxidase subunit I"[All Fields])'
    )
    params = parse.urlencode({"db": "nuccore", "retmode": "json", "retmax": "6", "sort": "relevance", "term": term})
    samples: list[SequenceSample] = []
    try:
        body = http_request(f"{BASE_ESEARCH}?{params}", timeout=35)
        ids = (json.loads(body).get("esearchresult") or {}).get("idlist") or []
        for nid in ids:
            candidate = fetch_by_accession(nid, label_hint)
            if candidate is None:
                continue
            candidate.source_group = "ncbi_esearch"
            candidate.source_name = f"NCBI esearch {species}"
            samples.append(candidate)
            if len(samples) >= max_take:
                break
    except Exception:
        return samples
    return samples


def load_fallback_delphinus_from_code() -> SequenceSample | None:
    if not os.path.exists(BACKEND_MAIN):
        return None
    text = open(BACKEND_MAIN, "r", encoding="utf-8", errors="replace").read()

    m = re.search(
        r'"Delphinus delphis":\s*\(\s*"([ATCG\\s]+)"\s*"([ATCG\\s]+)"\s*"([ATCG\\s]+)"\s*\)',
        text,
        flags=re.S,
    )
    if not m:
        return None

    seq = to_atcg("".join(m.groups()))
    if len(seq) < 120:
        return None
    return SequenceSample(
        source_group="model_reference",
        source_name="backend fallback reference",
        label_hint="Delphinus delphis",
        seq=seq,
    )


def call_predict(seq: str) -> dict:
    payload = json.dumps({"sequence": seq}).encode("utf-8")
    raw = http_request(
        PREDICT_URL,
        method="POST",
        data=payload,
        headers={"Content-Type": "application/json"},
        timeout=45,
    )
    return json.loads(raw)


def evaluate(samples: list[SequenceSample]) -> list[dict]:
    rows = []
    for idx, sample in enumerate(samples, start=1):
        row = {
            "id": idx,
            "source_group": sample.source_group,
            "source_name": sample.source_name,
            "label_hint": sample.label_hint,
            "accession": sample.accession,
            "input_len": len(sample.seq),
            "predicted_species": "",
            "confidence": "",
            "is_match": "",
            "is_uncertain": "",
            "is_novel": "",
            "status": "",
            "header": sample.header,
        }
        try:
            pred = call_predict(sample.seq)
            row["predicted_species"] = pred.get("species", "")
            row["confidence"] = pred.get("confidence", "")
            row["is_match"] = pred.get("is_match", "")
            row["is_uncertain"] = pred.get("is_uncertain", "")
            row["is_novel"] = pred.get("is_novel", "")
            row["status"] = "tested"
        except Exception as exc:
            row["status"] = f"predict_error:{type(exc).__name__}"
        rows.append(row)
    return rows


def save_outputs(rows: list[dict]) -> None:
    csv_path = os.path.join(OUTPUT_DIR, "delphinus_source_results.csv")
    md_path = os.path.join(OUTPUT_DIR, "delphinus_source_table.md")
    json_path = os.path.join(OUTPUT_DIR, "delphinus_source_summary.json")

    headers = [
        "id",
        "source_group",
        "source_name",
        "label_hint",
        "accession",
        "input_len",
        "predicted_species",
        "confidence",
        "is_match",
        "is_uncertain",
        "is_novel",
        "status",
        "header",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    tested = [r for r in rows if r["status"] == "tested"]
    predicted = Counter(r["predicted_species"] for r in tested)
    by_source = Counter(r["source_group"] for r in tested)
    novel_count = sum(1 for r in tested if str(r["is_novel"]).lower() == "true")
    match_count = sum(1 for r in tested if str(r["is_match"]).lower() == "true")
    uncertain_count = sum(1 for r in tested if str(r["is_uncertain"]).lower() == "true")

    summary = {
        "total_rows": len(rows),
        "tested_rows": len(tested),
        "error_rows": len(rows) - len(tested),
        "predicted_species_counts": dict(predicted),
        "tested_by_source_group": dict(by_source),
        "novel_count": novel_count,
        "match_count": match_count,
        "uncertain_count": uncertain_count,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Delphinus Multi-Source Results\n\n")
        f.write("| ID | Source Group | Source Name | Label Hint | Predicted Species | Confidence | Match | Uncertain | Novel | Len | Status |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
        for row in rows:
            f.write(
                "| "
                + " | ".join(
                    [
                        str(row["id"]),
                        str(row["source_group"]),
                        str(row["source_name"]),
                        str(row["label_hint"]),
                        str(row["predicted_species"]),
                        str(row["confidence"]),
                        str(row["is_match"]),
                        str(row["is_uncertain"]),
                        str(row["is_novel"]),
                        str(row["input_len"]),
                        str(row["status"]),
                    ]
                )
                + " |\n"
            )

        f.write("\n## Summary\n\n")
        for k, v in summary.items():
            f.write(f"- {k}: {v}\n")

    conf_png = os.path.join(OUTPUT_DIR, "delphinus_confidence_by_sample.png")
    outcome_png = os.path.join(OUTPUT_DIR, "delphinus_outcome_counts.png")

    if tested:
        labels = [f"#{r['id']}" for r in tested]
        conf = [float(r["confidence"] or 0.0) for r in tested]
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.bar(labels, conf)
        ax.set_ylim(0, 100)
        ax.set_ylabel("Confidence (%)")
        ax.set_xlabel("Sample")
        ax.set_title("Delphinus Source Test: Confidence by Sample")
        fig.tight_layout()
        fig.savefig(conf_png, dpi=160)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    keys = ["match", "uncertain", "novel"]
    vals = [match_count, uncertain_count, novel_count]
    ax.bar(keys, vals)
    ax.set_ylabel("Count")
    ax.set_title("Delphinus Source Test: Outcome Counts")
    fig.tight_layout()
    fig.savefig(outcome_png, dpi=160)
    plt.close(fig)


def main() -> None:
    samples: list[SequenceSample] = []

    samples.extend(load_zip_delphinus_samples())
    samples.extend(load_workspace_delphinus_samples())

    for accession, hint in [
        ("EF090639.1", "Delphinus delphis"),
        ("NC_012061.1", "Delphinus capensis"),
        ("NC_012053.1", "Stenella coeruleoalba"),
    ]:
        sample = fetch_by_accession(accession, hint)
        if sample is not None:
            samples.append(sample)

    samples.extend(fetch_esearch_samples("Delphinus delphis", "Delphinus delphis", max_take=3))
    samples.extend(fetch_esearch_samples("Delphinus capensis", "Delphinus capensis", max_take=3))

    fallback = load_fallback_delphinus_from_code()
    if fallback is not None:
        samples.append(fallback)

    dedup = {}
    for s in samples:
        key = (s.source_group, s.source_name, s.accession, len(s.seq), s.seq[:80])
        dedup[key] = s

    final_samples = list(dedup.values())
    if not final_samples:
        raise SystemExit("No Delphinus samples could be assembled from sources.")

    rows = evaluate(final_samples)
    save_outputs(rows)

    print("Delphinus source report generated:")
    print(os.path.join(OUTPUT_DIR, "delphinus_source_results.csv"))
    print(os.path.join(OUTPUT_DIR, "delphinus_source_table.md"))
    print(os.path.join(OUTPUT_DIR, "delphinus_source_summary.json"))
    print(os.path.join(OUTPUT_DIR, "delphinus_confidence_by_sample.png"))
    print(os.path.join(OUTPUT_DIR, "delphinus_outcome_counts.png"))


if __name__ == "__main__":
    main()
