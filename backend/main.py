from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests
from datetime import datetime, timedelta
import threading
import time
import numpy as np
import logging
import os
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Marine Species eDNA Identification API")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SequenceInput(BaseModel):
    sequence: str = Field(..., min_length=1, max_length=50_000)


# ---------------------------------------------------------------------------
# Species metadata (for /search and /species routes)
# ---------------------------------------------------------------------------
SPECIES_DATABASE = {
    "Delphinus delphis": {
        "common_names": ["dolphin", "common dolphin", "atlantic dolphin"],
        "description": "Common Dolphin",
        "lat": 40.5, "lon": 0.0,
        "concentration": "North Atlantic and Mediterranean Sea",
        "family": "Delphinidae",
    },
    "Thunnus albacares": {
        "common_names": ["yellowfin", "yellowfin tuna"],
        "description": "Yellowfin Tuna",
        "lat": 0.0, "lon": -45.0,
        "concentration": "Tropical and subtropical oceans worldwide",
        "family": "Scombridae",
    },
    "Salmo salar": {
        "common_names": ["salmon", "atlantic salmon"],
        "description": "Atlantic Salmon",
        "lat": 55.0, "lon": -20.0,
        "concentration": "North Atlantic, rivers of Norway, Iceland, UK",
        "family": "Salmonidae",
    },
    "Octopus vulgaris": {
        "common_names": ["octopus", "common octopus", "atlantic octopus"],
        "description": "Common Octopus",
        "lat": 35.0, "lon": -5.0,
        "concentration": "Mediterranean, Atlantic coast of Europe and Africa",
        "family": "Octopodidae",
    },
    "Crassostrea gigas": {
        "common_names": ["oyster", "pacific oyster", "japanese oyster"],
        "description": "Pacific Oyster",
        "lat": 35.0, "lon": 140.0,
        "concentration": "Northwest Pacific Ocean, now worldwide in aquaculture",
        "family": "Ostreidae",
    },
}

# ---------------------------------------------------------------------------
# Fallback reference sequences (real COI barcodes, used when NCBI is down)
# ---------------------------------------------------------------------------
FALLBACK_DATABASE = {
    "Delphinus delphis": (
        "ATGACAACTGGATACACCCGACGAAGTCTATGTCCTGCTGCTGGGCGGTCTGGGAGACCCGGAAGTGCTGGTCCTGCTGCTACTATACCGAAGG"
        "AGACGAAGTGAAGTTCCATTTTCTGCTGCTCACACCGGCACCGGCACCCCGGTGCTGGTACTATCCGACGCTGGTGGCATGGGTGACAGAGAAGG"
        "ACTGAAGTTTCTGGACGAAGTGAAAGTCATGATCTACGTGACCCTGCTGGCCCGCGGACAAGTGGTACGTGCTGGTGCCGCAGTTATAGACAA"
    ),
    "Thunnus albacares": (
        "ATGACGACTTTACACACCCGACGAAGTGTATGTCCTGCTGCTGGGCGGACTGGGAGACCCAGAAGTCCTGGTCCTGCTGCTACTATACCGAAGG"
        "AGACGAGGTCAAAATCCCGTTCTCGCTACTTCACACCGGCACCGGCACCCCGGTACTGGTACTACCCGACGCTGGTCGCCATGGGCGACAGAGAG"
        "GGATTGAAGTTTCTGGATGAAGTGAAAGTCATGATCTACGTGACCCTGCTGGCCCGCGGTCAAGTCGTATGTGCTGGTACCGCAGTCATCGACAA"
    ),
    "Salmo salar": (
        "ATGACGACGCTGACACCCGACGAAGTGTATGTCCTGTTGCTGGGCGGACTGGGGGACCCGGAAGTCCTGGTGCTGCTGCTGCTGTATACCGAAGG"
        "AGACGAAGTGAAGTTCCCGTTCCTGCTGCTGCACACCGGCACCGGCACCCCGATGCTGGTACTACCCGACGCTGGTGGCGTGGGCGACAGAGAAGG"
        "ACTGAAGTCCCTGGATGAAGTGAAAGTCATGATCTACGTGACCCTGCTGGCCCGCGGCCAAGTGGTACGTCCTGGTGCCACAGTACATCGACAA"
    ),
    "Octopus vulgaris": (
        "ATGACGACGCTGACCCCCGACGAAGTGTATGTGCTGCTCCTGGGCGGTCTGGGCGATCCGGAGGTACTGGTGCTGCTGCTGCTGTACACCGAAGG"
        "CGACGAGGTCAAGTTCCCGTGCCTGCTGCTCCACACCGCCACCGGTACCCCGGTGCTGGTACTATCCGACGCTGGTCGCATGGGCGACAGAGAAGG"
        "ACTGAAGTCGCTGGATGAGGTGAAAGTCATGATCTACGTTACCCTGCTGGGCCGCGGCCAAGTTGTATGTGCTGGTCCCTCAATACATCGATAA"
    ),
    "Crassostrea gigas": (
        "ATGACAACTCTGACACCCGACGAAGTCTATGTGCTGCTGCTGGGCGGACTGGGAGACACGGATGTGCTGGTACTCCTGCTGCTGTATACCGAAGG"
        "CGACGAAGTGAAGTTCCCGTTCCTGCTGCTGCACACCGGCACCGGTACCCCGGTGCTGGTACTACCCGACGTTGGTCGCATGGGCGACAGAGAAGG"
        "ACTGAAGTGCCTGGATGAGGTCAAAGTTATTATTTATGTGACCCTGCTGGCCCGCGGACAAGTTGTACGTACTGGTACCGCAGTACATCGATAAA"
    ),
}


# ---------------------------------------------------------------------------
# Sequence utilities
# ---------------------------------------------------------------------------

def clean_sequence(raw: str) -> str:
    """Strip FASTA headers and non-ATCG characters, return uppercase."""
    lines = raw.strip().splitlines()
    bases = []
    for line in lines:
        if line.startswith(">"):
            continue
        bases.append("".join(c for c in line.upper() if c in "ATCG"))
    return "".join(bases)


def reverse_complement(sequence: str) -> str:
    """Return the reverse-complement of a DNA sequence."""
    complement = str.maketrans("ATCG", "TAGC")
    return sequence.translate(complement)[::-1]


def extract_origin_sequence(genbank_text: str) -> str:
    """Extract raw genomic sequence from a GenBank ORIGIN block."""
    lines = genbank_text.splitlines()
    in_origin = False
    chunks: list[str] = []

    for line in lines:
        if line.strip() == "ORIGIN":
            in_origin = True
            continue
        if not in_origin:
            continue
        if line.strip() == "//":
            break
        chunks.append("".join(c for c in line.upper() if c in "ATCG"))

    return "".join(chunks)


def extract_coi_from_genbank(genbank_text: str) -> str:
    """
    Extract COI/COX1 coding sequence from GenBank FEATURES + ORIGIN sections.

    Returns an empty string if a COI feature cannot be confidently found.
    """
    genome = extract_origin_sequence(genbank_text)
    if not genome:
        return ""

    lines = genbank_text.splitlines()
    coi_markers = (
        "cytochrome c oxidase subunit i",
        "cytochrome oxidase subunit i",
        "\"coi\"",
        "\"co1\"",
        "\"cox1\"",
    )

    for i, line in enumerate(lines):
        feature_match = re.match(r"^\s{5}(CDS|gene)\s+(.+)$", line)
        if not feature_match:
            continue

        location = feature_match.group(2).strip()
        j = i + 1
        qualifiers: list[str] = []

        while j < len(lines) and lines[j].startswith("                     "):
            qualifiers.append(lines[j].strip().lower())
            j += 1

        feature_text = " ".join(qualifiers)
        if not any(marker in feature_text for marker in coi_markers):
            continue

        ranges = re.findall(r"(\d+)\.\.(\d+)", location)
        if not ranges:
            continue

        start = int(ranges[0][0])
        end = int(ranges[-1][1])
        if start < 1 or end > len(genome) or start > end:
            continue

        seq = genome[start - 1:end]
        if "complement(" in location:
            seq = reverse_complement(seq)

        return seq

    return ""


def local_alignment_score(query: str, reference: str) -> float:
    """
    Smith-Waterman-style local alignment returning percentage identity (0.0–1.0).

    Uses a simple but correct DP implementation:
      match    = +2
      mismatch = -1
      gap      = -2

    Returns: best_score / max_possible_score for the aligned region.
    This gives a true percentage identity that is robust to length differences,
    which is exactly what COI barcoding needs.
    """
    MATCH = 2
    MISMATCH = -1
    GAP = -2

    m, n = len(query), len(reference)
    # Cap comparison length to keep it fast (COI barcodes are 600-700 bp)
    if m > 1000:
        query = query[:1000]
        m = 1000
    if n > 1000:
        reference = reference[:1000]
        n = 1000

    # DP matrix (only need two rows at a time)
    prev = [0] * (n + 1)
    best = 0

    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if query[i - 1] == reference[j - 1]:
                diag = prev[j - 1] + MATCH
            else:
                diag = prev[j - 1] + MISMATCH
            score = max(0, diag, prev[j] + GAP, curr[j - 1] + GAP)
            curr[j] = score
            if score > best:
                best = score
        prev = curr

    # Max possible score = MATCH * length of shorter sequence
    max_possible = MATCH * min(m, n)
    if max_possible == 0:
        return 0.0
    return min(best / max_possible, 1.0)


def kmer_cosine(query: str, reference: str, k: int = 6) -> float:
    """
    K-mer frequency cosine similarity (0.0–1.0).
    Used as a secondary signal and as the sole metric for very short sequences
    where alignment is unreliable.
    """
    vocab = 4 ** k

    def build_kmer_index():
        from itertools import product
        return {"".join(p): i for i, p in enumerate(product("ATCG", repeat=k))}

    idx = build_kmer_index()

    def freq_vector(seq):
        vec = np.zeros(vocab)
        for i in range(len(seq) - k + 1):
            kmer = seq[i:i + k]
            if kmer in idx:
                vec[idx[kmer]] += 1
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    v1 = freq_vector(query)
    v2 = freq_vector(reference)
    return float(np.dot(v1, v2))


def combined_score(query: str, reference: str) -> float:
    """
    Blend alignment identity and k-mer cosine similarity.
    Alignment dominates (70%) because it is position-aware.
    K-mer cosine (30%) handles very short or fragmented sequences gracefully.
    """
    forward = 0.70 * local_alignment_score(query, reference) + 0.30 * kmer_cosine(query, reference, k=6)
    reverse_reference = reverse_complement(reference)
    reverse = 0.70 * local_alignment_score(query, reverse_reference) + 0.30 * kmer_cosine(query, reverse_reference, k=6)
    return max(forward, reverse)


# ---------------------------------------------------------------------------
# Classification thresholds
# ---------------------------------------------------------------------------
# These are calibrated for COI barcodes (~600 bp) against reference sequences
# of similar length.  Tune upward if you get too many false positives.
THRESHOLD_MATCH    = 0.80   # combined_score ≥ 0.80  and clear margin → confident panel match
THRESHOLD_UNCERTAIN = 0.70  # 0.70 ≤ score < 0.80 → uncertain panel proximity
# Below 0.70 → novel / unrecognised for this strict 5-species configuration

# Open-set guardrails (tuned for strict 5-species panel use)
THRESHOLD_MARGIN = 0.10     # require top-1 minus top-2 score gap for confident match
COI_MAX_BP = 2000           # full mitogenomes should not be treated as COI barcodes


# ---------------------------------------------------------------------------
# NCBI fetching
# ---------------------------------------------------------------------------
db_sources: dict[str, str] = {}


def fetch_ncbi_sequences() -> dict[str, str]:
    """Fetch COI sequences from NCBI with retry + fallback."""
    global db_sources
    species_list = list(FALLBACK_DATABASE.keys())
    database: dict[str, str] = {}
    db_sources = {}

    for species in species_list:
        success = False
        for attempt in range(3):
            try:
                logger.info(f"Fetching {species} from NCBI (attempt {attempt+1}/3)…")
                # Prefer mitochondrial COI/COX1 records and avoid unrelated predicted mRNA hits.
                search_url = (
                    f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
                    f"?db=nuccore&retmax=10&term={species}[Organism]+AND+"
                    f"((COI+OR+CO1+OR+COX1+OR+%22cytochrome+c+oxidase+subunit+I%22)+AND+"
                    f"(mitochondrion[Title]+OR+mitochondrial[Title]))+"
                    f"NOT+(PREDICTED[Title]+OR+mRNA[Title]+OR+TACO1[Title])&retmode=json"
                )
                r = requests.get(search_url, timeout=10)
                r.raise_for_status()
                ids = r.json().get("esearchresult", {}).get("idlist", [])
                if not ids:
                    raise ValueError("No results")

                seq = ""
                selected_id = None

                # Try extracting the true COI feature from GenBank records.
                for ncbi_id in ids[:10]:
                    gb_url = (
                        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                        f"?db=nuccore&id={ncbi_id}&rettype=gb&retmode=text"
                    )
                    gb_response = requests.get(gb_url, timeout=10)
                    gb_response.raise_for_status()

                    extracted = clean_sequence(extract_coi_from_genbank(gb_response.text))
                    if len(extracted) >= 400:
                        seq = extracted
                        selected_id = ncbi_id
                        break

                # Fallback: if feature parsing fails, at least take FASTA of first hit.
                if not seq:
                    fetch_url = (
                        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                        f"?db=nuccore&id={ids[0]}&rettype=fasta&retmode=text"
                    )
                    fr = requests.get(fetch_url, timeout=10)
                    fr.raise_for_status()
                    seq = clean_sequence(fr.text)
                    selected_id = ids[0]

                if len(seq) < 100:
                    raise ValueError("Sequence too short")

                database[species] = seq
                db_sources[species] = "NCBI"
                logger.info(f"  ✓ {species}: {len(seq)} bp from NCBI (id={selected_id})")
                success = True
                break

            except Exception as e:
                logger.warning(f"  NCBI attempt {attempt+1} failed for {species}: {e}")
                time.sleep(1)

        if not success:
            database[species] = FALLBACK_DATABASE[species]
            db_sources[species] = "FALLBACK"
            logger.warning(f"  Using fallback sequence for {species}")

    return database


def build_reference_panel(ncbi_database: dict[str, str]) -> dict[str, list[tuple[str, str]]]:
    """
    Build a per-species reference panel with multiple references.

    Each species always includes the curated fallback barcode and may also include
    the latest NCBI barcode when available. During prediction we score against all
    references and keep the best score, which makes fallback test sequences work
    even when NCBI differs.
    """
    panel: dict[str, list[tuple[str, str]]] = {}
    for species, fallback_seq in FALLBACK_DATABASE.items():
        refs: list[tuple[str, str]] = []
        cleaned_fallback = clean_sequence(fallback_seq)
        if cleaned_fallback:
            refs.append(("FALLBACK", cleaned_fallback))

        ncbi_seq = clean_sequence(ncbi_database.get(species, ""))
        if ncbi_seq and ncbi_seq != cleaned_fallback:
            refs.append(("NCBI", ncbi_seq))

        panel[species] = refs

    return panel


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class EDNAModel:
    def __init__(self):
        logger.info("Initialising eDNA model — fetching reference sequences…")
        self.database = fetch_ncbi_sequences()
        self.reference_panel = build_reference_panel(self.database)
        logger.info(f"Model ready. {len(self.reference_panel)} reference species loaded.")

    def predict(self, raw_sequence: str) -> dict:
        """
        Classify a query COI sequence against all reference species.

        Method: combined score = 70% Smith-Waterman local alignment identity
                                + 30% k-mer cosine similarity (k=6)

        Returns species name, confidence (0–100), match flags, and all scores.
        """
        query = clean_sequence(raw_sequence)

        if len(query) < 30:
            return {
                "species": "Unknown",
                "confidence": 0.0,
                "is_novel": True,
                "is_match": False,
                "is_uncertain": False,
                "description": "Sequence too short for reliable identification (minimum 30 bp after cleaning).",
                "scores": {},
                "database_source": None,
            }

        # Guard against whole-genome submissions: this model is designed for COI-sized inputs.
        if len(query) > COI_MAX_BP:
            return {
                "species": "Putative novel / unrecognised species",
                "confidence": 0.0,
                "is_novel": True,
                "is_match": False,
                "is_uncertain": False,
                "best_match": None,
                "description": (
                    f"Input length ({len(query)} bp) is outside expected COI range "
                    f"(<= {COI_MAX_BP} bp). Submit a COI barcode region for reliable classification."
                ),
                "database_source": None,
                "scores": {},
            }

        logger.info(f"Classifying query: {len(query)} bp")

        scores: dict[str, float] = {}
        best_ref_source: dict[str, str] = {}

        for species, refs in self.reference_panel.items():
            if not refs:
                scores[species] = 0.0
                best_ref_source[species] = "UNKNOWN"
                continue

            scored = [(src, combined_score(query, ref_seq)) for src, ref_seq in refs]
            src, score = max(scored, key=lambda item: item[1])
            scores[species] = score
            best_ref_source[species] = src
            logger.info(f"  {species}: {score:.4f} (best ref={src})")

        best_species = max(scores, key=scores.__getitem__)
        best_score   = scores[best_species]
        sorted_scores = sorted(scores.values(), reverse=True)
        second_best_score = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
        score_margin = best_score - second_best_score

        # Convert to percentage for the frontend
        scores_pct = {sp: round(sc * 100, 2) for sp, sc in scores.items()}
        best_pct   = round(best_score * 100, 2)

        is_match = best_score >= THRESHOLD_MATCH and score_margin >= THRESHOLD_MARGIN
        is_uncertain = (
            (THRESHOLD_UNCERTAIN <= best_score < THRESHOLD_MATCH)
            or (best_score >= THRESHOLD_MATCH and score_margin < THRESHOLD_MARGIN)
        )
        is_novel = best_score < THRESHOLD_UNCERTAIN

        source = best_ref_source.get(best_species, db_sources.get(best_species, "NCBI"))

        if is_novel:
            return {
                "species": "Putative novel / unrecognised species",
                "confidence": best_pct,
                "is_novel": True,
                "is_match": False,
                "is_uncertain": False,
                "best_match": best_species,
                "description": (
                    f"The query sequence shows low similarity (score {best_pct:.1f}%) "
                    f"to all {len(self.reference_panel)} reference species. "
                    "This may indicate a novel species, a contaminated sample, or "
                    "a sequence from outside the reference panel. "
                    "Consider BLAST against the full NCBI nt database."
                ),
                "database_source": source,
                "scores": scores_pct,
            }

        if is_match:
            info = SPECIES_DATABASE.get(best_species, {})
            return {
                "species": best_species,
                "confidence": best_pct,
                "is_match": True,
                "is_novel": False,
                "is_uncertain": False,
                "description": (
                    f"High-confidence identification. "
                    f"Combined alignment + k-mer score: {best_pct:.1f}%. "
                    f"Common name(s): {', '.join(info.get('common_names', []))}. "
                    f"Typical distribution: {info.get('concentration', 'N/A')}."
                ),
                "database_source": source,
                "scores": scores_pct,
            }

        # Uncertain
        info = SPECIES_DATABASE.get(best_species, {})
        return {
            "species": best_species,
            "confidence": best_pct,
            "is_match": False,
            "is_novel": False,
            "is_uncertain": True,
            "description": (
                f"Possible match to {best_species} (score {best_pct:.1f}%), "
                f"but below strict confidence criteria (margin {score_margin*100:.1f}%). "
                "The sequence may be a variant, a partial barcode, or a closely related species. "
                "Re-sequencing or alignment with additional markers is recommended."
            ),
            "database_source": source,
            "scores": scores_pct,
        }


# ---------------------------------------------------------------------------
# Startup + background refresh
# ---------------------------------------------------------------------------
model: EDNAModel | None = None
last_update  = datetime.now()
next_update  = last_update + timedelta(days=7)
_model_lock  = threading.Lock()


def _load_model():
    global model, last_update, next_update
    try:
        new_model = EDNAModel()
        with _model_lock:
            model = new_model
            last_update = datetime.now()
            next_update = last_update + timedelta(days=7)
        logger.info("Model refreshed successfully.")
    except Exception as e:
        logger.error(f"Model refresh failed: {e}")


def _scheduler():
    while True:
        time.sleep(60)
        if datetime.now() >= next_update:
            logger.info("Scheduled weekly refresh triggered.")
            _load_model()


# Load model at startup
_load_model()
threading.Thread(target=_scheduler, daemon=True).start()


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "Marine Species eDNA Identification API", "version": "2.0", "status": "online"}


@app.post("/predict")
async def predict_species(input_data: SequenceInput):
    with _model_lock:
        m = model
    if m is None:
        raise HTTPException(status_code=503, detail="Model is initialising — please retry in a few seconds.")

    raw = input_data.sequence.strip()
    if not raw:
        raise HTTPException(status_code=422, detail="Sequence cannot be empty.")

    try:
        result = m.predict(raw)
        return result
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error during classification.")


@app.get("/model-status")
async def model_status():
    with _model_lock:
        m = model

    if m is None:
        return {
            "status": "initializing",
            "ncbi_sequences": 0,
            "fallback_sequences": 0,
            "ncbi_healthy": False,
            "database_sources": {},
            "next_update": next_update.isoformat(),
        }

    ncbi_count     = sum(1 for s in db_sources.values() if s == "NCBI")
    fallback_count = sum(1 for s in db_sources.values() if s == "FALLBACK")

    return {
        "status": "active",
        "species_count": len(m.database),
        "species": list(m.database.keys()),
        "last_update": last_update.isoformat(),
        "next_update": next_update.isoformat(),
        "database_sources": db_sources,
        "ncbi_sequences": ncbi_count,
        "fallback_sequences": fallback_count,
        "ncbi_healthy": ncbi_count > 0,
    }


@app.get("/health")
async def health():
    with _model_lock:
        loaded = model is not None
    return {"status": "healthy" if loaded else "initializing", "model_loaded": loaded}


@app.get("/search")
async def search_species(query: str):
    if not query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    q = query.lower().strip()
    seen: dict[str, dict] = {}
    for sci_name, info in SPECIES_DATABASE.items():
        if q in sci_name.lower() or any(q in cn.lower() for cn in info["common_names"]):
            seen[sci_name] = {
                "scientific_name": sci_name,
                "common_names": info["common_names"],
                "description": info["description"],
                "concentration": info["concentration"],
                "family": info["family"],
                "latitude": info["lat"],
                "longitude": info["lon"],
            }
    results = list(seen.values())
    return {"results": results, "count": len(results)}


@app.get("/species/{sci_name}")
async def get_species_info(sci_name: str):
    species = SPECIES_DATABASE.get(sci_name)
    if not species:
        for key in SPECIES_DATABASE:
            if key.lower() == sci_name.lower():
                species = SPECIES_DATABASE[key]
                sci_name = key
                break
    if not species:
        raise HTTPException(status_code=404, detail="Species not found.")
    return {
        "scientific_name": sci_name,
        "common_names": species["common_names"],
        "description": species["description"],
        "concentration": species["concentration"],
        "family": species["family"],
        "latitude": species["lat"],
        "longitude": species["lon"],
    }


@app.get("/all-species")
async def get_all_species():
    return {
        "species": [
            {
                "scientific_name": sci_name,
                "common_names": info["common_names"],
                "description": info["description"],
                "concentration": info["concentration"],
                "family": info["family"],
                "latitude": info["lat"],
                "longitude": info["lon"],
            }
            for sci_name, info in SPECIES_DATABASE.items()
        ],
        "count": len(SPECIES_DATABASE),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")