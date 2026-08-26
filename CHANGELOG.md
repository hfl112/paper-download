# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims
to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
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
