"""Open-access fetch routes.

Thin: each entry point fetches content via the source engine, then hands off to
the shared assembler (paper_download.assemble) for the flatten → build → quality
→ mark-links sequence. The article↔flat translation and identity checks live in
that assembler, not here.
"""
from __future__ import annotations

from typing import Any

from .. import article as article_mod
from .. import assemble as assemble_mod
from .. import links as links_mod
from ..collection import CollectionStore
from ..sources.fulltext import fulltext_sources


def _write_back_resolved(article: dict[str, Any], resolved: dict[str, Any]) -> None:
    """A DOI found by Crossref title match / a LinkOut page used for the PDF: keep them, the article_id stays."""
    if resolved.get("doi"):
        article.setdefault("identifiers", {})["doi"] = resolved["doi"]
        article.setdefault("links", {}).setdefault("publisher", {})["page"] = f"https://doi.org/{resolved['doi']}"
    if resolved.get("land_url"):
        article.setdefault("links", {}).setdefault("publisher", {})["page"] = resolved["land_url"]


def _save_pdf(store: CollectionStore, article: dict[str, Any], pdf: bytes, url: str) -> None:
    path = store.pdf_path(article["article_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf)
    rel = str(path.relative_to(store.article_dir(article["article_id"])))
    article_mod.record_pdf(article, rel, "wiley_tdm" if "wiley.com" in (url or "") else "open")
    if url and url.startswith("http"):
        article.setdefault("links", {}).setdefault("publisher", {})["pdf"] = url


def fetch_json_open(store: CollectionStore, article: dict[str, Any], defer_pdf: bool = False) -> tuple[dict[str, Any] | None, str]:
    """Fetch structured full text via open sources. Returns (updated_article|None, reason).

    defer_pdf: only the sources that return structured text are tried; when they all fail the PDF is
    downloaded and saved (status.fulltext = pdf_pending) for the `parse` command, instead of being parsed
    here. Splits the network-bound fetch from the CPU/GPU-bound Docling parse so each can be scaled alone.
    """
    flat, warning = assemble_mod.flatten_article(article)
    sources = fulltext_sources.STRUCTURED_SOURCES if defer_pdf else None
    doc, reason = fulltext_sources.get_fulltext(flat, sources=sources)
    if doc is None:
        if not defer_pdf:
            return None, "; ".join(x for x in (warning, reason) if x)
        resolved, _why = fulltext_sources.resolve_identifiers(flat)
        pdf, url = fulltext_sources.download_pdf(flat)
        if not pdf:
            return None, "; ".join(x for x in (warning, reason, url or "pdf_download_failed") if x)
        _save_pdf(store, article, pdf, url)
        article_mod.mark_fulltext_pending(article)
        _write_back_resolved(article, resolved)
        links_mod.mark_sensitive_links(article)
        return article, "pdf_saved_for_parse"
    matches, mismatch_reason = assemble_mod.doc_matches_article(article, doc)
    if not matches:
        return None, "; ".join(x for x in (warning, mismatch_reason) if x)
    if warning:
        article.setdefault("identifiers", {})["pmcid"] = ""
        article.setdefault("links", {}).setdefault("pmc", {}).pop("page", None)
        article.setdefault("links", {}).setdefault("pmc", {}).pop("pdf", None)
    updated = assemble_mod.assemble_from_doc(article, doc)
    _write_back_resolved(updated, (doc.get("provenance") or {}).get("resolved_identifiers") or {})
    return updated, warning


def fetch_pdf_open(store: CollectionStore, article: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Download and save a PDF via open sources. Returns (updated_article|None, reason)."""
    flat, warning = assemble_mod.flatten_article(article)
    pdf, url = fulltext_sources.download_pdf(flat)
    if not pdf:
        # download_pdf returns its reason (no_mirror, unpaywall_404, landing_unreachable, ...) in the url slot
        return None, "; ".join(x for x in (warning, url or "pdf_download_failed") if x)
    _save_pdf(store, article, pdf, url)
    links_mod.mark_sensitive_links(article)
    return article, ""
