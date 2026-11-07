-- =====================================================================================
-- 03_profitability.sql: estimated vs actual profit and margin
-- Estimated Profit = Contract Value - Estimated (bid) Cost
-- Actual Profit    = Final Revenue - Actual Cost   (Final Revenue = contract + CO + PVC - LD, C05)
-- Margin %         = Profit / Revenue x 100
-- Margin deterioration (pp) = Estimated Margin % - Actual Margin %
-- =====================================================================================
SET search_path TO projectco;

-- Q3.1 Estimated vs actual profit and margin, completed projects, biggest margin loss first
SELECT project_id, industry,
       ROUND(contract_value_inr / 1e7, 1)   AS contract_cr,
       ROUND(final_revenue / 1e7, 1)        AS revenue_cr,
       ROUND(estimated_profit / 1e7, 2)     AS est_profit_cr,
       ROUND(final_profit / 1e7, 2)         AS actual_profit_cr,
       ROUND((final_profit - estimated_profit) / 1e7, 2) AS profit_variance_cr,
       estimated_margin_pct, final_margin_pct, margin_deterioration_pp
FROM v_project_kpis
WHERE status = 'Completed'
ORDER BY margin_deterioration_pp DESC;

-- Q3.2 Portfolio totals: how much profit did execution give away?
SELECT COUNT(*)                                                    AS completed_projects,
       ROUND(SUM(final_revenue) / 1e7, 0)                          AS revenue_cr,
       ROUND(SUM(estimated_profit) / 1e7, 1)                       AS estimated_profit_cr,
       ROUND(SUM(final_profit) / 1e7, 1)                           AS actual_profit_cr,
       ROUND(100 * SUM(estimated_profit) / SUM(contract_value_inr), 2) AS weighted_est_margin_pct,
       ROUND(100 * SUM(final_profit) / SUM(final_revenue), 2)      AS weighted_actual_margin_pct,
       SUM(CASE WHEN final_profit < 0 THEN 1 ELSE 0 END)           AS loss_making_projects,
       ROUND(SUM(ld_deducted) / 1e7, 1)                            AS ld_deducted_cr
FROM v_project_kpis
WHERE status = 'Completed';
-- Weighted margin = total profit / total revenue. A simple AVG of margins would let a
-- Rs 20 Cr project count as much as a Rs 400 Cr one.

-- Q3.3 Profitability by industry
SELECT industry, COUNT(*) AS projects,
       ROUND(SUM(final_revenue) / 1e7, 0)                          AS revenue_cr,
       ROUND(100 * SUM(estimated_profit) / SUM(contract_value_inr), 1) AS est_margin_pct,
       ROUND(100 * SUM(final_profit) / SUM(final_revenue), 1)      AS actual_margin_pct,
       ROUND(100 * SUM(estimated_profit) / SUM(contract_value_inr)
             - 100 * SUM(final_profit) / SUM(final_revenue), 1)    AS margin_lost_pp
FROM v_project_kpis
WHERE status = 'Completed'
GROUP BY industry
ORDER BY actual_margin_pct DESC;

-- Q3.4 Did the price-variation clause protect margin?
SELECT has_price_variation_clause AS has_pvc, COUNT(*) AS projects,
       ROUND(AVG(cost_variance_pct), 2)        AS avg_cv_pct,
       ROUND(SUM(pvc_revenue) / 1e7, 1)        AS pvc_recovered_cr,
       ROUND(AVG(margin_deterioration_pp), 2)  AS avg_margin_lost_pp
FROM v_project_kpis
WHERE status = 'Completed'
GROUP BY has_price_variation_clause;

-- Q3.5 Why revenue growth is not the same as better performance: revenue vs margin by FY of completion
SELECT d.fiscal_year AS completion_fy, COUNT(*) AS projects_completed,
       ROUND(SUM(k.final_revenue) / 1e7, 0)                     AS revenue_cr,
       ROUND(SUM(k.final_profit) / 1e7, 1)                      AS profit_cr,
       ROUND(100 * SUM(k.final_profit) / SUM(k.final_revenue), 1) AS margin_pct
FROM v_project_kpis k
JOIN dim_project p ON p.project_id = k.project_id
JOIN dim_date d    ON d.date = p.actual_end_date
GROUP BY d.fiscal_year
ORDER BY d.fiscal_year;

-- Q3.6 Loss-making and thin-margin projects (< 5%), with their main symptoms
SELECT k.project_id, k.project_name, k.industry, k.final_margin_pct, k.cost_variance_pct,
       s.delay_days, ROUND(k.ld_deducted / 1e7, 2) AS ld_cr
FROM v_project_kpis k
JOIN v_project_schedule s ON s.project_id = k.project_id
WHERE k.status = 'Completed' AND k.final_margin_pct < 5
ORDER BY k.final_margin_pct;

-- Q3.7 Profitability by project manager (read with care: PMs are not given equal projects)
SELECT e.employee_name AS project_manager, COUNT(*) AS projects,
       ROUND(AVG(k.contract_value_inr) / 1e7, 0)          AS avg_contract_cr,
       ROUND(100 * SUM(k.final_profit) / SUM(k.final_revenue), 1) AS margin_pct,
       ROUND(AVG(k.margin_deterioration_pp), 1)           AS avg_margin_lost_pp
FROM v_project_kpis k
JOIN dim_employee e ON e.employee_id = k.project_manager_id
WHERE k.status = 'Completed'
GROUP BY e.employee_name
ORDER BY avg_margin_lost_pp DESC;
