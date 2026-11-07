-- =====================================================================================
-- 05_procurement.sql: supplier performance and total cost to the project
-- On-time delivery % (OTD) = deliveries on or before promised date / deliveries x 100  (G03)
-- Lead time                = PO date -> goods receipt, days                          (G04)
-- Price index vs market    = unit price / benchmark price (1.00 = market; < 1 cheaper)
-- Rejection rate           = rejected quantity / delivered quantity x 100
-- =====================================================================================
SET search_path TO projectco;

-- Q5.1 Supplier scorecard
SELECT s.supplier_id, s.supplier_name, s.material_group,
       COUNT(*)                                                            AS po_lines,
       ROUND(SUM(f.line_value_inr) / 1e7, 2)                               AS spend_cr,
       ROUND(100.0 * AVG(f.is_on_time::int), 1)                            AS otd_pct,
       ROUND(AVG(f.delivery_delay_days) FILTER (WHERE f.delivery_delay_days > 0), 1) AS avg_days_late_when_late,
       ROUND(AVG(f.lead_time_days), 0)                                     AS avg_lead_time_days,
       ROUND(SUM(f.line_value_inr) / SUM(f.quantity * f.benchmark_unit_price_inr), 3) AS price_index,
       ROUND(100 * SUM(f.qty_rejected) / SUM(f.quantity), 2)               AS rejection_pct
FROM fact_procurement f
JOIN dim_supplier s ON s.supplier_id = f.supplier_id
WHERE f.delivery_date IS NOT NULL
GROUP BY s.supplier_id, s.supplier_name, s.material_group
ORDER BY otd_pct;

-- Q5.2 Rank suppliers within each material group (DENSE_RANK: ties share a rank, no gaps)
WITH sc AS (
    SELECT s.material_group, s.supplier_name,
           AVG(f.is_on_time::int)                                         AS otd,
           SUM(f.line_value_inr) / SUM(f.quantity * f.benchmark_unit_price_inr) AS price_index
    FROM fact_procurement f
    JOIN dim_supplier s ON s.supplier_id = f.supplier_id
    WHERE f.delivery_date IS NOT NULL
    GROUP BY s.material_group, s.supplier_name
)
SELECT material_group, supplier_name, ROUND(100 * otd, 1) AS otd_pct, ROUND(price_index, 3) AS price_index,
       DENSE_RANK() OVER (PARTITION BY material_group ORDER BY price_index)  AS price_rank,
       DENSE_RANK() OVER (PARTITION BY material_group ORDER BY otd DESC)     AS reliability_rank
FROM sc
ORDER BY material_group, price_rank;

-- Q5.3 Is the cheapest supplier really cheaper? Price saving vs cost of lateness on critical items.
-- A critical line (A-class or steel) delivered after it was needed holds up the project.
-- Delay cost per day is approximated from the project's time-based costs (site overhead + cranes),
-- which keep running while work waits: 60% of overhead + site equipment budget, spread per planned day.
WITH project_day_cost AS (
    SELECT p.project_id,
           SUM(CASE WHEN b.cost_category_id = 7 THEN 0.6 * b.revised_budget_inr
                    WHEN b.cost_category_id = 4 THEN 0.5 * b.revised_budget_inr ELSE 0 END)
           / MAX(p.planned_duration_days) AS time_cost_per_day
    FROM dim_project p
    JOIN fact_budget b ON b.project_id = p.project_id
    GROUP BY p.project_id
),
lines AS (
    SELECT f.supplier_id, f.line_value_inr, f.quantity * f.benchmark_unit_price_inr AS market_value,
           CASE WHEN (m.criticality_class = 'A' OR m.is_steel_linked) AND f.grn_date > f.need_by_date
                THEN (f.grn_date - f.need_by_date) * d.time_cost_per_day * 0.25 ELSE 0 END AS lateness_cost
    FROM fact_procurement f
    JOIN dim_material m       ON m.material_id = f.material_id
    JOIN project_day_cost d   ON d.project_id = f.project_id
    WHERE f.grn_date IS NOT NULL
)
SELECT s.supplier_name, s.material_group,
       ROUND(SUM(market_value - line_value_inr) / 1e5, 1) AS price_saving_vs_market_lakh,
       ROUND(SUM(lateness_cost) / 1e5, 1)                 AS lateness_cost_lakh,
       ROUND(SUM(market_value - line_value_inr - lateness_cost) / 1e5, 1) AS net_benefit_lakh
FROM lines l
JOIN dim_supplier s ON s.supplier_id = l.supplier_id
GROUP BY s.supplier_name, s.material_group
ORDER BY net_benefit_lakh;
-- The 0.25 factor is deliberately conservative: not every late item stops the whole site (only
-- items on the critical path do). It is an assumption to test, not a fact; see docs/ROI_ANALYSIS.md.

-- Q5.4 Which materials have the most volatile prices? (coefficient of variation of price vs standard)
SELECT m.material_group, m.is_steel_linked, COUNT(*) AS po_lines,
       ROUND(AVG(f.unit_price_inr / m.standard_price_inr), 3)                         AS avg_price_ratio,
       ROUND(STDDEV(f.unit_price_inr / m.standard_price_inr) / AVG(f.unit_price_inr / m.standard_price_inr), 3) AS coeff_variation
FROM fact_procurement f
JOIN dim_material m ON m.material_id = f.material_id
GROUP BY m.material_group, m.is_steel_linked
ORDER BY coeff_variation DESC;

-- Q5.5 Late critical deliveries per project vs its cost and schedule outcome
SELECT k.project_id, k.industry,
       COUNT(*) FILTER (WHERE (m.criticality_class = 'A' OR m.is_steel_linked) AND f.grn_date > f.need_by_date) AS late_critical_lines,
       ROUND(100.0 * AVG(CASE WHEN s.supplier_id IN (
                 SELECT supplier_id FROM fact_procurement WHERE delivery_date IS NOT NULL
                 GROUP BY supplier_id HAVING AVG(is_on_time::int) < 0.6) THEN 1 ELSE 0 END), 1) AS low_otd_supplier_share_pct,
       k.cost_variance_pct, sc.delay_days
FROM fact_procurement f
JOIN dim_material m        ON m.material_id = f.material_id
JOIN dim_supplier s        ON s.supplier_id = f.supplier_id
JOIN v_project_kpis k      ON k.project_id = f.project_id
JOIN v_project_schedule sc ON sc.project_id = f.project_id
WHERE k.status = 'Completed'
GROUP BY k.project_id, k.industry, k.cost_variance_pct, sc.delay_days
ORDER BY late_critical_lines DESC
LIMIT 15;

-- Q5.6 Monthly procurement spend and on-time rate (DATE_TRUNC groups dates into months)
SELECT DATE_TRUNC('quarter', po_date)::date AS quarter_start,
       ROUND(SUM(line_value_inr) / 1e7, 1)  AS spend_cr,
       ROUND(100.0 * AVG(is_on_time::int), 1) AS otd_pct
FROM fact_procurement
GROUP BY 1
ORDER BY 1;
