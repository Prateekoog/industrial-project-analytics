-- =====================================================================================
-- validation.sql: reconciliation checks inside the database (mirrors python/validation)
-- Every row should return result = 'PASS'.
-- =====================================================================================
SET search_path TO projectco;

WITH
material AS (   -- material in the cost ledger must equal received purchase-order value
    SELECT COALESCE(l.project_id, p.project_id) AS project_id,
           ABS(COALESCE(l.amt, 0) - COALESCE(p.amt, 0)) AS diff
    FROM (SELECT project_id, SUM(amount_inr) amt FROM fact_project_cost
           WHERE cost_category_id = 1 AND source_system = 'Procurement' GROUP BY 1) l
    FULL OUTER JOIN (SELECT project_id, SUM(line_value_inr) amt FROM fact_procurement
                      WHERE line_status = 'Received' GROUP BY 1) p ON p.project_id = l.project_id
),
works_labour AS (
    SELECT o.project_id, ABS(o.amt - COALESCE(l.amt, 0)) AS diff
    FROM (SELECT project_id, SUM(labour_cost_inr) amt FROM fact_operations GROUP BY 1) o
    LEFT JOIN (SELECT project_id, SUM(amount_inr) amt FROM fact_project_cost
                WHERE cost_category_id = 2 AND source_system = 'Production' GROUP BY 1) l ON l.project_id = o.project_id
),
site_labour AS (
    SELECT t.project_id, ABS(t.amt - COALESCE(l.amt, 0)) AS diff
    FROM (SELECT project_id, SUM(labour_cost_inr) amt FROM fact_labor GROUP BY 1) t
    LEFT JOIN (SELECT project_id, SUM(amount_inr) amt FROM fact_project_cost
                WHERE cost_category_id = 2 AND source_system = 'Timesheet' GROUP BY 1) l ON l.project_id = t.project_id
),
billing AS (    -- completed projects must have billed exactly 100% of contract value in milestones
    SELECT p.project_id,
           ABS(SUM(r.amount_inr) FILTER (WHERE r.revenue_type = 'Milestone Billing') - p.contract_value_inr) AS diff
    FROM dim_project p JOIN fact_revenue r ON r.project_id = p.project_id
    WHERE p.status = 'Completed'
    GROUP BY p.project_id, p.contract_value_inr
),
ld AS (
    SELECT p.project_id,
           COALESCE(-SUM(r.amount_inr) FILTER (WHERE r.revenue_type = 'Liquidated Damages'), 0) AS ld,
           p.contract_value_inr
    FROM dim_project p LEFT JOIN fact_revenue r ON r.project_id = p.project_id
    GROUP BY p.project_id, p.contract_value_inr
),
end_dates AS (
    SELECT p.project_id, p.actual_end_date, m.actual_end_date AS commissioning_end
    FROM dim_project p JOIN fact_milestones m ON m.project_id = p.project_id AND m.stage_id = 7
    WHERE p.status = 'Completed'
)
SELECT 'Material ledger = received PO value'          AS check_name, CASE WHEN MAX(diff) <= 1 THEN 'PASS' ELSE 'FAIL' END AS result, ROUND(MAX(diff), 2) AS max_diff FROM material
UNION ALL SELECT 'Works labour ledger = production log',      CASE WHEN MAX(diff) <= 1 THEN 'PASS' ELSE 'FAIL' END, ROUND(MAX(diff), 2) FROM works_labour
UNION ALL SELECT 'Site labour ledger = timesheets',           CASE WHEN MAX(diff) <= 1 THEN 'PASS' ELSE 'FAIL' END, ROUND(MAX(diff), 2) FROM site_labour
UNION ALL SELECT 'Completed projects billed 100% of contract', CASE WHEN MAX(diff) <= 1 THEN 'PASS' ELSE 'FAIL' END, ROUND(MAX(diff), 2) FROM billing
UNION ALL SELECT 'LD within 5% cap',                           CASE WHEN BOOL_AND(ld <= 0.05 * contract_value_inr + 1) THEN 'PASS' ELSE 'FAIL' END, NULL FROM ld
UNION ALL SELECT 'Project end = commissioning end',            CASE WHEN BOOL_AND(actual_end_date = commissioning_end) THEN 'PASS' ELSE 'FAIL' END, NULL FROM end_dates
UNION ALL SELECT 'Budget totals: revised = original + CO',     CASE WHEN BOOL_AND(revised_budget_inr = original_budget_inr + change_order_budget_inr) THEN 'PASS' ELSE 'FAIL' END, NULL FROM fact_budget
UNION ALL SELECT 'Views do not fan out: one KPI row per project', CASE WHEN COUNT(*) = (SELECT COUNT(*) FROM dim_project) THEN 'PASS' ELSE 'FAIL' END, COUNT(*) FROM v_project_kpis
UNION ALL SELECT 'View cost total = ledger total',             CASE WHEN ABS(SUM(actual_cost_to_date) - (SELECT SUM(amount_inr) FROM fact_project_cost)) < 1 THEN 'PASS' ELSE 'FAIL' END, NULL FROM v_project_kpis
UNION ALL SELECT 'View revenue total = billing total',         CASE WHEN ABS(SUM(revenue_to_date) - (SELECT SUM(amount_inr) FROM fact_revenue)) < 1 THEN 'PASS' ELSE 'FAIL' END, NULL FROM v_project_kpis
UNION ALL SELECT 'Machine hours balance',                      CASE WHEN BOOL_AND(downtime_hours + operating_hours <= available_hours + 0.01) THEN 'PASS' ELSE 'FAIL' END, NULL FROM fact_equipment;
