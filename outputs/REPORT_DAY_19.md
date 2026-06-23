# Lab Day 19 - Xây dựng hệ thống GraphRAG với Tech Company Corpus

> Report này được sinh từ pipeline LLM extraction, LLM answering và LLM-as-judge.

## 1. Nghiên cứu ngắn

**Entity Extraction.** LLM phân biệt node và thuộc tính bằng schema. Node là đối tượng có thể liên kết độc lập như công ty, cá nhân, chính sách, khu vực; thuộc tính là giá trị mô tả node như tỷ lệ %, doanh thu, năm, số xe giao. Trong pipeline chính, LLM đọc từng chunk của corpus và trả về triples JSON gồm `source`, `relation`, `target`, type, evidence và confidence.

**Graph Construction và Deduplication.** Nếu không khử trùng lặp, một thực thể có thể bị tách thành nhiều node, ví dụ `Tesla`, `TSLA`, `Tesla Motors`. Pipeline chuẩn hóa relation, gộp edge trùng theo cặp `source-relation-target`, cộng dồn weight/confidence và lưu evidence theo document.

**Query Answering.** Flat RAG dùng ChromaDB để tìm chunk gần nhất bằng vector search. GraphRAG tìm entity chính trong câu hỏi, đi qua graph trong phạm vi 2-hop, textualize evidence rồi gửi evidence đó cho LLM sinh câu trả lời. Điểm khác biệt là Flat RAG tìm đoạn văn tương tự, còn GraphRAG đi theo quan hệ có cấu trúc.

## 2. Môi trường và công cụ

- Graph store: NetworkX.
- Flat RAG baseline: ChromaDB vector store với embedding TF-IDF local.
- LLM extraction/answer/judge: OpenAI-compatible Chat Completions API, cấu hình qua `.env`.
- Model extract/answer: `gpt-4o-mini`; model judge: `gpt-4o-mini`.

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
- Graph nodes: 3228
- Graph edges/triples: 6294
- Runtime: 465.003 seconds
- Mode: `llm`
- Flat RAG backend: `chromadb-tfidf`
- LLM calls: 60
- Estimated LLM tokens: 63433
- Estimated LLM calls trước khi chạy: 60 (extract mới 0 chunks, benchmark 60 calls), ước tính khoảng 10.0 phút.

Top relation counts:

| Relation | Count |
|---|---:|
| MENTIONED_IN | 3714 |
| BARRIER_TO_ADOPTION | 45 |
| HAS_MARKET_SHARE | 40 |
| SUPPORTED_BY_POLICY | 40 |
| CAUSED_BY | 33 |
| SUPPORTS | 26 |
| FOCUSES_ON | 20 |
| SUPPORTED_BY | 20 |
| CAUSES | 18 |
| DRIVEN_BY | 16 |
| EXPANDS_TO | 15 |
| LISTED_ON | 14 |

## 5. Benchmark Flat RAG vs GraphRAG

Bảng đầy đủ nằm tại `outputs/benchmark_results.csv`. Tóm tắt:

| # | Question | Flat score | GraphRAG score | Flat hallucination | Graph hallucination | Verdict |
|---:|---|---:|---:|---|---|---|
| 1 | Why did Tesla's Q1 2024 U.S. EV market share fall, and which brands grew more than 50% year over year? | 8 | 3 | Không | Có | FlatRAG: Flat RAG trả lời đúng cả hai ý chính từ bằng chứng: Tesla giảm thị phần do doanh số Mỹ giảm 13,3% và liệt kê đúng 9 hãng tăng hơn 50% YoY. GraphRAG chỉ nêu đúng con số thị phần nhưng lại nói không đủ bằng chứng dù nguồn doc_2 đã nêu rõ nguyên nhân và danh sách các hãng, nên có dấu hiệu bỏ sót bằng chứng và trả lời không đầy đủ. |
| 2 | What Q3 2024 delivery and revenue results did VinFast report, and who backed its funding? | 2 | 9 | Có | Không | GraphRAG: GraphRAG trả lời đúng số liệu Q3/2024: VinFast giao 21.912 xe và doanh thu 12.326.537 triệu VND (511,6 triệu USD). Nó chỉ bỏ sót phần nguồn vốn được hậu thuẫn bởi Phạm Nhật Vượng/các công ty liên quan và Vingroup, nhưng không bịa. Flat RAG lại nói không có số liệu giao xe/doanh thu dù bằng chứng có, nên thiếu chính xác và có nguy cơ bỏ sót nghiêm trọng. |
| 3 | How are ZEV regulations linked to U.S. EV sales share and model availability? | 9 | 3 | Không | Có | FlatRAG: FlatRAG trả lời đúng và đầy đủ hơn: nêu rõ ZEV regulations liên quan đến thị phần EV mới 5% so với 1,3% ở bang không có ZEV, nhiều hơn ít nhất 13 mẫu EV, và chiếm khoảng 2/3 doanh số EV Mỹ năm 2020. GraphRAG chỉ nói chung chung về tầm quan trọng của sự sẵn có mẫu xe và thêm chi tiết về thiếu chip/doanh số EV tăng, nhưng chi tiết này không trả lời trực tiếp câu hỏi và làm loãng trọng tâm; phần về EV tăng mạnh bất chấp thiếu chip không được dùng để chứng minh liên kết ZEV. |
| 4 | How does public and workplace charging availability relate to EV uptake in top U.S. metropolitan areas? | 8 | 2 | Không | Có | FlatRAG: Flat RAG trả lời đúng trọng tâm: sạc công cộng và sạc nơi làm việc nhiều hơn đi kèm mức chấp nhận EV cao hơn ở các vùng đô thị lớn, và nêu đúng các số liệu từ bằng chứng. GraphRAG bỏ lỡ bằng chứng trực tiếp về mối liên hệ này và thay vào đó chỉ nói chung chung về chi phí đầu tư hạ tầng, nên có nguy cơ bịa/diễn giải sai do thiếu dẫn chứng. |
| 5 | What consumer charging concerns could slow EV adoption according to the corpus? | 8 | 7 | Không | Không | FlatRAG: FlatRAG bám sát corpus hơn vì nêu đúng các lo ngại về sạc: thiếu hạ tầng, khó sạc thuận tiện như đổ xăng, lo ngại khi đi xa, và vấn đề tiêu chuẩn/tương thích mạng sạc. GraphRAG đúng ý chính nhưng bỏ sót các điểm quan trọng trong evidence về sự tiện lợi và long trips. |
| 6 | Which company surpassed Tesla as the largest EV producer, and where are Chinese EV brands expanding? | 8 | 5 | Không | Có | FlatRAG: FlatRAG trả lời đúng ý chính: BYD vượt Tesla và các thương hiệu EV Trung Quốc đang mở rộng sang các thị trường mới nổi ở Đông Nam Á, nhất là Thái Lan, đúng với bằng chứng. GraphRAG đúng phần BYD vượt Tesla nhưng phần nơi mở rộng lại quá chung chung, không nêu được Đông Nam Á/thị trường mới nổi như evidence, nên kém chính xác hơn và có dấu hiệu suy diễn. |
| 7 | How does the Inflation Reduction Act connect to EV leasing incentives or battery investment? | 7 | 8 | Không | Không | GraphRAG: GraphRAG trả lời sát câu hỏi hơn vì nêu rõ ưu đãi leasing $7.500 và liên hệ với đầu tư pin/EV; FlatRAG đúng về phần đầu tư nhưng bỏ sót điểm leasing. Cả hai đều dựa trên bằng chứng cung cấp, nhưng GraphRAG bao quát đầy đủ hơn. |
| 8 | How did Cadillac, Mercedes, BMW, Audi, and Ford perform in Q1 2024 EV sales relative to Tesla? | 8 | 5 | Không | Có | FlatRAG: FlatRAG trả lời đúng phần lớn số liệu từ bằng chứng: Cadillac +499,2%, Ford +86,1%, Mercedes +66,9%, BMW +62,6%, Audi +28,8% và Tesla -13,3%, kèm thị phần 51,3%. GraphRAG đúng về Cadillac/Ford/Tesla nhưng bỏ sót Mercedes, BMW, Audi dù câu hỏi yêu cầu so sánh cả năm hãng; thêm nữa phần nói không có bằng chứng cho ba hãng này là sai vì doc_2 đã nêu rõ số liệu. |
| 9 | What is VinFast's relationship with Vingroup and Pham Nhat Vuong? | 8 | 6 | Không | Có | FlatRAG: Flat RAG bám sát bằng chứng hơn: nêu đúng VinFast là công ty con của Vingroup và có hỗ trợ tài chính từ Phạm Nhật Vượng/các công ty liên quan. GraphRAG sai khi nói ông Vượng là ‘nhà sáng lập kiêm CEO của VinFast’; bằng chứng chỉ cho thấy ông là Founder and Chief Executive Officer của một ngữ cảnh trong báo cáo, nhưng không đủ để khẳng định đó là CEO của VinFast. Ngoài ra, chi tiết khoản vay 35 nghìn tỷ VND chỉ là một phần của hỗ trợ, nên câu trả lời GraphRAG vừa lệch vừa hẹp hơn. |
| 10 | What are the main barriers to EV adoption mentioned across Deloitte, EPA, and McKinsey style sources? | 7 | 6 | Không | Có | FlatRAG: Flat RAG bám sát hơn các nguồn được đưa: chi phí/khả năng chi trả, hạ tầng sạc, lo ngại phạm vi di chuyển và khác biệt chính sách đều có trong evidence. GraphRAG có vài ý đúng nhưng thêm các điểm như chia rẽ chính trị, mất cân đối nhu cầu vùng và ‘monthly payment gap’ không được hỏi trực tiếp theo kiểu Deloitte/EPA/McKinsey, nên rủi ro hallucination cao hơn. |
| 11 | Why is Germany's EV charging infrastructure investment significant for consumer sentiment? | 9 | 2 | Không | Không | FlatRAG: FlatRAG bám sát bằng chứng: Đức đầu tư 2,8 tỷ USD và bắt buộc trạm xăng có điểm sạc, điều này quan trọng vì trực tiếp giảm hai rào cản lớn nhất của người tiêu dùng là lo ngại quãng đường và thiếu hạ tầng sạc, nên tác động tích cực đến tâm lý người dùng. GraphRAG quá dè dặt và bỏ sót bằng chứng nêu rõ liên hệ với consumer sentiment. |
| 12 | How did Polestar describe its strategic partners and major EV business risks? | 9 | 5 | Không | Không | FlatRAG: FlatRAG bám sát câu hỏi hơn: mô tả đúng đối tác chiến lược chính là Volvo Cars và Geely trong mô hình asset-light, và tổng hợp đầy đủ các rủi ro vận hành/sản xuất EV từ bằng chứng. GraphRAG có dùng chứng cứ thật nhưng lệch trọng tâm: thêm Xingji Meizu, servicing/software/charging và rủi ro chấp nhận EV thị trường, trong khi bỏ sót các rủi ro lớn được nêu rõ như chậm ramp-up, thiếu công suất, sai dự báo nhu cầu, giảm giá cạnh tranh và lead time linh kiện. |
| 13 | What first-quarter 2024 themes were reported for Zeekr? | 8 | 2 | Không | Không | FlatRAG: FlatRAG bám sát bằng chứng doc_14 về khởi đầu mạnh sau IPO, hiệu quả vận hành/tài chính và ra mắt ZEEKR 001 2024; có thêm ý về định vị BEV cao cấp cũng phù hợp phần giới thiệu công ty. Tuy nhiên câu trả lời hơi diễn giải rộng thành “chủ đề”. GraphRAG quá bảo thủ, dựa vào bằng chứng không đúng tài liệu tài chính quý 1 và bỏ sót các ý nêu rõ trong doc_14. |
| 14 | What did Nikola report in first-quarter 2023 results? | 8 | 6 | Không | Không | FlatRAG: Cả hai đều trả lời rằng không đủ bằng chứng, phù hợp với tư liệu. FlatRAG bám sát việc các nguồn không chứa thông tin về Nikola/Q1 2023 nên dùng chứng cứ an toàn hơn. GraphRAG cũng không bịa nhưng suy ra từ một nguồn chỉ nói định giá Nikola, nên kém liên quan hơn. |
| 15 | What investment level did U.S. EV investments reach, and what does that imply for the sector? | 3 | 2 | Không | Có | FlatRAG: Cả hai câu trả lời đều không tìm ra mức đầu tư EV của Mỹ nên không trả lời đúng trọng tâm. FlatRAG bám sát bằng chứng hơn khi thừa nhận thiếu dữ liệu cụ thể, dù suy luận còn yếu vì dẫn chứng rất nhiễu. GraphRAG cũng nói thiếu dữ liệu nhưng lại suy diễn sang mở rộng sản xuất pin và số xe EV sản xuất, những chi tiết không trả lời câu hỏi về mức đầu tư và hàm ý cho ngành, nên rủi ro suy diễn/hallucination cao hơn. |
| 16 | How are Chinese battery companies investing in Europe and the United States? | 10 | 1 | Không | Có | FlatRAG: FlatRAG trả lời đúng và bám sát chứng cứ: đầu tư mạnh ở châu u (CATL có nhà máy ở Đức, xây ở Hungary, thúc đẩy greenfield 2022) và ở Mỹ sau IRA (CATL-Ford, Gotion Michigan). GraphRAG nói thiếu bằng chứng dù bộ chứng cứ chuẩn có nêu rất rõ, lại chèn chi tiết không có trong evidence được đưa như BEV Mỹ +26%, châu u -1% và LG/SK mở rộng, nên sai và có rủi ro bịa. |
| 17 | What does the EPA say about battery manufacturing emissions versus lifetime EV emissions? | 9 | 1 | Không | Không | FlatRAG: FlatRAG bám đúng bằng chứng EPA ở doc_8: phát thải sản xuất EV/pin thường cao hơn, nhưng phát thải trọn vòng đời của EV vẫn thấp hơn xe xăng; cũng nêu đúng các yếu tố phụ thuộc. GraphRAG sai vì bỏ qua bằng chứng EPA liên quan trực tiếp và kết luận không đủ thông tin dù evidence FlatRAG đã đủ. |
| 18 | How does the Bipartisan Infrastructure Law address EV charging concerns? | 8 | 6 | Không | Không | FlatRAG: FlatRAG bám sát bằng chứng hơn: nêu đúng khoản 7,5 tỷ USD để mở rộng mạng sạc toàn quốc và liên hệ trực tiếp tới lo ngại về tiện lợi sạc/đi đường dài. GraphRAG cũng dựa trên chứng cứ thật nhưng thêm chi tiết Build a Better Grid và 13 tỷ USD cho lưới điện, phần này ít trực tiếp trả lời câu hỏi về lo ngại sạc EV nên suy luận kém tập trung hơn. |
| 19 | What does Goldman Sachs say about why EV sales are slowing? | 8 | 7 | Không | Không | FlatRAG: Cả hai câu trả lời đều đúng khi nói không có bằng chứng về nhận định của Goldman Sachs. FlatRAG bám sát chứng cứ hơn vì chỉ ra rõ dữ liệu liên quan là mức quan tâm mua EV giảm và lo ngại hạ tầng sạc từ Pew. GraphRAG cũng tránh bịa đặt nhưng diễn giải thêm về ưu đãi thuế và kỳ vọng doanh số tương lai, hơi xa câu hỏi gốc. |
| 20 | How do dealer sentiment reports describe uncertainty in the EV and auto market? | 9 | 4 | Không | Có | FlatRAG: FlatRAG bám sát chứng cứ CADSI Q2/Q3: thị trường yếu, bất định thị trường/kinh tế/chính trị, EV chỉ nhích nhẹ nhưng vẫn thấp. GraphRAG chỉ dùng được 1 ý trực tiếp về dealer sentiment; các dẫn chứng còn lại là vĩ mô chung hoặc xu hướng EV không nói về báo cáo sentiment của đại lý, nên suy luận lỏng và có nguy cơ gán ghép. |

## 6. Trường hợp Flat RAG yếu hoặc hallucinate

Các dòng dưới đây dựa trên verdict và cờ hallucination trong bảng benchmark.

| Question | GraphRAG evidence edge |
|---|---|
| Why did Tesla's Q1 2024 U.S. EV market share fall, and which brands grew more than 50% year over year? | Tesla -[HAS_MARKET_SHARE]-> 65% of US EV purchases in 2022 <br> Tesla -[HAS_MARKET_SHARE]-> 51.3% of US EV market in Q1 2024 <br> BYD -[COMPETES_WITH]-> Tesla <br> Tesla -[HAS_MARKET_SHARE]-> 55% of US EV purchases in 2023 |
| What Q3 2024 delivery and revenue results did VinFast report, and who backed its funding? | VinFast -[REPORTED_REVENUE]-> US$511.6 million in Q3 2024 <br> VinFast -[TARGETS_ANNUAL_DELIVERIES]-> 80,000 vehicles in 2024 <br> VinFast -[ACHIEVED_YOY_DELIVERY_GROWTH]-> 115% year-over-year in Q3 2024 <br> VinFast -[ACHIEVED_YOY_REVENUE_GROWTH]-> 49.3% year-over-year in Q3 2024 |
| How are ZEV regulations linked to U.S. EV sales share and model availability? | ZEV regulations -[ESSENTIAL_TO]-> EV market growth <br> EV market growth -[IMPACTED_BY]-> chip shortage |
| How does public and workplace charging availability relate to EV uptake in top U.S. metropolitan areas? | Charging infrastructure -[REQUIRES_INVESTMENT]-> Multi-billion-dollar capital investments <br> Charging infrastructure implementation -[REQUIRES]-> Multi-billion-dollar capital investments |
| What consumer charging concerns could slow EV adoption according to the corpus? | EV adoption -[BARRIER_TO_ADOPTION]-> limited driving range <br> EV adoption -[BARRIER_TO_ADOPTION]-> lack of charging infrastructure <br> EV adoption -[BARRIER_TO_ADOPTION]-> high purchase cost <br> EV adoption -[BARRIER_TO_ADOPTION]-> availability of public charging stations |
| Which company surpassed Tesla as the largest EV producer, and where are Chinese EV brands expanding? | BYD -[SURPASSED]-> Tesla <br> BYD -[COMPETES_WITH]-> Tesla <br> Tesla -[WAS_LARGEST_EXPORTER_FROM]-> China <br> Elon Musk -[CEO_OF]-> Tesla |
| How does the Inflation Reduction Act connect to EV leasing incentives or battery investment? | Inflation Reduction Act -[SUPPORTED_INVESTMENT_IN]-> battery factories <br> Inflation Reduction Act -[OFFERS_INCENTIVE]-> $7,500 EV incentive <br> Inflation Reduction Act -[OFFERS_EV_BATTERY_TAX_CREDIT]-> US$7,500 <br> Inflation Reduction Act -[BOOSTED_EXPECTED_SOLAR_DEPLOYMENT]-> 46% compared to pre-IRA projections |
| How did Cadillac, Mercedes, BMW, Audi, and Ford perform in Q1 2024 EV sales relative to Tesla? | Ford -[COMPETES_WITH]-> Tesla <br> Ford -[RANKED_BY_EV_SALES_VOLUME]-> second-highest behind Tesla in Q1 2024 <br> Tesla -[INCREASED_Q3_EV_SALES_BY]-> 40%–60% from Q3 2022 to Q3 2023 <br> BMW -[INCREASED_Q3_EV_SALES_BY]-> 40%–60% from Q3 2022 to Q3 2023 |
| What is VinFast's relationship with Vingroup and Pham Nhat Vuong? | Pham Nhat Vuong -[FOUNDER_OF]-> VinFast <br> Vingroup -[PROVIDES_LOANS_TO]-> VinFast subsidiaries in Vietnam up to VND35 trillion through end of 2026 <br> VinFast -[RELIES_ON_SUPPORT_FROM]-> Vingroup <br> VinFast -[ASSOCIATED_WITH]-> Vingroup affiliates |
| What are the main barriers to EV adoption mentioned across Deloitte, EPA, and McKinsey style sources? | EPA emissions targets -[AIMED_AT_BOOSTING]-> EV adoption <br> EV adoption -[BARRIER_TO_ADOPTION]-> cost <br> EV adoption -[BARRIER_TO_ADOPTION]-> limited driving range <br> EV adoption -[BARRIER_TO_ADOPTION]-> lack of charging infrastructure |

## 7. Deliverables

- Source code pipeline: `graphrag_lab.py`
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
