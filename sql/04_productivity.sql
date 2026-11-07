-- =====================================================================================
-- 04_productivity.sql: works productivity, machine utilisation, downtime, bottlenecks
-- Labour productivity   = man-hours per tonne (MH/t, lower is better)
-- Output achievement %  = actual output / planned output x 100
-- Defect (rework) rate  = rework tonnes / output tonnes x 100
-- Machine utilisation % = operating hours / available hours x 100
-- Downtime %            = downtime hours / available hours x 100   (F03)
-- =====================================================================================
SET search_path TO projectco;

-- Q4.1 Works scorecard: productivity, quality and unit cost
SELECT l.location_name AS works,
       ROUND(SUM(o.actual_output_t))                                            AS output_t,
       ROUND(SUM(o.regular_labour_hours + o.overtime_labour_hours) / SUM(o.actual_output_t), 1) AS mh_per_tonne,
       ROUND(100 * SUM(o.overtime_labour_hours) / SUM(o.regular_labour_hours + o.overtime_labour_hours), 1) AS overtime_pct,
       ROUND(100 * SUM(o.rework_t) / SUM(o.actual_output_t), 2)                 AS defect_rate_pct,
       ROUND(SUM(o.labour_cost_inr + o.machine_cost_inr + o.energy_cost_inr) / SUM(o.actual_output_t)) AS conversion_cost_per_t,
       ROUND(100.0 * AVG(o.capacity_constrained::int), 1)                       AS days_capacity_constrained_pct
FROM fact_operations o
JOIN dim_location l ON l.location_id = o.works_location_id
GROUP BY l.location_name
ORDER BY mh_per_tonne DESC;
-- Standard is 30 MH/t (F04). Anything above it is time lost to idling, rework or slow work.

-- Q4.2 Machine utilisation and downtime by works and fiscal year
SELECT l.location_name AS works, d.fiscal_year,
       ROUND(100 * SUM(e.operating_hours) / SUM(e.available_hours), 1) AS utilisation_pct,
       ROUND(100 * SUM(e.downtime_hours) / SUM(e.available_hours), 1)  AS downtime_pct,
       ROUND(100 * SUM(e.idle_hours) / SUM(e.available_hours), 1)      AS idle_pct
FROM fact_equipment e
JOIN dim_equipment q ON q.equipment_id = e.equipment_id
JOIN dim_location l  ON l.location_id = q.works_location_id
JOIN dim_date d      ON d.date = e.log_date
GROUP BY l.location_name, d.fiscal_year
ORDER BY l.location_name, d.fiscal_year;
-- Utilisation + downtime + idle = 100% of available time. Low utilisation caused by idle time
-- means "no work loaded"; low utilisation caused by downtime means "machine broken".

-- Q4.3 The ten machines with the worst downtime, ranked
SELECT q.equipment_id, q.equipment_name, wc.work_centre_name, q.commission_year,
       ROUND(100 * SUM(e.downtime_hours) / SUM(e.available_hours), 1) AS downtime_pct,
       COUNT(*) FILTER (WHERE e.downtime_hours > 0)                     AS breakdown_days,
       RANK() OVER (ORDER BY SUM(e.downtime_hours) / SUM(e.available_hours) DESC) AS downtime_rank
FROM fact_equipment e
JOIN dim_equipment q    ON q.equipment_id = e.equipment_id
JOIN dim_work_centre wc ON wc.work_centre_id = q.work_centre_id
GROUP BY q.equipment_id, q.equipment_name, wc.work_centre_name, q.commission_year
ORDER BY downtime_rank
LIMIT 10;

-- Q4.4 Bottlenecks: which work centre limited output on capacity-constrained days?
SELECT wc.work_centre_name, COUNT(*) AS constrained_project_days,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY wc.works_location_id), 1) AS share_within_works_pct
FROM fact_operations o
JOIN dim_work_centre wc ON wc.work_centre_id = o.bottleneck_work_centre_id
WHERE o.capacity_constrained
GROUP BY wc.works_location_id, wc.work_centre_name
ORDER BY wc.works_location_id, constrained_project_days DESC;

-- Q4.5 Downtime by reason (input to a Pareto chart)
SELECT downtime_reason, ROUND(SUM(downtime_hours)) AS downtime_hours,
       ROUND(100 * SUM(downtime_hours) / SUM(SUM(downtime_hours)) OVER (), 1) AS share_pct
FROM fact_equipment
WHERE downtime_hours > 0
GROUP BY downtime_reason
ORDER BY downtime_hours DESC;

-- Q4.6 Output achievement by works and quarter: are works delivering the plan?
SELECT o.works_location_id, d.fiscal_year, d.fiscal_quarter,
       ROUND(100 * SUM(o.actual_output_t) / SUM(o.planned_output_t), 1) AS output_achievement_pct
FROM fact_operations o
JOIN dim_date d ON d.date = o.production_date
GROUP BY o.works_location_id, d.fiscal_year, d.fiscal_quarter
ORDER BY o.works_location_id, d.fiscal_year, d.fiscal_quarter;

-- Q4.7 Site labour efficiency by project manager
-- Efficiency = earned hours / actual hours. 100% means the crew did the planned work in the planned time.
SELECT e.employee_name AS project_manager,
       ROUND(100 * SUM(l.earned_hours) / SUM(l.regular_hours + l.overtime_hours + l.idle_hours), 1) AS labour_efficiency_pct,
       ROUND(100 * SUM(l.idle_hours) / SUM(l.regular_hours + l.overtime_hours + l.idle_hours), 1)    AS idle_pct
FROM fact_labor l
JOIN dim_project p  ON p.project_id = l.project_id
JOIN dim_employee e ON e.employee_id = p.project_manager_id
WHERE l.labour_type = 'Site Erection'
GROUP BY e.employee_name
ORDER BY labour_efficiency_pct;
