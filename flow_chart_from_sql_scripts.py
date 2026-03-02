#!/usr/bin/env python3
"""
SQL SELECT Statement → Flowchart Generator (Visio-style)

Parses a SQL SELECT statement and produces a clean, horizontal SVG flowchart
resembling Visio diagrams — white boxes, thin borders, simple connector lines.

Usage:
    python sql_to_flowchart.py                          # runs built-in demo
    python sql_to_flowchart.py "SELECT * FROM users"    # from CLI arg
    python sql_to_flowchart.py input.sql                # from file
    python sql_to_flowchart.py input.sql output.svg     # custom output path

Or import and use programmatically:
    from sql_to_flowchart import sql_to_flowchart
    svg_string = sql_to_flowchart(sql, output_path="my_chart.svg")
"""

import re
import sys
import os
import textwrap
from dataclasses import dataclass
from typing import List, Optional

# ─── SQL Parser ───────────────────────────────────────────────────────────────

@dataclass
class SQLStep:
    category: str
    label: str
    detail: str = ""
    shape: str = "rect"  # rect | rounded | diamond | stadium


def _clean(sql: str) -> str:
    sql = re.sub(r'--[^\n]*', ' ', sql)
    sql = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.S)
    sql = re.sub(r'\s+', ' ', sql).strip()
    return sql


def _extract_between(sql: str, start_kw: str, stop_kws: list) -> Optional[str]:
    pattern = rf'\b{start_kw}\b\s+(.*?)(?:\b(?:{"|".join(stop_kws)})\b|;|$)'
    m = re.search(pattern, sql, re.I | re.S)
    return m.group(1).strip() if m else None


def _find_tables_in_from(from_clause: str) -> List[str]:
    base = re.split(r'\b(?:INNER|LEFT|RIGHT|FULL|CROSS|NATURAL|OUTER|JOIN)\b', from_clause, flags=re.I)[0]
    tables = []
    for part in base.split(','):
        part = part.strip()
        if part:
            tables.append(re.split(r'\s+', part)[0])
    return tables


def _find_joins(sql: str) -> List[dict]:
    joins = []
    pattern = r'\b(INNER|LEFT\s+OUTER|RIGHT\s+OUTER|FULL\s+OUTER|LEFT|RIGHT|FULL|CROSS|NATURAL)?\s*JOIN\s+([\w\.]+)\s*(?:AS\s+\w+\s*)?(?:ON\s+(.*?))?(?=\b(?:INNER|LEFT|RIGHT|FULL|CROSS|NATURAL|JOIN|WHERE|GROUP|HAVING|ORDER|LIMIT|UNION|EXCEPT|INTERSECT|WINDOW|$)\b|;|$)'
    for m in re.finditer(pattern, sql, re.I | re.S):
        jtype = (m.group(1) or "INNER").strip().upper()
        table = m.group(2).strip()
        on_clause = (m.group(3) or "").strip()
        joins.append({"type": jtype, "table": table, "on": on_clause})
    return joins


def _has_subquery(clause: str) -> bool:
    return bool(re.search(r'\bSELECT\b', clause or '', re.I))

def _has_aggregates(s: str) -> bool:
    return bool(re.search(r'\b(COUNT|SUM|AVG|MIN|MAX|GROUP_CONCAT|STRING_AGG|ARRAY_AGG)\s*\(', s or '', re.I))

def _has_window_functions(s: str) -> bool:
    return bool(re.search(r'\bOVER\s*\(', s or '', re.I))

def _has_distinct(s: str) -> bool:
    return bool(re.search(r'\bDISTINCT\b', s or '', re.I))

def _has_case(s: str) -> bool:
    return bool(re.search(r'\bCASE\b', s or '', re.I))

def _truncate(text: str, max_len: int = 55) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text if len(text) <= max_len else text[:max_len - 3] + "..."


def parse_sql(sql: str) -> List[SQLStep]:
    sql = _clean(sql)
    steps: List[SQLStep] = []
    stop_kws = ['FROM', 'WHERE', 'GROUP', 'HAVING', 'ORDER', 'LIMIT',
                'UNION', 'EXCEPT', 'INTERSECT', 'FETCH', 'OFFSET', 'WINDOW', 'FOR']

    # CTE
    cte_match = re.match(r'\bWITH\b\s+(.*?)\bSELECT\b', sql, re.I | re.S)
    if cte_match:
        cte_names = re.findall(r'(\w+)\s+AS\s*\(', cte_match.group(1), re.I)
        steps.append(SQLStep("CTE", "CTE", detail=", ".join(cte_names), shape="rounded"))

    # FROM
    from_clause = _extract_between(sql, 'FROM',
        ['WHERE', 'GROUP', 'HAVING', 'ORDER', 'LIMIT', 'UNION',
         'EXCEPT', 'INTERSECT', 'WINDOW', 'INNER', 'LEFT', 'RIGHT',
         'FULL', 'CROSS', 'NATURAL', 'JOIN'])
    if from_clause:
        tables = _find_tables_in_from(from_clause)
        if _has_subquery(from_clause):
            steps.append(SQLStep("SOURCE", "Subquery", shape="rounded"))
        steps.append(SQLStep("SOURCE", "FROM", detail=", ".join(tables), shape="stadium"))
    else:
        steps.append(SQLStep("SOURCE", "SELECT (no table)", shape="stadium"))

    # JOINs
    for j in _find_joins(sql):
        on_short = _truncate(j["on"], 45) if j["on"] else ""
        steps.append(SQLStep("JOIN", f'{j["type"]} JOIN',
                             detail=j["table"] + (f"  ON {on_short}" if on_short else "")))

    # WHERE
    where_clause = _extract_between(sql, 'WHERE',
        ['GROUP', 'HAVING', 'ORDER', 'LIMIT', 'UNION', 'EXCEPT', 'INTERSECT', 'WINDOW'])
    if where_clause:
        steps.append(SQLStep("FILTER", "WHERE", detail=_truncate(where_clause, 70), shape="diamond"))

    # GROUP BY
    group_clause = _extract_between(sql, 'GROUP\\s+BY',
        ['HAVING', 'ORDER', 'LIMIT', 'UNION', 'EXCEPT', 'INTERSECT', 'WINDOW', 'SELECT'])
    if group_clause:
        steps.append(SQLStep("GROUP", "GROUP BY", detail=_truncate(group_clause)))

    # HAVING
    having_clause = _extract_between(sql, 'HAVING',
        ['ORDER', 'LIMIT', 'UNION', 'EXCEPT', 'INTERSECT', 'WINDOW', 'SELECT'])
    if having_clause:
        steps.append(SQLStep("FILTER", "HAVING", detail=_truncate(having_clause), shape="diamond"))

    # SELECT
    select_clause = _extract_between(sql, 'SELECT', ['FROM'] + stop_kws)
    extras = []
    if select_clause:
        if _has_aggregates(select_clause): extras.append("aggregations")
        if _has_window_functions(select_clause): extras.append("window funcs")
        if _has_case(select_clause): extras.append("CASE")
    steps.append(SQLStep("PROJECT", "SELECT", detail=", ".join(extras) if extras else ""))

    # DISTINCT
    if select_clause and _has_distinct(select_clause):
        steps.append(SQLStep("DISTINCT", "DISTINCT", shape="rounded"))

    # Set ops
    for op in ['UNION ALL', 'UNION', 'EXCEPT', 'INTERSECT']:
        if re.search(rf'\b{op}\b', sql, re.I):
            steps.append(SQLStep("SET_OP", op.upper()))
            break

    # ORDER BY
    order_clause = _extract_between(sql, 'ORDER\\s+BY',
        ['LIMIT', 'OFFSET', 'FETCH', 'UNION', 'EXCEPT', 'INTERSECT', 'FOR'])
    if order_clause:
        steps.append(SQLStep("SORT", "ORDER BY", detail=_truncate(order_clause)))

    # LIMIT
    limit_clause = _extract_between(sql, 'LIMIT', ['OFFSET', 'FOR', 'UNION', 'EXCEPT', 'INTERSECT'])
    offset_clause = _extract_between(sql, 'OFFSET', ['FOR', 'FETCH', 'UNION', 'EXCEPT', 'INTERSECT', 'LIMIT'])
    if limit_clause or offset_clause:
        parts = []
        if limit_clause: parts.append(f"LIMIT {limit_clause.split()[0]}")
        if offset_clause: parts.append(f"OFFSET {offset_clause.split()[0]}")
        steps.append(SQLStep("LIMIT", " / ".join(parts), shape="rounded"))

    # Result
    steps.append(SQLStep("RESULT", "Result Set", shape="stadium"))

    return steps


# ─── SVG Renderer (Visio-style, horizontal) ──────────────────────────────────

def _escape(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _wrap(text: str, width: int = 22) -> List[str]:
    if not text:
        return []
    return textwrap.wrap(text, width=width)


def render_svg(steps: List[SQLStep],
               box_w: int = 160,
               box_h: int = 60,
               gap: int = 50,
               pad_x: int = 40,
               pad_y: int = 50,
               title: str = "") -> str:

    stroke = "#444"
    stroke_w = "1"
    font = "Segoe UI, Calibri, Helvetica, Arial, sans-serif"
    label_size = 13
    detail_size = 9.5
    detail_line_h = 13

    # Compute per-box heights — expand for wrapped detail text
    box_heights = []
    detail_lines_all = []
    for step in steps:
        lines = _wrap(step.detail, 22) if step.detail else []
        detail_lines_all.append(lines)
        text_block = 20 + max(0, len(lines)) * detail_line_h + 12
        h = max(box_h, text_block)
        if step.shape == "diamond":
            h = max(h + 18, 78)
        box_heights.append(h)

    row_h = max(box_heights)  # uniform height so connector is straight

    n = len(steps)
    canvas_w = pad_x * 2 + n * box_w + (n - 1) * gap
    title_offset = 40 if title else 0
    canvas_h = pad_y * 2 + row_h + title_offset

    cy = pad_y + title_offset + row_h / 2  # vertical centre

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
               f'viewBox="0 0 {canvas_w} {canvas_h}" '
               f'width="{canvas_w}" height="{canvas_h}" '
               f'font-family="{font}">')
    svg.append(f'<rect width="{canvas_w}" height="{canvas_h}" fill="white"/>')

    # Arrow marker
    svg.append(f'''<defs>
  <marker id="ah" viewBox="0 0 10 10" refX="10" refY="5"
          markerWidth="7" markerHeight="7" orient="auto-start-auto">
    <path d="M 0 1 L 10 5 L 0 9 z" fill="{stroke}"/>
  </marker>
</defs>''')

    # Title
    if title:
        svg.append(f'<text x="{canvas_w / 2}" y="{pad_y - 4}" text-anchor="middle" '
                   f'font-size="15" font-weight="600" fill="#222">{_escape(title)}</text>')

    for i, (step, d_lines, bh) in enumerate(zip(steps, detail_lines_all, box_heights)):
        bx = pad_x + i * (box_w + gap)
        by = cy - bh / 2
        bcx = bx + box_w / 2

        # ── Connector arrow ──
        if i > 0:
            prev_x = pad_x + (i - 1) * (box_w + gap)
            prev_bh = box_heights[i - 1]
            lx1 = prev_x + box_w
            lx2 = bx

            # Adjust start/end for diamond shapes
            if steps[i - 1].shape == "diamond":
                lx1 = prev_x + box_w / 2 + box_w / 2 + 8
            if step.shape == "diamond":
                lx2 = bx + box_w / 2 - box_w / 2 - 8

            svg.append(f'<line x1="{lx1}" y1="{cy}" x2="{lx2 - 2}" y2="{cy}" '
                       f'stroke="{stroke}" stroke-width="{stroke_w}" '
                       f'marker-end="url(#ah)"/>')

        # ── Shape ──
        if step.shape == "diamond":
            dw = box_w / 2 + 8
            dh = bh / 2 + 4
            pts = (f"{bcx},{cy - dh} {bcx + dw},{cy} "
                   f"{bcx},{cy + dh} {bcx - dw},{cy}")
            svg.append(f'<polygon points="{pts}" fill="white" '
                       f'stroke="{stroke}" stroke-width="{stroke_w}"/>')

        elif step.shape == "stadium":
            r = bh / 2
            svg.append(f'<rect x="{bx}" y="{by}" width="{box_w}" height="{bh}" '
                       f'rx="{r}" fill="white" stroke="{stroke}" stroke-width="{stroke_w}"/>')

        elif step.shape == "rounded":
            svg.append(f'<rect x="{bx}" y="{by}" width="{box_w}" height="{bh}" '
                       f'rx="10" fill="white" stroke="{stroke}" stroke-width="{stroke_w}"/>')

        else:
            svg.append(f'<rect x="{bx}" y="{by}" width="{box_w}" height="{bh}" '
                       f'rx="1" fill="white" stroke="{stroke}" stroke-width="{stroke_w}"/>')

        # ── Text ──
        if d_lines:
            # Label sits above detail block, everything centred vertically
            total_text_h = 16 + len(d_lines) * detail_line_h
            text_top = cy - total_text_h / 2

            svg.append(f'<text x="{bcx}" y="{text_top + 13}" text-anchor="middle" '
                       f'font-size="{label_size}" font-weight="600" fill="#222">'
                       f'{_escape(step.label)}</text>')
            for li, line in enumerate(d_lines):
                ly = text_top + 13 + 16 + li * detail_line_h
                svg.append(f'<text x="{bcx}" y="{ly}" text-anchor="middle" '
                           f'font-size="{detail_size}" fill="#666">'
                           f'{_escape(line)}</text>')
        else:
            svg.append(f'<text x="{bcx}" y="{cy + 5}" text-anchor="middle" '
                       f'font-size="{label_size}" font-weight="600" fill="#222">'
                       f'{_escape(step.label)}</text>')

    svg.append('</svg>')
    return "\n".join(svg)


# ─── Main API ─────────────────────────────────────────────────────────────────

def sql_to_flowchart(sql: str, output_path: str = "sql_flowchart.svg", title: str = "") -> str:
    steps = parse_sql(sql)
    svg = render_svg(steps, title=title or "SQL Execution Flow")
    with open(output_path, "w") as f:
        f.write(svg)
    print(f"Flowchart saved to: {output_path}")
    return svg


# ─── CLI ──────────────────────────────────────────────────────────────────────

DEMO_SQL = """
WITH monthly_sales AS (
    SELECT DATE_TRUNC('month', o.order_date) AS month,
           c.region,
           SUM(o.amount) AS total_sales
    FROM orders o
    INNER JOIN customers c ON c.id = o.customer_id
    LEFT JOIN promotions p ON p.order_id = o.id
    WHERE o.status = 'completed'
      AND o.order_date >= '2024-01-01'
    GROUP BY DATE_TRUNC('month', o.order_date), c.region
    HAVING SUM(o.amount) > 1000
)
SELECT DISTINCT month, region, total_sales,
       RANK() OVER (PARTITION BY month ORDER BY total_sales DESC) AS rank
FROM monthly_sales
ORDER BY month, total_sales DESC
LIMIT 50;
"""

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        arg = sys.argv[1]
        if os.path.isfile(arg):
            with open(arg) as f:
                sql_input = f.read()
        else:
            sql_input = arg
    else:
        sql_input = DEMO_SQL
        print("No SQL provided — running demo query.\n")

    out_path = sys.argv[2] if len(sys.argv) >= 3 else "sql_flowchart.svg"
    sql_to_flowchart(sql_input, output_path=out_path)