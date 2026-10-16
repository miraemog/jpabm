"""jpabm - a small agent-based model of Japan's demographics, economy and public finances,
calibrated to and validated against the IPSS 2023 national projections."""
from .model import Params, run, run_many, band, with_, REGIONS
from . import data

__version__ = "0.2.0"
__all__ = ["Params", "run", "run_many", "band", "with_", "REGIONS", "data"]
