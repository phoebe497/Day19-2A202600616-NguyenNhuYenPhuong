# Lab Day 19 - Xây dựng hệ thống GraphRAG với Tech Company Corpus

> Lưu ý: report hiện tại được sinh từ chế độ `offline` để kiểm tra kỹ thuật. Để có kết quả nộp đúng yêu cầu lab, hãy điền `.env` và chạy `python graphrag_lab.py`.

## 1. Nghiên cứu ngắn

**Entity Extraction.** LLM phân biệt node và thuộc tính bằng schema. Node là đối tượng có thể liên kết độc lập như công ty, cá nhân, chính sách, khu vực; thuộc tính là giá trị mô tả node như tỷ lệ %, doanh thu, năm, số xe giao. Trong pipeline chính, LLM đọc từng chunk của corpus và trả về triples JSON gồm `source`, `relation`, `target`, type, evidence và confidence.

**Graph Construction và Deduplication.** Nếu không khử trùng lặp, một thực thể có thể bị tách thành nhiều node, ví dụ `Tesla`, `TSLA`, `Tesla Motors`. Pipeline chuẩn hóa relation, gộp edge trùng theo cặp `source-relation-target`, cộng dồn weight/confidence và lưu evidence theo document.

**Query Answering.** Flat RAG dùng ChromaDB để tìm chunk gần nhất bằng vector search. GraphRAG tìm entity chính trong câu hỏi, đi qua graph trong phạm vi 2-hop, textualize evidence rồi gửi evidence đó cho LLM sinh câu trả lời. Điểm khác biệt là Flat RAG tìm đoạn văn tương tự, còn GraphRAG đi theo quan hệ có cấu trúc.

## 2. Môi trường và công cụ

- Graph store: NetworkX.
- Flat RAG baseline: ChromaDB vector store với embedding TF-IDF local.
- LLM extraction/answer/judge: OpenAI-compatible Chat Completions API, cấu hình qua `.env`.
- Chế độ offline rule-based, chỉ dùng để smoke test khi chưa có API key.

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

- Documents loaded: 70
- Documents skipped noisy full content: doc_50, doc_60
- Graph nodes: 238
- Graph edges/triples: 1094
- Runtime: 23.563 seconds
- Mode: `offline`
- Flat RAG backend: `chromadb-tfidf`
- LLM calls: 0
- Estimated LLM tokens: 0

Top relation counts:

| Relation | Count |
|---|---:|
| MENTIONED_IN | 645 |
| CO_OCCURS_WITH | 316 |
| SALES_INCREASED | 40 |
| RELATED_TO | 19 |
| HAS_MARKET_SHARE | 18 |
| DELIVERED | 18 |
| HAS_FUNDING | 13 |
| REPORTED_REVENUE | 8 |
| SALES_DECLINED | 8 |
| SURPASSED | 1 |
| COLLABORATES_WITH | 1 |
| FUNDS | 1 |

## 5. Benchmark Flat RAG vs GraphRAG

Bảng đầy đủ nằm tại `outputs/benchmark_results.csv`. Tóm tắt:

| # | Question | Flat score | GraphRAG score | Flat hallucination | Graph hallucination | Verdict |
|---:|---|---:|---:|---|---|---|
| 1 | Why did Tesla's Q1 2024 U.S. EV market share fall, and which brands grew more than 50% year over year? | 0.75 | 0.75 | Không | Không | Comparable |
| 2 | What Q3 2024 delivery and revenue results did VinFast report, and who backed its funding? | 0.75 | 0.75 | Không | Không | Comparable |
| 3 | How are ZEV regulations linked to U.S. EV sales share and model availability? | 1.107 | 0.964 | Không | Không | Comparable |
| 4 | How does public and workplace charging availability relate to EV uptake in top U.S. metropolitan areas? | 1.028 | 0.917 | Không | Không | Comparable |
| 5 | What consumer charging concerns could slow EV adoption according to the corpus? | 0.964 | 0.679 | Không | Không | Flat RAG better for this wording |
| 6 | Which company surpassed Tesla as the largest EV producer, and where are Chinese EV brands expanding? | 1.125 | 1.125 | Không | Không | Comparable |
| 7 | How does the Inflation Reduction Act connect to EV leasing incentives or battery investment? | 0.806 | 0.917 | Không | Không | Comparable |
| 8 | How did Cadillac, Mercedes, BMW, Audi, and Ford perform in Q1 2024 EV sales relative to Tesla? | 0.85 | 0.75 | Không | Không | Comparable |
| 9 | What is VinFast's relationship with Vingroup and Pham Nhat Vuong? | 1.083 | 0.583 | Không | Không | Flat RAG better for this wording |
| 10 | What are the main barriers to EV adoption mentioned across Deloitte, EPA, and McKinsey style sources? | 0.583 | 0.472 | Không | Không | Comparable |
| 11 | Why is Germany's EV charging infrastructure investment significant for consumer sentiment? | 1.107 | 0.964 | Không | Không | Comparable |
| 12 | How did Polestar describe its strategic partners and major EV business risks? | 0.679 | 0.821 | Không | Không | Comparable |
| 13 | What first-quarter 2024 themes were reported for Zeekr? | 0.5 | 0.5 | Không | Không | Comparable |
| 14 | What did Nikola report in first-quarter 2023 results? | 0.65 | 0.65 | Không | Không | Comparable |
| 15 | What investment level did U.S. EV investments reach, and what does that imply for the sector? | 0.875 | 0.5 | Không | Không | Flat RAG better for this wording |
| 16 | How are Chinese battery companies investing in Europe and the United States? | 1.25 | 1.107 | Không | Không | Comparable |
| 17 | What does the EPA say about battery manufacturing emissions versus lifetime EV emissions? | 0.625 | 0.375 | Không | Không | Flat RAG better for this wording |
| 18 | How does the Bipartisan Infrastructure Law address EV charging concerns? | 0.964 | 0.964 | Không | Không | Comparable |
| 19 | What does Goldman Sachs say about why EV sales are slowing? | 0.583 | 0.417 | Không | Không | Comparable |
| 20 | How do dealer sentiment reports describe uncertainty in the EV and auto market? | 1.083 | 1.083 | Không | Không | Comparable |

## 6. Trường hợp Flat RAG yếu hoặc hallucinate

Các dòng dưới đây dựa trên verdict và cờ hallucination trong bảng benchmark.

| Question | GraphRAG evidence edge |
|---|---|
| None | Không có trường hợp Flat RAG hallucinate rõ ràng trong lần chạy này. |

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
