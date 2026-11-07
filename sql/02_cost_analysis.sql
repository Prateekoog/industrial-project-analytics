-- =====================================================================================
-- 02_cost_analysis.sql: which projects are over budget, by how much, and why?
-- Cost Variance    = Actual Cost - Revised Budget          (C07: revised = bid + approved changes)
-- Cost Variance %  = Cost Variance / Revised Budget x 100
-- Status (H01): < -2% Under budget | -2..5% On budget | 5..10% Warning | > 10% Critical
-- Skills: CTEs, CASE, LEFT JOIN, GROUP BY, contribution %, earned value
-- =====================================================================================
SET search_path TO projectco;

-- Q2.1 Cost variance and status for every completed project, worst first
SELECT project_id, project_name, industry,
       ROUND(revised_budget / 1e7, 2)   AS revised_budget_cr,
       ROUND(final_cost / 1e7, 2)       AS actual_cost_cr,
       ROUND(cost_variance / 1e7, 2)    AS cost_variance_cr,
       cost_variance_pct, cost_status
FROM v_project_kpis
WHERE status = 'Completed'
ORDER BY cost_variance_pct DESC;

-- Q2.2 How many projects sit in each cost status band?
SELECT cost_status, COUNT(*) AS projects,
       ROUND(SUM(cost_variance) / 1e7, 1) AS total_variance_cr
FROM v_project_kpis
WHERE status = 'Completed'
GROUP BY cost_status
ORDER BY MIN(cost_variance_pct);

-- Q2.3 Which cost categories drive the overrun across completed projects?
-- Budget and actual are aggregated separately to project x category grain, then joined:
-- joining raw rows first would repeat each budget row once per cost posting (fan-out).
WITH budget AS (
    SELECT b.project_id, b.cost_category_id, b.revised_budget_inr
    FROM fact_budget b
    JOIN dim_project p ON p.project_id = b.project_id
    WHERE p.status = 'Completed'
),
actual AS (
    SELECT project_id, cost_category_id, SUM(amount_inr) AS actual_inr
    FROM fact_project_cost
    GROUP BY project_id, cost_category_id
)
SELECT cc.cost_category,
       ROUND(SUM(b.revised_budget_inr) / 1e7, 1)                         AS budget_cr,
       ROUND(SUM(a.actual_inr) / 1e7, 1)                                 AS actual_cr,
       ROUND(SUM(a.actual_inr - b.revised_budget_inr) / 1e7, 1)          AS variance_cr,
       ROUND(100 * SUM(a.actual_inr - b.revised_budget_inr) / SUM(b.revised_budget_inr), 1) AS variance_pct,
       ROUND(100 * SUM(a.actual_inr - b.revised_budget_inr)
             / SUM(SUM(a.actual_inr - b.revised_budget_inr)) OVER (), 1)  AS share_of_total_overrun_pct
FROM budget b
LEFT JOIN actual a ON a.project_id = b.project_id AND a.cost_category_id = b.cost_category_id
JOIN dim_cost_category cc ON cc.cost_category_id = b.cost_category_id
GROUP BY cc.cost_category
ORDER BY variance_cr DESC;
-- SUM(SUM(...)) OVER () = the grand total of the grouped variances, so each row's share adds to 100%.

-- Q2.4 Cost-driver decomposition for the single worst project
WITH worst AS (
    SELECT project_id FROM v_project_kpis
    WHERE status = 'Completed'
    ORDER BY cost_variance_pct DESC
    LIMIT 1
),
detail AS (
    SELECT b.cost_category_id, b.revised_budget_inr,
           (SELECT COALESCE(SUM(c.amount_inr), 0) FROM fact_project_cost c
             WHERE c.project_id = b.project_id AND c.cost_category_id = b.cost_category_id) AS actual_inr
    FROM fact_budget b
    WHERE b.project_id = (SELECT project_id FROM worst)
)
SELECT (SELECT project_id FROM worst) AS project_id, cc.cost_category,
       ROUND(d.revised_budget_inr / 1e7, 2)                      AS budget_cr,
       ROUND(d.actual_inr / 1e7, 2)                              AS actual_cr,
       ROUND((d.actual_inr - d.revised_budget_inr) / 1e7, 2)     AS variance_cr,
       ROUND(100 * (d.actual_inr - d.revised_budget_inr)
             / SUM(d.actual_inr - d.revised_budget_inr) OVER (), 1) AS contribution_pct
FROM detail d
JOIN dim_cost_category cc ON cc.cost_category_id = d.cost_category_id
ORDER BY variance_cr DESC;
-- The correlated subquery in `detail` re-runs for each budget row, using that row's project and category.

-- Q2.5 Cost variance by industry (does the bid team under-estimate some industries?)
SELECT industry, COUNT(*) AS completed_projects,
       ROUND(AVG(cost_variance_pct), 2)                                   AS avg_cv_pct,
       SUM(CASE WHEN cost_status IN ('Warning', 'Critical') THEN 1 ELSE 0 END) AS over_5pct
FROM v_project_kpis
WHERE status = 'Completed'
GROUP BY industry
ORDER BY avg_cv_pct DESC;

-- Q2.6 Where does the money come from? Cost by source system
SELECT source_system, cc.cost_category, ROUND(SUM(amount_inr) / 1e7, 1) AS cost_cr
FROM fact_project_cost f
JOIN dim_cost_category cc USING (cost_category_id)
GROUP BY source_system, cc.cost_category
ORDER BY source_system, cost_cr DESC;

-- Q2.7 In-progress projects: earned value and estimate at completion
-- EV = budget x % complete. CPI = EV / actual cost. CPI < 1 means each rupee spent earns less
-- than a rupee of planned work. EAC = budget / CPI forecasts the final cost if that efficiency continues.
SELECT project_id, project_name, percent_complete,
       ROUND(revised_budget / 1e7, 1)        AS budget_cr,
       ROUND(earned_value / 1e7, 1)          AS earned_value_cr,
       ROUND(actual_cost_to_date / 1e7, 1)   AS actual_cost_cr,
       cpi,
       ROUND(final_cost / 1e7, 1)            AS eac_cr,
       cost_variance_pct                     AS forecast_cv_pct,
       cost_status                           AS forecast_status
FROM v_project_kpis
WHERE status = 'In Progress'
ORDER BY cpi;
