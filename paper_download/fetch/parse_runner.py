"""`parse`: turn saved article.pdf files into sections.

The counterpart of `fetch --defer-pdf-parse`: fetch saved the PDF and left status.fulltext = pdf_pending;
this command runs the PDF parse (Docling -> PyMuPDF -> OCR) on every article that has a PDF and no full text,
with no network access, so it can run on many nodes (or a GPU) at once while fetch stays within publisher
rate limits. Idempotent: articles with full text are skipped unless --force.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import article as article_mod
from .. import assemble as assemble_mod
from .. import links as links_mod
from ..collection import CollectionStore
from ..sources.fulltext import fulltext_fetcher, fulltext_sources
from ..time import utc_now


def parse_saved_pdf(store: CollectionStore, article: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Parse the article's saved PDF into sections. Returns (updated_article|None, reason)."""
    path = store.pdf_path(article["article_id"])
    if not path.exists():
        return None, "pdf_file_missing"
    parsed, tag = fulltext_sources.parse_pdf_3layer(path.read_bytes())
    if parsed is None:
        return None, tag
    flat, _ = assemble_mod.flatten_article(article, validate_pmcid=False)   # no network in this step
    prov = {"access_source": tag, "source_endpoint": f"saved_pdf:{(article.get('source') or {}).get('pdf', '')}",
            "fulltext_url": (article.get("links") or {}).get("publisher", {}).get("pdf", ""),
            "accessed_at": utc_now(), "license": "", "license_url": "", "reuse_class": ""}
    doc = fulltext_fetcher.build_doc(flat.get("pmcid") or "", parsed, flat, prov)
    updated = assemble_mod.assemble_from_doc(article, doc)
    if updated is None:
        return None, "quality_reject(" + ",".join(doc["quality"].get("issues") or []) + ")"
    links_mod.mark_sensitive_links(updated)
    return updated, ""


def run_parse(store: CollectionStore, *, ids: set[str] | None = None, limit: int | None = None, force: bool = False) -> Path:
    started = utc_now()
    articles = store.iter_articles()
    if ids is not None:
        articles = [a for a in articles if a["article_id"] in ids]
    if limit:
        articles = articles[:limit]

    def _needs(a: dict) -> bool:
        return article_mod.has_pdf(a) and (force or not article_mod.has_fulltext(a))

    todo = [a for a in articles if _needs(a)]
    print(f"Parsing: {len(todo)} to parse, {len(articles) - len(todo)} skipped (no pdf or already parsed)", flush=True)
    items: list[dict[str, Any]] = []
    succeeded = failed = 0
    width = len(str(len(todo) or 1))
    for i, article in enumerate(todo, 1):
        updated, reason = parse_saved_pdf(store, article)
        if updated is None:
            failed += 1
            article_mod.reset_fulltext(article)
            store.write_article(article)
            status = "failed"
        else:
            succeeded += 1
            store.write_article(updated)
            status = "succeeded"
        items.append({"article_id": article["article_id"], "status": status,
                      "attempts": [{"access": "parse", "artifact": "json", "status": status, "reason": reason}]})
        print(f"  [{i:>{width}}/{len(todo)}] {status:9s} ok={succeeded} fail={failed}  {article['article_id']}", flush=True)
    for a in articles:
        if not _needs(a):
            items.append({"article_id": a["article_id"], "status": "skipped", "attempts": []})
    print(f"Done. ok={succeeded} fail={failed} / {len(todo)} parsed.", flush=True)
    refreshed = store.iter_articles()
    store.write_articles_csv(refreshed)
    store.update_stats(refreshed)
    return store.write_log("parse", {"limit": limit, "force": force, "ids": sorted(ids) if ids is not None else None},
                           {"total": len(articles), "succeeded": succeeded, "failed": failed,
                            "skipped": len(articles) - len(todo)}, items, started)
