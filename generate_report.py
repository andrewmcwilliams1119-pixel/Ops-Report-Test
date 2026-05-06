#!/usr/bin/env python3
"""
ANN Daily Operational Report Generator
Usage: python generate_report.py <input_file.csv|.xlsx> [output.html]
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import io, base64, sys, os

REPORT_TITLE = "ANN Daily Operational Report"

# Kobie brand palette
C_MIDNIGHT  = "#051C2C"
C_NAVY      = "#304F7F"
C_LIGHTBLUE = "#5B88EC"
C_CORAL     = "#FD7E4F"
C_PURPLE    = "#5401C8"
C_GREY      = "#EBE9FE"

# Threshold ranges (low, high) — values outside turn red
THRESHOLDS = {
    "Enrollments":                        (1_100,       5_000),
    "Loyalty Sale Transactions":          (11_352,      19_175),
    "Loyalty Return Transactions":        (13_640,      15_030),
    "Non-Loyalty Return Transactions":    (1_988,       2_747),
    "Base Points Earned":                 (4_327_566,   8_357_520),
    "Bonus Points Earned":                (6_672_329,   10_075_431),
    "Adjusted Points Earned":             (255_325,     379_061),
    "Base Points Redeemed":               (-4_913_202,  -2_021_618),
    "Bonus Points Redeemed":              (-11_256_037, -4_144_332),
    "Adjusted Points Redeemed":           (-364_761,    -219_975),
    "Base Points Expired":                (-2_128_453,  -1_318_800),
    "Bonus Points Expired":               (-789_266,    -334_009),
    "Adjusted Points Expired":            (-16_083,     -2_830),
    "Loyalty Certificates Issued Amount": (42_901.14,   109_848.69),
    "Loyalty Certificates Redeemed":      (10_400,      17_500),
    "Loyalty Certificates Redeemed Amount": (42_532.43, 109_137.48),
}


def fmt_int(n):
    if pd.isna(n): return "0"
    return f"{int(n):,}"

def fmt_currency(n):
    if pd.isna(n): return "$0.00"
    return f"${float(n):,.2f}"

def load_data(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, sep=None, engine="python")  # auto-detect delimiter
    df["Report Date"] = pd.to_datetime(df["Report Date"])
    return df.sort_values("Report Date").reset_index(drop=True)

def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")

# Distinct band colors for overlapping thresholds (light → darker green)
BAND_COLORS = ["#c8f0d8", "#8fd4b0", "#56b88a", "#2e8b6a"]

def fmt_label(n):
    """Abbreviated label for chart annotations."""
    a = abs(n)
    if a >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if a >= 1_000:     return f"{n/1_000:.1f}K"
    return f"{int(n):,}"

def style_ax(ax, labels, n_series=1):
    ax.set_facecolor("white")
    for spine in ["top", "right"]: ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]: ax.spines[spine].set_color("#cccccc")
    ax.tick_params(axis="both", labelsize=8, colors="#444")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: fmt_label(x)))
    ax.grid(axis="y", color="#eeeeee", linewidth=0.8, zorder=0)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=0, fontsize=7.5)
    ax.set_xlim(-0.5, len(labels) - 0.5)
    ax.margins(y=0.25 if n_series > 1 else 0.20)
    ax.set_axisbelow(True)

def make_chart(labels, series, fill_first=False, height=2.3):
    """
    series: list of (label, values, color, linestyle, low, high)
    Threshold bands use distinct green shades per series to avoid overlap confusion.
    Value labels shown on every data point.
    """
    fig, ax = plt.subplots(figsize=(10, height))
    x = list(range(len(labels)))
    band_idx = 0

    for label, values, color, ls, low, high in series:
        ax.plot(x, values, label=label, color=color, linestyle=ls,
                linewidth=2, zorder=3, clip_on=True, marker=None)

        # Threshold band — unique shade per series
        if low is not None and high is not None:
            lo, hi = min(low, high), max(low, high)
            bc = BAND_COLORS[band_idx % len(BAND_COLORS)]
            ax.axhspan(lo, hi, alpha=0.35, color=bc, zorder=1)
            ax.axhline(lo, color=bc, linewidth=1.0, linestyle="--", alpha=0.9, zorder=2)
            ax.axhline(hi, color=bc, linewidth=1.0, linestyle="--", alpha=0.9, zorder=2)
            band_idx += 1

        # Per-point markers + value labels
        for xi, yi in zip(x, values):
            outside = (low is not None and high is not None and
                       not (min(low, high) <= yi <= max(low, high)))
            mc = "#e53e3e" if outside else color
            ax.plot(xi, yi, "o", color=mc, markersize=4.5, zorder=4, clip_on=True)
            offset = 7 if yi >= 0 else -10
            ax.annotate(fmt_label(yi), (xi, yi),
                        textcoords="offset points", xytext=(0, offset),
                        ha="center", fontsize=6.5, color=mc, zorder=5)

    if fill_first:
        ax.fill_between(x, series[0][1], color=series[0][2], alpha=0.12, zorder=2)

    style_ax(ax, labels, n_series=len(series))
    if len(series) > 1:
        ax.legend(loc="upper right", frameon=True, framealpha=0.92,
                  edgecolor="#dddddd", fontsize=8, ncol=min(len(series), 4))
    fig.tight_layout(pad=0.5)
    return fig_to_b64(fig)


def make_bar_chart(labels, series, height=2.8):
    """
    Grouped bar chart — Kobie colors.
    series: list of (label, values, color, _, low, high)
    Value labels on every bar. Threshold lines drawn if provided.
    """
    fig, ax = plt.subplots(figsize=(10, height))
    x = np.arange(len(labels))
    n = len(series)
    width = 0.75 / n
    band_idx = 0

    for i, (label, values, color, _, low, high) in enumerate(series):
        offset = (i - n / 2 + 0.5) * width
        bars = ax.bar(x + offset, values, width * 0.92, label=label,
                      color=color, alpha=0.85, zorder=3)

        # Value labels on bars
        for bar, val in zip(bars, values):
            bh = bar.get_height()
            y_pos = bh + (abs(bh) * 0.03) if bh >= 0 else bh - (abs(bh) * 0.03)
            va = "bottom" if bh >= 0 else "top"
            ax.text(bar.get_x() + bar.get_width() / 2, y_pos,
                    fmt_label(val), ha="center", va=va,
                    fontsize=6, color="#333333", zorder=5)

        # Threshold lines
        if low is not None and high is not None:
            lo, hi = min(low, high), max(low, high)
            bc = BAND_COLORS[band_idx % len(BAND_COLORS)]
            ax.axhline(lo, color=bc, linewidth=1.0, linestyle="--", alpha=0.9, zorder=2)
            ax.axhline(hi, color=bc, linewidth=1.0, linestyle="--", alpha=0.9, zorder=2)
            band_idx += 1

    ax.axhline(0, color="#aaaaaa", linewidth=0.8, zorder=2)
    style_ax(ax, labels, n_series=n)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_xlim(-0.5, len(labels) - 0.5)
    ax.legend(loc="upper right", frameon=True, framealpha=0.92,
              edgecolor="#dddddd", fontsize=8, ncol=min(n, 4))
    fig.tight_layout(pad=0.5)
    return fig_to_b64(fig)


def generate_report(input_path, output_path=None):
    df = load_data(input_path)
    labels = [d.strftime("%-m/%-d/%Y") for d in df["Report Date"]]
    date_str = df["Report Date"].max().strftime("%A, %m/%d/%Y")
    t = df.sum(numeric_only=True)

    def col(name): return df[name].tolist()
    def neg(name): return [-v for v in df[name].tolist()]
    def thr(name): return THRESHOLDS.get(name, (None, None))

    # ── CHARTS ──────────────────────────────────────────────────────
    lo, hi = thr("Enrollments")
    img_enroll = make_chart(labels, [
        ("Enrollments", col("Enrollments"), C_LIGHTBLUE, "-", lo, hi)
    ], fill_first=True)

    img_txn = make_chart(labels, [
        ("Loyalty Sale Transactions",     col("Loyalty Sale Transactions"),     C_NAVY,      "-", *thr("Loyalty Sale Transactions")),
        ("Non-Loyalty Sale Transactions", col("Non-Loyalty Sale Transactions"), C_LIGHTBLUE, "-", None, None),
    ])

    img_returns = make_chart(labels, [
        ("Loyalty Return Transactions",     col("Loyalty Return Transactions"),     C_CORAL,  "-", *thr("Loyalty Return Transactions")),
        ("Non-Loyalty Return Transactions", col("Non-Loyalty Return Transactions"), C_PURPLE, "-", *thr("Non-Loyalty Return Transactions")),
    ])

    img_pts_earned = make_bar_chart(labels, [
        ("Base Points Earned",     col("Base Points Earned"),     C_NAVY,      "-", *thr("Base Points Earned")),
        ("Bonus Points Earned",    col("Bonus Points Earned"),    C_LIGHTBLUE, "-", *thr("Bonus Points Earned")),
        ("Adjusted Points Earned", col("Adjusted Points Earned"), C_CORAL,     "-", *thr("Adjusted Points Earned")),
    ], height=2.8)

    img_pts_redeemed = make_bar_chart(labels, [
        ("Base Points Redeemed",     col("Base Points Redeemed"),     C_NAVY,      "-", *thr("Base Points Redeemed")),
        ("Bonus Points Redeemed",    col("Bonus Points Redeemed"),    C_LIGHTBLUE, "-", *thr("Bonus Points Redeemed")),
        ("Adjusted Points Redeemed", col("Adjusted Points Redeemed"), C_CORAL,     "-", *thr("Adjusted Points Redeemed")),
    ], height=2.8)

    img_pts_expired = make_bar_chart(labels, [
        ("Base Points Expired",     col("Base Points Expired"),     C_NAVY,      "-", *thr("Base Points Expired")),
        ("Bonus Points Expired",    col("Bonus Points Expired"),    C_LIGHTBLUE, "-", *thr("Bonus Points Expired")),
        ("Adjusted Points Expired", col("Adjusted Points Expired"), C_CORAL,     "-", *thr("Adjusted Points Expired")),
    ], height=2.8)

    img_pts_forfeited = make_bar_chart(labels, [
        ("Base Points Forfeited",     col("Base Points Forfeited"),     C_NAVY,      "-", None, None),
        ("Bonus Points Forfeited",    col("Bonus Points Forfeited"),    C_LIGHTBLUE, "-", None, None),
        ("Adjusted Points Forfeited", col("Adjusted Points Forfeited"), C_CORAL,     "-", None, None),
    ], height=2.8)

    img_certs_issued = make_chart(labels, [
        ("Certificates Issued (Count)", col("Loyalty Certificates Issued"), C_NAVY, "-", None, None),
    ])

    img_certs_issued_amt = make_chart(labels, [
        ("Certificates Issued ($)", col("Loyalty Certificates Issued Amount"), C_LIGHTBLUE, "-",
         *thr("Loyalty Certificates Issued Amount")),
    ])

    img_certs_redeemed = make_chart(labels, [
        ("Certificates Redeemed (Count)", col("Loyalty Certificates Redeemed"), C_CORAL, "-",
         *thr("Loyalty Certificates Redeemed")),
    ])

    img_certs_redeemed_amt = make_chart(labels, [
        ("Certificates Redeemed ($)", col("Loyalty Certificates Redeemed Amount"), C_PURPLE, "-",
         *thr("Loyalty Certificates Redeemed Amount")),
    ])

    img_tier_up = make_chart(labels, [
        ("Tier Upgrades", col("Tier Upgrades"), C_NAVY, "-", None, None)
    ], fill_first=True)

    img_tier_down = make_chart(labels, [
        ("Tier Downgrades", col("Tier Downgrades"), C_CORAL, "-", None, None)
    ], fill_first=True)

    # ── DAILY TABLE ROWS ────────────────────────────────────────────
    rows = ""
    for _, r in df.iterrows():
        rows += f"""
        <tr>
          <td>{r['Report Date'].strftime('%-m/%-d/%Y')}</td>
          <td>{fmt_int(r['Enrollments'])}</td>
          <td>{fmt_int(r['Loyalty Sale Transactions'])}</td>
          <td>{fmt_int(r['Loyalty Return Transactions'])}</td>
          <td>{fmt_int(r['Non-Loyalty Sale Transactions'])}</td>
          <td>{fmt_int(r['Non-Loyalty Return Transactions'])}</td>
          <td>{fmt_int(r['Base Points Earned'])}</td>
          <td>{fmt_int(r['Bonus Points Earned'])}</td>
          <td>{fmt_int(r['Adjusted Points Earned'])}</td>
          <td>{fmt_int(r['Base Points Redeemed'])}</td>
          <td>{fmt_int(r['Bonus Points Redeemed'])}</td>
          <td>{fmt_int(r['Adjusted Points Redeemed'])}</td>
          <td>{fmt_int(r['Base Points Expired'])}</td>
          <td>{fmt_int(r['Bonus Points Expired'])}</td>
          <td>{fmt_int(r['Adjusted Points Expired'])}</td>
          <td>{fmt_int(r['Base Points Forfeited'])}</td>
          <td>{fmt_int(r['Bonus Points Forfeited'])}</td>
          <td>{fmt_int(r['Adjusted Points Forfeited'])}</td>
          <td>{fmt_int(r['Loyalty Certificates Issued'])}</td>
          <td>{fmt_currency(r['Loyalty Certificates Issued Amount'])}</td>
          <td>{fmt_int(r['Loyalty Certificates Redeemed'])}</td>
          <td>{fmt_currency(r['Loyalty Certificates Redeemed Amount'])}</td>
          <td>{fmt_int(r['Tier Upgrades'])}</td>
          <td>{fmt_int(r['Tier Downgrades'])}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{REPORT_TITLE} | {date_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
    background: #fff;
    color: #222;
    padding: 0 20px 40px;
  }}

  /* ── HEADER ── */
  .report-header {{
    background: {C_MIDNIGHT};
    padding: 14px 0 10px;
    text-align: center;
    margin: 0 -20px 16px;
  }}
  .report-header h1 {{ color: #fff; font-size: 20px; font-weight: 700; }}
  .report-header .date {{ color: {C_CORAL}; font-style: italic; font-size: 13px; margin-top: 3px; }}

  /* ── SECTION ── */
  .section {{
    border: 1px solid #d0d0d0;
    margin-bottom: 12px;
    background: #fff;
  }}
  .section-header {{
    background: {C_NAVY};
    color: #fff;
    font-weight: 700;
    font-size: 12px;
    padding: 6px 12px;
  }}
  .section-body {{ padding: 12px; }}
  .section-body img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; }}

  /* ── TWO-COLUMN ROW ── */
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }}

  /* ── EDITABLE FIELDS ── */
  .field-grid {{
    display: grid;
    grid-template-columns: 160px 1fr;
    row-gap: 6px;
    column-gap: 10px;
    align-items: start;
  }}
  .field-label {{ font-weight: 700; color: #333; font-size: 11.5px; padding-top: 3px; }}
  [contenteditable] {{
    border: 1px dashed #bbb;
    border-radius: 3px;
    padding: 3px 6px;
    min-height: 22px;
    font-size: 11.5px;
    color: #222;
    outline: none;
    background: #fafafa;
  }}
  [contenteditable]:focus {{ border-color: {C_LIGHTBLUE}; background: #f0f5ff; }}
  [contenteditable]:empty:before {{
    content: attr(data-placeholder);
    color: #aaa;
    font-style: italic;
  }}

  /* ── DEPLOYMENT TABLE ── */
  .deploy-table {{ width: 100%; border-collapse: collapse; font-size: 11.5px; }}
  .deploy-table th {{
    background: {C_MIDNIGHT}; color: #fff;
    padding: 5px 8px; text-align: left; font-weight: 600;
  }}
  .deploy-table td {{
    padding: 4px 8px;
    border-bottom: 1px solid #eee;
    vertical-align: top;
  }}
  .deploy-table td[contenteditable] {{
    border: none;
    border-bottom: 1px solid #eee;
    border-radius: 0;
    background: transparent;
    width: 100%;
    display: table-cell;
  }}
  .deploy-table td[contenteditable]:focus {{ background: #f0f5ff; }}
  .deploy-table tr:nth-child(even) td {{ background: {C_GREY}; }}
  .deploy-table tr:nth-child(even) td[contenteditable]:focus {{ background: #f0f5ff; }}

  /* ── NEW RELIC TABLE ── */
  .nr-table {{ width: 100%; border-collapse: collapse; font-size: 11.5px; }}
  .nr-table th {{
    background: {C_MIDNIGHT}; color: #fff;
    padding: 5px 8px; text-align: left; font-weight: 600;
  }}
  .nr-table td {{
    padding: 4px 8px; border-bottom: 1px solid #eee;
  }}
  .nr-table td[contenteditable] {{
    border: none; border-bottom: 1px solid #eee;
    border-radius: 0; background: transparent;
  }}
  .nr-table td[contenteditable]:focus {{ background: #f0f5ff; }}
  .nr-table tr:nth-child(even) td {{ background: {C_GREY}; }}

  /* ── THRESHOLD LEGEND ── */
  .threshold-note {{
    font-size: 10px; color: #666; margin-top: 4px; text-align: right;
  }}
  .dot-green {{ display:inline-block; width:8px; height:8px; border-radius:50%;
                background:#38a169; margin-right:3px; }}
  .dot-red   {{ display:inline-block; width:8px; height:8px; border-radius:50%;
                background:#e53e3e; margin-right:3px; }}

  /* ── DAILY TABLE ── */
  .table-wrap {{ overflow-x: auto; }}
  table.daily {{ width: 100%; border-collapse: collapse; font-size: 10.5px; }}
  table.daily thead th {{
    background: {C_NAVY}; color: #fff;
    text-align: right; padding: 5px 7px;
    font-weight: 600; white-space: nowrap;
  }}
  table.daily thead th:first-child {{ text-align: left; }}
  table.daily thead tr.group-header th {{
    background: {C_MIDNIGHT}; font-size: 10px;
    text-align: center; letter-spacing: 0.5px;
  }}
  table.daily tbody td {{
    padding: 4px 7px; text-align: right;
    border-bottom: 1px solid #eee; white-space: nowrap;
  }}
  table.daily tbody td:first-child {{ text-align: left; font-weight: 600; }}
  table.daily tbody tr:nth-child(even) {{ background: {C_GREY}; }}
  table.daily tfoot td {{
    background: {C_MIDNIGHT}; color: #fff;
    padding: 6px 7px; text-align: right;
    font-weight: 700; white-space: nowrap;
  }}
  table.daily tfoot td:first-child {{ text-align: left; }}

  @media print {{
    body {{ padding: 0 10px 20px; }}
    .section {{ page-break-inside: avoid; }}
    .report-header, .section-header, table.daily thead th,
    table.daily tfoot td, .deploy-table th, .nr-table th {{
      -webkit-print-color-adjust: exact; print-color-adjust: exact;
    }}
  }}
</style>
</head>
<body>

<div class="report-header">
  <h1>{REPORT_TITLE}</h1>
  <div class="date">{date_str}</div>
</div>

<!-- ── ROW 1: FUTURE DEPLOYMENTS + PINGDOM ── -->
<div class="two-col">

  <div class="section">
    <div class="section-header">Future Deployments</div>
    <div class="section-body" style="padding:0;">
      <table class="deploy-table">
        <thead>
          <tr>
            <th style="width:90px">Date</th>
            <th style="width:110px">Deploy Ticket</th>
            <th style="width:110px">JIRA Ticket</th>
            <th>Ticket Name</th>
          </tr>
        </thead>
        <tbody id="deploy-body">
          <tr>
            <td contenteditable="true" data-placeholder="Date"></td>
            <td contenteditable="true" data-placeholder="CM-XXXX"></td>
            <td contenteditable="true" data-placeholder="JIRA-XXXX"></td>
            <td contenteditable="true" data-placeholder="Ticket name"></td>
          </tr>
          <tr>
            <td contenteditable="true" data-placeholder="Date"></td>
            <td contenteditable="true" data-placeholder="CM-XXXX"></td>
            <td contenteditable="true" data-placeholder="JIRA-XXXX"></td>
            <td contenteditable="true" data-placeholder="Ticket name"></td>
          </tr>
          <tr>
            <td contenteditable="true" data-placeholder="Date"></td>
            <td contenteditable="true" data-placeholder="CM-XXXX"></td>
            <td contenteditable="true" data-placeholder="JIRA-XXXX"></td>
            <td contenteditable="true" data-placeholder="Ticket name"></td>
          </tr>
          <tr>
            <td contenteditable="true" data-placeholder="Date"></td>
            <td contenteditable="true" data-placeholder="CM-XXXX"></td>
            <td contenteditable="true" data-placeholder="JIRA-XXXX"></td>
            <td contenteditable="true" data-placeholder="Ticket name"></td>
          </tr>
          <tr>
            <td contenteditable="true" data-placeholder="Date"></td>
            <td contenteditable="true" data-placeholder="CM-XXXX"></td>
            <td contenteditable="true" data-placeholder="JIRA-XXXX"></td>
            <td contenteditable="true" data-placeholder="Ticket name"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-header">Pingdom: Web Services</div>
    <div class="section-body">
      <div style="font-weight:700;color:{C_NAVY};margin-bottom:8px;font-size:11.5px;">AMPANNWeb (Self-Service Portal)</div>
      <div class="field-grid">
        <div class="field-label">Date Range:</div>
        <div contenteditable="true" data-placeholder="e.g. 04/17 – 04/30"></div>
        <div class="field-label">Uptime (%):</div>
        <div contenteditable="true" data-placeholder="e.g. 99.95%"></div>
        <div class="field-label">Downtime (min):</div>
        <div contenteditable="true" data-placeholder="e.g. 2"></div>
        <div class="field-label">Avg Response (ms):</div>
        <div contenteditable="true" data-placeholder="e.g. 481"></div>
      </div>
      <div style="font-weight:700;color:{C_NAVY};margin:12px 0 8px;font-size:11.5px;">ANNWebService (Core Backend / API)</div>
      <div class="field-grid">
        <div class="field-label">Date Range:</div>
        <div contenteditable="true" data-placeholder="e.g. 04/17 – 04/30"></div>
        <div class="field-label">Uptime (%):</div>
        <div contenteditable="true" data-placeholder="e.g. 100.00%"></div>
        <div class="field-label">Downtime (min):</div>
        <div contenteditable="true" data-placeholder="e.g. 0"></div>
        <div class="field-label">Avg Response (ms):</div>
        <div contenteditable="true" data-placeholder="e.g. 312"></div>
      </div>
    </div>
  </div>

</div>

<!-- ── NEW RELIC ── -->
<div class="section">
  <div class="section-header">New Relic: API Web Transaction Data (Top 5 by Volume)</div>
  <div class="section-body" style="padding:0;">
    <table class="nr-table">
      <thead>
        <tr>
          <th>Transaction / API Call</th>
          <th style="width:120px;text-align:right">Count</th>
          <th style="width:180px;text-align:right">Avg Response Time (ms)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td contenteditable="true" data-placeholder="e.g. dofilterAccountCertificate"></td>
          <td contenteditable="true" data-placeholder="0" style="text-align:right"></td>
          <td contenteditable="true" data-placeholder="0.0" style="text-align:right"></td>
        </tr>
        <tr>
          <td contenteditable="true" data-placeholder="Transaction name"></td>
          <td contenteditable="true" data-placeholder="0" style="text-align:right"></td>
          <td contenteditable="true" data-placeholder="0.0" style="text-align:right"></td>
        </tr>
        <tr>
          <td contenteditable="true" data-placeholder="Transaction name"></td>
          <td contenteditable="true" data-placeholder="0" style="text-align:right"></td>
          <td contenteditable="true" data-placeholder="0.0" style="text-align:right"></td>
        </tr>
        <tr>
          <td contenteditable="true" data-placeholder="Transaction name"></td>
          <td contenteditable="true" data-placeholder="0" style="text-align:right"></td>
          <td contenteditable="true" data-placeholder="0.0" style="text-align:right"></td>
        </tr>
        <tr>
          <td contenteditable="true" data-placeholder="Transaction name"></td>
          <td contenteditable="true" data-placeholder="0" style="text-align:right"></td>
          <td contenteditable="true" data-placeholder="0.0" style="text-align:right"></td>
        </tr>
      </tbody>
    </table>
    <p style="font-size:10px;color:#666;padding:6px 12px;">
      ⚠ Note: <em>dofilterAccountCertificate</em> consistently shows a higher-than-average response time — this is expected behavior.
    </p>
  </div>
</div>

<!-- ── ENROLLMENTS ── -->
<div class="section">
  <div class="section-header">Enrollments</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_enroll}">
    <p class="threshold-note">
      <span class="dot-green"></span>Within range (1,100 – 5,000)&nbsp;&nbsp;
      <span class="dot-red"></span>Outside range
    </p>
  </div>
</div>

<!-- ── TRANSACTIONS ── -->
<div class="section">
  <div class="section-header">Transactions</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_txn}">
    <p class="threshold-note">
      <span class="dot-green"></span>Loyalty Sales range: 11,352 – 19,175&nbsp;&nbsp;
      <span class="dot-red"></span>Outside range
    </p>
  </div>
</div>

<!-- ── RETURN TRANSACTIONS ── -->
<div class="section">
  <div class="section-header">Return Transactions</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_returns}">
    <p class="threshold-note">
      <span class="dot-green"></span>Loyalty Returns: 13,640 – 15,030 &nbsp;|&nbsp;
      Non-Loyalty Returns: 1,988 – 2,747&nbsp;&nbsp;
      <span class="dot-red"></span>Outside range
    </p>
  </div>
</div>

<!-- ── POINTS EARNED ── -->
<div class="section">
  <div class="section-header">Points Earned</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_pts_earned}">
    <p class="threshold-note">
      <span class="dot-green"></span>Base: 4,327,566 – 8,357,520 &nbsp;|&nbsp;
      Bonus: 6,672,329 – 10,075,431 &nbsp;|&nbsp;
      Adjusted: 255,325 – 379,061&nbsp;&nbsp;
      <span class="dot-red"></span>Outside range
    </p>
  </div>
</div>

<!-- ── POINTS REDEEMED ── -->
<div class="section">
  <div class="section-header">Points Redeemed</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_pts_redeemed}">
    <p class="threshold-note">
      <span class="dot-green"></span>Base: -4,913,202 – -2,021,618 &nbsp;|&nbsp;
      Bonus: -11,256,037 – -4,144,332 &nbsp;|&nbsp;
      Adjusted: -364,761 – -219,975&nbsp;&nbsp;
      <span class="dot-red"></span>Outside range
    </p>
  </div>
</div>

<!-- ── POINTS EXPIRED ── -->
<div class="section">
  <div class="section-header">Points Expired</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_pts_expired}">
    <p class="threshold-note">
      <span class="dot-green"></span>Base: -2,128,453 – -1,318,800 &nbsp;|&nbsp;
      Bonus: -789,266 – -334,009 &nbsp;|&nbsp;
      Adjusted: -16,083 – -2,830&nbsp;&nbsp;
      <span class="dot-red"></span>Outside range
    </p>
  </div>
</div>

<!-- ── POINTS FORFEITED ── -->
<div class="section">
  <div class="section-header">Points Forfeited</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_pts_forfeited}">
    <p class="threshold-note" style="color:#aaa;">
      Note: ANN forfeiture includes Returns, Account Closures &amp; Data Cleanups.
    </p>
  </div>
</div>

<!-- ── CERTIFICATES ISSUED ── -->
<div class="section">
  <div class="section-header">Loyalty Certificates Issued</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_certs_issued}">
    <img src="data:image/png;base64,{img_certs_issued_amt}" style="margin-top:8px;">
    <p class="threshold-note">
      <span class="dot-green"></span>Issued Amount range: $42,901 – $109,849&nbsp;&nbsp;
      <span class="dot-red"></span>Outside range
    </p>
  </div>
</div>

<!-- ── CERTIFICATES REDEEMED ── -->
<div class="section">
  <div class="section-header">Loyalty Certificates Redeemed</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_certs_redeemed}">
    <img src="data:image/png;base64,{img_certs_redeemed_amt}" style="margin-top:8px;">
    <p class="threshold-note">
      <span class="dot-green"></span>Count range: 4,030 – 10,102 &nbsp;|&nbsp;
      Amount range: $42,532 – $109,137&nbsp;&nbsp;
      <span class="dot-red"></span>Outside range
    </p>
  </div>
</div>

<!-- ── TIER UPGRADES ── -->
<div class="section">
  <div class="section-header">Tier Upgrades</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_tier_up}">
  </div>
</div>

<!-- ── TIER DOWNGRADES ── -->
<div class="section">
  <div class="section-header">Tier Downgrades</div>
  <div class="section-body">
    <img src="data:image/png;base64,{img_tier_down}">
    <p class="threshold-note" style="color:#aaa;">
      Note: Tier downgrades are tracked monthly. Spikes typically occur at start of month/quarter.
    </p>
  </div>
</div>

<!-- ── DAILY BREAKDOWN TABLE ── -->
<div class="section">
  <div class="section-header">Daily Breakdown</div>
  <div class="section-body" style="padding:0;">
    <div class="table-wrap">
    <table class="daily">
      <thead>
        <tr class="group-header">
          <th rowspan="2" style="text-align:left">Date</th>
          <th rowspan="2">Enrollments</th>
          <th colspan="2">Loyalty Transactions</th>
          <th colspan="2">Non-Loyalty Transactions</th>
          <th colspan="3">Points Earned</th>
          <th colspan="3">Points Redeemed</th>
          <th colspan="3">Points Expired</th>
          <th colspan="3">Points Forfeited</th>
          <th colspan="2">Certs Issued</th>
          <th colspan="2">Certs Redeemed</th>
          <th rowspan="2">Tier Up</th>
          <th rowspan="2">Tier Down</th>
        </tr>
        <tr>
          <th>Sales</th><th>Returns</th>
          <th>Sales</th><th>Returns</th>
          <th>Base</th><th>Bonus</th><th>Adj</th>
          <th>Base</th><th>Bonus</th><th>Adj</th>
          <th>Base</th><th>Bonus</th><th>Adj</th>
          <th>Base</th><th>Bonus</th><th>Adj</th>
          <th>Count</th><th>Amount</th>
          <th>Count</th><th>Amount</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
      <tfoot>
        <tr>
          <td>TOTAL</td>
          <td>{fmt_int(t['Enrollments'])}</td>
          <td>{fmt_int(t['Loyalty Sale Transactions'])}</td>
          <td>{fmt_int(t['Loyalty Return Transactions'])}</td>
          <td>{fmt_int(t['Non-Loyalty Sale Transactions'])}</td>
          <td>{fmt_int(t['Non-Loyalty Return Transactions'])}</td>
          <td>{fmt_int(t['Base Points Earned'])}</td>
          <td>{fmt_int(t['Bonus Points Earned'])}</td>
          <td>{fmt_int(t['Adjusted Points Earned'])}</td>
          <td>{fmt_int(t['Base Points Redeemed'])}</td>
          <td>{fmt_int(t['Bonus Points Redeemed'])}</td>
          <td>{fmt_int(t['Adjusted Points Redeemed'])}</td>
          <td>{fmt_int(t['Base Points Expired'])}</td>
          <td>{fmt_int(t['Bonus Points Expired'])}</td>
          <td>{fmt_int(t['Adjusted Points Expired'])}</td>
          <td>{fmt_int(t['Base Points Forfeited'])}</td>
          <td>{fmt_int(t['Bonus Points Forfeited'])}</td>
          <td>{fmt_int(t['Adjusted Points Forfeited'])}</td>
          <td>{fmt_int(t['Loyalty Certificates Issued'])}</td>
          <td>{fmt_currency(t['Loyalty Certificates Issued Amount'])}</td>
          <td>{fmt_int(t['Loyalty Certificates Redeemed'])}</td>
          <td>{fmt_currency(t['Loyalty Certificates Redeemed Amount'])}</td>
          <td>{fmt_int(t['Tier Upgrades'])}</td>
          <td>{fmt_int(t['Tier Downgrades'])}</td>
        </tr>
      </tfoot>
    </table>
    </div>
  </div>
</div>

<script>
// Persist editable field content in localStorage so it survives page refresh
document.querySelectorAll('[contenteditable]').forEach((el, i) => {{
  const key = 'ann_report_field_' + i;
  if (localStorage.getItem(key)) el.innerHTML = localStorage.getItem(key);
  el.addEventListener('input', () => localStorage.setItem(key, el.innerHTML));
}});
</script>

</body>
</html>"""

    if output_path is None:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = f"{base}_report.html"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report generated: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_report.py <input_file> [output.html]")
        sys.exit(1)
    generate_report(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
