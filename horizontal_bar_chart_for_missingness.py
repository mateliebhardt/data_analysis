"""
Data Quality Report: Column Missingness Comparison
---------------------------------------------------
Horizontal grouped bar chart showing % missing values
per column for two DataFrames with identical column names.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ─────────────────────────────────────────────
# CONFIGURE HERE
# ─────────────────────────────────────────────
DF1_LABEL = "Source A"
DF2_LABEL = "Source B"

# ─────────────────────────────────────────────
# SAMPLE DATA  –  replace with your own dfs
# ─────────────────────────────────────────────
np.random.seed(42)
n = 200

def inject_nulls(series, rate):
    s = series.astype(object)
    s[np.random.choice(len(s), int(len(s) * rate), replace=False)] = np.nan
    return s

df1 = pd.DataFrame({
    "customer_id": inject_nulls(pd.Series(range(n)), 0.00),
    "email":       inject_nulls(pd.Series([f"u{i}@x.com" for i in range(n)]), 0.12),
    "age":         inject_nulls(pd.Series(np.random.randint(18, 80, n)), 0.08),
    "country":     inject_nulls(pd.Series(np.random.choice(["UK","US","DE","FR"], n)), 0.21),
    "revenue":     inject_nulls(pd.Series(np.random.uniform(10, 500, n)), 0.34),
    "signup_date": inject_nulls(pd.Series(pd.date_range("2022-01-01", periods=n, freq="D")), 0.05),
    "plan":        inject_nulls(pd.Series(np.random.choice(["free","pro","enterprise"], n)), 0.17),
    "last_login":  inject_nulls(pd.Series(pd.date_range("2023-01-01", periods=n, freq="D")), 0.44),
})

df2 = pd.DataFrame({
    "customer_id": inject_nulls(pd.Series(range(n)), 0.02),
    "email":       inject_nulls(pd.Series([f"u{i}@x.com" for i in range(n)]), 0.06),
    "age":         inject_nulls(pd.Series(np.random.randint(18, 80, n)), 0.19),
    "country":     inject_nulls(pd.Series(np.random.choice(["UK","US","DE","FR"], n)), 0.09),
    "revenue":     inject_nulls(pd.Series(np.random.uniform(10, 500, n)), 0.27),
    "signup_date": inject_nulls(pd.Series(pd.date_range("2022-01-01", periods=n, freq="D")), 0.00),
    "plan":        inject_nulls(pd.Series(np.random.choice(["free","pro","enterprise"], n)), 0.38),
    "last_login":  inject_nulls(pd.Series(pd.date_range("2023-01-01", periods=n, freq="D")), 0.51),
})


# ─────────────────────────────────────────────
# LOGIC
# ─────────────────────────────────────────────
columns = df1.columns.tolist()

miss1 = (df1.isnull().mean() * 100).round(1)
miss2 = (df2.isnull().mean() * 100).round(1)

# Sort by average missingness descending
avg_miss = ((miss1 + miss2) / 2).sort_values(ascending=True)
columns_sorted = avg_miss.index.tolist()

y      = columns_sorted
x1     = [miss1[c] for c in columns_sorted]
x2     = [miss2[c] for c in columns_sorted]

# ─────────────────────────────────────────────
# CHART
# ─────────────────────────────────────────────
BAR_HEIGHT = 28
chart_height = max(400, len(columns_sorted) * BAR_HEIGHT * 2 + 160)

fig = go.Figure()

fig.add_trace(go.Bar(
    name=DF1_LABEL,
    y=y,
    x=x1,
    orientation="h",
    marker=dict(
        color="#4F8EF7",
        line=dict(color="#1a1a2e", width=1),
    ),
    hovertemplate="<b>%{y}</b><br>" + DF1_LABEL + ": %{x:.1f}%<extra></extra>",
    text=[f"{v:.1f}%" if v > 0 else "" for v in x1],
    textposition="outside",
    textfont=dict(size=11, color="#4F8EF7"),
))

fig.add_trace(go.Bar(
    name=DF2_LABEL,
    y=y,
    x=x2,
    orientation="h",
    marker=dict(
        color="#F76B6B",
        line=dict(color="#1a1a2e", width=1),
    ),
    hovertemplate="<b>%{y}</b><br>" + DF2_LABEL + ": %{x:.1f}%<extra></extra>",
    text=[f"{v:.1f}%" if v > 0 else "" for v in x2],
    textposition="outside",
    textfont=dict(size=11, color="#F76B6B"),
))

# Threshold line at 20%
fig.add_vline(
    x=20,
    line=dict(color="rgba(255,200,80,0.5)", width=1.5, dash="dot"),
    annotation_text="20% threshold",
    annotation_position="top",
    annotation_font=dict(color="rgba(255,200,80,0.8)", size=11),
)

fig.update_layout(
    barmode="group",
    title=dict(
        text="<b>Column Missingness Comparison</b><br>"
             "<sup>% of null values per column · sorted by average missingness</sup>",
        font=dict(size=20, color="white"),
        x=0.5,
        xanchor="center",
        y=0.98,
    ),
    xaxis=dict(
        title="Missing (%)",
        range=[0, 110],
        ticksuffix="%",
        gridcolor="rgba(255,255,255,0.06)",
        showline=False,
        color="rgba(255,255,255,0.6)",
        tickfont=dict(size=11),
    ),
    yaxis=dict(
        tickfont=dict(size=12, color="white"),
        gridcolor="rgba(255,255,255,0.04)",
    ),
    paper_bgcolor="#0f0f1a",
    plot_bgcolor="#0f0f1a",
    font=dict(color="white", family="'IBM Plex Mono', monospace"),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.12,
        xanchor="center",
        x=0.5,
        font=dict(size=13),
        bgcolor="rgba(255,255,255,0.05)",
        bordercolor="rgba(255,255,255,0.1)",
        borderwidth=1,
    ),
    margin=dict(t=100, b=80, l=20, r=80),
    height=chart_height,
    width=800,
    bargap=0.25,
    bargroupgap=0.08,
)

fig.show()

# Optional: save
# fig.write_html("missingness_report.html")