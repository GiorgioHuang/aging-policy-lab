"""Connector framework for the Data Hub (docs/05).

A connector knows three things:
  * the `DataSourceSpec` it pulls from (becomes a `datasource` row),
  * the `IndicatorSpec`(s) it populates (become `indicator` rows), and
  * how to turn a raw payload into canonical `ObservationRecord`s.

Extraction is split into `fetch_live()` (hit the real upstream) and a vendored
fixture under `fixtures/`. Default runs read the fixture so the pipeline is
deterministic and offline-reproducible; `--live` re-fetches and refreshes the
fixture. Idempotency is keyed on the SHA-256 of the payload bytes, so a re-run
with unchanged upstream data is a no-op regardless of mode (docs/05 §3-4).
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@dataclass(frozen=True)
class DataSourceSpec:
    """Mirrors the `datasource` table (docs/03 §2.5)."""

    name: str
    publisher: str
    url: str
    access_method: str  # api | csv | portal_download | web_scrape
    licence: str
    update_frequency: str
    notes: str = ""


@dataclass(frozen=True)
class IndicatorSpec:
    """Mirrors the `indicator` table (docs/03 §2.4)."""

    code: str
    domain: str
    name: str
    definition: str
    formula: str
    unit: str
    direction: str | None = None
    normalization: dict | None = None
    coverage: dict | None = None


@dataclass(frozen=True)
class ObservationRecord:
    """One measured value, pre-load (docs/03 §2.7). `value=None` means suppressed."""

    indicator_code: str
    jurisdiction_code: str
    period_start: str  # ISO date, inclusive
    period_end: str    # ISO date, inclusive
    value: float | None
    quality_flag: str = "ok"


@dataclass(frozen=True)
class RawPayload:
    content: bytes
    source_version: str  # publisher edition/release, or 'fixture:<name>' for vendored data
    content_type: str = ""

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    @property
    def is_fixture(self) -> bool:
        return self.source_version.startswith("fixture:")


class Connector(ABC):
    #: stable slug, also the CLI selector (e.g. 'statcan_wds')
    name: str
    #: filename under fixtures/
    fixture_name: str
    source: DataSourceSpec
    indicators: list[IndicatorSpec]

    @property
    def fixture_path(self) -> Path:
        return FIXTURES_DIR / self.fixture_name

    @abstractmethod
    def fetch_live(self) -> RawPayload:
        """Fetch the real upstream payload. Used only with --live."""

    @abstractmethod
    def parse(self, payload: RawPayload) -> list[ObservationRecord]:
        """Parse a raw payload into canonical observation records."""

    def inspect_live(self) -> str:
        """Fetch the real upstream and return a human-readable schema dump
        (column names, distinct dimension values, sample rows). Used by
        `hapi inspect` to confirm parsing assumptions against the real source."""
        return "(no live inspection implemented for this connector)"

    def extract(self, live: bool = False, capture: bool = True) -> RawPayload:
        """Return a payload from the live source or the vendored fixture.

        live=True   fetch from the real upstream; when capture=True also refresh
                    the vendored fixture (capture=False for dry runs).
        live=False  read the deterministic, offline fixture.
        """
        if live:
            payload = self.fetch_live()
            if capture:
                self.fixture_path.parent.mkdir(parents=True, exist_ok=True)
                self.fixture_path.write_bytes(payload.content)
            return payload
        content = self.fixture_path.read_bytes()
        return RawPayload(
            content=content,
            source_version=f"fixture:{self.fixture_name}",
            content_type="",
        )
