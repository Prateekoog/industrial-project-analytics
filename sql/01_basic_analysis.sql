-- =====================================================================================
-- 01_basic_analysis.sql: portfolio overview
-- Skills: SELECT, WHERE, ORDER BY, LIMIT, GROUP BY, HAVING, COUNT/SUM/AVG, JOIN, date functions
-- Money is shown in Rs crore: amount / 1e7.
-- =====================================================================================
SET search_path TO projectco;

-- Q1.1 How big is the portfolio, and how much of it is still running?
-- Tables: dim_project only. GROUP BY status collapses 80 rows into one row per status.
SELECT status,
       COUNT(*)                                   AS projects,
       ROUND(SUM(contract_value_inr) / 1e7, 1)    AS contract_value_cr,
       ROUND(AVG(contract_value_inr) / 1e7, 1)    AS avg_contract_cr
FROM dim_project
GROUP BY status
ORDER BY status;
-- Modify: add industry to the SELECT and GROUP BY to see the split per industry.

-- Q1.2 Which industries carry the most contract value?
-- Median is shown next to the average because contract values are right-skewed (B05):
-- a few very large contracts pull the average up.
SELECT industry,
       COUNT(*)                                                              AS projects,
       ROUND(SUM(contract_value_inr) / 1e7, 0)                               AS contract_value_cr,
       ROUND(100 * SUM(contract_value_inr) / (SELECT SUM(contract_value_inr) FROM dim_project), 1) AS share_pct,
       ROUND(AVG(contract_value_inr) / 1e7, 1)                               AS avg_cr,
       ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY contract_value_inr) / 1e7)::numeric, 1) AS median_cr
FROM dim_project
GROUP BY industry
ORDER BY contract_value_cr DESC;
-- The scalar subquery in share_pct runs once and returns the grand total.

-- Q1.3 Order intake by fiscal year of award
-- JOIN to dim_date turns a calendar date into the Indian fiscal year (Apr-Mar).
SELECT d.fiscal_year,
       COUNT(*)                                AS projects_awarded,
       ROUND(SUM(p.contract_value_inr) / 1e7)  AS order_intake_cr
FROM dim_project p
JOIN dim_date d ON d.date = p.award_date
GROUP BY d.fiscal_year
ORDER BY d.fiscal_year;

-- Q1.4 The ten largest contracts, with client and project manager names
-- INNER JOINs: every project has exactly one client and one PM, so no rows are lost.
SELECT p.project_id, p.project_name, c.client_name, e.employee_name AS project_manager,
       ROUND(p.contract_value_inr / 1e7, 1) AS contract_cr, p.status
FROM dim_project p
JOIN dim_client c   ON c.client_id = p.client_id
JOIN dim_employee e ON e.employee_id = p.project_manager_id
ORDER BY p.contract_value_inr DESC
LIMIT 10;

-- Q1.5 Repeat clients: clients with more than one project
-- HAVING filters groups after aggregation; WHERE could not, because COUNT(*) does not exist yet.
SELECT c.client_name, c.industry, COUNT(*) AS projects,
       ROUND(SUM(p.contract_value_inr) / 1e7, 1) AS total_cr
FROM dim_project p
JOIN dim_client c ON c.client_id = p.client_id
GROUP BY c.client_name, c.industry
HAVING COUNT(*) > 1
ORDER BY projects DESC, total_cr DESC;

-- Q1.6 Large in-progress projects starting in FY25 or later (WHERE with several conditions)
SELECT project_id, project_name, industry, planned_start_date,
       ROUND(contract_value_inr / 1e7, 1) AS contract_cr, percent_complete
FROM dim_project
WHERE status = 'In Progress'
  AND planned_start_date >= DATE '2024-04-01'
  AND contract_value_inr >= 100 * 1e7
ORDER BY planned_start_date;

-- Q1.7 Planned project duration by size band (CASE builds the bands, EXTRACT reads date parts)
SELECT CASE WHEN contract_value_inr < 50e7  THEN '1. < Rs 50 Cr'
            WHEN contract_value_inr < 150e7 THEN '2. Rs 50-150 Cr'
            ELSE '3. > Rs 150 Cr' END                          AS size_band,
       COUNT(*)                                                AS projects,
       ROUND(AVG(planned_duration_days) / 30.44, 1)            AS avg_planned_months,
       MIN(EXTRACT(YEAR FROM planned_start_date))::int         AS first_start_year
FROM dim_project
GROUP BY 1
ORDER BY 1;
