"""StatCan connector — population 65+ denominators (Table 17-10-0005).

VERIFIED 2026-06 (WebSearch; direct fetch blocked in this sandbox):
  * Table 17-10-0005 "Population estimates on July 1, by age and gender",
    Canada + provinces/territories. productId = 17100005.
  * Robust access is the **full-table CSV**: the WDS method
    getFullTableDownloadCSV/{productId}/en returns the URL of a zip
    (https://www150.statcan.gc.ca/n1/tbl/csv/17100005-eng.zip) containing the
    whole cube as CSV. We download it, then filter to the rows we need — no
    fragile vector IDs/coordinates required (docs/10 §2.1).

Population 65+ is demographic *reference data* (domain='demography'), not a HAPI
outcome; it anchors the per-capita denominators used by Care Access indicators in
Phase 3, and is stored with the same lineage/versioning as everything else.

TO CONFIRM on first --live run: the gender member label changed across vintages
("Both sexes" -> "Total - gender"); the parser accepts both.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
import zipfile

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

PRODUCT_ID = "17100005"
WDS_FULL_CSV = (
    f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{PRODUCT_ID}/en"
)

GEO_TO_JURISDICTION = {"Canada": "CA", "Nova Scotia": "CA-NS"}
AGE_TARGET = "65 years and over"
GENDER_TARGETS = {"total - gender", "both sexes", "total - sex"}
MIN_YEAR = 2019


def _col(row: dict, *candidates: str) -> str:
    for c in candidates:
        if c in row:
            return row[c]
    # case-insensitive fallback
    lower = {k.lower(): v for k, v in row.items()}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return ""


class StatCanWDSConnector(Connector):
    name = "statcan_wds"
    fixture_name = "statcan_population_65plus.csv"

    source = DataSourceSpec(
        name="Statistics Canada — Population estimates by age (Table 17-10-0005)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710000501",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="annual",
        notes="WDS getFullTableDownloadCSV(17100005); filtered to 65+ / total gender.",
    )

    indicators = [
        IndicatorSpec(
            code="demography.population_65plus",
            domain="demography",
            name="Population aged 65 and over",
            definition="Estimated number of persons aged 65 and over as of July 1.",
            formula="StatCan Table 17-10-0005, age='65 years and over', total gender.",
            unit="persons",
            direction=None,  # a denominator, not directional
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": MIN_YEAR},
        )
    ]

    def fetch_live(self) -> RawPayload:
        # 1) ask WDS for the CSV zip URL
        with urllib.request.urlopen(WDS_FULL_CSV, timeout=60) as resp:  # noqa: S310
            meta = json.loads(resp.read().decode("utf-8"))
        zip_url = meta["object"]
        # 2) download + unzip the cube CSV
        with urllib.request.urlopen(zip_url, timeout=180) as resp:  # noqa: S310
            zbytes = resp.read()
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            data_name = next(
                n for n in zf.namelist()
                if n.lower().endswith(".csv") and "metadata" not in n.lower()
            )
            full_csv = zf.read(data_name).decode("utf-8-sig")
        # 3) filter to the rows we keep, to vendor a small payload
        kept = self._filter_csv(full_csv)
        return RawPayload(content=kept.encode("utf-8"),
                          source_version=f"WDS:getFullTableDownloadCSV/{PRODUCT_ID}",
                          content_type="text/csv")

    @staticmethod
    def _filter_csv(text: str) -> str:
        reader = csv.DictReader(io.StringIO(text))
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["REF_DATE", "GEO", "Age group", "Gender", "VALUE", "STATUS"])
        for row in reader:
            geo = _col(row, "GEO")
            age = _col(row, "Age group", "Age group at July 1")
            gender = _col(row, "Gender", "Sex")
            if geo not in GEO_TO_JURISDICTION:
                continue
            if age.strip() != AGE_TARGET:
                continue
            if gender.strip().lower() not in GENDER_TARGETS:
                continue
            writer.writerow([
                _col(row, "REF_DATE"), geo, age, gender,
                _col(row, "VALUE"), _col(row, "STATUS"),
            ])
        return out.getvalue()

    def _raw_csv(self) -> str:
        with urllib.request.urlopen(WDS_FULL_CSV, timeout=60) as resp:  # noqa: S310
            meta = json.loads(resp.read().decode("utf-8"))
        with urllib.request.urlopen(meta["object"], timeout=180) as resp:  # noqa: S310
            zbytes = resp.read()
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            data_name = next(
                n for n in zf.namelist()
                if n.lower().endswith(".csv") and "metadata" not in n.lower()
            )
            return zf.read(data_name).decode("utf-8-sig")

    def inspect_live(self) -> str:
        reader = csv.DictReader(io.StringIO(self._raw_csv()))
        fields = reader.fieldnames or []
        geos: set[str] = set()
        ages: set[str] = set()
        genders: set[str] = set()
        samples: list[str] = []
        age_field = "Age group" if "Age group" in fields else (
            "Age group at July 1" if "Age group at July 1" in fields else "")
        gender_field = "Gender" if "Gender" in fields else ("Sex" if "Sex" in fields else "")
        for row in reader:
            geos.add(_col(row, "GEO"))
            if age_field:
                ages.add(row.get(age_field, ""))
            if gender_field:
                genders.add(row.get(gender_field, ""))
            if _col(row, "GEO") == "Canada" and len(samples) < 3:
                samples.append({k: row.get(k) for k in fields})  # type: ignore[arg-type]
        age_65 = sorted(a for a in ages if "65" in a)
        return (
            f"headers: {fields}\n"
            f"age column: {age_field!r}; gender column: {gender_field!r}\n"
            f"GEO has Canada={'Canada' in geos}, Nova Scotia={'Nova Scotia' in geos}\n"
            f"age values containing '65': {age_65}\n"
            f"gender values: {sorted(genders)}\n"
            f"sample Canada rows: {samples}"
        )

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        reader = csv.DictReader(io.StringIO(payload.content.decode("utf-8-sig")))
        records: list[ObservationRecord] = []
        for row in reader:
            geo = _col(row, "GEO")
            jcode = GEO_TO_JURISDICTION.get(geo)
            if jcode is None:
                continue
            year = _col(row, "REF_DATE")[:4]
            if not year or int(year) < MIN_YEAR:
                continue
            raw = _col(row, "VALUE").strip()
            status = _col(row, "STATUS").strip().upper()
            suppressed = raw == "" or status in ("F", "X", "..", "...")
            records.append(
                ObservationRecord(
                    indicator_code="demography.population_65plus",
                    jurisdiction_code=jcode,
                    period_start=f"{year}-01-01",
                    period_end=f"{year}-12-31",
                    value=None if suppressed else float(raw),
                    quality_flag="suppressed" if suppressed else "ok",
                )
            )
        return records
