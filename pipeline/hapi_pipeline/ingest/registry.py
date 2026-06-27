"""Registry of available connectors. Adding a source = add a connector here."""
from __future__ import annotations

from .base import Connector
from .cihi_caregiver_distress import CIHICaregiverDistressConnector
from .cihi_irrs import CIHIIRRSConnector
from .ns_open_data import NSOpenDataConnector
from .statcan_cchs import StatCanCCHSConnector
from .statcan_functional_health import StatCanFunctionalHealthConnector
from .statcan_internet_use import StatCanInternetUseConnector
from .statcan_life_expectancy import StatCanLifeExpectancyConnector
from .statcan_low_income import StatCanLowIncomeConnector
from .statcan_wds import StatCanWDSConnector

CONNECTORS: list[Connector] = [
    StatCanWDSConnector(),
    NSOpenDataConnector(),
    CIHIIRRSConnector(),
    CIHICaregiverDistressConnector(),
    StatCanLowIncomeConnector(),
    StatCanInternetUseConnector(),
    StatCanLifeExpectancyConnector(),
    StatCanCCHSConnector(),
    StatCanFunctionalHealthConnector(),
]


def all_connectors() -> list[Connector]:
    return CONNECTORS


def get_connector(name: str) -> Connector:
    for c in CONNECTORS:
        if c.name == name:
            return c
    names = ", ".join(c.name for c in CONNECTORS)
    raise KeyError(f"unknown connector '{name}'. Available: {names}")
