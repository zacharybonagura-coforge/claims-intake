Run `c68b9458-b7f4-4e4f-b573-74f5d30864e5`: Mistral, temperature `0.0`. `summarize.v1.md` on S01–S12 (`SummarizationOutput`) and `extract.v2.md` on E01–E12 (`PolicyExtraction`).

- Summarization repair rate: **0/12**
- Extraction repair rate: **1/12** (E11)
- Example leakage count for Extraction: **0**
- Citation-existence failure count: **6** (all on S11)

The only schema repair was E11: `beneficial_ownership_threshold.citation` was a list (`["3. Beneficial Ownership", "6. Reviewer Note"]`) instead of a string. The repair prompt sent that validation error and asked the model to correct only that field, where the second response used a string citation and passed Pydantic.