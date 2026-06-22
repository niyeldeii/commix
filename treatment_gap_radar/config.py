"""
Central configuration for the Treatment Gap Radar pipeline.
Adjust paths and weights here before running the pipeline.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
RD_HUB_DIR = os.path.join(DATA_DIR, "rd_hub")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Priority Gram-negative pathogens (WHO critical/high priority)
PRIORITY_PATHOGENS = [
    "Acinetobacter baumannii",
    "Pseudomonas aeruginosa",
    "Klebsiella pneumoniae",
    "Escherichia coli",
    "Enterobacter cloacae",
    "Stenotrophomonas maltophilia",
    "Haemophilus influenzae",
    "Neisseria gonorrhoeae",
]

# Drug classes of interest
PRIORITY_DRUG_CLASSES = [
    "Carbapenems",
    "Cephalosporins",
    "Fluoroquinolones",
    "Aminoglycosides",
    "Polymyxins",
    "Monobactams",
    "Beta-lactam/beta-lactamase inhibitor combinations",
    "Tetracyclines",
]

# WHO regions for geographic analysis
WHO_REGIONS = [
    "Africa",
    "Americas",
    "South-East Asia",
    "Europe",
    "Eastern Mediterranean",
    "Western Pacific",
]

# Resistance Need Index (RNI) component weights — must sum to 1.0
RNI_WEIGHTS = {
    "resistance_prevalence": 0.30,
    "mic_drift":             0.20,
    "mdr_frequency":         0.20,
    "geographic_spread":     0.15,
    "therapeutic_scarcity":  0.10,
    "pediatric_involvement": 0.05,
}

# R&D Attention Index (RDAI) component weights — must sum to 1.0
RDAI_WEIGHTS = {
    "investment_score":  0.40,
    "pipeline_score":    0.40,
    "surveillance_score": 0.20,
}

# Minimum isolate count for a pathogen-drug-country combo to be included
MIN_ISOLATE_COUNT = 5

# Years to analyse (filter applied during ingestion)
ANALYSIS_YEARS = list(range(2010, 2025))

# MIC drift: minimum years of data needed to compute a trend
MIN_YEARS_FOR_DRIFT = 3

# EUCAST/CLSI breakpoint thresholds (drug → breakpoint in mg/L)
# Used when susceptibility interpretation column is absent
MIC_BREAKPOINTS = {
    "Meropenem":     {"S": 2, "I": 4,  "R": 8},
    "Imipenem":      {"S": 2, "I": 4,  "R": 8},
    "Ceftazidime":   {"S": 4, "I": 8,  "R": 16},
    "Ciprofloxacin": {"S": 0.5, "I": 1, "R": 2},
    "Colistin":      {"S": 2, "I": None, "R": 4},
    "Aztreonam":     {"S": 4, "I": 8,  "R": 16},
    "Cefiderocol":   {"S": 2, "I": 4,  "R": 8},
    "Omadacycline":  {"S": 2, "I": 4,  "R": 8},
}

# Column name aliases — each dataset uses different naming conventions.
# The harmonizer maps these to canonical names.
COLUMN_ALIASES = {
    "organism":    ["species", "pathogen", "organism_name", "bacterial_species", "Organism"],
    "drug":        ["antibiotic", "antimicrobial", "agent", "drug_name", "Antibiotic", "Drug"],
    "mic":         ["mic_value", "MIC", "mic_result", "MIC_value"],
    "interpret":   ["susceptibility", "interpretation", "sir", "category", "SIR"],
    "country":     ["country_name", "country_code", "nation", "Country"],
    "year":        ["collection_year", "study_year", "year_collected", "Year"],
    "age_group":   ["patient_age_group", "age_category", "pediatric_flag", "Age"],
    "drug_class":  ["antibiotic_class", "class", "drug_category", "Class"],
    "specimen":    ["specimen_type", "sample_type", "source", "Specimen"],
    "dataset":     ["study", "trial", "source_dataset"],
}
