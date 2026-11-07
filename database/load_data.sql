-- Load the processed CSVs into the projectco schema.
-- Run from the project root (paths are relative):  psql -d projectco_analytics -f database/load_data.sql
-- \copy runs client-side, so no server file permissions are needed.
SET search_path TO projectco;

\copy dim_date              FROM 'data/processed/dim_date.csv'              WITH (FORMAT csv, HEADER true)
\copy dim_location          FROM 'data/processed/dim_location.csv'          WITH (FORMAT csv, HEADER true)
\copy dim_client            FROM 'data/processed/dim_client.csv'            WITH (FORMAT csv, HEADER true)
\copy dim_employee          FROM 'data/processed/dim_employee.csv'          WITH (FORMAT csv, HEADER true)
\copy dim_supplier          FROM 'data/processed/dim_supplier.csv'          WITH (FORMAT csv, HEADER true)
\copy dim_material          FROM 'data/processed/dim_material.csv'          WITH (FORMAT csv, HEADER true)
\copy dim_work_centre       FROM 'data/processed/dim_work_centre.csv'       WITH (FORMAT csv, HEADER true)
\copy dim_equipment         FROM 'data/processed/dim_equipment.csv'         WITH (FORMAT csv, HEADER true)
\copy dim_cost_category     FROM 'data/processed/dim_cost_category.csv'     WITH (FORMAT csv, HEADER true)
\copy dim_stage             FROM 'data/processed/dim_stage.csv'             WITH (FORMAT csv, HEADER true)
\copy dim_project           FROM 'data/processed/dim_project.csv'           WITH (FORMAT csv, HEADER true)
\copy fact_budget           FROM 'data/processed/fact_budget.csv'           WITH (FORMAT csv, HEADER true)
\copy fact_project_cost     FROM 'data/processed/fact_project_cost.csv'     WITH (FORMAT csv, HEADER true)
\copy fact_procurement      FROM 'data/processed/fact_procurement.csv'      WITH (FORMAT csv, HEADER true)
\copy fact_operations       FROM 'data/processed/fact_operations.csv'       WITH (FORMAT csv, HEADER true)
\copy fact_equipment        FROM 'data/processed/fact_equipment.csv'        WITH (FORMAT csv, HEADER true)
\copy fact_labor            FROM 'data/processed/fact_labor.csv'            WITH (FORMAT csv, HEADER true)
\copy fact_milestones       FROM 'data/processed/fact_milestones.csv'       WITH (FORMAT csv, HEADER true)
\copy fact_revenue          FROM 'data/processed/fact_revenue.csv'          WITH (FORMAT csv, HEADER true)
\copy ref_steel_price_index FROM 'data/processed/ref_steel_price_index.csv' WITH (FORMAT csv, HEADER true)

ANALYZE;

SELECT 'dim_project' AS table_name, COUNT(*) AS rows FROM dim_project
UNION ALL SELECT 'fact_project_cost', COUNT(*) FROM fact_project_cost
UNION ALL SELECT 'fact_procurement', COUNT(*) FROM fact_procurement
UNION ALL SELECT 'fact_operations', COUNT(*) FROM fact_operations
UNION ALL SELECT 'fact_equipment', COUNT(*) FROM fact_equipment
UNION ALL SELECT 'fact_labor', COUNT(*) FROM fact_labor
UNION ALL SELECT 'fact_milestones', COUNT(*) FROM fact_milestones
UNION ALL SELECT 'fact_revenue', COUNT(*) FROM fact_revenue;
