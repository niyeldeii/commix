"""
Dataset loaders for each Vivli AMR dataset.

Each loader reads the raw file (CSV/Excel) and returns a DataFrame with
at minimum the columns expected by the harmonizer:
  organism, drug, mic, interpret, country, year, age_group, drug_class,
  specimen, dataset

When real data files are placed in data/raw/, set the file path via the
DATASET_FILES mapping in config or pass it directly to each loader.
"""

import os
import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BaseLoader:
    """Abstract base for all dataset loaders."""

    dataset_name: str = "unknown"

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath

    def load(self) -> pd.DataFrame:
        if self.filepath and os.path.exists(self.filepath):
            df = self._read_file(self.filepath)
            df["dataset"] = self.dataset_name
            logger.info(f"Loaded {len(df)} rows from {self.dataset_name}")
            return df
        else:
            logger.warning(
                f"File not found for {self.dataset_name}: {self.filepath}. "
                "Returning synthetic sample data for pipeline testing."
            )
            return self._synthetic_sample()

    def _read_file(self, path: str) -> pd.DataFrame:
        ext = os.path.splitext(path)[-1].lower()
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(path)
        return pd.read_csv(path, low_memory=False)

    def _synthetic_sample(self) -> pd.DataFrame:
        raise NotImplementedError


def _base_synthetic(
    dataset_name: str,
    n: int = 500,
    organisms: Optional[list] = None,
    drugs: Optional[list] = None,
) -> pd.DataFrame:
    """Shared synthetic data generator used by all loaders for testing."""
    rng = np.random.default_rng(seed=42)

    if organisms is None:
        organisms = [
            "Klebsiella pneumoniae",
            "Escherichia coli",
            "Pseudomonas aeruginosa",
            "Acinetobacter baumannii",
        ]
    if drugs is None:
        drugs = ["Meropenem", "Ceftazidime", "Ciprofloxacin", "Colistin", "Aztreonam"]

    drug_class_map = {
        "Meropenem": "Carbapenems",
        "Imipenem": "Carbapenems",
        "Ceftazidime": "Cephalosporins",
        "Cefiderocol": "Cephalosporins",
        "Ciprofloxacin": "Fluoroquinolones",
        "Colistin": "Polymyxins",
        "Aztreonam": "Monobactams",
        "Omadacycline": "Tetracyclines",
        "Amikacin": "Aminoglycosides",
        "Gentamicin": "Aminoglycosides",
        "Ceftazidime/Avibactam": "Beta-lactam/beta-lactamase inhibitor combinations",
        "Meropenem/Vaborbactam": "Beta-lactam/beta-lactamase inhibitor combinations",
    }

    countries = [
        "USA", "China", "India", "Brazil", "Germany", "Nigeria",
        "South Africa", "Thailand", "France", "Japan", "Mexico", "Egypt",
    ]
    years = list(range(2010, 2024))
    age_groups = ["Adult", "Pediatric", "Elderly"]
    specimens = ["Blood", "Urine", "Respiratory", "Wound", "Other"]

    df = pd.DataFrame({
        "organism":   rng.choice(organisms, n),
        "drug":       rng.choice(drugs, n),
        "country":    rng.choice(countries, n),
        "year":       rng.choice(years, n),
        "age_group":  rng.choice(age_groups, n, p=[0.65, 0.20, 0.15]),
        "specimen":   rng.choice(specimens, n),
        "mic":        np.round(2 ** rng.uniform(-3, 6, n), 3),
        "dataset":    dataset_name,
    })

    # Map drug class
    df["drug_class"] = df["drug"].map(drug_class_map).fillna("Other")

    # Derive susceptibility: R if MIC >= breakpoint heuristic
    breakpoints = {"Meropenem": 8, "Ceftazidime": 16, "Ciprofloxacin": 2,
                   "Colistin": 4, "Aztreonam": 16, "Amikacin": 16,
                   "Gentamicin": 8, "Cefiderocol": 8}
    def interpret(row):
        bp = breakpoints.get(row["drug"], 8)
        if row["mic"] >= bp:
            return "R"
        elif row["mic"] >= bp / 4:
            return "I"
        return "S"

    df["interpret"] = df.apply(interpret, axis=1)
    return df


# ---------------------------------------------------------------------------
# Individual loaders — one per dataset
# ---------------------------------------------------------------------------

class AtlasAntibioticsLoader(BaseLoader):
    dataset_name = "ATLAS_Antibiotics"

    def _read_file(self, path: str) -> pd.DataFrame:
        df = super()._read_file(path)
        # ATLAS uses: Organism, Antibiotic, MIC, I/S/R, Country, Year, Age
        rename = {
            "Organism": "organism", "Antibiotic": "drug", "MIC": "mic",
            "I/S/R": "interpret", "Country": "country", "Year": "year",
            "Age Group": "age_group", "Antibiotic Class": "drug_class",
            "Specimen": "specimen",
        }
        return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    def _synthetic_sample(self) -> pd.DataFrame:
        return _base_synthetic(self.dataset_name, n=3000,
            drugs=["Meropenem", "Ceftazidime", "Ciprofloxacin", "Amikacin",
                   "Ceftazidime/Avibactam", "Colistin"])


class AtlasAntifungalsLoader(BaseLoader):
    dataset_name = "ATLAS_Antifungals"

    def _read_file(self, path: str) -> pd.DataFrame:
        df = super()._read_file(path)
        rename = {
            "Organism": "organism", "Antifungal": "drug", "MIC": "mic",
            "I/S/R": "interpret", "Country": "country", "Year": "year",
            "Age Group": "age_group", "Antifungal Class": "drug_class",
        }
        return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    def _synthetic_sample(self) -> pd.DataFrame:
        return _base_synthetic(self.dataset_name, n=800,
            organisms=["Candida albicans", "Candida glabrata",
                       "Aspergillus fumigatus", "Candida auris"],
            drugs=["Fluconazole", "Voriconazole", "Caspofungin", "Amphotericin B"])


class SoarLoader(BaseLoader):
    """Loader for SOAR (Study for Monitoring Antimicrobial Resistance Trends)."""

    def __init__(self, filepath: Optional[str] = None, dataset_name: str = "SOAR"):
        super().__init__(filepath)
        self.dataset_name = dataset_name

    def _read_file(self, path: str) -> pd.DataFrame:
        df = super()._read_file(path)
        rename = {
            "Species": "organism", "Agent": "drug", "MIC": "mic",
            "Category": "interpret", "Country": "country",
            "Year": "year", "Age Group": "age_group",
            "Drug Class": "drug_class", "Specimen Type": "specimen",
        }
        return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    def _synthetic_sample(self) -> pd.DataFrame:
        return _base_synthetic(self.dataset_name, n=1200,
            organisms=["Haemophilus influenzae", "Moraxella catarrhalis",
                       "Streptococcus pneumoniae", "Klebsiella pneumoniae"],
            drugs=["Amoxicillin/Clavulanate", "Ceftriaxone",
                   "Azithromycin", "Levofloxacin", "Meropenem"])


class SideroWtLoader(BaseLoader):
    dataset_name = "SIDERO-WT"

    def _read_file(self, path: str) -> pd.DataFrame:
        df = super()._read_file(path)
        rename = {
            "Organism": "organism", "Drug": "drug", "MIC": "mic",
            "Interpretation": "interpret", "Country": "country",
            "Year": "year", "Age": "age_group", "Drug Class": "drug_class",
        }
        return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    def _synthetic_sample(self) -> pd.DataFrame:
        return _base_synthetic(self.dataset_name, n=900,
            organisms=["Klebsiella pneumoniae", "Escherichia coli",
                       "Pseudomonas aeruginosa", "Acinetobacter baumannii",
                       "Enterobacter cloacae"],
            drugs=["Cefiderocol", "Meropenem", "Colistin",
                   "Ceftazidime/Avibactam", "Aztreonam"])


class GearsLoader(BaseLoader):
    dataset_name = "GEARS"

    def _read_file(self, path: str) -> pd.DataFrame:
        df = super()._read_file(path)
        rename = {
            "Pathogen": "organism", "Antibiotic": "drug", "MIC": "mic",
            "SIR": "interpret", "Country": "country", "Year": "year",
            "Age Group": "age_group", "Class": "drug_class",
        }
        return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    def _synthetic_sample(self) -> pd.DataFrame:
        return _base_synthetic(self.dataset_name, n=700,
            drugs=["Cefepime/Taniborbactam", "Meropenem", "Ceftazidime/Avibactam",
                   "Aztreonam/Avibactam", "Colistin"])


class KeystoneLoader(BaseLoader):
    dataset_name = "KEYSTONE"

    def _read_file(self, path: str) -> pd.DataFrame:
        df = super()._read_file(path)
        rename = {
            "Organism": "organism", "Antibiotic": "drug", "MIC": "mic",
            "Susceptibility": "interpret", "Country": "country",
            "Year": "year", "Age Group": "age_group",
            "Antibiotic Class": "drug_class",
        }
        return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    def _synthetic_sample(self) -> pd.DataFrame:
        return _base_synthetic(self.dataset_name, n=600,
            organisms=["Acinetobacter baumannii", "Klebsiella pneumoniae",
                       "Pseudomonas aeruginosa", "Escherichia coli"],
            drugs=["Omadacycline", "Meropenem", "Ciprofloxacin", "Colistin"])


class DreamLoader(BaseLoader):
    dataset_name = "DREAM"

    def _read_file(self, path: str) -> pd.DataFrame:
        df = super()._read_file(path)
        rename = {
            "Organism": "organism", "Drug": "drug", "MIC": "mic",
            "Interpretation": "interpret", "Country": "country",
            "Year": "year", "Patient Age Group": "age_group",
        }
        return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    def _synthetic_sample(self) -> pd.DataFrame:
        return _base_synthetic(self.dataset_name, n=400,
            organisms=["Mycobacterium tuberculosis"],
            drugs=["Bedaquiline", "Delamanid", "Linezolid", "Clofazimine"])


class InnovivaLoader(BaseLoader):
    dataset_name = "Innoviva_Acinetobacter"

    def _read_file(self, path: str) -> pd.DataFrame:
        df = super()._read_file(path)
        rename = {
            "Species": "organism", "Antibiotic": "drug", "MIC": "mic",
            "Category": "interpret", "Country": "country", "Year": "year",
            "Age Group": "age_group", "Drug Class": "drug_class",
        }
        return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    def _synthetic_sample(self) -> pd.DataFrame:
        return _base_synthetic(self.dataset_name, n=500,
            organisms=["Acinetobacter baumannii"],
            drugs=["Sulbactam/Durlobactam", "Meropenem", "Colistin",
                   "Imipenem", "Cefiderocol"])


class VenusLoader(BaseLoader):
    """Loader for Venus Remedies datasets (PLEA I, PLEA II, GASAR III)."""

    def __init__(self, filepath: Optional[str] = None, dataset_name: str = "Venus"):
        super().__init__(filepath)
        self.dataset_name = dataset_name

    def _synthetic_sample(self) -> pd.DataFrame:
        return _base_synthetic(self.dataset_name, n=350,
            organisms=["Klebsiella pneumoniae", "Escherichia coli",
                       "Pseudomonas aeruginosa"],
            drugs=["Elores", "Meropenem", "Ceftriaxone", "Piperacillin/Tazobactam"])


class SpidaarLoader(BaseLoader):
    dataset_name = "SPIDAAR_RWE"

    def _synthetic_sample(self) -> pd.DataFrame:
        return _base_synthetic(self.dataset_name, n=450,
            organisms=["Pseudomonas aeruginosa", "Klebsiella pneumoniae",
                       "Acinetobacter baumannii"],
            drugs=["Ceftolozane/Tazobactam", "Meropenem", "Colistin",
                   "Ceftazidime/Avibactam"])


# ---------------------------------------------------------------------------
# Master loader
# ---------------------------------------------------------------------------

class DatasetLoader:
    """Loads all datasets and concatenates them into a single DataFrame."""

    # Map dataset name → (loader class, expected raw file path suffix)
    REGISTRY = {
        "ATLAS_Antibiotics":     (AtlasAntibioticsLoader, "atlas_antibiotics.csv"),
        "ATLAS_Antifungals":     (AtlasAntifungalsLoader, "atlas_antifungals.csv"),
        "SOAR_201818":           (SoarLoader,             "soar_201818.csv"),
        "SOAR_207965":           (SoarLoader,             "soar_207965.csv"),
        "SOAR_201910":           (SoarLoader,             "soar_201910.csv"),
        "SIDERO-WT":             (SideroWtLoader,         "sidero_wt.csv"),
        "GEARS":                 (GearsLoader,             "gears.csv"),
        "KEYSTONE":              (KeystoneLoader,          "keystone.csv"),
        "DREAM":                 (DreamLoader,             "dream.csv"),
        "Innoviva_Acinetobacter":(InnovivaLoader,          "innoviva_acinetobacter.csv"),
        "Venus_PLEA_I":          (VenusLoader,             "venus_plea_i.csv"),
        "Venus_PLEA_II":         (VenusLoader,             "venus_plea_ii.csv"),
        "Venus_GASAR_III":       (VenusLoader,             "venus_gasar_iii.csv"),
        "SPIDAAR_RWE":           (SpidaarLoader,           "spidaar_rwe.csv"),
    }

    def __init__(self, raw_dir: str):
        self.raw_dir = raw_dir

    def load_all(self, datasets: Optional[list] = None) -> pd.DataFrame:
        """Load all (or a subset of) datasets and concatenate."""
        target = datasets or list(self.REGISTRY.keys())
        frames = []

        for name in target:
            if name not in self.REGISTRY:
                logger.warning(f"Unknown dataset: {name}")
                continue
            loader_cls, filename = self.REGISTRY[name]
            filepath = os.path.join(self.raw_dir, filename)

            # SOAR and Venus loaders need dataset_name kwarg
            if loader_cls in (SoarLoader, VenusLoader):
                loader = loader_cls(filepath=filepath, dataset_name=name)
            else:
                loader = loader_cls(filepath=filepath)

            frames.append(loader.load())

        if not frames:
            raise RuntimeError("No datasets loaded.")

        combined = pd.concat(frames, ignore_index=True)
        logger.info(f"Total rows across all datasets: {len(combined)}")
        return combined
