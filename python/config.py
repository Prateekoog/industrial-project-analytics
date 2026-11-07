"""Central configuration: paths, random seed, key dates and business constants.

Every script imports from here, so a threshold or rate is defined exactly once.
Each constant references its entry in docs/ASSUMPTIONS.md.
"""
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_QA = ROOT / "data" / "qa"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
TABLES = REPORTS / "tables"
EXCEL_DIR = ROOT / "excel"
POWERBI_DIR = ROOT / "powerbi"

SEED = 42                                   # J05: reproducibility
DATA_START = dt.date(2021, 4, 1)            # B02: start of FY22
CUTOFF = dt.date(2026, 3, 31)               # B02: data cut-off, end of FY26

# Commercial terms
LD_RATE_PER_WEEK = 0.005                    # C08: 0.5% of contract value per week
LD_CAP = 0.05                               # C08: capped at 5%
PVC_PASS_THROUGH = 0.75                     # C04: share of steel price movement recovered from client

# Cost variance status thresholds, in % (H01)
CV_UNDER = -2.0
CV_WARNING = 5.0
CV_CRITICAL = 10.0

# Schedule delay status thresholds, delay as % of planned duration (H02)
DELAY_MINOR = 2.0
DELAY_MAJOR = 10.0
DELAY_CRITICAL = 20.0

# Labour (E03, E04)
OVERTIME_MULTIPLIER = 2.0
WORKS_STD_MH_PER_TONNE = 30.0               # F04: standard man-hours per fabricated tonne

# Finance (C12)
DISCOUNT_RATE = 0.12

# Presentation units (C01)
LAKH = 1e5
CRORE = 1e7
