*This project has been created as part of the 42 curriculum by jose-car.*

# RAG against the machine

## Description

A **Retrieval-Augmented Generation** (RAG) system that answers questions about
the source code and documentation of **vLLM 0.10.1**. It runs entirely on a
CPU and has four stages:

1. **Indexing:** the corpus in `data/raw/` is cut into chunks of at most 2000
   characters and stored in SQLite.
2. **Retrieving:** a lexical search with **BM25**, implemented in this
   project, returns the chunks most related to a question.
3. **Augmenting:** the best chunks are placed in a prompt next to the
   question, within a token budget.
4. **Generating:** the local model **Qwen/Qwen3-0.6B** writes an answer
   grounded in those chunks.

The system also measures its own retrieval quality with **recall@k** (and
MRR) against datasets of questions with known correct sources.

## Instructions

Requirements: Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).
No GPU is needed: `torch` is installed from the CPU-only wheel index.

```bash
make install          # uv sync: creates .venv from pyproject.toml and uv.lock
```

Place the data where the commands expect it (all paths can be changed with
flags):

```
data/raw/vllm-0.10.1/                    the vLLM 0.10.1 source tree
data/datasets/UnansweredQuestions/       dataset_docs_public.json, dataset_code_public.json
data/datasets/AnsweredQuestions/         the same questions with their correct sources
```

The first `answer` downloads Qwen3-0.6B (about 1.5 GB) into
`.cache/huggingface/`; uv's package cache lives in `.cache/uv/`. Both stay
inside the repository on purpose: at school the home quota is small. Run every
command from the repository root.

Other Makefile rules:

| Rule | What it does |
|---|---|
| `make run ARGS="..."` | Runs `python -m src` with any arguments |
| `make debug ARGS="..."` | The same under `pdb` |
| `make lint` | `flake8` and `mypy` with the subject's flags |
| `make lint-strict` | `flake8` and `mypy --strict` |
| `make test` | The test suite without the three tests that load the real model |
| `make test-all` | The whole test suite (about 50 s) |
| `make clean` | Removes `__pycache__`, `.mypy_cache` and `.pytest_cache` |

## Example usage

The full pipeline, step by step. Every command has a `make` shortcut whose
values can be overridden on the command line (`DATASET`, `SCOPE`, `K`, `Q`,
`MAX_CHUNK_SIZE`, `SEARCH_DIR`, `ANSWER_DIR`).

**1. Build the index**

```bash
uv run python -m src index --max_chunk_size 2000
make index
```
```
Indexing: 100%|██████████| 1969/1969 [00:02<00:00, 695.15file/s]
Ingestion complete! Indexed 18941 chunks under data/processed/
```

**2. Search one question**

```bash
uv run python -m src search "How to configure OpenAI server?" --k 3
make search Q="How to configure OpenAI server?" K=3
```
```
1.  17.53  data/raw/vllm-0.10.1/docs/deployment/frameworks/dstack.md  [1936:3170]
2.  17.07  data/raw/vllm-0.10.1/examples/online_serving/openai_chat_completion_with_reasoning.py  [0:677]
3.  16.28  data/raw/vllm-0.10.1/examples/online_serving/openai_transcription_client.py  [0:713]
```

Each line shows the position, the BM25 score, the file and the character
range `[first:last)` of the chunk.

**3. Search a whole dataset**

```bash
uv run python -m src search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \
    --k 10 --save_directory data/output/search_results
make search_dataset                  # docs
make search_dataset DATASET=code
```
```
Saved student_search_results to data/output/search_results/dataset_docs_public.json
```

**4. Evaluate the retrieval**

```bash
uv run python -m src evaluate \
    --student_search_results_path data/output/search_results/dataset_docs_public.json \
    --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json
make evaluate                        # docs
make evaluate DATASET=code
```
```
Recall@1: 0.610 Recall@3: 0.810 Recall@5: 0.830 Recall@10: 0.860
MRR: 0.704
```

**5. Answer one question**

```bash
uv run python -m src answer "How do I dynamically load a LoRA adapter in vLLM?" --k 5
make answer Q="How do I dynamically load a LoRA adapter in vLLM?" K=5
```
```
To dynamically load a LoRA adapter in vLLM, you can use the `/v1/load_lora_adapter` endpoint or set up a LoRAResolver plugin.
```

**6. Answer a whole file of search results**

```bash
uv run python -m src answer_dataset \
    --student_search_results_path data/output/search_results/dataset_docs_public.json \
    --save_directory data/output/search_results_and_answer
make answer_dataset
```
```
Loaded 100 questions ... Processed 100 of 100 questions
Saved student_search_results_and_answer to data/output/search_results_and_answer/dataset_docs_public.json
```

Errors never show a traceback: an empty query, `--k 0`, a missing file,
malformed JSON or a save directory that is a file end with one line such as
`ERROR: k must be a positive integer` and exit code 1.

## System architecture

The code follows a **hexagonal architecture** (ports and adapters): the
centre knows nothing about files, SQLite or the model, and every import
points inwards. `tests/test_architecture.py` fails if a layer imports what it
must not.

```
src/
  domain/             pure logic, no I/O: pydantic models, chunking, tokenizer,
                      BM25, recall@k and MRR, prompt building
  application/
    ports/            what the use cases need from outside, as Protocols:
                      CorpusReader, IndexStore, DatasetStore, Generator
    use_cases/        one module per command, plus the retrieval they share
  adapters/
    inbound/cli.py    Python Fire CLI; the error boundary
    inbound/api/      FastAPI app (bonus): one router per route
    outbound/         corpus files, JSON files, SQLite index, Qwen generator
  bootstrap.py        the only place that builds the concrete adapters
```

How the pieces interact:

```
index:   corpus files ──read──> chunking (domain) ──> SQLite (data/processed/index.db)
search:  SQLite ──load chunks──> BM25 index in memory ──rank──> top k sources
answer:  top k sources ──prompt (domain, token budget)──> Qwen3-0.6B ──> answer
evaluate: search results + answered dataset ──recall@k, MRR (domain)──> scores
```

The CLI receives the adapters from `bootstrap.py`, calls a use case and turns
any `ValueError` into one `ERROR:` line. `torch` and `transformers` are only
imported by `answer` and `answer_dataset`, so the other commands start fast.

## Chunking strategy

Two strategies, chosen by file suffix; both guarantee that the chunks of a
file cover it entirely, without gaps or overlap, and that none is wider than
`--max_chunk_size` (default and maximum 2000 characters). A chunk is stored as
its file path and character range, exactly as the subject's sources.

- **Markdown and text** are cut in cascade: first at headings (`#` at the
  start of a line), then a section that does not fit is filled with whole
  paragraphs (split at blank lines), and only a paragraph wider than the limit
  is cut by force. Measured on the corpus: 61% of the 206 `.md`/`.txt` files
  exceed 2000 characters, but 93% of their sections and 99.7% of their
  paragraphs fit.
- **Python** is parsed with `ast` and cut at every top-level definition
  (`def`, `async def`, `class`, with their decorators), so a function stays
  in one chunk whenever it fits. A definition that does not fit goes through
  the same cascade (blank lines, then a forced cut). A file that does not
  parse is chunked as text instead of failing.

On the real corpus: 1,969 files give 18,941 chunks, the widest exactly 2000
characters.

## Retrieval method

Retrieval is lexical and uses **Okapi BM25**, implemented in
`src/domain/bm25.py` (SQLite only stores the chunks; it does not rank them).
Text is lowercased and split into runs of letters, digits and underscores.
An identifier with underscores is kept **whole and followed by its parts**
(`lm_eval` gives `lm_eval`, `lm`, `eval`): a question may quote an identifier
verbatim, which the whole token matches with a high IDF, or paraphrase it,
which only the parts can match. `CamelCase` is not split.

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
- **Ranking.** The chunks are sorted by descending score, ties broken by chunk
  id so the order is stable, and the first `k` are returned. A chunk with no
  query term is never a candidate, so a query with no known word returns
  nothing instead of random chunks.

The index of the 18,941 chunks is built in memory from SQLite once per
command (most of the 1.8 s of one `search`), so `search_dataset` answers
every question from the same index.

## Performance analysis

Measured on 2026-10-20 on an Intel Core i7-8750H (6 cores, 12 threads), with
`time uv run ...` (so uv's start-up is included), public datasets, `--k 10`:

| Metric | Value | Subject limit |
|---|---|---|
| Indexing (1,969 files, 18,941 chunks) | 3.7 s | ≤ 300 s |
| `search_dataset`, 199 questions (100 docs + 99 code) | 8.9 s (4.2 + 4.7) | ≤ 90 s for 200 |
| One `search` | 1.8 s, almost all of it building the BM25 index | — |
| Recall@5, docs | **0.830** | ≥ 0.80 |
| Recall@5, code | **0.636** | ≥ 0.50 |

| Dataset | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|---|
| docs | 0.610 | 0.810 | 0.830 | 0.860 | 0.704 |
| code | 0.354 | 0.566 | 0.636 | 0.697 | 0.480 |

Our `evaluate` reproduces the official recall@k (a correct source counts
when a retrieved chunk of the same file overlaps it with an IoU above 0.05).
It also reports the **MRR** (mean reciprocal rank: 1 / the position of the
first correct source, averaged over the questions), because recall@5 cannot
tell position 1 from position 5.

How we got there, one change at a time on the code dataset (Recall@5):
0.485 with the first BM25 version (Lucene IDF, `k1 = 1.5`), 0.535 with the
original Okapi definition, 0.636 with identifiers kept whole and split. Docs
stayed between 0.830 and 0.840.

Generation is the slow part: Qwen3-0.6B on the CPU takes about 30 s for one
`answer` (model load included) and answered the 199 public questions in
56 minutes (docs 33:42, code 22:23), with no empty answer.

## Design decisions

- **BM25 over TF-IDF**, written by hand: it saturates repeated terms and
  normalises by chunk length, and every number can be explained. SQLite
  FTS5 and its `bm25()` are not used.
- **One flat SQLite table** `chunks(id, file_path, first_character_index,
  last_character_index, text)`: storing the text lets `search` and the prompt
  use it without reading the corpus again; repeating the path costs about
  1 MB of the 25 MB index and avoids a join. A second table, `files`, keeps
  one fingerprint per file for incremental indexing (see the bonus below).
- **Prompt by chat roles:** the rules go in the `system` message; the sources
  go in the `user` message, each wrapped in
  `<source id="N" path="...">...</source>`, with the question last. The rules
  ask the model to answer only from the sources or to say it cannot.
- **Token budget of 2,000 tokens** for the whole prompt, counted with Qwen's
  own tokenizer. Sources are added in BM25 order until the next one would not
  fit, and then adding stops (a smaller, worse source is never slipped in).
  The limit is CPU time, not the 32,768-token window: in `float32` one source
  takes about 13 s and five about 31 s.
- **Qwen in `float32`, greedy decoding, thinking disabled, at most 256 new
  tokens:** `bfloat16` is about 2.7 times slower on this CPU, and the answers
  should be short and reproducible.
- **Hexagonal architecture:** the bonus parts (HTTP API, embeddings, cache)
  would be new adapters, without touching the use cases.
- **No tuning on the public datasets:** a change was kept only if it had a
  reason before measuring, and it did not lower the thresholded metric on any
  dataset. Two measured experiments were **discarded** that way: cutting
  large Python classes at their methods (code Recall@5 0.485 → 0.465) and
  adding the words of the file path to every chunk (code 0.636 → 0.727, but
  docs 0.830 → 0.820).
- **Python 3.10** is pinned in `.python-version`, the version of the school
  machines; the CI runs on it too.

## Challenges faced

- **Code questions were below the threshold** (Recall@5 0.485 against 0.50).
  Reading the misses showed questions that quote identifiers like
  `max_num_seqs` while chunks were tokenised into `max`, `num`, `seqs`.
  Keeping each identifier whole *and* split, plus the original BM25
  definition, took code to 0.636 without lowering docs.
- **Python files larger than any chunk:** 24% of the top-level definitions are
  wider than 2000 characters. Cutting at definitions first and at blank lines
  afterwards keeps most methods whole, because PEP 8 puts a blank line between
  them.
- **Generation time on the CPU:** the model loads in `bfloat16` by default,
  which was 2.7 times slower; switching to `float32` and capping the prompt at
  2,000 tokens made a full dataset run fit in under an hour.
- **Character offsets:** sources are character ranges, not bytes. Files are
  read as strict UTF-8 text, and a test checks that `ñ` counts as one
  character.
- **Errors without tracebacks:** every adapter turns its failures into a
  `ValueError` with one clear sentence (the JSON line and column, the first
  field that does not match the model, the path that is missing), and the CLI
  is the only place that prints it.
- **Python 3.10 at school:** a null byte in a source file raises `ValueError`
  instead of `SyntaxError` before Python 3.12, and one vLLM script uses a
  3.12-only f-string. Both now fall back to text chunking, with a test.

## Bonus: local HTTP API

The same `search` and `answer` are served over HTTP by a second inbound
adapter, so another program (or a browser page) can use the system without
the command line. The use cases did not change.

```bash
make serve            # uvicorn on http://127.0.0.1:8000; try it at /docs
```

| Route | Body | Returns |
|---|---|---|
| `GET /api/v1/health` | none | `{"status": "ok"}` |
| `POST /api/v1/search` | `{"query": "...", "k": 10}` | the question and its `retrieved_sources` |
| `POST /api/v1/answer` | `{"query": "...", "k": 10}` | the question and the model `answer` |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search \
     -H "Content-Type: application/json" \
     -d '{"query": "How do I load a LoRA adapter?", "k": 2}'
```

- The layout follows one router per route under `/api/v1`, with the request
  and response shapes as pydantic models in `schemas.py`.
- `bootstrap.py` builds the app with the real adapters; the routes receive
  the ports through FastAPI's `Depends`, so the inbound layer still never
  imports SQLite or Qwen.
- The model is loaded on the first `answer` and kept for the life of the
  server (`functools.cache` inside the app, not a module global).
- A user error (empty query, `k = 0`, missing index) is a `400` with the same
  sentence the CLI prints; a malformed body is a `422` from pydantic.

## Bonus: index cache

Building the searchable index is almost the whole cost of a search: about
2.1 s (0.13 s reading SQLite, 1.26 s tokenising, 0.73 s building BM25) against
12 ms for the search itself. A CLI command lives for one query, so it has
nothing to reuse; the HTTP server does.

- `IndexCache` keeps the last built index, keyed by the index path and its
  version: the file's modification time and size, read with one `stat` call
  through the `IndexStore` port. Running `index` recreates the file, so the
  next request rebuilds automatically.
- Each app owns its cache (no module-level state). `run_search` and
  `run_answer` take the loader as an optional parameter, so the CLI is
  unchanged.
- Measured with `make serve`, `k = 5`:

| Request | Time |
|---|---|
| First search (empty cache) | 2.22 s |
| Second and third search | 0.013 s |
| After touching the index file | 2.06 s, then 0.013 s |

- Known limit: two requests that miss at the same time both build the index
  once; a lock would avoid it. Caching whole answers was left out because it
  only helps when the exact same question repeats.

## Bonus: incremental indexing

`index` re-chunks only the files that changed. Chunking is most of the work
(2.27 s of the full run, mostly `ast`), while telling what changed is cheap.

- Every file gets a **fingerprint**: the SHA-256 of its text together with
  `max_chunk_size`, stored in a `files` table next to the chunks. A file whose
  fingerprint matches keeps its chunks; a modified file is re-chunked; a
  deleted file loses its chunks. All of it happens in one SQLite transaction.
- SHA-256 of the content (0.074 s for the 1,969 files) was chosen over
  modification time and size (0.013 s): archives restore old dates, so a
  changed file could keep both and the index would go stale without anyone
  noticing.
- The chunk size is part of the fingerprint, so a new `--max_chunk_size`
  re-chunks everything. When nothing can be reused (first run, an index from
  before this change, a new size) the index is rebuilt from scratch, which
  also gives the file back its minimal size.
- No new flag: the command is the subject's `index --max_chunk_size`.

| `index` run | Time |
|---|---|
| Full rebuild | 3.7-3.8 s (4.2 s before the change) |
| Nothing changed | 1.05 s |
| One file changed | 1.11 s |

The index written incrementally gives the same recall: docs Recall@5 0.830
(MRR 0.704), code 0.636 (MRR 0.480). On this corpus most of the remaining
second is Python starting up; the gain grows with the size of the corpus.

## Resources

- S. E. Robertson, S. Walker, S. Jones, M. M. Hancock-Beaulieu, M. Gatford,
  *Okapi at TREC-3*, Proceedings of TREC-3, 1994.
- S. Robertson, H. Zaragoza, *The Probabilistic Relevance Framework: BM25 and
  Beyond*, Foundations and Trends in Information Retrieval, 2009.
- K. Spärck Jones, *A statistical interpretation of term specificity and its
  application in retrieval*, Journal of Documentation, 1972.
- P. Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP
  Tasks*, NeurIPS 2020.
- C. D. Manning, P. Raghavan, H. Schütze, *Introduction to Information
  Retrieval*, Cambridge University Press, 2008 (chapters 6 and 11).
- [Qwen3-0.6B model card](https://huggingface.co/Qwen/Qwen3-0.6B) and the
  [Hugging Face Transformers documentation](https://huggingface.co/docs/transformers).
- Documentation of [Python `ast`](https://docs.python.org/3/library/ast.html),
  [sqlite3](https://docs.python.org/3/library/sqlite3.html),
  [pydantic](https://docs.pydantic.dev/),
  [Python Fire](https://github.com/google/python-fire) and
  [uv](https://docs.astral.sh/uv/).

### How AI was used

An AI assistant (Claude) was used throughout the project as a tutor, reviewer
and helper for repetitive work:

- **Explanations** of the concepts (RAG, BM25, SQLite, `ast`, pydantic, the
  architecture, tokens and context windows) before each part was written.
- **Tests:** writing the failing tests that defined each behaviour first.
- **Code suggestions and review:** suggesting code for parts of the
  production code, which the author copied, adapted and can explain, and
  reviewing the author's code for bugs and missed cases.
- **Docstrings, configuration and tooling:** Makefile, `pyproject.toml`, CI,
  and project documentation, including this README.
- **Measurements:** running the timing and recall measurements recorded in
  this README.

Design choices (chunking strategy, BM25 variant, prompt layout, architecture)
were made by the author from options laid out with the assistant, and every
part of the code was reviewed and run by the author.
