-- =====================================================================================
-- 07_window_functions.sql: trends, rankings and running totals
-- A window function computes across a set of rows related to the current row WITHOUT
-- collapsing them (GROUP BY collapses; OVER (...) keeps every row).
--   PARTITION BY = restart the calculation for each group
--   ORDER BY     = the order the window moves in (needed for running totals, LAG, LEAD)
--   ROWS BETWEEN = how many neighbouring rows the window includes (moving averages)
-- =====================================================================================
SET search_path TO projectco;

-- Q7.1 Monthly revenue and cost with running totals (SUM OVER ORDER BY)
WITH m AS (
    SELECT d.month_start,
           SUM(CASE WHEN x.kind = 'revenue' THEN x.amount ELSE 0 END) AS revenue,
           SUM(CASE WHEN x.kind = 'cost'    THEN x.amount ELSE 0 END) AS cost
    FROM (SELECT invoice_date AS dt, amount_inr AS amount, 'revenue' AS kind FROM fact_revenue
          UNION ALL
          SELECT posting_date, amount_inr, 'cost' FROM fact_project_cost) x
    JOIN dim_date d ON d.date = x.dt
    GROUP BY d.month_start
)
SELECT month_start,
       ROUND(revenue / 1e7, 1)                                  AS revenue_cr,
       ROUND(cost / 1e7, 1)                                     AS cost_cr,
       ROUND(SUM(revenue) OVER (ORDER BY month_start) / 1e7, 0) AS cumulative_revenue_cr,
       ROUND(SUM(cost)    OVER (ORDER BY month_start) / 1e7, 0) AS cumulative_cost_cr
FROM m
ORDER BY month_start;
-- UNION ALL stacks revenue and cost rows into one stream (UNION would also remove duplicates,
-- which is slower and wrong here: two equal amounts are two real transactions).

-- Q7.2 3-month moving average of monthly cost, and month-on-month change (AVG OVER + LAG)
WITH m AS (
    SELECT DATE_TRUNC('month', posting_date)::date AS month_start, SUM(amount_inr) AS cost
    FROM fact_project_cost GROUP BY 1
)
SELECT month_start,
       ROUND(cost / 1e7, 1) AS cost_cr,
       ROUND(AVG(cost) OVER (ORDER BY month_start ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) / 1e7, 1) AS cost_3m_avg_cr,
       ROUND(100 * (cost - LAG(cost) OVER (ORDER BY month_start)) / LAG(cost) OVER (ORDER BY month_start), 1) AS mom_change_pct
FROM m
ORDER BY month_start;

-- Q7.3 Rank projects by margin within each industry (RANK vs DENSE_RANK vs ROW_NUMBER)
SELECT industry, project_id, final_margin_pct,
       ROW_NUMBER() OVER w AS row_num,       -- 1,2,3,4 always unique
       RANK()       OVER w AS rnk,           -- ties share a rank, next rank skips (1,1,3)
       DENSE_RANK() OVER w AS dense_rnk      -- ties share a rank, no gaps     (1,1,2)
FROM v_project_kpis
WHERE status = 'Completed'
WINDOW w AS (PARTITION BY industry ORDER BY final_margin_pct DESC)
ORDER BY industry, row_num;

-- Q7.4 Best and worst project per industry (ROW_NUMBER to pick one row per group)
WITH r AS (
    SELECT industry, project_id, final_margin_pct,
           ROW_NUMBER() OVER (PARTITION BY industry ORDER BY final_margin_pct DESC) AS best,
           ROW_NUMBER() OVER (PARTITION BY industry ORDER BY final_margin_pct ASC)  AS worst
    FROM v_project_kpis WHERE status = 'Completed'
)
SELECT industry,
       MAX(project_id) FILTER (WHERE best = 1)        AS best_project,
       MAX(final_margin_pct) FILTER (WHERE best = 1)  AS best_margin_pct,
       MAX(project_id) FILTER (WHERE worst = 1)       AS worst_project,
       MAX(final_margin_pct) FILTER (WHERE worst = 1) AS worst_margin_pct
FROM r
GROUP BY industry
ORDER BY industry;

-- Q7.5 Next and previous milestone for one project (LEAD / LAG over stages)
SELECT m.project_id, st.stage_name, m.planned_end_date, m.actual_end_date, m.end_delay_days,
       LAG(m.end_delay_days)  OVER (PARTITION BY m.project_id ORDER BY st.stage_order) AS prev_stage_delay,
       LEAD(st.stage_name)    OVER (PARTITION BY m.project_id ORDER BY st.stage_order) AS next_stage
FROM fact_milestones m
JOIN dim_stage st ON st.stage_id = m.stage_id
WHERE m.project_id = (SELECT project_id FROM v_project_schedule ORDER BY delay_days DESC NULLS LAST LIMIT 1)
ORDER BY st.stage_order;

-- Q7.6 Supplier spend Pareto: cumulative share of spend (running total over a ranked list)
WITH s AS (
    SELECT supplier_id, SUM(line_value_inr) AS spend FROM fact_procurement GROUP BY supplier_id
)
SELECT supplier_id, ROUND(spend / 1e7, 1) AS spend_cr,
       ROUND(100 * spend / SUM(spend) OVER (), 1)                                        AS share_pct,
       ROUND(100 * SUM(spend) OVER (ORDER BY spend DESC ROWS UNBOUNDED PRECEDING) / SUM(spend) OVER (), 1) AS cumulative_pct
FROM s
ORDER BY spend DESC;

-- Q7.7 Quartiles of cost variance (NTILE) and each project's gap to its industry average (AVG OVER PARTITION)
SELECT project_id, industry, cost_variance_pct,
       NTILE(4) OVER (ORDER BY cost_variance_pct)                                  AS cv_quartile,
       ROUND(AVG(cost_variance_pct) OVER (PARTITION BY industry), 2)               AS industry_avg_cv_pct,
       ROUND(cost_variance_pct - AVG(cost_variance_pct) OVER (PARTITION BY industry), 2) AS gap_to_industry
FROM v_project_kpis
WHERE status = 'Completed'
ORDER BY cost_variance_pct DESC;

-- Q7.8 Weekly downtime trend for Works-East with a 4-week moving average
WITH w AS (
    SELECT DATE_TRUNC('week', e.log_date)::date AS week_start,
           100 * SUM(e.downtime_hours) / SUM(e.available_hours) AS downtime_pct
    FROM fact_equipment e
    JOIN dim_equipment q ON q.equipment_id = e.equipment_id
    WHERE q.works_location_id = 'LOC-W2'
    GROUP BY 1
)
SELECT week_start, ROUND(downtime_pct, 1) AS downtime_pct,
       ROUND(AVG(downtime_pct) OVER (ORDER BY week_start ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 1) AS downtime_4wk_avg
FROM w
ORDER BY week_start DESC
LIMIT 12;
