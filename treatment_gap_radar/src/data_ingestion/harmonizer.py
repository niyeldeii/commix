"""
DataHarmonizer: normalises column names, values, and data types across all
loaded datasets so downstream analysis sees a consistent schema.

Output schema (canonical column names):
  organism    – species name (str)
  drug        – antimicrobial agent (str)
  drug_class  – antibiotic class (str)
  mic         – minimum inhibitory concentration (float, mg/L)
  interpret   – susceptibility category: S / I / R (str)
  country     – country name (str)
  region      – WHO region (str)
  year        – collection year (int)
  age_group   – Pediatric / Adult / Elderly (str)
  specimen    – specimen source (str)
  dataset     – source dataset name (str)
  is_resistant– bool (True if interpret == 'R')
  is_pediatric– bool (True if age_group == 'Pediatric')
"""

import pandas as pd
import numpy as np
import logging
from config import COLUMN_ALIASES, PRIORITY_PATHOGENS, ANALYSIS_YEARS

logger = logging.getLogger(__name__)


COUNTRY_TO_REGION = {
    # Africa
    "Nigeria": "Africa", "South Africa": "Africa", "Kenya": "Africa",
    "Egypt": "Africa", "Ghana": "Africa", "Ethiopia": "Africa",
    "Tanzania": "Africa", "Uganda": "Africa", "Cameroon": "Africa",
    "Morocco": "Africa", "Tunisia": "Africa", "Algeria": "Africa",
    # Americas
    "USA": "Americas", "United States": "Americas", "Brazil": "Americas",
    "Mexico": "Americas", "Colombia": "Americas", "Argentina": "Americas",
    "Canada": "Americas", "Peru": "Americas", "Venezuela": "Americas",
    "Chile": "Americas",
    # South-East Asia
    "India": "South-East Asia", "Thailand": "South-East Asia",
    "Indonesia": "South-East Asia", "Bangladesh": "South-East Asia",
    "Myanmar": "South-East Asia", "Sri Lanka": "South-East Asia",
    "Nepal": "South-East Asia",
    # Europe
    "Germany": "Europe", "France": "Europe", "UK": "Europe",
    "United Kingdom": "Europe", "Italy": "Europe", "Spain": "Europe",
    "Poland": "Europe", "Netherlands": "Europe", "Sweden": "Europe",
    "Turkey": "Europe", "Russia": "Europe", "Greece": "Europe",
    # Eastern Mediterranean
    "Iran": "Eastern Mediterranean", "Pakistan": "Eastern Mediterranean",
    "Saudi Arabia": "Eastern Mediterranean", "Iraq": "Eastern Mediterranean",
    "Jordan": "Eastern Mediterranean", "Lebanon": "Eastern Mediterranean",
    "Afghanistan": "Eastern Mediterranean",
    # Western Pacific
    "China": "Western Pacific", "Japan": "Western Pacific",
    "South Korea": "Western Pacific", "Australia": "Western Pacific",
    "Philippines": "Western Pacific", "Vietnam": "Western Pacific",
    "Malaysia": "Western Pacific", "Taiwan": "Western Pacific",
}

PATHOGEN_ALIASES = {
    "A. baumannii": "Acinetobacter baumannii",
    "Acinetobacter baumannii-calcoaceticus complex": "Acinetobacter baumannii",
    "P. aeruginosa": "Pseudomonas aeruginosa",
    "K. pneumoniae": "Klebsiella pneumoniae",
    "E. coli": "Escherichia coli",
    "E. cloacae": "Enterobacter cloacae",
}


class DataHarmonizer:
    def __init__(self, filter_priority: bool = False):
        """
        filter_priority: if True, keep only PRIORITY_PATHOGENS rows.
        """
        self.filter_priority = filter_priority

    def harmonize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self._rename_columns(df)
        df = self._ensure_columns(df)
        df = self._clean_organism(df)
        df = self._clean_drug(df)
        df = self._clean_interpret(df)
        df = self._clean_mic(df)
        df = self._clean_year(df)
        df = self._clean_age_group(df)
        df = self._assign_region(df)
        df = self._derive_flags(df)

        if self.filter_priority:
            before = len(df)
            df = df[df["organism"].isin(PRIORITY_PATHOGENS)]
            logger.info(f"Priority filter: {before} → {len(df)} rows")

        df = df[df["year"].isin(ANALYSIS_YEARS)]
        df = df.dropna(subset=["organism", "drug", "country", "year"])
        df = df.reset_index(drop=True)
        logger.info(f"Harmonized dataset: {len(df)} rows, "
                    f"{df['organism'].nunique()} pathogens, "
                    f"{df['drug'].nunique()} drugs, "
                    f"{df['country'].nunique()} countries")
        return df

    # ------------------------------------------------------------------

    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map dataset-specific column names to canonical names."""
        rename_map = {}
        existing = set(df.columns)
        for canonical, aliases in COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in existing and canonical not in existing:
                    rename_map[alias] = canonical
                    break
        return df.rename(columns=rename_map)

    def _ensure_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in ["organism", "drug", "mic", "interpret", "country",
                    "year", "age_group", "drug_class", "specimen", "dataset"]:
            if col not in df.columns:
                df[col] = np.nan
        return df

    def _clean_organism(self, df: pd.DataFrame) -> pd.DataFrame:
        df["organism"] = (
            df["organism"].astype(str).str.strip()
            .replace(PATHOGEN_ALIASES)
        )
        df.loc[df["organism"].isin(["nan", "", "None"]), "organism"] = np.nan
        return df

    def _clean_drug(self, df: pd.DataFrame) -> pd.DataFrame:
        df["drug"] = df["drug"].astype(str).str.strip()
        df.loc[df["drug"].isin(["nan", "", "None"]), "drug"] = np.nan
        return df

    def _clean_interpret(self, df: pd.DataFrame) -> pd.DataFrame:
        mapping = {
            "S": "S", "Susceptible": "S", "susceptible": "S",
            "I": "I", "Intermediate": "I", "intermediate": "I",
            "NS": "R",  # Non-susceptible → resistant for analysis
            "R": "R", "Resistant": "R", "resistant": "R",
        }
        df["interpret"] = df["interpret"].astype(str).str.strip().map(mapping)
        return df

    def _clean_mic(self, df: pd.DataFrame) -> pd.DataFrame:
        def parse_mic(v):
            if pd.isna(v):
                return np.nan
            s = str(v).strip().replace(">", "").replace("<", "").replace("=", "")
            # Handle ranges like "0.5/1"
            if "/" in s:
                s = s.split("/")[0]
            try:
                return float(s)
            except ValueError:
                return np.nan

        df["mic"] = df["mic"].apply(parse_mic)
        df.loc[df["mic"] <= 0, "mic"] = np.nan
        return df

    def _clean_year(self, df: pd.DataFrame) -> pd.DataFrame:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        return df

    def _clean_age_group(self, df: pd.DataFrame) -> pd.DataFrame:
        def normalise_age(v):
            if pd.isna(v):
                return "Unknown"
            s = str(v).lower()
            if any(x in s for x in ["ped", "child", "infant", "neo", "<18", "0-17"]):
                return "Pediatric"
            if any(x in s for x in ["elder", "old", "senior", ">65", ">=65"]):
                return "Elderly"
            return "Adult"

        df["age_group"] = df["age_group"].apply(normalise_age)
        return df

    def _assign_region(self, df: pd.DataFrame) -> pd.DataFrame:
        df["region"] = df["country"].map(COUNTRY_TO_REGION).fillna("Unknown")
        return df

    def _derive_flags(self, df: pd.DataFrame) -> pd.DataFrame:
        df["is_resistant"] = df["interpret"] == "R"
        df["is_pediatric"] = df["age_group"] == "Pediatric"
        return df
