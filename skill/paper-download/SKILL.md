---
name: paper-download
description: Build an auditable local collection of biomedical papers — search Europe PMC + PubMed, import by DOI/PMID, fetch structured full-text JSON and PDFs (open-access AND institutional/library via EZProxy/LibKey), then export BibTeX/RIS/CSV/JSONL. Use when the user wants to gather literature, build a paper/citation collection, pull full text for a set of DOIs/PMIDs, get PDFs behind a paywall through their university login, or prepare papers for downstream LLM/RAG extraction.
---

# paper-download

Drives the `paper-download` CLI (an installable Python package) to build
reproducible, auditable literature collections. Each collection is a folder with
`article.json` per paper, an `articles.csv` index, and a `logs/*.json` audit trail.

## Scope

Use this skill when the user wants to:
- build a literature collection from a topic, query, DOI/PMID list, or CSV;
- fetch structured full-text JSON and/or PDFs;
- export a collection to BibTeX / RIS / CSV / JSONL;
- retrieve paywalled full text through **their own** institutional access.

Do NOT use this skill to:
- bypass authentication or access controls;
- auto-solve captchas (the user solves any challenge themselves, in the browser);
- mass-download publisher content in violation of terms of service;
- access content the user has no valid credentials for.

Library access always runs through the user's own valid login; the tool never
stores credentials and never circumvents authentication. If a request implies
otherwise, decline the circumvention and offer the legitimate path.

## Prerequisites

- Two equivalent invocations. `python paper_download.py <command>` needs no install but
  must run from the repo root (or use its absolute path). `paper-download <command>` is the
  console script from `pip install`, and needs the environment it was installed into.
  Verify with `python paper_download.py --help` (or `uv run python paper_download.py --help`).
- Install if missing (uv recommended, no conda needed; run from the repo root):
  - `uv venv --python 3.11`, then `source .venv/bin/activate`, then
    `uv pip install ".[browser,pdf,llm]"` — engine + browser/PDF extras + LLM provider SDKs.
  - ALWAYS activate the venv before `uv pip install`: if a conda env is active and no
    venv is activated, uv installs into the conda env instead of `.venv`.
  - Plain pip works too (inside the activated venv): `pip install ".[browser,pdf,llm]"`.
- If the user set up a venv, prefix commands with `uv run` (or activate the venv).

## Workflow

```text
search-plan → search / collection import → fetch → status → collection export
```

Pick the entry point from what the user has:
- **A topic/question** → `search-plan` (optionally LLM) then `search`.
- **A raw query string** → `search --query`.
- **A list of DOIs/PMIDs or a CSV/JSON** → `collection import`.

Then `fetch` full text, `status` to review, `collection export` to hand off.

## Command quick reference

```bash
# Plan (deterministic):
python paper_download.py search-plan --collection C --keyword A --keyword B --anchor A --no-llm
# Plan (LLM aliases + anchor/M-of-N; needs a provider key):
python paper_download.py search-plan --collection C --prompt "…" --provider gemini

python paper_download.py search --collection C --query '…' --max 30      # or omit --query to use current plan
python paper_download.py collection import --collection C --input-doi 10.x/y --input-pmid 12345678
python paper_download.py collection import --collection C --input file.csv        # or --input-json file.json

python paper_download.py fetch --collection C --output-format json --access open  # --output-format REQUIRED
python paper_download.py fetch --collection C --output-format both --access library --speed normal --limit 5

python paper_download.py status --collection C
python paper_download.py collection export --collection C --to bib   # bib | ris | csv | jsonl
```

## Rules that matter

- `fetch --output-format` is **required** (`json` | `pdf` | `both`). Never omit it.
- `--access`: `open` (PMC/OA/publisher/PDF) | `library` (institutional) | `both` (open then library).
- Author search uses Europe PMC field syntax, e.g. `--query 'AUTH:"Houghton PJ" AND AUTH:"Smith MA"'`.
- No default year filter; add `--min-year` / `--max-year` to restrict.
- `--speed` (library only): `fast` (default, fixed 8s between articles) | `normal`
  (random 5–60s) | `slow` (random 50–300s). Use `normal`/`slow` if a publisher
  keeps challenging the session.
- fetch skips already-successful articles; add `--force` to redo. `--force` never
  destroys existing good full text on a failed re-fetch.
- Exports write to the current directory (`./<name>.<ext>`). Never touch Zotero.
- Sensitive (proxy/token) links are auto-stripped from exports; never surface or
  commit cookies, tokens, `.env`, `api.md`, PDFs, or anything under `data/`.

## Reading results

Every command writes `data/collections/<C>/logs/<cmd>_<ts>.json`. After a run,
read the newest log and report from its `summary` (total/succeeded/failed/skipped)
and per-item `attempts[].reason`. For full text, check the article's
`status.fulltext`, `source.fulltext`, and `quality.status` in `article.json`.
The CLI prints the log path on completion.

## Institutional / library full text

Login is INTERACTIVE and is the USER's job. **Never try to log in for them** —
SSO / captcha / 2FA / school policy are theirs to handle in their own browser.

Agent flow for `--access library`:
1. Run `python paper_download.py library doctor` (read-only, never opens a browser). If it
   reports NOT READY, STOP and tell the user to run `python paper_download.py library login`
   in **their own terminal** (it opens a browser and waits for Enter), then
   continue once they confirm.
2. When ready, batch-fetch non-interactively:
   `python paper_download.py fetch --collection C --output-format both --access library --non-interactive`
   `--non-interactive` never opens a login prompt: it reuses the session the user
   established and fails fast (per article, on a login page) instead of hanging.
   In a real TTY you may omit it — fetch then opens the login browser once itself.
   The browser profile now persists a stable fingerprint seed; login and fetch
   must reuse the same profile so challenge-clearance cookies remain valid.

During interactive library fetches, if a captcha/login wall appears, the user
solves it in the browser window only. The tool polls the page and continues
automatically when the wall clears; do not ask the user to press Enter for each
article.

**Before any `--access library` work read `references/library-access.md`** — setup
decision tree, "log in once → batch many", and troubleshooting (captcha, session
expiry, proxy auto-detection). The LibKey-extension path is macOS + Chrome only.

## LLM search plans

`search-plan --prompt` and alias expansion use the bundled `llmclient` package
(Gemini/OpenAI/DeepSeek/Claude). If the user has no API key configured, the LLM
paths fail with a clear error — fall back to `--no-llm` with explicit `--keyword`s,
or ask which provider/key to use. Provider = `--provider` arg → `$LLM_PROVIDER` →
first provider with a key in the environment / `.env`.
