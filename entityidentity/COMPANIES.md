hort answer: you don’t need a server or a full database to get very good “on-the-fly” company name resolution. You can ship a pure Python library that:

loads a compact snapshot of companies (e.g., Wikidata + LEI) into memory (Parquet/CSV),

runs cheap, deterministic blocking + fuzzy scoring,

only calls a small/cheap LLM when the match is ambiguous (an “uncertainty band”), and

caches results aggressively.

If/when your corpus grows beyond a few hundred thousand rows or you want persistence, add a tiny SQLite + FTS5 index. You still don’t need Flask; a CLI or a single function is fine. If you later want multi-process or remote access, wrap the same function with FastAPI (or Flask) in an afternoon.

Below is a practical recipe with code you can drop in.

Architecture options (pick one now, upgrade later)

A. No DB (fast to ship, great up to ~100–300k companies)

Store a snapshot companies.parquet with columns like:

name, name_norm, aliases (list), country, lei, wikidata_qid, address, lat, lon

Load once on import (or first call).

Block by country (if given) and by first token or n-gram; score candidates with RapidFuzz; return top hit if score ≥ threshold (e.g., 0.88).

If best score is 0.75–0.87 (uncertain band), ask a cheap LLM to pick among top-K candidates using a structured, deterministic prompt.

Cache with functools.lru_cache or a tiny on-disk cache (sqlite dict).

B. Lightweight DB (same algorithm, more data)

Build a SQLite file with:

a canonical table and an FTS5 virtual table on name/aliases,

simple indexes on country, lei.

Use SQL to pull ~200–1000 candidates (country+FTS), then score in Python.

Still optional LLM fallback. No server required.

C. Service

Only if you need multi-client access/latency SLAs. Wrap the same resolver in FastAPI; keep state (the dataframe or SQLite handle) global so it’s warm in the worker.

Matching strategy (that works)

Normalize the query: lowercase, strip legal suffixes (inc, ltd, plc, sa, gmbh, spa, oyj, ag, jsc, co., s.r.o., etc.), remove punctuation/whitespace noise; collapse unicode variants.

Block candidates:

If country provided → filter by ISO2/3 first.

If lei provided → exact hit and return.

Use a quick token/FTS prefix query (or a hash map on the first significant token).

Score with RapidFuzz features:

token_sort_ratio, WRatio, and exact/alias hits. Add small boosts for:

country match,

address city/ADM match (if available),

LEI presence,

parent/brand alias hits.

Decide:

If best score ≥ 0.88 and Δ to #2 ≥ 0.06 → accept.

If best score in [0.76, 0.88) and user didn’t provide disambiguators → LLM tie-break among top-K (3–5).

Else return top-K with scores and ask the caller for a hint (country, city, LEI).

Explain: return matched alias, which features fired, and source IDs (LEI/QID) so you can trust but verify.

Minimal working code (in-memory, no server)
# resolver.py
from __future__ import annotations
import re, unicodedata
from functools import lru_cache
from typing import List, Optional, Dict, Any
import pandas as pd
from rapidfuzz import fuzz, process

LEGAL_SUFFIXES = r"(incorporated|inc|corp|co|company|ltd|plc|sa|ag|gmbh|spa|oyj|kgaa|sarl|s\.r\.o\.|pte|llc|lp|bv|nv|ab|as|oy|sas|s\.a\.|s\.p\.a\.)"
LEGAL_RE = re.compile(rf"\b{LEGAL_SUFFIXES}\b\.?", re.IGNORECASE)

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = LEGAL_RE.sub("", s)
    s = re.sub(r"[^a-z0-9&\-\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

@lru_cache(maxsize=1)
def _load_companies() -> pd.DataFrame:
    # Replace with your snapshot path
    df = pd.read_parquet("companies.parquet")
    if "name_norm" not in df.columns:
        df["name_norm"] = df["name"].map(_norm)
    # explode aliases for blocking but keep original
    df["aliases"] = df.get("aliases", [[]]).apply(lambda x: x or [])
    return df

def _candidate_block(df: pd.DataFrame, q_norm: str, country: Optional[str]) -> pd.DataFrame:
    cand = df
    if country:
        country = country.upper()
        cand = cand[cand["country"].str.upper() == country]
        if cand.empty:
            cand = df  # fallback if too strict
    # fast prefix token blocking on first token
    first = q_norm.split()[0] if q_norm else ""
    if first and len(first) >= 3:
        mask = cand["name_norm"].str.startswith(first)
        if "aliases" in cand.columns:
            # alias startswith check (cheap)
            mask = mask | cand["aliases"].apply(lambda al: any(_norm(a).startswith(first) for a in al))
        cand = cand[mask] if mask.any() else cand
    # cap size—RapidFuzz is fast but don't go crazy
    return cand.head(50_000)

def _score_one(q: str, row: pd.Series) -> float:
    # base on name + best alias
    base = fuzz.WRatio(q, row["name_norm"])
    alias_best = 0
    for a in row.get("aliases", []):
        alias_best = max(alias_best, fuzz.WRatio(q, _norm(a)))
    s = max(base, alias_best)
    # gentle boosts
    if row.get("country_match", False): s += 2
    if row.get("has_lei", False): s += 1
    return min(s, 100.0)

def resolve_company(
    name: str,
    country: Optional[str] = None,
    address_hint: Optional[str] = None,
    use_llm_tiebreak: bool = False,
    llm_pick_fn = None,  # callable(candidates: List[Dict], query: Dict) -> Dict
    k: int = 5,
) -> Dict[str, Any]:
    df = _load_companies()
    q_norm = _norm(name)
    cand = _candidate_block(df, q_norm, country)

    if country:
        cand = cand.assign(country_match=(cand["country"].str.upper() == country.upper()))
    else:
        cand = cand.assign(country_match=False)

    cand = cand.assign(has_lei=cand["lei"].notna() & cand["lei"].ne(""))

    # RapidFuzz ranking
    # Build choices as name_norm + top alias surface for better ratios
    choices = cand["name_norm"].tolist()
    scores = process.cdist([q_norm], choices, scorer=fuzz.WRatio)[0]
    cand = cand.assign(score_primary=scores)
    # add simple alias bump
    alias_bumps = []
    for al in cand["aliases"].tolist():
        bump = 0
        for a in al or []:
            bump = max(bump, fuzz.WRatio(q_norm, _norm(a)))
        alias_bumps.append(bump)
    cand = cand.assign(score_alias=alias_bumps)
    cand = cand.assign(score=cand[["score_primary","score_alias"]].max(axis=1))
    cand = cand.sort_values("score", ascending=False).head(max(k, 10))

    top = cand.iloc[0] if not cand.empty else None
    result = {
        "query": {"name": name, "name_norm": q_norm, "country": country, "address_hint": address_hint},
        "matches": [
            {
                "name": r["name"],
                "score": float(r["score"]),
                "country": r.get("country"),
                "lei": r.get("lei"),
                "wikidata_qid": r.get("wikidata_qid"),
                "aliases": r.get("aliases", []),
                "explain": {
                    "name_norm": r["name_norm"],
                    "country_match": bool(r.get("country_match", False)),
                    "has_lei": bool(r.get("has_lei", False)),
                },
            }
            for _, r in cand.head(k).iterrows()
        ],
        "final": None,
        "decision": "no_match" if top is None else "auto_or_llm",
    }

    if top is None:
        return result

    best, second = float(top["score"]), float(cand.iloc[1]["score"]) if len(cand) > 1 else 0.0
    gap = best - second

    if best >= 88.0 and gap >= 6.0:
        result["final"] = result["matches"][0]
        result["decision"] = "auto_high_conf"
        return result

    # Uncertainty band → optional LLM tie-break
    if 76.0 <= best < 88.0 and use_llm_tiebreak and llm_pick_fn is not None:
        pick = llm_pick_fn(result["matches"], result["query"])
        result["final"] = pick or result["matches"][0]
        result["decision"] = "llm_tiebreak"
        return result

    # Low confidence: return shortlist; caller can provide more hints
    result["decision"] = "needs_hint_or_llm"
    return result


Notes

This is fully usable today with only pandas and rapidfuzz.

Add postal (libpostal) if you want to parse address_hint and reward city/ADM matches.

Add a country dictionary of legal suffixes (PT “Lda.”, BR “Ltda.”, CN “有限公司”, JP “株式会社”, etc.) to improve _norm.

Optional: tiny SQLite + FTS5 (scales to millions, still no server)

Build once:

CREATE TABLE company (
  id INTEGER PRIMARY KEY,
  name TEXT, name_norm TEXT,
  country TEXT, lei TEXT, wikidata_qid TEXT, address TEXT, aliases_json TEXT
);
CREATE VIRTUAL TABLE company_fts USING fts5(name, content='company', content_rowid='id');
-- For each row, also insert into company_fts(name)
CREATE INDEX idx_company_country ON company(country);
CREATE INDEX idx_company_lei ON company(lei);


Query candidates:

def _candidates_sqlite(conn, q_norm, country=None, limit=500):
    cur = conn.cursor()
    if country:
        cur.execute("""
          SELECT c.* FROM company c
          JOIN company_fts f ON c.id=f.rowid
          WHERE c.country=? AND f.name MATCH ?
          LIMIT ?;
        """, (country.upper(), q_norm.replace(" ", "* ") + "*", limit))
    else:
        cur.execute("""
          SELECT c.* FROM company c
          JOIN company_fts f ON c.id=f.rowid
          WHERE f.name MATCH ?
          LIMIT ?;
        """, (q_norm.replace(" ", "* ") + "*", limit))
    rows = cur.fetchall()
    # Convert to DataFrame then reuse the same scoring logic


This gives you sub-100ms candidate pulls even for multi-million rows on a laptop.









Tier 1 (open, high-quality anchors)

GLEIF LEI Golden Copy – global legal entities with canonical names, addresses, and corporate events; updated 3×/day. Perfect as your backbone ID set (LEI). 
gleif.org
+1

Wikidata – labels + rich aliases, historical names, languages, and links (to LEI, ISIN, stock tickers, Wikipedia). Ideal for fuzzy matching and multilingual search. 
olh.openlibhums.org

Tier 2 (exchange rolls to fill gaps, add tickers)

ASX official list (CSV, daily) – authoritative names and codes (many miners list here). 
Australian Securities Exchange
+1

LSE instruments/SETS list – broad UK coverage of resources issuers. 
docs.londonstockexchange.com

(You can add TSX/TSXV, JSE, HKEX later—same idea: pull their official downloadable lists when available.)

Tier 3 (registries & filings, for extra confidence + addresses)

UK Companies House bulk snapshots (free) – registered names, status, addresses; great for UK-domiciled miners and subsidiaries. 
GOV.UK
+1

SEC EDGAR APIs – U.S. and many foreign issuers; use for legal names and recent name changes. 
SEC
+2
SEC
+2

SEDAR+ (Canada) – search/reporting issuers list and company profiles for Canadian miners. 
sedarplus.ca
+1

OpenCorporates API – cross-jurisdiction company registry aggregator (good for long tail; check rate limits/licensing). 
api.opencorporates.com
+2
api.opencorporates.com
+2

Smelter/refiner special case (important in mining)

Responsible Minerals Initiative facility lists (conformant/active smelters & refiners). Use to normalize smelter/refiner names and map company relationships. (Mind licensing/terms.) 
responsiblemineralsinitiative.org
+2
responsiblemineralsinitiative.org
+2

Mindat is fantastic for deposits/localities, and sometimes operators, but license/ToS are restrictive for commercial reuse—treat as a look-up source, not your primary company list. 
Mindat
+2
Mindat
+2