"""Generate docs/DATA_DICTIONARY.md from the processed data plus the descriptions below.

Run: python python/reporting/build_data_dictionary.py

Data type, nullability, null count and an example value are read from the actual files, so the
dictionary cannot drift from the data. Meanings are written once, here.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402

# table: (grain, source system it imitates, how the synthetic values are produced, {column: (meaning, how it is used)})
D = {
"dim_project": ("One row per project", "ERP project master", "80 projects; size log-normal (median ~Rs 70 Cr), duration grows with size and technology risk (B03-B06)", {
    "project_id": ("Project key", "Joins every fact table"), "project_name": ("Client short name + scope", "Labels"),
    "client_id": ("Client key", "Client profitability"), "industry": ("One of 10 synthetic industries", "Slice margin, CV, delay"),
    "site_location_id": ("Project site", "Regional analysis"), "works_location_id": ("Fabrication works assigned by load-balancing", "Links projects to works productivity"),
    "project_manager_id": ("Project manager (dim_employee)", "PM comparison (confounded by project type)"),
    "contract_type": ("Fixed Price (Lump Sum) for all (C04)", "Explains why overruns hit margin"),
    "has_price_variation_clause": ("Contract passes 75% of steel price movement to client (C04)", "PVC vs no-PVC margin"),
    "contract_value_inr": ("Signed contract value, Rs, excl. GST", "Revenue base, estimated margin, LD"),
    "award_date": ("Contract award date", "Order intake by FY; bid steel index"), "planned_start_date": ("Baseline start", "Schedule"),
    "planned_end_date": ("Contractual completion date (D05)", "Delay and LD"), "actual_start_date": ("Actual kick-off", "Schedule"),
    "actual_end_date": ("Commissioning completion; null while in progress", "Delay; status"),
    "status": ("Completed or In Progress at 31-Mar-2026", "Splits actual vs forecast KPIs"),
    "percent_complete": ("Physical progress reported at cut-off (100 if completed)", "Earned value, EAC"),
    "planned_fab_tonnes": ("Tonnes to fabricate in works", "Works planning"), "planned_duration_days": ("Planned end - planned start", "Delay %")}),
"dim_client": ("One row per client", "ERP customer master", "37 fictional clients, 2+ per industry", {
    "client_id": ("Client key", "Join"), "client_name": ("Fictional client name", "Labels"), "industry": ("Client industry", "Slicing"),
    "hq_state": ("Head-office state", "Geography"), "client_since_year": ("First year as a client", "Relationship age")}),
"dim_location": ("One row per works or project site", "Location master", "3 works + 30 site cities (B07)", {
    "location_id": ("Location key (LOC-W* works, LOC-S* sites)", "Join"), "location_name": ("Display name", "Labels"),
    "location_type": ("Works or Project Site", "Filter"), "city": ("City", "Map"), "state": ("Indian state", "Map / region"),
    "region": ("West / East / South", "Works allocation")}),
"dim_employee": ("One row per staff member", "HR master", "84 staff in 6 roles; contract workers are not individual records", {
    "employee_id": ("Employee key", "Join"), "employee_name": ("Generated Indian name (fictional person)", "Labels"),
    "role": ("Project Manager, Planning/Design Engineer, Site/Works Supervisor, Procurement Buyer", "Filter"),
    "department": ("Department", "Filter"), "base_location_id": ("Home works", "Filter"), "join_year": ("Year joined", "Seniority"),
    "hourly_cost_inr": ("Fully loaded hourly cost, Rs", "Reference")}),
"dim_supplier": ("One row per supplier", "Vendor master", "40 suppliers with hidden behaviour archetypes (G02) not stored here", {
    "supplier_id": ("Supplier key", "Join"), "supplier_name": ("Canonical vendor name", "Name matching target in cleaning"),
    "material_group": ("Main material group supplied", "Peer comparison"), "supplier_state": ("State", "Geography"),
    "established_year": ("Year founded", "Reference")}),
"dim_material": ("One row per material", "Material master", "94 materials in 12 groups (G01)", {
    "material_id": ("Material key", "Join"), "material_name": ("Description", "Labels"), "material_group": ("Group", "Spend / volatility"),
    "unit_of_measure": ("MT, m, m2, Nos, Set", "Quantity meaning"), "criticality_class": ("A = long-lead critical, B, C", "Critical-item lateness"),
    "is_steel_linked": ("Price follows the steel index", "Benchmark price, PVC"), "standard_lead_time_days": ("Typical lead time", "Planning"),
    "standard_price_inr": ("Standard price at index 100", "Benchmark and price ratio")}),
"dim_work_centre": ("One row per work centre in a works", "MES master", "6 process types x 3 works", {
    "work_centre_id": ("Work centre key", "Join (bottleneck)"), "work_centre_name": ("Display name", "Labels"),
    "works_location_id": ("Parent works", "Roll-up"), "process_type": ("Cutting ... Blasting & Painting", "Bottleneck analysis"),
    "std_mh_per_tonne": ("Standard man-hours per tonne at this step", "Efficiency"), "std_machine_hours_per_tonne": ("Machine hours per tonne", "Capacity"),
    "is_final_operation": ("Last step before dispatch", "Reference")}),
"dim_equipment": ("One row per machine", "Asset register", "42 machines; reliability class hidden (F06)", {
    "equipment_id": ("Machine key", "Join"), "equipment_name": ("Display name", "Labels"), "equipment_type": ("Machine type", "Filter"),
    "work_centre_id": ("Parent work centre", "Roll-up"), "works_location_id": ("Parent works", "Roll-up"),
    "commission_year": ("Year installed", "Age vs downtime"), "rated_kw": ("Rated power", "Energy"),
    "machine_hour_rate_inr": ("Cost per operating hour (depreciation + maintenance)", "Machine cost"),
    "rated_tonnes_per_hour": ("Throughput per operating hour", "Capacity, lost output")}),
"dim_cost_category": ("One row per cost category", "Chart of accounts", "8 categories (E01)", {
    "cost_category_id": ("Category key", "Join"), "cost_category": ("Material ... Other", "Cost-driver analysis"),
    "sort_order": ("Display order", "Visual sorting"), "cost_behaviour": ("Variable / Time-based / Mixed", "Explains delay sensitivity"),
    "gl_account": ("General-ledger account", "Infers missing categories in cleaning")}),
"dim_stage": ("One row per lifecycle stage", "Project methodology", "7 stages (D01)", {
    "stage_id": ("Stage key", "Join"), "stage_name": ("Concept ... Commissioning", "Delay by stage"), "stage_order": ("Sequence", "Sorting, LAG/LEAD"),
    "billing_share": ("Milestone billing share of contract value", "Revenue timing"), "description": ("What happens in the stage", "Documentation")}),
"dim_date": ("One row per calendar day, Oct 2020 - Dec 2027", "Built in cleaning", "Indian fiscal year Apr-Mar (C02); 6-day week (F02)", {
    "date": ("Calendar date (primary key)", "Relationships"), "date_key": ("YYYYMMDD integer", "Alternate key"), "year": ("Calendar year", "Time slicing"),
    "quarter": ("Calendar quarter", "Time slicing"), "month_num": ("1-12", "Sorting"), "month_name": ("January ...", "Labels"),
    "month_short": ("Jan ...", "Labels"), "year_month": ("YYYY-MM", "Monthly axis"), "month_start": ("First day of month", "Monthly grouping"),
    "fiscal_year_num": ("FY end year (2025 = FY25)", "Sorting"), "fiscal_year": ("FY25 etc.", "FY slicing"),
    "fiscal_month_num": ("April = 1", "FY sorting"), "fiscal_quarter": ("Q1 = Apr-Jun", "FY slicing"), "day_of_week": ("Mon ...", "Labels"),
    "is_working_day": ("Not Sunday and not a holiday", "Capacity")}),
"fact_budget": ("One row per project x cost category", "Estimation / budgeting system", "Bid cost = contract x (1 - bid margin), split by industry cost mix; change orders add budget (C06, C07)", {
    "project_id": ("Project", "Join"), "cost_category_id": ("Category", "Join"), "original_budget_inr": ("Bid estimate", "Estimated cost / profit"),
    "change_order_budget_inr": ("Budget added by approved change orders", "Revised budget"),
    "revised_budget_inr": ("Original + change orders", "Cost variance baseline")}),
"fact_project_cost": ("One ledger posting: project x category x month x source", "Finance general ledger", "Sub-ledgers (procurement, production, timesheets) post monthly; finance categories respond to delay (E02)", {
    "document_no": ("Journal document number (primary key)", "De-duplication"), "project_id": ("Project", "Join"),
    "cost_category_id": ("Category", "Join"), "gl_account": ("GL account", "Category inference"), "posting_date": ("Month-end posting date", "Trend"),
    "source_system": ("Procurement / Production / Timesheet / Finance", "Reconciliation"), "amount_inr": ("Posted cost, Rs", "Actual cost")}),
"fact_procurement": ("One row per purchase-order line", "ERP purchasing", "Supplier choice depends on bid tightness; price follows steel index; lateness by hidden archetype (G01-G05)", {
    "po_line_id": ("PO line key", "Join"), "po_number": ("PO header number", "Grouping"), "project_id": ("Project", "Join"),
    "supplier_id": ("Supplier (matched from free-text name in cleaning)", "Scorecard"), "material_id": ("Material", "Join"),
    "buyer_id": ("Procurement buyer", "Workload"), "pr_date": ("Purchase requisition raised", "Cycle time"),
    "pr_approval_date": ("Requisition approved", "Approval cycle time (bottleneck)"), "rfq_date": ("RFQ issued", "Cycle time"),
    "po_date": ("PO issued", "Spend timing, steel index"), "supplier_confirm_date": ("Supplier acknowledged PO", "Cycle time"),
    "promised_date": ("Committed delivery date", "On-time test"), "delivery_date": ("Goods arrived", "On-time test"),
    "inspection_date": ("Quality inspection", "Cycle time"), "grn_date": ("Goods receipt posted (usable)", "Lead time, material cost posting"),
    "need_by_date": ("When the project needs it (from schedule)", "Critical-item lateness"), "quantity": ("Quantity ordered", "Spend"),
    "unit_price_inr": ("Price per unit, Rs", "Price index"), "line_value_inr": ("Quantity x unit price", "Spend"),
    "benchmark_unit_price_inr": ("Market price at PO date = standard x steel index (steel-linked)", "Price index vs market"),
    "qty_rejected": ("Quantity rejected at inspection", "Quality"), "line_status": ("Received or Open at cut-off", "Filtering"),
    "lead_time_days": ("PO date to goods receipt", "Lead time KPI"), "delivery_delay_days": ("Delivery - promised (>0 = late)", "Lateness"),
    "is_on_time": ("Delivered on or before promised date", "OTD %"), "delivery_date_imputed": ("Delivery date was missing and imputed", "Transparency")}),
"fact_operations": ("One row per works x production day x project", "Manufacturing execution system (MES)", "Day-by-day simulation of shared machine capacity; downtime limits output (F01-F06)", {
    "production_id": ("Record key", "Join"), "works_location_id": ("Works", "Join"), "production_date": ("Working day", "Trend"),
    "project_id": ("Project fabricated", "Join"), "overtime_shift": ("Extended 18-hour day to catch up", "Overtime analysis"),
    "planned_output_t": ("Planned tonnes for the day", "Output achievement"), "actual_output_t": ("Tonnes fabricated", "Productivity"),
    "rework_t": ("Tonnes needing rework at inspection", "Defect rate"), "regular_labour_hours": ("Direct labour hours, normal time", "MH/t"),
    "overtime_labour_hours": ("Overtime hours (paid 2x)", "Overtime %"), "labour_cost_inr": ("Labour cost", "Cost per tonne; reconciles to ledger"),
    "machine_hours": ("Machine operating hours used", "Machine cost"), "machine_cost_inr": ("Machine-hour cost", "Reconciles to ledger"),
    "energy_kwh": ("Electricity used", "Energy"), "energy_cost_inr": ("Energy cost", "Reconciles to ledger"),
    "bottleneck_work_centre_id": ("Work centre with least capacity vs demand that day", "Bottleneck analysis"),
    "capacity_constrained": ("Demand exceeded bottleneck capacity", "Constraint frequency"), "labour_hours_imputed": ("Hours were missing and imputed", "Transparency")}),
"fact_equipment": ("One row per machine x working day", "Machine log / maintenance system", "Breakdown probability by hidden reliability class; planned maintenance every 24 working days", {
    "machine_log_id": ("Record key", "De-duplication"), "log_date": ("Working day", "Trend"), "equipment_id": ("Machine", "Join"),
    "scheduled_hours": ("16 (or 18 on catch-up days)", "Capacity"), "planned_maintenance_hours": ("Planned stoppage", "Availability"),
    "available_hours": ("Scheduled - planned maintenance", "Utilisation denominator"), "downtime_hours": ("Unplanned stoppage", "Downtime %"),
    "operating_hours": ("Hours actually producing", "Utilisation numerator"), "idle_hours": ("Available, not down, no work loaded", "Loading analysis"),
    "downtime_reason": ("Reason code when down", "Downtime Pareto")}),
"fact_labor": ("One row per project x labour type x week", "Site and engineering timesheets", "Hours = earned hours / efficiency + idle waiting time; overtime when behind (E03, E04)", {
    "labour_entry_id": ("Record key", "Join"), "week_ending_date": ("Saturday week end", "Trend"), "project_id": ("Project", "Join"),
    "labour_type": ("Engineering or Site Erection", "Filter"), "supervisor_id": ("Supervising employee", "Accountability"),
    "headcount": ("Crew size", "Resourcing"), "earned_hours": ("Budgeted hours for work done", "Labour efficiency numerator"),
    "regular_hours": ("Normal hours", "Efficiency denominator"), "overtime_hours": ("Overtime hours", "Cost"),
    "idle_hours": ("Paid waiting time (materials, client, weather)", "Lost productivity"), "labour_cost_inr": ("Cost", "Reconciles to ledger")}),
"fact_milestones": ("One row per project x stage", "Project schedule (planning tool)", "Stages overlap; slips propagate; cause = largest own contribution (D02-D04)", {
    "project_id": ("Project", "Join"), "stage_id": ("Stage", "Join"), "planned_start_date": ("Baseline start", "Schedule"),
    "planned_end_date": ("Baseline end", "Schedule"), "actual_start_date": ("Actual start (null if not started)", "Delay"),
    "actual_end_date": ("Actual end (null if not finished)", "Delay"), "milestone_status": ("Completed / In Progress / Not Started", "Progress"),
    "delay_cause": ("Dominant cause of the stage's own delay", "Root cause Pareto"), "planned_duration_days": ("Planned length", "Delay %"),
    "actual_duration_days": ("Actual length", "Stage overrun"), "start_delay_days": ("Actual - planned start", "Inherited delay"),
    "end_delay_days": ("Actual - planned end", "Own delay = end - start delay")}),
"fact_revenue": ("One row per invoice or revenue adjustment", "Billing system", "Milestone billing on stage completion; change orders, PVC and LD as separate lines (C05)", {
    "invoice_no": ("Invoice key", "De-duplication"), "project_id": ("Project", "Join"), "invoice_date": ("Invoice date", "Revenue trend"),
    "revenue_type": ("Milestone Billing / Change Order / Price Variation / Liquidated Damages", "Revenue bridge"),
    "stage_id": ("Billing milestone stage", "Timing"), "amount_inr": ("Amount, Rs (LD negative)", "Revenue")}),
"ref_steel_price_index": ("One row per month", "Market data feed", "Synthetic index shaped like the 2021-22 spike (C11)", {
    "month_start": ("Month", "Join on PO month"), "steel_price_index": ("Index, Apr 2021 = 100", "Benchmark price, PVC")}),
}


def main():
    out = ["# Data Dictionary", "",
           "Generated by `python/reporting/build_data_dictionary.py` from the files in `data/processed/`. Type, nullability, "
           "null count and example are read from the data itself. All values are synthetic; all names are fictional.", "",
           "Types: `text`, `integer`, `decimal`, `date`, `boolean`. Money columns ending `_inr` are full rupees (C01).", ""]
    out.append("| Table | Grain | Rows |\n|---|---|---|")
    files = {p.stem: pd.read_csv(p) for p in sorted(C.DATA_PROCESSED.glob("*.csv"))}
    for name in D:
        out.append(f"| [{name}](#{name}) | {D[name][0]} | {len(files[name]):,} |")
    out.append("")
    for name, (grain, source, logic, cols) in D.items():
        df = files[name]
        out += [f"## {name}", "", f"- **Grain:** {grain}", f"- **Imitates:** {source}", f"- **Synthetic logic:** {logic}",
                f"- **Rows:** {len(df):,}", "",
                "| Column | Type | Nullable | Nulls | Example | Meaning | How it is used |", "|---|---|---|---|---|---|---|"]
        missing = set(df.columns) - set(cols)
        assert not missing, f"{name}: undocumented columns {missing}"
        for col in df.columns:
            s = df[col]
            if col.endswith("_date") or col in ("date", "month_start"):
                typ = "date"
            elif s.dtype == bool or set(s.dropna().astype(str).unique()) <= {"True", "False"}:
                typ = "boolean"
            elif pd.api.types.is_integer_dtype(s) or (pd.api.types.is_float_dtype(s) and (s.dropna() % 1 == 0).all() and col.endswith(("_days", "_year", "count"))):
                typ = "integer"
            elif pd.api.types.is_numeric_dtype(s):
                typ = "decimal"
            else:
                typ = "text"
            ex = s.dropna().iloc[0] if s.notna().any() else ""
            if isinstance(ex, float):
                ex = f"{ex:,.2f}" if abs(ex) >= 1000 else round(ex, 3)
            meaning, use = cols[col]
            out.append(f"| `{col}` | {typ} | {'yes' if s.isna().any() else 'no'} | {int(s.isna().sum())} | {str(ex)[:28]} | {meaning} | {use} |")
        out.append("")
    (C.ROOT / "docs" / "DATA_DICTIONARY.md").write_text("\n".join(out))
    print(f"Wrote docs/DATA_DICTIONARY.md ({sum(len(v[3]) for v in D.values())} columns documented)")


if __name__ == "__main__":
    main()
