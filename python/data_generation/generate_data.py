"""Generate the synthetic ProjectCo dataset.

Run from the project root:
    python python/data_generation/generate_data.py

This is a small simulation, not a random-number dump. Each project is pushed through
its lifecycle and the causes below create the effects the analysis later has to find:

    engineering rework  -> late purchase requests and extra steel quantity
    cheap-but-late supplier -> late steel / critical items -> fabrication or installation waits
    machine downtime    -> lower works throughput -> longer fabrication, idle labour, overtime
    tight bid margin    -> procurement buys from the lowest bidder more often
    delay               -> time-based overhead, crane hire and subcontractor claims rise, LD deducted
    steel price spike   -> material overrun, partly recovered on contracts with a price-variation clause

Outputs:
    data/qa/truth/*.csv          clean "true" tables (used only to measure cleaning accuracy)
    data/qa/hidden_drivers.csv   the planted causes (never used by the analysis)
    data/raw/*.csv               source-system extracts with injected data-quality issues
"""
import datetime as dt
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as C  # noqa: E402
from data_generation import reference_data as R  # noqa: E402
from data_generation.inject_quality_issues import write_raw_extracts  # noqa: E402

rng = np.random.default_rng(C.SEED)
DAY = dt.timedelta(days=1)
# Split of the labour budget: works fabrication / site erection / engineering
WORKS_LABOUR_SHARE, SITE_LABOUR_SHARE, ENG_LABOUR_SHARE = 0.35, 0.45, 0.20
# Planners know Works-East loses more time to breakdowns, so they load it a little less
EFFECTIVE_CAPACITY = {"LOC-W1": 1.0, "LOC-W2": 0.85, "LOC-W3": 0.95}
LD_GRACE_DAYS = 14   # C08: minor contractor delays inside the grace period attract no LD

# --------------------------------------------------------------------------------------
# Calendar helpers (F02: 6-day week, Sunday off, national holidays closed)
# --------------------------------------------------------------------------------------
WEEKMASK = "1111110"
HOLIDAYS = np.array(sorted(R.HOLIDAYS), dtype="datetime64[D]")
WORKDAYS = [d.date() for d in pd.date_range(C.DATA_START, C.CUTOFF)
            if d.weekday() != 6 and d.date() not in R.HOLIDAYS]


def wd_between(a, b):
    """Working days in [a, b)."""
    return int(np.busday_count(np.datetime64(a), np.datetime64(b), weekmask=WEEKMASK, holidays=HOLIDAYS))


def add_wd(a, n):
    return np.busday_offset(np.datetime64(a), int(round(n)), roll="forward",
                            weekmask=WEEKMASK, holidays=HOLIDAYS).astype(dt.date)


def month_end(d):
    nxt = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return nxt - DAY


def steel_index(d):
    """Synthetic monthly steel price index (C11). Base 100 = Apr 2021. Not real market data."""
    m = (d.year - 2021) * 12 + (d.month - 4)
    if m < 0:
        v = 100 + 1.2 * m
    elif m <= 14:
        v = 100 + 30 * m / 14
    elif m <= 32:
        v = 130 - 20 * (m - 14) / 18
    else:
        v = 110 - 2 * (m - 32) / 27
    return round(v + 1.8 * math.sin(m / 2.3), 2)


def energy_tariff(d):
    """Rs per kWh (E05), rising about 3% a year."""
    return 7.6 * 1.03 ** ((d - C.DATA_START).days / 365)


def spread(amount, start, end):
    """Split an amount across month-ends in proportion to calendar days between start and end."""
    end = max(end, start)
    days = pd.date_range(start, end)
    counts = pd.Series(1, index=days).groupby(days.to_period("M")).sum()
    out, running = {}, 0.0
    for i, (period, n) in enumerate(counts.items()):
        me = period.to_timestamp(how="end").date()
        value = round(amount * n / len(days), 2) if i < len(counts) - 1 else round(amount - running, 2)
        running += value
        out[me] = out.get(me, 0) + value
    return out


# --------------------------------------------------------------------------------------
# Master data
# --------------------------------------------------------------------------------------
def build_locations():
    rows = [(w[0], w[1], "Works", w[2], w[3], w[4]) for w in R.WORKS]
    for i, (city, (state, region)) in enumerate(R.SITES.items(), 1):
        rows.append((f"LOC-S{i:02d}", f"Site - {city}", "Project Site", city, state, region))
    return pd.DataFrame(rows, columns=["location_id", "location_name", "location_type", "city", "state", "region"])


def build_clients():
    rows, k = [], 0
    for ind, spec in R.INDUSTRIES.items():
        for _ in range(max(2, round(spec["n"] / 2.2))):
            k += 1
            city = rng.choice(spec["sites"])
            rows.append((f"CL-{k:03d}", f"{R.CLIENT_PREFIXES[k - 1]} {R.CLIENT_SUFFIX[ind]}", ind,
                         R.SITES[city][0], int(rng.integers(2008, 2021))))
    return pd.DataFrame(rows, columns=["client_id", "client_name", "industry", "hq_state", "client_since_year"])


def build_employees():
    roles = [("Project Manager", 12, "Projects", 2200), ("Planning Engineer", 10, "Projects", 1300),
             ("Design Engineer", 20, "Engineering", 1250), ("Site Supervisor", 24, "Construction", 900),
             ("Works Supervisor", 12, "Manufacturing", 850), ("Procurement Buyer", 6, "Supply Chain", 1000)]
    rows, k, pm_skill = [], 0, {}
    used = set()
    for role, n, dept, cost in roles:
        for j in range(n):
            k += 1
            while True:
                name = f"{rng.choice(R.FIRST_NAMES)} {rng.choice(R.LAST_NAMES)}"
                if name not in used:
                    used.add(name)
                    break
            emp_id = f"EMP-{k:03d}"
            if role == "Works Supervisor":
                base = R.WORKS[j % 3][0]
            else:
                base = R.WORKS[int(rng.integers(0, 3))][0]
            if role == "Project Manager":
                skill = float(rng.normal(0, 1))
                pm_skill[emp_id] = skill
                join = int(np.clip(round(2016 - 3 * skill + rng.normal(0, 2)), 2004, 2021))
            else:
                join = int(rng.integers(2008, 2023))
            hourly = round(cost * rng.uniform(0.9, 1.15), 0)
            rows.append((emp_id, name, role, dept, base, join, hourly))
    cols = ["employee_id", "employee_name", "role", "department", "base_location_id", "join_year", "hourly_cost_inr"]
    return pd.DataFrame(rows, columns=cols), pm_skill


def build_suppliers():
    rows, hidden, k = [], {}, 0
    for group, spec in R.MATERIAL_GROUPS.items():
        for arch in spec["archetypes"]:
            k += 1
            a = R.ARCHETYPES[arch]
            suffix = rng.choice(["Pvt Ltd", "Pvt Ltd", "Ltd", "Industries Pvt Ltd"])
            name = f"{R.SUPPLIER_PREFIXES[k - 1]} {R.GROUP_SUPPLIER_WORD[group]} {suffix}"
            sid = f"SUP-{k:03d}"
            rows.append((sid, name, group, rng.choice(R.SUPPLIER_STATES), int(rng.integers(1995, 2019))))
            hidden[sid] = dict(archetype=arch, group=group, price_factor=rng.uniform(*a["price"]), **a)
    cols = ["supplier_id", "supplier_name", "material_group", "supplier_state", "established_year"]
    return pd.DataFrame(rows, columns=cols), hidden


def build_materials():
    rows = []
    for k, (name, group, unit, price) in enumerate(R.MATERIALS, 1):
        g = R.MATERIAL_GROUPS[group]
        rows.append((f"MAT-{k:03d}", name, group, unit, g["crit"], g["steel"],
                     int(rng.integers(g["lead"][0], g["lead"][1] + 1)), float(price)))
    cols = ["material_id", "material_name", "material_group", "unit_of_measure", "criticality_class",
            "is_steel_linked", "standard_lead_time_days", "standard_price_inr"]
    return pd.DataFrame(rows, columns=cols)


def build_works():
    wc_rows, eq_rows, machines = [], [], []
    commission = {"good": (2013, 2020), "average": (2008, 2016), "poor": (2003, 2010), "chronic": (1998, 2006)}
    for w_index, works in enumerate(R.WORKS, 1):
        loc = works[0]
        for wc_type, mname, n, rate, mhr, kw, mh, crew in R.WORK_CENTRE_TYPES:
            code = "".join(word[0] for word in wc_type.replace("&", "").split())[:3].upper()
            wc_id = f"WC-W{w_index}-{code}"
            wc_rows.append((wc_id, f"{wc_type} - {works[1]}", loc, wc_type, mh, round(1 / rate, 3),
                            wc_type == "Blasting & Painting"))
            for i in range(n):
                cls = R.WORKS_RELIABILITY[loc][wc_type][i]
                p_break, mean_down = R.RELIABILITY[cls]
                eq_id = f"EQ-W{w_index}-{code}{i + 1}"
                year = int(rng.integers(*commission[cls]))
                eq_rows.append((eq_id, f"{mname} #{i + 1}", mname, wc_id, loc, year, kw, mhr, rate))
                machines.append(dict(equipment_id=eq_id, works=loc, wc_id=wc_id, wc_type=wc_type, rate=rate,
                                     mhr=mhr, kw=kw, crew=crew, mh=mh, p_break=p_break, mean_down=mean_down,
                                     pm_offset=int(rng.integers(0, 24)), reliability=cls))
    wc = pd.DataFrame(wc_rows, columns=["work_centre_id", "work_centre_name", "works_location_id", "process_type",
                                        "std_mh_per_tonne", "std_machine_hours_per_tonne", "is_final_operation"])
    eq = pd.DataFrame(eq_rows, columns=["equipment_id", "equipment_name", "equipment_type", "work_centre_id",
                                        "works_location_id", "commission_year", "rated_kw",
                                        "machine_hour_rate_inr", "rated_tonnes_per_hour"])
    return wc, eq, machines


def _scope_name(template):
    ranges = {"TCD": (2500, 10000, 500), "TPD Clinker": (3000, 10000, 500), "TPH Overland": (800, 4000, 200),
              "TPH Boiler": (60, 250, 10), "MW": (5, 100, 5), "MLD": (5, 60, 5), "KLPD": (60, 300, 20),
              "TPD CO2": (50, 500, 50)}
    for key, (lo, hi, step) in ranges.items():
        if "{n} " + key in template:
            return template.format(n=f"{int(rng.integers(lo // step, hi // step + 1)) * step:,}")
    return template


def assign_works(load_book, home, start, dur, cost):
    """Planning rule: send fabrication to the works with the least committed load over the
    project's planned fabrication window, preferring the home-region works (cheaper freight)."""
    fs, fe = start + dt.timedelta(days=round(0.30 * dur)), start + dt.timedelta(days=round(0.75 * dur))
    daily = cost * 0.11 * WORKS_LABOUR_SHARE / (380 * C.WORKS_STD_MH_PER_TONNE) / max(1, (fe - fs).days * 6 / 7)
    scores = {}
    for w, book in load_book.items():
        load = sum(r * max(0, (min(fe, e) - max(fs, s)).days) for s, e, r in book) / max(1, (fe - fs).days)
        scores[w] = load / EFFECTIVE_CAPACITY[w] - (8 if w == home else 0)
    best = min(scores, key=scores.get)
    load_book[best].append((fs, fe, daily))
    return best


def build_projects(clients, employees, pm_skill, locations):
    site_loc = dict(zip(locations.city, locations.location_id))
    pm_ids = employees.loc[employees.role == "Project Manager", "employee_id"].tolist()
    senior_pms = (employees[employees.role == "Project Manager"].sort_values("join_year").employee_id.tolist())[:6]
    industries = [ind for ind, s in R.INDUSTRIES.items() for _ in range(s["n"])]
    rng.shuffle(industries)
    drafts = []
    for ind in industries:
        s = R.INDUSTRIES[ind]
        lo = dt.date(2022, 10, 1) if ind in R.NEW_ENERGY else dt.date(2021, 4, 1)
        start = lo + dt.timedelta(days=int(rng.integers(0, (dt.date(2025, 9, 30) - lo).days)))
        drafts.append((start, ind))
    drafts.sort()

    projects, budget_rows, load_book = [], [], {w[0]: [] for w in R.WORKS}
    for i, (start, ind) in enumerate(drafts, 1):
        s = R.INDUSTRIES[ind]
        value_cr = round(float(np.clip(rng.lognormal(np.log(70 * s["value_mult"]), 0.6), 15, 450)), 2)
        cv = value_cr * C.CRORE
        dur = int(round(np.clip(9 + 4.5 * np.log(value_cr / 15) + 3 * s["foak"] + rng.normal(0, 1.5), 10, 36) * 30.44))
        m_lo, m_hi = s["margin"]
        margin = rng.uniform(m_lo, m_hi)
        city = rng.choice(s["sites"])
        state, region = R.SITES[city]
        big = value_cr > 150 or s["foak"] >= 0.7
        pm = rng.choice(senior_pms) if (big and rng.random() < 0.75) else rng.choice(pm_ids)
        client = rng.choice(clients.loc[clients.industry == ind, "client_id"].tolist())
        name = f"{clients.set_index('client_id').at[client, 'client_name'].split()[0]} - " \
               f"{_scope_name(rng.choice(s['scopes']))}"
        co_frac = rng.uniform(0.02, 0.08) if rng.random() < 0.40 else 0.0
        pid = f"PRJ-{i:03d}"
        works = assign_works(load_book, R.REGION_TO_WORKS[region], start, dur, cv * (1 - margin) * (1 + co_frac))

        # Bid budget by cost category (E01), then revised budget with change orders (C06, C07)
        mix = np.array([c[2] * s["mix_adjust"].get(c[1], 1.0) for c in R.COST_CATEGORIES])
        mix = mix * rng.lognormal(0, 0.06, len(mix))
        mix /= mix.sum()
        original = np.round(cv * (1 - margin) * mix, -3)
        budget = {}
        for (cid, cname, *_), orig in zip(R.COST_CATEGORIES, original):
            co_budget = round(orig * co_frac, -3)
            budget[cname] = orig + co_budget
            budget_rows.append((pid, cid, orig, co_budget, orig + co_budget))

        projects.append(dict(
            project_id=pid, project_name=name, client_id=client, industry=ind, site_location_id=site_loc[city],
            region=region, works=works, pm=pm, pm_skill=pm_skill[pm], foak=s["foak"],
            contract_value=cv, value_cr=value_cr, bid_margin=1 - original.sum() / cv,
            price_pressure=margin < m_lo + 0.4 * (m_hi - m_lo), pvc=rng.random() < 0.35, co_frac=co_frac,
            planned_start=start, planned_duration=dur, contractual_end=start + dt.timedelta(days=dur),
            award_date=start - dt.timedelta(days=int(rng.integers(30, 91))), budget=budget,
        ))
    budgets = pd.DataFrame(budget_rows, columns=["project_id", "cost_category_id", "original_budget_inr",
                                                 "change_order_budget_inr", "revised_budget_inr"])
    return projects, budgets


def planned_stages(p):
    return {sid: (p["planned_start"] + dt.timedelta(days=round(s0 * p["planned_duration"])),
                  p["planned_start"] + dt.timedelta(days=round(s1 * p["planned_duration"])))
            for sid, _, s0, s1, *_ in R.STAGES}


# --------------------------------------------------------------------------------------
# Engineering and procurement
# --------------------------------------------------------------------------------------
def simulate_engineering(p):
    p["plan"] = planned_stages(p)
    p["kickoff_delay"] = 0 if rng.random() < 0.2 else int(np.clip(rng.gamma(1.2, 4), 0, 25))
    p["shift"] = dt.timedelta(days=p["kickoff_delay"])
    p["actual_start"] = p["planned_start"] + p["shift"]
    scale = p["planned_duration"] / 480
    p["eng_slip"] = int(max(0, rng.normal(6 + 30 * p["foak"] - 7 * p["pm_skill"], 10 + 10 * p["foak"])) * scale)
    p["rework_frac"] = float(np.clip(rng.normal(0.03 + 0.10 * p["foak"] - 0.01 * p["pm_skill"], 0.03), 0, 0.25))
    # Bill-of-material estimating error: mature industries are estimated well, new technologies are not
    p["estimate_bias"] = float(rng.normal(0.0 + 0.08 * p["foak"], 0.06))
    # A minority of projects hit a design-basis change mid-engineering (more likely on new technology):
    # long engineering slip, heavy rework and scope growth all at once -> the "multiple problems" projects
    p["design_change"] = rng.random() < 0.12 + 0.3 * p["foak"]
    if p["design_change"]:
        p["eng_slip"] += int(rng.uniform(45, 110) * scale)
        p["rework_frac"] += float(rng.uniform(0.08, 0.18))
        p["estimate_bias"] += float(rng.uniform(0.04, 0.10))
    es, ee = p["plan"][2]
    p["eng_start"] = es + p["shift"]
    p["eng_end"] = ee + p["shift"] + dt.timedelta(days=p["eng_slip"])


def simulate_procurement(p, suppliers_by_group, sup_hidden, materials_by_group, buyers, line_counter):
    rev_material = p["budget"]["Material"]
    shares = {g: spec["share"] * R.GROUP_MIX_ADJUST.get(p["industry"], {}).get(g, 1.0)
              for g, spec in R.MATERIAL_GROUPS.items()}
    groups = [g for g in shares if shares[g] > 0]
    probs = np.array([shares[g] for g in groups])
    probs /= probs.sum()
    n_lines = int(np.clip(22 + 0.4 * p["value_cr"] + rng.normal(0, 5), 18, 160))
    line_groups = list(rng.choice(groups, n_lines, p=probs))
    for g in groups:                              # every material group in the mix appears at least once
        if g not in line_groups:
            line_groups.append(g)
    present_share = sum(shares[g] for g in set(line_groups))
    bid_idx = steel_index(p["award_date"].replace(day=1))
    eng_dur = (p["eng_end"] - p["eng_start"]).days
    inst_s, inst_e = p["plan"][5]
    inst_dur = (inst_e - inst_s).days
    fab_need = p["plan"][4][0] + p["shift"]
    buyer = rng.choice(buyers)
    lines = []
    for g in sorted(set(line_groups)):          # sorted: set order changes between Python runs
        idx = [k for k, x in enumerate(line_groups) if x == g]
        weights = rng.lognormal(0, 0.5, len(idx))
        group_budget = rev_material * shares[g] / present_share
        spec = R.MATERIAL_GROUPS[g]
        for w in weights:
            budget_line = group_budget * w / weights.sum()
            mats = materials_by_group[g]
            affordable = [m for m in mats if m["standard_price_inr"] <= budget_line]
            mat = (affordable[int(rng.integers(0, len(affordable)))] if affordable
                   else min(mats, key=lambda m: m["standard_price_inr"]))
            bid_price = mat["standard_price_inr"] * (bid_idx / 100 if spec["steel"] else 1.0)
            qty_plan = budget_line / bid_price
            growth = p["rework_frac"] * 0.6 * rng.uniform(0, 2) if spec["steel"] else 0.0
            qty = qty_plan * max(0.5, 1 + growth + p["estimate_bias"] + rng.normal(0, 0.04))
            if mat["unit_of_measure"] == "MT":
                qty_plan, qty = max(0.5, round(qty_plan, 1)), max(0.5, round(qty, 1))
            else:
                qty_plan, qty = max(1, round(qty_plan)), max(1, round(qty))

            # Timing: when the requisition is raised and when the item is needed
            if spec["crit"] == "A":
                # Critical bought-outs (gearboxes, drives, motors) are erected mid-installation;
                # everything after them (alignment, cabling, trials) needs ~55% of installation time.
                # Their specifications freeze late in design, so requisitions come late in engineering.
                pr = p["eng_start"] + dt.timedelta(days=int(rng.uniform(0.45, 0.90) * eng_dur))
                need_by = inst_s + p["shift"] + dt.timedelta(days=int(0.45 * inst_dur))
            elif spec["steel"]:
                pr = p["eng_start"] + dt.timedelta(days=int(rng.uniform(0.15, 0.45) * eng_dur))
                need_by = fab_need
            else:
                pr = p["eng_start"] + dt.timedelta(days=int(rng.uniform(0.40, 0.90) * eng_dur + rng.uniform(0, 40)))
                need_by = inst_s + p["shift"] + dt.timedelta(days=int(rng.uniform(0.1, 0.6) * inst_dur))

            # As-Is procurement process (G05). Manual approval is slower for high-value lines.
            if budget_line < 10 * C.LAKH:
                approval = int(rng.integers(1, 5))
            elif budget_line < C.CRORE:
                approval = int(rng.integers(3, 10))
            else:
                approval = int(rng.integers(6, 19))
            if rng.random() < 0.2:
                approval += int(rng.integers(5, 16))      # approver unavailable
            approved = pr + dt.timedelta(days=approval)
            rfq = approved + dt.timedelta(days=int(rng.integers(1, 3)))
            po = rfq + dt.timedelta(days=int(rng.integers(6, 17)) + int(rng.integers(2, 8)))
            confirm = po + dt.timedelta(days=int(rng.integers(1, 7)))

            # Supplier choice: tight bids push buyers to the lowest price (B03 / G02)
            cands = suppliers_by_group[g]
            wts = []
            for sid in cands:
                h = sup_hidden[sid]
                wt = h["weight"]
                if p["price_pressure"]:
                    wt *= {"cheap_late": 2.5, "reliable": 0.5, "quality_problem": 1.3}.get(h["archetype"], 1.0)
                wts.append(wt)
            wts = np.array(wts) / sum(wts)
            sid = cands[int(rng.choice(len(cands), p=wts))]
            h = sup_hidden[sid]

            po_idx = steel_index(po.replace(day=1))
            benchmark = mat["standard_price_inr"] * (po_idx / 100 if spec["steel"] else 1.0)
            unit_price = round(benchmark * h["price_factor"] * rng.normal(1, h["noise"]), 2)

            lead = int(mat["standard_lead_time_days"] * rng.normal(1, 0.08))
            promised = confirm + dt.timedelta(days=lead)
            crunch = dt.date(2021, 4, 1) <= po <= dt.date(2022, 12, 31) and g in (
                "Structural Steel", "Steel Plates", "Castings & Forgings", "Motors")
            if rng.random() < h["p_late"] + (0.12 if crunch else 0.0):
                late = int(math.ceil(rng.gamma(*h["late"]) * (1.3 if crunch else 1.0))) + 1
            else:
                late = -int(rng.integers(0, 6)) if rng.random() < 0.5 else 0
            delivery = promised + dt.timedelta(days=late)
            inspection = delivery + dt.timedelta(days=int(rng.integers(1, 7)))
            rejected = 0.0
            grn = inspection + dt.timedelta(days=int(rng.integers(0, 4)))
            if rng.random() < h["p_reject"]:
                rejected = round(qty * rng.uniform(*h["reject"]), 1 if mat["unit_of_measure"] == "MT" else 0)
                if rejected > 0:
                    grn = inspection + dt.timedelta(days=int(rng.integers(10, 26)))   # replacement supply

            line_counter[0] += 1
            lines.append(dict(
                po_line_id=f"POL-{line_counter[0]:06d}", project_id=p["project_id"], supplier_id=sid,
                material_id=mat["material_id"], buyer_id=buyer, pr_date=pr, pr_approval_date=approved,
                rfq_date=rfq, po_date=po, supplier_confirm_date=confirm, promised_date=promised,
                delivery_date=delivery, inspection_date=inspection, grn_date=grn, need_by_date=need_by,
                quantity=qty, unit_price_inr=unit_price, line_value_inr=round(qty * unit_price, 2),
                qty_rejected=rejected, _steel=spec["steel"], _crit=spec["crit"], _qty_plan=qty_plan,
                _std=mat["standard_price_inr"], _bid_idx=bid_idx, _po_idx=po_idx,
            ))

    # PO numbers group lines raised to the same supplier in the same week
    lines.sort(key=lambda r: (r["po_date"], r["supplier_id"]))
    po_map = {}
    for r in lines:
        key = (r["supplier_id"], r["po_date"].isocalendar()[:2])
        po_map.setdefault(key, f"PO-{p['project_id'][4:]}-{len(po_map) + 1:03d}")
        r["po_number"] = po_map[key]

    steel = sorted([r for r in lines if r["_steel"]], key=lambda r: r["grn_date"])
    total = sum(r["line_value_inr"] for r in steel)
    running = 0.0
    p["steel_60_date"] = fab_need
    for r in steel:
        running += r["line_value_inr"]
        if running >= 0.6 * total:
            p["steel_60_date"] = r["grn_date"]
            break
    crit_a = [r for r in lines if r["_crit"] == "A"]
    p["last_a_grn"] = max(r["grn_date"] for r in crit_a) if crit_a else p["eng_end"]
    critical = [r for r in lines if r["_crit"] == "A" or r["_steel"]]
    p["late_crit_share"] = np.mean([r["grn_date"] > r["need_by_date"] for r in critical]) if critical else 0.0
    p["proc_start"] = min(r["pr_date"] for r in lines)
    p["proc_end"] = max(r["grn_date"] for r in lines)
    p["pvc_amount"] = sum(C.PVC_PASS_THROUGH * r["_qty_plan"] * r["_std"] * (r["_po_idx"] - r["_bid_idx"]) / 100
                          for r in lines if r["_steel"]) if p["pvc"] else 0.0
    return lines


# --------------------------------------------------------------------------------------
# Works (fabrication) simulation: day by day, shared machine capacity, downtime
# --------------------------------------------------------------------------------------
def prepare_fabrication(p):
    works = next(w for w in R.WORKS if w[0] == p["works"])
    p["works_rate"], p["works_labour_factor"], p["defect_rate"] = works[5], works[6], works[7]
    works_labour_budget = WORKS_LABOUR_SHARE * p["budget"]["Labour"]
    p["tonnes"] = works_labour_budget / (p["works_rate"] * C.WORKS_STD_MH_PER_TONNE)
    fs, fe = p["plan"][4]
    p["planned_fab_wd"] = max(20, wd_between(fs, fe))
    p["daily_rate"] = p["tonnes"] / p["planned_fab_wd"]
    p["release"] = max(fs + p["shift"] + dt.timedelta(days=int(0.6 * p["eng_slip"])), p["steel_60_date"])
    p["remaining"], p["produced"] = p["tonnes"], 0.0
    p["fab_start"] = p["fab_end"] = p["install_ready"] = None
    p["constrained_down"] = p["constrained_load"] = 0


def simulate_works(projects, machines, work_centres):
    ops, eq_log = [], []
    wc_final = dict(zip(work_centres.work_centre_id, work_centres.process_type))
    for works in [w[0] for w in R.WORKS]:
        projs = [p for p in projects if p["works"] == works]
        mach = [m for m in machines if m["works"] == works]
        wc_types = list(dict.fromkeys(m["wc_type"] for m in mach))
        wc_of_type = {m["wc_type"]: m["wc_id"] for m in mach}
        spec = {t: next(m for m in mach if m["wc_type"] == t) for t in wc_types}   # per-WC standards
        labour_rate = next(w[5] for w in R.WORKS if w[0] == works)
        for di, d in enumerate(WORKDAYS):
            active = [p for p in projs if p["release"] <= d and p["remaining"] > 0.01]
            planned_cum = {p["project_id"]: p["daily_rate"] * wd_between(p["plan"][4][0], d) for p in active}
            behind = {p["project_id"]: p["produced"] < 0.95 * planned_cum[p["project_id"]] for p in active}
            sched = 18.0 if active and any(behind.values()) else 16.0
            outage = rng.uniform(2, 5) if rng.random() < 0.012 else 0.0
            state = []
            for m in mach:
                pm = 6.0 if di % 24 == m["pm_offset"] else 0.0
                down, reason = 0.0, None
                if rng.random() < m["p_break"]:
                    down = min(float(rng.gamma(2.0, m["mean_down"] / 2)), sched - pm)
                    reason = R.DOWNTIME_REASONS[int(rng.integers(0, len(R.DOWNTIME_REASONS)))]
                if outage:
                    down = min(sched - pm, down + outage)
                    reason = reason or "Power outage"
                state.append([m, sched, pm, round(down, 2), reason, max(0.0, sched - pm - down), 0.0])

            if active:
                demand = {p["project_id"]: min(p["remaining"], p["daily_rate"] * (1.25 if behind[p["project_id"]] else 1.0))
                          for p in active}
                total_demand = sum(demand.values())
                cap = {t: sum(s[5] * s[0]["rate"] for s in state if s[0]["wc_type"] == t) for t in wc_types}
                ratio = {t: cap[t] / total_demand for t in wc_types}
                bottleneck = min(ratio, key=ratio.get)
                scale = min(1.0, ratio[bottleneck])
                down_by_type = {t: sum(s[3] for s in state if s[0]["wc_type"] == t) for t in wc_types}
                out = {pid: dem * scale for pid, dem in demand.items()}
                total_out = sum(out.values())
                for t in wc_types:                       # spread operating hours over the machines of each WC
                    rows = [s for s in state if s[0]["wc_type"] == t]
                    need = total_out / rows[0][0]["rate"]
                    avail = sum(s[5] for s in rows)
                    for s in rows:
                        s[6] = min(s[5], need * s[5] / avail) if avail > 0 else 0.0
                for p in active:
                    pid = p["project_id"]
                    o = out[pid]
                    if o <= 0:
                        continue
                    share = o / total_out
                    std_hours = sum(o * spec[t]["mh"] for t in wc_types)
                    # crews stand idle while their machine is down (60% cannot be redeployed)
                    idle_hours = sum(down_by_type[t] * spec[t]["crew"] * 0.6 for t in wc_types) * share
                    rework = o * p["defect_rate"] * float(rng.lognormal(0, 0.35))
                    labour = std_hours * p["works_labour_factor"] * rng.normal(1, 0.05) + idle_hours + rework * 12
                    ot = labour * 2 / 18 if sched == 18 else 0.0
                    reg = labour - ot
                    mh_hours = sum(o / spec[t]["rate"] for t in wc_types)
                    m_cost = sum(o / spec[t]["rate"] * spec[t]["mhr"] for t in wc_types)
                    kwh = sum(o / spec[t]["rate"] * spec[t]["kw"] * 0.65 for t in wc_types)
                    ops.append(dict(
                        works_location_id=works, production_date=d, project_id=pid, overtime_shift=sched == 18,
                        planned_output_t=round(p["daily_rate"], 3), actual_output_t=round(o, 3),
                        rework_t=round(rework, 3), regular_labour_hours=round(reg, 1),
                        overtime_labour_hours=round(ot, 1),
                        labour_cost_inr=round(reg * labour_rate + ot * labour_rate * C.OVERTIME_MULTIPLIER, 2),
                        machine_hours=round(mh_hours, 2), machine_cost_inr=round(m_cost, 2),
                        energy_kwh=round(kwh, 1), energy_cost_inr=round(kwh * energy_tariff(d), 2),
                        bottleneck_work_centre_id=wc_of_type[bottleneck], capacity_constrained=scale < 1.0,
                    ))
                    if scale < 1.0:
                        if down_by_type[bottleneck] > 0:
                            p["constrained_down"] += 1
                        else:
                            p["constrained_load"] += 1
                    p["produced"] += o
                    p["remaining"] -= o
                    if p["fab_start"] is None:
                        p["fab_start"] = d
                    if p["install_ready"] is None and p["produced"] >= 0.4 * p["tonnes"]:
                        p["install_ready"] = d
                    if p["remaining"] <= 0.01:
                        p["remaining"] = 0.0
                        p["fab_end"] = d

            for m, sch, pm, down, reason, prod, oper in state:
                eq_log.append(dict(
                    log_date=d, equipment_id=m["equipment_id"], scheduled_hours=sch, planned_maintenance_hours=pm,
                    available_hours=sch - pm, downtime_hours=down, operating_hours=round(oper, 2),
                    idle_hours=round(max(0.0, prod - oper), 2), downtime_reason=reason,
                ))

    # Projects still in fabrication (or not started) at the cut-off: forecast their would-be dates
    for p in projects:
        if p["fab_end"] is None:
            if p["fab_start"] is None:
                p["fab_start"] = p["release"]
                p["install_ready"] = add_wd(p["release"], 0.4 * p["planned_fab_wd"] / 0.9)
                p["fab_end"] = add_wd(p["release"], p["planned_fab_wd"] / 0.9)
            else:
                rate = p["produced"] / max(1, wd_between(p["fab_start"], C.CUTOFF))
                rate = max(rate, 0.6 * p["daily_rate"])
                p["fab_end"] = add_wd(C.CUTOFF, p["remaining"] / rate)
                if p["install_ready"] is None:
                    p["install_ready"] = add_wd(C.CUTOFF, max(0.0, 0.4 * p["tonnes"] - p["produced"]) / rate)
    return ops, eq_log


# --------------------------------------------------------------------------------------
# Site execution, delays, labour, costs and revenue
# --------------------------------------------------------------------------------------
def simulate_site(p):
    td = dt.timedelta
    (inst_ps, inst_pe), (test_ps, test_pe), (comm_ps, comm_pe) = p["plan"][5], p["plan"][6], p["plan"][7]
    p["inst_start"] = max(inst_ps + p["shift"], p["install_ready"], p["fab_start"] + td(days=20))
    p["site_eff"] = float(np.clip(rng.normal(0.97 + 0.05 * p["pm_skill"] - 0.04 * p["foak"], 0.05), 0.72, 1.10))
    p["client_delay"] = int(rng.uniform(15, 60)) if rng.random() < 0.15 else 0
    p["weather_delay"] = int(rng.uniform(7, 25)) if rng.random() < 0.20 else 0
    planned_inst = (inst_pe - inst_ps).days
    nominal_end = p["inst_start"] + td(days=int(planned_inst / p["site_eff"]) + p["client_delay"] + p["weather_delay"])
    supplier_gate = p["last_a_grn"] + td(days=int(0.55 * planned_inst))   # install + align + trial the late item
    works_gate = p["fab_end"] + td(days=25)
    p["inst_end"] = max(nominal_end, supplier_gate, works_gate)
    p["inst_wait"] = (p["inst_end"] - nominal_end).days
    p["inst_wait_cause"] = "Supplier delay" if supplier_gate >= works_gate else "Works capacity constraint"

    overlap = (inst_pe - test_ps).days
    p["test_start"] = p["inst_end"] - td(days=int(overlap * rng.uniform(0.5, 1.0)))
    test_dur = (test_pe - test_ps).days * max(0.8, 1 + p["foak"] * rng.uniform(0.2, 0.8) + rng.normal(0, 0.08))
    p["test_end"] = p["test_start"] + td(days=max(3, int(test_dur)))
    overlap = (test_pe - comm_ps).days
    p["comm_start"] = p["test_end"] - td(days=int(overlap * rng.uniform(0.5, 1.0)))
    comm_dur = (comm_pe - comm_ps).days * max(0.8, 1 + p["foak"] * rng.uniform(0.1, 0.6) + rng.normal(0, 0.06))
    p["comm_end"] = p["comm_start"] + td(days=max(3, int(comm_dur)))
    p["concept_end"] = p["plan"][1][1] + p["shift"] + td(days=int(rng.integers(-2, 7)))

    p["total_delay"] = (p["comm_end"] - p["contractual_end"]).days
    excusable = p["kickoff_delay"] + p["client_delay"] + p["weather_delay"]   # C08: client / force majeure
    p["contractor_delay"] = max(0, p["total_delay"] - excusable)
    weeks = math.ceil(p["contractor_delay"] / 7) if p["contractor_delay"] > LD_GRACE_DAYS else 0
    p["ld_amount"] = round(min(weeks * C.LD_RATE_PER_WEEK, C.LD_CAP) * p["contract_value"], 2) if weeks else 0.0
    p["completed"] = p["comm_end"] <= C.CUTOFF


def stage_actuals(p):
    return {1: (p["actual_start"], p["concept_end"]), 2: (p["eng_start"], p["eng_end"]),
            3: (p["proc_start"], p["proc_end"]), 4: (p["fab_start"], p["fab_end"]),
            5: (p["inst_start"], p["inst_end"]), 6: (p["test_start"], p["test_end"]),
            7: (p["comm_start"], p["comm_end"])}


def delay_causes(p):
    """Dominant cause of the delay each stage adds on its own (D04)."""
    causes = {1: "Client-side" if p["kickoff_delay"] > 5 else "On schedule",
              2: "Engineering rework" if p["eng_slip"] > 3 else "On schedule"}
    plan_proc_end = p["plan"][3][1] + p["shift"]
    causes[3] = "Supplier delay" if (p["proc_end"] - plan_proc_end).days > 7 else "On schedule"
    fs, fe = p["plan"][4]
    steel_late = (p["steel_60_date"] - (fs + p["shift"])).days
    ext = (p["fab_end"] - p["fab_start"]).days - (fe - fs).days
    works_cause = "Equipment breakdown" if p["constrained_down"] >= p["constrained_load"] else "Works capacity constraint"
    drivers = {"Supplier delay": steel_late, "Engineering rework": 0.6 * p["eng_slip"], works_cause: ext}
    top = max(drivers, key=drivers.get)
    causes[4] = top if drivers[top] > 5 else "On schedule"
    planned_inst = (p["plan"][5][1] - p["plan"][5][0]).days
    drivers = {"Labour productivity": planned_inst / p["site_eff"] - planned_inst, "Client-side": p["client_delay"],
               "Weather": p["weather_delay"], p["inst_wait_cause"]: p["inst_wait"]}
    top = max(drivers, key=drivers.get)
    causes[5] = top if drivers[top] > 5 else "On schedule"
    for sid, (a, b) in ((6, (p["test_start"], p["test_end"])), (7, (p["comm_start"], p["comm_end"]))):
        ext = (b - a).days - (p["plan"][sid][1] - p["plan"][sid][0]).days
        causes[sid] = "Technical issues" if ext > 3 else "On schedule"
    return causes


def build_labour(p, site_supervisors, design_engineers, counter):
    """Weekly site-erection and engineering timesheets (fact_labor). Works labour is in the production log."""
    rows = []
    site_rate = 340 * {"West": 1.05, "East": 0.95, "South": 1.0}[p["region"]]
    eng_rate = 1250.0
    site_hours = SITE_LABOUR_SHARE * p["budget"]["Labour"] / site_rate
    eng_hours = ENG_LABOUR_SHARE * p["budget"]["Labour"] / eng_rate
    supervisor, lead = rng.choice(site_supervisors), rng.choice(design_engineers)

    def weeks(a, b):
        return list(pd.date_range(a, b, freq="W-SAT").date) or [b]

    # Engineering: rework adds hours that earn nothing
    ew = weeks(p["eng_start"], p["eng_end"])
    for w in ew:
        earned = eng_hours / len(ew)
        actual = earned * (1 + p["rework_frac"]) * rng.normal(1, 0.05)
        ot = actual * 0.08
        counter[0] += 1
        rows.append(dict(labour_entry_id=f"LAB-{counter[0]:06d}", week_ending_date=w, project_id=p["project_id"],
                         labour_type="Engineering", supervisor_id=lead, headcount=max(1, round(actual / 48)),
                         earned_hours=round(earned, 1), regular_hours=round(actual - ot, 1),
                         overtime_hours=round(ot, 1), idle_hours=0.0,
                         labour_cost_inr=round((actual - ot) * eng_rate + ot * eng_rate * C.OVERTIME_MULTIPLIER, 2)))

    # Site erection: inefficiency, then idle crew while waiting for materials, client or weather
    sw = weeks(p["inst_start"], p["inst_end"])
    behind = p["inst_end"] > p["plan"][5][1] + p["shift"]
    weekly_actual = site_hours / p["site_eff"] / len(sw)
    idle_total = weekly_actual * (0.35 * p["inst_wait"] + 0.25 * p["client_delay"] + 0.4 * p["weather_delay"]) / 7
    idle_weeks = max(1, int(round((p["inst_wait"] + p["client_delay"] + p["weather_delay"]) / 7)))
    for k, w in enumerate(sw):
        earned = site_hours / len(sw)
        actual = weekly_actual * rng.normal(1, 0.04)
        idle = idle_total / idle_weeks if k >= len(sw) - idle_weeks else 0.0
        ot = actual * (0.12 if behind else 0.04)
        counter[0] += 1
        rows.append(dict(labour_entry_id=f"LAB-{counter[0]:06d}", week_ending_date=w, project_id=p["project_id"],
                         labour_type="Site Erection", supervisor_id=supervisor,
                         headcount=max(1, round((actual + idle) / 52)), earned_hours=round(earned, 1),
                         regular_hours=round(actual - ot, 1), overtime_hours=round(ot, 1), idle_hours=round(idle, 1),
                         labour_cost_inr=round((actual - ot + idle) * site_rate
                                               + ot * site_rate * C.OVERTIME_MULTIPLIER, 2)))
    return rows


def build_costs(p, proc_lines, ops_df, labour_rows, counter):
    """Monthly cost ledger postings by category and source system (fact_project_cost)."""
    gl = {c[1]: (c[0], c[4]) for c in R.COST_CATEGORIES}
    postings = {}

    def post(cat, source, amounts):
        for me, amt in amounts.items():
            key = (cat, source, me)
            postings[key] = postings.get(key, 0.0) + amt

    for r in proc_lines:
        post("Material", "Procurement", {month_end(r["grn_date"]): r["line_value_inr"]})
    pops = ops_df[ops_df.project_id == p["project_id"]]
    if len(pops):
        me = pops.production_date.map(month_end)
        for col, cat in (("labour_cost_inr", "Labour"), ("machine_cost_inr", "Equipment"), ("energy_cost_inr", "Energy")):
            post(cat, "Production", pops.groupby(me)[col].sum().to_dict())
    for r in labour_rows:
        post("Labour", "Timesheet", {month_end(r["week_ending_date"]): r["labour_cost_inr"]})

    b = p["budget"]
    planned_inst = (p["plan"][5][1] - p["plan"][5][0]).days
    planned_site = (p["plan"][7][1] - p["plan"][5][0]).days
    works_machine_budget = p["tonnes"] * sum(m[4] / m[3] for m in R.WORK_CENTRE_TYPES)
    works_energy_budget = p["tonnes"] * sum(m[5] * 0.65 / m[3] for m in R.WORK_CENTRE_TYPES) * energy_tariff(p["award_date"])
    site_equipment = max(b["Equipment"] - works_machine_budget, 0.2 * b["Equipment"])
    site_energy = max(b["Energy"] - works_energy_budget, 0.2 * b["Energy"])
    inst_days = (p["inst_end"] - p["inst_start"]).days
    site_days = (p["comm_end"] - p["inst_start"]).days
    site_ext = max(0.0, site_days / planned_site - 1)
    total_days = (p["comm_end"] - p["actual_start"]).days

    finance = {
        "Equipment": (site_equipment / planned_inst * inst_days, p["inst_start"], p["inst_end"]),
        "Energy": (site_energy / planned_site * site_days, p["inst_start"], p["comm_end"]),
        "Subcontractor": (b["Subcontractor"] * (1 + rng.normal(0.01 - 0.02 * p["pm_skill"], 0.06) + 0.35 * site_ext),
                          p["inst_start"], p["test_end"]),
        "Transportation": (b["Transportation"] * (1 + rng.normal(-0.01, 0.04) + 0.3 * p["late_crit_share"]),
                           min(r["grn_date"] for r in proc_lines), p["inst_end"]),
        "Other": (b["Other"] * (1 + rng.normal(-0.01 - 0.01 * p["pm_skill"], 0.04)
                                + 0.3 * max(0, p["total_delay"]) / p["planned_duration"]),
                  p["actual_start"], p["comm_end"]),
    }
    for cat, (amt, a, z) in finance.items():
        post(cat, "Finance", spread(amt, a, z))

    # Overhead (E02): 60% time-based, 40% allocated on direct cost
    direct_actual = sum(v for (cat, _, _), v in postings.items() if cat not in ("Overhead", "Other"))
    direct_budget = sum(v for k, v in b.items() if k not in ("Overhead", "Other"))
    overhead = 0.6 * b["Overhead"] * total_days / p["planned_duration"] + 0.4 * b["Overhead"] * direct_actual / direct_budget
    post("Overhead", "Finance", spread(overhead, p["actual_start"], p["comm_end"]))

    rows, total = [], 0.0
    for (cat, source, me), amt in sorted(postings.items(), key=lambda kv: (kv[0][2], kv[0][0])):
        total += amt
        if me > C.CUTOFF:
            continue
        counter[0] += 1
        rows.append(dict(document_no=f"JV-{counter[0]:07d}", project_id=p["project_id"],
                         cost_category_id=gl[cat][0], gl_account=gl[cat][1], posting_date=me,
                         source_system=source, amount_inr=round(amt, 2)))
    p["would_be_cost"] = total
    return rows


def build_revenue(p, counter):
    acts = stage_actuals(p)
    events = []
    for sid, _, _, _, bill, _ in R.STAGES:
        if bill > 0:
            when = acts[sid][0] if sid == 1 else acts[sid][1]
            events.append((when, "Milestone Billing", sid, bill * p["contract_value"]))
    if p["co_frac"] > 0:
        events.append((p["inst_end"], "Change Order", 5, p["co_frac"] * p["contract_value"]))
    if p["pvc"] and abs(p["pvc_amount"]) > 0:
        events.append((p["proc_end"], "Price Variation", 3, p["pvc_amount"]))
    if p["ld_amount"] > 0:
        events.append((p["comm_end"], "Liquidated Damages", 7, -p["ld_amount"]))
    rows = []
    for when, rtype, sid, amt in sorted(events, key=lambda e: e[0]):
        if when > C.CUTOFF:
            continue
        counter[0] += 1
        rows.append(dict(invoice_no=f"INV-{counter[0]:05d}", project_id=p["project_id"], invoice_date=when,
                         revenue_type=rtype, stage_id=sid, amount_inr=round(amt, 2)))
    return rows


def build_milestones(p):
    acts, causes, rows = stage_actuals(p), delay_causes(p), []
    for sid, *_ in R.STAGES:
        (ps, pe), (a_s, a_e) = p["plan"][sid], acts[sid]
        started, finished = a_s <= C.CUTOFF, a_e <= C.CUTOFF
        rows.append(dict(project_id=p["project_id"], stage_id=sid, planned_start_date=ps, planned_end_date=pe,
                         actual_start_date=a_s if started else None, actual_end_date=a_e if finished else None,
                         milestone_status="Completed" if finished else ("In Progress" if started else "Not Started"),
                         delay_cause=causes[sid] if finished else None))
    return rows


# --------------------------------------------------------------------------------------
def main():
    locations = build_locations()
    clients = build_clients()
    employees, pm_skill = build_employees()
    suppliers, sup_hidden = build_suppliers()
    materials = build_materials()
    work_centres, equipment, machines = build_works()
    projects, budgets = build_projects(clients, employees, pm_skill, locations)

    suppliers_by_group = suppliers.groupby("material_group").supplier_id.apply(list).to_dict()
    materials_by_group = {g: df.to_dict("records") for g, df in materials.groupby("material_group")}
    buyers = employees.loc[employees.role == "Procurement Buyer", "employee_id"].tolist()
    site_sups = employees.loc[employees.role == "Site Supervisor", "employee_id"].tolist()
    designers = employees.loc[employees.role == "Design Engineer", "employee_id"].tolist()

    line_counter, proc = [0], {}
    for p in projects:
        simulate_engineering(p)
        proc[p["project_id"]] = simulate_procurement(p, suppliers_by_group, sup_hidden, materials_by_group,
                                                     buyers, line_counter)
        prepare_fabrication(p)

    print("Simulating works operations day by day ...")
    ops, eq_log = simulate_works(projects, machines, work_centres)
    ops_df = pd.DataFrame(ops)

    lab_counter, cost_counter, rev_counter = [0], [0], [0]
    labour, costs, revenue, milestones, project_rows, hidden = [], [], [], [], [], []
    for p in projects:
        simulate_site(p)
        lab = build_labour(p, site_sups, designers, lab_counter)
        lines = proc[p["project_id"]]
        cost_rows = build_costs(p, lines, ops_df, lab, cost_counter)
        to_date = sum(r["amount_inr"] for r in cost_rows)
        p["percent_complete"] = 100.0 if p["completed"] else float(
            np.clip(100 * to_date / p["would_be_cost"] + rng.normal(0, 1.5), 1, 99))
        labour += [r for r in lab if r["week_ending_date"] <= C.CUTOFF]
        costs += cost_rows
        revenue += build_revenue(p, rev_counter)
        milestones += build_milestones(p)
        project_rows.append(dict(
            project_id=p["project_id"], project_name=p["project_name"], client_id=p["client_id"],
            industry=p["industry"], site_location_id=p["site_location_id"], works_location_id=p["works"],
            project_manager_id=p["pm"], contract_type="Fixed Price (Lump Sum)", has_price_variation_clause=p["pvc"],
            contract_value_inr=p["contract_value"], award_date=p["award_date"], planned_start_date=p["planned_start"],
            planned_end_date=p["contractual_end"], actual_start_date=p["actual_start"],
            actual_end_date=p["comm_end"] if p["completed"] else None,
            status="Completed" if p["completed"] else "In Progress",
            percent_complete=round(p["percent_complete"], 1), planned_fab_tonnes=round(p["tonnes"], 1)))
        hidden.append(dict(project_id=p["project_id"], foak=p["foak"], pm_skill=round(p["pm_skill"], 3),
                           estimate_bias=round(p["estimate_bias"], 3), design_change=p["design_change"],
                           price_pressure=p["price_pressure"], kickoff_delay=p["kickoff_delay"],
                           eng_slip=p["eng_slip"], rework_frac=round(p["rework_frac"], 3),
                           site_eff=round(p["site_eff"], 3), client_delay=p["client_delay"],
                           weather_delay=p["weather_delay"], inst_wait=p["inst_wait"],
                           total_delay=p["total_delay"], contractor_delay=p["contractor_delay"]))

    # Procurement: keep what existed by the cut-off; later events are unknown
    po_rows = []
    for lines in proc.values():
        for r in lines:
            if r["po_date"] > C.CUTOFF:
                continue
            row = {k: v for k, v in r.items() if not k.startswith("_")}
            for col in ("supplier_confirm_date", "delivery_date", "inspection_date", "grn_date"):
                if row[col] is not None and row[col] > C.CUTOFF:
                    row[col] = None
            if row["delivery_date"] is None:
                row["qty_rejected"] = 0.0
            row["line_status"] = "Received" if row["grn_date"] is not None else "Open"
            po_rows.append(row)

    steel = pd.DataFrame({"month_start": pd.date_range("2020-10-01", C.CUTOFF, freq="MS").date})
    steel["steel_price_index"] = steel.month_start.map(steel_index)

    truth = {
        "dim_location": locations, "dim_client": clients, "dim_employee": employees, "dim_supplier": suppliers,
        "dim_material": materials, "dim_work_centre": work_centres, "dim_equipment": equipment,
        "dim_cost_category": pd.DataFrame([(c[0], c[1], i + 1, c[3], c[4]) for i, c in enumerate(R.COST_CATEGORIES)],
                                          columns=["cost_category_id", "cost_category", "sort_order",
                                                   "cost_behaviour", "gl_account"]),
        "dim_stage": pd.DataFrame([(s[0], s[1], s[0], s[4], s[5]) for s in R.STAGES],
                                  columns=["stage_id", "stage_name", "stage_order", "billing_share", "description"]),
        "dim_project": pd.DataFrame(project_rows),
        "fact_budget": budgets,
        "fact_project_cost": pd.DataFrame(costs),
        "fact_procurement": pd.DataFrame(po_rows),
        "fact_operations": ops_df,
        "fact_equipment": pd.DataFrame(eq_log),
        "fact_labor": pd.DataFrame(labour),
        "fact_milestones": pd.DataFrame(milestones),
        "fact_revenue": pd.DataFrame(revenue),
        "ref_steel_price_index": steel,
    }
    supplier_hidden = pd.DataFrame([dict(supplier_id=k, archetype=v["archetype"],
                                         price_factor=round(v["price_factor"], 3)) for k, v in sup_hidden.items()])
    machine_hidden = pd.DataFrame([dict(equipment_id=m["equipment_id"], reliability=m["reliability"]) for m in machines])

    C.DATA_QA.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(hidden).to_csv(C.DATA_QA / "hidden_drivers.csv", index=False)
    supplier_hidden.to_csv(C.DATA_QA / "hidden_supplier_archetypes.csv", index=False)
    machine_hidden.to_csv(C.DATA_QA / "hidden_machine_reliability.csv", index=False)
    truth_dir = C.DATA_QA / "truth"
    truth_dir.mkdir(exist_ok=True)
    for name, df in truth.items():
        df.to_csv(truth_dir / f"{name}.csv", index=False)

    write_raw_extracts(truth, rng)
    print("Rows generated:")
    for name, df in truth.items():
        print(f"  {name:<24}{len(df):>8,}")


if __name__ == "__main__":
    main()
