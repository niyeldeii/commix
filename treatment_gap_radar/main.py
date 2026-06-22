"""
Treatment Gap Radar — main pipeline entry point.

Usage:
    # Run full pipeline (uses synthetic data if real files are absent)
    python main.py

    # Run and launch interactive dashboard
    python main.py --dashboard

    # Run with real datasets (place CSV/XLSX files in data/raw/ first)
    python main.py --data-dir /path/to/raw/data
"""

import argparse
import logging
import os
import sys

import pandas as pd

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import RAW_DIR, PROCESSED_DIR, OUTPUT_DIR
from src.data_ingestion import DatasetLoader, DataHarmonizer
from src.indices import ResistanceNeedIndex, RDAttentionIndex
from src.analysis import GapAnalysis
from src.visualization import RadarChart, GapScatterPlot, ResistanceHeatmap

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("treatment_gap_radar")


def run_pipeline(
    raw_dir: str = None,
    datasets: list = None,
    return_data: bool = False,
    dashboard: bool = False,
):
    raw_dir = raw_dir or RAW_DIR
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── 1. Ingest ──────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 1 — Data Ingestion")
    loader = DatasetLoader(raw_dir=raw_dir)
    raw_df = loader.load_all(datasets=datasets)

    # ── 2. Harmonise ───────────────────────────────────────────────────
    logger.info("STEP 2 — Harmonisation")
    harmonizer = DataHarmonizer(filter_priority=False)
    harmonized_df = harmonizer.harmonize(raw_df)

    processed_path = os.path.join(PROCESSED_DIR, "harmonized.csv")
    harmonized_df.to_csv(processed_path, index=False)
    logger.info(f"Saved harmonized data → {processed_path}")

    # ── 3. Resistance Need Index ────────────────────────────────────────
    logger.info("STEP 3 — Resistance Need Index")
    rni_engine = ResistanceNeedIndex()
    rni_df = rni_engine.compute(harmonized_df)
    rni_df.to_csv(os.path.join(OUTPUT_DIR, "rni_scores.csv"), index=False)
    logger.info(f"Top 5 RNI combinations:\n{rni_df[['organism','drug','country','RNI']].head()}")

    # ── 4. R&D Attention Index ──────────────────────────────────────────
    logger.info("STEP 4 — R&D Attention Index")
    rdai_engine = RDAttentionIndex()
    rdai_df = rdai_engine.compute(
        organisms=list(rni_df["organism"].unique()),
        drugs=list(rni_df["drug"].unique()),
    )
    rdai_df.to_csv(os.path.join(OUTPUT_DIR, "rdai_scores.csv"), index=False)
    logger.info(f"Top 5 RDAI combinations:\n{rdai_df[['organism','drug','RDAI']].head()}")

    # ── 5. Gap Analysis ─────────────────────────────────────────────────
    logger.info("STEP 5 — Gap Analysis")
    gap_engine = GapAnalysis()
    gap_df = gap_engine.merge(rni_df, rdai_df)
    gap_df.to_csv(os.path.join(OUTPUT_DIR, "gap_analysis.csv"), index=False)

    crits = gap_engine.critical_gaps(gap_df, top_n=20)
    crits.to_csv(os.path.join(OUTPUT_DIR, "critical_gaps.csv"), index=False)

    pathogen_summary = gap_engine.pathogen_summary(gap_df)
    pathogen_summary.to_csv(os.path.join(OUTPUT_DIR, "pathogen_summary.csv"), index=False)

    country_gaps = gap_engine.country_gaps(rni_df, rdai_df)
    country_gaps.to_csv(os.path.join(OUTPUT_DIR, "country_gaps.csv"), index=False)

    logger.info("Critical gaps (top 10):")
    logger.info(crits[["organism", "drug", "RNI", "RDAI", "gap_score"]].head(10).to_string())

    # ── 6. Visualisations ───────────────────────────────────────────────
    logger.info("STEP 6 — Visualisations")

    # Attach region to rni_df for heatmap
    if "region" not in rni_df.columns:
        region_map = harmonized_df[["country", "region"]].drop_duplicates().set_index("country")["region"]
        rni_df["region"] = rni_df["country"].map(region_map)

    # Scatter plot
    scatter = GapScatterPlot()
    scatter.plot(gap_df)

    # Radar charts (top 5 pathogens by critical gap count)
    top_orgs = (
        gap_df[gap_df["quadrant"] == "IV_Critical_Gap"]
        .groupby("organism")["gap_score"].sum()
        .nlargest(5).index.tolist()
    )
    radar = RadarChart()
    for org in top_orgs:
        radar.plot_pathogen(rni_df, org)

    # Heatmaps
    heatmap = ResistanceHeatmap()
    heatmap.plot_country_pathogen(rni_df)
    heatmap.plot_drug_pathogen(rni_df)

    logger.info(f"All outputs saved to: {OUTPUT_DIR}")
    logger.info("=" * 60)
    logger.info("Pipeline complete.")

    if return_data:
        return harmonized_df, rni_df, rdai_df, gap_df

    if dashboard:
        from src.visualization import build_dashboard
        app = build_dashboard(harmonized_df, rni_df, gap_df)
        logger.info("Starting dashboard at http://localhost:8050")
        app.run(debug=False, port=8050)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treatment Gap Radar pipeline")
    parser.add_argument("--dashboard", action="store_true",
                        help="Launch interactive Dash dashboard after pipeline")
    parser.add_argument("--data-dir", default=None,
                        help="Path to raw data directory (default: data/raw/)")
    parser.add_argument("--datasets", nargs="+", default=None,
                        help="Specific dataset names to load (default: all)")
    args = parser.parse_args()

    run_pipeline(
        raw_dir=args.data_dir,
        datasets=args.datasets,
        dashboard=args.dashboard,
    )
