"""Registry of available connectors. Adding a source = add a connector here."""
from __future__ import annotations

from .base import Connector
from .cihi_caregiver_distress import CIHICaregiverDistressConnector
from .cihi_ccrs_ltc import CIHICCRSLTCConnector
from .cihi_ltc_beds import CIHILTCBedsConnector
from .ns_ltc_facilities import NSLTCFacilitiesConnector
from .ns_ltc_waitlist import NSLTCWaitlistConnector
from .ns_open_data import NSOpenDataConnector
from .statcan_cchs import StatCanCCHSConnector
from .statcan_functional_health import StatCanFunctionalHealthConnector
from .statcan_internet_use import StatCanInternetUseConnector
from .statcan_life_expectancy import StatCanLifeExpectancyConnector
from .statcan_low_income import StatCanLowIncomeConnector
from .statcan_ltc_employment import StatCanLTCEmploymentConnector
from .statcan_wds import StatCanWDSConnector

# CIHI home-care client counts (cihi_irrs) were retired: CIHI's HCRS/IRRS Quick
# Stats exclude Nova Scotia entirely (NS does not submit), so they cannot back an
# NS Care-Access indicator. The NS LTC Waitlist (Socrata, live) replaces it.
CONNECTORS: list[Connector] = [
    StatCanWDSConnector(),
    NSOpenDataConnector(),
    NSLTCWaitlistConnector(),
    NSLTCFacilitiesConnector(),
    CIHICaregiverDistressConnector(),
    CIHILTCBedsConnector(),
    CIHICCRSLTCConnector(),
    StatCanLowIncomeConnector(),
    StatCanInternetUseConnector(),
    StatCanLifeExpectancyConnector(),
    StatCanCCHSConnector(),
    StatCanFunctionalHealthConnector(),
    StatCanLTCEmploymentConnector(),
]


def all_connectors() -> list[Connector]:
    return CONNECTORS


def get_connector(name: str) -> Connector:
    for c in CONNECTORS:
        if c.name == name:
            return c
    names = ", ".join(c.name for c in CONNECTORS)
    raise KeyError(f"unknown connector '{name}'. Available: {names}")
