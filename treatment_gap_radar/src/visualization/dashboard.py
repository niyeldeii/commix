"""
Interactive Plotly/Dash dashboard for the Treatment Gap Radar.

Run:
    python -m src.visualization.dashboard

Then open http://localhost:8050 in your browser.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import logging
import os

logger = logging.getLogger(__name__)

QUADRANT_COLORS = {
    "I_Well_Addressed":  "#2ecc71",
    "II_Over_Invested":  "#3498db",
    "III_Low_Priority":  "#95a5a6",
    "IV_Critical_Gap":   "#e74c3c",
}


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def _gap_scatter(gap_df: pd.DataFrame, rni_th: float = 0.5,
                 rdai_th: float = 0.5) -> go.Figure:
    gap_df = gap_df.copy()
    gap_df["color"] = gap_df["quadrant"].map(QUADRANT_COLORS).fillna("#7f8c8d")
    gap_df["label"] = gap_df["organism"] + " / " + gap_df["drug"]
    gap_df["size"]  = 10 + 30 * gap_df["RNI"]

    fig = px.scatter(
        gap_df, x="RDAI", y="RNI",
        color="quadrant",
        color_discrete_map=QUADRANT_COLORS,
        hover_name="label",
        hover_data={
            "organism": True, "drug": True,
            "RNI": ":.3f", "RDAI": ":.3f",
            "gap_score": ":.3f", "quadrant": True,
            "label": False,
        },
        size="size", size_max=35,
        title="Treatment Gap Radar — RNI vs RDAI",
    )
    # Threshold lines
    fig.add_hline(y=rni_th, line_dash="dash", line_color="black", opacity=0.4)
    fig.add_vline(x=rdai_th, line_dash="dash", line_color="black", opacity=0.4)

    # Quadrant labels
    for text, x, y in [
        ("IV: CRITICAL GAP", 0.05, 0.95),
        ("I: Well-addressed", 0.75, 0.95),
        ("III: Low priority", 0.05, 0.05),
        ("II: Over-invested", 0.75, 0.05),
    ]:
        fig.add_annotation(
            text=text, xref="paper", yref="paper",
            x=x, y=y, showarrow=False, font=dict(size=11, color="grey"),
        )

    fig.update_layout(
        xaxis_title="R&D Attention Index (RDAI)",
        yaxis_title="Resistance Need Index (RNI)",
        xaxis=dict(range=[-0.05, 1.05]),
        yaxis=dict(range=[-0.05, 1.05]),
        legend_title="Quadrant",
        height=550,
    )
    return fig


def _radar_figure(rni_df: pd.DataFrame, organism: str, drugs: list) -> go.Figure:
    indicators = [
        "resistance_prevalence", "mic_drift", "mdr_frequency",
        "geographic_spread", "therapeutic_scarcity", "pediatric_involvement",
    ]
    labels = [
        "Resistance Prevalence", "MIC Drift", "MDR Frequency",
        "Geographic Spread", "Therapeutic Scarcity", "Pediatric Involvement",
    ]
    subset = rni_df[rni_df["organism"] == organism]
    fig = go.Figure()
    for drug in drugs:
        row = subset[subset["drug"] == drug][indicators].mean()
        if row.empty:
            continue
        vals = [row.get(ind, 0) for ind in indicators]
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=labels + [labels[0]],
            fill="toself", name=drug, opacity=0.7,
        ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title=f"RNI Sub-indicators — {organism}",
        height=480,
    )
    return fig


def _country_bar(rni_df: pd.DataFrame, organism: str) -> go.Figure:
    subset = rni_df[rni_df["organism"] == organism]
    country_rni = (
        subset.groupby("country")["RNI"]
        .mean()
        .reset_index()
        .sort_values("RNI", ascending=False)
        .head(15)
    )
    fig = px.bar(
        country_rni, x="RNI", y="country", orientation="h",
        color="RNI", color_continuous_scale="YlOrRd",
        title=f"Top Countries by RNI — {organism}",
        labels={"country": "Country", "RNI": "Mean RNI"},
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), height=420)
    return fig


def _resistance_trend(df: pd.DataFrame, organism: str, drug: str) -> go.Figure:
    subset = df[(df["organism"] == organism) & (df["drug"] == drug)]
    trend = (
        subset.groupby("year")["is_resistant"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "resistant", "count": "total"})
        .reset_index()
    )
    trend["prevalence"] = trend["resistant"] / trend["total"].clip(lower=1)

    fig = px.line(
        trend, x="year", y="prevalence", markers=True,
        title=f"Resistance Prevalence Over Time — {organism} / {drug}",
        labels={"year": "Year", "prevalence": "Resistance Prevalence"},
    )
    fig.update_layout(yaxis=dict(range=[0, 1]), height=380)
    return fig


# ---------------------------------------------------------------------------
# Dashboard app
# ---------------------------------------------------------------------------

def build_dashboard(
    harmonized_df: pd.DataFrame,
    rni_df: pd.DataFrame,
    gap_df: pd.DataFrame,
    port: int = 8050,
):
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        title="Treatment Gap Radar",
    )

    organisms = sorted(rni_df["organism"].unique())
    org_options = [{"label": o, "value": o} for o in organisms]
    default_org = organisms[0] if organisms else ""

    def drug_options_for(org):
        drugs = sorted(rni_df[rni_df["organism"] == org]["drug"].unique())
        return [{"label": d, "value": d} for d in drugs]

    app.layout = dbc.Container(fluid=True, children=[
        dbc.Row([
            dbc.Col(html.H2("Treatment Gap Radar", className="text-primary fw-bold"), width=9),
            dbc.Col(html.P("AMR Data Challenge · Vivli", className="text-muted mt-2"), width=3),
        ], className="my-3"),

        dbc.Tabs([
            # ── Tab 1: Gap Overview ─────────────────────────────────────
            dbc.Tab(label="Gap Overview", children=[
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Pathogen Filter", className="card-subtitle"),
                                dcc.Dropdown(
                                    id="scatter-organism-filter",
                                    options=[{"label": "All", "value": "all"}] + org_options,
                                    value="all", clearable=False,
                                ),
                            ])
                        ], className="mb-3"),
                        dbc.Card(dbc.CardBody(id="gap-stats")),
                    ], width=3),
                    dbc.Col(dcc.Graph(id="gap-scatter", config={"displayModeBar": True}),
                            width=9),
                ], className="mt-3"),

                dbc.Row([
                    dbc.Col(dcc.Graph(id="critical-gap-bar"), width=12),
                ]),
            ]),

            # ── Tab 2: Pathogen Deep-dive ───────────────────────────────
            dbc.Tab(label="Pathogen Deep-dive", children=[
                dbc.Row([
                    dbc.Col([
                        html.Label("Select Pathogen"),
                        dcc.Dropdown(id="dd-organism", options=org_options,
                                     value=default_org, clearable=False),
                        html.Label("Select Drug(s)", className="mt-2"),
                        dcc.Dropdown(id="dd-drug", multi=True),
                    ], width=3),
                    dbc.Col(dcc.Graph(id="radar-fig"), width=5),
                    dbc.Col(dcc.Graph(id="country-bar"), width=4),
                ], className="mt-3"),
            ]),

            # ── Tab 3: Resistance Trends ────────────────────────────────
            dbc.Tab(label="Resistance Trends", children=[
                dbc.Row([
                    dbc.Col([
                        html.Label("Pathogen"),
                        dcc.Dropdown(id="trend-organism", options=org_options,
                                     value=default_org, clearable=False),
                        html.Label("Drug", className="mt-2"),
                        dcc.Dropdown(id="trend-drug"),
                    ], width=3),
                    dbc.Col(dcc.Graph(id="trend-fig"), width=9),
                ], className="mt-3"),
            ]),

            # ── Tab 4: Critical Gaps Table ──────────────────────────────
            dbc.Tab(label="Critical Gaps Table", children=[
                dbc.Row([
                    dbc.Col(
                        html.Div(id="gap-table", className="mt-3"),
                        width=12
                    ),
                ]),
            ]),
        ]),
    ])

    # ── Callbacks ──────────────────────────────────────────────────────

    @app.callback(
        Output("gap-scatter", "figure"),
        Output("gap-stats", "children"),
        Output("critical-gap-bar", "figure"),
        Input("scatter-organism-filter", "value"),
    )
    def update_scatter(org_filter):
        filtered = gap_df if org_filter == "all" else \
                   gap_df[gap_df["organism"] == org_filter]

        fig = _gap_scatter(filtered)
        n_crit = (filtered["quadrant"] == "IV_Critical_Gap").sum()
        stats = [
            html.P(f"Total combinations: {len(filtered)}"),
            html.P(f"Critical gaps (Q-IV): {n_crit}",
                   className="text-danger fw-bold"),
            html.P(f"Well-addressed (Q-I): "
                   f"{(filtered['quadrant'] == 'I_Well_Addressed').sum()}",
                   className="text-success"),
        ]

        top_gaps = (
            filtered[filtered["quadrant"] == "IV_Critical_Gap"]
            .nlargest(15, "gap_score")
        )
        top_gaps["label"] = top_gaps["organism"].str.split().str[-1] + \
                             " / " + top_gaps["drug"]
        bar_fig = px.bar(
            top_gaps, x="gap_score", y="label", orientation="h",
            color="gap_score", color_continuous_scale="Reds",
            title="Top Critical Gaps (Quadrant IV) — Ranked by Gap Score",
            labels={"label": "", "gap_score": "Gap Score (RNI − RDAI)"},
        )
        bar_fig.update_layout(yaxis=dict(autorange="reversed"), height=420)
        return fig, stats, bar_fig

    @app.callback(
        Output("dd-drug", "options"),
        Output("dd-drug", "value"),
        Input("dd-organism", "value"),
    )
    def update_drug_dropdown(org):
        opts = drug_options_for(org)
        default = [opts[0]["value"]] if opts else []
        return opts, default

    @app.callback(
        Output("radar-fig", "figure"),
        Output("country-bar", "figure"),
        Input("dd-organism", "value"),
        Input("dd-drug", "value"),
    )
    def update_deep_dive(org, drugs):
        drugs = drugs or []
        return _radar_figure(rni_df, org, drugs), _country_bar(rni_df, org)

    @app.callback(
        Output("trend-drug", "options"),
        Output("trend-drug", "value"),
        Input("trend-organism", "value"),
    )
    def update_trend_drug(org):
        drugs = sorted(harmonized_df[harmonized_df["organism"] == org]["drug"].unique())
        opts = [{"label": d, "value": d} for d in drugs]
        return opts, (drugs[0] if drugs else None)

    @app.callback(
        Output("trend-fig", "figure"),
        Input("trend-organism", "value"),
        Input("trend-drug", "value"),
    )
    def update_trend(org, drug):
        if not org or not drug:
            return go.Figure()
        return _resistance_trend(harmonized_df, org, drug)

    @app.callback(
        Output("gap-table", "children"),
        Input("scatter-organism-filter", "value"),
    )
    def update_table(org_filter):
        filtered = gap_df if org_filter == "all" else \
                   gap_df[gap_df["organism"] == org_filter]
        crits = (
            filtered[filtered["quadrant"] == "IV_Critical_Gap"]
            .nlargest(30, "gap_score")
            [["rank", "organism", "drug", "RNI", "RDAI", "gap_score",
              "n_countries", "resistance_prevalence", "mdr_frequency"]]
        )
        crits = crits.round(3)

        rows = [html.Tr([html.Th(c) for c in crits.columns])]
        for _, r in crits.iterrows():
            rows.append(html.Tr([html.Td(str(v)) for v in r]))

        return dbc.Table(
            [html.Thead(rows[0]), html.Tbody(rows[1:])],
            bordered=True, hover=True, striped=True, responsive=True,
            className="table-sm",
        )

    return app


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
    from main import run_pipeline

    harmonized_df, rni_df, rdai_df, gap_df = run_pipeline(return_data=True)
    app = build_dashboard(harmonized_df, rni_df, gap_df)
    app.run(debug=True, port=8050)
