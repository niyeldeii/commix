"""
R&D Attention Index (RDAI)

Quantifies how much global R&D attention is directed at each (organism, drug)
combination using data from the Global AMR R&D Hub.

Sub-indicators:
  1. investment_score  – total USD investment normalised to [0, 1]
  2. pipeline_score    – number of active pipeline candidates (Phase I–III)
  3. surveillance_score– number of active surveillance programmes

Expected input file: data/rd_hub/rd_hub_data.csv
Columns: organism, drug, drug_class, investment_usd, pipeline_count,
         surveillance_count, year (optional)

A synthetic sample is auto-generated when the file is absent.
"""

import os
import pandas as pd
import numpy as np
import logging
from config import RDAI_WEIGHTS, RD_HUB_DIR

logger = logging.getLogger(__name__)

RD_HUB_FILE = os.path.join(RD_HUB_DIR, "rd_hub_data.csv")


class RDAttentionIndex:

    def __init__(self, weights: dict = None, rd_hub_path: str = None):
        self.weights = weights or RDAI_WEIGHTS
        assert abs(sum(self.weights.values()) - 1.0) < 1e-6, \
            "RDAI weights must sum to 1.0"
        self.rd_hub_path = rd_hub_path or RD_HUB_FILE

    # ------------------------------------------------------------------

    def compute(self, organisms: list = None, drugs: list = None) -> pd.DataFrame:
        """
        Returns a DataFrame indexed by (organism, drug) with columns:
          investment_score, pipeline_score, surveillance_score, RDAI
        """
        hub = self._load_hub_data()
        if organisms:
            hub = hub[hub["organism"].isin(organisms)]
        if drugs:
            hub = hub[hub["drug"].isin(drugs)]

        hub = self._normalise(hub)

        hub["RDAI"] = sum(
            hub[col] * self.weights[col]
            for col in self.weights
        )
        hub = hub.sort_values("RDAI", ascending=False).reset_index(drop=True)
        logger.info(f"RDAI computed for {len(hub)} (organism, drug) combinations.")
        return hub

    # ------------------------------------------------------------------

    def _load_hub_data(self) -> pd.DataFrame:
        if os.path.exists(self.rd_hub_path):
            df = pd.read_csv(self.rd_hub_path)
            logger.info(f"Loaded R&D Hub data: {len(df)} rows")
            return df
        logger.warning("R&D Hub data file not found — using synthetic sample.")
        return self._synthetic_hub()

    def _normalise(self, df: pd.DataFrame) -> pd.DataFrame:
        for col, target in [
            ("investment_usd",        "investment_score"),
            ("pipeline_count",        "pipeline_score"),
            ("surveillance_count",    "surveillance_score"),
        ]:
            if col in df.columns:
                max_val = df[col].max()
                df[target] = (df[col] / max_val).clip(0, 1) if max_val > 0 else 0.0
            else:
                df[target] = 0.0
        return df

    def _synthetic_hub(self) -> pd.DataFrame:
        """
        Synthetic Global AMR R&D Hub data reflecting approximate real-world
        investment asymmetries (well-funded vs. neglected pathogens).
        """
        rng = np.random.default_rng(seed=99)

        rows = [
            # (organism, drug, investment_usd, pipeline_count, surveillance_count)
            # High attention
            ("Mycobacterium tuberculosis",   "Bedaquiline",             180_000_000, 12, 8),
            ("Klebsiella pneumoniae",        "Ceftazidime/Avibactam",   120_000_000,  8, 6),
            ("Pseudomonas aeruginosa",       "Ceftolozane/Tazobactam",   95_000_000,  7, 5),
            ("Acinetobacter baumannii",      "Sulbactam/Durlobactam",    85_000_000,  6, 4),
            ("Klebsiella pneumoniae",        "Meropenem/Vaborbactam",    80_000_000,  6, 5),
            ("Escherichia coli",             "Ceftazidime/Avibactam",    75_000_000,  5, 6),
            # Medium attention
            ("Pseudomonas aeruginosa",       "Aztreonam/Avibactam",      55_000_000,  5, 4),
            ("Acinetobacter baumannii",      "Cefiderocol",              50_000_000,  4, 3),
            ("Klebsiella pneumoniae",        "Cefiderocol",              48_000_000,  4, 4),
            ("Escherichia coli",             "Meropenem",                40_000_000,  3, 5),
            ("Enterobacter cloacae",         "Ceftazidime/Avibactam",    38_000_000,  3, 3),
            ("Haemophilus influenzae",       "Amoxicillin/Clavulanate",  30_000_000,  2, 4),
            # Low attention
            ("Acinetobacter baumannii",      "Colistin",                 15_000_000,  2, 2),
            ("Pseudomonas aeruginosa",       "Colistin",                 14_000_000,  2, 2),
            ("Klebsiella pneumoniae",        "Colistin",                 12_000_000,  1, 2),
            ("Stenotrophomonas maltophilia", "Trimethoprim/Sulfamethoxazole",
                                                                          10_000_000,  1, 1),
            ("Neisseria gonorrhoeae",        "Ceftriaxone",               9_000_000,  1, 3),
            ("Enterobacter cloacae",         "Colistin",                  8_000_000,  1, 1),
            # Neglected
            ("Stenotrophomonas maltophilia", "Cefiderocol",               5_000_000,  1, 1),
            ("Neisseria gonorrhoeae",        "Azithromycin",              4_000_000,  0, 2),
            ("Acinetobacter baumannii",      "Meropenem",                 3_000_000,  0, 1),
            ("Klebsiella pneumoniae",        "Ciprofloxacin",             3_000_000,  0, 2),
            ("Pseudomonas aeruginosa",       "Ciprofloxacin",             2_500_000,  0, 1),
            ("Escherichia coli",             "Ciprofloxacin",             2_000_000,  0, 2),
        ]

        df = pd.DataFrame(rows, columns=[
            "organism", "drug", "investment_usd",
            "pipeline_count", "surveillance_count"
        ])
        # Add jitter
        df["investment_usd"] = (df["investment_usd"]
                                 * rng.uniform(0.9, 1.1, len(df))).astype(int)
        df["drug_class"] = df["drug"].map({
            "Bedaquiline": "Diarylquinolines",
            "Ceftazidime/Avibactam": "Beta-lactam/beta-lactamase inhibitor combinations",
            "Ceftolozane/Tazobactam": "Beta-lactam/beta-lactamase inhibitor combinations",
            "Sulbactam/Durlobactam": "Beta-lactam/beta-lactamase inhibitor combinations",
            "Meropenem/Vaborbactam": "Beta-lactam/beta-lactamase inhibitor combinations",
            "Aztreonam/Avibactam": "Beta-lactam/beta-lactamase inhibitor combinations",
            "Cefiderocol": "Cephalosporins",
            "Meropenem": "Carbapenems",
            "Colistin": "Polymyxins",
            "Ciprofloxacin": "Fluoroquinolones",
            "Amoxicillin/Clavulanate": "Beta-lactam/beta-lactamase inhibitor combinations",
            "Ceftriaxone": "Cephalosporins",
            "Trimethoprim/Sulfamethoxazole": "Folate pathway inhibitors",
            "Azithromycin": "Macrolides",
        }).fillna("Other")
        return df
