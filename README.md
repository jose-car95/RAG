# RAG
RAG system for querying codebases using retrieval, local LLM generation, and recall@k evaluation.

## Retrieval method

Retrieval is lexical and uses **Okapi BM25**, implemented in
`src/domain/bm25.py` (SQLite only stores the chunks; it does not rank them).
Text is lowercased and split into runs of letters, digits and underscores.
An identifier with underscores is kept **whole and followed by its parts**
(`lm_eval` gives `lm_eval`, `lm`, `eval`): a question may quote an identifier
verbatim, which the whole token matches with a high IDF, or paraphrase it,
which only the parts can match. This raised code Recall@5 on the public
datasets from 0.535 to 0.636, with docs Recall@5 unchanged at 0.830 (docs
Recall@1 went from 0.650 to 0.610). `CamelCase` is not split.

We follow the **original Okapi BM25 definition**, with the classic
**Robertson/Spärck Jones IDF**:

```
score(q, d) = Σ over each term t of q:  IDF(t) × tf × (k1 + 1) / (tf + k1 × (1 − b + b × |d| / avgdl))

IDF(t) = ln( (N − df(t) + 0.5) / (df(t) + 0.5) )
```

- `tf`: how many times `t` appears in the chunk `d`; `|d|`: the chunk length
  in tokens; `avgdl`: the mean chunk length; `N`: the number of chunks;
  `df(t)`: how many chunks contain `t`.
- `k1 = 1.2` and `b = 0.75`, the values of the original definition (also the
  defaults of Lucene and Elasticsearch). They were chosen because they are the
  reference definition, not tuned against the public datasets.
- **IDF floor.** The original IDF is 0 or negative for a term found in half
  or more of the chunks; in our index that only happens to `def`. A negative
  weight would push a chunk down for containing a word of the question, so a
  non-positive IDF is raised to a tiny floor, `1e-6` (the one SQLite FTS5
  uses): the term barely counts but still breaks ties.
- Until this change we used Lucene's IDF variant, `ln(1 + ...)`, with
  `k1 = 1.5`. The switch raised code Recall@5 on the public datasets from
  0.485 to 0.535 (docs: 0.840 to 0.830). For transparency: before deciding,
  we had seen a one-off probe with SQLite FTS5, which uses this same variant.

Besides recall@k, our `evaluate` command reports the **MRR** (mean
reciprocal rank: 1 / the position of the first correct source, averaged over
the questions), because recall@5 cannot tell position 1 from position 5. On
the public datasets it is 0.704 for docs and 0.480 for code.

References:

- S. E. Robertson, S. Walker, S. Jones, M. M. Hancock-Beaulieu, M. Gatford,
  *Okapi at TREC-3*, Proceedings of TREC-3, 1994.
- S. Robertson, H. Zaragoza, *The Probabilistic Relevance Framework: BM25 and
  Beyond*, Foundations and Trends in Information Retrieval, 2009.
- K. Spärck Jones, *A statistical interpretation of term specificity and its
  application in retrieval*, Journal of Documentation, 1972.
