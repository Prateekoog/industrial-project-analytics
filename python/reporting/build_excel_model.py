"""Build excel/project_financial_model.xlsx: a live-formula financial model of the portfolio.

Run: python python/reporting/build_excel_model.py   (after the analysis scripts)

Data sheets hold values; every analysis sheet is built from Excel formulas (XLOOKUP, INDEX/MATCH,
SUMIFS, COUNTIFS, AVERAGEIFS, IF/IFERROR, TEXT, CHOOSE, RANK.EQ, NPV ...) so the model can be
audited and changed in Excel. A Checks sheet compares formula results with the Python pipeline.
Colour code: blue text = input you may change; black = formula; grey fill = header.
"""
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
import config as C  # noqa: E402
from common import load, project_kpis  # noqa: E402

HEAD = PatternFill("solid", fgColor="E7E6E1")
INPUT = Font(color="1C5CAB", bold=True)
BOLD = Font(bold=True)
TITLE = Font(bold=True, size=14)
NOTE = Font(italic=True, color="52514E", size=9)
THIN = Border(bottom=Side(style="thin", color="C3C2B7"))
CR = '#,##0.00'
PCT = '0.0%'


def xlookup(value, lookup, result, not_found='"not found"'):
    """XLOOKUP where the Excel version has it; IFERROR falls back to INDEX/MATCH (Excel 2019 and older)."""
    return f"IFERROR(_xlfn.XLOOKUP({value},{lookup},{result},{not_found}),IFERROR(INDEX({result},MATCH({value},{lookup},0)),{not_found}))"


def header(ws, row, labels, col=1):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=lab)
        c.font, c.fill, c.alignment = BOLD, HEAD, Alignment(wrap_text=True, vertical="center")


def widths(ws, mapping):
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


def data_sheet(wb, name, df, table_name):
    ws = wb.create_sheet(name)
    ws.append(list(df.columns))
    for row in df.itertuples(index=False):
        ws.append([None if pd.isna(v) else v for v in row])
    ref = f"A1:{get_column_letter(df.shape[1])}{len(df) + 1}"
    tab = Table(displayName=table_name, ref=ref)
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(tab)
    ws.freeze_panes = "A2"
    for i in range(1, df.shape[1] + 1):
        ws.column_dimensions[get_column_letter(i)].width = 14
    return ws


def main():
    t = load()
    k = project_kpis(t)
    wb = Workbook()

    # ------------------------------------------------------------------ README
    ws = wb.active
    ws.title = "README"
    lines = [
        ("ProjectCo - Project Financial Model (synthetic case study)", TITLE),
        ("Fictional company and synthetic data. Inspired by an Engineering Internship role at TKIL Industries; no TKIL data.", NOTE),
        ("", None),
        ("Sheet guide", BOLD),
        ("Inputs - thresholds and rates every formula refers to (change them and the model updates)", None),
        ("Project_Summary - pick a project in C3: XLOOKUP / INDEX-MATCH / SUMIFS pull its financials and cost breakdown", None),
        ("Profitability - estimated vs actual profit and margin for all 80 projects, cost-variance status, industry summary", None),
        ("Cost_Analysis - budget vs actual by cost category and by industry (SUMIFS matrices, colour scales)", None),
        ("Supplier_Scorecard - COUNTIFS / AVERAGEIFS / SUMIFS supplier KPIs, composite score and RANK.EQ", None),
        ("ROI_Model - four improvement initiatives: payback, 3-year ROI, 5-year NPV, scenario switch, sensitivity grid", None),
        ("What_If - portfolio margin if overruns and liquidated damages are reduced", None),
        ("Checks - each formula result compared with the Python pipeline (should all be TRUE)", None),
        ("Formula_Guide - what each Excel function does and where it is used", None),
        ("Data_* sheets - values exported from the cleaned dataset (Rs crore unless stated)", None),
        ("", None),
        ("Colour code: blue bold text = input you can change; black = formula; grey = header.", NOTE),
        ("Money is in Rs crore (1 Cr = Rs 1,00,00,000) unless a column says lakh.", NOTE),
        ("Try: Data > What-If Analysis > Goal Seek on ROI_Model to find the break-even downtime reduction.", NOTE),
    ]
    for i, (text, font) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=text)
        if font:
            c.font = font
    ws.column_dimensions["A"].width = 120

    # ------------------------------------------------------------------ Inputs
    inp = wb.create_sheet("Inputs")
    inp["A1"], inp["A1"].font = "Model inputs", TITLE
    inputs = [("Under-budget threshold (CV%)", C.CV_UNDER / 100, PCT), ("Warning threshold (CV%)", C.CV_WARNING / 100, PCT),
              ("Critical threshold (CV%)", C.CV_CRITICAL / 100, PCT), ("LD rate per week", C.LD_RATE_PER_WEEK, '0.00%'),
              ("LD cap", C.LD_CAP, PCT), ("Discount rate (NPV)", C.DISCOUNT_RATE, PCT)]
    header(inp, 3, ["Input", "Value", "Source"])
    for i, (lab, v, fmt) in enumerate(inputs, 4):
        inp.cell(row=i, column=1, value=lab)
        c = inp.cell(row=i, column=2, value=v)
        c.font, c.number_format = INPUT, fmt
        inp.cell(row=i, column=3, value="docs/ASSUMPTIONS.md").font = NOTE
    widths(inp, {"A": 34, "B": 12, "C": 24})
    UNDER, WARN, CRIT, LDR, LDC, DISC = (f"Inputs!$B${r}" for r in range(4, 10))

    # ------------------------------------------------------------------ Data sheets
    cols = ["project_id", "project_name", "industry", "status", "works_location_id", "project_manager_id",
            "has_price_variation_clause", "contract_value_inr", "estimated_cost", "revised_budget", "approved_co_value",
            "actual_cost_to_date", "percent_complete", "revenue_to_date", "pvc_revenue", "ld_deducted", "delay_days",
            "planned_duration_days"]
    dp = k[cols].copy()
    for c in ["contract_value_inr", "estimated_cost", "revised_budget", "approved_co_value", "actual_cost_to_date",
              "revenue_to_date", "pvc_revenue", "ld_deducted"]:
        dp[c] = (dp[c] / C.CRORE).round(4)
    dp = dp.rename(columns={"contract_value_inr": "contract_value_cr", "estimated_cost": "estimated_cost_cr",
                            "revised_budget": "revised_budget_cr", "approved_co_value": "approved_co_value_cr",
                            "actual_cost_to_date": "actual_cost_to_date_cr", "revenue_to_date": "revenue_to_date_cr",
                            "pvc_revenue": "pvc_revenue_cr", "ld_deducted": "ld_deducted_cr"})
    dp["has_price_variation_clause"] = dp.has_price_variation_clause.map({True: "Yes", False: "No"})
    dp["delay_days"] = dp.delay_days.round(0)
    n = len(dp)
    data_sheet(wb, "Data_Projects", dp, "tblProjects")

    b = t["fact_budget"].merge(t["dim_cost_category"][["cost_category_id", "cost_category"]])
    a = t["fact_project_cost"].groupby(["project_id", "cost_category_id"]).amount_inr.sum().rename("actual").reset_index()
    dc = b.merge(a, how="left").fillna({"actual": 0}).merge(k[["project_id", "status", "industry"]])
    dc = dc.assign(revised_budget_cr=(dc.revised_budget_inr / C.CRORE).round(4), actual_cr=(dc.actual / C.CRORE).round(4))
    dc = dc[["project_id", "status", "industry", "cost_category", "revised_budget_cr", "actual_cr"]]
    data_sheet(wb, "Data_Costs", dc, "tblCosts")

    po = t["fact_procurement"].merge(t["dim_supplier"][["supplier_id", "supplier_name", "material_group"]])
    po = po.assign(on_time=po.is_on_time.map({True: 1, False: 0}), delivered=po.delivery_date.notna().astype(int),
                   line_value_lakh=(po.line_value_inr / C.LAKH).round(3),
                   market_value_lakh=(po.quantity * po.benchmark_unit_price_inr / C.LAKH).round(3))
    po = po[["po_line_id", "project_id", "supplier_id", "supplier_name", "material_group", "po_date", "on_time",
             "lead_time_days", "line_value_lakh", "market_value_lakh", "quantity", "qty_rejected", "delivered"]]
    po["po_date"] = po.po_date.dt.date
    data_sheet(wb, "Data_PO", po, "tblPO")
    npo = len(po)

    # ------------------------------------------------------------------ Profitability
    pf = wb.create_sheet("Profitability", 2)
    pf["A1"], pf["A1"].font = "Profitability: estimated vs actual (Rs crore)", TITLE
    pf["A2"] = "Completed projects use actual cost and revenue. In-progress projects use EAC = cost to date / % complete, and forecast revenue = contract + approved change orders + PVC billed."
    pf["A2"].font = NOTE
    cols_pf = ["Project", "Industry", "Status", "Contract value", "Estimated cost", "Estimated profit", "Estimated margin",
               "Final cost (actual / EAC)", "Final revenue", "Final profit", "Final margin", "Margin lost (pp)",
               "Revised budget", "Cost variance", "Cost variance %", "Cost status", "Delay days", "Profit label"]
    header(pf, 4, cols_pf)
    for i in range(n):
        r, d = 5 + i, 2 + i
        f = {
            "A": f"=Data_Projects!A{d}", "B": f"=Data_Projects!C{d}", "C": f"=Data_Projects!D{d}",
            "D": f"=Data_Projects!H{d}", "E": f"=Data_Projects!I{d}", "F": f"=D{r}-E{r}", "G": f"=IFERROR(F{r}/D{r},0)",
            "H": f'=IF(C{r}="Completed",Data_Projects!L{d},IFERROR(Data_Projects!L{d}/(Data_Projects!M{d}/100),Data_Projects!L{d}))',
            "I": f'=IF(C{r}="Completed",Data_Projects!N{d},D{r}+Data_Projects!K{d}+Data_Projects!O{d})',
            "J": f"=I{r}-H{r}", "K": f"=IFERROR(J{r}/I{r},0)", "L": f"=(G{r}-K{r})*100", "M": f"=Data_Projects!J{d}",
            "N": f"=H{r}-M{r}", "O": f"=IFERROR(N{r}/M{r},0)",
            "P": f'=IF(O{r}<{UNDER},"Under budget",IF(O{r}<={WARN},"On budget",IF(O{r}<={CRIT},"Warning","Critical")))',
            "Q": f"=Data_Projects!Q{d}", "R": f'=TEXT(J{r},"#,##0.0")&" Cr ("&TEXT(K{r},"0.0%")&")"',
        }
        for col, formula in f.items():
            pf[f"{col}{r}"] = formula
        for col in "DEFHIJMN":
            pf[f"{col}{r}"].number_format = CR
        for col in "GKO":
            pf[f"{col}{r}"].number_format = PCT
        pf[f"L{r}"].number_format = "0.0"
    last = 4 + n
    pf.conditional_formatting.add(f"O5:O{last}", ColorScaleRule(start_type="num", start_value=-0.05, start_color="2A78D6",
                                                                mid_type="num", mid_value=0, mid_color="F0EFEC",
                                                                end_type="num", end_value=0.15, end_color="D03B3B"))
    pf.conditional_formatting.add(f"K5:K{last}", CellIsRule(operator="lessThan", formula=["0"], font=Font(color="D03B3B", bold=True)))
    pf.conditional_formatting.add(f"J5:J{last}", DataBarRule(start_type="min", end_type="max", color="2A78D6"))
    pf.freeze_panes = "B5"

    # Summary block (completed projects) using SUMIFS / COUNTIFS
    s0 = last + 3
    pf[f"A{s0}"], pf[f"A{s0}"].font = "Portfolio summary - completed projects", BOLD
    rng = lambda col: f"${col}$5:${col}${last}"  # noqa: E731
    summary = [
        ("Completed projects", f'=COUNTIFS({rng("C")},"Completed")', "0"),
        ("Revenue", f'=SUMIFS({rng("I")},{rng("C")},"Completed")', CR),
        ("Estimated profit", f'=SUMIFS({rng("F")},{rng("C")},"Completed")', CR),
        ("Actual profit", f'=SUMIFS({rng("J")},{rng("C")},"Completed")', CR),
        ("Weighted estimated margin", f'=B{s0 + 3}/SUMIFS({rng("D")},{rng("C")},"Completed")', PCT),
        ("Weighted actual margin", f"=B{s0 + 4}/B{s0 + 2}", PCT),
        ("Profit lost vs bid", f"=B{s0 + 3}-B{s0 + 4}", CR),
        ("Cost overrun (vs revised budget)", f'=SUMIFS({rng("N")},{rng("C")},"Completed")', CR),
        ("Loss-making projects", f'=COUNTIFS({rng("C")},"Completed",{rng("J")},"<0")', "0"),
        ("Critical cost overruns", f'=COUNTIFS({rng("C")},"Completed",{rng("P")},"Critical")', "0"),
        ("Liquidated damages deducted", f'=SUMIFS(Data_Projects!$P$2:$P${n + 1},Data_Projects!$D$2:$D${n + 1},"Completed")', CR),
    ]
    for i, (lab, formula, fmt) in enumerate(summary, 1):
        pf[f"A{s0 + i}"] = lab
        pf[f"B{s0 + i}"] = formula
        pf[f"B{s0 + i}"].number_format = fmt
    SUM_ROW = {lab: f"Profitability!B{s0 + i}" for i, (lab, _, _) in enumerate(summary, 1)}

    i0 = s0 + len(summary) + 3
    pf[f"A{i0 - 1}"], pf[f"A{i0 - 1}"].font = "By industry - completed projects", BOLD
    header(pf, i0, ["Industry", "Projects", "Revenue", "Actual profit", "Actual margin", "Avg cost variance %"])
    for j, ind in enumerate(sorted(k.industry.unique()), 1):
        r = i0 + j
        pf[f"A{r}"] = ind
        pf[f"B{r}"] = f'=COUNTIFS({rng("B")},A{r},{rng("C")},"Completed")'
        pf[f"C{r}"] = f'=SUMIFS({rng("I")},{rng("B")},A{r},{rng("C")},"Completed")'
        pf[f"D{r}"] = f'=SUMIFS({rng("J")},{rng("B")},A{r},{rng("C")},"Completed")'
        pf[f"E{r}"] = f"=IFERROR(D{r}/C{r},0)"
        pf[f"F{r}"] = f'=IFERROR(AVERAGEIFS({rng("O")},{rng("B")},A{r},{rng("C")},"Completed"),0)'
        pf[f"C{r}"].number_format = pf[f"D{r}"].number_format = CR
        pf[f"E{r}"].number_format = pf[f"F{r}"].number_format = PCT
    widths(pf, {"A": 30, "B": 26, "C": 12, "P": 13, "R": 22, **{c: 13 for c in "DEFGHIJKLMNOQ"}})

    # ------------------------------------------------------------------ Project_Summary
    ps = wb.create_sheet("Project_Summary", 2)
    ps["A1"], ps["A1"].font = "Project summary - choose a project", TITLE
    ps["B3"] = "Project ID"
    ps["C3"] = k.sort_values("cost_variance_pct", ascending=False).iloc[0].project_id
    ps["C3"].font = INPUT
    dv = DataValidation(type="list", formula1=f"=Data_Projects!$A$2:$A${n + 1}", allow_blank=False)
    ps.add_data_validation(dv)
    dv.add("C3")
    pid = "$C$3"
    col = lambda letter: f"Data_Projects!${letter}$2:${letter}${n + 1}"  # noqa: E731
    fields = [
        ("Project name (XLOOKUP)", "=" + xlookup(pid, col("A"), col("B")), None),
        ("Industry (INDEX/MATCH)", f"=INDEX({col('C')},MATCH({pid},{col('A')},0))", None),
        ("Status", "=" + xlookup(pid, col("A"), col("D")), None),
        ("Contract value (Rs Cr)", "=" + xlookup(pid, col("A"), col("H")), CR),
        ("Revised budget (Rs Cr)", "=" + xlookup(pid, col("A"), col("J")), CR),
        ("Final cost - actual or EAC (Rs Cr)", f"=INDEX(Profitability!$H$5:$H${last},MATCH({pid},Profitability!$A$5:$A${last},0))", CR),
        ("Final profit (Rs Cr)", f"=INDEX(Profitability!$J$5:$J${last},MATCH({pid},Profitability!$A$5:$A${last},0))", CR),
        ("Final margin", f"=INDEX(Profitability!$K$5:$K${last},MATCH({pid},Profitability!$A$5:$A${last},0))", PCT),
        ("Estimated margin", f"=INDEX(Profitability!$G$5:$G${last},MATCH({pid},Profitability!$A$5:$A${last},0))", PCT),
        ("Cost variance %", f"=INDEX(Profitability!$O$5:$O${last},MATCH({pid},Profitability!$A$5:$A${last},0))", PCT),
        ("Cost status", f"=INDEX(Profitability!$P$5:$P${last},MATCH({pid},Profitability!$A$5:$A${last},0))", None),
        ("Delay (days)", "=" + xlookup(pid, col("A"), col("Q")), "0"),
        ("Liquidated damages (Rs Cr)", "=" + xlookup(pid, col("A"), col("P")), CR),
        ("Headline", f'=C4&" | "&C6&" | margin "&TEXT(C11,"0.0%")&" vs bid "&TEXT(C12,"0.0%")', None),
    ]
    for i, (lab, formula, fmt) in enumerate(fields, 4):
        ps[f"B{i}"] = lab
        ps[f"C{i}"] = formula
        if fmt:
            ps[f"C{i}"].number_format = fmt
    r0 = 4 + len(fields) + 2
    ps[f"B{r0 - 1}"], ps[f"B{r0 - 1}"].font = "Cost breakdown (SUMIFS on Data_Costs)", BOLD
    header(ps, r0, ["Cost category", "Revised budget", "Actual to date", "Variance", "Variance %", "Share of variance"], col=2)
    cats = list(t["dim_cost_category"].sort_values("sort_order").cost_category)
    ncost = len(dc)
    cc = lambda letter: f"Data_Costs!${letter}$2:${letter}${ncost + 1}"  # noqa: E731
    for j, cat in enumerate(cats, 1):
        r = r0 + j
        ps[f"B{r}"] = cat
        ps[f"C{r}"] = f"=SUMIFS({cc('E')},{cc('A')},{pid},{cc('D')},B{r})"
        ps[f"D{r}"] = f"=SUMIFS({cc('F')},{cc('A')},{pid},{cc('D')},B{r})"
        ps[f"E{r}"] = f"=D{r}-C{r}"
        ps[f"F{r}"] = f"=IFERROR(E{r}/C{r},0)"
        ps[f"G{r}"] = f"=IFERROR(E{r}/SUM($E${r0 + 1}:$E${r0 + len(cats)}),0)"
        for c_ in "CDE":
            ps[f"{c_}{r}"].number_format = CR
        ps[f"F{r}"].number_format = ps[f"G{r}"].number_format = PCT
    rt = r0 + len(cats) + 1
    ps[f"B{rt}"], ps[f"B{rt}"].font = "Total", BOLD
    for c_ in "CDE":
        ps[f"{c_}{rt}"] = f"=SUM({c_}{r0 + 1}:{c_}{rt - 1})"
        ps[f"{c_}{rt}"].number_format = CR
    ps.conditional_formatting.add(f"F{r0 + 1}:F{rt - 1}", ColorScaleRule(start_type="num", start_value=-0.05, start_color="2A78D6",
                                                                        mid_type="num", mid_value=0, mid_color="F0EFEC",
                                                                        end_type="num", end_value=0.2, end_color="D03B3B"))
    widths(ps, {"B": 36, "C": 44, "D": 15, "E": 14, "F": 12, "G": 16})

    # ------------------------------------------------------------------ Cost_Analysis
    ca = wb.create_sheet("Cost_Analysis", 4)
    ca["A1"], ca["A1"].font = "Cost analysis - completed projects (Rs crore)", TITLE
    header(ca, 3, ["Cost category", "Revised budget", "Actual", "Variance", "Variance %", "Share of total overrun"])
    for j, cat in enumerate(cats, 1):
        r = 3 + j
        ca[f"A{r}"] = cat
        ca[f"B{r}"] = f'=SUMIFS({cc("E")},{cc("D")},A{r},{cc("B")},"Completed")'
        ca[f"C{r}"] = f'=SUMIFS({cc("F")},{cc("D")},A{r},{cc("B")},"Completed")'
        ca[f"D{r}"] = f"=C{r}-B{r}"
        ca[f"E{r}"] = f"=IFERROR(D{r}/B{r},0)"
        ca[f"F{r}"] = f"=IFERROR(D{r}/SUM($D$4:$D${3 + len(cats)}),0)"
        for c_ in "BCD":
            ca[f"{c_}{r}"].number_format = CR
        ca[f"E{r}"].number_format = ca[f"F{r}"].number_format = PCT
    tot = 4 + len(cats)
    ca[f"A{tot}"], ca[f"A{tot}"].font = "Total", BOLD
    for c_ in "BCD":
        ca[f"{c_}{tot}"] = f"=SUM({c_}4:{c_}{tot - 1})"
        ca[f"{c_}{tot}"].number_format = CR
    ca[f"E{tot}"] = f"=D{tot}/B{tot}"
    ca[f"E{tot}"].number_format = PCT
    ca.conditional_formatting.add(f"D4:D{tot - 1}", DataBarRule(start_type="min", end_type="max", color="EB6834"))

    m0 = tot + 3
    ca[f"A{m0 - 1}"], ca[f"A{m0 - 1}"].font = "Cost variance % by industry and category (completed)", BOLD
    header(ca, m0, ["Industry"] + cats)
    for j, ind in enumerate(sorted(k.industry.unique()), 1):
        r = m0 + j
        ca[f"A{r}"] = ind
        for q, cat in enumerate(cats):
            colL = get_column_letter(2 + q)
            ca[f"{colL}{r}"] = (f'=IFERROR(SUMIFS({cc("F")},{cc("C")},$A{r},{cc("D")},{colL}${m0},{cc("B")},"Completed")'
                                f'/SUMIFS({cc("E")},{cc("C")},$A{r},{cc("D")},{colL}${m0},{cc("B")},"Completed")-1,"")')
            ca[f"{colL}{r}"].number_format = PCT
    ca.conditional_formatting.add(f"B{m0 + 1}:I{m0 + 10}", ColorScaleRule(start_type="num", start_value=-0.1, start_color="2A78D6",
                                                                         mid_type="num", mid_value=0, mid_color="F0EFEC",
                                                                         end_type="num", end_value=0.25, end_color="D03B3B"))
    widths(ca, {"A": 30, **{get_column_letter(i): 15 for i in range(2, 10)}})

    # ------------------------------------------------------------------ Supplier_Scorecard
    sc = wb.create_sheet("Supplier_Scorecard", 5)
    sc["A1"], sc["A1"].font = "Supplier scorecard (COUNTIFS / SUMIFS / AVERAGEIFS on Data_PO)", TITLE
    sc["A2"] = "Composite = 40% delivery + 30% price + 30% quality, each as a percentile rank (PERCENTRANK.INC). Price index 1.00 = market price."
    sc["A2"].font = NOTE
    header(sc, 4, ["Supplier", "Name (XLOOKUP)", "Material group (INDEX/MATCH)", "PO lines", "Delivered", "On time",
                   "OTD %", "Avg lead time (days)", "Spend (Rs lakh)", "Price index", "Rejection %", "Composite score", "Rank"])
    pcol = lambda letter: f"Data_PO!${letter}$2:${letter}${npo + 1}"  # noqa: E731
    sups = sorted(po.supplier_id.unique())
    ns = len(sups)
    for j, sid in enumerate(sups):
        r = 5 + j
        sc[f"A{r}"] = sid
        sc[f"B{r}"] = "=" + xlookup(f"A{r}", pcol("C"), pcol("D"))
        sc[f"C{r}"] = f"=INDEX({pcol('E')},MATCH(A{r},{pcol('C')},0))"
        sc[f"D{r}"] = f"=COUNTIFS({pcol('C')},A{r})"
        sc[f"E{r}"] = f"=COUNTIFS({pcol('C')},A{r},{pcol('M')},1)"
        sc[f"F{r}"] = f"=COUNTIFS({pcol('C')},A{r},{pcol('G')},1)"
        sc[f"G{r}"] = f"=IFERROR(F{r}/E{r},0)"
        sc[f"H{r}"] = f'=IFERROR(AVERAGEIFS({pcol("H")},{pcol("C")},A{r},{pcol("H")},"<>"),"")'
        sc[f"I{r}"] = f"=SUMIFS({pcol('I')},{pcol('C')},A{r})"
        sc[f"J{r}"] = f"=IFERROR(I{r}/SUMIFS({pcol('J')},{pcol('C')},A{r}),0)"
        sc[f"K{r}"] = f"=IFERROR(SUMIFS({pcol('L')},{pcol('C')},A{r})/SUMIFS({pcol('K')},{pcol('C')},A{r}),0)"
        end = 4 + ns
        sc[f"L{r}"] = (f"=100*(0.4*_xlfn.PERCENTRANK.INC($G$5:$G${end},G{r})+0.3*(1-_xlfn.PERCENTRANK.INC($J$5:$J${end},J{r}))"
                       f"+0.3*(1-_xlfn.PERCENTRANK.INC($K$5:$K${end},K{r})))")
        sc[f"M{r}"] = f"=_xlfn.RANK.EQ(L{r},$L$5:$L${end})"
        sc[f"G{r}"].number_format = sc[f"K{r}"].number_format = PCT
        sc[f"H{r}"].number_format = sc[f"L{r}"].number_format = "0.0"
        sc[f"I{r}"].number_format = "#,##0"
        sc[f"J{r}"].number_format = "0.000"
    end = 4 + ns
    sc.conditional_formatting.add(f"G5:G{end}", ColorScaleRule(start_type="num", start_value=0.5, start_color="D03B3B",
                                                               mid_type="num", mid_value=0.75, mid_color="FAB219",
                                                               end_type="num", end_value=0.95, end_color="0CA30C"))
    sc.conditional_formatting.add(f"G5:G{end}", CellIsRule(operator="lessThan", formula=["0.6"], font=Font(bold=True)))
    sc.freeze_panes = "B5"
    widths(sc, {"A": 10, "B": 40, "C": 28, **{c: 12 for c in "DEFGHIJKLM"}})

    # ------------------------------------------------------------------ ROI_Model
    roi = pd.read_csv(C.TABLES / "roi_scenarios.csv")
    rm = wb.create_sheet("ROI_Model", 6)
    rm["A1"], rm["A1"].font = "Improvement initiatives: payback, ROI and NPV (Rs crore)", TITLE
    rm["A3"], rm["B3"] = "Scenario (choose)", "Base"
    rm["B3"].font = INPUT
    dv2 = DataValidation(type="list", formula1='"Low,Base,High"', allow_blank=False)
    rm.add_data_validation(dv2)
    dv2.add("B3")
    rm["C3"] = "Low/Base/High = effectiveness assumptions tested in python/analysis/roi_business_case.py"
    rm["C3"].font = NOTE
    header(rm, 5, ["Initiative", "Upfront investment", "Running cost / yr", "Saving / yr (Low)", "Saving / yr (Base)",
                   "Saving / yr (High)", "Selected saving / yr", "Net annual benefit", "Payback (years)",
                   "3-year ROI", "5-year NPV", "NPV rank"])
    inits = list(roi.initiative.unique())
    for j, name in enumerate(inits):
        r = 6 + j
        sub = roi[roi.initiative == name].set_index("scenario")
        rm[f"A{r}"] = name
        for c_, v in (("B", sub.at["base", "investment"]), ("C", sub.at["base", "running_cost"]),
                      ("D", sub.at["low", "annual_saving"]), ("E", sub.at["base", "annual_saving"]),
                      ("F", sub.at["high", "annual_saving"])):
            rm[f"{c_}{r}"] = round(v / C.CRORE, 4)
            rm[f"{c_}{r}"].font, rm[f"{c_}{r}"].number_format = INPUT, CR
        rm[f"G{r}"] = f'=CHOOSE(MATCH($B$3,{{"Low","Base","High"}},0),D{r},E{r},F{r})'
        rm[f"H{r}"] = f"=G{r}-C{r}"
        rm[f"I{r}"] = f'=IF(H{r}>0,B{r}/H{r},"Never")'
        rm[f"J{r}"] = f"=(3*G{r}-(B{r}+3*C{r}))/(B{r}+3*C{r})"
        rm[f"K{r}"] = f"=NPV({DISC},H{r},H{r},H{r},H{r},H{r})-B{r}"
        rm[f"L{r}"] = f"=_xlfn.RANK.EQ(K{r},$K$6:$K${5 + len(inits)})"
        for c_ in "GHK":
            rm[f"{c_}{r}"].number_format = CR
        rm[f"I{r}"].number_format = "0.00"
        rm[f"J{r}"].number_format = "0%"
    rm.conditional_formatting.add(f"K6:K{5 + len(inits)}", CellIsRule(operator="lessThan", formula=["0"], font=Font(color="D03B3B", bold=True)))
    s1 = 8 + len(inits)
    rm[f"A{s1}"], rm[f"A{s1}"].font = "Sensitivity: predictive maintenance NPV vs downtime reduction achieved", BOLD
    header(rm, s1 + 1, ["Downtime reduction", "Annual saving", "Net benefit", "5-year NPV", "Payback (years)"])
    pm_row = 6 + inits.index("Predictive maintenance on chronic machines")
    for q, red in enumerate([0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50, 0.60]):
        r = s1 + 2 + q
        rm[f"A{r}"] = red
        rm[f"A{r}"].font, rm[f"A{r}"].number_format = INPUT, "0%"
        rm[f"B{r}"] = f"=$E${pm_row}/0.35*A{r}"
        rm[f"C{r}"] = f"=B{r}-$C${pm_row}"
        rm[f"D{r}"] = f"=NPV({DISC},C{r},C{r},C{r},C{r},C{r})-$B${pm_row}"
        rm[f"E{r}"] = f'=IF(C{r}>0,$B${pm_row}/C{r},"Never")'
        for c_ in "BCD":
            rm[f"{c_}{r}"].number_format = CR
        rm[f"E{r}"].number_format = "0.00"
    rm.conditional_formatting.add(f"D{s1 + 2}:D{s1 + 9}", CellIsRule(operator="lessThan", formula=["0"], font=Font(color="D03B3B", bold=True)))
    rm[f"A{s1 + 11}"] = "Goal Seek: set the base-case NPV cell (column K) to 0 by changing the Base saving (column E) to find the break-even saving."
    rm[f"A{s1 + 11}"].font = NOTE
    widths(rm, {"A": 42, **{c: 14 for c in "BCDEFGHIJKL"}})

    # ------------------------------------------------------------------ What_If
    wi = wb.create_sheet("What_If", 7)
    wi["A1"], wi["A1"].font = "What-if: portfolio margin if execution improves (completed projects)", TITLE
    rows = [("Revenue (Rs Cr)", f"={SUM_ROW['Revenue']}", CR, False),
            ("Actual profit (Rs Cr)", f"={SUM_ROW['Actual profit']}", CR, False),
            ("Cost overrun (Rs Cr)", f"={SUM_ROW['Cost overrun (vs revised budget)']}", CR, False),
            ("Liquidated damages (Rs Cr)", f"={SUM_ROW['Liquidated damages deducted']}", CR, False),
            ("Reduce cost overrun by", 0.25, PCT, True), ("Reduce liquidated damages by", 0.5, PCT, True),
            ("Profit after improvement (Rs Cr)", "=B5+B6*B8+B7*B9", CR, False),
            ("Revenue after improvement (Rs Cr)", "=B4+B7*B9", CR, False),
            ("Margin before", "=B5/B4", PCT, False), ("Margin after", "=B10/B11", PCT, False),
            ("Margin gained (pp)", "=(B13-B12)*100", "0.00", False)]
    for i, (lab, v, fmt, is_input) in enumerate(rows, 4):
        wi[f"A{i}"] = lab
        wi[f"B{i}"] = v
        wi[f"B{i}"].number_format = fmt
        if is_input:
            wi[f"B{i}"].font = INPUT
    wi["A16"] = "Change the blue cells. LD reduction also raises revenue, because LD is deducted from revenue (C05)."
    wi["A16"].font = NOTE
    widths(wi, {"A": 40, "B": 16})

    # ------------------------------------------------------------------ Checks
    ck = wb.create_sheet("Checks", 8)
    ck["A1"], ck["A1"].font = "Checks: Excel formulas vs Python pipeline (every row should be TRUE)", TITLE
    done = k[k.status == "Completed"]
    expect = [("Completed projects", SUM_ROW["Completed projects"], len(done), 0),
              ("Revenue (Rs Cr)", SUM_ROW["Revenue"], done.final_revenue.sum() / C.CRORE, 0.05),
              ("Estimated profit (Rs Cr)", SUM_ROW["Estimated profit"], done.estimated_profit.sum() / C.CRORE, 0.05),
              ("Actual profit (Rs Cr)", SUM_ROW["Actual profit"], done.final_profit.sum() / C.CRORE, 0.05),
              ("Cost overrun (Rs Cr)", SUM_ROW["Cost overrun (vs revised budget)"], done.cost_variance.sum() / C.CRORE, 0.05),
              ("Loss-making projects", SUM_ROW["Loss-making projects"], int((done.final_profit < 0).sum()), 0),
              ("Critical overruns", SUM_ROW["Critical cost overruns"], int((done.cost_status == "Critical").sum()), 0),
              ("Total cost overrun, Cost_Analysis", f"Cost_Analysis!D{tot}", done.cost_variance.sum() / C.CRORE, 0.05)]
    header(ck, 3, ["Check", "Excel value", "Python value", "Tolerance", "Match?"])
    for i, (lab, ref, val, tol) in enumerate(expect, 4):
        ck[f"A{i}"], ck[f"B{i}"], ck[f"C{i}"], ck[f"D{i}"] = lab, f"={ref}", round(float(val), 4), tol
        ck[f"E{i}"] = f"=ABS(B{i}-C{i})<=D{i}"
        ck[f"B{i}"].number_format = ck[f"C{i}"].number_format = "#,##0.00"
    widths(ck, {"A": 36, "B": 14, "C": 14, "D": 11, "E": 10})

    # ------------------------------------------------------------------ Formula_Guide
    fg = wb.create_sheet("Formula_Guide", 9)
    fg["A1"], fg["A1"].font = "Formula guide", TITLE
    guide = [
        ("XLOOKUP", "Project_Summary!C4", "Finds a value in one column and returns the matching value from another. Safer than VLOOKUP: looks left or right and has a built-in 'not found' result. Excel 2019 and older do not have XLOOKUP, so each one is wrapped in IFERROR(..., INDEX/MATCH) and still works there."),
        ("INDEX / MATCH", "Project_Summary!C5", "MATCH finds the row number; INDEX returns the value at that row. Works in every Excel version."),
        ("SUMIFS", "Cost_Analysis!B4", "Adds values that meet several conditions (category = Material AND status = Completed)."),
        ("COUNTIFS", "Supplier_Scorecard!F5", "Counts rows meeting several conditions (supplier = X AND on_time = 1)."),
        ("AVERAGEIFS", "Supplier_Scorecard!H5", "Average of rows meeting conditions; '<>' skips blanks."),
        ("IF (nested)", "Profitability!P5", "Classifies cost variance into Under budget / On budget / Warning / Critical using the Inputs thresholds."),
        ("IFERROR", "Profitability!G5", "Returns a fallback instead of #DIV/0! when a denominator is zero."),
        ("TEXT", "Profitability!R5", "Formats a number inside a text label, e.g. TEXT(0.083,\"0.0%\") -> 8.3%."),
        ("CHOOSE + MATCH", "ROI_Model!G6", "Picks the Low / Base / High saving according to the scenario selected in B3."),
        ("NPV", "ROI_Model!K6", "Present value of five yearly net benefits at the discount rate, minus the upfront investment."),
        ("RANK.EQ", "Supplier_Scorecard!M5", "Ranks a value within a list (1 = highest)."),
        ("PERCENTRANK.INC", "Supplier_Scorecard!L5", "Position of a value within a list as 0-100%, used to combine KPIs with different units."),
        ("Data validation", "Project_Summary!C3, ROI_Model!B3", "Drop-down lists that restrict inputs to valid choices."),
        ("Conditional formatting", "Profitability!O:O", "Colour scales, data bars and rules highlight overruns and losses."),
        ("What-if / Goal Seek", "What_If, ROI_Model", "Change blue inputs to see the effect; Goal Seek finds the input that hits a target."),
        ("Pivot tables", "Data_* sheets", "Each data sheet is an Excel Table: Insert > PivotTable to slice it by any column."),
    ]
    header(fg, 3, ["Function", "Where used", "What it does"])
    for i, row in enumerate(guide, 4):
        for j, v in enumerate(row, 1):
            fg.cell(row=i, column=j, value=v).alignment = Alignment(wrap_text=True, vertical="top")
    widths(fg, {"A": 20, "B": 34, "C": 100})

    wb.calculation.fullCalcOnLoad = True          # Excel computes every formula when the file opens
    C.EXCEL_DIR.mkdir(exist_ok=True)
    out = C.EXCEL_DIR / "project_financial_model.xlsx"
    wb.save(out)
    print(f"Wrote {out.relative_to(C.ROOT)} with sheets: {wb.sheetnames}")


if __name__ == "__main__":
    main()
