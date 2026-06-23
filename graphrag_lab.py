from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import textwrap
import time
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import networkx as nx


ROOT = Path(__file__).resolve().parent
DATASET_DIR = ROOT / "dataset"
OUTPUT_DIR = ROOT / "outputs"

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "how", "in", "into",
    "is", "it", "its", "of", "on", "or", "that", "the", "their", "this", "to", "was", "were", "what",
    "when", "where", "which", "who", "why", "with", "year", "years", "according", "about", "across",
}


def log(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


MOJIBAKE_REPLACEMENTS = {
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€": '"',
    "â€“": "-",
    "â€”": "-",
    "â€¢": "-",
    "Â ": " ",
    "Â": "",
    "\u00a0": " ",
}


ENTITY_DEFINITIONS = {
    "Tesla": {
        "type": "Company",
        "aliases": ["Tesla", "TSLA", "Tesla Motors"],
    },
    "Cox Automotive": {
        "type": "Company",
        "aliases": ["Cox Automotive", "Cox Auto"],
    },
    "Kelley Blue Book": {
        "type": "Company",
        "aliases": ["Kelley Blue Book", "KBB"],
    },
    "VinFast": {
        "type": "Company",
        "aliases": ["VinFast", "VinFast Auto", "VFS"],
    },
    "Vingroup": {
        "type": "Company",
        "aliases": ["Vingroup", "Vingroup JSC", "Vingroup Joint Stock Company"],
    },
    "Polestar": {
        "type": "Company",
        "aliases": ["Polestar"],
    },
    "Zeekr": {
        "type": "Company",
        "aliases": ["Zeekr", "ZEEKR"],
    },
    "NVIDIA": {
        "type": "Company",
        "aliases": ["NVIDIA", "Nvidia"],
    },
    "EPA": {
        "type": "Organization",
        "aliases": ["EPA", "US EPA", "U.S. EPA", "Environmental Protection Agency"],
    },
    "Mercedes-Benz": {
        "type": "Company",
        "aliases": ["Mercedes-Benz", "Mercedes", "Mercedes-Benz Group"],
    },
    "BMW": {
        "type": "Company",
        "aliases": ["BMW", "BMW Group"],
    },
    "Cadillac": {
        "type": "Company",
        "aliases": ["Cadillac"],
    },
    "Ford": {
        "type": "Company",
        "aliases": ["Ford", "Ford Motor Company"],
    },
    "General Motors": {
        "type": "Company",
        "aliases": ["General Motors", "GM"],
    },
    "Rivian": {
        "type": "Company",
        "aliases": ["Rivian"],
    },
    "Hyundai": {
        "type": "Company",
        "aliases": ["Hyundai", "Hyundai Motor Group"],
    },
    "Kia": {
        "type": "Company",
        "aliases": ["Kia"],
    },
    "Lexus": {
        "type": "Company",
        "aliases": ["Lexus"],
    },
    "Audi": {
        "type": "Company",
        "aliases": ["Audi"],
    },
    "Chevrolet": {
        "type": "Company",
        "aliases": ["Chevrolet", "Chevy", "Chevy Bolt", "Bolt"],
    },
    "BYD": {
        "type": "Company",
        "aliases": ["BYD", "Build Your Dreams"],
    },
    "CATL": {
        "type": "Company",
        "aliases": ["CATL", "Contemporary Amperex Technology"],
    },
    "Gotion": {
        "type": "Company",
        "aliases": ["Gotion"],
    },
    "Great Wall Motors": {
        "type": "Company",
        "aliases": ["Great Wall Motors"],
    },
    "Toyota": {
        "type": "Company",
        "aliases": ["Toyota"],
    },
    "Honda": {
        "type": "Company",
        "aliases": ["Honda"],
    },
    "Nissan": {
        "type": "Company",
        "aliases": ["Nissan"],
    },
    "Lucid": {
        "type": "Company",
        "aliases": ["Lucid", "Lucid Motors"],
    },
    "Nikola": {
        "type": "Company",
        "aliases": ["Nikola", "Nikola Corporation"],
    },
    "REE Automotive": {
        "type": "Company",
        "aliases": ["REE Automotive", "REE"],
    },
    "Volkswagen": {
        "type": "Company",
        "aliases": ["Volkswagen", "VW"],
    },
    "Volvo Cars": {
        "type": "Company",
        "aliases": ["Volvo Cars", "Volvo"],
    },
    "Geely": {
        "type": "Company",
        "aliases": ["Geely"],
    },
    "Xingji Meizu": {
        "type": "Company",
        "aliases": ["Xingji Meizu", "Xingji Meizu Group"],
    },
    "Pham Nhat Vuong": {
        "type": "Person",
        "aliases": ["Pham Nhat Vuong", "Mr. Pham Nhat Vuong"],
    },
    "Thuy Le": {
        "type": "Person",
        "aliases": ["Thuy Le", "Madam Thuy Le"],
    },
    "Lan Anh Nguyen": {
        "type": "Person",
        "aliases": ["Lan Anh Nguyen", "Ms. Lan Anh Nguyen"],
    },
    "Stephanie Valdez Streaty": {
        "type": "Person",
        "aliases": ["Stephanie Valdez Streaty"],
    },
    "United States": {
        "type": "Region",
        "aliases": ["United States", "U.S.", "US", "USA", "US EV market", "U.S. market"],
    },
    "China": {
        "type": "Region",
        "aliases": ["China", "Chinese"],
    },
    "Europe": {
        "type": "Region",
        "aliases": ["Europe", "European"],
    },
    "Vietnam": {
        "type": "Region",
        "aliases": ["Vietnam", "Vietnamese"],
    },
    "North America": {
        "type": "Region",
        "aliases": ["North America"],
    },
    "Indonesia": {
        "type": "Region",
        "aliases": ["Indonesia"],
    },
    "Philippines": {
        "type": "Region",
        "aliases": ["Philippines", "Philippine"],
    },
    "India": {
        "type": "Region",
        "aliases": ["India", "Indian"],
    },
    "Middle East": {
        "type": "Region",
        "aliases": ["Middle East", "Middle Eastern"],
    },
    "Thailand": {
        "type": "Region",
        "aliases": ["Thailand", "Thai"],
    },
    "Brazil": {
        "type": "Region",
        "aliases": ["Brazil"],
    },
    "Germany": {
        "type": "Region",
        "aliases": ["Germany", "German"],
    },
    "EV sales": {
        "type": "Concept",
        "aliases": ["EV sales", "electric vehicle sales", "electric sales"],
    },
    "EV adoption": {
        "type": "Concept",
        "aliases": ["EV adoption", "electric vehicle adoption", "EV uptake", "electric uptake"],
    },
    "Charging infrastructure": {
        "type": "Concept",
        "aliases": [
            "charging infrastructure",
            "public charging",
            "workplace charging",
            "charging network",
            "chargers",
            "charging stations",
            "charge point",
        ],
    },
    "Public and workplace charging availability": {
        "type": "Concept",
        "aliases": [
            "public and workplace charging availability",
            "public and workplace charging",
            "workplace charging availability",
        ],
    },
    "Top 10 metropolitan areas by EV uptake": {
        "type": "Concept",
        "aliases": [
            "top 10 metropolitan areas by EV uptake",
            "top U.S. metropolitan areas",
            "top US metropolitan areas",
            "metropolitan areas with the greatest electric vehicle uptake",
            "metropolitan areas",
            "EV uptake",
        ],
    },
    "Battery range": {
        "type": "Concept",
        "aliases": ["battery range", "driving range", "vehicle range", "battery capacity"],
    },
    "Consumer incentives": {
        "type": "Policy",
        "aliases": ["consumer incentives", "purchase incentives", "incentive spending", "incentives"],
    },
    "ZEV regulations": {
        "type": "Policy",
        "aliases": [
            "ZEV regulations",
            "zero-emission vehicle regulations",
            "zero-emission vehicle (ZEV) regulations",
        ],
    },
    "Inflation Reduction Act": {
        "type": "Policy",
        "aliases": ["Inflation Reduction Act", "IRA"],
    },
    "Bipartisan Infrastructure Law": {
        "type": "Policy",
        "aliases": ["Bipartisan Infrastructure Law"],
    },
    "EV tax credit": {
        "type": "Policy",
        "aliases": ["EV tax credit", "$7,500 incentive", "full $7,500 incentive"],
    },
    "Market share": {
        "type": "Concept",
        "aliases": ["market share", "share of the electric vehicle market", "EV share"],
    },
    "Dealer sentiment": {
        "type": "Concept",
        "aliases": ["dealer sentiment", "Automobile Dealer Sentiment Index"],
    },
}


BENCHMARK_QUESTIONS = [
    "Why did Tesla's Q1 2024 U.S. EV market share fall, and which brands grew more than 50% year over year?",
    "What Q3 2024 delivery and revenue results did VinFast report, and who backed its funding?",
    "How are ZEV regulations linked to U.S. EV sales share and model availability?",
    "How does public and workplace charging availability relate to EV uptake in top U.S. metropolitan areas?",
    "What consumer charging concerns could slow EV adoption according to the corpus?",
    "Which company surpassed Tesla as the largest EV producer, and where are Chinese EV brands expanding?",
    "How does the Inflation Reduction Act connect to EV leasing incentives or battery investment?",
    "How did Cadillac, Mercedes, BMW, Audi, and Ford perform in Q1 2024 EV sales relative to Tesla?",
    "What is VinFast's relationship with Vingroup and Pham Nhat Vuong?",
    "What are the main barriers to EV adoption mentioned across Deloitte, EPA, and McKinsey style sources?",
    "Why is Germany's EV charging infrastructure investment significant for consumer sentiment?",
    "How did Polestar describe its strategic partners and major EV business risks?",
    "What first-quarter 2024 themes were reported for Zeekr?",
    "What did Nikola report in first-quarter 2023 results?",
    "What investment level did U.S. EV investments reach, and what does that imply for the sector?",
    "How are Chinese battery companies investing in Europe and the United States?",
    "What does the EPA say about battery manufacturing emissions versus lifetime EV emissions?",
    "How does the Bipartisan Infrastructure Law address EV charging concerns?",
    "What does Goldman Sachs say about why EV sales are slowing?",
    "How do dealer sentiment reports describe uncertainty in the EV and auto market?",
]


@dataclass(frozen=True)
class Document:
    doc_id: str
    path: Path
    query: str
    title: str
    link: str
    snippet: str
    content: str
    text: str
    skipped_content: bool


@dataclass(frozen=True)
class Evidence:
    source_id: str
    title: str
    text: str
    score: float


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str | None
    model: str
    judge_model: str
    chunk_chars: int
    max_chunks_per_doc: int
    temperature: float


@dataclass(frozen=True)
class Triple:
    source: str
    relation: str
    target: str
    source_type: str
    target_type: str
    evidence: str
    confidence: float


class EntityMatcher:
    def __init__(self, definitions: dict[str, dict[str, object]]) -> None:
        self.definitions = definitions
        aliases: list[tuple[str, str]] = []
        for canonical, info in definitions.items():
            for alias in info["aliases"]:
                aliases.append((str(alias), canonical))
            aliases.append((canonical, canonical))
        aliases.sort(key=lambda item: len(item[0]), reverse=True)
        self.aliases = aliases

    def find(self, text: str) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        for alias, canonical in self.aliases:
            if canonical in seen:
                continue
            if _contains_alias(text, alias):
                seen.add(canonical)
                found.append(canonical)
        return found

    def entity_type(self, entity: str) -> str:
        return str(self.definitions.get(entity, {}).get("type", "Entity"))


def _contains_alias(text: str, alias: str) -> bool:
    if alias in {"U.S.", "US EV market", "U.S. market"}:
        pattern = re.escape(alias)
    elif alias in {"GM", "VW", "BMW", "BYD", "CATL", "IRA", "VFS"}:
        pattern = rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])"
    else:
        pattern = rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def clean_text(text: str) -> str:
    for bad, good in MOJIBAKE_REPLACEMENTS.items():
        text = text.replace(bad, good)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_entity_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(text).lower())


def canonicalize_entity_name(name: str) -> str:
    cleaned = clean_text(name)
    if not cleaned or cleaned.startswith(("doc:", "metric:")):
        return cleaned
    key = normalize_entity_key(cleaned)
    for canonical, info in ENTITY_DEFINITIONS.items():
        aliases = [canonical, *[str(alias) for alias in info.get("aliases", [])]]
        if key in {normalize_entity_key(alias) for alias in aliases}:
            return canonical
    return cleaned


def canonical_node_type(name: str, fallback: str = "Entity") -> str:
    if name in ENTITY_DEFINITIONS:
        return str(ENTITY_DEFINITIONS[name].get("type", fallback))
    return fallback


def probably_binary_or_pdf_garbage(text: str) -> bool:
    if not text:
        return False
    bad_chars = sum(1 for char in text if char == "\ufffd")
    controls = sum(1 for char in text if ord(char) < 32 and char not in "\n\r\t")
    bad_ratio = (bad_chars + controls) / max(len(text), 1)
    stream_markers = text.count("endstream") + text.count("endobj")
    return bad_ratio > 0.015 or stream_markers > 12


def read_field(raw: str, field: str) -> str:
    match = re.search(rf"^{re.escape(field)}:\s*(.+)$", raw, flags=re.MULTILINE)
    return clean_text(match.group(1)) if match else ""


def read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


def read_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float, got {value!r}") from exc


def load_llm_config(required: bool = True) -> LLMConfig | None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        if required:
            raise RuntimeError(
                "Missing OPENAI_API_KEY. Copy .env_example to .env, fill OPENAI_API_KEY and OPENAI_BASE_URL, "
                "then run again. Use --mode offline only for local smoke tests."
            )
        return None

    return LLMConfig(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None,
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        judge_model=os.getenv("OPENAI_JUDGE_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")).strip(),
        chunk_chars=read_int_env("GRAPHRAG_CHUNK_CHARS", 6000),
        max_chunks_per_doc=read_int_env("GRAPHRAG_MAX_CHUNKS_PER_DOC", 3),
        temperature=read_float_env("OPENAI_TEMPERATURE", 0.0),
    )


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        from openai import OpenAI

        self.config = config
        kwargs: dict[str, Any] = {"api_key": config.api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self.client = OpenAI(**kwargs)
        self.calls = 0
        self.estimated_prompt_chars = 0
        self.estimated_completion_chars = 0

    def json_chat(self, system: str, user: str, model: str | None = None) -> dict[str, Any]:
        self.calls += 1
        self.estimated_prompt_chars += len(system) + len(user)
        response = self.client.chat.completions.create(
            model=model or self.config.model,
            temperature=self.config.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or "{}"
        self.estimated_completion_chars += len(content)
        return parse_json_object(content)

    @property
    def estimated_tokens(self) -> int:
        return math.ceil((self.estimated_prompt_chars + self.estimated_completion_chars) / 4)


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object")
    return data


def load_documents(dataset_dir: Path) -> list[Document]:
    documents: list[Document] = []
    for path in sorted(dataset_dir.glob("doc_*.txt"), key=lambda p: int(re.search(r"\d+", p.stem).group())):
        raw = path.read_text(encoding="utf-8", errors="replace")
        query = read_field(raw, "Query")
        title = read_field(raw, "Title")
        link = read_field(raw, "Link")
        snippet = read_field(raw, "Snippet")
        content = raw.split("Full Content:", 1)[1] if "Full Content:" in raw else ""
        skipped = probably_binary_or_pdf_garbage(content)
        clean_content = "" if skipped else clean_text(content)
        text = clean_text("\n".join(part for part in [title, snippet, clean_content] if part))
        if len(text) > 90_000:
            text = text[:90_000]
        documents.append(
            Document(
                doc_id=path.stem,
                path=path,
                query=query,
                title=title or path.stem,
                link=link,
                snippet=snippet,
                content=clean_content,
                text=text,
                skipped_content=skipped,
            )
        )
    return documents


def chunk_document(doc: Document, chunk_chars: int, max_chunks: int) -> list[str]:
    text = doc.text
    if not text:
        return []
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text) and len(chunks) < max_chunks:
        end = min(len(text), cursor + chunk_chars)
        if end < len(text):
            boundary = max(text.rfind(". ", cursor, end), text.rfind("\n", cursor, end))
            if boundary > cursor + chunk_chars // 2:
                end = boundary + 1
        chunk = text[cursor:end].strip()
        if chunk:
            chunks.append(chunk)
        cursor = end
    return chunks


def cache_key(doc: Document, chunk_index: int, chunk: str) -> str:
    digest = hashlib.sha256(chunk.encode("utf-8")).hexdigest()[:16]
    return f"{doc.doc_id}:{chunk_index}:{len(chunk)}:{digest}"


def load_triple_cache(cache_path: Path) -> dict[str, list[dict[str, Any]]]:
    cache: dict[str, list[dict[str, Any]]] = {}
    if not cache_path.exists():
        return cache
    for line in cache_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cache[str(row["key"])] = list(row.get("triples", []))
    return cache


def append_triple_cache(cache_path: Path, key: str, triples: list[dict[str, Any]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps({"key": key, "triples": triples}, ensure_ascii=False) + "\n")


def normalize_relation(relation: str) -> str:
    relation = re.sub(r"[^A-Za-z0-9_ ]+", "", relation.strip().upper())
    relation = re.sub(r"\s+", "_", relation)
    return relation[:60] or "RELATED_TO"


def coerce_triple(raw: dict[str, Any], doc: Document) -> Triple | None:
    source = clean_text(str(raw.get("source", "")))
    relation = normalize_relation(str(raw.get("relation", "")))
    target = clean_text(str(raw.get("target", "")))
    evidence = clean_text(str(raw.get("evidence", "")))
    if not source or not relation or not target:
        return None
    if source.lower() == target.lower():
        return None
    try:
        confidence = float(raw.get("confidence", 0.75))
    except (TypeError, ValueError):
        confidence = 0.75
    confidence = max(0.0, min(confidence, 1.0))
    return Triple(
        source=source[:120],
        relation=relation,
        target=target[:160],
        source_type=clean_text(str(raw.get("source_type", "Entity")))[:40] or "Entity",
        target_type=clean_text(str(raw.get("target_type", "Entity")))[:40] or "Entity",
        evidence=evidence[:700] or doc.title,
        confidence=confidence,
    )


def extract_triples_from_chunk(llm: LLMClient, doc: Document, chunk: str, chunk_index: int) -> list[Triple]:
    system = (
        "You extract knowledge graph triples for a GraphRAG system. "
        "Return only JSON. Do not add prose. "
        "Use concise canonical entity names. Relations must be uppercase snake_case. "
        "Prefer factual business/technology/policy relations over generic co-occurrence."
    )
    user = f"""
Extract up to 18 high-value triples from this Tech Company Corpus chunk.

Required JSON schema:
{{
  "triples": [
    {{
      "source": "entity name",
      "relation": "RELATION_NAME",
      "target": "entity/metric/value",
      "source_type": "Company|Person|Policy|Region|Metric|Concept|Document",
      "target_type": "Company|Person|Policy|Region|Metric|Concept|Document",
      "evidence": "short exact evidence sentence from the text",
      "confidence": 0.0
    }}
  ]
}}

Guidelines:
- Extract relations useful for multi-hop GraphRAG, for example FOUNDED_BY, SUBSIDIARY_OF, BACKED_BY,
  REPORTED_REVENUE, DELIVERED_VEHICLES, HAS_MARKET_SHARE, EXPANDS_TO, COMPETES_WITH,
  SUPPORTED_BY_POLICY, BARRIER_TO_ADOPTION, CAUSED_BY, INVESTED_IN, COLLABORATES_WITH.
- Turn numeric attributes into target nodes, for example "21,912 vehicles in Q3 2024".
- Do not invent facts not supported by the text.

Document ID: {doc.doc_id}
Title: {doc.title}
Link: {doc.link}
Chunk: {chunk_index}

Text:
{chunk}
""".strip()
    data = llm.json_chat(system, user)
    triples = data.get("triples", [])
    if not isinstance(triples, list):
        return []
    coerced = [coerce_triple(item, doc) for item in triples if isinstance(item, dict)]
    return [triple for triple in coerced if triple is not None]


def extract_llm_triples(
    documents: list[Document],
    llm: LLMClient,
    output_dir: Path,
    force_refresh: bool = False,
) -> list[tuple[Document, Triple]]:
    cache_path = output_dir / "llm_triples_cache.jsonl"
    cache = {} if force_refresh else load_triple_cache(cache_path)
    extracted: list[tuple[Document, Triple]] = []
    total_chunks = sum(len(chunk_document(doc, llm.config.chunk_chars, llm.config.max_chunks_per_doc)) for doc in documents)
    cached_chunks = 0
    uncached_chunks = 0
    benchmark_llm_calls = len(BENCHMARK_QUESTIONS) * 3
    processed_chunks = 0
    log(
        "LLM indexing plan: "
        f"documents={len(documents)}, chunks={total_chunks}, cache entries={len(cache)}, "
        f"benchmark_llm_calls={benchmark_llm_calls}, total_est_llm_calls={benchmark_llm_calls}"
    )

    for doc in documents:
        for chunk_index, chunk in enumerate(chunk_document(doc, llm.config.chunk_chars, llm.config.max_chunks_per_doc), start=1):
            processed_chunks += 1
            key = cache_key(doc, chunk_index, chunk)
            if key in cache:
                raw_triples = cache[key]
                triples = [coerce_triple(item, doc) for item in raw_triples if isinstance(item, dict)]
                extracted.extend((doc, triple) for triple in triples if triple is not None)
                cached_chunks += 1
                log(
                    f"LLM indexing [{processed_chunks}/{total_chunks}] {doc.doc_id} chunk {chunk_index}: "
                    f"cache hit, triples={len(triples)}"
                )
                continue
            uncached_chunks += 1
            log(f"LLM indexing [{processed_chunks}/{total_chunks}] {doc.doc_id} chunk {chunk_index}: calling LLM")
            triples = extract_triples_from_chunk(llm, doc, chunk, chunk_index)
            raw_triples = [
                {
                    "source": triple.source,
                    "relation": triple.relation,
                    "target": triple.target,
                    "source_type": triple.source_type,
                    "target_type": triple.target_type,
                    "evidence": triple.evidence,
                    "confidence": triple.confidence,
                }
                for triple in triples
            ]
            append_triple_cache(cache_path, key, raw_triples)
            extracted.extend((doc, triple) for triple in triples)
            log(
                f"LLM indexing [{processed_chunks}/{total_chunks}] {doc.doc_id} chunk {chunk_index}: "
                f"triples={len(triples)}, llm_calls={llm.calls}, est_tokens={llm.estimated_tokens}"
            )

    log(
        "LLM indexing summary: "
        f"cached_chunks={cached_chunks}, uncached_chunks={uncached_chunks}, extracted_triples={len(extracted)}, "
        f"llm_calls_used={llm.calls}, est_tokens={llm.estimated_tokens}"
    )
    return extracted


def estimate_llm_work(
    documents: list[Document],
    config: LLMConfig,
    output_dir: Path,
    force_refresh: bool,
    benchmark_questions: int,
) -> dict[str, float]:
    cache_path = output_dir / "llm_triples_cache.jsonl"
    cache = {} if force_refresh else load_triple_cache(cache_path)
    total_chunks = 0
    uncached_chunks = 0
    for doc in documents:
        chunks = chunk_document(doc, config.chunk_chars, config.max_chunks_per_doc)
        total_chunks += len(chunks)
        for chunk_index, chunk in enumerate(chunks, start=1):
            if cache_key(doc, chunk_index, chunk) not in cache:
                uncached_chunks += 1

    benchmark_calls = benchmark_questions * 3
    total_llm_calls = uncached_chunks + benchmark_calls
    seconds_per_call = read_float_env("GRAPHRAG_EST_SECONDS_PER_LLM_CALL", 10.0)
    estimated_seconds = total_llm_calls * seconds_per_call
    return {
        "total_chunks": float(total_chunks),
        "cached_chunks": float(total_chunks - uncached_chunks),
        "uncached_chunks": float(uncached_chunks),
        "benchmark_calls": float(benchmark_calls),
        "total_llm_calls": float(total_llm_calls),
        "seconds_per_call": float(seconds_per_call),
        "estimated_seconds": float(estimated_seconds),
    }


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} minutes"
    return f"{minutes / 60:.1f} hours"


def build_graph_from_llm_triples(triples: list[tuple[Document, Triple]]) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    for doc, triple in triples:
        doc_node = f"doc:{doc.doc_id}"
        source = canonicalize_entity_name(triple.source)
        target = canonicalize_entity_name(triple.target)
        source_type = canonical_node_type(source, triple.source_type)
        target_type = canonical_node_type(target, triple.target_type)
        add_node(graph, doc_node, "Document", doc.doc_id, title=doc.title, link=doc.link)
        add_node(graph, source, source_type, source, mentions=0)
        add_node(graph, target, target_type, target, mentions=0)
        add_fact(
            graph,
            source,
            triple.relation,
            target,
            triple.evidence,
            doc.doc_id,
            doc.title,
            weight=max(0.25, triple.confidence),
        )
        add_fact(graph, source, "MENTIONED_IN", doc_node, doc.title, doc.doc_id, doc.title, 0.2)
        add_fact(graph, target, "MENTIONED_IN", doc_node, doc.title, doc.doc_id, doc.title, 0.2)
    return graph


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    rough = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text)
    sentences = []
    for sentence in rough:
        sentence = sentence.strip(" -\t\n")
        if 35 <= len(sentence) <= 700:
            sentences.append(sentence)
    return sentences


def content_terms(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-']+", text.lower())
    return [
        word
        for word in words
        if word not in STOP_WORDS and (len(word) > 2 or re.fullmatch(r"q[1-4]", word)) and word not in {"evs", "ev"}
    ]


def query_markers(text: str) -> set[str]:
    lowered = text.lower()
    markers = set(re.findall(r"\bq[1-4]\b|\b20\d{2}\b|\b\d+(?:\.\d+)?%", lowered))
    for phrase in [
        "year over year",
        "year-over-year",
        "more than 50%",
        "market share",
        "sales",
        "deliveries",
        "revenue",
        "funding",
        "charging",
        "investment",
        "investing",
    ]:
        if phrase in lowered:
            markers.add(phrase)
    return markers


def marker_overlap_score(markers: set[str], text: str) -> float:
    lowered = text.lower()
    score = 0.0
    for marker in markers:
        if marker in lowered:
            score += 1.0
    return score


def add_node(graph: nx.MultiDiGraph, node: str, node_type: str, label: str | None = None, **attrs: object) -> None:
    if not graph.has_node(node):
        graph.add_node(node, type=node_type, label=label or node, **attrs)
    else:
        graph.nodes[node]["mentions"] = int(graph.nodes[node].get("mentions", 0)) + 1


def add_fact(
    graph: nx.MultiDiGraph,
    source: str,
    relation: str,
    target: str,
    evidence: str,
    source_id: str,
    title: str,
    weight: float = 1.0,
) -> None:
    if graph.has_edge(source, target, key=relation):
        data = graph[source][target][relation]
        data["weight"] = float(data.get("weight", 1.0)) + weight
        sources = set(str(data.get("sources", "")).split("|")) if data.get("sources") else set()
        sources.add(source_id)
        data["sources"] = "|".join(sorted(sources))
        evidence_list = [item for item in str(data.get("evidence", "")).split(" || ") if item]
        if evidence and evidence not in evidence_list and len(evidence_list) < 4:
            evidence_list.append(evidence)
        data["evidence"] = " || ".join(evidence_list)
        return

    graph.add_edge(
        source,
        target,
        key=relation,
        relation=relation,
        weight=weight,
        evidence=evidence,
        sources=source_id,
        title=title,
    )


def metric_node(label: str) -> str:
    cleaned = re.sub(r"\s+", " ", label.strip())
    return f"metric:{cleaned[:90]}"


def extract_numbers(sentence: str) -> list[str]:
    money = re.findall(r"(?:US)?\$[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:billion|million|trillion)?", sentence, re.I)
    percents = re.findall(r"[0-9]+(?:\.[0-9]+)?%", sentence)
    counts = re.findall(r"\b[0-9][0-9,]{2,}\b", sentence)
    return money + percents + counts


def extract_pattern_facts(
    graph: nx.MultiDiGraph,
    sentence: str,
    entities: list[str],
    doc: Document,
) -> None:
    lowered = sentence.lower()
    numbers = extract_numbers(sentence)

    for entity in entities:
        if ENTITY_DEFINITIONS.get(entity, {}).get("type") != "Company":
            continue

        if "deliver" in lowered and numbers:
            target = metric_node(f"{entity} deliveries: {', '.join(numbers[:3])}")
            add_node(graph, target, "Metric", target.replace("metric:", ""))
            add_fact(graph, entity, "DELIVERED", target, sentence, doc.doc_id, doc.title, 2.0)

        if "revenue" in lowered and numbers:
            target = metric_node(f"{entity} revenue: {', '.join(numbers[:3])}")
            add_node(graph, target, "Metric", target.replace("metric:", ""))
            add_fact(graph, entity, "REPORTED_REVENUE", target, sentence, doc.doc_id, doc.title, 2.0)

        if "market share" in lowered or "share of the electric vehicle market" in lowered:
            if numbers:
                target = metric_node(f"{entity} market share: {', '.join(numbers[:3])}")
                add_node(graph, target, "Metric", target.replace("metric:", ""))
                add_fact(graph, entity, "HAS_MARKET_SHARE", target, sentence, doc.doc_id, doc.title, 2.0)

        if "sales" in lowered and numbers:
            if any(word in lowered for word in ["down", "declined", "fell", "lower", "decrease", "slow"]):
                target = metric_node(f"{entity} sales decline/change: {', '.join(numbers[:3])}")
                add_node(graph, target, "Metric", target.replace("metric:", ""))
                add_fact(graph, entity, "SALES_DECLINED", target, sentence, doc.doc_id, doc.title, 2.0)
            if any(word in lowered for word in ["up", "increase", "growth", "grew", "rose", "higher", "achieved"]):
                target = metric_node(f"{entity} sales growth/change: {', '.join(numbers[:3])}")
                add_node(graph, target, "Metric", target.replace("metric:", ""))
                add_fact(graph, entity, "SALES_INCREASED", target, sentence, doc.doc_id, doc.title, 2.0)

        if any(word in lowered for word in ["funding", "loans", "grants", "capital commitments", "financial backing"]):
            if numbers:
                target = metric_node(f"{entity} funding: {', '.join(numbers[:3])}")
                add_node(graph, target, "Metric", target.replace("metric:", ""))
                add_fact(graph, entity, "HAS_FUNDING", target, sentence, doc.doc_id, doc.title, 2.0)

    if "subsidiary of vingroup" in lowered:
        add_fact(graph, "VinFast", "SUBSIDIARY_OF", "Vingroup", sentence, doc.doc_id, doc.title, 3.0)

    if "founder" in lowered and "pham nhat vuong" in lowered and "vinfast" in lowered:
        add_fact(graph, "Pham Nhat Vuong", "FOUNDER_OR_BACKER_OF", "VinFast", sentence, doc.doc_id, doc.title, 3.0)

    if "chairwoman of vinfast" in lowered:
        add_fact(graph, "Thuy Le", "CHAIRWOMAN_OF", "VinFast", sentence, doc.doc_id, doc.title, 3.0)

    if "chief financial officer of vinfast" in lowered or "cfo of vinfast" in lowered:
        add_fact(graph, "Lan Anh Nguyen", "CFO_OF", "VinFast", sentence, doc.doc_id, doc.title, 3.0)

    if "cox automotive" in lowered and "stephanie valdez streaty" in lowered:
        add_fact(graph, "Stephanie Valdez Streaty", "DIRECTOR_AT", "Cox Automotive", sentence, doc.doc_id, doc.title, 3.0)

    if "byd" in lowered and "surpassing tesla" in lowered:
        add_fact(graph, "BYD", "SURPASSED", "Tesla", sentence, doc.doc_id, doc.title, 3.0)

    if "catl-ford" in lowered or ("catl" in lowered and "ford collaboration" in lowered):
        add_fact(graph, "CATL", "COLLABORATES_WITH", "Ford", sentence, doc.doc_id, doc.title, 3.0)

    if "zev" in lowered and "5%" in sentence:
        target = metric_node("ZEV states combined new EV share: 5%")
        add_node(graph, target, "Metric", target.replace("metric:", ""))
        add_fact(graph, "ZEV regulations", "ASSOCIATED_WITH", target, sentence, doc.doc_id, doc.title, 3.0)

    if "zev" in lowered and "13 more electric models" in lowered:
        target = metric_node("ZEV states model availability: at least 13 more electric models")
        add_node(graph, target, "Metric", target.replace("metric:", ""))
        add_fact(graph, "ZEV regulations", "INCREASED_MODEL_AVAILABILITY", target, sentence, doc.doc_id, doc.title, 3.0)

    if "bipartisan infrastructure law" in lowered and "$7.5 billion" in sentence:
        target = metric_node("Bipartisan Infrastructure Law charger investment: up to $7.5 billion")
        add_node(graph, target, "Metric", target.replace("metric:", ""))
        add_fact(graph, "Bipartisan Infrastructure Law", "FUNDS", target, sentence, doc.doc_id, doc.title, 3.0)

    if "inflation reduction act" in lowered or "ira" in lowered:
        for entity in entities:
            if entity != "Inflation Reduction Act":
                add_fact(graph, "Inflation Reduction Act", "RELATED_TO", entity, sentence, doc.doc_id, doc.title, 1.5)


def build_graph(documents: list[Document], matcher: EntityMatcher) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()

    for entity, info in ENTITY_DEFINITIONS.items():
        add_node(graph, entity, str(info["type"]), entity, mentions=0)

    for doc in documents:
        doc_node = f"doc:{doc.doc_id}"
        add_node(graph, doc_node, "Document", doc.doc_id, title=doc.title, link=doc.link)
        doc_entities = matcher.find(doc.text)
        for entity in doc_entities:
            add_fact(graph, entity, "MENTIONED_IN", doc_node, doc.title, doc.doc_id, doc.title, 0.4)

        for sentence in split_sentences(doc.text):
            entities = matcher.find(sentence)
            if not entities:
                continue
            for entity in entities:
                graph.nodes[entity]["mentions"] = int(graph.nodes[entity].get("mentions", 0)) + 1

            if len(entities) >= 2:
                for left, right in combinations(sorted(set(entities)), 2):
                    if left == right:
                        continue
                    add_fact(graph, left, "CO_OCCURS_WITH", right, sentence, doc.doc_id, doc.title, 0.7)

            extract_pattern_facts(graph, sentence, entities, doc)

    return graph


def edge_rows(graph: nx.MultiDiGraph) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for source, target, key, data in graph.edges(keys=True, data=True):
        rows.append(
            {
                "source": source,
                "relation": data.get("relation", key),
                "target": target,
                "weight": round(float(data.get("weight", 1.0)), 3),
                "sources": data.get("sources", ""),
                "evidence": data.get("evidence", ""),
            }
        )
    return sorted(rows, key=lambda row: (-float(row["weight"]), str(row["source"]), str(row["target"])))


def write_triples(graph: nx.MultiDiGraph, output_dir: Path) -> None:
    rows = edge_rows(graph)
    output = output_dir / "triples.csv"
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["source", "relation", "target", "weight", "sources", "evidence"])
        writer.writeheader()
        writer.writerows(rows)


def infer_node_type(node: str) -> str:
    if node.startswith("doc:"):
        return "Document"
    if node.startswith("metric:"):
        return "Metric"
    if node in ENTITY_DEFINITIONS:
        return str(ENTITY_DEFINITIONS[node].get("type", "Entity"))
    return "Entity"


def load_graph_from_triples(triples_path: Path) -> nx.MultiDiGraph:
    if not triples_path.exists():
        raise FileNotFoundError(f"Missing triples file: {triples_path}. Run graphrag_lab.py once to build artifacts.")

    graph = nx.MultiDiGraph()
    with triples_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            source = canonicalize_entity_name(row.get("source", ""))
            relation = normalize_relation(row.get("relation", "RELATED_TO"))
            target = canonicalize_entity_name(row.get("target", ""))
            if not source or not target:
                continue
            try:
                weight = float(row.get("weight", 1.0))
            except ValueError:
                weight = 1.0
            add_node(graph, source, canonical_node_type(source, infer_node_type(source)), source, mentions=0)
            add_node(graph, target, canonical_node_type(target, infer_node_type(target)), target, mentions=0)
            add_fact(
                graph,
                source,
                relation,
                target,
                clean_text(row.get("evidence", "")),
                clean_text(row.get("sources", "")),
                "",
                weight,
            )
    return graph


def graph_to_simple(graph: nx.MultiDiGraph, include_documents: bool = False) -> nx.Graph:
    simple = nx.Graph()
    for node, data in graph.nodes(data=True):
        if not include_documents and data.get("type") == "Document":
            continue
        simple.add_node(
            node,
            type=str(data.get("type", "Entity")),
            label=str(data.get("label", node)),
            mentions=int(data.get("mentions", 0) or 0),
        )

    for source, target, _key, data in graph.edges(keys=True, data=True):
        if source not in simple or target not in simple:
            continue
        weight = float(data.get("weight", 1.0))
        relation = str(data.get("relation", "RELATED_TO"))
        if simple.has_edge(source, target):
            simple[source][target]["weight"] += weight
            relations = Counter(simple[source][target]["relations"].split("|"))
            relations[relation] += 1
            simple[source][target]["relations"] = "|".join(relations.keys())
        else:
            simple.add_edge(source, target, weight=weight, relations=relation)
    return simple


def draw_graph(graph: nx.MultiDiGraph, output_dir: Path, max_nodes: int = 40) -> None:
    mpl_config = output_dir / ".matplotlib"
    mpl_config.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_config))

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    semantic = nx.Graph()
    weak_relations = {"CO_OCCURS_WITH", "RELATED_TO"}
    metric_relation_terms = {
        "MARKET_SHARE",
        "SALES",
        "DELIVER",
        "REVENUE",
        "FUND",
        "INVEST",
        "GROWTH",
        "EMISSION",
        "CHARGER",
        "CHARGING",
        "DENSITY",
        "SHARE",
        "PRICE",
        "COST",
    }
    visual_anchors = {
        "Tesla",
        "VinFast",
        "Vingroup",
        "Pham Nhat Vuong",
        "BYD",
        "CATL",
        "Ford",
        "Mercedes-Benz",
        "BMW",
        "Audi",
        "Cadillac",
        "ZEV regulations",
        "Inflation Reduction Act",
        "Bipartisan Infrastructure Law",
        "Charging infrastructure",
        "Public and workplace charging availability",
        "Top 10 metropolitan areas by EV uptake",
        "EPA",
        "Polestar",
        "Zeekr",
        "Nikola",
        "China",
        "United States",
        "Europe",
    }

    for node, data in graph.nodes(data=True):
        if data.get("type") == "Document":
            continue
        semantic.add_node(
            node,
            type=str(data.get("type", "Entity")),
            label=str(data.get("label", node)),
            mentions=int(data.get("mentions", 0) or 0),
        )

    for source, target, _key, data in graph.edges(keys=True, data=True):
        if source not in semantic or target not in semantic:
            continue
        relation = str(data.get("relation", "RELATED_TO"))
        if relation == "MENTIONED_IN":
            continue
        source_type = str(semantic.nodes[source].get("type", "Entity"))
        target_type = str(semantic.nodes[target].get("type", "Entity"))
        if source_type == "Metric" and target_type == "Metric":
            continue
        relation_has_metric_signal = any(term in relation for term in metric_relation_terms)
        if "Metric" in {source_type, target_type} and not relation_has_metric_signal:
            continue
        raw_weight = float(data.get("weight", 1.0))
        visual_weight = raw_weight * (0.22 if relation in weak_relations else 1.0)
        if relation == "CO_OCCURS_WITH" and visual_weight < 0.45:
            continue
        if semantic.has_edge(source, target):
            semantic[source][target]["weight"] += visual_weight
            relations = Counter(semantic[source][target]["relations"].split("|"))
            relations[relation] += 1
            semantic[source][target]["relations"] = "|".join(relations.keys())
        else:
            semantic.add_edge(
                source,
                target,
                weight=visual_weight,
                relations=relation,
                sources=str(data.get("sources", "")),
            )

    semantic.remove_nodes_from([node for node, degree in semantic.degree() if degree == 0])
    if semantic.number_of_nodes() == 0:
        return

    def node_score(node: str) -> float:
        node_type = str(semantic.nodes[node].get("type", "Entity"))
        score = float(semantic.degree(node, weight="weight"))
        if node in visual_anchors:
            score += 18.0
        if node_type in {"Company", "Policy", "Organization"}:
            score += 4.0
        if node_type == "Concept":
            score += 2.0
        if node_type == "Metric":
            score -= 5.0
        if node in GENERIC_GRAPH_NODES and node not in {"China", "United States", "Europe"}:
            score -= 3.5
        return score

    def label_for(node: str) -> str:
        label = str(semantic.nodes[node].get("label", node)).replace("metric:", "")
        label = re.sub(r"\s+", " ", label).strip()
        if len(label) > 20:
            label = label[:19].rstrip() + "..."
        return "\n".join(textwrap.wrap(label, width=10, break_long_words=False)) or node[:10]

    def edge_score(source: str, target: str, data: dict[str, object]) -> float:
        relation = str(data.get("relations", "RELATED_TO"))
        score = float(data.get("weight", 1.0))
        score += 0.08 * node_score(source) + 0.08 * node_score(target)
        if source in visual_anchors or target in visual_anchors:
            score += 3.0
        if source in {"China", "United States", "Europe"} or target in {"China", "United States", "Europe"}:
            score -= 3.8
        if relation in weak_relations:
            score -= 1.0
        if "Metric" in {semantic.nodes[source].get("type"), semantic.nodes[target].get("type")}:
            score -= 0.6
        return score

    focus_order = [
        "Tesla",
        "BYD",
        "Ford",
        "VinFast",
        "China",
        "United States",
        "CATL",
        "Inflation Reduction Act",
    ]
    focus = next((node for node in focus_order if node in semantic), max(semantic.nodes, key=node_score))
    focus_component = nx.node_connected_component(semantic, focus)
    selected_nodes: set[str] = {focus}
    tree_edges: list[tuple[str, str, dict[str, object]]] = []
    incident_counts: Counter[str] = Counter()

    def incident_limit(node: str) -> int:
        if node in {"China", "United States", "Europe"}:
            return 8
        if node in visual_anchors:
            return 12
        return 10

    while len(selected_nodes) < max_nodes:
        expansion_edges = []
        for source, target, data in semantic.edges(data=True):
            if source not in focus_component or target not in focus_component:
                continue
            source_selected = source in selected_nodes
            target_selected = target in selected_nodes
            if source_selected == target_selected:
                continue
            if incident_counts[source] >= incident_limit(source) or incident_counts[target] >= incident_limit(target):
                continue
            relation = str(data.get("relations", ""))
            if relation == "CO_OCCURS_WITH" and len(selected_nodes) < max_nodes // 2:
                continue
            expansion_edges.append((source, target, data))
        if not expansion_edges:
            break
        source, target, data = max(expansion_edges, key=lambda item: edge_score(item[0], item[1], item[2]))
        selected_nodes.update([source, target])
        tree_edges.append((source, target, data))
        incident_counts[source] += 1
        incident_counts[target] += 1

    selected_edge_keys = {tuple(sorted((source, target))) for source, target, _data in tree_edges}
    selected_edges = list(tree_edges)
    internal_edges = sorted(
        (
            (source, target, data)
            for source, target, data in semantic.edges(data=True)
            if source in selected_nodes and target in selected_nodes and tuple(sorted((source, target))) not in selected_edge_keys
        ),
        key=lambda item: edge_score(item[0], item[1], item[2]),
        reverse=True,
    )
    selected_edges.extend(internal_edges[: max_nodes])

    visual_graph = nx.Graph()
    for node in selected_nodes:
        visual_graph.add_node(node, **semantic.nodes[node])
    for source, target, data in selected_edges:
        if source in visual_graph and target in visual_graph:
            visual_graph.add_edge(source, target, **data)
    visual_graph.remove_nodes_from([node for node, degree in visual_graph.degree() if degree == 0])

    if visual_graph.number_of_nodes() == 0:
        return

    pos = nx.spring_layout(
        visual_graph,
        seed=19,
        k=1.35 / math.sqrt(max(visual_graph.number_of_nodes(), 1)),
        iterations=450,
        weight="weight",
        scale=3.2,
    )

    fig, ax = plt.subplots(figsize=(18, 14), facecolor="white")
    ax.set_facecolor("white")
    edge_widths = [
        1.0 + min(2.4, 0.24 * math.sqrt(float(data.get("weight", 1.0))))
        for _, _, data in visual_graph.edges(data=True)
    ]
    nx.draw_networkx_edges(
        visual_graph,
        pos,
        width=edge_widths,
        edge_color="#AEB9BA",
        alpha=0.62,
        ax=ax,
    )

    node_sizes = [
        720 + min(1250, 130 * math.sqrt(max(1.0, float(visual_graph.degree(node, weight="weight")))))
        for node in visual_graph.nodes
    ]
    nx.draw_networkx_nodes(
        visual_graph,
        pos,
        node_size=node_sizes,
        node_color="#344555",
        linewidths=1.2,
        edgecolors="#F8FAFC",
        alpha=0.98,
        ax=ax,
    )

    nx.draw_networkx_labels(
        visual_graph,
        pos,
        labels={node: label_for(node) for node in visual_graph.nodes},
        font_size=8,
        font_family="DejaVu Sans",
        font_weight="bold",
        font_color="white",
        ax=ax,
    )

    labelled_edges = sorted(
        visual_graph.edges(data=True),
        key=lambda item: edge_score(item[0], item[1], item[2]),
        reverse=True,
    )[:26]
    edge_labels = {}
    for source, target, data in labelled_edges:
        relation = str(data.get("relations", "RELATED_TO")).split("|")[0]
        if len(relation) > 34:
            relation = relation[:33].rstrip() + "..."
        edge_labels[(source, target)] = relation

    nx.draw_networkx_edge_labels(
        visual_graph,
        pos,
        edge_labels=edge_labels,
        font_size=7,
        font_family="DejaVu Sans",
        font_color="#EF4E45",
        rotate=True,
        bbox={"boxstyle": "round,pad=0.1", "fc": "white", "ec": "none", "alpha": 0.72},
        ax=ax,
    )

    ax.set_title(
        f"Tech Company & EV Industry Knowledge Graph (Top {visual_graph.number_of_nodes()} Nodes)",
        fontsize=22,
        fontweight="bold",
        pad=28,
        color="#111111",
    )
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_dir / "knowledge_graph.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    nx.write_graphml(visual_graph, output_dir / "knowledge_graph.graphml")


class FlatRAG:
    def __init__(self, documents: list[Document]) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.chunks: list[dict[str, str]] = []
        for doc in documents:
            sentences = split_sentences(doc.text)
            if not sentences:
                continue
            for index in range(0, len(sentences), 4):
                chunk = " ".join(sentences[index : index + 4])
                if len(chunk) >= 80:
                    self.chunks.append(
                        {
                            "doc_id": doc.doc_id,
                            "title": doc.title,
                            "text": chunk,
                        }
                    )
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=2048)
        self.matrix = self.vectorizer.fit_transform([chunk["text"] for chunk in self.chunks])
        self.collection = None
        self.backend = "tfidf-cosine"
        try:
            import chromadb
        except ImportError:
            chromadb = None
        if chromadb is not None:
            self.backend = "chromadb-tfidf"
            client = chromadb.EphemeralClient()
            self.collection = client.get_or_create_collection("flat_rag_chunks")
            embeddings = self.matrix.astype("float32").toarray().tolist()
            ids = [f"chunk_{idx}" for idx in range(len(self.chunks))]
            self.collection.add(
                ids=ids,
                documents=[chunk["text"] for chunk in self.chunks],
                metadatas=[{"doc_id": chunk["doc_id"], "title": chunk["title"]} for chunk in self.chunks],
                embeddings=embeddings,
            )

    def query(self, question: str, top_k: int = 5) -> list[Evidence]:
        from sklearn.metrics.pairwise import cosine_similarity

        vector = self.vectorizer.transform([question])
        if self.collection is not None:
            result = self.collection.query(
                query_embeddings=vector.astype("float32").toarray().tolist(),
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
            evidence: list[Evidence] = []
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            for text, metadata, distance in zip(documents, metadatas, distances):
                score = 1.0 / (1.0 + float(distance))
                evidence.append(
                    Evidence(
                        source_id=str(metadata.get("doc_id", "")),
                        title=str(metadata.get("title", "")),
                        text=str(text),
                        score=score,
                    )
                )
            return evidence

        scores = cosine_similarity(vector, self.matrix).ravel()
        order = scores.argsort()[::-1][:top_k]
        evidence: list[Evidence] = []
        for idx in order:
            chunk = self.chunks[int(idx)]
            evidence.append(Evidence(chunk["doc_id"], chunk["title"], chunk["text"], float(scores[int(idx)])))
        return evidence


GENERIC_GRAPH_NODES = {
    "EV",
    "EVs",
    "EV sales",
    "EV adoption",
    "electric vehicle",
    "electric vehicles",
    "Market share",
    "market",
    "growth",
    "China",
    "Chinese",
    "United States",
    "U.S.",
    "US",
    "USA",
    "Europe",
}


class GraphRAG:
    def __init__(self, graph: nx.MultiDiGraph, matcher: EntityMatcher, documents: list[Document] | None = None) -> None:
        self.graph = graph
        self.matcher = matcher
        self.undirected = graph_to_simple(graph, include_documents=True)
        self.documents = {doc.doc_id: doc for doc in documents or []}
        self.chunk_index: list[dict[str, str]] = []
        self.chunk_vectorizer: Any | None = None
        self.chunk_matrix: Any | None = None
        self._build_chunk_index(list(documents or []))

    def query(self, question: str, max_hops: int = 2, top_k: int = 10) -> tuple[list[str], list[Evidence], list[dict[str, object]]]:
        seeds = [entity for entity in self.matcher.find(question) if self.graph.has_node(entity)]
        if not seeds:
            seeds = self._fallback_seed_nodes(question)
        primary_seeds = self._primary_seeds(seeds)
        if primary_seeds and all(self.graph.nodes[seed].get("type") == "Region" for seed in primary_seeds):
            for seed in self._fallback_seed_nodes(question, limit=4):
                if seed not in primary_seeds:
                    primary_seeds.append(seed)

        frontier: set[str] = set()
        distances: dict[str, int] = {}
        for seed in primary_seeds:
            if seed in self.undirected:
                lengths = nx.single_source_shortest_path_length(self.undirected, seed, cutoff=max_hops)
                frontier.update(lengths.keys())
                for node, distance in lengths.items():
                    distances[node] = min(distances.get(node, max_hops + 1), distance)

        if not frontier:
            return seeds, [], []

        terms = set(content_terms(question))
        markers = query_markers(question)
        rows: list[dict[str, object]] = []
        evidence: list[Evidence] = []
        seen_sentences: set[str] = set()
        selected_source_ids: Counter[str] = Counter()

        for source, target, key, data in self.graph.edges(keys=True, data=True):
            if source not in frontier or target not in frontier:
                continue
            source_distance = distances.get(source, max_hops + 1)
            target_distance = distances.get(target, max_hops + 1)
            min_distance = min(source_distance, target_distance)
            relation = str(data.get("relation", key))
            if relation == "MENTIONED_IN":
                continue
            if min_distance > 1 and source not in primary_seeds and target not in primary_seeds:
                continue
            sentence_blob = str(data.get("evidence", ""))
            row_text = f"{source} {relation} {target} {sentence_blob}"
            overlap = len(terms.intersection(content_terms(row_text)))
            marker_bonus = 1.6 * marker_overlap_score(markers, row_text)
            if overlap == 0 and relation == "CO_OCCURS_WITH" and source not in primary_seeds and target not in primary_seeds:
                continue
            relation_bonus = 1.8 if relation not in {"CO_OCCURS_WITH", "RELATED_TO"} else 0.35
            seed_bonus = 5.0 if source in primary_seeds or target in primary_seeds else 0.0
            path_bonus = max(0.0, 2.4 - 0.8 * min_distance)
            weight_bonus = min(2.0, 0.08 * float(data.get("weight", 1.0)))
            generic_penalty = 1.2 * sum(1 for node in (source, target) if self._is_generic_node(node) and node not in primary_seeds)
            score = seed_bonus + path_bonus + relation_bonus + weight_bonus + 1.45 * overlap + marker_bonus - generic_penalty
            rows.append(
                {
                    "source": source,
                    "relation": relation,
                    "target": target,
                    "score": score,
                    "sources": data.get("sources", ""),
                    "evidence": sentence_blob,
                }
            )
            for source_id in str(data.get("sources", "")).split("|"):
                if source_id in self.documents:
                    selected_source_ids[source_id] += max(1, int(round(score)))
            for sentence in sentence_blob.split(" || "):
                sentence = sentence.strip()
                if len(sentence) < 35 or sentence in seen_sentences:
                    continue
                seen_sentences.add(sentence)
                evidence.append(
                    Evidence(
                        source_id=str(data.get("sources", "")).split("|")[0],
                        title=str(data.get("title", "")),
                        text=f"Graph fact: {source} -[{relation}]-> {target}. Supporting extraction: {sentence}",
                        score=score + 0.6 * len(terms.intersection(content_terms(sentence))),
                    )
                )

        doc_relevance = self._doc_relevance_scores(question)
        for row in rows:
            row_doc_scores = [
                doc_relevance.get(source_id, 0.0)
                for source_id in str(row.get("sources", "")).split("|")
            ]
            if row_doc_scores:
                row["score"] = float(row["score"]) + max(row_doc_scores)

        rows.sort(key=lambda row: float(row["score"]), reverse=True)
        evidence.extend(self._graph_guided_chunk_evidence(question, rows[: max(30, top_k)], selected_source_ids, seen_sentences))
        evidence.sort(key=lambda item: item.score, reverse=True)
        return primary_seeds or seeds, evidence[:top_k], rows[:top_k]

    def _build_chunk_index(self, documents: list[Document]) -> None:
        if not documents:
            return
        for doc in documents:
            sentences = split_sentences(doc.text)
            if not sentences:
                continue
            for index in range(0, len(sentences), 3):
                chunk = " ".join(sentences[index : index + 5])
                if len(chunk) >= 100:
                    self.chunk_index.append(
                        {
                            "doc_id": doc.doc_id,
                            "title": doc.title,
                            "text": chunk,
                        }
                    )
        if not self.chunk_index:
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self.chunk_vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=4096)
            self.chunk_matrix = self.chunk_vectorizer.fit_transform([chunk["text"] for chunk in self.chunk_index])
        except Exception:
            self.chunk_vectorizer = None
            self.chunk_matrix = None

    def _doc_relevance_scores(self, question: str) -> dict[str, float]:
        if not self.chunk_index or self.chunk_vectorizer is None or self.chunk_matrix is None:
            return {}
        from sklearn.metrics.pairwise import cosine_similarity

        question_terms = set(content_terms(question))
        markers = query_markers(question)
        query_vector = self.chunk_vectorizer.transform([question])
        similarities = cosine_similarity(query_vector, self.chunk_matrix).ravel()
        scores: dict[str, float] = {}
        for index, chunk in enumerate(self.chunk_index):
            similarity = float(similarities[index])
            if similarity <= 0:
                continue
            overlap = len(question_terms.intersection(content_terms(chunk["text"])))
            marker_bonus = 1.4 * marker_overlap_score(markers, chunk["text"])
            score = min(10.0, 18.0 * similarity + 0.7 * overlap + marker_bonus)
            doc_id = chunk["doc_id"]
            scores[doc_id] = max(scores.get(doc_id, 0.0), score)
        return scores

    def _graph_guided_chunk_evidence(
        self,
        question: str,
        graph_rows: list[dict[str, object]],
        source_votes: Counter[str],
        seen_sentences: set[str],
        max_items: int = 8,
    ) -> list[Evidence]:
        if not self.chunk_index:
            return []

        from sklearn.metrics.pairwise import cosine_similarity

        candidate_doc_ids: set[str] = set(source_votes)
        for row in graph_rows:
            for source_id in str(row.get("sources", "")).split("|"):
                if source_id in self.documents:
                    candidate_doc_ids.add(source_id)

        graph_terms: set[str] = set()
        for row in graph_rows:
            graph_terms.update(content_terms(f"{row['source']} {row['relation']} {row['target']} {row.get('evidence', '')}"))
        question_terms = set(content_terms(question))
        markers = query_markers(question)

        if self.chunk_vectorizer is not None and self.chunk_matrix is not None:
            query_vector = self.chunk_vectorizer.transform([question])
            similarities = cosine_similarity(query_vector, self.chunk_matrix).ravel()
        else:
            similarities = [0.0 for _ in self.chunk_index]

        scored: list[tuple[float, Evidence]] = []
        for index, chunk in enumerate(self.chunk_index):
            doc_id = chunk["doc_id"]
            if candidate_doc_ids and doc_id not in candidate_doc_ids:
                continue
            text = chunk["text"]
            normalized = re.sub(r"\W+", " ", text.lower()).strip()
            if normalized in seen_sentences:
                continue
            chunk_terms = set(content_terms(text))
            question_overlap = len(question_terms.intersection(chunk_terms))
            graph_overlap = len(graph_terms.intersection(chunk_terms))
            marker_bonus = 2.2 * marker_overlap_score(markers, text)
            if float(similarities[index]) <= 0.0 and question_overlap == 0 and graph_overlap < 2:
                continue
            graph_source_boost = 2.2 if doc_id in source_votes else 0.0
            vote_boost = min(2.0, 0.05 * source_votes.get(doc_id, 0))
            score = (
                20.0 * float(similarities[index])
                + 1.25 * question_overlap
                + 0.25 * graph_overlap
                + marker_bonus
                + graph_source_boost
                + vote_boost
            )
            scored.append(
                (
                    score,
                    Evidence(
                        source_id=doc_id,
                        title=chunk["title"],
                        text=f"Graph-guided supporting chunk: {text}",
                        score=score,
                    ),
                )
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        selected: list[Evidence] = []
        for _score, item in scored:
            normalized = re.sub(r"\W+", " ", item.text.lower()).strip()
            if normalized in seen_sentences:
                continue
            seen_sentences.add(normalized)
            selected.append(item)
            if len(selected) >= max_items:
                break
        return selected

    def _primary_seeds(self, seeds: list[str]) -> list[str]:
        if not seeds:
            return seeds
        specific = [
            seed
            for seed in seeds
            if self.graph.nodes[seed].get("type") not in {"Region"}
            and seed not in {"EV sales", "EV adoption", "Market share"}
        ]
        if specific:
            return specific
        non_region = [seed for seed in seeds if self.graph.nodes[seed].get("type") != "Region"]
        return non_region or seeds

    def _fallback_seed_nodes(self, question: str, limit: int = 2) -> list[str]:
        terms = set(content_terms(question))
        scored: list[tuple[float, str]] = []
        for node, data in self.graph.nodes(data=True):
            if data.get("type") == "Document":
                continue
            label = str(data.get("label", node))
            overlap = len(terms.intersection(content_terms(label)))
            if overlap:
                generic_penalty = 0.75 if self._is_generic_node(node) else 0.0
                degree_penalty = min(1.25, self.graph.degree(node) * 0.006)
                scored.append((overlap - generic_penalty - degree_penalty, node))
        scored.sort(reverse=True)
        return [node for _, node in scored[:limit]]

    def _is_generic_node(self, node: str) -> bool:
        label = str(self.graph.nodes[node].get("label", node)) if self.graph.has_node(node) else node
        return label in GENERIC_GRAPH_NODES or label.lower() in {item.lower() for item in GENERIC_GRAPH_NODES}

    def _supporting_text_evidence(
        self,
        question: str,
        graph_rows: list[dict[str, object]],
        source_votes: Counter[str],
        seen_sentences: set[str],
        max_items: int = 8,
    ) -> list[Evidence]:
        if not self.documents:
            return []

        terms = set(content_terms(question))
        graph_terms: set[str] = set()
        for row in graph_rows:
            graph_terms.update(content_terms(f"{row['source']} {row['relation']} {row['target']} {row.get('evidence', '')}"))

        candidate_doc_ids: set[str] = set(source_votes)
        for row in graph_rows:
            for source_id in str(row.get("sources", "")).split("|"):
                if source_id in self.documents:
                    candidate_doc_ids.add(source_id)

        scored_sentences: list[tuple[float, Evidence]] = []
        for doc_id in candidate_doc_ids:
            doc = self.documents.get(doc_id)
            if doc is None:
                continue
            doc_vote = source_votes.get(doc_id, 1)
            for sentence in split_sentences(doc.text):
                sentence = sentence.strip()
                if len(sentence) < 45:
                    continue
                normalized = re.sub(r"\W+", " ", sentence.lower()).strip()
                if normalized in seen_sentences:
                    continue
                sentence_terms = set(content_terms(sentence))
                question_overlap = len(terms.intersection(sentence_terms))
                graph_overlap = len(graph_terms.intersection(sentence_terms))
                if question_overlap == 0 and graph_overlap < 2:
                    continue
                score = 2.0 + 1.7 * question_overlap + 0.45 * graph_overlap + min(2.0, 0.08 * doc_vote)
                scored_sentences.append(
                    (
                        score,
                        Evidence(
                            source_id=doc.doc_id,
                            title=doc.title,
                            text=f"Supporting text: {sentence}",
                            score=score,
                        ),
                    )
                )

        scored_sentences.sort(key=lambda item: item[0], reverse=True)
        selected: list[Evidence] = []
        for _score, item in scored_sentences:
            normalized = re.sub(r"\W+", " ", item.text.lower()).strip()
            if normalized in seen_sentences:
                continue
            seen_sentences.add(normalized)
            selected.append(item)
            if len(selected) >= max_items:
                break
        return selected


def synthesize_answer(question: str, evidence: list[Evidence], max_sentences: int = 5) -> str:
    if not evidence:
        return "No strong evidence found in the indexed corpus."

    terms = set(content_terms(question))
    sentence_scores: list[tuple[float, Evidence, str]] = []
    for item in evidence:
        for sentence in split_sentences(item.text):
            overlap = len(terms.intersection(content_terms(sentence)))
            score = item.score + overlap * 1.3
            sentence_scores.append((score, item, sentence))

    if not sentence_scores:
        sentence_scores = [(item.score, item, item.text[:650]) for item in evidence]

    selected: list[tuple[Evidence, str]] = []
    seen: set[str] = set()
    for _score, item, sentence in sorted(sentence_scores, key=lambda row: row[0], reverse=True):
        normalized = re.sub(r"\W+", " ", sentence.lower()).strip()
        if normalized in seen:
            continue
        seen.add(normalized)
        sentence = re.sub(
            r"^(Graph fact:|Supporting text:|Supporting extraction:|Graph-guided supporting chunk:)\s*",
            "",
            sentence,
        ).strip()
        sentence = sentence.replace(" Supporting extraction:", "").replace(" Supporting text:", "")
        selected.append((item, sentence))
        if len(selected) >= max_sentences:
            break

    answer_parts = [sentence for _, sentence in selected]
    citations = []
    for item, _sentence in selected:
        citation = f"{item.source_id}"
        if citation and citation not in citations:
            citations.append(citation)
    return " ".join(answer_parts) + (f" Sources: {', '.join(citations)}." if citations else "")


def textualize_evidence(evidence: list[Evidence], max_items: int = 8) -> str:
    lines = []
    for index, item in enumerate(evidence[:max_items], start=1):
        text = re.sub(r"\s+", " ", item.text).strip()
        lines.append(f"[{index}] source={item.source_id}; title={item.title}; evidence={text}")
    return "\n".join(lines)


def llm_answer(question: str, evidence: list[Evidence], llm: LLMClient, system_name: str) -> str:
    if not evidence:
        return "Không tìm thấy đủ bằng chứng trong corpus đã index."
    system = (
        "You answer questions for a RAG evaluation. Use only the provided evidence. "
        "If evidence is insufficient, say so clearly. Return JSON only."
    )
    user = f"""
System being evaluated: {system_name}
Question: {question}

Evidence:
{textualize_evidence(evidence)}

Return JSON:
{{
  "answer": "concise Vietnamese answer with source IDs in parentheses"
}}
""".strip()
    data = llm.json_chat(system, user)
    answer = clean_text(str(data.get("answer", "")))
    return answer or "Không tìm thấy đủ bằng chứng trong corpus đã index."


def llm_judge(
    question: str,
    flat_answer: str,
    graph_answer: str,
    flat_evidence: list[Evidence],
    graph_evidence: list[Evidence],
    llm: LLMClient,
) -> dict[str, Any]:
    system = (
        "You are a strict evaluator for a GraphRAG lab. Return JSON only. "
        "Judge factual correctness, use of supplied evidence, multi-hop reasoning, and hallucination risk."
    )
    user = f"""
Question:
{question}

Flat RAG answer:
{flat_answer}

Flat RAG evidence:
{textualize_evidence(flat_evidence, max_items=5)}

GraphRAG answer:
{graph_answer}

GraphRAG evidence:
{textualize_evidence(graph_evidence, max_items=8)}

Return JSON with this exact shape:
{{
  "flat_score": 0,
  "graphrag_score": 0,
  "winner": "FlatRAG|GraphRAG|Tie",
  "flat_hallucination": false,
  "graphrag_hallucination": false,
  "reason": "short Vietnamese explanation"
}}

Scores are integers from 0 to 10.
""".strip()
    data = llm.json_chat(system, user, model=llm.config.judge_model)
    def score_value(name: str) -> int:
        try:
            value = int(float(data.get(name, 0)))
        except (TypeError, ValueError):
            value = 0
        return max(0, min(10, value))

    return {
        "flat_score": score_value("flat_score"),
        "graphrag_score": score_value("graphrag_score"),
        "winner": str(data.get("winner", "Tie")),
        "flat_hallucination": bool(data.get("flat_hallucination", False)),
        "graphrag_hallucination": bool(data.get("graphrag_hallucination", False)),
        "reason": clean_text(str(data.get("reason", ""))),
    }


def score_answer(question: str, answer: str) -> float:
    terms = set(content_terms(question))
    answer_terms = set(content_terms(answer))
    if not terms:
        return 0.0
    coverage = len(terms.intersection(answer_terms)) / len(terms)
    evidence_bonus = 0.25 if "Sources:" in answer else 0.0
    weak_penalty = 0.45 if "No strong evidence" in answer else 0.0
    return max(0.0, coverage + evidence_bonus - weak_penalty)


def compare_systems(flat_answer: str, graph_answer: str, flat_score: float, graph_score: float) -> str:
    if "No strong evidence" in graph_answer and "No strong evidence" in flat_answer:
        return "Both systems lack enough evidence"
    if graph_score >= flat_score + 0.18:
        if flat_score < 0.42:
            return "GraphRAG better; Flat RAG weak or off-context"
        return "GraphRAG better supported"
    if flat_score >= graph_score + 0.18:
        return "Flat RAG better for this wording"
    return "Comparable"


def run_benchmark(
    documents: list[Document],
    graph: nx.MultiDiGraph,
    matcher: EntityMatcher,
    output_dir: Path,
    llm: LLMClient | None = None,
):
    import pandas as pd

    log("Preparing Flat RAG vector store")
    flat = FlatRAG(documents)
    log(f"Flat RAG backend ready: {flat.backend}, chunks={len(flat.chunks)}")
    graph_rag = GraphRAG(graph, matcher, documents)

    rows = []
    for question_index, question in enumerate(BENCHMARK_QUESTIONS, start=1):
        log(f"Benchmark [{question_index}/{len(BENCHMARK_QUESTIONS)}]: retrieving evidence")
        flat_evidence = flat.query(question)
        seeds, graph_evidence, graph_edges = graph_rag.query(question)
        if llm is not None:
            log(f"Benchmark [{question_index}/{len(BENCHMARK_QUESTIONS)}]: answering + judging with LLM")
            flat_answer = llm_answer(question, flat_evidence, llm, "Flat RAG")
            graph_answer = llm_answer(question, graph_evidence, llm, "GraphRAG")
            judgment = llm_judge(question, flat_answer, graph_answer, flat_evidence, graph_evidence, llm)
            flat_score = judgment["flat_score"]
            graph_score = judgment["graphrag_score"]
            verdict = f"{judgment['winner']}: {judgment['reason']}"
            flat_hallucination = judgment["flat_hallucination"]
            graph_hallucination = judgment["graphrag_hallucination"]
        else:
            flat_answer = synthesize_answer(question, flat_evidence)
            graph_answer = synthesize_answer(question, graph_evidence)
            flat_score = score_answer(question, flat_answer)
            graph_score = score_answer(question, graph_answer)
            verdict = compare_systems(flat_answer, graph_answer, flat_score, graph_score)
            flat_hallucination = False
            graph_hallucination = False
        log(
            f"Benchmark [{question_index}/{len(BENCHMARK_QUESTIONS)}] done: "
            f"flat={round(flat_score, 3)}, graph={round(graph_score, 3)}, verdict={verdict}"
        )
        rows.append(
            {
                "question": question,
                "query_entities": ", ".join(seeds),
                "flat_backend": flat.backend,
                "flat_answer": flat_answer,
                "graphrag_answer": graph_answer,
                "flat_score": round(flat_score, 3),
                "graphrag_score": round(graph_score, 3),
                "flat_hallucination": flat_hallucination,
                "graphrag_hallucination": graph_hallucination,
                "verdict": verdict,
                "top_graph_edges": " | ".join(
                    f"{edge['source']} -[{edge['relation']}]-> {edge['target']}" for edge in graph_edges[:4]
                ),
            }
        )

    dataframe = pd.DataFrame(rows)
    dataframe.to_csv(output_dir / "benchmark_results.csv", index=False, encoding="utf-8")
    return dataframe


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Lab Day 19 GraphRAG pipeline with LLM triple extraction and LLM judging.")
    parser.add_argument("--dataset", type=Path, default=DATASET_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--mode", choices=["llm", "offline"], default="llm", help="Default uses LLM extraction and LLM judge.")
    parser.add_argument("--refresh-cache", action="store_true", help="Ignore cached LLM triples and re-extract from the corpus.")
    parser.add_argument("--no-plot", action="store_true", help="Skip PNG/GraphML visualization.")
    parser.add_argument("--redraw-graph", action="store_true", help="Only redraw outputs/knowledge_graph.png and GraphML from outputs/triples.csv, then exit.")
    parser.add_argument("--ask", type=str, default="", help="Ask one GraphRAG query from existing outputs/triples.csv and exit.")
    parser.add_argument("--ask-after-build", action="store_true", help="Run the full pipeline first, then ask the query.")
    parser.add_argument("--ask-use-llm", action="store_true", help="Use the configured LLM to write the ad-hoc answer.")
    args = parser.parse_args()

    started = time.perf_counter()
    args.output.mkdir(parents=True, exist_ok=True)

    if args.redraw_graph:
        log("Redraw-graph mode: loading existing triples.csv")
        graph = load_graph_from_triples(args.output / "triples.csv")
        log("Drawing semantic-core knowledge graph image")
        draw_graph(graph, args.output)
        log(f"Graph visualization written to: {args.output / 'knowledge_graph.png'}")
        return

    if args.ask and not args.ask_after_build:
        log("Ask-only mode: loading existing graph from outputs/triples.csv")
        matcher = EntityMatcher(ENTITY_DEFINITIONS)
        graph = load_graph_from_triples(args.output / "triples.csv")
        documents = load_documents(args.dataset)
        seeds, evidence, edges = GraphRAG(graph, matcher, documents).query(args.ask)
        llm = None
        if args.ask_use_llm:
            try:
                config = load_llm_config(required=True)
            except RuntimeError as exc:
                parser.error(str(exc))
            if config is None:
                raise RuntimeError("LLM config is required with --ask-use-llm.")
            llm = LLMClient(config)
        answer = llm_answer(args.ask, evidence, llm, "GraphRAG") if llm is not None else synthesize_answer(args.ask, evidence)
        print("\nAd-hoc GraphRAG query")
        print(f"Question: {args.ask}")
        print(f"Query entities: {', '.join(seeds) if seeds else 'none'}")
        print(f"Answer: {answer}")
        print("Top graph edges:")
        for edge in edges[:5]:
            print(f"- {edge['source']} -[{edge['relation']}]-> {edge['target']}")
        if llm is not None:
            log(f"LLM calls: {llm.calls}")
            log(f"Estimated LLM tokens: {llm.estimated_tokens}")
        log("Ask-only query done; pipeline was not rebuilt.")
        return

    log("Loading documents")
    matcher = EntityMatcher(ENTITY_DEFINITIONS)
    documents = load_documents(args.dataset)
    log(f"Loaded documents: {len(documents)}")
    llm: LLMClient | None = None
    runtime_estimate: dict[str, float] | None = None
    if args.mode == "llm":
        try:
            config = load_llm_config(required=True)
        except RuntimeError as exc:
            parser.error(str(exc))
        if config is None:
            raise RuntimeError("LLM config is required in llm mode.")
        log(f"Using LLM mode: model={config.model}, judge_model={config.judge_model}, base_url={config.base_url or 'default'}")
        runtime_estimate = estimate_llm_work(
            documents,
            config,
            args.output,
            force_refresh=args.refresh_cache,
            benchmark_questions=len(BENCHMARK_QUESTIONS),
        )
        log(
            "Runtime estimate: "
            f"chunks={int(runtime_estimate['total_chunks'])}, "
            f"cached={int(runtime_estimate['cached_chunks'])}, "
            f"to_extract={int(runtime_estimate['uncached_chunks'])}, "
            f"benchmark_llm_calls={int(runtime_estimate['benchmark_calls'])}, "
            f"total_llm_calls={int(runtime_estimate['total_llm_calls'])}, "
            f"~{format_duration(runtime_estimate['estimated_seconds'])} "
            f"at {runtime_estimate['seconds_per_call']:.1f}s/call"
        )
        llm = LLMClient(config)
        triples = extract_llm_triples(documents, llm, args.output, force_refresh=args.refresh_cache)
        log("Building NetworkX graph from LLM triples")
        graph = build_graph_from_llm_triples(triples)
    else:
        log("Using offline smoke-test mode: rule-based triples")
        log("Building NetworkX graph from offline rules")
        graph = build_graph(documents, matcher)

    log("Writing triples.csv")
    write_triples(graph, args.output)
    if not args.no_plot:
        log("Drawing knowledge graph image")
        draw_graph(graph, args.output)
    log("Running benchmark")
    benchmark = run_benchmark(documents, graph, matcher, args.output, llm=llm)
    elapsed = time.perf_counter() - started
    run_metadata = {
        "mode": args.mode,
        "documents": len(documents),
        "skipped_noisy_documents": [doc.doc_id for doc in documents if doc.skipped_content],
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "benchmark_questions": len(benchmark),
        "runtime_seconds": round(elapsed, 3),
        "llm_calls": llm.calls if llm is not None else 0,
        "estimated_llm_tokens": llm.estimated_tokens if llm is not None else 0,
        "model": llm.config.model if llm is not None else None,
        "judge_model": llm.config.judge_model if llm is not None else None,
        "flat_backend": str(benchmark["flat_backend"].iloc[0]) if not benchmark.empty and "flat_backend" in benchmark else None,
        "runtime_estimate": runtime_estimate,
    }
    (args.output / "run_metadata.json").write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    log("Pipeline artifacts written. Run generate_report.py to create REPORT_DAY_19.md")

    if args.ask and args.ask_after_build:
        seeds, evidence, edges = GraphRAG(graph, matcher, documents).query(args.ask)
        answer = llm_answer(args.ask, evidence, llm, "GraphRAG") if llm is not None else synthesize_answer(args.ask, evidence)
        print("\nAd-hoc GraphRAG query")
        print(f"Question: {args.ask}")
        print(f"Query entities: {', '.join(seeds) if seeds else 'none'}")
        print(f"Answer: {answer}")
        print("Top graph edges:")
        for edge in edges[:5]:
            print(f"- {edge['source']} -[{edge['relation']}]-> {edge['target']}")

    log(f"Mode: {args.mode}")
    log(f"Loaded documents: {len(documents)}")
    log(f"Graph nodes: {graph.number_of_nodes()}")
    log(f"Graph edges/triples: {graph.number_of_edges()}")
    log(f"Benchmark questions: {len(benchmark)}")
    if llm is not None:
        log(f"LLM calls: {llm.calls}")
        log(f"Estimated LLM tokens: {llm.estimated_tokens}")
    log(f"Outputs written to: {args.output}")
    log(f"Runtime seconds: {elapsed:.2f}")


if __name__ == "__main__":
    main()
