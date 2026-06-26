"""StatCan Web Data Service (WDS) connector — population 65+ denominators.

Real source: https://www.statcan.gc.ca/en/developers/wds (docs/10 §2.1). Public
aggregate data, no API key. We use `getDataFromVectorsAndLatestNPeriods`, whose
response is a list of series objects, one per requested vector.

Population 65+ is demographic *reference data* (domain='demography'), not a HAPI
outcome — it anchors the per-capita denominators used by Care Access indicators
in Phase 3. It is stored with the same lineage/versioning as everything else.

NOTE: the exact vector IDs for the 65+ series (Table 17-10-0005) must be verified
against the WDS before a `--live` run; the mapping below is illustrative and the
vendored fixture mirrors the real WDS response shape so `parse()` is identical for
both paths.
"""
from __future__ import annotations

import json
import urllib.request

from .base import Connector, DataSourceSpec, IndicatorSpec, ObservationRecord, RawPayload

WDS_ENDPOINT = (
    "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods"
)
LATEST_N = 5

# vectorId -> jurisdiction code (verify against WDS before going live).
VECTOR_TO_JURISDICTION: dict[int, str] = {1: "CA", 2: "CA-NS"}


class StatCanWDSConnector(Connector):
    name = "statcan_wds"
    fixture_name = "statcan_population_65plus.json"

    source = DataSourceSpec(
        name="Statistics Canada — Population estimates by age (Table 17-10-0005)",
        publisher="Statistics Canada",
        url="https://www150.statcan.gc.ca/t1/wds/rest/",
        access_method="api",
        licence="Statistics Canada Open Licence",
        update_frequency="annual",
        notes="WDS getDataFromVectorsAndLatestNPeriods. Anchors per-capita denominators.",
    )

    indicators = [
        IndicatorSpec(
            code="demography.population_65plus",
            domain="demography",
            name="Population aged 65 and over",
            definition="Estimated number of persons aged 65 and over as of July 1.",
            formula="StatCan population estimate, age group 65+ (count).",
            unit="persons",
            direction=None,  # a denominator, not directional
            coverage={"jurisdictions": ["CA", "CA-NS"], "from": 2019},
        )
    ]

    def fetch_live(self) -> RawPayload:
        body = json.dumps(
            [{"vectorId": v, "latestN": LATEST_N} for v in VECTOR_TO_JURISDICTION]
        ).encode()
        req = urllib.request.Request(
            WDS_ENDPOINT, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (trusted gov endpoint)
            content = resp.read()
        return RawPayload(
            content=content,
            source_version="WDS:getDataFromVectorsAndLatestNPeriods",
            content_type="application/json",
        )

    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        data = json.loads(payload.content.decode("utf-8"))
        records: list[ObservationRecord] = []
        for series in data:
            obj = series.get("object", {})
            jcode = VECTOR_TO_JURISDICTION.get(obj.get("vectorId"))
            if jcode is None:
                continue
            for dp in obj.get("vectorDataPoint", []):
                ref = dp.get("refPer", "")  # e.g. "2023-01-01"
                year = ref[:4]
                raw = dp.get("value")
                # WDS suppression/symbol: a null value (or symbolCode 1/2) -> suppressed
                suppressed = raw is None or dp.get("symbolCode") in (1, 2)
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
