# Lab Day 19 - GraphRAG với Tech Company Corpus

## Mục tiêu

Repo này triển khai đúng luồng bài Lab Day 19:

1. Dùng LLM đọc corpus và trích xuất triples.
2. Xây dựng knowledge graph bằng NetworkX.
3. Query GraphRAG bằng duyệt graph 2-hop rồi textualize evidence cho LLM trả lời.
4. So sánh với Flat RAG dùng ChromaDB vector store.
5. Dùng LLM-as-judge để chấm câu trả lời và ghi nhận hallucination.

## Cài đặt

```powershell
python -m pip install -r requirements-lab-day19.txt
```

## Cấu hình API

Copy `.env_example` thành `.env`, sau đó điền key/base URL thật:

```powershell
Copy-Item .env_example .env
```

Các biến quan trọng:

- `OPENAI_API_KEY`: API key của bạn.
- `OPENAI_BASE_URL`: base URL của provider OpenAI-compatible.
- `OPENAI_MODEL`: model dùng để extract triples và sinh câu trả lời.
- `OPENAI_JUDGE_MODEL`: model dùng để judge Flat RAG vs GraphRAG.
- `GRAPHRAG_CHUNK_CHARS`: số ký tự mỗi chunk khi gửi cho LLM.
- `GRAPHRAG_MAX_CHUNKS_PER_DOC`: số chunk tối đa mỗi document.

## Chạy pipeline đúng yêu cầu lab

```powershell
python graphrag_lab.py
```

`graphrag_lab.py` chỉ chạy pipeline và benchmark. Script sẽ sinh các artifact kỹ thuật trong `outputs/`:

- `triples.csv`: triples đã extract.
- `knowledge_graph.png`: ảnh đồ thị tri thức.
- `knowledge_graph.graphml`: graph để mở bằng công cụ ngoài.
- `benchmark_results.csv`: bảng so sánh 20 câu hỏi.
- `run_metadata.json`: metadata của lần chạy.
- `llm_triples_cache.jsonl`: cache triples để lần chạy sau đỡ tốn token.

## Sinh report

Sau khi pipeline chạy xong, tạo báo cáo bằng file riêng:

```powershell
python generate_report.py
```

File này sẽ đọc các artifact trong `outputs/` và ghi:

- `outputs/REPORT_DAY_19.md`: báo cáo cuối.

## Smoke test không cần API key

Chỉ dùng để kiểm tra code chạy được, không phải kết quả nộp chính:

```powershell
python graphrag_lab.py --mode offline
python generate_report.py
```

## Query thử một câu

```powershell
python graphrag_lab.py --ask "What is VinFast's relationship with Vingroup and Pham Nhat Vuong?"
```

## Ghi chú chi phí

Lần chạy LLM đầu tiên tốn token nhiều nhất vì phải extract triples. Các lần sau dùng cache trong `outputs/llm_triples_cache.jsonl`. Nếu muốn giảm chi phí, giảm `GRAPHRAG_MAX_CHUNKS_PER_DOC` hoặc `GRAPHRAG_CHUNK_CHARS` trong `.env`.
