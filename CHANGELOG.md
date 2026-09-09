# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims
to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `fetch --defer-pdf-parse` and the new `parse` command split full-text
  retrieval in two: fetch tries the structured sources and, when only a PDF is
  available (Wiley TDM, Unpaywall mirrors, landing pages), saves it with
  `status.fulltext = pdf_pending`; `parse` later runs Docling on the saved
  PDFs with no network access. Fetch stays inside publisher rate limits while
  parsing scales across nodes or onto a GPU (Docling on one Wiley PDF: about
  35 s on 4 CPU cores).
- `ELSEVIER_INSTTOKEN`: sent as `X-ELS-Insttoken` with the Elsevier article API
  so text mining works from hosts outside the institution's IP range.
- Articles without a usable DOI (none, or a journal's own code that Europe PMC
  put in the doi field, e.g. `011143/aim.005`) are no longer dead ends: the
  full-text chain first asks Crossref for the DOI by exact title match (year
  within 1), then falls back to the PubMed LinkOut publisher page, whose PDF
  link is parsed like any landing page. A resolved DOI or page is written back
  to `identifiers` / `links.publisher`; the article_id does not change.
- PDF downloads (`fetch --output-format pdf`) now try the Wiley TDM API when
  `WILEY_TDM_TOKEN` is set and the DOI is a Wiley prefix, right after the PMC
  route; the API is throttled to 6 requests per minute (Wiley's 60 per 10 min).
  Before, the token was only used by the full-text JSON chain.
- `fetch --ids-file <file>`: fetch only the listed article_ids, so several jobs
  can work on disjoint slices of one collection in parallel.

### Fixed
- `parse` runs Docling once before the batch and aborts on a CUDA / kernel-image
  error instead of letting every article fall back to PyMuPDF flat text (that
  happened on a V100 with a CUDA 13 torch build, which carries no sm_70 kernels).
- Docling's torch.compile is switched off (`DOCLING_INFERENCE_COMPILE_TORCH_MODELS=0`
  unless already set): on hosts whose g++ lacks c++20 it raised inside
  `parse_pdf_docling`, and the silent fallback to the flat pymupdf text lost
  every paragraph before the first recognised heading. That flat splitter now
  keeps such text as a `Preamble` section when it is 1000+ characters and no
  abstract was found, so case reports without an Introduction heading survive
  even when Docling is unavailable.
- Docling PDF parsing runs with its own OCR disabled: text-layer PDFs never
  needed it, scanned PDFs already fall through to the tesseract route, and the
  RapidOCR model download it triggered cost two minutes per PDF on hosts that
  cannot reach modelscope.cn.
- The fetch log now records why an open-access PDF download failed
  (`no_mirror`, `unpaywall_404`, `landing_unreachable`, ...) instead of the
  generic `pdf_download_failed`.

### Changed
- Per-host throttles for link.springer.com and www.nature.com (3 s, Springer
  Nature's TDM policy allows 1 request/s for direct downloads) and the Europe
  PMC PDF render (1 s).
- **Renamed the project `paper-extract` -> `paper-download`.** The old name
  collided with the sibling table-extraction tool; this one never extracts from
  paper content, it searches, fetches and exports. Import package
  `paper_extract` -> `paper_download`, console script `paper-extract` ->
  `paper-download`, skill dir `skill/paper-extract` -> `skill/paper-download`.
  Subcommands, flags and on-disk output are unchanged.
- New launcher: `python paper_download.py <command>` runs the CLI from a clone
  with no install step, matching the sibling tool's invocation style. The
  `paper-download` console script from `pip install` still works.
- HTTP `User-Agent` strings sent to Europe PMC / PubMed / OpenAlex / full-text
  sources now say `paper-download`.
- Environment variables renamed to `PAPER_DOWNLOAD_EMAIL` / `PAPER_DOWNLOAD_ROOT`;
  the pre-rename `PAPER_EXTRACT_*` names are still honoured as a fallback.

### Added
- **OpenAlex** as a third search source (default-on), extending coverage beyond
  biomedical to all disciplines (2.5M+ venues, no API key). Abstracts are
  reconstructed from OpenAlex's inverted index. Because OpenAlex indexes arXiv,
  arXiv papers now surface in ordinary searches.
- **arXiv full text**: an arXiv fetch adapter (keyed on the `10.48550/arXiv.*`
  DOI, like the bioRxiv adapter) downloads and parses the PDF for arXiv papers
  found via OpenAlex. arXiv is intentionally *not* a separate search source.
- `search --source <name>` (repeatable) to limit a search to specific sources
  (`epmc` / `pubmed` / `openalex`); default searches all. Unknown names error.
- `collection import --input-pdf`: import papers from a local PDF file or a
  directory of PDFs. Metadata (DOI, title) is read from the PDF via PyMuPDF
  (optional `[pdf]` extra) with a filename fallback when it is not installed,
  then enriched via Europe PMC.

### Changed
- Internal architecture refactor — no change to CLI behavior or on-disk output:
  - The article schema and its state transitions now live in one **Article
    module** (`paper_download/article.py`); status values are defined once.
  - Full-text assembly (the flatten → build → quality → link-marking sequence)
    is shared by the open-access and institutional routes via one **assemble**
    module, removing duplicated code and an internal import cycle.
  - The fetch transport is an **injectable HTTP client**, so the full-text
    fetch path is exercisable offline.
  - Search sources sit behind a **Source interface** with Europe PMC and PubMed
    adapters, sharing one retry loop and dedup key.
  - Citation exports (BibTeX/RIS/CSV) share one `citation_view`.

### Removed
- Dead modules and unused writers left over from a retired CLI
  (`cancer_tagger`, `dedup_merge`, per-fetcher `write_csv`/`write_json`).

## [0.1.0] - 2026-07-05

### Added
- Initial public release: search (Europe PMC + PubMed), import by DOI/PMID/CSV,
  structured full-text JSON + PDF fetch (open access and institutional via
  EZProxy/LibKey), and BibTeX/RIS/CSV/JSONL export, with per-command audit logs.
- Agent Skill for Claude Code / Codex-style agents.

[Unreleased]: https://github.com/hfl112/paper-download/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hfl112/paper-download/releases/tag/v0.1.0
