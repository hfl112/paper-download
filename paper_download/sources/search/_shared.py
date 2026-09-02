"""Shared helpers for the search sources.

`retry_get` is the one exponential-backoff GET both fetchers use (Europe PMC
decodes it as JSON, PubMed keeps the raw bytes); `retry_post` is the same for a
form-encoded POST, which a long query needs (a several-thousand-character query
string makes the GET URL exceed the server limit and return 414); `doc_key` is
the one dedup key (normalized DOI, else PMID) shared by the fetchers and the
cross-source merge.
"""
from __future__ import annotations

import http.client
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict


def retry_get(url: str, user_agent: str, max_retries: int = 5) -> bytes:
    """GET with exponential backoff on 429/5xx and transient network errors.
    Returns the raw response bytes; raises on final failure."""
    return _retry(url, user_agent, max_retries, None)


def retry_post(url: str, user_agent: str, params: Dict[str, object],
               max_retries: int = 5) -> bytes:
    """Form-encoded POST with the same backoff as `retry_get`.

    A query of a few thousand characters exceeds the URL length Europe PMC
    accepts (HTTP 414), so the query goes in the body instead."""
    body = urllib.parse.urlencode(params).encode("utf-8")
    return _retry(url, user_agent, max_retries, body)


def _retry(url: str, user_agent: str, max_retries: int, body: bytes | None) -> bytes:
    headers = {"User-Agent": user_agent}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    delay = 1.0
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                print(f"  HTTP {e.code}，{delay:.0f}s 后重试 ({attempt + 1}/{max_retries})")
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                print(f"  网络错误 {e.reason}，{delay:.0f}s 后重试 ({attempt + 1}/{max_retries})")
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except (http.client.IncompleteRead, ConnectionError, TimeoutError) as e:
            if attempt < max_retries - 1:
                print(f"  读取中断 {type(e).__name__}，{delay:.0f}s 后重试 ({attempt + 1}/{max_retries})")
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("超过最大重试次数")


def doc_key(doc: Dict) -> str:
    """Dedup key for a search doc: normalized DOI, else PMID, else ''."""
    doi = (doc.get("doi") or "").lower().strip()
    if doi:
        return f"doi:{doi}"
    pmid = (doc.get("pmid") or "").strip()
    return f"pmid:{pmid}" if pmid else ""
