-- =====================================================================================
-- ProjectCo industrial project analytics: PostgreSQL star schema
-- Fictional company, synthetic data. Compatible with PostgreSQL 13+.
--
-- Design (docs/DATA_MODEL.md):
--   * Dimension tables describe things  (who / what / where / when).
--   * Fact tables record events and measurements, each at one declared grain.
--   * Every fact references dimensions through foreign keys, so no descriptive text is
--     repeated on fact rows and every number can be sliced by any dimension.
-- Money is NUMERIC(18,2) in full rupees (C01). Dates are DATE and relate to dim_date(date).
-- =====================================================================================

DROP SCHEMA IF EXISTS projectco CASCADE;
CREATE SCHEMA projectco;
SET search_path TO projectco;

-- -------------------------------------------------------------------------------------
-- DIMENSIONS
-- -------------------------------------------------------------------------------------

-- One row per calendar day, Oct 2020 - Dec 2027. Indian fiscal year runs April-March (C02).
CREATE TABLE dim_date (
    date              DATE PRIMARY KEY,
    date_key          INTEGER NOT NULL UNIQUE,          -- YYYYMMDD
    year              SMALLINT NOT NULL,
    quarter           CHAR(2) NOT NULL,
    month_num         SMALLINT NOT NULL CHECK (month_num BETWEEN 1 AND 12),
    month_name        VARCHAR(10) NOT NULL,
    month_short       CHAR(3) NOT NULL,
    year_month        CHAR(7) NOT NULL,                 -- e.g. 2024-05
    month_start       DATE NOT NULL,
    fiscal_year_num   SMALLINT NOT NULL,                -- FY ending March of this year
    fiscal_year       CHAR(4) NOT NULL,                 -- e.g. FY25
    fiscal_month_num  SMALLINT NOT NULL CHECK (fiscal_month_num BETWEEN 1 AND 12),  -- April = 1
    fiscal_quarter    CHAR(2) NOT NULL,
    day_of_week       CHAR(3) NOT NULL,
    is_working_day    BOOLEAN NOT NULL                  -- 6-day week, national holidays closed (F02)
);

CREATE TABLE dim_location (
    location_id    VARCHAR(10) PRIMARY KEY,
    location_name  VARCHAR(60) NOT NULL,
    location_type  VARCHAR(20) NOT NULL CHECK (location_type IN ('Works', 'Project Site')),
    city           VARCHAR(40) NOT NULL,
    state          VARCHAR(40) NOT NULL,
    region         VARCHAR(10) NOT NULL
);

CREATE TABLE dim_client (
    client_id          VARCHAR(10) PRIMARY KEY,
    client_name        VARCHAR(80) NOT NULL,
    industry           VARCHAR(40) NOT NULL,
    hq_state           VARCHAR(40) NOT NULL,
    client_since_year  SMALLINT NOT NULL
);

CREATE TABLE dim_employee (
    employee_id       VARCHAR(10) PRIMARY KEY,
    employee_name     VARCHAR(60) NOT NULL,
    role              VARCHAR(30) NOT NULL,
    department        VARCHAR(30) NOT NULL,
    base_location_id  VARCHAR(10) NOT NULL REFERENCES dim_location (location_id),
    join_year         SMALLINT NOT NULL,
    hourly_cost_inr   NUMERIC(10,2) NOT NULL CHECK (hourly_cost_inr > 0)
);

CREATE TABLE dim_supplier (
    supplier_id       VARCHAR(10) PRIMARY KEY,
    supplier_name     VARCHAR(80) NOT NULL UNIQUE,
    material_group    VARCHAR(40) NOT NULL,
    supplier_state    VARCHAR(40) NOT NULL,
    established_year  SMALLINT NOT NULL
);

CREATE TABLE dim_material (
    material_id              VARCHAR(10) PRIMARY KEY,
    material_name            VARCHAR(80) NOT NULL,
    material_group           VARCHAR(40) NOT NULL,
    unit_of_measure          VARCHAR(5) NOT NULL,
    criticality_class        CHAR(1) NOT NULL CHECK (criticality_class IN ('A', 'B', 'C')),
    is_steel_linked          BOOLEAN NOT NULL,
    standard_lead_time_days  SMALLINT NOT NULL CHECK (standard_lead_time_days > 0),
    standard_price_inr       NUMERIC(14,2) NOT NULL CHECK (standard_price_inr > 0)
);

CREATE TABLE dim_work_centre (
    work_centre_id               VARCHAR(12) PRIMARY KEY,
    work_centre_name             VARCHAR(60) NOT NULL,
    works_location_id            VARCHAR(10) NOT NULL REFERENCES dim_location (location_id),
    process_type                 VARCHAR(30) NOT NULL,
    std_mh_per_tonne             NUMERIC(6,2) NOT NULL,   -- standard man-hours per tonne (F04)
    std_machine_hours_per_tonne  NUMERIC(6,3) NOT NULL,
    is_final_operation           BOOLEAN NOT NULL
);

CREATE TABLE dim_equipment (
    equipment_id           VARCHAR(12) PRIMARY KEY,
    equipment_name         VARCHAR(60) NOT NULL,
    equipment_type         VARCHAR(40) NOT NULL,
    work_centre_id         VARCHAR(12) NOT NULL REFERENCES dim_work_centre (work_centre_id),
    works_location_id      VARCHAR(10) NOT NULL REFERENCES dim_location (location_id),
    commission_year        SMALLINT NOT NULL,
    rated_kw               NUMERIC(8,1) NOT NULL,
    machine_hour_rate_inr  NUMERIC(10,2) NOT NULL,
    rated_tonnes_per_hour  NUMERIC(6,2) NOT NULL
);

CREATE TABLE dim_cost_category (
    cost_category_id  SMALLINT PRIMARY KEY,
    cost_category     VARCHAR(20) NOT NULL UNIQUE,
    sort_order        SMALLINT NOT NULL,
    cost_behaviour    VARCHAR(12) NOT NULL,             -- Variable / Time-based / Mixed (E01, E02)
    gl_account        VARCHAR(10) NOT NULL UNIQUE
);

CREATE TABLE dim_stage (
    stage_id       SMALLINT PRIMARY KEY,
    stage_name     VARCHAR(20) NOT NULL UNIQUE,
    stage_order    SMALLINT NOT NULL,
    billing_share  NUMERIC(4,2) NOT NULL,               -- milestone billing % of contract value
    description    VARCHAR(120) NOT NULL
);

CREATE TABLE dim_project (
    project_id                  VARCHAR(10) PRIMARY KEY,
    project_name                VARCHAR(100) NOT NULL,
    client_id                   VARCHAR(10) NOT NULL REFERENCES dim_client (client_id),
    industry                    VARCHAR(40) NOT NULL,
    site_location_id            VARCHAR(10) NOT NULL REFERENCES dim_location (location_id),
    works_location_id           VARCHAR(10) NOT NULL REFERENCES dim_location (location_id),
    project_manager_id          VARCHAR(10) NOT NULL REFERENCES dim_employee (employee_id),
    contract_type               VARCHAR(30) NOT NULL,
    has_price_variation_clause  BOOLEAN NOT NULL,
    contract_value_inr          NUMERIC(18,2) NOT NULL CHECK (contract_value_inr > 0),
    award_date                  DATE NOT NULL,
    planned_start_date          DATE NOT NULL,
    planned_end_date            DATE NOT NULL,          -- contractual completion date (D05)
    actual_start_date           DATE NOT NULL,
    actual_end_date             DATE,                   -- NULL while the project is in progress
    status                      VARCHAR(12) NOT NULL CHECK (status IN ('Completed', 'In Progress')),
    percent_complete            NUMERIC(5,1) NOT NULL CHECK (percent_complete BETWEEN 0 AND 100),
    planned_fab_tonnes          NUMERIC(10,1) NOT NULL,
    planned_duration_days       INTEGER NOT NULL,
    CHECK (planned_end_date > planned_start_date),
    CHECK ((status = 'Completed') = (actual_end_date IS NOT NULL))
);

-- -------------------------------------------------------------------------------------
-- FACTS
-- -------------------------------------------------------------------------------------

-- Grain: one row per project per cost category. The bid estimate and the revised budget.
CREATE TABLE fact_budget (
    project_id               VARCHAR(10) NOT NULL REFERENCES dim_project (project_id),
    cost_category_id         SMALLINT NOT NULL REFERENCES dim_cost_category (cost_category_id),
    original_budget_inr      NUMERIC(18,2) NOT NULL,
    change_order_budget_inr  NUMERIC(18,2) NOT NULL,
    revised_budget_inr       NUMERIC(18,2) NOT NULL,
    PRIMARY KEY (project_id, cost_category_id),
    CHECK (revised_budget_inr = original_budget_inr + change_order_budget_inr)
);

-- Grain: one ledger posting = project x cost category x month x source system.
CREATE TABLE fact_project_cost (
    document_no       VARCHAR(12) PRIMARY KEY,
    project_id        VARCHAR(10) NOT NULL REFERENCES dim_project (project_id),
    cost_category_id  SMALLINT NOT NULL REFERENCES dim_cost_category (cost_category_id),
    gl_account        VARCHAR(10) NOT NULL,
    posting_date      DATE NOT NULL REFERENCES dim_date (date),     -- month-end
    source_system     VARCHAR(12) NOT NULL CHECK (source_system IN ('Procurement', 'Production', 'Timesheet', 'Finance')),
    amount_inr        NUMERIC(18,2) NOT NULL
);

-- Grain: one purchase-order line. Carries every procurement process timestamp (G05).
CREATE TABLE fact_procurement (
    po_line_id                VARCHAR(12) PRIMARY KEY,
    po_number                 VARCHAR(14) NOT NULL,
    project_id                VARCHAR(10) NOT NULL REFERENCES dim_project (project_id),
    supplier_id               VARCHAR(10) NOT NULL REFERENCES dim_supplier (supplier_id),
    material_id               VARCHAR(10) NOT NULL REFERENCES dim_material (material_id),
    buyer_id                  VARCHAR(10) NOT NULL REFERENCES dim_employee (employee_id),
    pr_date                   DATE NOT NULL,
    pr_approval_date          DATE NOT NULL,
    rfq_date                  DATE NOT NULL,
    po_date                   DATE NOT NULL REFERENCES dim_date (date),
    supplier_confirm_date     DATE,
    promised_date             DATE,
    delivery_date             DATE,
    inspection_date           DATE,
    grn_date                  DATE,
    need_by_date              DATE NOT NULL,
    quantity                  NUMERIC(14,2) NOT NULL CHECK (quantity > 0),
    unit_price_inr            NUMERIC(14,2) NOT NULL CHECK (unit_price_inr > 0),
    line_value_inr            NUMERIC(18,2) NOT NULL CHECK (line_value_inr > 0),
    benchmark_unit_price_inr  NUMERIC(14,2) NOT NULL,   -- market price at PO date (standard x steel index)
    qty_rejected              NUMERIC(14,2) NOT NULL DEFAULT 0,
    line_status               VARCHAR(10) NOT NULL CHECK (line_status IN ('Received', 'Open')),
    lead_time_days            INTEGER,                  -- PO date -> goods receipt (G04)
    delivery_delay_days       INTEGER,                  -- delivery - promised; > 0 means late
    is_on_time                BOOLEAN,                  -- delivered on or before promised date (G03)
    delivery_date_imputed     BOOLEAN NOT NULL,
    CHECK (pr_date <= pr_approval_date AND pr_approval_date <= po_date)
);

-- Grain: one works x production day x project (daily fabrication record).
CREATE TABLE fact_operations (
    production_id              VARCHAR(12) PRIMARY KEY,
    works_location_id          VARCHAR(10) NOT NULL REFERENCES dim_location (location_id),
    production_date            DATE NOT NULL REFERENCES dim_date (date),
    project_id                 VARCHAR(10) NOT NULL REFERENCES dim_project (project_id),
    overtime_shift             BOOLEAN NOT NULL,
    planned_output_t           NUMERIC(10,3) NOT NULL,
    actual_output_t            NUMERIC(10,3) NOT NULL CHECK (actual_output_t >= 0),
    rework_t                   NUMERIC(10,3) NOT NULL CHECK (rework_t >= 0),
    regular_labour_hours       NUMERIC(10,1) NOT NULL,
    overtime_labour_hours      NUMERIC(10,1) NOT NULL,
    labour_cost_inr            NUMERIC(14,2) NOT NULL,
    machine_hours              NUMERIC(10,2) NOT NULL,
    machine_cost_inr           NUMERIC(14,2) NOT NULL,
    energy_kwh                 NUMERIC(12,1) NOT NULL,
    energy_cost_inr            NUMERIC(14,2) NOT NULL,
    bottleneck_work_centre_id  VARCHAR(12) NOT NULL REFERENCES dim_work_centre (work_centre_id),
    capacity_constrained       BOOLEAN NOT NULL,        -- demand exceeded the bottleneck's capacity that day
    labour_hours_imputed       BOOLEAN NOT NULL,
    UNIQUE (works_location_id, production_date, project_id)
);

-- Grain: one machine x working day.
CREATE TABLE fact_equipment (
    machine_log_id             VARCHAR(10) PRIMARY KEY,
    log_date                   DATE NOT NULL REFERENCES dim_date (date),
    equipment_id               VARCHAR(12) NOT NULL REFERENCES dim_equipment (equipment_id),
    scheduled_hours            NUMERIC(5,2) NOT NULL,
    planned_maintenance_hours  NUMERIC(5,2) NOT NULL,
    available_hours            NUMERIC(5,2) NOT NULL,   -- scheduled - planned maintenance (F03)
    downtime_hours             NUMERIC(5,2) NOT NULL CHECK (downtime_hours >= 0),
    operating_hours            NUMERIC(5,2) NOT NULL,
    idle_hours                 NUMERIC(5,2) NOT NULL,
    downtime_reason            VARCHAR(30),
    UNIQUE (equipment_id, log_date),
    CHECK (downtime_hours + operating_hours <= available_hours + 0.01)
);

-- Grain: one project x labour type x week (site erection and engineering timesheets).
CREATE TABLE fact_labor (
    labour_entry_id   VARCHAR(12) PRIMARY KEY,
    week_ending_date  DATE NOT NULL REFERENCES dim_date (date),
    project_id        VARCHAR(10) NOT NULL REFERENCES dim_project (project_id),
    labour_type       VARCHAR(15) NOT NULL CHECK (labour_type IN ('Engineering', 'Site Erection')),
    supervisor_id     VARCHAR(10) NOT NULL REFERENCES dim_employee (employee_id),
    headcount         INTEGER NOT NULL CHECK (headcount > 0),
    earned_hours      NUMERIC(10,1) NOT NULL,           -- budgeted hours for the work actually done
    regular_hours     NUMERIC(10,1) NOT NULL,
    overtime_hours    NUMERIC(10,1) NOT NULL,
    idle_hours        NUMERIC(10,1) NOT NULL,
    labour_cost_inr   NUMERIC(14,2) NOT NULL
);

-- Grain: one project x lifecycle stage.
CREATE TABLE fact_milestones (
    project_id             VARCHAR(10) NOT NULL REFERENCES dim_project (project_id),
    stage_id               SMALLINT NOT NULL REFERENCES dim_stage (stage_id),
    planned_start_date     DATE NOT NULL,
    planned_end_date       DATE NOT NULL,
    actual_start_date      DATE,
    actual_end_date        DATE,
    milestone_status       VARCHAR(12) NOT NULL CHECK (milestone_status IN ('Completed', 'In Progress', 'Not Started')),
    delay_cause            VARCHAR(30),
    planned_duration_days  INTEGER NOT NULL,
    actual_duration_days   INTEGER,
    start_delay_days       INTEGER,
    end_delay_days         INTEGER,
    PRIMARY KEY (project_id, stage_id),
    CHECK (actual_end_date IS NULL OR actual_end_date >= actual_start_date)
);

-- Grain: one invoice or revenue adjustment.
CREATE TABLE fact_revenue (
    invoice_no    VARCHAR(10) PRIMARY KEY,
    project_id    VARCHAR(10) NOT NULL REFERENCES dim_project (project_id),
    invoice_date  DATE NOT NULL REFERENCES dim_date (date),
    revenue_type  VARCHAR(20) NOT NULL CHECK (revenue_type IN ('Milestone Billing', 'Change Order', 'Price Variation', 'Liquidated Damages')),
    stage_id      SMALLINT REFERENCES dim_stage (stage_id),
    amount_inr    NUMERIC(18,2) NOT NULL                -- LD rows are negative
);

-- Reference: synthetic monthly steel price index, base 100 = April 2021 (C11)
CREATE TABLE ref_steel_price_index (
    month_start        DATE PRIMARY KEY,
    steel_price_index  NUMERIC(6,2) NOT NULL
);

-- Indexes on the foreign keys most used for joins and filters
CREATE INDEX ix_cost_project      ON fact_project_cost (project_id, cost_category_id);
CREATE INDEX ix_proc_project      ON fact_procurement (project_id);
CREATE INDEX ix_proc_supplier     ON fact_procurement (supplier_id);
CREATE INDEX ix_ops_project_date  ON fact_operations (project_id, production_date);
CREATE INDEX ix_equip_date        ON fact_equipment (log_date);
CREATE INDEX ix_labor_project     ON fact_labor (project_id);
CREATE INDEX ix_revenue_project   ON fact_revenue (project_id);
