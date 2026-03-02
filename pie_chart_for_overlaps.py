"""
Data Quality Report: DataFrame Overlap Pie Chart
-------------------------------------------------
Compares two DataFrames based on two key columns and visualises:
  - Only in DF1
  - Only in DF2
  - In Both (overlap)
"""

import pandas as pd
import plotly.graph_objects as go

# ─────────────────────────────────────────────
# CONFIGURE HERE
# ─────────────────────────────────────────────
COL1 = "id"          # First key column to compare on
COL2 = "date"        # Second key column to compare on
DF1_LABEL = "Source A"
DF2_LABEL = "Source B"

# ─────────────────────────────────────────────
# SAMPLE DATA  –  replace with your own dfs
# ─────────────────────────────────────────────
df1 = pd.DataFrame({
    "id":   [1, 2, 3, 4, 5, 6],
    "date": ["2024-01", "2024-01", "2024-02", "2024-02", "2024-03", "2024-03"],
    "value": [100, 200, 150, 300, 250, 400],
})

df2 = pd.DataFrame({
    "id":   [3, 4, 5, 6, 7, 8],
    "date": ["2024-02", "2024-02", "2024-03", "2024-03", "2024-04", "2024-04"],
    "value": [155, 310, 260, 390, 180, 220],
})


# ─────────────────────────────────────────────
# LOGIC
# ─────────────────────────────────────────────
def compute_overlap(df1, df2, col1, col2):
    keys1 = set(zip(df1[col1], df1[col2]))
    keys2 = set(zip(df2[col1], df2[col2]))

    both   = keys1 & keys2
    only1  = keys1 - keys2
    only2  = keys2 - keys1

    return len(only1), len(only2), len(both)


only1, only2, both = compute_overlap(df1, df2, COL1, COL2)
total = only1 + only2 + both

labels = [f"Only in {DF1_LABEL}", f"Only in {DF2_LABEL}", "In Both"]
values = [only1, only2, both]
colors = ["#4F8EF7", "#F76B6B", "#44D9A2"]

# ─────────────────────────────────────────────
# CHART
# ─────────────────────────────────────────────
fig = go.Figure(
    data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(
                colors=colors,
                line=dict(color="#1a1a2e", width=3),
            ),
            textinfo="label+percent",
            textfont=dict(size=14, color="white"),
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
            pull=[0.03, 0.03, 0.06],   # slight pull on "Both" to highlight it
        )
    ]
)

fig.update_layout(
    title=dict(
        text=f"<b>Data Overlap Report</b><br>"
             f"<sup>Comparing on columns: <i>{COL1}</i> × <i>{COL2}</i> &nbsp;|&nbsp; "
             f"Total unique keys: {total}</sup>",
        font=dict(size=20, color="white"),
        x=0.5,
        xanchor="center",
        y=0.97,
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
    ),
    margin=dict(t=110, b=80, l=40, r=40),
    # Centre annotation showing total
    annotations=[
        dict(
            text=f"<b>{total}</b><br><span style='font-size:12px'>total<br>keys</span>",
            x=0.5, y=0.5,
            font=dict(size=18, color="white"),
            showarrow=False,
        )
    ],
    width=700,
    height=520,
)

fig.show()

# Optional: save to HTML for sharing
# fig.write_html("overlap_report.html")