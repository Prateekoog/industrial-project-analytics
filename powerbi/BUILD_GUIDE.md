# Power BI Build Guide

Everything the dashboard needs is already prepared: the data workbook, the model design, every DAX measure and the page layouts. Expect the build to take about 3 to 4 hours. Two routes are available (ASSUMPTIONS J04).

## Route A: Power BI service in the browser (works on a Mac)

Needs a work or school Microsoft account. A personal Gmail or Outlook address will not work.

1. Go to `app.powerbi.com` and sign in. Open **My workspace**.
2. **New > Upload a file > Browse** and choose `powerbi/ProjectCo_PowerBI_Dataset.xlsx`. Choose to import the data. This creates a semantic model with all 18 tables.
3. Open the semantic model and click **Open data model** (web modelling).
4. **Relationships:** drag each relationship listed in `data_dictionary.md`. Set cardinality to Many-to-one and cross-filter to Single. Set `fact_procurement[grn_date]` to inactive.
5. **Date table:** select `dim_date` > Mark as date table > `date`.
6. **Measures:** create a table `_Measures` and paste each measure from `dax_measures.md`. Set formats: percentages as %, money with thousands separators.
7. **Create report** from the model. Build the 4 pages in `dashboard_design.md`. Apply the theme: View > Themes > Browse > `projectco_theme.json`.
8. Check every card against the **Reconciliation targets** table at the end of `dax_measures.md`.
9. Export screenshots (File > Export > PDF or PowerPoint) for the GitHub README.

## Route B: Power BI Desktop (any Windows PC, for example a college lab)

1. Install Power BI Desktop from the Microsoft Store (usually no admin rights needed).
2. **Get data > Excel workbook** and select `ProjectCo_PowerBI_Dataset.xlsx`. Tick all tables and choose Load. Alternatively use **Text/CSV** on the files in `powerbi/data/`.
3. In **Model view**, delete any relationships Power BI auto-detected, then create the ones in `data_dictionary.md`.
4. Follow steps 5 to 8 of Route A.
5. **File > Save as** `powerbi/ProjectCo_Dashboard.pbix`, and commit it to the repository.

## Before you call it done
- [ ] All cards match the reconciliation targets.
- [ ] Industry slicer changes every visual on the page; Works slicer changes both production and machine visuals.
- [ ] No visual shows "(Blank)" categories, which would indicate a missing relationship.
- [ ] Every visual has a title phrased as the question it answers.
- [ ] Screenshots saved to `reports/figures/powerbi_page*.png` and linked from the README.
