"""Shared helpers for Statistics Canada WDS full-table connectors (docs/10 §2.1).

Every StatCan cube can be pulled as a whole-table CSV via the WDS method
`getFullTableDownloadCSV/{productId}/en`, which returns the URL of a zip holding
the full cube as CSV. That's robust to vector-id / coordinate churn: we download
the cube once and filter to the rows we keep. Each connector then vendors a slim,
already-filtered CSV as its fixture so default (offline) runs are deterministic.
"""
from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.request
import zipfile

# Transient upstream statuses worth retrying (StatCan WDS occasionally 503s under
# load, especially when several full tables are pulled back-to-back).
_RETRY_STATUS = {429, 500, 502, 503, 504}


def wds_full_csv_url(product_id: str) -> str:
    return f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{product_id}/en"


def _urlopen_retry(url: str, timeout: int, retries: int = 2, backoff: float = 2.0) -> bytes:
    """Open `url` and return its bytes, retrying transient errors with backoff.

    Kept deliberately short (few retries, modest timeouts) so a slow/stalling
    upstream fails fast and the loader degrades to the vendored fixture rather
    than burning the whole job's time budget — across several full-table
    connectors the worst case must stay well under the workflow timeout.
    """
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
                return resp.read()
        except urllib.error.HTTPError as e:  # noqa: PERF203
            last = e
            if e.code not in _RETRY_STATUS:
                raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        if attempt < retries - 1:
            time.sleep(backoff * (2 ** attempt))
    assert last is not None
    raise last


def fetch_full_table_csv(product_id: str) -> str:
    """Return the full cube as CSV text (the real upstream; used only with --live)."""
    meta = json.loads(_urlopen_retry(wds_full_csv_url(product_id), timeout=30).decode("utf-8"))
    zbytes = _urlopen_retry(meta["object"], timeout=90)
    with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
        data_name = next(
            n for n in zf.namelist()
            if n.lower().endswith(".csv") and "metadata" not in n.lower()
        )
        return zf.read(data_name).decode("utf-8-sig")


def col(row: dict, *candidates: str) -> str:
    """Fetch a column value tolerantly (exact, then case-insensitive)."""
    for c in candidates:
        if c in row:
            return row[c]
    lower = {k.lower(): v for k, v in row.items()}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return ""


def find_field(fields: list[str], *hints: str) -> str:
    """Return the first header whose lowercased name contains any hint, else ''."""
    for f in fields:
        fl = f.lower()
        if any(h in fl for h in hints):
            return f
    return ""


def is_age_65plus(age: str) -> bool:
    """True for the aggregate '65 years and over/older' member, not 65-69 / 65-74 bands."""
    a = age.strip().lower()
    if a in {"65 years and over", "65 years and older", "65 years and over (1)"}:
        return True
    return "65" in a and ("over" in a or "older" in a) and "to" not in a and "-" not in a


def map_geo(geo: str) -> str | None:
    """Map a StatCan GEO member to our jurisdiction code, tolerating the CCHS
    national label 'Canada (excluding territories)' as well as plain 'Canada'."""
    g = geo.strip()
    if g.startswith("Canada"):
        return "CA"
    if g == "Nova Scotia":
        return "CA-NS"
    return None


def is_total_gender(g: str) -> bool:
    return g.strip().lower() in {
        "total - gender", "both sexes", "total - sex", "total, gender",
        "all genders", "both genders", "",
    }


def inspect_dump(text: str, dim_hints: dict[str, tuple[str, ...]], geo_name: str = "Canada") -> str:
    """Human-readable schema dump for `hapi inspect`: headers, detected dimension
    columns, their distinct members, and a few sample rows for one geography."""
    reader = csv.DictReader(io.StringIO(text))
    fields = reader.fieldnames or []
    detected = {label: find_field(fields, *hints) for label, hints in dim_hints.items()}
    members: dict[str, set[str]] = {label: set() for label in detected}
    samples: list[dict] = []
    geos: set[str] = set()
    for row in reader:
        geos.add(col(row, "GEO"))
        for label, fld in detected.items():
            if fld:
                members[label].add(row.get(fld, ""))
        if col(row, "GEO") == geo_name and len(samples) < 3:
            samples.append({k: row.get(k) for k in fields})
    lines = [f"headers: {fields}", f"detected columns: {detected}",
             f"GEO has Canada={'Canada' in geos}, Nova Scotia={'Nova Scotia' in geos}"]
    for label, vals in members.items():
        shown = sorted(v for v in vals if v)[:25]
        lines.append(f"{label} members (<=25): {shown}")
    lines.append(f"sample {geo_name} rows: {samples}")
    return "\n".join(lines)
