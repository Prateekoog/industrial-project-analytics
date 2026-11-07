# Power BI Semantic Model

Source: `ProjectCo_PowerBI_Dataset.xlsx` (one Excel Table per sheet) or the same tables as CSVs in `powerbi/data/`. Column meanings are in [docs/DATA_DICTIONARY.md](../docs/DATA_DICTIONARY.md). This page covers only what is specific to Power BI.

## Differences from the database

The PostgreSQL schema is normalised (client, employee and location are separate tables). For Power BI they are **flattened into the dimensions** at export:

| Power BI table | What was added | Why |
|---|---|---|
| `dim_project` | `client_name`, `project_manager`, `site_city`, `site_state`, `region`, `works_name`, plus the analysis snapshot: `cost_variance_pct`, `final_margin_pct`, `estimated_margin_pct`, `cost_status`, `delay_days`, `schedule_status`, `risk_score`, `risk_tier` | A star schema has one filter path from each dimension to each fact. Keeping client, PM and location as separate tables would create a second path (for example location → project → operations *and* location → operations), which Power BI resolves by deactivating a relationship. |
| `dim_equipment` | `process_type`, `works_name` | Same reason: avoids a snowflake through `dim_work_centre`. |
| `dim_location` | Works rows only | Acts as the **Works** dimension for `fact_operations` and `dim_equipment`. |
| `ref_initiatives` | New, disconnected | Feeds the Potential Savings KPI and the ROI visual. |

## Relationships

All relationships are **many-to-one (*:1)** from fact to dimension, with **single** cross-filter direction (dimension filters fact). No bi-directional filters are used: they create ambiguous paths and slow the model, and nothing here needs them.

| From (many) | To (one) | Active | Notes |
|---|---|---|---|
| `fact_budget[project_id]` | `dim_project[project_id]` | Yes | |
| `fact_budget[cost_category_id]` | `dim_cost_category[cost_category_id]` | Yes | |
| `fact_project_cost[project_id]` | `dim_project[project_id]` | Yes | |
| `fact_project_cost[cost_category_id]` | `dim_cost_category[cost_category_id]` | Yes | Lets budget and actual sit side by side by category |
| `fact_project_cost[posting_date]` | `dim_date[date]` | Yes | |
| `fact_revenue[project_id]` | `dim_project[project_id]` | Yes | |
| `fact_revenue[invoice_date]` | `dim_date[date]` | Yes | |
| `fact_revenue[stage_id]` | `dim_stage[stage_id]` | Yes | |
| `fact_procurement[project_id]` | `dim_project[project_id]` | Yes | |
| `fact_procurement[supplier_id]` | `dim_supplier[supplier_id]` | Yes | |
| `fact_procurement[material_id]` | `dim_material[material_id]` | Yes | |
| `fact_procurement[po_date]` | `dim_date[date]` | Yes | Spend by order month |
| `fact_procurement[grn_date]` | `dim_date[date]` | **No** | Used with `USERELATIONSHIP` for receipts by month |
| `fact_operations[project_id]` | `dim_project[project_id]` | Yes | |
| `fact_operations[works_location_id]` | `dim_location[location_id]` | Yes | Works slicer |
| `fact_operations[production_date]` | `dim_date[date]` | Yes | |
| `fact_operations[bottleneck_work_centre_id]` | `dim_work_centre[work_centre_id]` | Yes | Bottleneck analysis |
| `fact_equipment[equipment_id]` | `dim_equipment[equipment_id]` | Yes | |
| `fact_equipment[log_date]` | `dim_date[date]` | Yes | |
| `dim_equipment[works_location_id]` | `dim_location[location_id]` | Yes | Lets the Works slicer filter machine data too |
| `fact_labor[project_id]` | `dim_project[project_id]` | Yes | |
| `fact_labor[week_ending_date]` | `dim_date[date]` | Yes | |
| `fact_milestones[project_id]` | `dim_project[project_id]` | Yes | |
| `fact_milestones[stage_id]` | `dim_stage[stage_id]` | Yes | |

`dim_project` is deliberately **not** related to `dim_date`. A project has several dates (award, start, end), and relating any one of them would make a date slicer filter projects in a surprising way. Fiscal-year-of-award analysis uses a calculated column instead:

```dax
Award FY = "FY" & RIGHT ( YEAR ( EDATE ( dim_project[award_date], 9 ) ), 2 )
```
Adding 9 months moves April to January, so the calendar year becomes the Indian fiscal year that ends in March.

## Cardinality and grain check

| Table | Rows | Key |
|---|---|---|
| dim_project | 80 | project_id |
| dim_date | 2,648 | date |
| fact_equipment | 64,848 | machine_log_id |
| fact_operations | 13,396 | production_id |
| fact_project_cost | 8,835 | document_no |
| fact_procurement | 4,439 | po_line_id |
| fact_labor | 3,787 | labour_entry_id |
| fact_budget | 640 | project_id + cost_category_id |
| fact_milestones | 560 | project_id + stage_id |
| fact_revenue | 510 | invoice_no |

## Housekeeping after import

- Mark `dim_date` as the date table; sort `month_name` by `month_num` and `fiscal_quarter` by `fiscal_month_num`.
- Hide all key and foreign-key columns (`*_id`) from report view; users slice by names.
- Set summarisation to "Don't summarise" on IDs, years and percentages stored on `dim_project`.
- Format money measures with a thousands separator, and show them in crore via the display measures.
- Sort `cost_status` (Under budget, On budget, Warning, Critical) and `risk_tier` (Low to Critical) with small sort-order columns, or by adding the order to the label.
