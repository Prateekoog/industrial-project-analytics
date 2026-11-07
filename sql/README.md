# SQL Analysis (PostgreSQL)

Run everything from the project root with `bash database/build_database.sh`. It creates the schema, loads the data, creates the views, runs the reconciliation checks and saves the output of every query to `sql/results/`, so each query's expected result can be read without a database.

| File | Business questions | SQL skills |
|---|---|---|
| `00_views.sql` | Project-level financials, KPIs and schedule (reused by every file) | CTEs, LEFT JOIN, CASE, NULLIF, aggregation before joining (avoids fan-out) |
| `01_basic_analysis.sql` | Portfolio size, industry mix, order intake by FY, repeat clients | SELECT, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, INNER JOIN, scalar subquery, PERCENTILE_CONT, EXTRACT |
| `02_cost_analysis.sql` | Which projects are over budget, by how much, which categories drive it; EVM for live projects | CTEs, LEFT JOIN, correlated subquery, `SUM(SUM()) OVER ()` for contribution % |
| `03_profitability.sql` | Estimated vs actual profit and margin; industry; PVC; revenue growth vs margin; PM view | Weighted ratios, joins to dim_date for fiscal year |
| `04_productivity.sql` | Works scorecard, utilisation and downtime, worst machines, bottlenecks, labour efficiency | FILTER clause, RANK, PARTITION BY, boolean casting |
| `05_procurement.sql` | Supplier scorecard, ranking within group, price saving vs lateness cost, price volatility | DENSE_RANK, STDDEV, subquery with HAVING, DATE_TRUNC |
| `06_project_delays.sql` | Delay by project and stage, root causes, delay cost, correlation, live projects slipping | CORR, GREATEST, correlated subquery |
| `07_window_functions.sql` | Running totals, moving averages, month-on-month change, ranks, Pareto, quartiles | SUM/AVG OVER, ROWS BETWEEN, LAG, LEAD, ROW_NUMBER, RANK, DENSE_RANK, NTILE, WINDOW clause, UNION ALL |
| `08_business_insights.sql` | Exception list for management, worse-than-industry projects, cost Pareto, downtime cost, procurement step times | UNION ALL, STRING_AGG, correlated subquery, PERCENTILE_CONT |
| `../database/validation.sql` | Do the numbers reconcile? | FULL OUTER JOIN, BOOL_AND, CASE-based PASS/FAIL |

Each query starts with a comment block that states the business question, the tables, the reason for the joins and how to modify it.

**Money convention:** amounts are stored in rupees; queries divide by `1e7` to show ₹ crore.
