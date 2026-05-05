#!/usr/bin/env python3
"""
ANN Daily Operational Report Generator
Usage: python generate_report.py <input_file.csv|.xlsx> [output.html]
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import io
import base64
import sys
import os

REPORT_TITLE = "ANN Daily Operational Report"

# Kobie brand palette
C_MIDNIGHT  = "#051C2C"
C_NAVY      = "#304F7F"
C_LIGHTBLUE = "#5B88EC"
C_CORAL     = "#FD7E4F"
C_PURPLE    = "#5401C8"
C_GREY      = "#EBE9FE"
C_WHITE     = "#FFFFFF"

# Chart alias
C_BLUE      = C_NAVY
C_GREEN     = C_NAVY
C_RED       = C_CORAL
C_ORANGE    = C_LIGHTBLUE
C_FILL      = C_LIGHTBLUE


def fmt_int(n):
    if pd.isna(n):
        return "0"
    return f"{int(n):,}"


def fmt_currency(n):
    if pd.isna(n):
        return "$0.00"
    return f"${float(n):,.2f}"


def load_data(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    df["Report Date"] = pd.to_datetime(df["Report Date"])
    df = df.sort_values("Report Date").reset_index(drop=True)
    return df


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def style_axes(ax, labels):
    ax.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cccccc")
    ax.spines["bottom"].set_color("#cccccc")
    ax.tick_params(axis="both", labelsize=8, colors="#444444")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="y", color="#eeeeee", linewidth=0.8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=0, fontsize=7.5)


def make_line_chart(labels, series, fill=False, height=2.2, with_labels=True):
    """series: list of (label, values, color, linestyle)"""
    fig, ax = plt.subplots(figsize=(10, height))
    x = list(range(len(labels)))

    for label, values, color, ls in series:
        ax.plot(x, values, label=label, color=color, linestyle=ls,
                linewidth=2, marker="o", markersize=4)
        if with_labels and len(series) <= 2:
            for xi, yi in zip(x, values):
                ax.annotate(f"{int(yi):,}", (xi, yi),
                            textcoords="offset points", xytext=(0, 6),
                            ha="center", fontsize=7, color="#333333")

    if fill and len(series) == 1:
        ax.fill_between(x, series[0][1], color=series[0][2], alpha=0.18)

    style_axes(ax, labels)
    if len(series) > 1:
        ax.legend(loc="upper right", frameon=False, fontsize=8.5,
                  ncol=min(len(series), 4))
    fig.tight_layout()
    return fig_to_base64(fig)


def generate_report(input_path, output_path=None):
    df = load_data(input_path)

    labels = [d.strftime("%-m/%-d/%Y") for d in df["Report Date"]]
    end_date = df["Report Date"].max()
    date_str = end_date.strftime("%A, %m/%d/%Y")

    # Series
    enrollments    = df["Enrollments"].astype(int).tolist()
    loy_sales      = df["Loyalty Sale Transactions"].astype(int).tolist()
    nonloy_sales   = df["Non-Loyalty Sale Transactions"].astype(int).tolist()
    loy_returns    = df["Loyalty Return Transactions"].astype(int).tolist()
    nonloy_returns = df["Non-Loyalty Return Transactions"].astype(int).tolist()
    base_earned    = df["Base Points Earned"].astype(int).tolist()
    bonus_earned   = df["Bonus Points Earned"].astype(int).tolist()
    base_redeemed  = [-int(x) for x in df["Base Points Redeemed"]]
    bonus_redeemed = [-int(x) for x in df["Bonus Points Redeemed"]]
    certs_issued   = df["Loyalty Certificates Issued"].astype(int).tolist()
    certs_redeemed = df["Loyalty Certificates Redeemed"].astype(int).tolist()
    tier_up        = df["Tier Upgrades"].astype(int).tolist()

    # Charts
    img_enrollments = make_line_chart(
        labels, [("Enrollments", enrollments, C_FILL, "-")],
        fill=True, with_labels=False)

    img_transactions = make_line_chart(
        labels,
        [("Loyalty Sale Transactions",     loy_sales,    C_NAVY,      "-"),
         ("Non-Loyalty Sale Transactions", nonloy_sales, C_LIGHTBLUE, "-")],
        with_labels=False)

    img_returns = make_line_chart(
        labels,
        [("Loyalty Return Transactions",     loy_returns,    C_CORAL,  "-"),
         ("Non-Loyalty Return Transactions", nonloy_returns, C_PURPLE, "-")],
        with_labels=False)

    img_points = make_line_chart(
        labels,
        [("Base Points Earned",    base_earned,    C_NAVY,      "-"),
         ("Bonus Points Earned",   bonus_earned,   C_LIGHTBLUE, "-"),
         ("Base Points Redeemed",  base_redeemed,  C_CORAL,     "--"),
         ("Bonus Points Redeemed", bonus_redeemed, C_PURPLE,    "--")],
        height=2.6, with_labels=False)

    img_certs = make_line_chart(
        labels,
        [("Certificates Issued",   certs_issued,   C_NAVY,  "-"),
         ("Certificates Redeemed", certs_redeemed, C_CORAL, "-")],
        with_labels=False)

    img_tier = make_line_chart(
        labels, [("Tier Upgrades", tier_up, C_PURPLE, "-")],
        fill=True, with_labels=False)

    # Daily table
    t = df.sum(numeric_only=True)
    rows_html = ""
    for _, r in df.iterrows():
        rows_html += f"""
        <tr>
          <td>{r['Report Date'].strftime('%-m/%-d/%Y')}</td>
          <td>{fmt_int(r['Enrollments'])}</td>
          <td>{fmt_int(r['Loyalty Sale Transactions'])}</td>
          <td>{fmt_int(r['Loyalty Return Transactions'])}</td>
          <td>{fmt_int(r['Non-Loyalty Sale Transactions'])}</td>
          <td>{fmt_int(r['Non-Loyalty Return Transactions'])}</td>
          <td>{fmt_int(r['Base Points Earned'] + r['Bonus Points Earned'] + r['Adjusted Points Earned'])}</td>
          <td>{fmt_int(-(r['Base Points Redeemed'] + r['Bonus Points Redeemed'] + r['Adjusted Points Redeemed']))}</td>
          <td>{fmt_int(r['Loyalty Certificates Issued'])}</td>
          <td>{fmt_currency(r['Loyalty Certificates Issued Amount'])}</td>
          <td>{fmt_int(r['Loyalty Certificates Redeemed'])}</td>
          <td>{fmt_currency(r['Loyalty Certificates Redeemed Amount'])}</td>
          <td>{fmt_int(r['Tier Upgrades'])}</td>
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
    background: #ffffff;
    color: #222;
    padding: 0 24px 40px;
  }}
  .report-header {{
    background: #051C2C;
    padding: 14px 0 10px;
    text-align: center;
    margin: 0 -24px 18px;
  }}
  .report-header h1 {{
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }}
  .report-header .date {{
    color: #FD7E4F;
    font-style: italic;
    font-size: 13px;
    margin-top: 2px;
  }}
  .section {{
    border: 1px solid #d0d0d0;
    margin-bottom: 14px;
    background: #ffffff;
  }}
  .section-header {{
    background: #304F7F;
    color: #ffffff;
    font-weight: 700;
    font-size: 12px;
    padding: 6px 12px;
  }}
  .section-body {{
    padding: 12px;
    text-align: center;
  }}
  .section-body img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
  }}
  thead th {{
    background: #304F7F;
    color: #ffffff;
    text-align: right;
    padding: 6px 8px;
    font-weight: 600;
    white-space: nowrap;
  }}
  thead th:first-child {{ text-align: left; }}
  tbody td {{
    padding: 5px 8px;
    text-align: right;
    border-bottom: 1px solid #eee;
    white-space: nowrap;
  }}
  tbody td:first-child {{ text-align: left; font-weight: 600; }}
  tbody tr:nth-child(even) {{ background: #EBE9FE; }}
  tfoot td {{
    background: #051C2C;
    color: #ffffff;
    padding: 7px 8px;
    text-align: right;
    font-weight: 700;
    white-space: nowrap;
  }}
  tfoot td:first-child {{ text-align: left; }}
  @media print {{
    body {{ padding: 0 12px 20px; }}
    .section {{ page-break-inside: avoid; }}
    .report-header, thead th, tfoot td, .section-header {{
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

<div class="section">
  <div class="section-header">Enrollments</div>
  <div class="section-body"><img src="data:image/png;base64,{img_enrollments}"></div>
</div>

<div class="section">
  <div class="section-header">Transactions</div>
  <div class="section-body"><img src="data:image/png;base64,{img_transactions}"></div>
</div>

<div class="section">
  <div class="section-header">Return Transactions</div>
  <div class="section-body"><img src="data:image/png;base64,{img_returns}"></div>
</div>

<div class="section">
  <div class="section-header">Points Activity (Earned vs Redeemed)</div>
  <div class="section-body"><img src="data:image/png;base64,{img_points}"></div>
</div>

<div class="section">
  <div class="section-header">Loyalty Certificates</div>
  <div class="section-body"><img src="data:image/png;base64,{img_certs}"></div>
</div>

<div class="section">
  <div class="section-header">Tier Upgrades</div>
  <div class="section-body"><img src="data:image/png;base64,{img_tier}"></div>
</div>

<div class="section">
  <div class="section-header">Daily Breakdown</div>
  <div class="section-body" style="padding:0;">
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Enroll</th>
          <th>Loy Sales</th>
          <th>Loy Returns</th>
          <th>Non-Loy Sales</th>
          <th>Non-Loy Returns</th>
          <th>Pts Earned</th>
          <th>Pts Redeemed</th>
          <th>Certs Issued</th>
          <th>Issued $</th>
          <th>Certs Redeemed</th>
          <th>Redeemed $</th>
          <th>Tier Up</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
      <tfoot>
        <tr>
          <td>TOTAL</td>
          <td>{fmt_int(t['Enrollments'])}</td>
          <td>{fmt_int(t['Loyalty Sale Transactions'])}</td>
          <td>{fmt_int(t['Loyalty Return Transactions'])}</td>
          <td>{fmt_int(t['Non-Loyalty Sale Transactions'])}</td>
          <td>{fmt_int(t['Non-Loyalty Return Transactions'])}</td>
          <td>{fmt_int(t['Base Points Earned'] + t['Bonus Points Earned'] + t['Adjusted Points Earned'])}</td>
          <td>{fmt_int(-(t['Base Points Redeemed'] + t['Bonus Points Redeemed'] + t['Adjusted Points Redeemed']))}</td>
          <td>{fmt_int(t['Loyalty Certificates Issued'])}</td>
          <td>{fmt_currency(t['Loyalty Certificates Issued Amount'])}</td>
          <td>{fmt_int(t['Loyalty Certificates Redeemed'])}</td>
          <td>{fmt_currency(t['Loyalty Certificates Redeemed Amount'])}</td>
          <td>{fmt_int(t['Tier Upgrades'])}</td>
        </tr>
      </tfoot>
    </table>
  </div>
</div>

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
