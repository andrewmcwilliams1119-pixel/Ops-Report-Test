#!/usr/bin/env python3
"""
Operations Report Generator
Usage: python generate_report.py <input_file.csv or input_file.xlsx> [output_file.html]
"""

import pandas as pd
import sys
import os
from datetime import datetime


def fmt_int(n):
    if pd.isna(n):
        return "0"
    return f"{int(n):,}"


def fmt_currency(n):
    if pd.isna(n):
        return "$0.00"
    return f"${float(n):,.2f}"


def fmt_pts(n):
    """Format points — always show sign for redeemed/expired/forfeited."""
    if pd.isna(n):
        return "0"
    val = int(n)
    return f"{val:,}"


def load_data(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    df["Report Date"] = pd.to_datetime(df["Report Date"])
    df = df.sort_values("Report Date").reset_index(drop=True)
    return df


def build_daily_rows(df):
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
            <td>{fmt_pts(r['Base Points Earned'])}</td>
            <td>{fmt_pts(r['Bonus Points Earned'])}</td>
            <td>{fmt_pts(r['Adjusted Points Earned'])}</td>
            <td>{fmt_pts(r['Base Points Redeemed'])}</td>
            <td>{fmt_pts(r['Bonus Points Redeemed'])}</td>
            <td>{fmt_pts(r['Adjusted Points Redeemed'])}</td>
            <td>{fmt_pts(r['Base Points Expired'])}</td>
            <td>{fmt_pts(r['Bonus Points Expired'])}</td>
            <td>{fmt_pts(r['Adjusted Points Expired'])}</td>
            <td>{fmt_pts(r['Base Points Forfeited'])}</td>
            <td>{fmt_pts(r['Bonus Points Forfeited'])}</td>
            <td>{fmt_pts(r['Adjusted Points Forfeited'])}</td>
            <td>{fmt_int(r['Loyalty Certificates Issued'])}</td>
            <td>{fmt_currency(r['Loyalty Certificates Issued Amount'])}</td>
            <td>{fmt_int(r['Loyalty Certificates Redeemed'])}</td>
            <td>{fmt_currency(r['Loyalty Certificates Redeemed Amount'])}</td>
            <td>{fmt_currency(r['Daily $20 Birthday Certificate'])}</td>
            <td>{fmt_int(r['Tier Upgrades'])}</td>
            <td>{fmt_int(r['Tier Downgrades'])}</td>
        </tr>"""
    return rows


def generate_report(input_path, output_path=None):
    df = load_data(input_path)

    t = df.sum(numeric_only=True)
    avg = df.mean(numeric_only=True)

    start = df["Report Date"].min().strftime("%B %d, %Y")
    end = df["Report Date"].max().strftime("%B %d, %Y")
    num_days = len(df)
    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    net_loyalty_txn = int(t["Loyalty Sale Transactions"]) + int(t["Loyalty Return Transactions"])
    net_nonloyalty_txn = int(t["Non-Loyalty Sale Transactions"]) + int(t["Non-Loyalty Return Transactions"])

    daily_rows = build_daily_rows(df)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Operations Report | {start} &ndash; {end}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    background: #f0f2f5;
    color: #1a1a2e;
  }}

  /* ── HEADER ── */
  .report-header {{
    background: #1a1a2e;
    color: #ffffff;
    padding: 28px 40px 22px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }}
  .report-header h1 {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }}
  .report-header .subtitle {{
    font-size: 14px;
    color: #a0aec0;
    margin-top: 4px;
  }}
  .report-header .meta {{
    text-align: right;
    font-size: 12px;
    color: #a0aec0;
    line-height: 1.8;
  }}
  .report-header .meta strong {{
    color: #ffffff;
  }}

  /* ── CONTENT ── */
  .content {{ padding: 30px 40px 50px; }}

  /* ── SECTION TITLES ── */
  .section-title {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #718096;
    margin: 28px 0 12px;
    padding-bottom: 6px;
    border-bottom: 2px solid #e2e8f0;
  }}

  /* ── KPI CARDS ── */
  .kpi-grid {{
    display: grid;
    gap: 14px;
  }}
  .kpi-grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
  .kpi-grid-4 {{ grid-template-columns: repeat(4, 1fr); }}
  .kpi-grid-5 {{ grid-template-columns: repeat(5, 1fr); }}
  .kpi-grid-6 {{ grid-template-columns: repeat(6, 1fr); }}

  .kpi-card {{
    background: #ffffff;
    border-radius: 8px;
    padding: 18px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    border-left: 4px solid #4a90d9;
  }}
  .kpi-card.green  {{ border-left-color: #38a169; }}
  .kpi-card.red    {{ border-left-color: #e53e3e; }}
  .kpi-card.purple {{ border-left-color: #805ad5; }}
  .kpi-card.orange {{ border-left-color: #dd6b20; }}
  .kpi-card.teal   {{ border-left-color: #319795; }}
  .kpi-card.gray   {{ border-left-color: #718096; }}

  .kpi-label {{
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #718096;
    margin-bottom: 6px;
  }}
  .kpi-value {{
    font-size: 22px;
    font-weight: 700;
    color: #1a1a2e;
    line-height: 1.1;
  }}
  .kpi-sub {{
    font-size: 11px;
    color: #a0aec0;
    margin-top: 4px;
  }}

  /* Points cards: show base / bonus / adjusted in one card */
  .pts-card {{
    background: #ffffff;
    border-radius: 8px;
    padding: 18px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    border-left: 4px solid #4a90d9;
  }}
  .pts-card.green  {{ border-left-color: #38a169; }}
  .pts-card.red    {{ border-left-color: #e53e3e; }}
  .pts-card.orange {{ border-left-color: #dd6b20; }}
  .pts-card.gray   {{ border-left-color: #718096; }}

  .pts-title {{
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #4a5568;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e2e8f0;
  }}
  .pts-row {{
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
  }}
  .pts-row-label {{
    font-size: 11.5px;
    color: #718096;
  }}
  .pts-row-value {{
    font-size: 12px;
    font-weight: 600;
    color: #1a1a2e;
  }}
  .pts-row.adjusted .pts-row-label {{
    color: #1a1a2e;
    font-weight: 700;
  }}
  .pts-row.adjusted .pts-row-value {{
    font-size: 13px;
    color: #1a1a2e;
  }}

  /* ── CERT CARD ── */
  .cert-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
  }}

  /* ── DAILY TABLE ── */
  .table-wrapper {{
    overflow-x: auto;
    background: #ffffff;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    margin-top: 4px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11.5px;
  }}
  thead tr {{
    background: #1a1a2e;
    color: #ffffff;
  }}
  thead th {{
    padding: 10px 10px;
    text-align: right;
    font-weight: 600;
    font-size: 10.5px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
  }}
  thead th:first-child {{ text-align: left; }}
  thead tr.subhead {{
    background: #2d3748;
    color: #a0aec0;
    font-size: 9.5px;
  }}
  thead tr.subhead th {{ padding: 4px 10px 6px; }}

  tbody tr {{ border-bottom: 1px solid #e2e8f0; }}
  tbody tr:nth-child(even) {{ background: #f7fafc; }}
  tbody tr:hover {{ background: #ebf4ff; }}
  tbody td {{
    padding: 8px 10px;
    text-align: right;
    white-space: nowrap;
    color: #2d3748;
  }}
  tbody td:first-child {{
    text-align: left;
    font-weight: 600;
    color: #1a1a2e;
  }}

  tfoot tr {{ background: #2d3748; color: #ffffff; font-weight: 700; }}
  tfoot td {{
    padding: 9px 10px;
    text-align: right;
    white-space: nowrap;
    font-size: 12px;
  }}
  tfoot td:first-child {{ text-align: left; }}

  /* column group backgrounds */
  .col-enroll  {{ border-left: 3px solid #4a90d9; }}
  .col-loy     {{ border-left: 3px solid #38a169; }}
  .col-nonloy  {{ border-left: 3px solid #805ad5; }}
  .col-earned  {{ border-left: 3px solid #38a169; }}
  .col-redeem  {{ border-left: 3px solid #e53e3e; }}
  .col-expire  {{ border-left: 3px solid #dd6b20; }}
  .col-forfeit {{ border-left: 3px solid #718096; }}
  .col-cert    {{ border-left: 3px solid #319795; }}
  .col-tier    {{ border-left: 3px solid #4a90d9; }}

  /* ── PRINT ── */
  @media print {{
    body {{ background: white; font-size: 11px; }}
    .content {{ padding: 20px; }}
    .report-header {{ padding: 16px 20px; }}
    .kpi-value {{ font-size: 18px; }}
    .table-wrapper {{ box-shadow: none; }}
    thead tr {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    tfoot tr  {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .kpi-card, .pts-card {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>

<!-- ════════════════════════════════════════════
     HEADER
════════════════════════════════════════════ -->
<div class="report-header">
  <div>
    <h1>Operations Report</h1>
    <div class="subtitle">{start} &ndash; {end} &nbsp;|&nbsp; {num_days} Days</div>
  </div>
  <div class="meta">
    <strong>Generated</strong><br>{generated}
  </div>
</div>

<div class="content">

<!-- ════════════════════════════════════════════
     SECTION 1 — ENROLLMENTS & TRANSACTIONS
════════════════════════════════════════════ -->
<div class="section-title">Enrollments &amp; Transactions</div>
<div class="kpi-grid kpi-grid-5">

  <div class="kpi-card">
    <div class="kpi-label">Total Enrollments</div>
    <div class="kpi-value">{fmt_int(t['Enrollments'])}</div>
    <div class="kpi-sub">Avg {fmt_int(avg['Enrollments'])} / day</div>
  </div>

  <div class="kpi-card green">
    <div class="kpi-label">Loyalty Sale Transactions</div>
    <div class="kpi-value">{fmt_int(t['Loyalty Sale Transactions'])}</div>
    <div class="kpi-sub">Avg {fmt_int(avg['Loyalty Sale Transactions'])} / day</div>
  </div>

  <div class="kpi-card red">
    <div class="kpi-label">Loyalty Return Transactions</div>
    <div class="kpi-value">{fmt_int(t['Loyalty Return Transactions'])}</div>
    <div class="kpi-sub">Avg {fmt_int(avg['Loyalty Return Transactions'])} / day</div>
  </div>

  <div class="kpi-card purple">
    <div class="kpi-label">Non-Loyalty Sale Transactions</div>
    <div class="kpi-value">{fmt_int(t['Non-Loyalty Sale Transactions'])}</div>
    <div class="kpi-sub">Avg {fmt_int(avg['Non-Loyalty Sale Transactions'])} / day</div>
  </div>

  <div class="kpi-card purple">
    <div class="kpi-label">Non-Loyalty Return Transactions</div>
    <div class="kpi-value">{fmt_int(t['Non-Loyalty Return Transactions'])}</div>
    <div class="kpi-sub">Avg {fmt_int(avg['Non-Loyalty Return Transactions'])} / day</div>
  </div>

</div>

<!-- ════════════════════════════════════════════
     SECTION 2 — POINTS ACTIVITY
════════════════════════════════════════════ -->
<div class="section-title">Points Activity</div>
<div class="kpi-grid kpi-grid-4">

  <!-- EARNED -->
  <div class="pts-card green">
    <div class="pts-title">Points Earned</div>
    <div class="pts-row">
      <span class="pts-row-label">Base</span>
      <span class="pts-row-value">{fmt_pts(t['Base Points Earned'])}</span>
    </div>
    <div class="pts-row">
      <span class="pts-row-label">Bonus</span>
      <span class="pts-row-value">{fmt_pts(t['Bonus Points Earned'])}</span>
    </div>
    <div class="pts-row adjusted">
      <span class="pts-row-label">Adjusted</span>
      <span class="pts-row-value">{fmt_pts(t['Adjusted Points Earned'])}</span>
    </div>
  </div>

  <!-- REDEEMED -->
  <div class="pts-card red">
    <div class="pts-title">Points Redeemed</div>
    <div class="pts-row">
      <span class="pts-row-label">Base</span>
      <span class="pts-row-value">{fmt_pts(t['Base Points Redeemed'])}</span>
    </div>
    <div class="pts-row">
      <span class="pts-row-label">Bonus</span>
      <span class="pts-row-value">{fmt_pts(t['Bonus Points Redeemed'])}</span>
    </div>
    <div class="pts-row adjusted">
      <span class="pts-row-label">Adjusted</span>
      <span class="pts-row-value">{fmt_pts(t['Adjusted Points Redeemed'])}</span>
    </div>
  </div>

  <!-- EXPIRED -->
  <div class="pts-card orange">
    <div class="pts-title">Points Expired</div>
    <div class="pts-row">
      <span class="pts-row-label">Base</span>
      <span class="pts-row-value">{fmt_pts(t['Base Points Expired'])}</span>
    </div>
    <div class="pts-row">
      <span class="pts-row-label">Bonus</span>
      <span class="pts-row-value">{fmt_pts(t['Bonus Points Expired'])}</span>
    </div>
    <div class="pts-row adjusted">
      <span class="pts-row-label">Adjusted</span>
      <span class="pts-row-value">{fmt_pts(t['Adjusted Points Expired'])}</span>
    </div>
  </div>

  <!-- FORFEITED -->
  <div class="pts-card gray">
    <div class="pts-title">Points Forfeited</div>
    <div class="pts-row">
      <span class="pts-row-label">Base</span>
      <span class="pts-row-value">{fmt_pts(t['Base Points Forfeited'])}</span>
    </div>
    <div class="pts-row">
      <span class="pts-row-label">Bonus</span>
      <span class="pts-row-value">{fmt_pts(t['Bonus Points Forfeited'])}</span>
    </div>
    <div class="pts-row adjusted">
      <span class="pts-row-label">Adjusted</span>
      <span class="pts-row-value">{fmt_pts(t['Adjusted Points Forfeited'])}</span>
    </div>
  </div>

</div>

<!-- ════════════════════════════════════════════
     SECTION 3 — CERTIFICATES & TIER ACTIVITY
════════════════════════════════════════════ -->
<div class="section-title">Certificates &amp; Tier Activity</div>
<div class="kpi-grid kpi-grid-5">

  <div class="kpi-card teal">
    <div class="kpi-label">Certificates Issued</div>
    <div class="kpi-value">{fmt_int(t['Loyalty Certificates Issued'])}</div>
    <div class="kpi-sub">{fmt_currency(t['Loyalty Certificates Issued Amount'])} total value</div>
  </div>

  <div class="kpi-card teal">
    <div class="kpi-label">Certificates Redeemed</div>
    <div class="kpi-value">{fmt_int(t['Loyalty Certificates Redeemed'])}</div>
    <div class="kpi-sub">{fmt_currency(t['Loyalty Certificates Redeemed Amount'])} total value</div>
  </div>

  <div class="kpi-card orange">
    <div class="kpi-label">Daily $20 Birthday Cert.</div>
    <div class="kpi-value">{fmt_currency(t['Daily $20 Birthday Certificate'])}</div>
    <div class="kpi-sub">Total issued value</div>
  </div>

  <div class="kpi-card green">
    <div class="kpi-label">Tier Upgrades</div>
    <div class="kpi-value">{fmt_int(t['Tier Upgrades'])}</div>
    <div class="kpi-sub">Avg {fmt_int(avg['Tier Upgrades'])} / day</div>
  </div>

  <div class="kpi-card red">
    <div class="kpi-label">Tier Downgrades</div>
    <div class="kpi-value">{fmt_int(t['Tier Downgrades'])}</div>
    <div class="kpi-sub">Avg {fmt_int(avg['Tier Downgrades'])} / day</div>
  </div>

</div>

<!-- ════════════════════════════════════════════
     SECTION 4 — DAILY BREAKDOWN
════════════════════════════════════════════ -->
<div class="section-title">Daily Breakdown</div>
<div class="table-wrapper">
<table>
  <thead>
    <tr>
      <!-- grouping header row -->
      <th rowspan="2" style="text-align:left;">Date</th>
      <th rowspan="2" class="col-enroll">Enrollments</th>
      <th colspan="2" class="col-loy" style="text-align:center;">Loyalty Transactions</th>
      <th colspan="2" class="col-nonloy" style="text-align:center;">Non-Loyalty Transactions</th>
      <th colspan="3" class="col-earned" style="text-align:center;">Points Earned</th>
      <th colspan="3" class="col-redeem" style="text-align:center;">Points Redeemed</th>
      <th colspan="3" class="col-expire" style="text-align:center;">Points Expired</th>
      <th colspan="3" class="col-forfeit" style="text-align:center;">Points Forfeited</th>
      <th colspan="2" class="col-cert" style="text-align:center;">Certs Issued</th>
      <th colspan="2" class="col-cert" style="text-align:center;">Certs Redeemed</th>
      <th rowspan="2" class="col-cert">Birthday Cert</th>
      <th rowspan="2" class="col-tier">Tier Up</th>
      <th rowspan="2" class="col-tier">Tier Down</th>
    </tr>
    <tr class="subhead">
      <!-- Loyalty Txn -->
      <th class="col-loy">Sales</th>
      <th>Returns</th>
      <!-- Non-Loyalty Txn -->
      <th class="col-nonloy">Sales</th>
      <th>Returns</th>
      <!-- Points Earned -->
      <th class="col-earned">Base</th>
      <th>Bonus</th>
      <th>Adjusted</th>
      <!-- Points Redeemed -->
      <th class="col-redeem">Base</th>
      <th>Bonus</th>
      <th>Adjusted</th>
      <!-- Points Expired -->
      <th class="col-expire">Base</th>
      <th>Bonus</th>
      <th>Adjusted</th>
      <!-- Points Forfeited -->
      <th class="col-forfeit">Base</th>
      <th>Bonus</th>
      <th>Adjusted</th>
      <!-- Certs Issued -->
      <th class="col-cert">Count</th>
      <th>Amount</th>
      <!-- Certs Redeemed -->
      <th class="col-cert">Count</th>
      <th>Amount</th>
    </tr>
  </thead>
  <tbody>
    {daily_rows}
  </tbody>
  <tfoot>
    <tr>
      <td>TOTAL</td>
      <td>{fmt_int(t['Enrollments'])}</td>
      <td>{fmt_int(t['Loyalty Sale Transactions'])}</td>
      <td>{fmt_int(t['Loyalty Return Transactions'])}</td>
      <td>{fmt_int(t['Non-Loyalty Sale Transactions'])}</td>
      <td>{fmt_int(t['Non-Loyalty Return Transactions'])}</td>
      <td>{fmt_pts(t['Base Points Earned'])}</td>
      <td>{fmt_pts(t['Bonus Points Earned'])}</td>
      <td>{fmt_pts(t['Adjusted Points Earned'])}</td>
      <td>{fmt_pts(t['Base Points Redeemed'])}</td>
      <td>{fmt_pts(t['Bonus Points Redeemed'])}</td>
      <td>{fmt_pts(t['Adjusted Points Redeemed'])}</td>
      <td>{fmt_pts(t['Base Points Expired'])}</td>
      <td>{fmt_pts(t['Bonus Points Expired'])}</td>
      <td>{fmt_pts(t['Adjusted Points Expired'])}</td>
      <td>{fmt_pts(t['Base Points Forfeited'])}</td>
      <td>{fmt_pts(t['Bonus Points Forfeited'])}</td>
      <td>{fmt_pts(t['Adjusted Points Forfeited'])}</td>
      <td>{fmt_int(t['Loyalty Certificates Issued'])}</td>
      <td>{fmt_currency(t['Loyalty Certificates Issued Amount'])}</td>
      <td>{fmt_int(t['Loyalty Certificates Redeemed'])}</td>
      <td>{fmt_currency(t['Loyalty Certificates Redeemed Amount'])}</td>
      <td>{fmt_currency(t['Daily $20 Birthday Certificate'])}</td>
      <td>{fmt_int(t['Tier Upgrades'])}</td>
      <td>{fmt_int(t['Tier Downgrades'])}</td>
    </tr>
  </tfoot>
</table>
</div>

</div><!-- /content -->
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
        print("Usage: python generate_report.py <input_file> [output_file.html]")
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    generate_report(input_file, output_file)
