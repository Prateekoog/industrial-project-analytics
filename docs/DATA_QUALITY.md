# Data Quality: Raw to Analysis-Ready

```
RAW extracts (data/raw)  ->  QUALITY CHECKS  ->  CLEANING RULES  ->  VALIDATION  ->  ANALYSIS DATASET (data/processed)
   17 source files           profile, test       49 logged rules      83 automated       20 star-schema tables
   2,981 injected issues      every column        (data/qa/            checks, 0 failed
                                                   cleaning_log.csv)
```

Real source systems are messy, so the generator damages about 1-3% of rows in realistic ways and records each change in an answer key (`data/qa/injected_issues_log.csv`). **The cleaning code never reads that key.** It only sees the raw files, as it would with a real ERP export. Afterwards, validation compares the cleaned data with the key and with the true tables to measure how much was actually recovered.

## Issues found and how each was handled

| Source file | Issue (rows) | Detection rule | Decision | Why this decision |
|---|---|---|---|---|
| purchase_orders | Inconsistent supplier names (533): `UPPER`, `lower`, "Private Limited", "Pvt. Ltd.", "&" vs "and", stray spaces, typos | Name does not match the vendor master | Normalise (case, punctuation, "private limited" to "pvt ltd", spaces), exact-match to the master; otherwise fuzzy match with similarity >= 0.85 | Spend per supplier is wrong if one supplier appears under five names. Fuzzy matching is restricted to a high cutoff so two *different* suppliers are never merged. |
| purchase_orders | Duplicate lines (67) | Fully identical rows | Drop | They would double-count spend and deliveries |
| purchase_orders | Mixed date formats (about 5% of date cells): DD/MM/YYYY, DD-Mon-YYYY | ISO parse fails | Parse each explicit format in order | Never let a parser *guess* the day/month order |
| purchase_orders | Day and month swapped (9) | Delivery earlier than order confirmation | Swap day/month if that produces a date between confirmation and inspection | Only fix when the correction is provably consistent |
| purchase_orders | Missing delivery date on a received line (65) | Null delivery, inspection present | Impute = inspection date - median delivery-to-inspection lag (3 days); flag `delivery_date_imputed` | Keeps the line in lead-time and OTD analysis; the flag lets anyone exclude it |
| purchase_orders | Missing (44), zero (18) or 10x unit price (35) | Unit price x quantity differs from line value by > 1% | Unit price = line value / quantity | Line value is the invoiced amount and is trusted; price is the derived field |
| purchase_orders | Negative quantity (22) | Quantity < 0 while value > 0 | Absolute value | Sign error; line value confirms direction |
| cost_ledger | Duplicate postings (88) | Fully identical rows | Drop | Would double-count cost |
| cost_ledger | Zero-amount placeholder postings (44) | amount = 0 | Drop | Carry no information; inflate row counts |
| cost_ledger | Category typos and legacy codes (442): "Matrial", "MAT-01", "Labor", "Subcon", "O/H", "Freight"... | Not one of 8 standard names | Mapping table to the 8 categories | Cost-driver analysis depends on correct categories |
| cost_ledger | Missing category (133) | Null | Infer from the GL account code | The GL account is a system field, so it is reliable |
| production_log | Missing labour hours (201) | Null | Output x the works' median hours per tonne; flag `labour_hours_imputed` | Keeps output; median is robust to outliers |
| production_log | Output 10x too high (53) | > 3x plan and plausible after dividing by 10 | Divide by 10 | Decimal-shift error |
| production_log | Negative rework (40) | < 0 | Absolute value | Sign error |
| machine_log | Duplicate machine-days (324) | Identical rows | Drop | Would overstate available and down hours |
| machine_log | Negative downtime (194) | < 0 | Absolute value | Sign error |
| machine_log | Downtime x10 (259), of which 21 still looked plausible | Breaks the identity available = downtime + operating + idle | Recalculate downtime from the identity | Operating and idle come from the machine controller; downtime is typed by hand. The identity caught even the hidden errors. |
| machine_log | Missing downtime reason (295) | Downtime > 0, reason null | Label "Unspecified" | Keep the hours; do not invent a reason |
| site_timesheets | Missing overtime (38) | Null | Back-calculate from labour cost and the crew's hourly rate | Cost and hours must agree |
| site_timesheets | Zero headcount with hours (15) | headcount = 0 | Hours / standard weekly hours | Physical impossibility |
| projects_master | Industry label variants (10): "cement", "Mining & MH", "CCUS", "Green H2" | Not one of 10 industries | Mapping to canonical names | Industry slicing |
| projects_master | Y/Yes/1/TRUE flags | Mixed values | Boolean | Consistent filtering |
| milestones | Actual end before actual start (6) | end < start | Swap back | Physical impossibility |
| billing | Duplicate invoices (5), revenue-type variants (41): "LD", "Penalty - LD", "CO", "PVC" | Identical rows; non-standard labels | Drop; map to 4 types | Duplicates double-count revenue |

## How well the cleaning worked

Measured by `python/validation/validate_data.py` against the answer key and true tables:

| Check | Result |
|---|---|
| Supplier names matched to the correct supplier | 533 of 533 (100%) |
| Prices restored (missing, zero, 10x) | 97 of 97 (100%) |
| Negative quantities restored | 22 of 22 (100%) |
| Missing delivery dates imputed within 3 days of truth | 65 of 65 |
| Day/month swaps corrected | 4 of 9 (44%). The other 5 swaps still produced plausible dates, so no rule can detect them. This residual error is reported, not hidden. |
| Cost, spend, output, downtime, revenue and overtime totals vs truth | All within 0.001% |
| Row counts after de-duplication vs truth | Exact match for cost ledger, PO lines, machine log and billing |

## Validation after cleaning (83 checks, all pass)

- **Integrity:** unique primary keys on all 19 tables; 27 foreign-key checks with 0 orphans; quantities and prices positive; PO dates in process order; machine hours balanced; rework <= output.
- **Reconciliation:**
  - Material ledger = received PO value, per project, to the rupee. Works labour, machine and energy ledger = production log. Site labour ledger = timesheets.
  - Revised budget = original + change orders.
  - Completed projects billed exactly 100% of contract in milestones.
  - LD never exceeds the 5% cap and is always whole weeks x 0.5%.
  - Project end = commissioning end; status agrees with end date.
  - No transaction after the cut-off.
- The same reconciliations run again inside PostgreSQL (`database/validation.sql`, 11 checks), together with checks that the SQL views do not fan out and that view totals equal ledger totals.

## What remains imperfect (by design, and stated openly)

- 5 undetectable day/month swaps in delivery dates (about 0.1% of lines) remain.
- Imputed values (65 delivery dates, 201 labour-hour values, 38 overtime values) are estimates and are flagged.
- "Unspecified" downtime reasons (2.8% of downtime hours) cannot be attributed to a cause.
