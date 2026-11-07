-- =====================================================================================
-- 00_views.sql: reusable project-level views (run once after loading the data)
-- Every later file builds on these, so each KPI formula is written exactly once.
-- =====================================================================================
SET search_path TO projectco;

-- -------------------------------------------------------------------------------------
-- v_project_financials: one row per project with budget, cost, revenue, profit, margin.
-- Business question: "For every project, what did we expect to earn and what are we earning?"
-- Tables: dim_project + fact_budget + fact_project_cost + fact_revenue
-- Why CTEs: each fact table is aggregated to project grain FIRST, then joined. Joining the
-- raw fact tables directly would multiply rows (8 budget rows x 100+ cost rows per project)
-- and double-count money: the classic "fan-out" mistake.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_project_financials AS
WITH budget AS (
    SELECT project_id,
           SUM(original_budget_inr)     AS estimated_cost,        -- bid estimate
           SUM(change_order_budget_inr) AS change_order_budget,
           SUM(revised_budget_inr)      AS revised_budget         -- estimate + approved change orders
    FROM fact_budget
    GROUP BY project_id
),
cost AS (
    SELECT project_id, SUM(amount_inr) AS actual_cost_to_date
    FROM fact_project_cost
    GROUP BY project_id
),
revenue AS (
    SELECT project_id,
           SUM(amount_inr) AS revenue_to_date,
           SUM(CASE WHEN revenue_type = 'Change Order'       THEN amount_inr ELSE 0 END) AS change_order_revenue,
           SUM(CASE WHEN revenue_type = 'Price Variation'    THEN amount_inr ELSE 0 END) AS pvc_revenue,
           SUM(CASE WHEN revenue_type = 'Liquidated Damages' THEN -amount_inr ELSE 0 END) AS ld_deducted
    FROM fact_revenue
    GROUP BY project_id
),
base AS (
    SELECT p.project_id, p.project_name, p.industry, p.status, p.client_id, p.project_manager_id,
           p.works_location_id, p.has_price_variation_clause, p.percent_complete,
           p.contract_value_inr, b.estimated_cost, b.revised_budget, b.change_order_budget,
           c.actual_cost_to_date,
           COALESCE(r.revenue_to_date, 0)      AS revenue_to_date,
           COALESCE(r.change_order_revenue, 0) AS change_order_revenue,
           COALESCE(r.pvc_revenue, 0)          AS pvc_revenue,
           COALESCE(r.ld_deducted, 0)          AS ld_deducted,
           -- Change-order revenue is priced at the bid margin, so it can be forecast from its budget
           b.change_order_budget * p.contract_value_inr / b.estimated_cost AS approved_co_value
    FROM dim_project p
    JOIN budget b ON b.project_id = p.project_id
    LEFT JOIN cost c ON c.project_id = p.project_id         -- LEFT JOIN: keep projects with no cost yet
    LEFT JOIN revenue r ON r.project_id = p.project_id
)
SELECT base.*,
       contract_value_inr - estimated_cost                                     AS estimated_profit,
       ROUND(100 * (contract_value_inr - estimated_cost) / contract_value_inr, 2) AS estimated_margin_pct,
       -- Earned value (in-progress projects): budget x % physically complete
       revised_budget * percent_complete / 100                                 AS earned_value,
       CASE WHEN status = 'In Progress'
            THEN ROUND((revised_budget * percent_complete / 100) / NULLIF(actual_cost_to_date, 0), 3)
       END                                                                     AS cpi,
       -- Final cost: actual for completed projects, Estimate at Completion (EAC = budget / CPI) otherwise
       CASE WHEN status = 'Completed' THEN actual_cost_to_date
            ELSE actual_cost_to_date / NULLIF(percent_complete / 100, 0) END   AS final_cost,
       -- Final revenue: actual for completed; contract + approved changes + PVC billed so far otherwise
       CASE WHEN status = 'Completed' THEN revenue_to_date
            ELSE contract_value_inr + approved_co_value + pvc_revenue END      AS final_revenue
FROM base;

CREATE OR REPLACE VIEW v_project_kpis AS
SELECT f.*,
       final_cost - revised_budget                                            AS cost_variance,
       ROUND(100 * (final_cost - revised_budget) / revised_budget, 2)          AS cost_variance_pct,
       final_revenue - final_cost                                              AS final_profit,
       ROUND(100 * (final_revenue - final_cost) / final_revenue, 2)            AS final_margin_pct,
       ROUND(estimated_margin_pct - 100 * (final_revenue - final_cost) / final_revenue, 2) AS margin_deterioration_pp,
       CASE WHEN 100 * (final_cost - revised_budget) / revised_budget < -2  THEN 'Under budget'
            WHEN 100 * (final_cost - revised_budget) / revised_budget <= 5  THEN 'On budget'
            WHEN 100 * (final_cost - revised_budget) / revised_budget <= 10 THEN 'Warning'
            ELSE 'Critical' END                                                AS cost_status       -- H01
FROM v_project_financials f;

-- -------------------------------------------------------------------------------------
-- v_project_schedule: planned vs actual (or current) timing per project.
-- For in-progress projects, "current slip" = the largest delay already visible on any stage.
-- -------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_project_schedule AS
WITH slip AS (
    SELECT project_id,
           MAX(COALESCE(end_delay_days, start_delay_days)) AS current_slip_days
    FROM fact_milestones
    WHERE actual_start_date IS NOT NULL
    GROUP BY project_id
)
SELECT p.project_id, p.status, p.planned_start_date, p.planned_end_date, p.actual_start_date, p.actual_end_date,
       p.planned_duration_days,
       CASE WHEN p.status = 'Completed' THEN p.actual_end_date - p.planned_end_date
            ELSE GREATEST(s.current_slip_days, 0) END                          AS delay_days,
       ROUND(100.0 * CASE WHEN p.status = 'Completed' THEN p.actual_end_date - p.planned_end_date
                          ELSE GREATEST(s.current_slip_days, 0) END / p.planned_duration_days, 2) AS delay_pct
FROM dim_project p
LEFT JOIN slip s ON s.project_id = p.project_id;

CREATE OR REPLACE VIEW v_project_schedule_status AS
SELECT s.*,
       CASE WHEN delay_pct <= 2  THEN 'On time'
            WHEN delay_pct <= 10 THEN 'Minor delay'
            WHEN delay_pct <= 20 THEN 'Major delay'
            ELSE 'Critical delay' END AS schedule_status                       -- H02
FROM v_project_schedule s;
