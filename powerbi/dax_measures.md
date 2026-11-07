# DAX Measures

All measures live in a dedicated, empty table called `_Measures` (Home > Enter data > name it `_Measures`, then hide its column). Table and column names match `ProjectCo_PowerBI_Dataset.xlsx`.

**Why measures, not calculated columns.** A *measure* is calculated at query time for whatever filter the visual applies (an industry, a year, a supplier), so one `Actual Margin %` works on every page. A *calculated column* is computed once per row at refresh and stored. It is right for row-level labels (a size band, a flag) and wrong for ratios: summing or averaging a per-row margin gives a meaningless number. Rule used here: **ratios and totals are measures; row attributes are columns.**

**Why `DIVIDE` instead of `/`.** `DIVIDE(a, b)` returns blank instead of an error when `b` is 0 (for example, a supplier with no deliveries in the selected month).

**Completed vs in progress.** Revenue is billed by milestone, so for a running project "revenue to date minus cost to date" is not its profit. Financial KPIs on the executive page therefore use the `(Completed)` versions, which filter `dim_project[status] = "Completed"`. In-progress projects are judged with CPI and EAC.

---

## 1. Financial base measures

```dax
Total Revenue = SUM ( fact_revenue[amount_inr] )
```
Adds every invoice line: milestone bills, change orders and price variation, minus liquidated damages (LD rows are negative). It follows the revenue formula in ASSUMPTIONS C05.

```dax
Contract Value = SUM ( dim_project[contract_value_inr] )
```
The signed price. It lives on `dim_project` because it is one number per project. Do not slice it by cost category; it does not vary by category.

```dax
Estimated Cost = SUM ( fact_budget[original_budget_inr] )
Revised Budget = SUM ( fact_budget[revised_budget_inr] )
Actual Cost    = SUM ( fact_project_cost[amount_inr] )
```
Bid estimate, bid plus approved change orders, and ledger actuals. All three slice by project **and** by cost category, because both fact tables relate to `dim_cost_category`.

```dax
Cost Variance   = [Actual Cost] - [Revised Budget]
Cost Variance % = DIVIDE ( [Cost Variance], [Revised Budget] )
```
- Line 1: positive means overspent.
- Line 2: dividing by the revised budget (not the original) means client-paid extra scope is not counted as an overrun (C07).
- Format line 2 as a percentage.

```dax
Estimated Profit   = [Contract Value] - [Estimated Cost]
Actual Profit      = [Total Revenue] - [Actual Cost]
Estimated Margin % = DIVIDE ( [Estimated Profit], [Contract Value] )
Actual Margin %    = DIVIDE ( [Actual Profit], [Total Revenue] )
Margin Deterioration (pp) = ( [Estimated Margin %] - [Actual Margin %] ) * 100
```
- Margin divides by revenue, so large and small projects are compared fairly.
- Deterioration is in percentage points (pp): 13.2% to 8.3% is 4.9 pp, not 37%.

```dax
Actual Profit (Completed)   = CALCULATE ( [Actual Profit],   dim_project[status] = "Completed" )
Actual Margin % (Completed) = CALCULATE ( [Actual Margin %], dim_project[status] = "Completed" )
Estimated Profit (Completed)   = CALCULATE ( [Estimated Profit],   dim_project[status] = "Completed" )
Estimated Margin % (Completed) = CALCULATE ( [Estimated Margin %], dim_project[status] = "Completed" )
Cost Overrun % (Completed)  = CALCULATE ( [Cost Variance %], dim_project[status] = "Completed" )
Revenue (Completed)         = CALCULATE ( [Total Revenue],   dim_project[status] = "Completed" )
Actual Cost (Completed)     = CALCULATE ( [Actual Cost],     dim_project[status] = "Completed" )
```
`CALCULATE` evaluates the inner measure under an extra filter. Filtering `dim_project` flows down the one-to-many relationships to every fact table, so revenue, cost and budget are all restricted to the same projects.

```dax
LD Deducted = - CALCULATE ( SUM ( fact_revenue[amount_inr] ), fact_revenue[revenue_type] = "Liquidated Damages" )
```
LD rows are stored as negatives, so the leading minus shows LD as a positive amount lost.

## 2. Earned value (in-progress projects)

```dax
Earned Value =
SUMX (
    dim_project,
    dim_project[percent_complete] / 100 * CALCULATE ( [Revised Budget] )
)
```
- `SUMX` loops over each project in the current filter.
- `CALCULATE ( [Revised Budget] )` turns the row into a filter (*context transition*), so each project gets its own budget.
- That budget times % complete is the budgeted cost of the work actually done.

```dax
CPI = DIVIDE ( [Earned Value], [Actual Cost] )
EAC = DIVIDE ( [Revised Budget], [CPI] )
Forecast Cost Variance % = DIVIDE ( [EAC] - [Revised Budget], [Revised Budget] )
```
CPI below 1 means each rupee spent has earned less than a rupee of planned work. EAC assumes that efficiency continues to the end of the project. Use these with a page filter `status = "In Progress"`.

## 3. Project and schedule measures

```dax
Project Count       = COUNTROWS ( dim_project )
Completed Projects  = CALCULATE ( [Project Count], dim_project[status] = "Completed" )
Delayed Projects    = CALCULATE ( [Project Count], dim_project[status] = "Completed", dim_project[delay_days] > 0 )
Average Delay (days) = CALCULATE ( AVERAGE ( dim_project[delay_days] ), dim_project[status] = "Completed" )
Projects at High or Critical Risk = CALCULATE ( [Project Count], dim_project[risk_tier] IN { "High", "Critical" } )
```
`delay_days`, `cost_status`, `schedule_status`, `risk_score` and `risk_tier` are analysis outputs exported onto `dim_project`. The risk weights were derived in Python (`docs/BUSINESS_INSIGHTS.md`); recomputing them in DAX would duplicate logic.

```dax
Stage Own Delay (days) =
AVERAGEX (
    FILTER ( fact_milestones, fact_milestones[milestone_status] = "Completed" ),
    MAX ( 0, fact_milestones[end_delay_days] - fact_milestones[start_delay_days] )
)
```
The delay a stage *adds*: end delay minus the delay it inherited at its start. Put `dim_stage[stage_name]` on the axis.

## 4. Operations and productivity measures

```dax
Labour Hours        = SUM ( fact_operations[regular_labour_hours] ) + SUM ( fact_operations[overtime_labour_hours] )
Output (t)          = SUM ( fact_operations[actual_output_t] )
Labour Productivity (MH per t) = DIVIDE ( [Labour Hours], [Output (t)] )
Average Productivity (t per 100 MH) = DIVIDE ( [Output (t)] * 100, [Labour Hours] )
Output Achievement % = DIVIDE ( [Output (t)], SUM ( fact_operations[planned_output_t] ) )
Defect Rate %        = DIVIDE ( SUM ( fact_operations[rework_t] ), [Output (t)] )
Overtime %           = DIVIDE ( SUM ( fact_operations[overtime_labour_hours] ), [Labour Hours] )
Conversion Cost per Tonne =
DIVIDE (
    SUM ( fact_operations[labour_cost_inr] ) + SUM ( fact_operations[machine_cost_inr] ) + SUM ( fact_operations[energy_cost_inr] ),
    [Output (t)]
)
```
MH per tonne is "lower is better"; t per 100 MH is the same thing inverted, "higher is better". Show one per visual so the reader is not confused.

```dax
Machine Utilisation % = DIVIDE ( SUM ( fact_equipment[operating_hours] ), SUM ( fact_equipment[available_hours] ) )
Downtime %            = DIVIDE ( SUM ( fact_equipment[downtime_hours] ),  SUM ( fact_equipment[available_hours] ) )
Idle %                = DIVIDE ( SUM ( fact_equipment[idle_hours] ),      SUM ( fact_equipment[available_hours] ) )
Capacity Constrained Days % = AVERAGEX ( fact_operations, IF ( fact_operations[capacity_constrained], 1, 0 ) )
```
Utilisation + Downtime + Idle = 100% of available hours. This split is the point: low utilisation from *idle* means no work was loaded, while low utilisation from *downtime* means the machine was broken.

## 5. Procurement measures

```dax
Procurement Spend = SUM ( fact_procurement[line_value_inr] )

Supplier On-Time % =
VAR Delivered = CALCULATE ( COUNTROWS ( fact_procurement ), NOT ISBLANK ( fact_procurement[delivery_date] ) )
VAR OnTime    = CALCULATE ( COUNTROWS ( fact_procurement ), fact_procurement[is_on_time] = TRUE () )
RETURN DIVIDE ( OnTime, Delivered )
```
- `VAR` stores an intermediate result, which makes the measure readable and stops it computing the same thing twice.
- The denominator is *delivered* lines only; open orders are not late yet.

```dax
Late Deliveries      = CALCULATE ( COUNTROWS ( fact_procurement ), fact_procurement[is_on_time] = FALSE () )
Avg Lead Time (days) = AVERAGE ( fact_procurement[lead_time_days] )
Price Index vs Market =
DIVIDE (
    [Procurement Spend],
    SUMX ( fact_procurement, fact_procurement[quantity] * fact_procurement[benchmark_unit_price_inr] )
)
Rejection Rate % = DIVIDE ( SUM ( fact_procurement[qty_rejected] ), SUM ( fact_procurement[quantity] ) )
```
`SUMX` multiplies quantity by benchmark price row by row before adding. Multiplying two separate sums would be wrong. A price index of 0.93 means 7% below market.

## 6. Time intelligence

`dim_date` is marked as the date table (Table tools > Mark as date table > `date`).

```dax
Revenue FYTD = TOTALYTD ( [Total Revenue], dim_date[date], "3/31" )
```
Year-to-date for an Indian fiscal year: the third argument sets the year end to 31 March.

```dax
Actual Cost Running Total =
CALCULATE ( [Actual Cost], FILTER ( ALL ( dim_date[date] ), dim_date[date] <= MAX ( dim_date[date] ) ) )
```
`ALL` removes the current date filter, then `FILTER` keeps every date up to the last date in context. The result is a cumulative total.

```dax
Actual Cost 3M Avg = DIVIDE ( CALCULATE ( [Actual Cost], DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -3, MONTH ) ), 3 )
Receipts by GRN Month = CALCULATE ( [Procurement Spend], USERELATIONSHIP ( fact_procurement[grn_date], dim_date[date] ) )
```
`USERELATIONSHIP` switches on the inactive GRN-date relationship for this one measure. The active relationship uses the PO date.

## 7. Savings

```dax
Potential Savings (net per year) =
SUMX ( FILTER ( ref_initiatives, ref_initiatives[net_annual_benefit] > 0 ), ref_initiatives[net_annual_benefit] )
```
The sum of net annual benefit for the initiatives that are worth doing. The blanket supplier switch is negative and is excluded on purpose. `ref_initiatives` is a disconnected table, so no relationship is needed.

## 8. Display helpers

```dax
Revenue (Rs Cr)       = DIVIDE ( [Revenue (Completed)], 1e7 )
Actual Profit (Rs Cr) = DIVIDE ( [Actual Profit (Completed)], 1e7 )
Margin Label = FORMAT ( [Actual Margin % (Completed)], "0.0%" ) & " vs bid " & FORMAT ( [Estimated Margin % (Completed)], "0.0%" )
```
Indian presentation uses crore (1 Cr = 1e7 rupees). Keep the base measures in rupees and convert only for display.

## Reconciliation targets

After the build, the cards must show these values (from `reports/metrics.json`). If they don't, a relationship or filter is wrong.

| Measure | Expected |
|---|---|
| Project Count | 80 |
| Revenue (Rs Cr), completed | 5,247 |
| Actual Profit (Rs Cr), completed | 437 |
| Estimated Profit (Completed), Rs Cr | 683 |
| Actual Margin % (Completed) | 8.3% |
| Estimated Margin % (Completed) | 13.2% |
| Cost Overrun % (Completed) | 4.2% |
| LD Deducted, Rs Cr | 69.5 |
| Supplier On-Time % | 76.0% |
| Potential Savings, Rs Cr per year | 7.7 |
