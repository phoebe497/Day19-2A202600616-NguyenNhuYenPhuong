from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_metadata(output_dir: Path) -> dict[str, object]:
    path = output_dir / "run_metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def bool_text(value: object) -> str:
    return "Có" if str(value).lower() == "true" else "Không"


def build_report(output_dir: Path) -> str:
    metadata = read_metadata(output_dir)
    triples = read_csv(output_dir / "triples.csv")
    benchmark = read_csv(output_dir / "benchmark_results.csv")
    relation_counts = Counter(row.get("relation", "") for row in triples if row.get("relation"))
    top_relations = relation_counts.most_common(12)

    mode = str(metadata.get("mode", "unknown"))
    if mode == "llm":
        run_note = "Report này được sinh từ pipeline LLM extraction, LLM answering và LLM-as-judge."
        model_line = (
            f"Model extract/answer: `{metadata.get('model')}`; "
            f"model judge: `{metadata.get('judge_model')}`."
        )
    else:
        run_note = (
            "Lưu ý: report hiện tại được sinh từ chế độ `offline` để kiểm tra kỹ thuật. "
            "Để có kết quả nộp đúng yêu cầu lab, hãy điền `.env` và chạy `python graphrag_lab.py`."
        )
        model_line = "Chế độ offline rule-based, chỉ dùng để smoke test khi chưa có API key."

    skipped = metadata.get("skipped_noisy_documents", [])
    skipped_text = ", ".join(skipped) if isinstance(skipped, list) and skipped else "none"

    report = f"""# Lab Day 19 - Xây dựng hệ thống GraphRAG với Tech Company Corpus

> {run_note}

## 1. Nghiên cứu ngắn

**Entity Extraction.** LLM phân biệt node và thuộc tính bằng schema. Node là đối tượng có thể liên kết độc lập như công ty, cá nhân, chính sách, khu vực; thuộc tính là giá trị mô tả node như tỷ lệ %, doanh thu, năm, số xe giao. Trong pipeline chính, LLM đọc từng chunk của corpus và trả về triples JSON gồm `source`, `relation`, `target`, type, evidence và confidence.

**Graph Construction và Deduplication.** Nếu không khử trùng lặp, một thực thể có thể bị tách thành nhiều node, ví dụ `Tesla`, `TSLA`, `Tesla Motors`. Pipeline chuẩn hóa relation, gộp edge trùng theo cặp `source-relation-target`, cộng dồn weight/confidence và lưu evidence theo document.

**Query Answering.** Flat RAG dùng ChromaDB để tìm chunk gần nhất bằng vector search. GraphRAG tìm entity chính trong câu hỏi, đi qua graph trong phạm vi 2-hop, textualize evidence rồi gửi evidence đó cho LLM sinh câu trả lời. Điểm khác biệt là Flat RAG tìm đoạn văn tương tự, còn GraphRAG đi theo quan hệ có cấu trúc.

## 2. Môi trường và công cụ

- Graph store: NetworkX.
- Flat RAG baseline: ChromaDB vector store với embedding TF-IDF local.
- LLM extraction/answer/judge: OpenAI-compatible Chat Completions API, cấu hình qua `.env`.
- {model_line}

## 3. Pipeline đã thực hiện

1. Đọc các file trong `dataset/`.
2. Lọc nội dung PDF/binary bị hỏng nhưng vẫn giữ metadata title/snippet.
3. Chia tài liệu thành chunk theo `GRAPHRAG_CHUNK_CHARS` và `GRAPHRAG_MAX_CHUNKS_PER_DOC`.
4. Dùng LLM để trích xuất triples từ từng chunk, có cache tại `outputs/llm_triples_cache.jsonl`.
5. Xây dựng knowledge graph bằng NetworkX.
6. Query GraphRAG bằng entity extraction, graph traversal 2-hop, textualization và LLM answer.
7. Query Flat RAG bằng ChromaDB retrieval và LLM answer.
8. Dùng LLM-as-judge để chấm hai hệ thống.

## 4. Kết quả indexing

- Documents loaded: {metadata.get("documents", "N/A")}
- Documents skipped noisy full content: {skipped_text}
- Graph nodes: {metadata.get("graph_nodes", "N/A")}
- Graph edges/triples: {metadata.get("graph_edges", len(triples))}
- Runtime: {metadata.get("runtime_seconds", "N/A")} seconds
- Mode: `{mode}`
- Flat RAG backend: `{metadata.get("flat_backend", "N/A")}`
- LLM calls: {metadata.get("llm_calls", 0)}
- Estimated LLM tokens: {metadata.get("estimated_llm_tokens", 0)}

Top relation counts:

| Relation | Count |
|---|---:|
"""

    for relation, count in top_relations:
        report += f"| {relation} | {count} |\n"

    report += """
## 5. Benchmark Flat RAG vs GraphRAG

Bảng đầy đủ nằm tại `outputs/benchmark_results.csv`. Tóm tắt:

| # | Question | Flat score | GraphRAG score | Flat hallucination | Graph hallucination | Verdict |
|---:|---|---:|---:|---|---|---|
"""

    for index, row in enumerate(benchmark, start=1):
        question = row.get("question", "").replace("|", "\\|")
        verdict = row.get("verdict", "").replace("|", "/")
        report += (
            f"| {index} | {question} | {row.get('flat_score', '')} | {row.get('graphrag_score', '')} | "
            f"{bool_text(row.get('flat_hallucination'))} | {bool_text(row.get('graphrag_hallucination'))} | {verdict} |\n"
        )

    report += """
## 6. Trường hợp Flat RAG yếu hoặc hallucinate

Các dòng dưới đây dựa trên verdict và cờ hallucination trong bảng benchmark.

| Question | GraphRAG evidence edge |
|---|---|
"""

    failures = [
        row
        for row in benchmark
        if str(row.get("flat_hallucination", "")).lower() == "true"
        or "GraphRAG" in row.get("verdict", "")
    ]
    if not failures:
        report += "| None | Không có trường hợp Flat RAG hallucinate rõ ràng trong lần chạy này. |\n"
    else:
        for row in failures[:10]:
            question = row.get("question", "").replace("|", "\\|")
            edges = row.get("top_graph_edges", "").replace("|", "<br>")
            report += f"| {question} | {edges} |\n"

    report += """
## 7. Deliverables

- Source code pipeline: `graphrag_lab.py`
- Report generator: `generate_report.py`
- Environment template: `.env_example`
- Knowledge graph image: `outputs/knowledge_graph.png`
- GraphML file: `outputs/knowledge_graph.graphml`
- Triples: `outputs/triples.csv`
- Benchmark table: `outputs/benchmark_results.csv`
- Run metadata: `outputs/run_metadata.json`
- LLM extraction cache: `outputs/llm_triples_cache.jsonl`

## 8. Cách chạy

Chạy pipeline:

```powershell
python graphrag_lab.py
```

Sinh report sau khi pipeline xong:

```powershell
python generate_report.py
```

Smoke test không cần API key:

```powershell
python graphrag_lab.py --mode offline
python generate_report.py
```

## 9. Phân tích chi phí

Chi phí phụ thuộc vào số chunk gửi cho LLM. Script có cache nên lần chạy sau sẽ tái sử dụng triples đã extract. Nếu muốn giảm chi phí, giảm `GRAPHRAG_MAX_CHUNKS_PER_DOC` hoặc `GRAPHRAG_CHUNK_CHARS`; nếu muốn tăng độ phủ corpus, tăng hai giá trị đó.
"""
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Lab Day 19 report from pipeline artifacts.")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    report = build_report(args.output)
    report_path = args.output / "REPORT_DAY_19.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()

