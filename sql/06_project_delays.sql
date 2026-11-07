-- =====================================================================================
-- 06_project_delays.sql: which projects are late, why, and what does it cost?
-- Delay days        = actual (or current) end - planned (contractual) end
-- Delay %           = delay days / planned duration x 100
-- Stage's own delay = end delay - start delay: the slip a stage ADDS, excluding what it inherited
-- =====================================================================================
SET search_path TO projectco;

-- Q6.1 Delay and schedule status for completed projects
SELECT s.project_id, p.industry, s.planned_duration_days, s.delay_days, s.delay_pct, s.schedule_status,
       ROUND(k.ld_deducted / 1e7, 2) AS ld_cr
FROM v_project_schedule_status s
JOIN dim_project p    ON p.project_id = s.project_id
JOIN v_project_kpis k ON k.project_id = s.project_id
WHERE s.status = 'Completed'
ORDER BY s.delay_days DESC;

-- Q6.2 Which lifecycle stage adds the most slippage?
SELECT st.stage_order, st.stage_name,
       COUNT(*)                                                     AS completed_stages,
       ROUND(AVG(m.end_delay_days - m.start_delay_days), 1)         AS avg_own_delay_days,
       SUM(GREATEST(m.end_delay_days - m.start_delay_days, 0))      AS total_added_delay_days,
       ROUND(100.0 * SUM(GREATEST(m.end_delay_days - m.start_delay_days, 0))
             / SUM(SUM(GREATEST(m.end_delay_days - m.start_delay_days, 0))) OVER (), 1) AS share_pct
FROM fact_milestones m
JOIN dim_stage st ON st.stage_id = m.stage_id
WHERE m.milestone_status = 'Completed'
GROUP BY st.stage_order, st.stage_name
ORDER BY st.stage_order;
-- Procurement's own delay looks large partly because its "end" is the last goods receipt, which
-- is often a non-critical item. Fabrication and installation slips move the completion date.

-- Q6.3 Root causes of delay: how often, and how many days each cause added
SELECT m.delay_cause, COUNT(*) AS stages_affected,
       SUM(GREATEST(m.end_delay_days - m.start_delay_days, 0)) AS added_delay_days
FROM fact_milestones m
WHERE m.milestone_status = 'Completed' AND m.delay_cause <> 'On schedule'
  AND m.stage_id <> 3            -- procurement's "end" is its last (often non-critical) receipt; late critical
                                 -- items are already coded as 'Supplier delay' on fabrication / installation
GROUP BY m.delay_cause
ORDER BY added_delay_days DESC;

-- Q6.4 What did delay cost? LD plus the extra time-based overhead and crane hire
-- Extra time cost = (actual days / planned days - 1) x time-based budget (60% of overhead + site equipment share)
WITH t AS (
    SELECT p.project_id,
           SUM(CASE WHEN b.cost_category_id = 7 THEN 0.6 * b.revised_budget_inr
                    WHEN b.cost_category_id = 4 THEN 0.5 * b.revised_budget_inr ELSE 0 END) AS time_based_budget
    FROM dim_project p JOIN fact_budget b ON b.project_id = p.project_id
    GROUP BY p.project_id
)
SELECT ss.schedule_status, COUNT(*) AS projects,
       ROUND(AVG(ss.delay_days)) AS avg_delay_days,
       ROUND(SUM(k.ld_deducted) / 1e7, 1) AS ld_cr,
       ROUND(SUM(GREATEST(ss.delay_days, 0)::numeric / ss.planned_duration_days * t.time_based_budget) / 1e7, 1) AS extra_time_cost_cr,
       ROUND(AVG(k.final_margin_pct), 1) AS avg_margin_pct
FROM v_project_schedule_status ss
JOIN v_project_kpis k ON k.project_id = ss.project_id
JOIN t ON t.project_id = ss.project_id
WHERE ss.status = 'Completed'
GROUP BY ss.schedule_status
ORDER BY MIN(ss.delay_pct);

-- Q6.5 Do delays and cost overruns travel together? (Pearson correlation)
SELECT ROUND(CORR(s.delay_pct, k.cost_variance_pct)::numeric, 3)        AS corr_delay_vs_cost_variance,
       ROUND(CORR(s.delay_pct, k.margin_deterioration_pp)::numeric, 3)  AS corr_delay_vs_margin_loss
FROM v_project_schedule s
JOIN v_project_kpis k ON k.project_id = s.project_id
WHERE s.status = 'Completed';
-- Correlation is not causation: a design change can cause both a delay and an overrun.

-- Q6.6 In-progress projects already slipping (where management can still act)
SELECT s.project_id, p.project_name, p.percent_complete, s.delay_days AS current_slip_days, s.schedule_status,
       (SELECT st.stage_name FROM fact_milestones m JOIN dim_stage st ON st.stage_id = m.stage_id
         WHERE m.project_id = s.project_id AND m.milestone_status = 'In Progress'
         ORDER BY st.stage_order DESC LIMIT 1) AS current_stage
FROM v_project_schedule_status s
JOIN dim_project p ON p.project_id = s.project_id
WHERE s.status = 'In Progress' AND s.delay_days > 0
ORDER BY s.delay_days DESC;
