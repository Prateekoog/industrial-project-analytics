"""Static reference data for the synthetic ProjectCo world.

Everything here is fictional. Ranges are plausible synthetic values documented in
docs/ASSUMPTIONS.md, not sourced market data.
"""
import datetime as dt

# --------------------------------------------------------------------------------------
# Industries (B04, C10). foak = first-of-a-kind technology risk, 0 (mature) .. 1 (new).
# value_mult scales the typical contract size; mix_adjust tweaks the cost mix (E01).
# --------------------------------------------------------------------------------------
INDUSTRIES = {
    "Sugar": dict(n=12, margin=(0.11, 0.15), value_mult=0.8, foak=0.0,
                  sites=["Kolhapur", "Ahmednagar", "Muzaffarnagar", "Lakhimpur Kheri", "Belagavi"],
                  mix_adjust={}, scopes=["{n} TCD Cane Mill Expansion", "Cogeneration Boiler Package",
                                         "Sugar Refinery Upgrade", "Process House Modernisation"]),
    "Cement": dict(n=12, margin=(0.10, 0.14), value_mult=1.4, foak=0.0,
                   sites=["Chittorgarh", "Satna", "Kurnool", "Raipur"],
                   mix_adjust={"Transportation": 1.1},
                   scopes=["{n} TPD Clinker Line", "Preheater and Kiln Upgrade", "Cement Grinding Unit",
                           "Clinker Cooler Retrofit"]),
    "Mining & Material Handling": dict(n=12, margin=(0.12, 0.16), value_mult=1.3, foak=0.0,
                                       sites=["Dhanbad", "Angul", "Keonjhar", "Korba", "Singrauli"],
                                       mix_adjust={"Equipment": 1.15, "Transportation": 1.2},
                                       scopes=["{n} TPH Overland Conveyor", "Stacker-Reclaimer Package",
                                               "Wagon Tippler Complex", "Crushing and Screening Plant"]),
    "Industrial Equipment": dict(n=10, margin=(0.15, 0.20), value_mult=0.5, foak=0.0,
                                 sites=["Chakan", "Hosur", "Vadodara", "Coimbatore", "Rourkela"],
                                 mix_adjust={"Labour": 1.25, "Subcontractor": 0.6, "Equipment": 1.1},
                                 scopes=["Heavy Gearbox Supply", "Ball Mill Package", "Hydraulic Press Line",
                                         "Kiln Drive Package"]),
    "Thermal Energy": dict(n=8, margin=(0.08, 0.12), value_mult=1.8, foak=0.0,
                           sites=["Korba", "Jharsuguda", "Singrauli", "Angul"],
                           mix_adjust={"Subcontractor": 1.15},
                           scopes=["Coal Handling Plant", "Ash Handling System", "{n} TPH Boiler Package"]),
    "Wastewater Treatment": dict(n=8, margin=(0.11, 0.15), value_mult=0.6, foak=0.0,
                                 sites=["Nagpur", "Ennore", "Patancheru", "Vadodara", "Haldia"],
                                 mix_adjust={"Subcontractor": 1.4, "Material": 0.9},
                                 scopes=["{n} MLD Effluent Treatment Plant", "Sludge Handling System",
                                         "Zero Liquid Discharge Plant"]),
    "Biochemicals": dict(n=6, margin=(0.12, 0.16), value_mult=0.9, foak=0.3,
                         sites=["Ahmednagar", "Muzaffarnagar", "Bharuch", "Haldia"],
                         mix_adjust={}, scopes=["{n} KLPD Distillery", "Fermentation and Evaporation Package"]),
    "Green Hydrogen": dict(n=5, margin=(0.14, 0.19), value_mult=1.2, foak=1.0,
                           sites=["Kutch", "Jamnagar", "Bikaner"],
                           mix_adjust={"Material": 1.05, "Other": 1.3},
                           scopes=["{n} MW Electrolyser Balance-of-Plant", "Hydrogen Compression and Storage"]),
    "Industrial Batteries": dict(n=4, margin=(0.13, 0.18), value_mult=1.0, foak=0.7,
                                 sites=["Sanand", "Hosur", "Bharuch"],
                                 mix_adjust={"Material": 1.05, "Other": 1.3},
                                 scopes=["Cell Plant Utilities Package", "Electrode Material Handling Line"]),
    "Carbon Capture": dict(n=3, margin=(0.15, 0.20), value_mult=1.1, foak=1.0,
                           sites=["Jamnagar", "Haldia", "Visakhapatnam"],
                           mix_adjust={"Material": 1.05, "Other": 1.3},
                           scopes=["{n} TPD CO2 Capture Unit"]),
}
NEW_ENERGY = {"Green Hydrogen", "Industrial Batteries", "Carbon Capture"}

# --------------------------------------------------------------------------------------
# Locations (B07). Works serve the sites in their region.
# --------------------------------------------------------------------------------------
WORKS = [
    # location_id, name, city, state, region, labour rate (Rs/h), labour factor, defect rate
    ("LOC-W1", "Works-West", "Pune", "Maharashtra", "West", 400, 0.95, 0.016),
    ("LOC-W2", "Works-East", "Kolkata", "West Bengal", "East", 340, 1.08, 0.038),
    ("LOC-W3", "Works-South", "Chennai", "Tamil Nadu", "South", 380, 1.00, 0.024),
]
REGION_TO_WORKS = {"West": "LOC-W1", "East": "LOC-W2", "South": "LOC-W3"}

SITES = {  # city: (state, region)
    "Kolhapur": ("Maharashtra", "West"), "Ahmednagar": ("Maharashtra", "West"),
    "Muzaffarnagar": ("Uttar Pradesh", "East"), "Lakhimpur Kheri": ("Uttar Pradesh", "East"),
    "Belagavi": ("Karnataka", "South"), "Chittorgarh": ("Rajasthan", "West"),
    "Satna": ("Madhya Pradesh", "West"), "Kurnool": ("Andhra Pradesh", "South"),
    "Raipur": ("Chhattisgarh", "East"), "Dhanbad": ("Jharkhand", "East"), "Angul": ("Odisha", "East"),
    "Keonjhar": ("Odisha", "East"), "Korba": ("Chhattisgarh", "East"),
    "Singrauli": ("Madhya Pradesh", "West"), "Jharsuguda": ("Odisha", "East"),
    "Chakan": ("Maharashtra", "West"), "Hosur": ("Tamil Nadu", "South"), "Vadodara": ("Gujarat", "West"),
    "Coimbatore": ("Tamil Nadu", "South"), "Rourkela": ("Odisha", "East"), "Nagpur": ("Maharashtra", "West"),
    "Ennore": ("Tamil Nadu", "South"), "Patancheru": ("Telangana", "South"), "Haldia": ("West Bengal", "East"),
    "Bharuch": ("Gujarat", "West"), "Kutch": ("Gujarat", "West"), "Jamnagar": ("Gujarat", "West"),
    "Bikaner": ("Rajasthan", "West"), "Sanand": ("Gujarat", "West"),
    "Visakhapatnam": ("Andhra Pradesh", "South"),
}

# --------------------------------------------------------------------------------------
# Lifecycle stages (D01, D02): planned start/end as a fraction of planned project duration.
# Stages overlap on purpose (fast-tracking). bill = milestone billing % of contract value.
# --------------------------------------------------------------------------------------
STAGES = [
    # id, name, start_frac, end_frac, billing share, description
    (1, "Concept", 0.00, 0.06, 0.10, "Kick-off, scope freeze, basic design basis; advance payment"),
    (2, "Engineering", 0.04, 0.30, 0.10, "Detailed design, drawings, specifications, bills of material"),
    (3, "Procurement", 0.15, 0.55, 0.30, "Purchase requisitions, RFQs, purchase orders, deliveries"),
    (4, "Fabrication", 0.30, 0.75, 0.20, "Cutting, rolling, welding, machining, assembly, painting in works"),
    (5, "Installation", 0.55, 0.92, 0.20, "Site erection of fabricated and bought-out equipment"),
    (6, "Testing", 0.88, 0.97, 0.00, "Mechanical completion checks, no-load and load trials"),
    (7, "Commissioning", 0.95, 1.00, 0.10, "Performance guarantee test run and handover"),
]

# --------------------------------------------------------------------------------------
# Cost categories (E01): base share of estimated cost and cost behaviour.
# --------------------------------------------------------------------------------------
COST_CATEGORIES = [
    # id, name, base share, behaviour, GL account
    (1, "Material", 0.520, "Variable", "GL-5100"),
    (2, "Labour", 0.110, "Variable", "GL-5200"),
    (3, "Subcontractor", 0.130, "Variable", "GL-5300"),
    (4, "Equipment", 0.055, "Time-based", "GL-5400"),
    (5, "Transportation", 0.045, "Variable", "GL-5500"),
    (6, "Energy", 0.030, "Mixed", "GL-5600"),
    (7, "Overhead", 0.075, "Time-based", "GL-5700"),
    (8, "Other", 0.035, "Mixed", "GL-5800"),
]

# --------------------------------------------------------------------------------------
# Material groups (G01): spend share of material budget, criticality, steel-linked flag,
# standard lead time range (days) and the supplier archetypes serving the group (G02).
# --------------------------------------------------------------------------------------
MATERIAL_GROUPS = {
    "Structural Steel": dict(share=0.16, crit="C", steel=True, lead=(20, 40),
                             archetypes=["reliable", "average", "cheap_late", "price_volatile"]),
    "Steel Plates": dict(share=0.14, crit="B", steel=True, lead=(25, 45),
                         archetypes=["reliable", "average", "price_volatile", "cheap_late"]),
    "Pipes & Fittings": dict(share=0.08, crit="B", steel=True, lead=(25, 50),
                             archetypes=["reliable", "average", "quality_problem"]),
    "Castings & Forgings": dict(share=0.09, crit="A", steel=False, lead=(100, 150),
                                archetypes=["reliable", "cheap_late", "quality_problem", "average"]),
    "Gearboxes & Drives": dict(share=0.10, crit="A", steel=False, lead=(100, 160),
                               archetypes=["reliable", "cheap_late", "average"]),
    "Motors": dict(share=0.10, crit="A", steel=False, lead=(80, 130),
                   archetypes=["reliable", "average", "cheap_late"]),
    "Bearings & Power Transmission": dict(share=0.08, crit="B", steel=False, lead=(30, 70),
                                          archetypes=["reliable", "average", "price_volatile"]),
    "Valves": dict(share=0.05, crit="B", steel=False, lead=(40, 80),
                   archetypes=["reliable", "average", "quality_problem"]),
    "Pumps & Compressors": dict(share=0.06, crit="A", steel=False, lead=(80, 130),
                                archetypes=["reliable", "average", "cheap_late"]),
    "Electrical & Cables": dict(share=0.08, crit="C", steel=False, lead=(20, 50),
                                archetypes=["reliable", "average", "price_volatile", "average"]),
    "Instrumentation": dict(share=0.04, crit="B", steel=False, lead=(40, 80),
                            archetypes=["reliable", "average", "cheap_late"]),
    "Refractory & Insulation": dict(share=0.02, crit="C", steel=False, lead=(20, 45),
                                    archetypes=["average", "quality_problem", "reliable"]),
}

# Industry tweaks to the material group mix
GROUP_MIX_ADJUST = {
    "Cement": {"Refractory & Insulation": 4.0},
    "Thermal Energy": {"Refractory & Insulation": 3.0, "Pipes & Fittings": 1.4},
    "Wastewater Treatment": {"Pumps & Compressors": 2.0, "Valves": 1.8, "Castings & Forgings": 0.3},
    "Mining & Material Handling": {"Bearings & Power Transmission": 2.0},
    "Sugar": {"Castings & Forgings": 1.3},
    "Green Hydrogen": {"Pumps & Compressors": 1.8, "Valves": 1.5, "Instrumentation": 2.0,
                       "Refractory & Insulation": 0.0},
    "Carbon Capture": {"Pumps & Compressors": 1.8, "Valves": 1.5, "Instrumentation": 2.0,
                       "Refractory & Insulation": 0.0},
    "Industrial Batteries": {"Electrical & Cables": 1.5, "Refractory & Insulation": 0.0},
    "Biochemicals": {"Pipes & Fittings": 1.5, "Valves": 1.4},
}

# Materials: (name, group, unit, standard price in Rs at base index)
MATERIALS = [
    ("ISMB 300 Beams", "Structural Steel", "MT", 62_000), ("ISMC 200 Channels", "Structural Steel", "MT", 60_000),
    ("Angles 100x100x10", "Structural Steel", "MT", 58_000), ("RHS 200x100 Hollow Section", "Structural Steel", "MT", 70_000),
    ("Chequered Plate 6 mm", "Structural Steel", "MT", 64_000), ("Built-up Column Sections", "Structural Steel", "MT", 76_000),
    ("Gratings and Handrails", "Structural Steel", "MT", 95_000), ("Purlins and Girts", "Structural Steel", "MT", 66_000),
    ("MS Plate 10 mm", "Steel Plates", "MT", 63_000), ("MS Plate 20 mm", "Steel Plates", "MT", 64_000),
    ("MS Plate 40 mm", "Steel Plates", "MT", 67_000), ("Boiler Quality Plate SA516", "Steel Plates", "MT", 88_000),
    ("Wear-resistant Plate 400 BHN", "Steel Plates", "MT", 145_000), ("SS 304 Plate", "Steel Plates", "MT", 240_000),
    ("SS 316L Plate", "Steel Plates", "MT", 310_000), ("Alloy Steel Plate SA387", "Steel Plates", "MT", 160_000),
    ("CS Pipe 6 inch Sch 40", "Pipes & Fittings", "m", 3_200), ("CS Pipe 12 inch Sch 40", "Pipes & Fittings", "m", 9_800),
    ("SS Pipe 4 inch Sch 10", "Pipes & Fittings", "m", 5_600), ("Alloy Steel Pipe P22", "Pipes & Fittings", "m", 14_500),
    ("Forged Elbows Set", "Pipes & Fittings", "Set", 48_000), ("Weld-neck Flanges Set", "Pipes & Fittings", "Set", 62_000),
    ("Expansion Bellows", "Pipes & Fittings", "Nos", 185_000), ("Pipe Supports Kit", "Pipes & Fittings", "Set", 38_000),
    ("Girth Gear Segment", "Castings & Forgings", "Nos", 4_800_000), ("Kiln Tyre Forging", "Castings & Forgings", "Nos", 6_500_000),
    ("Mill Roll Shell Casting", "Castings & Forgings", "Nos", 2_900_000), ("Crusher Hammer Set", "Castings & Forgings", "Set", 950_000),
    ("Main Shaft Forging", "Castings & Forgings", "Nos", 2_200_000), ("Pinion Forging", "Castings & Forgings", "Nos", 1_350_000),
    ("Grate Plate Castings", "Castings & Forgings", "Set", 1_150_000), ("Liner Plate Castings", "Castings & Forgings", "Set", 1_600_000),
    ("Planetary Gearbox 500 kW", "Gearboxes & Drives", "Nos", 7_800_000), ("Helical Gearbox 200 kW", "Gearboxes & Drives", "Nos", 2_600_000),
    ("Helical Gearbox 75 kW", "Gearboxes & Drives", "Nos", 980_000), ("Fluid Coupling Assembly", "Gearboxes & Drives", "Nos", 640_000),
    ("Kiln Main Drive Unit", "Gearboxes & Drives", "Nos", 11_500_000), ("Conveyor Drive Unit", "Gearboxes & Drives", "Nos", 1_850_000),
    ("Mill Drive Gear Unit", "Gearboxes & Drives", "Nos", 9_200_000), ("Brake and Holdback Set", "Gearboxes & Drives", "Set", 420_000),
    ("HT Motor 1 MW", "Motors", "Nos", 5_600_000), ("HT Motor 2.5 MW", "Motors", "Nos", 11_800_000),
    ("LT Motor 75 kW", "Motors", "Nos", 420_000), ("LT Motor 15 kW", "Motors", "Nos", 95_000),
    ("Slip-ring Motor 500 kW", "Motors", "Nos", 3_400_000), ("VFD Panel 500 kW", "Motors", "Nos", 2_900_000),
    ("Flameproof Motor 30 kW", "Motors", "Nos", 240_000), ("Soft Starter Panel", "Motors", "Nos", 560_000),
    ("Spherical Roller Bearing Set", "Bearings & Power Transmission", "Set", 380_000),
    ("Plummer Block Assembly", "Bearings & Power Transmission", "Nos", 145_000),
    ("Conveyor Idler Set", "Bearings & Power Transmission", "Set", 9_500),
    ("Steel Cord Conveyor Belt", "Bearings & Power Transmission", "m", 18_500),
    ("Fabric Conveyor Belt", "Bearings & Power Transmission", "m", 6_800),
    ("Drive Pulley Assembly", "Bearings & Power Transmission", "Nos", 860_000),
    ("Chain and Sprocket Set", "Bearings & Power Transmission", "Set", 210_000),
    ("Flexible Coupling", "Bearings & Power Transmission", "Nos", 78_000),
    ("Butterfly Valve 300 NB", "Valves", "Nos", 165_000), ("Gate Valve 150 NB", "Valves", "Nos", 72_000),
    ("Control Valve 100 NB", "Valves", "Nos", 410_000), ("Safety Relief Valve", "Valves", "Nos", 290_000),
    ("Knife Gate Valve 200 NB", "Valves", "Nos", 135_000), ("Ball Valve SS 50 NB", "Valves", "Nos", 38_000),
    ("Check Valve 200 NB", "Valves", "Nos", 88_000), ("Motorised Damper", "Valves", "Nos", 520_000),
    ("Centrifugal Pump 100 m3/h", "Pumps & Compressors", "Nos", 780_000), ("Slurry Pump 250 m3/h", "Pumps & Compressors", "Nos", 2_100_000),
    ("Screw Air Compressor 250 cfm", "Pumps & Compressors", "Nos", 1_650_000), ("Process Blower", "Pumps & Compressors", "Nos", 1_250_000),
    ("Boiler Feed Pump", "Pumps & Compressors", "Nos", 3_900_000), ("Hydrogen Compressor Skid", "Pumps & Compressors", "Nos", 18_500_000),
    ("Dosing Pump Skid", "Pumps & Compressors", "Nos", 420_000), ("Vacuum Pump", "Pumps & Compressors", "Nos", 960_000),
    ("HT Cable 11 kV", "Electrical & Cables", "m", 2_400), ("LT Power Cable", "Electrical & Cables", "m", 680),
    ("Control Cable", "Electrical & Cables", "m", 210), ("MCC Panel", "Electrical & Cables", "Nos", 2_800_000),
    ("Distribution Transformer 2 MVA", "Electrical & Cables", "Nos", 3_600_000), ("Cable Trays", "Electrical & Cables", "m", 1_150),
    ("Earthing Kit", "Electrical & Cables", "Set", 145_000), ("Lighting Package", "Electrical & Cables", "Set", 650_000),
    ("Pressure Transmitter", "Instrumentation", "Nos", 68_000), ("Electromagnetic Flow Meter", "Instrumentation", "Nos", 185_000),
    ("PLC/DCS Cabinet", "Instrumentation", "Nos", 4_200_000), ("Gas Analyser", "Instrumentation", "Nos", 1_650_000),
    ("Level Transmitter", "Instrumentation", "Nos", 92_000), ("Temperature Element Kit", "Instrumentation", "Set", 58_000),
    ("Weigh Feeder Controller", "Instrumentation", "Nos", 760_000), ("Vibration Monitoring Kit", "Instrumentation", "Set", 340_000),
    ("Refractory Bricks 70% Alumina", "Refractory & Insulation", "MT", 72_000),
    ("Low-cement Castable", "Refractory & Insulation", "MT", 58_000),
    ("Ceramic Fibre Blanket", "Refractory & Insulation", "m2", 1_450),
    ("Mineral Wool Insulation", "Refractory & Insulation", "m2", 820),
    ("Insulating Bricks", "Refractory & Insulation", "MT", 64_000),
    ("Anchors and Accessories", "Refractory & Insulation", "Set", 125_000),
]

# --------------------------------------------------------------------------------------
# Supplier behaviour archetypes (G02). Hidden from the analysis data.
#   price = price factor vs market benchmark, p_late = probability of late delivery,
#   late = (gamma shape, scale) of days late, p_reject / reject = rejection probability and share.
# --------------------------------------------------------------------------------------
ARCHETYPES = {
    "reliable":        dict(price=(1.04, 1.08), noise=0.02, p_late=0.07, late=(2.0, 2.5), p_reject=0.03, reject=(0.02, 0.06), weight=1.0),
    "average":         dict(price=(0.99, 1.03), noise=0.03, p_late=0.20, late=(2.0, 5.0), p_reject=0.05, reject=(0.03, 0.08), weight=1.4),
    "cheap_late":      dict(price=(0.90, 0.95), noise=0.03, p_late=0.48, late=(2.5, 9.0), p_reject=0.07, reject=(0.04, 0.10), weight=1.0),
    "quality_problem": dict(price=(0.95, 0.99), noise=0.03, p_late=0.22, late=(2.0, 5.0), p_reject=0.32, reject=(0.10, 0.30), weight=0.7),
    "price_volatile":  dict(price=(0.97, 1.02), noise=0.09, p_late=0.16, late=(2.0, 4.0), p_reject=0.04, reject=(0.02, 0.06), weight=0.7),
}

SUPPLIER_PREFIXES = [
    "Arkesh", "Bhuvik", "Charvik", "Dravin", "Ekansh", "Falgun", "Girvan", "Harsev", "Ishvar", "Jalvik",
    "Kavrin", "Lohit", "Madhvik", "Navrin", "Ojasvi", "Prakrit", "Ruchit", "Saumik", "Tanvik", "Udyan",
    "Vasvik", "Yashvin", "Zorav", "Amrit", "Bhavik", "Chirag", "Darsh", "Eklav", "Gaurik", "Hemant",
    "Indrav", "Jivan", "Keshav", "Lavik", "Mitrav", "Nikhar", "Omkar", "Parth", "Rudrav", "Sarthak",
]
GROUP_SUPPLIER_WORD = {
    "Structural Steel": "Structurals", "Steel Plates": "Plates & Alloys", "Pipes & Fittings": "Pipes & Fittings",
    "Castings & Forgings": "Castings", "Gearboxes & Drives": "Gears", "Motors": "Electric Motors",
    "Bearings & Power Transmission": "Transmission", "Valves": "Valves", "Pumps & Compressors": "Pumps",
    "Electrical & Cables": "Electricals", "Instrumentation": "Instruments", "Refractory & Insulation": "Refractories",
}
SUPPLIER_STATES = ["Maharashtra", "Gujarat", "Tamil Nadu", "West Bengal", "Karnataka", "Jharkhand",
                   "Haryana", "Telangana", "Odisha", "Punjab"]

CLIENT_PREFIXES = [
    "Arvenya", "Brahmora", "Dhanvira", "Ekamra", "Gaurang", "Hiranya", "Jalpari", "Kalpaka", "Lokesha",
    "Mahodaya", "Nirvaan", "Padmavan", "Rajvansh", "Sanjivani", "Tejaswa", "Ujjwala", "Vanshika", "Vikrama",
    "Yuvraj", "Akshaya", "Bhoomija", "Chandrika", "Devgiri", "Gomukh", "Indrayani", "Kanakpur", "Meghalay",
    "Narmadeya", "Prayag", "Shivalik", "Trivenya", "Vidarbha", "Amaravat", "Kaliyan", "Suryansh", "Rohilkhand",
    "Satpura", "Malwan", "Konkanastha", "Sahyadrik",
]
CLIENT_SUFFIX = {
    "Sugar": "Sugars Ltd", "Cement": "Cements Ltd", "Mining & Material Handling": "Minerals Ltd",
    "Industrial Equipment": "Industries Ltd", "Thermal Energy": "Power Ltd",
    "Wastewater Treatment": "Water Infrastructure Ltd", "Biochemicals": "Biorefineries Ltd",
    "Green Hydrogen": "Green Energy Ltd", "Industrial Batteries": "Cell Technologies Ltd",
    "Carbon Capture": "Decarbonisation Ltd",
}

FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Karan", "Ishaan", "Siddharth", "Rahul", "Vikram",
               "Ananya", "Priya", "Sneha", "Kavya", "Neha", "Pooja", "Meera", "Divya", "Riya", "Shreya",
               "Amit", "Sanjay", "Rajesh", "Suresh", "Manoj", "Deepak", "Nitin", "Prakash", "Anil", "Ravi",
               "Lakshmi", "Swati", "Nandini", "Aparna", "Kiran", "Gaurav", "Harish", "Mahesh", "Tarun", "Varun"]
LAST_NAMES = ["Sharma", "Verma", "Patil", "Kulkarni", "Iyer", "Nair", "Reddy", "Rao", "Das", "Banerjee",
              "Mukherjee", "Ghosh", "Singh", "Yadav", "Gupta", "Agarwal", "Joshi", "Deshmukh", "Pillai", "Menon",
              "Chatterjee", "Mishra", "Pandey", "Shetty", "Naidu", "Bhat", "Kumar", "Jain", "Mehta", "Shah"]

# --------------------------------------------------------------------------------------
# Works layout (F01): work centre types with machines, rated tonnes/hour per machine,
# machine-hour rate (Rs/h), rated kW, standard labour man-hours per tonne, crew per machine.
# --------------------------------------------------------------------------------------
WORK_CENTRE_TYPES = [
    # type, machines (name, n), t/h per machine, MHR, kW, std MH/t, crew
    ("Cutting", "CNC Plasma Cutter", 2, 2.9, 1_800, 120, 2.5, 2),
    ("Plate Rolling", "Plate Bending Rolls", 2, 2.85, 2_200, 90, 2.5, 3),
    ("Welding", "SAW Welding Station", 4, 1.4, 1_500, 45, 12.0, 3),
    ("Machining", "Vertical Turning Lathe", 3, 1.9, 4_200, 75, 6.0, 2),
    ("Assembly", "Assembly Bay (EOT Crane)", 2, 2.9, 1_600, 30, 5.0, 4),
    ("Blasting & Painting", "Shot Blasting and Paint Booth", 1, 5.85, 2_000, 110, 2.0, 3),
]

# Machine reliability classes (F06): daily breakdown probability, mean downtime hours per event
RELIABILITY = {
    "good": (0.08, 4.0), "average": (0.12, 5.0), "poor": (0.22, 7.0), "chronic": (0.35, 10.0),
}
# Per works: reliability class by work centre type; tuple entries are per machine.
WORKS_RELIABILITY = {
    "LOC-W1": {"Cutting": ("average", "good"), "Plate Rolling": ("good", "good"),
               "Welding": ("good", "average", "good", "good"), "Machining": ("good", "average", "good"),
               "Assembly": ("good", "good"), "Blasting & Painting": ("average",)},
    "LOC-W2": {"Cutting": ("poor", "average"), "Plate Rolling": ("chronic", "average"),
               "Welding": ("average", "chronic", "poor", "average"), "Machining": ("chronic", "poor", "average"),
               "Assembly": ("average", "good"), "Blasting & Painting": ("poor",)},
    "LOC-W3": {"Cutting": ("good", "average"), "Plate Rolling": ("average", "good"),
               "Welding": ("average", "good", "average", "chronic"), "Machining": ("average", "good", "poor"),
               "Assembly": ("good", "average"), "Blasting & Painting": ("average",)},
}
DOWNTIME_REASONS = ["Mechanical failure", "Electrical fault", "Hydraulic leak", "Tooling / consumables",
                    "Operator unavailable", "Awaiting spares"]

# National holidays and major festivals (works closed) used for the working calendar (F02)
HOLIDAYS = {dt.date(y, 1, 26) for y in range(2021, 2027)} | {dt.date(y, 8, 15) for y in range(2021, 2027)} | \
           {dt.date(y, 10, 2) for y in range(2021, 2027)} | {
    dt.date(2021, 11, 4), dt.date(2022, 10, 24), dt.date(2023, 11, 12), dt.date(2024, 11, 1), dt.date(2025, 10, 21),
    dt.date(2022, 3, 18), dt.date(2023, 3, 8), dt.date(2024, 3, 25), dt.date(2025, 3, 14), dt.date(2026, 3, 4),
}
