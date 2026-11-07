-- =====================================================================================
-- 08_business_insights.sql: answers for management
-- "Which projects need attention, where can we cut cost, and what should we fix first?"
-- =====================================================================================
SET search_path TO projectco;

-- Q8.1 Exception list: every project that breaches at least one threshold, with the reason(s)
-- UNION ALL stacks three different exception rules into one list; STRING_AGG combines reasons per project.
WITH exceptions AS (
    SELECT project_id, 'Cost ' || cost_status || ' (' || cost_variance_pct || '%)' AS reason
    FROM v_project_kpis WHERE cost_status IN ('Warning', 'Critical')
    UNION ALL
    SELECT project_id, schedule_status || ' (' || delay_days || ' days)'
    FROM v_project_schedule_status WHERE schedule_status IN ('Major delay', 'Critical delay')
    UNION ALL
    SELECT project_id, 'Margin below 5% (' || final_margin_pct || '%)'
    FROM v_project_kpis WHERE final_margin_pct < 5
)
SELECT e.project_id, p.status, p.industry, COUNT(*) AS issues, STRING_AGG(e.reason, '; ') AS reasons
FROM exceptions e
JOIN dim_project p ON p.project_id = e.project_id
GROUP BY e.project_id, p.status, p.industry
ORDER BY p.status DESC, issues DESC, e.project_id;

-- Q8.2 Projects whose overrun is worse than their own industry's average (correlated subquery)
SELECT k.project_id, k.industry, k.cost_variance_pct,
       ROUND((SELECT AVG(k2.cost_variance_pct) FROM v_project_kpis k2
               WHERE k2.industry = k.industry AND k2.status = 'Completed'), 2) AS industry_avg
FROM v_project_kpis k
WHERE k.status = 'Completed'
  AND k.cost_variance_pct > (SELECT AVG(k2.cost_variance_pct) FROM v_project_kpis k2
                              WHERE k2.industry = k.industry AND k2.status = 'Completed') + 5
ORDER BY k.cost_variance_pct DESC;
-- The subquery references k.industry from the outer row, so it is re-evaluated per project.

-- Q8.3 Cost-reduction opportunity: Pareto of overrun rupees by category, completed projects
WITH v AS (
    SELECT cc.cost_category,
           SUM(a.actual) - SUM(b.revised_budget_inr) AS overrun
    FROM fact_budget b
    JOIN dim_project p ON p.project_id = b.project_id AND p.status = 'Completed'
    JOIN dim_cost_category cc ON cc.cost_category_id = b.cost_category_id
    JOIN (SELECT project_id, cost_category_id, SUM(amount_inr) AS actual
            FROM fact_project_cost GROUP BY 1, 2) a
      ON a.project_id = b.project_id AND a.cost_category_id = b.cost_category_id
    GROUP BY cc.cost_category
)
SELECT cost_category, ROUND(overrun / 1e7, 1) AS overrun_cr,
       ROUND(100 * SUM(overrun) OVER (ORDER BY overrun DESC ROWS UNBOUNDED PRECEDING)
             / SUM(overrun) FILTER (WHERE overrun > 0) OVER (), 1) AS cumulative_share_pct
FROM v
ORDER BY overrun DESC;

-- Q8.4 What unplanned downtime costs each works per year (idle crews + lost machine time)
-- Idle labour cost: 60% of crew stands idle during downtime (generator assumption, documented)
SELECT q.works_location_id, d.fiscal_year,
       ROUND(SUM(e.downtime_hours))                                       AS downtime_hours,
       ROUND(SUM(e.downtime_hours * q.machine_hour_rate_inr) / 1e5, 1)     AS machine_time_lost_lakh
FROM fact_equipment e
JOIN dim_equipment q ON q.equipment_id = e.equipment_id
JOIN dim_date d      ON d.date = e.log_date
WHERE d.fiscal_year IN ('FY25', 'FY26')
GROUP BY q.works_location_id, d.fiscal_year
ORDER BY q.works_location_id, d.fiscal_year;

-- Q8.5 Approval is the slowest admin step in procurement (input to the As-Is / To-Be redesign)
SELECT 'PR to approval' AS step, ROUND(AVG(pr_approval_date - pr_date), 1) AS avg_days,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pr_approval_date - pr_date) AS median_days,
       PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY pr_approval_date - pr_date) AS p90_days
FROM fact_procurement
UNION ALL
SELECT 'Approval to RFQ', ROUND(AVG(rfq_date - pr_approval_date), 1),
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rfq_date - pr_approval_date),
       PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY rfq_date - pr_approval_date)
FROM fact_procurement
UNION ALL
SELECT 'RFQ to PO', ROUND(AVG(po_date - rfq_date), 1),
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY po_date - rfq_date),
       PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY po_date - rfq_date)
FROM fact_procurement
UNION ALL
SELECT 'PO to supplier confirmation', ROUND(AVG(supplier_confirm_date - po_date), 1),
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY supplier_confirm_date - po_date),
       PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY supplier_confirm_date - po_date)
FROM fact_procurement WHERE supplier_confirm_date IS NOT NULL
UNION ALL
SELECT 'Delivery to goods receipt', ROUND(AVG(grn_date - delivery_date), 1),
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY grn_date - delivery_date),
       PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY grn_date - delivery_date)
FROM fact_procurement WHERE grn_date IS NOT NULL;

-- Q8.6 Order book health: in-progress projects ranked by forecast margin
SELECT k.project_id, k.project_name, k.percent_complete, k.cpi, k.cost_variance_pct AS forecast_cv_pct,
       k.estimated_margin_pct, k.final_margin_pct AS forecast_margin_pct, s.delay_days AS current_slip_days
FROM v_project_kpis k
JOIN v_project_schedule s ON s.project_id = k.project_id
WHERE k.status = 'In Progress'
ORDER BY k.final_margin_pct;
