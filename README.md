# Lab Day 19: GraphRAG System

This repository implements Lab Day 19: building a GraphRAG pipeline from a raw text corpus and comparing it with a Flat RAG baseline.

The corpus is stored in `dataset/`, and the generated evaluation artifacts are stored in `outputs/`.

## Features

- Extracts entity-relation triples from raw text with an OpenAI-compatible LLM.
- Builds a NetworkX knowledge graph from extracted triples.
- Creates a Flat RAG baseline with ChromaDB, with a TF-IDF fallback.
- Implements GraphRAG retrieval by linking questions to graph entities, traversing related graph facts, and retrieving supporting source chunks.
- Runs the same benchmark questions through Flat RAG and GraphRAG.
- Uses an LLM judge to compare answer quality, grounding, and hallucination risk.

## Repository Structure

```text
.
|-- dataset/                         # Raw text corpus
|-- outputs/                         # Generated triples, graph, benchmark, and metadata
|-- graphrag_lab.py                  # Main GraphRAG pipeline
|-- LAB DAY 19.md                    # Original lab instruction
|-- requirements-lab-day19.txt       # Python dependencies
|-- .env_example                     # Environment variable template
`-- README.md
```

## Requirements

- Python 3.10 or newer
- An OpenAI-compatible chat completions API key

Install dependencies:

```powershell
python -m pip install -r requirements-lab-day19.txt
```

## Configuration

Copy `.env_example` to `.env`:

```powershell
Copy-Item .env_example .env
```

Fill in the required values:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_JUDGE_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0
GRAPHRAG_CHUNK_CHARS=6000
GRAPHRAG_MAX_CHUNKS_PER_DOC=3
GRAPHRAG_EST_SECONDS_PER_LLM_CALL=10
```

## Run the Pipeline

Run the full GraphRAG experiment:

```powershell
python graphrag_lab.py
```

The script will:

1. Load documents from `dataset/`.
2. Extract LLM triples from the corpus.
3. Build a NetworkX knowledge graph.
4. Build the Flat RAG retrieval index.
5. Run the Flat RAG vs GraphRAG benchmark.
6. Judge both systems with an LLM.
7. Write all artifacts to `outputs/`.

## Main Outputs

| File | Description |
| --- | --- |
| `outputs/triples.csv` | Extracted knowledge graph triples |
| `outputs/knowledge_graph.png` | Top-node knowledge graph visualization |
| `outputs/knowledge_graph.graphml` | GraphML export for graph inspection |
| `outputs/benchmark_results.csv` | Flat RAG vs GraphRAG benchmark results |
| `outputs/run_metadata.json` | Runtime metadata and pipeline statistics |

## Optional Commands

Ask a single GraphRAG question from existing artifacts:

```powershell
python graphrag_lab.py --ask "What is VinFast's relationship with Vingroup and Pham Nhat Vuong?"
```

Use the configured LLM to write the ad-hoc answer:

```powershell
python graphrag_lab.py --ask "What is VinFast's relationship with Vingroup and Pham Nhat Vuong?" --ask-use-llm
```

Redraw the graph visualization from existing triples:

```powershell
python graphrag_lab.py --redraw-graph
```

Run a local smoke test without an API key:

```powershell
python graphrag_lab.py --mode offline
```

The offline mode is intended only for code validation. The official lab result should be produced with `--mode llm`, which is the default mode.

## Method Summary

Flat RAG retrieves relevant chunks directly from the text corpus. GraphRAG first maps the question to graph entities, retrieves multi-hop graph facts, then uses those graph signals to select supporting source text. Both systems answer the same benchmark questions and are evaluated by an LLM judge using the same criteria.

The final comparison is available in `outputs/benchmark_results.csv`.
