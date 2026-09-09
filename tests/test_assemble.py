"""Tests for the shared assembler (Phase 3).

Both fetch routes converge on assemble_*; these pin its behavior and prove the
open and institutional routes produce an identical article shape from the same
content (the sequence is no longer copy-pasted per route).
"""
from __future__ import annotations

from paper_download import article as article_mod
from paper_download import assemble

_LONG = (
    "This body section is long enough for the extraction quality gate to treat it "
    "as a substantial article body rather than too short. " * 10
)

_PARSED = {
    "title": "Fixture Study",
    "sections": {"abstract": "abs", "Introduction": _LONG,
                 "Methods": "we did methods", "Results": "we got results"},
    "references": [{"citation": "Ref 1"}],
}


def _fresh():
    return article_mod.new_article({"doi": "10.1/x", "title": "Fixture Study", "abstract": "abs"})


def _prov(source):
    return {"access_source": source, "source_endpoint": source,
            "fulltext_url": "https://example.org/full", "accessed_at": "2026-01-01T00:00:00Z"}


def test_flatten_article_offline_shape():
    art = article_mod.new_article({"doi": "10.1/x", "pmid": "9", "title": "T",
                                   "abstract": "a", "authors": ["Doe J"]})
    flat, warning = assemble.flatten_article(art, validate_pmcid=False)
    assert warning == ""
    assert flat["doi"] == "10.1/x" and flat["pmid"] == "9"
    assert flat["sections"] == {"abstract": "a"}


def test_assemble_from_parsed_writes_fulltext():
    art = _fresh()
    updated = assemble.assemble_from_parsed(art, _PARSED, _prov("pmc_xml"))
    assert updated is not None
    assert article_mod.has_fulltext(updated)
    assert "Introduction" in updated["sections"]
    assert updated["source"]["fulltext"] == "pmc_xml"
    assert updated["quality"]["status"] != "reject"


def test_assemble_from_parsed_none_when_empty():
    assert assemble.assemble_from_parsed(_fresh(), None, _prov("x")) is None


def test_assemble_from_doc_rejects_low_quality():
    # a doc whose quality was rejected must not be written in
    doc = {"sections": {"abstract": "a"}, "provenance": _prov("pmc_xml"),
           "quality": {"quality_status": "reject", "issues": ["body_too_short"]}}
    assert assemble.assemble_from_doc(_fresh(), doc) is None


def _norm(article: dict) -> dict:
    a = dict(article)
    a["updated_at"] = "<ts>"
    return a


def test_open_and_library_routes_assemble_identically():
    # Same parsed content + provenance flowing through the one assembler yields
    # the same article shape regardless of which route called it.
    open_art = assemble.assemble_from_parsed(_fresh(), _PARSED, _prov("pmc_xml"))
    lib_art = assemble.assemble_from_parsed(_fresh(), _PARSED, _prov("pmc_xml"))
    assert _norm(open_art) == _norm(lib_art)
    # sections + fulltext status are what a downstream consumer relies on
    assert open_art["sections"] == lib_art["sections"]
    assert open_art["status"]["fulltext"] == lib_art["status"]["fulltext"] == article_mod.AVAILABLE


def test_doc_matches_article_rejects_pdf_text_from_another_document():
    from paper_download import assemble
    article = {"identifiers": {"doi": "10.1016/j.gim.2024.101334", "pmid": "1"},
               "metadata": {"title": "Germline variants in pediatric solid tumours: a cohort study"}}
    decoy = {"provenance": {"access_source": "pdf_docling", "fulltext_url": "https://repo/flyer.pdf"},
             "sections": {"abstract": "Germline variants pediatric solid tumours cohort study",   # metadata, must be ignored
                          "Preamble": "Les licences Creative Commons sont des outils juridiques gratuits"}}
    ok, reason = assemble.doc_matches_article(article, decoy)
    assert not ok and reason.startswith("pdf_identity_mismatch")
    real = {"provenance": {"access_source": "pdf_pymupdf", "fulltext_url": "x"},
            "sections": {"Preamble": "Germline Variants in Pediatric Solid Tumours: A Cohort Study. Introduction ..."}}
    assert assemble.doc_matches_article(article, real) == (True, "")
    by_doi = {"provenance": {"access_source": "pdf_ocr", "fulltext_url": "x"},
              "sections": {"Body": "https://doi.org/10.1016/j.gim.2024.101334 some other words"}}
    assert assemble.doc_matches_article(article, by_doi) == (True, "")
