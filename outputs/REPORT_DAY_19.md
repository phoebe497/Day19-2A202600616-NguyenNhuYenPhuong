# Lab Day 19 - Xây dựng hệ thống GraphRAG với Tech Company Corpus

> Report này được sinh từ pipeline LLM extraction, LLM answering và LLM-as-judge.

## 1. Nghiên cứu ngắn

**Entity & Relation Extraction.** LLM đọc từng chunk của corpus và trích xuất triples JSON gồm `source`, `relation`, `target`, entity type, evidence và confidence. Triples là lớp cấu trúc giúp chuyển văn bản tự do thành knowledge graph có thể truy vấn theo quan hệ.

**Graph Construction và Deduplication.** Nếu không khử trùng lặp, một thực thể có thể bị tách thành nhiều node, ví dụ `Tesla`, `TSLA`, `Tesla Motors`. Pipeline chuẩn hóa relation, gộp edge trùng theo cặp `source-relation-target`, cộng dồn weight/confidence và lưu source document cho mỗi edge.

**Indexing.** Flat RAG chia tài liệu thành chunks và tạo vector index bằng ChromaDB nếu có, fallback sang TF-IDF cosine nếu môi trường chưa cài ChromaDB.

**GraphRAG Query Answering.** GraphRAG link câu hỏi vào graph entities, duyệt subgraph 2-hop, xếp hạng graph facts, sau đó dùng các source documents mà graph chạm tới để rerank chunks gốc theo câu hỏi. LLM chỉ được trả lời dựa trên graph facts và graph-guided supporting chunks này.

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
6. Query GraphRAG bằng entity linking, graph traversal 2-hop, graph fact ranking và graph-guided chunk reranking.
7. Query Flat RAG bằng vector retrieval.
8. Dùng LLM-as-judge để chấm hai hệ thống theo factuality, evidence use và hallucination risk.

## 4. Kết quả indexing

- Documents loaded: 70
- Documents skipped noisy full content: doc_50, doc_60
- Graph nodes: 3208
- Graph edges/triples: 6287
- Runtime: 986.053 seconds
- Mode: `llm`
- Flat RAG backend: `chromadb-tfidf`
- LLM calls: 60
- Estimated LLM tokens: 138210
- Estimated LLM calls trước khi chạy: 60 (extract mới 0 chunks, benchmark 60 calls), ước tính khoảng 10.0 phút.

Top relation counts:

| Relation | Count |
|---|---:|
| MENTIONED_IN | 3709 |
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

Bảng đầy đủ nằm tại `outputs/benchmark_results.csv`.

- FlatRAG wins: 7
- GraphRAG wins: 10
- GraphRAG hallucination flags: 4

| # | Question | Flat score | GraphRAG score | Flat hallucination | Graph hallucination | Verdict |
|---:|---|---:|---:|---|---|---|
| 1 | Why did Tesla's Q1 2024 U.S. EV market share fall, and which brands grew more than 50% year over year? | 9 | 9 | Không | Không | Tie: Cả hai câu trả lời đều đúng về факт chính: Tesla giảm doanh số 13,3%, thị phần giảm từ 61,7% xuống 51,3%, và 9 hãng tăng trên 50% YoY gồm BMW, Cadillac, Ford, Hyundai, Kia, Lexus, Mercedes, Rivian, VinFast. FlatRAG bám sát chứng cứ hơn và đủ để trả lời câu hỏi. GraphRAG cũng đúng, dùng thêm bối cảnh thị trường chậm lại/quý giảm để nối lý do, nhưng phần này hơi mở rộng hơn nhu cầu câu hỏi. Không thấy bịa đặt ở cả hai. |
| 2 | What Q3 2024 delivery and revenue results did VinFast report, and who backed its funding? | 3 | 9 | Không | Không | GraphRAG: GraphRAG trả lời đúng đủ hai ý: Q3/2024 VinFast giao 21.912 xe, doanh thu 511,6 triệu USD, và nêu đúng nguồn hậu thuẫn từ nhà sáng lập/Phạm Nhật Vượng và Vingroup. FlatRAG dùng đúng chứng cứ về tài trợ nhưng bỏ sót số liệu giao xe và doanh thu dù có trong tài liệu, nên độ đầy đủ và suy luận kém hơn. |
| 3 | How are ZEV regulations linked to U.S. EV sales share and model availability? | 10 | 10 | Không | Không | Tie: Cả hai câu trả lời đều bám sát bằng chứng doc_1: bang có ZEV đạt 5% thị phần EV mới so với 1,3% ở bang không có ZEV, có nhiều hơn khoảng 13 mẫu EV, và đóng góp khoảng 2/3 doanh số EV Mỹ năm 2020 dù dưới 1/3 doanh số xe hạng nhẹ. Lập luận đúng và không thấy bịa đặt; GraphRAG chỉ dư dẫn chứng không liên quan nhưng không làm sai nội dung. |
| 4 | How does public and workplace charging availability relate to EV uptake in top U.S. metropolitan areas? | 8 | 9 | Không | Không | GraphRAG: Cả hai câu trả lời đều đúng về mặt факt và bám sát bằng chứng cốt lõi từ doc_1: thị phần EV 10%, 935 sạc công cộng/một triệu dân, 430 sạc nơi làm việc/một triệu dân, và chênh lệch lớn với phần còn lại của dân số Mỹ. Tuy nhiên, GraphRAG chặt chẽ hơn vì chỉ dùng các mệnh đề được hỗ trợ trực tiếp để kết luận quan hệ giữa hạ tầng sạc công cộng/nơi làm việc và mức tiếp nhận EV. FlatRAG cũng đúng nhưng thêm chi tiết về việc bộ sạc Level 2/3 tập trung ở MSA để củng cố lập luận, đây là bằng chứng liên quan nhưng gián tiếp hơn với câu hỏi so với bộ số liệu chính. |
| 5 | What consumer charging concerns could slow EV adoption according to the corpus? | 8 | 9 | Không | Không | GraphRAG: Cả hai câu trả lời đều bám bằng chứng. FlatRAG đúng về thiếu hạ tầng, bất tiện khi sạc, nhu cầu chuẩn hóa/tương thích và yếu tố kinh tế của hệ sạc, nhưng có một ý như “đủ nhanh” chỉ được hỗ trợ gián tiếp. GraphRAG đầy đủ hơn vì nêu rõ hạ tầng không theo kịp nhu cầu, sạc kém tiện hơn đổ xăng, lo ngại hết pin/range anxiety, và xu hướng người mua trì hoãn chuyển sang EV; các ý này được hỗ trợ trực tiếp bởi doc_70 và doc_9/doc_69. Không thấy bịa đặt đáng kể ở cả hai. |
| 6 | Which company surpassed Tesla as the largest EV producer, and where are Chinese EV brands expanding? | 10 | 9 | Không | Không | FlatRAG: Cả hai câu trả lời đều đúng: BYD vượt Tesla, và các hãng EV Trung Quốc mở rộng sang thị trường mới nổi, đặc biệt Đông Nam Á như Thái Lan. FlatRAG bám sát đúng chứng cứ [1][2] và trả lời trực tiếp hơn. GraphRAG cũng đúng nhưng kèm thêm nhiều chứng cứ dư thừa, trong đó có đoạn về Tesla vẫn là top-selling brand toàn cầu năm 2023 nên làm tăng nhẹ rủi ro nhiễu, dù không thành hallucination. |
| 7 | How does the Inflation Reduction Act connect to EV leasing incentives or battery investment? | 7 | 6 | Không | Có | FlatRAG: FlatRAG bám sát bằng chứng: IRA gắn với hỗ trợ EV nói chung và thúc đẩy đầu tư pin/EV, đồng thời thừa nhận không có chi tiết rõ về ưu đãi thuê EV. GraphRAG nêu tốt phần đầu tư pin, nhưng thêm chi tiết về tín dụng thuế 7.500 USD và điều kiện mua/thuê xe không trả lời đúng trọng tâm leasing và vượt quá bằng chứng được cung cấp về leasing, nên rủi ro suy diễn/hallucination cao hơn. |
| 8 | How did Cadillac, Mercedes, BMW, Audi, and Ford perform in Q1 2024 EV sales relative to Tesla? | 10 | 10 | Không | Không | Tie: Cả hai câu trả lời đều đúng với bằng chứng: Tesla giảm 13,3% YoY, còn Cadillac (+499,2%), Ford (+86,1%), Mercedes (+66,9%), BMW (+62,6%) và Audi (+28,8%) đều tăng mạnh hơn. Cả hai cũng dùng đúng bằng chứng để so sánh tương đối với Tesla; suy luận đa bước là tối thiểu và chính xác. GraphRAG trích hơi thừa nguồn, nhưng không thêm nội dung sai hay bịa. |
| 9 | What is VinFast's relationship with Vingroup and Pham Nhat Vuong? | 9 | 10 | Không | Không | GraphRAG: Cả hai câu trả lời đều đúng và bám sát bằng chứng. FlatRAG trả lời đúng quan hệ cốt lõi: VinFast là công ty con của Vingroup và nhận tài trợ từ Phạm Nhật Vượng cùng các công ty liên quan. Tuy nhiên, GraphRAG đầy đủ hơn vì nêu thêm các quan hệ tài chính quan trọng với Vingroup: khoản vay tối đa 35 nghìn tỷ VND và chuyển đổi tối đa 80 nghìn tỷ VND khoản vay thành cổ phần ưu đãi tại VFTP, đồng thời vẫn xác nhận đúng vai trò nhà sáng lập/CEO của Phạm Nhật Vượng. Không thấy bịa đặt ở cả hai. |
| 10 | What are the main barriers to EV adoption mentioned across Deloitte, EPA, and McKinsey style sources? | 9 | 2 | Không | Có | FlatRAG: FlatRAG bám sát câu hỏi hơn, dùng đúng bằng chứng về giá/khả năng chi trả, hạ tầng sạc, bất định chính sách và giá nhiên liệu thấp từ các nguồn kiểu Deloitte/EY/Goldman. GraphRAG lệch trọng tâm: chủ yếu suy diễn từ trang EPA về “myths” môi trường và phạm vi, trong khi bằng chứng lại nhấn mạnh EV thường sạch hơn và đủ đáp ứng nhu cầu di chuyển; vì vậy có rủi ro diễn giải quá mức và bỏ sót rào cản chi phí/chính sách quan trọng. |
| 11 | Why is Germany's EV charging infrastructure investment significant for consumer sentiment? | 8 | 9 | Không | Không | GraphRAG: Cả hai câu trả lời đều đúng và bám sát bằng chứng: đầu tư của Đức quan trọng vì giảm lo ngại về quãng đường và thiếu điểm sạc, từ đó cải thiện tâm lý người tiêu dùng. GraphRAG nhỉnh hơn vì dùng bằng chứng trực tiếp hơn về consumer sentiment và nối tốt hơn từ hạ tầng sạc -> tăng niềm tin -> hỗ trợ doanh số EV. FlatRAG cũng đúng nhưng có phần khái quát hơn và dựa nhiều vào các đoạn trùng lặp. |
| 12 | How did Polestar describe its strategic partners and major EV business risks? | 9 | 8 | Không | Không | FlatRAG: Cả hai câu trả lời đều bám sát bằng chứng và tổng hợp đúng các rủi ro chính quanh mô hình asset-light, phụ thuộc Volvo Cars/Geely, năng lực sản xuất, chuỗi cung ứng, dự báo nhu cầu và áp lực giảm giá. FlatRAG nhỉnh hơn vì trả lời trực tiếp hơn đúng trọng tâm “đối tác chiến lược được mô tả thế nào” và “rủi ro EV lớn”, không thêm ý ngoài trọng tâm. GraphRAG cũng đúng và có suy luận đa bước tốt, nhưng đưa thêm rủi ro mẫu xe mới không được thị trường đón nhận; ý này có trong bằng chứng nhưng hơi lệch khỏi trọng tâm đối tác chiến lược/rủi ro vận hành EV chính nên kém gọn hơn. Không thấy bịa đặt rõ ràng ở cả hai. |
| 13 | What first-quarter 2024 themes were reported for Zeekr? | 7 | 9 | Không | Không | GraphRAG: GraphRAG đầy đủ và bám chứng cứ hơn: nêu rõ giao xe Q1, tăng trưởng doanh thu/lợi nhuận gộp, biên lợi nhuận xe, vị thế phân khúc >200.000 RMB và định hướng tiếp theo. FlatRAG đúng một phần nhưng bỏ sót nhiều ý quan trọng và thêm chi tiết IPO/ra mắt công ty đại chúng như một chủ đề Q1 dù xảy ra vào tháng 5/2024. |
| 14 | What did Nikola report in first-quarter 2023 results? | 2 | 9 | Không | Không | GraphRAG: FlatRAG bám sát bằng chứng nhưng trả lời thiếu vì bỏ sót nguồn liên quan trực tiếp đến Nikola. GraphRAG dùng đúng chứng cứ doc_20, tổng hợp được nhiều ý chính của báo cáo quý 1/2023 và suy luận đa bước tốt; chỉ hơi dài và có vài chi tiết thiên về kế hoạch tương lai nhưng vẫn được nguồn hỗ trợ. |
| 15 | What investment level did U.S. EV investments reach, and what does that imply for the sector? | 6 | 7 | Không | Không | GraphRAG: Cả hai đều trả lời rằng không đủ bằng chứng, phù hợp với ngữ liệu. Tuy nhiên, GraphRAG dùng chứng cứ sát chủ đề EV hơn và giải thích rõ rằng số liệu nổi bật là của Trung Quốc chứ không phải Mỹ; dù có suy diễn nhẹ về hàm ý cho ngành, mức độ vẫn an toàn. FlatRAG cũng an toàn nhưng chứng cứ phần lớn lạc đề và hỗ trợ yếu. |
| 16 | How are Chinese battery companies investing in Europe and the United States? | 10 | 7 | Không | Có | FlatRAG: FlatRAG bám rất sát chứng cứ: đầu tư nhà máy ở châu u, châu u là điểm đến lớn nhất, và vào Mỹ sau IRA với CATL-Ford và Gotion Michigan. GraphRAG cũng đúng phần châu u và Mỹ, nhưng thêm ý BYD/CATL đầu tư tích hợp dọc để bảo đảm khoáng sản ngoài Trung Quốc; chứng cứ chỉ nói xu hướng đầu tư khoáng sản nói chung, không gắn riêng với châu u và Mỹ, nên có suy diễn thừa so với câu hỏi. |
| 17 | What does the EPA say about battery manufacturing emissions versus lifetime EV emissions? | 8 | 9 | Không | Không | GraphRAG: Cả hai câu trả lời đều đúng theo EPA: phát thải sản xuất pin làm tăng phát thải chế tạo EV, nhưng tổng phát thải vòng đời của EV thường vẫn thấp hơn xe xăng. FlatRAG dùng chứng cứ đúng nhưng có chỗ diễn đạt hơi lệch khi nói thanh xanh là toàn bộ phát thải chế tạo EV; thực ra EPA nói thanh xanh chỉ là phần pin, còn thanh cam là phần chế tạo còn lại và cuối vòng đời. GraphRAG bám sát chứng cứ EPA hơn, nối tốt quan hệ giữa phát thải sản xuất pin, phát thải vận hành và tổng vòng đời, nên nhỉnh hơn. |
| 18 | How does the Bipartisan Infrastructure Law address EV charging concerns? | 9 | 8 | Không | Không | FlatRAG: Cả hai câu trả lời đều bám sát bằng chứng về khoản 7,5 tỷ USD để mở rộng mạng lưới sạc EV. FlatRAG trả lời trực tiếp đúng trọng tâm câu hỏi. GraphRAG thêm ý về nâng cấp lưới điện và Build a Better Grid, có căn cứ trong bằng chứng nhưng hơi mở rộng sang lo ngại tác động EV lên lưới điện, không phải trọng tâm chính của “charging concerns”, nên kém chính xác hơn một chút. |
| 19 | What does Goldman Sachs say about why EV sales are slowing? | 8 | 6 | Không | Có | FlatRAG: FlatRAG bám sát câu hỏi và nêu đúng rằng không có bằng chứng nào cho thấy Goldman Sachs giải thích nguyên nhân doanh số EV chậm lại. Dù có suy luận thêm từ Pew/Cox, câu trả lời vẫn không gán sai cho Goldman Sachs. GraphRAG cũng nhận ra thiếu bằng chứng trực tiếp, nhưng lại đưa ra các lý do từ tâm lý đại lý và điều kiện kinh tế như thể gần với câu hỏi, trong khi không hề chứng minh đó là nhận định của Goldman Sachs, nên rủi ro gán ghép/hallucination cao hơn. |
| 20 | How do dealer sentiment reports describe uncertainty in the EV and auto market? | 8 | 9 | Không | Không | GraphRAG: Cả hai câu trả lời đều bám sát bằng chứng và trả lời đúng ý về bất định trong thị trường ô tô/EV. FlatRAG đúng nhưng hơi dàn trải và có một vài chi tiết Q3/EV không trực tiếp làm rõ bản chất của “uncertainty”. GraphRAG mạnh hơn vì tổng hợp đa bước tốt hơn: nối lãi suất, mùa bầu cử/khí hậu chính trị, tác động tới người tiêu dùng và đại lý, rồi kết luận rằng bất định gây thận trọng/paralysis và làm xấu doanh số, tâm lý. Không thấy bịa đặt rõ ràng ở cả hai. |

## 6. Phân tích failure modes

Nếu Flat RAG thắng GraphRAG ở một số câu, kết quả đó không có nghĩa là ý tưởng GraphRAG sai. Nó thường cho thấy câu hỏi thuộc dạng fact lookup nằm gọn trong một chunk, hoặc GraphRAG chưa lấy lại đủ supporting text gốc.

Các failure modes cần theo dõi:

- **Super-nodes**: node quá rộng như `China`, `United States`, `EV`, `market` có nhiều cạnh và dễ kéo retrieval sang context nhiễu.
- **Disconnected components**: nếu LLM extract thiếu bridge entity/relation, graph bị tách thành các đảo nhỏ và traversal không tới được evidence đúng.
- **Poor textualization**: nếu chỉ trả lời từ triples, các danh sách, số liệu và sắc thái trong văn bản gốc dễ bị mất.

Phiên bản pipeline hiện tại giảm rủi ro này bằng cách dùng graph để tìm graph facts/source documents, sau đó rerank chunks gốc bằng TF-IDF và marker scoring như `Q1`, năm, phần trăm, market share, charging, investment trước khi đưa evidence cho LLM.

## 7. Trường hợp Flat RAG yếu hoặc hallucinate

Các dòng dưới đây dựa trên verdict và cờ hallucination trong bảng benchmark.

| Question | GraphRAG evidence edge |
|---|---|
| Why did Tesla's Q1 2024 U.S. EV market share fall, and which brands grew more than 50% year over year? | Tesla -[YEAR_OVER_YEAR_SALES_CHANGE]-> -13.3% in US Q1 2024 <br> Tesla -[REPORTED_AVERAGE_TRANSACTION_PRICE]-> $52,315 in Q1 2024 <br> Tesla -[AVERAGE_TRANSACTION_PRICE_CHANGE]-> -13.5% year over year in Q1 2024 <br> Tesla -[HAS_MARKET_SHARE]-> 51.3% of US EV market in Q1 2024 |
| What Q3 2024 delivery and revenue results did VinFast report, and who backed its funding? | VinFast -[REPORTED_REVENUE]-> US$511.6 million in Q3 2024 <br> VinFast -[ACHIEVED_YOY_REVENUE_GROWTH]-> 49.3% year-over-year in Q3 2024 <br> VinFast -[ACHIEVED_YOY_DELIVERY_GROWTH]-> 115% year-over-year in Q3 2024 <br> VinFast -[REPORTED_VEHICLE_DELIVERIES]-> 21,912 EVs in Q3 2024 |
| How are ZEV regulations linked to U.S. EV sales share and model availability? | ZEV regulations -[ESSENTIAL_TO]-> EV market growth <br> EV market growth -[IMPACTED_BY]-> chip shortage |
| How does public and workplace charging availability relate to EV uptake in top U.S. metropolitan areas? | Top 10 metropolitan areas by EV uptake -[HAS_WORKPLACE_CHARGER_DENSITY]-> 430 workplace chargers per million population <br> EV growth -[LINKED_TO]-> Public and workplace charging availability <br> Top 10 metropolitan areas by EV uptake -[HAS_EV_SHARE]-> 10% electric share <br> Top 10 metropolitan areas by EV uptake -[HAS_PUBLIC_CHARGER_DENSITY]-> 935 public chargers per million population |
| What consumer charging concerns could slow EV adoption according to the corpus? | Insufficient EV Charging Infrastructure Growth -[BARRIER_TO_ADOPTION]-> EV adoption <br> EV adoption -[BARRIER_TO_ADOPTION]-> limited driving range <br> EV adoption -[BARRIER_TO_ADOPTION]-> lack of charging infrastructure <br> EV adoption -[BARRIER_TO_ADOPTION]-> high purchase cost |
| Which company surpassed Tesla as the largest EV producer, and where are Chinese EV brands expanding? | BYD -[SURPASSED]-> Tesla <br> Tesla -[WAS_LARGEST_EXPORTER_FROM]-> China <br> BYD -[COMPETES_WITH]-> Tesla <br> Tesla -[HAS_EXPORT_SHARE]-> 40.25 percent of EV exports from China between January and April 2023 |
| How does the Inflation Reduction Act connect to EV leasing incentives or battery investment? | Inflation Reduction Act -[CATALYZED]-> investment and job creation in American electric vehicle manufacturing <br> Inflation Reduction Act -[SUPPORTED_INVESTMENT_IN]-> battery factories <br> Inflation Reduction Act -[ACCELERATED]-> U.S. electric vehicle and battery manufacturing markets <br> Inflation Reduction Act -[SUPPORTED_INVESTMENT_IN]-> Rivian EV factory in Georgia |
| How did Cadillac, Mercedes, BMW, Audi, and Ford perform in Q1 2024 EV sales relative to Tesla? | Ford -[RANKED_BY_EV_SALES_VOLUME]-> second-highest behind Tesla in Q1 2024 <br> Cadillac -[YEAR_OVER_YEAR_EV_SALES_GROWTH]-> 499.2% in Q1 2024 <br> Tesla -[YEAR_OVER_YEAR_SALES_CHANGE]-> -13.3% in US Q1 2024 <br> Ford -[YEAR_OVER_YEAR_EV_SALES_GROWTH]-> 86.1% in Q1 2024 |
| What is VinFast's relationship with Vingroup and Pham Nhat Vuong? | Pham Nhat Vuong -[FOUNDER_OF]-> VinFast <br> Vingroup -[PROVIDES_LOANS_TO]-> VinFast subsidiaries in Vietnam up to VND35 trillion through end of 2026 <br> VinFast -[RELIES_ON_SUPPORT_FROM]-> Vingroup <br> VinFast -[ASSOCIATED_WITH]-> Vingroup affiliates |
| What are the main barriers to EV adoption mentioned across Deloitte, EPA, and McKinsey style sources? | EPA -[PROVIDES]-> Beyond Tailpipe Emissions Calculator <br> EPA -[COLLABORATES_WITH]-> Department of Energy <br> Department of Energy -[PROVIDES]-> Beyond Tailpipe Emissions Calculator <br> Department of Energy -[OFFERS]-> EV Pro Lite Tool |

## 8. Deliverables

- Source code pipeline: `graphrag_lab.py`
- Report generator: `generate_report.py`
- Environment template: `.env_example`
- Knowledge graph top-40 image: `outputs/knowledge_graph.png`
- GraphML top-40 visualization subset: `outputs/knowledge_graph.graphml`
- Triples: `outputs/triples.csv`
- Benchmark table: `outputs/benchmark_results.csv`
- Run metadata: `outputs/run_metadata.json`
- LLM extraction cache: `outputs/llm_triples_cache.jsonl`

## 9. Cách chạy

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
