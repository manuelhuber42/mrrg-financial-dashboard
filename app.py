import streamlit as st
import pandas as pd
import numpy as np
import calendar
import plotly.graph_objects as go

# --- GLOBAL MODELING CONSTANTS & FINANCIAL ARCHITECTURE ---
VAT_RATE = 0.19
# H-03 FIX: AfA period aligned to BMF AfA-Tabellen for Mietwagen/Taxi (intensive use).
# 60 months = 5 Jahre Nutzungsdauer per § 7 EStG. Loan term also extends to 60 months
# (KfW Universell + commercial Kfz-Finanzierung both support 5-7y terms).
VEHICLE_AMORTIZATION_PERIOD = 60
IT_AMORTIZATION_PERIOD = 36
OVERDRAFT_ANNUAL_RATE = 0.095
STANDARD_TAX_ROUNDING = 2

# --- DASHBOARD CONFIGURATION & CUSTOM CSS ---
st.set_page_config(page_title="MRRG Master Financial Engine", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Urbanist:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Urbanist', sans-serif !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Urbanist', sans-serif !important;
        font-weight: 700 !important;
    }
    
    /* Prevent Metric Cutoff - Override Streamlit Default Font Sizes */
    div[data-testid="stMetricValue"] > div {
        font-size: 1.6rem !important;
        white-space: nowrap !important;
    }
    div[data-testid="stMetricDelta"] > div {
        font-size: 0.85rem !important;
        white-space: nowrap !important;
    }
    div[data-testid="stMetricLabel"] > div {
        font-size: 0.9rem !important;
        white-space: nowrap !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LANGUAGE DICTIONARY ---
lang_choice = st.sidebar.selectbox("Language / Sprache", ["English", "Deutsch"])

if lang_choice == "English":
    loc = {
        "title": "MRRG Cybercab Fleet: Master Financial Engine",
        "subtitle": "*(HGB 3-Statement Model - Layer 20: Operational Calibration to Bank-Grade Defensible Central Case)*",
        "sec1": "1a. FLEET SCALING SCHEDULE",
        "y1_adds": "Year 1 Additions (Jan-Dec)",
        "y2_adds": "Year 2 Additions (Jan-Dec)",
        "y3_adds": "Year 3 Additions (Jan-Dec)",
        "y4_adds": "Year 4 Additions (Jan-Dec)",
        "y5_adds": "Year 5 Additions (Jan-Dec)",
        "sec1b": "1b. OPERATIONAL PHYSICS",
        "active_hours": "Active Hours / Day",
        "help_active_hours": "Blended weekly-average productive shift hours. Weekday 12.5h (sustained demand 7am-10pm minus charging/cleaning), weekend 14.5h (longer demand window 10am-3am, more lucrative routes). Excludes charging/maintenance windows. Onboard sensor cleaning (Cybercab spec, Cybertruck-derived) eliminates the depot-cleaning penalty assumed in earlier Waymo-benchmark estimates.",
        "speed": "Average Speed (km/h)",
        "help_speed": "Munich blended average speed: TomTom Traffic Index 2024 free-flow inner-city 21 km/h, adjusted for rush-hour congestion (14-17 km/h during 7-10am and 4-7pm), weather (60-90 days/year of rain/snow at -15-25% speed), and autonomous vehicle speed-limit discipline (-8% vs human drivers per Waymo Phoenix data).",
        "deadhead": "Deadhead Rate (%)",
        "help_deadhead": "Mature-state empty repositioning rate (Y3+, post-data accumulation). Y1-Y2 effectively higher (28-32%) due to cold-start routing; engine averages this implicitly through the 60-month horizon. Benchmark: Uber/Lyft mature European markets 18-22% per published Marketplace data. Munich's compact urban core supports lower-end of range.",
        "sec1c": "1c. UTILIZATION DYNAMICS",
        "util_mode": "Utilization Mode",
        "util_dyn": "Dynamic (Ramp & Cannibalization)",
        "util_fix": "Fixed Rate",
        "target_util": "Target Utilization (%)",
        "help_target": "Mature-state steady utilization. 75% reflects realistic demand-fill rate accounting for: weekday/weekend variance, geographic demand pockets (Schwabing/Maxvorstadt dense, Pasing/Hadern sparse), inevitable demand troughs (Tue-Thu 10am-noon). Waymo Phoenix Y5 utilization data: 72-78%.",
        "init_util": "Month 1 Launch Util. (%)",
        "help_init": "Month-1 launch utilization. 35% reflects market awareness ramp — early adopters only, limited demand density, brand recognition building. Conservative vs Uber's Munich launch curve (which had benefit of driver supply network effects unavailable to robotaxi).",
        "rec_rate": "Monthly Recovery (+%)",
        "help_rec": "Monthly utilization recovery rate. 3%/month implies ~12-15 months from launch utilization to target — aligns with Waymo's Phoenix ramp data (San Francisco launch took 14 months to reach 70% utilization). Faster recovery rates assume marketing/network effects that early-stage robotaxi operators rarely achieve.",
        "can_fac": "Cannibalization Factor",
        "help_can": "Measures how much new cars steal rides from existing cars.",
        "util_label": "Avg Util",
        "sec2": "2. TRIP DYNAMICS",
        "trip_dist": "Average Trip Distance (km)",
        "dwell": "Dwell Time (Minutes)",
        "help_dwell": "Total per-trip non-productive time: passenger ingress 60-90s (locating car via app, opening door, settling) + egress 60-90s (collecting belongings, ride end confirmation) + brief AI confirmation/sensor check 15-30s. Waymo Phoenix empirical data 2.5-4 min. First 18-24 months may run higher (4-5 min) as users learn the system; central case assumes mature-state user behavior.",
        "sec3": "3. PRICING (Incl. 19% VAT)",
        "base_fare": "Base Fare (€)",
        "price_km": "Price per km (€)",
        "tesla_take": "Tesla Take-Rate (%)",
        "sec4": "4. DAILY VARIABLE COSTS (Net)",
        "cleaning": "Cleaning Cost per Vehicle/Day (€)",
        "wear_rate": "Maintenance/Wear per km (€)",
        "wear_help": "Management-view levelized rate reflecting 4-5y vehicle scrap strategy (post-AfA exhaustion). Breakdown: tires €0.027, sensor maintenance €0.034 (Cybercab onboard cleaning reduces vs Waymo benchmark), body wear €0.012, fluids/suspension €0.005, HVAC/inspections €0.005, accident reserve €0.008, contingency €0.005. Benchmarked vs Sixt+, Free Now, MOIA published data. Below Waymo (€0.12-0.16) due to simpler Cybercab sensor stack and German labor rates.",
        "energy_rate": "Base Energy Cost per km (€)",
        "energy_help": "Base case: 0.17 kWh/km real-world consumption × €0.41/kWh blended Supercharger rate ÷ 0.84 charging efficiency = €0.085/km net base. Seasonality multiplier applied dynamically in engine (winter +45%, shoulder +30%, hot summer +10%). Benchmarked vs Sixt fleet operating cost data 2024.",
        "sec5": "5. VEHICLE FIXED COSTS (€ / Month, Net)",
        "insurance": "Insurance",
        "parking": "APCOA Charging Capable Space (Munich)",
        "telemetry": "Telemetry & API",
        "tuev": "TÜV / BO-Kraft Accrual",
        "help_tuev": "Monthly accrual for mandatory passenger transport inspections.",
        "charging_sub": "Tesla Charging Sub",
        "sec6": "6. CORPORATE HQ & REGULATORY (€ / Month, Net)",
        "hq_lease": "HQ Lease (Raumkosten)",
        "it_cloud": "IT, Cloud & AI Services",
        "base_legal": "Base Legal & Bookkeeping",
        "base_hq_ins": "Base HQ Insurance (Liability)",
        "legal_scale": "Legal/Tax Scaling (per added vehicle)",
        "ins_scale": "Corp Insurance Scaling (per added vehicle)",
        "bank_fees": "Bank Fees",
        "ihk": "IHK Membership",
        "gez": "GEZ (per vehicle)",
        "setup_costs": "One-off Setup Costs (Y1)",
        "sec7": "7. CAPEX & ASSET IMPAIRMENT",
        "base_price": "Base Cybercab Price (USD)",
        "fx": "USD to EUR Exchange Rate",
        "freight": "Import Freight & Ins. per Vehicle (€)",
        "duty": "Import Duty (Zoll) %",
        "it_hw": "IT Hardware CapEx (Y1)",
        "imp_trigger": "Tech Impairment Trigger Month (0=None)",
        "imp_pct": "Extraordinary Impairment Pct (§ 253 HGB) %",
        "sec8": "8. CAPITAL STRUCTURE & CASH POLICIES",
        "stamm": "Stammkapital (€)",
        "sh_loan": "Shareholder Loan (Subord.) (€)",
        "sh_loan_rate": "SH Loan Interest Rate (%)",
        "help_sh_rate": "Market rate required by Finanzamt to avoid hidden profit distribution (vGA) tax issues.",
        "ltv": "Vehicle Loan-to-Value (LTV) %",
        "help_ltv": "Percentage of total vehicle landing costs financed via bank debt.",
        "y1_loan_rate": "KfW Gründerkredit Rate (Y1) %",
        "y2_loan_rate": "Commercial Kfz-Finanzierung Rate (Y2+) %",
        "vat_rate_input": "VAT Bridge Loan Rate (%)",
        "vat_lag_input": "VAT Refund Lag (Months)",
        "cash_buffer_input": "Minimum Corporate Cash Buffer (€)",
        "max_overdraft_input": "Max Overdraft Line / Kontokorrentlinie (€)",
        "help_max_od": "Bank-approved overdraft ceiling. If model needs more than this, INSOLVENCY is flagged.",
        "legal_provision_input": "Monthly Legal/Litigation Provision (€) (§ 249 HGB)",
        "int_rate": "Cash Interest Rate (%)",
        "sec9": "9. OTHER INCOME / SALVAGE",
        "thg": "THG Quote per vehicle/yr",
        "help_thg": "Greenhouse Gas (GHG) Reduction Quota certificates.",
        "salvage": "Vehicle Sale Price (End of 5-Yr Useful Life)",
        
        "pnl_gbv": "Gross Booking Value (Customer Pays incl. 19% VAT)",
        "pnl_vat": "Less: 19% VAT (Finanzamt)",
        "pnl_net_rev": "Net Revenue (Umsatzerlöse excl. VAT)",
        "pnl_tesla_fee": "Less: Tesla Platform Fee (Take-Rate on Net Rev)",
        "pnl_mrrg_net": "MRRG Net Revenue (After Platform Fee)",
        "pnl_energy": "Less: Direct Energy (Variable, Seasonally Adjusted)",
        "pnl_wear": "Less: Direct Maintenance/Wear (Variable)",
        "pnl_clean": "Less: Cleaning Cost (Variable)",
        "pnl_db1": "Deckungsbeitrag 1 (DB1)",
        "pnl_ins": "Less: Insurance (Fixed)",
        "pnl_park": "Less: APCOA Parking (Fixed)",
        "pnl_api": "Less: Telemetry & API (Fixed)",
        "pnl_tuev": "Less: TÜV / BO-Kraft (Fixed)",
        "pnl_sub": "Less: Tesla Charging Sub (Fixed)",
        "pnl_db2": "Deckungsbeitrag 2 (DB2)",
        "pnl_hq_lease": "Less: HQ Lease (Raumkosten)",
        "pnl_it": "Less: IT, Cloud & AI Services",
        "pnl_legal": "Less: Legal, Tax & Bookkeeping (Scaled)",
        "pnl_hq_ins": "Less: Corporate Insurance (Liability, D&O - Scaled)",
        "pnl_fees": "Less: Subscriptions & Fees (IHK, GEZ)",
        "pnl_bank": "Less: Bank Fees",
        "pnl_legal_prov": "Less: Legal/Litigation Provision (§ 249 HGB)",
        "pnl_thg": "Add: THG Quote (Other Operating Income)",
        "pnl_ebitda": "EBITDA (Management View)",
        "pnl_ebitda_hgb": "EBITDA (HGB View, incl. Anlagenabgang per § 275 II Nr.4 HGB)",
        "pnl_afa_veh": "Less: Vehicle Depreciation (AfA)",
        "pnl_afa_it": "Less: IT Hardware Depreciation (AfA)",
        "pnl_salvage": "Add: Fleet Liquidation (Asset Sale)",
        "pnl_ebit": "EBIT (Operating Income)",
        "pnl_int_inc": "Add: Interest Income (Zinserträge)",
        "pnl_int_exp": "Less: Interest Expense (Loans & Overdraft)",
        "pnl_ebt": "EBT (Earnings Before Tax)",
        "pnl_tax": "Less: Corporate Taxes (Ertragsteuern)",
        "pnl_ni": "Net Income / Periodenergebnis",
        
        "cf_ni": "+ Net Income (Periodenergebnis)",
        "cf_depr": "+ Depreciation & Amortization",
        "cf_gain_sale": "- Gain on Sale of Assets",
        "cf_tax_prov": "+ Tax Provision Increase",
        "cf_tax_paid": "- Taxes Paid (Prepayments & True-up)",
        "cf_legal_prov": "+ Legal/Litigation Provision Increase",
        "cf_wc_thg": "-/+ Delta THG Receivable (WC)",
        "cf_vat_coll": "+ VAT Collected (Operations)",
        "cf_vat_paid": "- VAT Paid (Net Remittance & Vendor Input VAT)",
        "cf_op": "Net Cash from Operations",
        "cf_capex": "- Net CapEx (Vehicles & HW, incl. VAT)",
        "cf_vat_ref": "+ VAT Refund from Finanzamt (CapEx)",
        "cf_sale": "+ Proceeds from Asset Sale",
        "cf_inv": "Net Cash from Investing",
        "cf_eq": "+ Founder Equity Injection",
        "cf_sh": "+ Shareholder Loan Injection",
        "cf_kfw_draw": "+ Debt Drawdown (Vehicles)",
        "cf_prin": "- Principal Repayment (incl. Balloon)",
        "cf_vat_draw": "+ VAT Bridge Loan Drawdown",
        "cf_vat_repay": "- VAT Bridge Loan Repayment",
        "cf_overdraft_delta": "+/- Overdraft Line Net Flows",
        "cf_fin": "Net Cash from Financing",
        "cf_net": "Net Change in Cash",
        "cf_beg": "+ Beginning Cash Balance",
        "cf_end": "Ending Cash Balance",
        
        "bs_gfa": "Gross Fixed Assets",
        "bs_acc_depr": "- Accumulated Depreciation",
        "bs_nfa": "Net Fixed Assets",
        "bs_vat_rec": "VAT Receivable — CapEx Bridge (Finanzamt)",
        "bs_vat_rec_op": "VAT Receivable — Operational Vorsteuerüberhang (Finanzamt)",
        "bs_thg_rec": "THG Quota Receivable",
        "bs_tax_rec": "Tax Receivable — Vorauszahlungs-Überhang (§ 246 II HGB Bruttoprinzip)",
        "bs_cash": "Ending Cash Balance",
        "bs_tca": "Total Current Assets",
        "bs_ta": "TOTAL ASSETS",
        "bs_eq_share": "Share Capital (Stammkapital)",
        "bs_eq_ret": "Retained Earnings (Gewinnvortrag)",
        "bs_teq": "Total Equity",
        "bs_prov_tax": "Steuerrückstellungen (Tax Provision)",
        "bs_prov_legal": "Sonstige Rückstellungen (Legal/Litigation)",
        "bs_tprov": "Total Provisions",
        "bs_debt_kfw": "Long-Term Debt (Vehicle Loans)",
        "bs_debt_vat": "Short-Term Debt (VAT Bridge)",
        "bs_debt_overdraft": "Short-Term Overdraft Line (Kontokorrent)",
        "bs_pay_vat": "Umsatzsteuer-Zahllast (VAT Payable)",
        "bs_sh_loan": "Shareholder Loan (Subordinated)",
        "bs_tliab": "Total Liabilities",
        "bs_tleq": "TOTAL LIAB. & EQUITY",
        "bs_check": "BALANCE CHECK (Assets - Liab & Eq)",

        # === TAB LABELS (RESTORED — these were missing and would KeyError) ===
        "tab_pnl": "Income Statement (P&L)",
        "tab_hgb_pnl": "Statutory P&L (§ 275 HGB)",
        "tab_cf": "Cash Flow Statement",
        "tab_bs": "Balance Sheet",
        "tab_kpi": "KPIs & Ratios",
        "tab_charts": "Visualizations & Dashboards",
        "tab_readme": "README & User Manual",

        "hgb_title": "Statutory Income Statement (Gesamtkostenverfahren)",
        "hgb_pos1": "1. Revenues (Umsatzerlöse)",
        "hgb_pos2": "4. Other operating income (Sonstige betriebliche Erträge)",
        "hgb_pos3": "5. Cost of materials (Materialaufwand)",
        "hgb_pos4": "6. Personnel expenses (Personalaufwand)",
        "hgb_pos5": "7. Depreciation & Amortization (Abschreibungen)",
        "hgb_pos6": "8. Other operating expenses (Sonstige betriebliche Aufwendungen)",
        "hgb_pos7": "Finanzergebnis (Interest Result)",
        "hgb_pos8": "14. Taxes on income (Steuern vom Einkommen und vom Ertrag)",
        "hgb_pos9": "16. Period Result (Jahresüberschuss per § 275 HGB in annual view)",

        # === KPI LABELS (RESTORED — these were missing and would KeyError) ===
        "kpi_dscr": "Debt Service Coverage Ratio (DSCR)",
        "kpi_eq_ratio": "Equity Ratio",
        "kpi_runway": "Liquidity Runway (Months)",
        "kpi_net_ltv": "Net LTV (Adj. for Cash Shield)",
        "kpi_var_ratio": "Variable Expense Ratio",
        "kpi_fix_ratio": "Fixed Expense Ratio",
        "kpi_tot_ratio": "Total Expense Ratio",
        "kpi_other_inc_ratio": "Other Income Ratio (THG)",
        "kpi_db2_m": "Contribution Margin Ratio (DB2)",
        "kpi_ebitda_m": "EBITDA Margin",

        "sources_title": "Day 1 Sources & Uses of Capital",
        "src_stamm": "Sources: Stammkapital",
        "src_sh": "Sources: Shareholder Loan",
        "src_veh": "Sources: Vehicle Loan",
        "liquidity": "End of Month 1 Cash (Actual)",
        "output_title": "Master Financial Schedules (HGB)",
        "active_fleet": "Active Fleet",
        "cars": "Vehicles",
        "view_mode": "Display Granularity",
        "yearly": "Yearly Overview",
        "monthly": "Monthly Drilldown",
        "exp_y1": "Expand Year 1",
        "exp_y2": "Expand Year 2",
        "exp_y3": "Expand Year 3",
        "exp_y4": "Expand Year 4",
        "exp_y5": "Expand Year 5",
        "glossary_title": "Financial Metric Definitions & Methodology",
        "chart_rev": "Net Revenue",
        "chart_ebitda": "EBITDA",
        "chart_ni": "Net Income",
        "chart_fleet": "Vehicle Fleet (End of Year)",
        "chart_fcf": "Free Cash Flow",
        "chart_ta": "Total Balance Sheet (Assets)",
        "toggle_fcf": "Show Cumulative FCF",
        "cash_warn": "🚨 CRITICAL: Liquidity Floor Breached! Minimum cash cushion violated in month: ",
        "net_liq_warn": "⚠️  Net Liquidity Negative (Cash − Overdraft < Min Buffer) in month: ",
        "insolv_warn": "💀 INSOLVENCY: Required cash shortfall exceeds the bank-approved overdraft ceiling in month: ",
        "ebitda_recon_title": "EBITDA Reconciliation Bridge (Mgmt View → HGB View)"
    }
else:
    loc = {
        "title": "MRRG Cybercab-Flotte: Master-Finanzmodell",
        "subtitle": "*(HGB 3-Statement Model - Layer 20: Operative Kalibrierung auf bankgerechten Basisfall)*",
        "sec1": "1a. FLOTTENSKALIERUNG",
        "y1_adds": "Jahr 1 Zugänge (Jan-Dez)",
        "y2_adds": "Jahr 2 Zugänge (Jan-Dez)",
        "y3_adds": "Jahr 3 Zugänge (Jan-Dez)",
        "y4_adds": "Jahr 4 Zugänge (Jan-Dez)",
        "y5_adds": "Jahr 5 Zugänge (Jan-Dez)",
        "sec1b": "1b. OPERATIVE PHYSIK",
        "active_hours": "Aktive Stunden / Tag",
        "help_active_hours": "Gemischter Wochendurchschnitt produktiver Schichtstunden. Werktag 12,5h (Nachfrage 7-22 Uhr abzüglich Laden/Reinigung), Wochenende 14,5h (längeres Nachfragefenster 10-3 Uhr, lukrativere Strecken). Lade-/Wartungsfenster ausgeschlossen. Cybercab Onboard-Sensorreinigung eliminiert die Depot-Reinigungspause älterer Waymo-Benchmark-Schätzungen.",
        "speed": "Durchschnittsgeschwindigkeit (km/h)",
        "help_speed": "Münchner Mischgeschwindigkeit: TomTom Traffic Index 2024 Free-Flow Innenstadt 21 km/h, bereinigt um Berufsverkehr (14-17 km/h zwischen 7-10 und 16-19 Uhr), Wetter (60-90 Tage/Jahr Regen/Schnee bei -15-25% Geschwindigkeit), und autonomes Tempolimit-Verhalten (-8% ggü. menschlichen Fahrern, Waymo Phoenix Daten).",
        "deadhead": "Leerfahrten-Quote (%)",
        "help_deadhead": "Mature-State Leerfahrtenquote (J3+, nach Datenakkumulation). J1-J2 effektiv höher (28-32%) wegen Cold-Start-Routing; Engine mittelt dies implizit über 60-Monats-Horizont. Benchmark: Uber/Lyft etablierte europäische Märkte 18-22% laut Marketplace-Daten. Münchner kompakter Stadtkern unterstützt unteres Bandende.",
        "sec1c": "1c. AUSLASTUNGSDYNAMIK",
        "util_mode": "Auslastungsmodell",
        "util_dyn": "Dynamisch (Anlauf & Kannibalisierung)",
        "util_fix": "Fester Wert",
        "target_util": "Ziel-Auslastung (%)",
        "help_target": "Mature-State stationäre Auslastung. 75% spiegelt realistischen Nachfragebefüllungsgrad wider unter Berücksichtigung von: Werktag/Wochenend-Varianz, geografischen Nachfrageinseln (Schwabing/Maxvorstadt dicht, Pasing/Hadern dünn), unvermeidbaren Nachfragetiefs (Di-Do 10-12 Uhr). Waymo Phoenix J5 Auslastungsdaten: 72-78%.",
        "init_util": "Start-Auslastung Monat 1 (%)",
        "help_init": "Auslastung Monat 1. 35% reflektiert Markteinführungs-Ramp — nur Early Adopters, begrenzte Nachfragedichte, Markenbekanntheit im Aufbau. Konservativ ggü. Uber Münchner Launch-Kurve (die Fahrer-Netzwerkeffekte hatte, die Robotaxi nicht zur Verfügung stehen).",
        "rec_rate": "Monatliche Erholung (+%)",
        "help_rec": "Monatliche Auslastungs-Erholungsrate. 3%/Monat impliziert ~12-15 Monate von Start- zu Zielauslastung — entspricht Waymo Phoenix Ramp-Daten (San Francisco Launch benötigte 14 Monate für 70% Auslastung). Schnellere Erholungsraten setzen Marketing-/Netzwerkeffekte voraus, die frühe Robotaxi-Betreiber selten erreichen.",
        "can_fac": "Kannibalisierungsfaktor",
        "help_can": "Bestimmt den Auslastungseinbruch bei Neuzugängen.",
        "util_label": "Ø Auslastung",
        "sec2": "2. FAHRTDYNAMIK",
        "trip_dist": "Durchschnittliche Fahrstrecke (km)",
        "dwell": "Standzeit pro Fahrt (Minuten)",
        "help_dwell": "Gesamte unproduktive Zeit pro Fahrt: Einstieg 60-90s (App-Verifizierung, Tür öffnen, hinsetzen) + Ausstieg 60-90s (Sachen sammeln, Fahrt beenden) + KI-Bestätigung/Sensor-Check 15-30s. Waymo Phoenix Empirik 2,5-4 Min. Erste 18-24 Monate ggf. höher (4-5 Min); Basisfall: eingespielte Nutzer.",
        "sec3": "3. PREISGESTALTUNG (inkl. 19% USt)",
        "base_fare": "Grundgebühr (€)",
        "price_km": "Preis pro km (€)",
        "tesla_take": "Tesla Plattformgebühr (%)",
        "sec4": "4. TÄGLICHE VARIABLE KOSTEN (Netto)",
        "cleaning": "Reinigungskosten pro Fahrzeug/Tag (€)",
        "wear_rate": "Instandhaltung/Verschleiß pro km (€)",
        "wear_help": "Management-Sicht: nivellierter Verschleißsatz für 4-5j Scrap-Strategie (nach AfA-Schild). Aufschlüsselung: Reifen €0,027, Sensorwartung €0,034 (Cybercab Onboard-Reinigung reduziert ggü. Waymo-Benchmark), Innenraumverschleiß €0,012, Flüssigkeiten/Fahrwerk €0,005, HVAC/Inspektionen €0,005, Unfallrückstellung €0,008, Reserve €0,005. Benchmarks: Sixt+, Free Now, MOIA. Unter Waymo (€0,12-0,16) wegen einfacherem Cybercab-Sensorstack und deutschen Arbeitskosten.",
        "energy_rate": "Basis-Energiekosten pro km (€)",
        "energy_help": "Basisfall: 0,17 kWh/km Real-Verbrauch × €0,41/kWh Supercharger-Mischpreis ÷ 0,84 Ladewirkungsgrad = €0,085/km Netto-Basis. Saisonzuschläge dynamisch im Engine (Winter +45%, Übergang +30%, Hochsommer +10%). Benchmarks: Sixt Flottenbetriebskosten 2024.",
        "sec5": "5. FAHRZEUG-FIXKOSTEN (€ / Monat, Netto)",
        "insurance": "Kfz-Versicherung",
        "parking": "Münchner Stellplatz (APCOA Lade-Infrastruktur)",
        "telemetry": "Telemetrie & API",
        "tuev": "TÜV / BO-Kraft Rückstellung",
        "help_tuev": "Monatliche Rückstellung für die BO-Kraft Untersuchung.",
        "charging_sub": "Tesla Lade-Abo",
        "sec6": "6. CORPORATE HQ & REGULIERUNG (€ / Monat, Netto)",
        "hq_lease": "Raumkosten (HQ Lease)",
        "it_cloud": "IT, Cloud & AI Services",
        "base_legal": "Basis Rechts- & Beratungskosten",
        "base_hq_ins": "Basis Firmenversicherung (Haftpflicht)",
        "legal_scale": "Recht/StB Skalierung (pro zus. Fahrzeug)",
        "ins_scale": "Versicherung Skalierung (pro zus. Fahrzeug)",
        "bank_fees": "Bankgebühren",
        "ihk": "IHK Beitrag",
        "gez": "GEZ (Rundfunkbeitrag pro Fahrzeug)",
        "setup_costs": "Einmalige Gründungskosten (J1)",
        "sec7": "7. CAPEX & ANLAGENRISIKO-ABSCHREIBUNG",
        "base_price": "Basis Cybercab Preis (USD)",
        "fx": "Wechselkurs USD zu EUR",
        "freight": "Importfracht & Vers. pro Fahrzeug (€)",
        "duty": "Zollsatz (%)",
        "it_hw": "IT Hardware CapEx (J1)",
        "imp_trigger": "Tech-Impairment Monat (0=Keines)",
        "imp_pct": "Außerplanmäßige Abschreibung (§ 253 HGB) %",
        "sec8": "8. KAPITALSTRUKTUR & TREASURY-POLICIES",
        "stamm": "Stammkapital (€)",
        "sh_loan": "Gesellschafterdarlehen (Nachrangig) (€)",
        "sh_loan_rate": "Gesellschafterdarlehen Zins (%)",
        "help_sh_rate": "Marktüblicher Zins, den das Finanzamt verlangt, um verdeckte Gewinnausschüttungen (vGA) zu vermeiden.",
        "ltv": "Fremdkapitalquote Fahrzeuge (LTV) %",
        "help_ltv": "Prozentualer Anteil der finanzierten Anschaffungskosten.",
        "y1_loan_rate": "KfW Gründerkredit Zins (J1) %",
        "y2_loan_rate": "Kommerzielle Kfz-Finanzierung Zins (J2+) %",
        "vat_rate_input": "USt-Überbrückungskredit Zins (%)",
        "vat_lag_input": "USt-Erstattungsdauer (Monate)",
        "cash_buffer_input": "Mindest-Liquiditätsreserve (€)",
        "max_overdraft_input": "Max. Kontokorrentlinie (€)",
        "help_max_od": "Bankseitig genehmigte Linie. Übersteigt der Modellbedarf diese, wird INSOLVENZ angezeigt.",
        "legal_provision_input": "Monatliche Rechtsrisiko-Rückstellung (€) (§ 249 HGB)",
        "int_rate": "Guthabenzinsen (%)",
        "sec9": "9. SONSTIGE ERTRÄGE / RESTWERT",
        "thg": "THG-Quote pro Fahrzeug/Jahr",
        "help_thg": "Treibhausgasminderungsquote.",
        "salvage": "Fahrzeugverkaufspreis (Ende 5-J. Nutzungsdauer)",
        
        "pnl_gbv": "Bruttobuchungswert (Kunde zahlt inkl. 19% USt)",
        "pnl_vat": "Abzüglich: 19% Umsatzsteuer (Finanzamt)",
        "pnl_net_rev": "Umsatzerlöse (netto)",
        "pnl_tesla_fee": "Abzüglich: Tesla-Plattformgebühr (auf Netto)",
        "pnl_mrrg_net": "MRRG Nettoerlöse (nach Plattformgebühr)",
        "pnl_energy": "Abzüglich: Direkte Energiekosten (variabel, saisonal gewichtet)",
        "pnl_wear": "Abzüglich: Instandhaltung/Verschleiß (variabel)",
        "pnl_clean": "Abzüglich: Reinigungskosten (variabel)",
        "pnl_db1": "Deckungsbeitrag 1 (DB1)",
        "pnl_ins": "Abzüglich: Kfz-Versicherung (fix)",
        "pnl_park": "Abzüglich: APCOA Stellplätze (fix)",
        "pnl_api": "Abzüglich: Telemetrie & API (fix)",
        "pnl_tuev": "Abzüglich: TÜV / BO-Kraft (fix)",
        "pnl_sub": "Abzüglich: Tesla Lade-Abo (fix)",
        "pnl_db2": "Deckungsbeitrag 2 (DB2)",
        "pnl_hq_lease": "Abzüglich: Raumkosten (HQ Lease)",
        "pnl_it": "Abzüglich: IT, Cloud & AI Services",
        "pnl_legal": "Abzüglich: Rechts- & Beratungskosten (skaliert)",
        "pnl_hq_ins": "Abzüglich: Firmenversicherung (Haftpflicht, D&O - skaliert)",
        "pnl_fees": "Abzüglich: Beiträge & Gebühren (IHK, GEZ)",
        "pnl_bank": "Abzüglich: Bankgebühren",
        "pnl_legal_prov": "Abzüglich: Zuführung Rückstellung Rechtsrisiken (§ 249 HGB)",
        "pnl_thg": "Zuzüglich: THG-Quote (Sonstige betriebliche Erträge)",
        "pnl_ebitda": "EBITDA (Management View)",
        "pnl_ebitda_hgb": "EBITDA (HGB-Sicht, inkl. Anlagenabgang gem. § 275 II Nr.4 HGB)",
        "pnl_afa_veh": "Abzüglich: Abschreibung Fahrzeuge (AfA)",
        "pnl_afa_it": "Abzüglich: Abschreibung IT Hardware (AfA)",
        "pnl_salvage": "Zuzüglich: Flottenliquidation (Anlagenverkauf)",
        "pnl_ebit": "EBIT (Betriebsergebnis)",
        "pnl_int_inc": "Zuzüglich: Zinserträge",
        "pnl_int_exp": "Abzüglich: Zinsaufwendungen (Kredite & Überzug)",
        "pnl_ebt": "EBT (Ergebnis vor Steuern)",
        "pnl_tax": "Abzüglich: Ertragsteuern",
        "pnl_ni": "Periodenergebnis (Nettoergebnis)",
        
        "cf_ni": "+ Periodenergebnis",
        "cf_depr": "+ Abschreibungen (AfA inkl. Sonderabschreibung)",
        "cf_gain_sale": "- Buchgewinn aus Anlagenabgang",
        "cf_tax_prov": "+ Zunahme Steuerrückstellungen",
        "cf_tax_paid": "- Gezahlte Steuern (Vorausz. & Nachzahlung)",
        "cf_legal_prov": "+ Zuführung sonstiger Rückstellungen",
        "cf_wc_thg": "-/+ Veränderung THG-Forderungen (WC)",
        "cf_vat_coll": "+ Erhaltene Umsatzsteuer (laufender Betrieb)",
        "cf_vat_paid": "- Gezahlte USt (Netto-Zahllast & Lieferanten-Vorsteuer)",
        "cf_op": "Operativer Cashflow",
        "cf_capex": "- Auszahlungen Sachanlagen (CapEx inkl. USt)",
        "cf_vat_ref": "+ USt-Erstattung Finanzamt (auf CapEx)",
        "cf_sale": "+ Einzahlungen aus Anlagenabgängen",
        "cf_inv": "Cashflow aus Investitionstätigkeit",
        "cf_eq": "+ Einzahlungen Eigenkapital",
        "cf_sh": "+ Einzahlungen Gesellschafterdarlehen",
        "cf_kfw_draw": "+ Einzahlungen Fahrzeugdarlehen",
        "cf_prin": "- Tilgung Darlehen (inkl. Ballon)",
        "cf_vat_draw": "+ Einzahlungen USt-Überbrückungskredit",
        "cf_vat_repay": "- Tilgung USt-Überbrückungskredit",
        "cf_overdraft_delta": "+/- Netto-Veränderung Kontokorrentlinie",
        "cf_fin": "Cashflow aus Finanzierungstätigkeit",
        "cf_net": "Nettoveränderung Finanzmittel",
        "cf_beg": "+ Anfangsbestand Finanzmittel",
        "cf_end": "Endbestand Finanzmittel",
        
        "bs_gfa": "Brutto-Sachanlagen",
        "bs_acc_depr": "- Kumulierte Abschreibungen",
        "bs_nfa": "Netto-Sachanlagen (Anlagevermögen)",
        "bs_vat_rec": "Umsatzsteuerforderungen — CapEx-Brücke (Finanzamt)",
        "bs_vat_rec_op": "Umsatzsteuerforderungen — Vorsteuerüberhang Betrieb (Finanzamt)",
        "bs_thg_rec": "THG-Prämien Forderungen",
        "bs_tax_rec": "Steuerforderungen — Vorauszahlungs-Überhang (§ 246 II HGB Bruttoprinzip)",
        "bs_cash": "Kassenbestand / Bankguthaben",
        "bs_tca": "Summe Umlaufvermögen",
        "bs_ta": "SUMME AKTIVA",
        "bs_eq_share": "Gezeichnetes Kapital (Stammkapital)",
        "bs_eq_ret": "Gewinnvortrag / Periodenergebnis",
        "bs_teq": "Summe Eigenkapital",
        "bs_prov_tax": "Steuerrückstellungen",
        "bs_prov_legal": "Sonstige Rückstellungen (Rechtsrisiken)",
        "bs_tprov": "Summe Rückstellungen",
        "bs_debt_kfw": "Verbindlichkeiten ggü. Kreditinstituten",
        "bs_debt_vat": "Kurzfristige Verbindlichkeiten (USt-Kredit)",
        "bs_debt_overdraft": "Kurzfristige Bankverbindlichkeiten (Kontokorrent)",
        "bs_pay_vat": "Umsatzsteuer-Zahllast",
        "bs_sh_loan": "Gesellschafterdarlehen (Nachrangig)",
        "bs_tliab": "Summe Verbindlichkeiten",
        "bs_tleq": "SUMME PASSIVA",
        "bs_check": "BILANZKONTROLLE (Aktiva - Passiva)",

        # === TAB LABELS (RESTORED — these were missing and would KeyError) ===
        "tab_pnl": "Gewinn- und Verlustrechnung (GuV)",
        "tab_hgb_pnl": "Gesetzliche GuV (§ 275 HGB)",
        "tab_cf": "Kapitalflussrechnung",
        "tab_bs": "Bilanz",
        "tab_kpi": "KPIs & Kennzahlen",
        "tab_charts": "Visualisierungen & Dashboards",
        "tab_readme": "Handbuch & Dokumentation",

        "hgb_title": "Gesetzliche Gewinn- und Verlustrechnung (Gesamtkostenverfahren)",
        "hgb_pos1": "1. Umsatzerlöse",
        "hgb_pos2": "4. Sonstige betriebliche Erträge",
        "hgb_pos3": "5. Materialaufwand",
        "hgb_pos4": "6. Personalaufwand",
        "hgb_pos5": "7. Abschreibungen auf Sachanlagen",
        "hgb_pos6": "8. Sonstige betriebliche Aufwendungen",
        "hgb_pos7": "Finanzergebnis (Zinsertrag ./. Aufwand)",
        "hgb_pos8": "14. Steuern vom Einkommen und vom Ertrag",
        "hgb_pos9": "16. Periodenergebnis (Jahresüberschuss i.S.d. § 275 HGB bei Jahresansicht)",

        # === KPI LABELS (RESTORED — these were missing and would KeyError) ===
        "kpi_dscr": "Schuldendienstdeckungsgrad (DSCR)",
        "kpi_eq_ratio": "Eigenkapitalquote",
        "kpi_runway": "Liquiditätsreichweite (Monate)",
        "kpi_net_ltv": "Netto-LTV (Cash-bereinigt)",
        "kpi_var_ratio": "Variable Kostenquote",
        "kpi_fix_ratio": "Fixkostenquote",
        "kpi_tot_ratio": "Gesamtkostenquote",
        "kpi_other_inc_ratio": "Sonstige Ertragsquote (THG)",
        "kpi_db2_m": "Deckungsbeitragsmarge (DB2)",
        "kpi_ebitda_m": "EBITDA-Marge",

        "sources_title": "Tag 1 Mittelherkunft & Mittelverwendung",
        "src_stamm": "Mittelherkunft: Stammkapital",
        "src_sh": "Mittelherkunft: Gesellschafterdarlehen",
        "src_veh": "Mittelherkunft: Fahrzeugdarlehen",
        "liquidity": "Endbestand Kasse nach Monat 1 (Ist)",
        "output_title": "Master-Finanzpläne (HGB)",
        "active_fleet": "Aktive Flotte",
        "cars": "Fahrzeuge",
        "view_mode": "Darstellung",
        "yearly": "Jährlich",
        "monthly": "Monatlich (Detailansicht)",
        "exp_y1": "J1 Aufklappen",
        "exp_y2": "J2 Aufklappen",
        "exp_y3": "J3 Aufklappen",
        "exp_y4": "J4 Aufklappen",
        "exp_y5": "J5 Aufklappen",
        "glossary_title": "Erläuterungen der Kennzahlen & Methodik",
        "chart_rev": "Umsatzerlöse (Netto)",
        "chart_ebitda": "EBITDA",
        "chart_ni": "Jahresüberschuss",
        "chart_fleet": "Fahrzeugflotte (Jahresende)",
        "chart_fcf": "Free Cash Flow",
        "chart_ta": "Bilanzsumme (Aktiva)",
        "toggle_fcf": "Kumulierten FCF anzeigen",
        "cash_warn": "🚨 KRITISCH: Mindestliquidität unterschritten in Monat: ",
        "net_liq_warn": "⚠️  Netto-Liquidität negativ (Kasse − Kontokorrent < Mindestpuffer) in Monat: ",
        "insolv_warn": "💀 INSOLVENZ: Erforderlicher Liquiditätsbedarf übersteigt die genehmigte Kontokorrentlinie in Monat: ",
        "ebitda_recon_title": "EBITDA-Überleitung (Management-Sicht → HGB-Sicht)"
    }

# --- SIDEBAR INTERFACE CONTROLS ---
# UI Inputs defined first to prevent NameErrors in cache engine
st.sidebar.header(loc["sec1"])
y1_adds_str = st.sidebar.text_input(loc["y1_adds"], "3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0")
y2_adds_str = st.sidebar.text_input(loc["y2_adds"], "2, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0")
y3_adds_str = st.sidebar.text_input(loc["y3_adds"], "3, 0, 0, 3, 0, 0, 3, 0, 0, 3, 0, 0")
y4_adds_str = st.sidebar.text_input(loc["y4_adds"], "4, 0, 0, 4, 0, 0, 4, 0, 0, 3, 0, 0")
y5_adds_str = st.sidebar.text_input(loc["y5_adds"], "6, 0, 0, 5, 0, 0, 5, 0, 0, 5, 0, 0")

# L-04 FIX: Surface bad fleet input to the user (rather than silently zeroing out).
def _validate_fleet_str(label, s):
    try:
        arr = [int(x.strip()) for x in s.split(',')]
    except ValueError:
        st.sidebar.error(f"⚠️ {label}: invalid number(s) — parsed as zero fleet. Use comma-separated integers.")
        return
    if len(arr) != 12:
        st.sidebar.warning(f"ℹ️ {label}: expected 12 values, got {len(arr)}. Engine pads/truncates to 12.")
    if any(x < 0 for x in arr):
        st.sidebar.warning(f"ℹ️ {label}: negative additions detected — typically fleet additions are ≥ 0.")

for _label, _s in [(loc["y1_adds"], y1_adds_str), (loc["y2_adds"], y2_adds_str),
                   (loc["y3_adds"], y3_adds_str), (loc["y4_adds"], y4_adds_str),
                   (loc["y5_adds"], y5_adds_str)]:
    _validate_fleet_str(_label, _s)

st.sidebar.header(loc["sec1b"])
active_hours_per_day = st.sidebar.number_input(loc["active_hours"], value=13.5, help=loc["help_active_hours"])
avg_speed_kmh = st.sidebar.number_input(loc["speed"], value=19.0, help=loc["help_speed"])
deadhead_rate = st.sidebar.number_input(loc["deadhead"], value=22.0, help=loc["help_deadhead"]) / 100

st.sidebar.header(loc["sec1c"])
util_mode = st.sidebar.radio(loc["util_mode"], [loc["util_dyn"], loc["util_fix"]])
if util_mode == loc["util_dyn"]:
    target_util = st.sidebar.number_input(loc["target_util"], value=75.0, help=loc["help_target"]) / 100
    init_util = st.sidebar.number_input(loc["init_util"], value=35.0, help=loc["help_init"]) / 100
    rec_rate = st.sidebar.number_input(loc["rec_rate"], value=3.0, help=loc["help_rec"]) / 100
    can_fac = st.sidebar.number_input(loc["can_fac"], value=0.5, step=0.1, help=loc["help_can"])
    flat_util = target_util
else:
    flat_util = st.sidebar.number_input(loc["util_fix"], value=90.0) / 100
    target_util, init_util, rec_rate, can_fac = flat_util, flat_util, 0, 0

# === FIX 5 (Logic Bug 1): Compute is_dynamic boolean from localized radio selection ===
# This replaces the hardcoded English string comparison inside the function,
# which would silently fail in German mode.
is_dynamic = (util_mode == loc["util_dyn"])

st.sidebar.header(loc["sec2"])
avg_trip_distance_km = st.sidebar.number_input(loc["trip_dist"], value=5.0)
dwell_time_mins = st.sidebar.number_input(loc["dwell"], value=3.5, help=loc["help_dwell"])

st.sidebar.header(loc["sec3"])
base_fare_eur = st.sidebar.number_input(loc["base_fare"], value=2.50)
price_per_km_eur = st.sidebar.number_input(loc["price_km"], value=1.49)
tesla_take_rate = st.sidebar.number_input(loc["tesla_take"], value=25.0) / 100

st.sidebar.header(loc["sec4"])
cleaning_cost_per_day = st.sidebar.number_input(loc["cleaning"], value=3.00)
wear_and_tear_rate = st.sidebar.number_input(loc["wear_rate"], value=0.10, format="%.2f", step=0.01, help=loc["wear_help"])
energy_rate = st.sidebar.number_input(loc["energy_rate"], value=0.085, format="%.4f", step=0.0001, help=loc["energy_help"])

st.sidebar.header(loc["sec5"])
insurance_pm = st.sidebar.number_input(loc["insurance"], value=300.0)
parking_pm = st.sidebar.number_input(loc["parking"], value=250.0)
telemetry_pm = st.sidebar.number_input(loc["telemetry"], value=100.0)
tuev_pm = st.sidebar.number_input(loc["tuev"], value=15.0, help=loc["help_tuev"])
charging_sub_pm = st.sidebar.number_input(loc["charging_sub"], value=10.0)

st.sidebar.header(loc["sec6"])
hq_lease_pm = st.sidebar.number_input(loc["hq_lease"], value=450.0)
it_cloud_pm = st.sidebar.number_input(loc["it_cloud"], value=320.0)
legal_bookkeeping_pm = st.sidebar.number_input(loc["base_legal"], value=230.0)
hq_insurance_pm = st.sidebar.number_input(loc["base_hq_ins"], value=250.0)
legal_scaling_pm = st.sidebar.number_input(loc["legal_scale"], value=25.0)
insurance_scaling_pm = st.sidebar.number_input(loc["ins_scale"], value=40.0)
bank_fees_pm = st.sidebar.number_input(loc["bank_fees"], value=20.0)
ihk_pm = st.sidebar.number_input(loc["ihk"], value=35.0)
gez_pm_per_car = st.sidebar.number_input(loc["gez"], value=7.0)
setup_costs_y1 = st.sidebar.number_input(loc["setup_costs"], value=1700.0)

st.sidebar.header(loc["sec7"])
cybercab_base_usd = st.sidebar.number_input(loc["base_price"], value=30000.0)
usd_eur_rate = st.sidebar.number_input(loc["fx"], value=1.15)
import_freight_eur = st.sidebar.number_input(loc["freight"], value=1800.0)
customs_duty_rate = st.sidebar.number_input(loc["duty"], value=10.0) / 100
it_hardware_capex_y1 = st.sidebar.number_input(loc["it_hw"], value=2500.0)
imp_month = st.sidebar.number_input(loc["imp_trigger"], value=0, min_value=0, max_value=60)
imp_pct_val = st.sidebar.number_input(loc["imp_pct"], value=0.0, step=5.0) / 100

st.sidebar.header(loc["sec8"])
stammkapital = st.sidebar.number_input(loc["stamm"], value=25000.0)
shareholder_loan = st.sidebar.number_input(loc["sh_loan"], value=15000.0)
sh_loan_rate = st.sidebar.number_input(loc["sh_loan_rate"], value=5.0, step=0.1, help=loc["help_sh_rate"]) / 100
vehicle_ltv = st.sidebar.number_input(loc["ltv"], value=80.0, help=loc["help_ltv"]) / 100
y1_loan_rate = st.sidebar.number_input(loc["y1_loan_rate"], value=4.5, step=0.1) / 100
y2_loan_rate = st.sidebar.number_input(loc["y2_loan_rate"], value=5.5, step=0.1) / 100
vat_bridge_rate = st.sidebar.number_input(loc["vat_rate_input"], value=6.5, step=0.1) / 100
vat_lag_months = st.sidebar.number_input(loc["vat_lag_input"], value=3, min_value=1, max_value=12)
min_cash_buffer = st.sidebar.number_input(loc["cash_buffer_input"], value=10000.0, step=5000.0)
max_overdraft_limit = st.sidebar.number_input(loc["max_overdraft_input"], value=50000.0, step=10000.0, help=loc["help_max_od"])
legal_provision_rate = st.sidebar.number_input(loc["legal_provision_input"], value=200.0, step=50.0)
interest_income_rate = st.sidebar.number_input(loc["int_rate"], value=2.2) / 100

st.sidebar.header(loc["sec9"])
thg_quote_per_car_py = st.sidebar.number_input(loc["thg"], value=200.0, help=loc["help_thg"])
salvage_value_per_car_y4 = st.sidebar.number_input(loc["salvage"], value=10000.0)


# --- 5. COMPREHENSIVE COMPUTATIONAL ENGINE FUNCTION (CACHED) ---
@st.cache_data
def execute_financial_simulation(
    y1_adds_str, y2_adds_str, y3_adds_str, y4_adds_str, y5_adds_str,
    active_hours_per_day, avg_speed_kmh, deadhead_rate, util_mode,
    target_util, init_util, rec_rate, can_fac, flat_util, avg_trip_distance_km,
    dwell_time_mins, base_fare_eur, price_per_km_eur, tesla_take_rate,
    cleaning_cost_per_day, wear_and_tear_rate, energy_rate, insurance_pm,
    parking_pm, telemetry_pm, tuev_pm, charging_sub_pm, hq_lease_pm, it_cloud_pm,
    legal_bookkeeping_pm, hq_insurance_pm, legal_scaling_pm,
    insurance_scaling_pm, bank_fees_pm, ihk_pm, gez_pm_per_car, setup_costs_y1,
    cybercab_base_usd, usd_eur_rate, import_freight_eur, customs_duty_rate,
    it_hardware_capex_y1, imp_month, imp_pct_val, stammkapital, shareholder_loan,
    sh_loan_rate, vehicle_ltv, y1_loan_rate, y2_loan_rate, vat_bridge_rate,
    vat_lag_months, min_cash_buffer, legal_provision_rate, interest_income_rate,
    thg_quote_per_car_py, salvage_value_per_car_y4, max_overdraft_limit, is_dynamic, lang_choice
):
    # ============================================================
    # FIX 5 (Logic Bug 1): is_dynamic parameter added before lang_choice
    # Replaces the buggy hardcoded English string comparison that
    # silently failed in German mode and forced flat utilization.
    # ============================================================
    
    # Pure Static Keys to Prevent Variable Reference Errors in Cache Mapping
    P_GBV, P_VAT, P_NET, P_TFEE, P_MNET, P_EN, P_WR, P_CL, P_DB1, P_INS, P_PK, P_API, P_TV, P_SUB, P_DB2, P_HQ, P_IT, P_LEG, P_HINS, P_FEE, P_BNK, P_LPR, P_THG, P_EB, P_EB_HGB, P_AF_V, P_AF_I, P_SAL, P_EBIT, P_I_IN, P_I_EX, P_EBT, P_TX, P_NI = [
        "pnl_gbv", "pnl_vat", "pnl_net_rev", "pnl_tesla_fee", "pnl_mrrg_net", "pnl_energy", "pnl_wear", "pnl_clean", "pnl_db1", "pnl_ins", "pnl_park",
        "pnl_api", "pnl_tuev", "pnl_sub", "pnl_db2", "pnl_hq_lease", "pnl_it", "pnl_legal", "pnl_hq_ins", "pnl_fees", "pnl_bank", "pnl_legal_prov", "pnl_thg",
        "pnl_ebitda", "pnl_ebitda_hgb", "pnl_afa_veh", "pnl_afa_it", "pnl_salvage", "pnl_ebit", "pnl_int_inc", "pnl_int_exp", "pnl_ebt", "pnl_tax", "pnl_ni"
    ]

    C_NI, C_DP, C_GS, C_TP, C_TPD, C_LPR, C_WCT, C_VCOL, C_VPD, C_OP, C_CAP, C_VRF, C_SLE, C_INV, C_EQ, C_SH, C_KFW, C_PRN, C_VDR, C_VRP, C_OD, C_FIN, C_NET, C_BEG, C_END = [
        "cf_ni", "cf_depr", "cf_gain_sale", "cf_tax_prov", "cf_tax_paid", "cf_legal_prov", "cf_wc_thg", "cf_vat_coll", "cf_vat_paid", "cf_op",
        "cf_capex", "cf_vat_ref", "cf_sale", "cf_inv", "cf_eq", "cf_sh", "cf_kfw_draw", "cf_prin", "cf_vat_draw", "cf_vat_repay", "cf_overdraft_delta",
        "cf_fin", "cf_net", "cf_beg", "cf_end"
    ]

    B_GF, B_AD, B_NF, B_VR, B_OPVRX, B_TR, B_TRX, B_CS, B_TC, B_TA, B_ES, B_ER, B_TEQ, B_PT, B_PL, B_TPV, B_DK, B_DV, B_DO, B_PV, B_SL, B_TL, B_TLEQ, B_CH = [
        "bs_gfa", "bs_acc_depr", "bs_nfa", "bs_vat_rec", "bs_vat_rec_op", "bs_thg_rec", "bs_tax_rec", "bs_cash", "bs_tca", "bs_ta", "bs_eq_share", "bs_eq_ret", "bs_teq",
        "bs_prov_tax", "bs_prov_legal", "bs_tprov", "bs_debt_kfw", "bs_debt_vat", "bs_debt_overdraft", "bs_pay_vat", "bs_sh_loan", "bs_tliab", "bs_tleq", "bs_check"
    ]
    bs_keys_internal = [B_GF, B_AD, B_NF, B_VR, B_OPVRX, B_TR, B_TRX, B_CS, B_TC, B_TA, B_ES, B_ER, B_TEQ, B_PT, B_PL, B_TPV, B_DK, B_DV, B_DO, B_PV, B_SL, B_TL, B_TLEQ, B_CH]

    def parse_adds(add_str):
        try:
            arr = [int(x.strip()) for x in add_str.split(',')]
            return (arr + [0]*12)[:12]
        except:
            return [0]*12

    all_adds = parse_adds(y1_adds_str) + parse_adds(y2_adds_str) + parse_adds(y3_adds_str) + parse_adds(y4_adds_str) + parse_adds(y5_adds_str)
    # === FIX 1 (Crash 1): base_fleet_size restored inside cached function scope ===
    base_fleet_size = sum(parse_adds(y1_adds_str))
    
    cybercab_base_eur = cybercab_base_usd / usd_eur_rate
    zollwert_cif_eur = cybercab_base_eur + import_freight_eur
    zollkosten_eur = zollwert_cif_eur * customs_duty_rate
    total_capex_per_car = zollwert_cif_eur + zollkosten_eur

    cohorts = []
    for m in range(60):
        mo_val = all_adds[m]
        if mo_val > 0:
            capex = mo_val * total_capex_per_car
            loan = capex * vehicle_ltv
            rate = y1_loan_rate if m < 12 else y2_loan_rate
            
            monthly_rate = rate / 12
            if monthly_rate > 0:
                pmt = loan * (monthly_rate * (1 + monthly_rate)**VEHICLE_AMORTIZATION_PERIOD) / ((1 + monthly_rate)**VEHICLE_AMORTIZATION_PERIOD - 1)
            else:
                pmt = loan / VEHICLE_AMORTIZATION_PERIOD
                
            cohorts.append({
                "start_month": m + 1,
                "size": mo_val,
                "capex": capex,
                "original_loan": loan,
                "loan_bal": loan,
                "rate": rate,
                "pmt": pmt,
                "afa_per_mo": capex / VEHICLE_AMORTIZATION_PERIOD,
                "accum_afa": 0,
                "impaired": False
            })

    # Trip Physics Mathematics Canvas
    max_theoretical_km = active_hours_per_day * avg_speed_kmh
    theoretical_deadhead_km = max_theoretical_km * deadhead_rate
    max_billable_km_theoretical = max_theoretical_km - theoretical_deadhead_km
    distance_lost_per_dwell_km = (avg_speed_kmh / 60.0) * dwell_time_mins
    effective_trip_distance_km = avg_trip_distance_km + distance_lost_per_dwell_km

    actual_trips_per_day = np.floor(max_billable_km_theoretical / effective_trip_distance_km)
    actual_billable_km_per_day = actual_trips_per_day * avg_trip_distance_km
    actual_total_km_per_day = actual_billable_km_per_day / (1.0 - deadhead_rate)

    base_fare_rev_per_day_gross = actual_trips_per_day * base_fare_eur
    distance_rev_per_day_gross = actual_billable_km_per_day * price_per_km_eur
    gross_booking_value_per_day_per_car = base_fare_rev_per_day_gross + distance_rev_per_day_gross

    pnl_m = {k: [] for k in [P_GBV, P_VAT, P_NET, P_TFEE, P_MNET, P_EN, P_WR, P_CL, P_DB1, P_INS, P_PK, P_API, P_TV, P_SUB, P_DB2, P_HQ, P_IT, P_LEG, P_HINS, P_FEE, P_BNK, P_LPR, P_THG, P_EB, P_EB_HGB, P_AF_V, P_AF_I, P_SAL, P_EBIT, P_I_IN, P_I_EX, P_EBT, P_TX, P_NI]}
    cf_m = {k: [] for k in [C_NI, C_DP, C_GS, C_TP, C_TPD, C_LPR, C_WCT, C_VCOL, C_VPD, C_OP, C_CAP, C_VRF, C_SLE, C_INV, C_EQ, C_SH, C_KFW, C_PRN, C_VDR, C_VRP, C_OD, C_FIN, C_NET, C_BEG, C_END]}
    bs_m = {k: [] for k in [B_GF, B_AD, B_NF, B_VR, B_OPVRX, B_TR, B_TRX, B_CS, B_TC, B_TA, B_ES, B_ER, B_TEQ, B_PT, B_PL, B_TPV, B_DK, B_DV, B_DO, B_PV, B_SL, B_TL, B_TLEQ, B_CH]}

    tax_schedule = {1: 0.23520, 2: 0.22465, 3: 0.21410, 4: 0.20355, 5: 0.19300}

    # State Loops Configuration
    current_cash = 0.0
    vat_loan_bal = 0.0
    overdraft_facility_bal = 0.0
    operational_vat_payable = 0.0
    vat_receivable = 0.0
    thg_receivable = 0.0
    tax_provision_bal = 0.0
    legal_provision_bal = 0.0
    
    prior_year_tax_actual = 0.0
    current_year_tax_accrued = 0.0
    prepayments_made_this_year = 0.0
    true_up_due_this_m5 = 0.0
    
    cum_gfa = 0.0
    cum_depr = 0.0
    cum_net_income = 0.0

    vat_repay_schedule = [0.0]*120 
    active_fleet_by_month = []
    utilization_by_month = []
    month_col_names = []
    cash_breach_months = []
    # H-01 / H-02: Distinct liquidity-stress signals
    net_liq_breach_months = []   # Cash − Overdraft < min_buffer (going concern stress)
    insolvency_months = []       # Required draw exceeds bank-approved ceiling

    # === FIX 5 STEP A (Logic Bug 1): use is_dynamic flag instead of hardcoded English string ===
    current_u = init_util if is_dynamic else flat_util
    prev_fleet = 0

    m_names_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    m_names_de = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
    m_names = m_names_en if lang_choice == "English" else m_names_de

    for m in range(60):
        current_month = m + 1
        current_year_cal = 2028 + (m // 12)
        current_month_index = (m % 12) + 1
        current_year = (m // 12) + 1
        
        # === FIX 4 (Logic Bug 2): Save beginning cash BEFORE any mutations.
        # Without this, when the overdraft draws and resets current_cash to 0.0,
        # the CF statement records beg_cash = 0 instead of the actual prior period balance. ===
        beg_cash = current_cash
        
        month_col_names.append(f"{m_names[current_month_index-1]} '{str(current_year_cal)[-2:]}")
        days_in_mo = calendar.monthrange(current_year_cal, current_month_index)[1]
        
        # ============================================================
        # === LAYER 20 CHANGE 1b: 4-tier seasonality (replaces 3-tier) ===
        # Empirical basis:
        #   - Winter (Dec-Feb) 1.45×: ADAC Wintertest 2023 shows +35-55% EV
        #     consumption at sustained sub-zero ambient. Munich Dec-Feb avg
        #     low -3 to -5°C. Robotaxis cannot pre-condition while plugged.
        #   - Shoulder (Nov, Mar) 1.30×: partial battery thermal load.
        #   - Cool summer (Apr, Oct) 1.05×: minimal HVAC load.
        #   - Hot summer (May-Sep) 1.10×: A/C draw 8-15% per Geotab fleet
        #     data; Munich has multi-week heat waves (2018, 2022, 2023, 2024).
        # Annual blend (unweighted): (3×1.45 + 2×1.30 + 2×1.05 + 5×1.10)/12 = 1.2125
        # Day-weighted blend (Munich calendar): 1.2114
        # Note: Earlier scoping referenced 1.19× as the target; the multipliers
        # themselves are empirically primary, so the engine implements the
        # multipliers as specified and the realized blend is 1.2125×.
        # ============================================================
        if current_month_index in [12, 1, 2]:
            season_mult = 1.45
        elif current_month_index in [11, 3]:
            season_mult = 1.30
        elif current_month_index in [4, 10]:
            season_mult = 1.05
        else:  # May-Sep
            season_mult = 1.10
            
        active_fleet = 0
        current_veh_afa = 0
        fleet_sale_rev = 0
        int_exp = 0
        prin_pay = 0
        kfw_draw = 0
        capex_this_mo = 0
        capex_sold_this_mo = 0
        accum_afa_sold_this_mo = 0
        
        for c in cohorts:
            c_start = c["start_month"]
            if current_month == c_start:
                kfw_draw += c["original_loan"]
                capex_this_mo += c["capex"]
                
            if current_month >= c_start and current_month < c_start + VEHICLE_AMORTIZATION_PERIOD:
                active_fleet += c["size"]
                int_for_this_loan = c["loan_bal"] * (c["rate"] / 12)
                int_exp += int_for_this_loan
                
                # F-26 Extraordinary HGB Impairment Logic Implementation
                if current_month == imp_month and not c["impaired"]:
                    extra_afa = c["loan_bal"] * imp_pct_val if c["loan_bal"] > 0 else c["capex"] * imp_pct_val
                    current_veh_afa += extra_afa
                    c["accum_afa"] += extra_afa
                    c["impaired"] = True
                
                current_veh_afa += c["afa_per_mo"]
                c["accum_afa"] += c["afa_per_mo"]
                
                if current_month >= c_start + 12:
                    prin = c["pmt"] - int_for_this_loan
                    if c["loan_bal"] - prin < 0: prin = c["loan_bal"]
                    prin_pay += prin
                    c["loan_bal"] -= prin
                    
            if current_month == c_start + VEHICLE_AMORTIZATION_PERIOD:
                fleet_sale_rev += c["size"] * salvage_value_per_car_y4
                capex_sold_this_mo += c["capex"]
                accum_afa_sold_this_mo += c["accum_afa"]
                prin_pay += c["loan_bal"]
                c["loan_bal"] = 0
                c["accum_afa"] = 0

        # === FIX 5 STEP B (Logic Bug 1): use is_dynamic flag for cannibalization branch ===
        if is_dynamic:
            if active_fleet > prev_fleet and prev_fleet > 0:
                supply_shock = (active_fleet - prev_fleet) / active_fleet
                current_u -= (supply_shock * can_fac)
                current_u = max(current_u, 0.20)
            elif active_fleet <= prev_fleet and prev_fleet > 0:
                current_u = min(target_util, current_u + rec_rate)
        else:
            current_u = flat_util
            
        op_days = days_in_mo * current_u
        utilization_by_month.append(current_u)
        prev_fleet = active_fleet
        active_fleet_by_month.append(active_fleet)
        
        if current_month == 1: capex_this_mo += it_hardware_capex_y1
        current_it_afa = (it_hardware_capex_y1 / IT_AMORTIZATION_PERIOD) if current_month <= IT_AMORTIZATION_PERIOD else 0
        total_afa_this_mo = current_veh_afa + current_it_afa
        
        gbv_mo = gross_booking_value_per_day_per_car * op_days * active_fleet
        net_rev_mo = gbv_mo / (1.0 + VAT_RATE)
        vat_owed_mo = gbv_mo - net_rev_mo
        # F-07 Net Revenue Correction: Platform take fee maps off Net instead of Gross
        tesla_fee_mo = net_rev_mo * tesla_take_rate
        mrrg_net_mo = net_rev_mo - tesla_fee_mo
        
        total_km_mo = actual_total_km_per_day * op_days * active_fleet
        wear_mo = total_km_mo * wear_and_tear_rate
        energy_mo = total_km_mo * (energy_rate * season_mult)
        clean_mo = cleaning_cost_per_day * days_in_mo * active_fleet
        db1_mo = mrrg_net_mo - wear_mo - energy_mo - clean_mo
        
        ins_mo = insurance_pm * active_fleet
        park_mo = parking_pm * active_fleet
        tel_mo = telemetry_pm * active_fleet
        tuev_mo = tuev_pm * active_fleet
        sub_mo = charging_sub_pm * active_fleet
        db2_mo = db1_mo - (ins_mo + park_mo + tel_mo + tuev_mo + sub_mo)
        
        add_cars = max(0, active_fleet - base_fleet_size)
        hq_lease_mo = hq_lease_pm
        it_cloud_mo = it_cloud_pm
        legal_mo = legal_bookkeeping_pm + (legal_scaling_pm * add_cars) + (setup_costs_y1 if current_month == 1 else 0)
        hq_ins_mo = hq_insurance_pm + (insurance_scaling_pm * add_cars)
        fees_mo = ihk_pm + (gez_pm_per_car * active_fleet)
        
        # ============================================================
        # === LAYER 17 FEATURE A: OpEx Input VAT (Vorsteuerabzug) ====
        # Under German UStG, input VAT on eligible operating expenses
        # is deductible against output VAT. Vendors are paid GROSS;
        # the 19% VAT portion offsets the monthly Umsatzsteuerzahllast.
        #
        # VAT-Eligible OpEx (services charging 19% USt):
        #   energy, wear, clean, park, telemetry, TÜV, charging sub,
        #   HQ lease, IT/cloud, legal/bookkeeping
        #
        # VAT-Exempt OpEx (per UStG):
        #   - Insurance: § 4 Nr. 10 UStG
        #   - HQ Insurance: § 4 Nr. 10 UStG
        #   - Bank fees: § 4 Nr. 8 UStG
        #   - IHK contributions: Mitgliedsbeitrag (no VAT)
        #   - GEZ broadcast fee: öffentliche Abgabe (no VAT)
        # ============================================================
        vat_eligible_opex_mo = (energy_mo + wear_mo + clean_mo + park_mo
                                + tel_mo + tuev_mo + sub_mo + hq_lease_mo
                                + it_cloud_mo + legal_mo)
        opex_input_vat_mo = vat_eligible_opex_mo * VAT_RATE
        # P&L impact: ZERO (P&L always books net of VAT — Feature A invariant)
        # CF impact: -opex_input_vat_mo (vendors paid gross this month)
        # BS impact: operational_vat_payable netted by -opex_input_vat_mo below
        
        # F-18 Fix Applied: Realisationsprinzip Accrual mapping
        thg_rev_mo = (thg_quote_per_car_py / 12) * active_fleet
        thg_receivable += thg_rev_mo
        thg_cash_mo = 0.0
        if current_month % 3 == 0:
            thg_cash_mo = thg_receivable
            thg_receivable = 0.0
        thg_wc_delta = thg_cash_mo - thg_rev_mo
        
        # F-36 Risk Provisions allocation (§ 249 HGB)
        legal_provision_mo = legal_provision_rate if active_fleet > 0 else 0.0
        legal_provision_bal += legal_provision_mo
        
        # F-01 Fix Applied: Capital gains stripped cleanly from operational cash line
        ebitda_mo = db2_mo - hq_lease_mo - it_cloud_mo - legal_mo - hq_ins_mo - fees_mo - bank_fees_pm + thg_rev_mo - legal_provision_mo
        ebit_mo = ebitda_mo - total_afa_this_mo + fleet_sale_rev
        
        # === M-03 FIX (supersedes F-25) ===
        # Interest income accrues on Beginning-of-Period cash balance.
        # Rationale: F-25's projected_mid hack used only capex/financing flows,
        # excluding operating CF, which materially under-estimated interest
        # in profitable years (Y4-5 with €3M+ cash). BoP basis is conservative,
        # standard treasury practice, free of circularity, and rigorously
        # defensible to bank credit committees.
        int_inc_mo = beg_cash * (interest_income_rate / 12.0) if beg_cash > 0 else 0.0
        sh_int_mo = shareholder_loan * (sh_loan_rate / 12.0)
        int_exp += sh_int_mo
        
        vat_draw_mo = capex_this_mo * VAT_RATE
        vat_loan_bal += vat_draw_mo
        vat_repay_schedule[current_month + vat_lag_months] += vat_draw_mo
        
        vat_refund_inflow = vat_repay_schedule[current_month]
        # M-05 FIX: Defensive cap — vat_repay cannot exceed outstanding bridge loan.
        # Excess refund still flows through inv_cf_mo as a real cash inflow.
        vat_repay_mo = min(vat_refund_inflow, vat_loan_bal)
        vat_loan_bal -= vat_repay_mo
        vat_int_mo = vat_loan_bal * (vat_bridge_rate / 12.0)
        int_exp += vat_int_mo
        
        if overdraft_facility_bal > 0:
            int_exp += overdraft_facility_bal * (OVERDRAFT_ANNUAL_RATE / 12.0)
            
        ebt_mo = ebit_mo + int_inc_mo - int_exp
        
        # Monthly HGB tax provision accruals (F-04 / F-16 fixed matrix)
        tax_exp_mo = max(0.0, ebt_mo) * tax_schedule[current_year]
        current_year_tax_accrued += tax_exp_mo
        
        tax_paid_mo = 0.0
        if current_month_index == 5:
            tax_paid_mo += true_up_due_this_m5
            true_up_due_this_m5 = 0.0
            
        # F-08 Compliance Calendar Loop
        if current_year > 1:
            if current_month_index in [3, 6, 9, 12]:
                payment = prior_year_tax_actual * 0.50 * 0.25
                tax_paid_mo += payment
                prepayments_made_this_year += payment
            if current_month_index in [2, 5, 8, 11]:
                payment = prior_year_tax_actual * 0.50 * 0.25
                tax_paid_mo += payment
                prepayments_made_this_year += payment
                
        if current_month % 12 == 0:
            true_up_due_this_m5 = current_year_tax_accrued - prepayments_made_this_year
            prior_year_tax_actual = current_year_tax_accrued
            current_year_tax_accrued = 0.0
            prepayments_made_this_year = 0.0

        net_inc_mo = ebt_mo - tax_exp_mo
        
        # F-23 Short-Term Overdraft Linkage Mechanics
        op_vat_collected = vat_owed_mo
        # === LAYER 17 FEATURE A: VAT cash flow ===
        # op_vat_paid = prior month's NETTED payable being remitted to Finanzamt
        # opex_input_vat_mo = vendors paid gross THIS month (separate cash drain)
        # Combine both into op_vat_paid_total for the CF statement.
        op_vat_paid = -operational_vat_payable
        op_vat_paid_total = op_vat_paid - opex_input_vat_mo
        
        op_cf_mo = net_inc_mo + total_afa_this_mo - fleet_sale_rev + tax_exp_mo - tax_paid_mo + thg_wc_delta + op_vat_collected + op_vat_paid_total + legal_provision_mo
        inv_cf_mo = -(capex_this_mo + vat_draw_mo) + vat_refund_inflow + fleet_sale_rev
        fin_cf_mo_excl_od = (stammkapital if current_month == 1 else 0.0) + (shareholder_loan if current_month == 1 else 0.0) + kfw_draw - prin_pay + vat_draw_mo - vat_repay_mo
        
        net_before_overdraft = op_cf_mo + inv_cf_mo + fin_cf_mo_excl_od
        tentative_ending_cash = current_cash + net_before_overdraft
        
        # =====================================================================
        # === H-01 + H-02 FIX: Capped Overdraft + Insolvency Detection ========
        # Overdraft draws are now capped at max_overdraft_limit (bank Linie).
        # If shortfall exceeds available headroom → INSOLVENCY flagged but
        # overdraft is still drawn to the cap (engine continues for visibility).
        # =====================================================================
        overdraft_net_flow = 0.0
        if tentative_ending_cash < 0:
            needed_from_od = -tentative_ending_cash
            available_od_headroom = max(0.0, max_overdraft_limit - overdraft_facility_bal)
            actual_od_draw = min(needed_from_od, available_od_headroom)
            if needed_from_od > available_od_headroom:
                # Shortfall exceeds approved line → INSOLVENZ-Antragspflicht territory
                insolvency_months.append(month_col_names[-1])
            overdraft_net_flow = actual_od_draw
            overdraft_facility_bal += actual_od_draw
            current_cash = tentative_ending_cash + actual_od_draw  # may still be negative if insolvent
        else:
            if overdraft_facility_bal > 0:
                repay_amt = min(tentative_ending_cash, overdraft_facility_bal)
                overdraft_net_flow = -repay_amt
                overdraft_facility_bal -= repay_amt
                current_cash = tentative_ending_cash - repay_amt
            else:
                current_cash = tentative_ending_cash
                
        # H-01 FIX: Dual-track liquidity-stress signals
        # (a) Raw cash floor: traditional "do we have €X on hand?"
        if current_cash < min_cash_buffer and active_fleet > 0:
            cash_breach_months.append(month_col_names[-1])
        # (b) Net liquidity (cash − overdraft): "are we net positive after debt?"
        #     This is what bank credit committee computes — Effektive Liquidität.
        effective_cash = current_cash - overdraft_facility_bal
        if effective_cash < min_cash_buffer and active_fleet > 0:
            net_liq_breach_months.append(month_col_names[-1])

        # === FIX 2 (Crash 2): Define eq_in and sh_in BEFORE the CF appends section ===
        eq_in = stammkapital if current_month == 1 else 0.0
        sh_in = shareholder_loan if current_month == 1 else 0.0

        # Commit State Adjustments to Objects
        cum_gfa += capex_this_mo - capex_sold_this_mo
        cum_depr += total_afa_this_mo - accum_afa_sold_this_mo 
        nfa = cum_gfa - cum_depr
        vat_receivable += vat_draw_mo - vat_refund_inflow
        # === LAYER 17 FEATURE A: NET VAT Payable ===
        # operational_vat_payable = Output VAT − OpEx Input VAT (Vorsteuer offset)
        # The cash drain to vendors (-opex_input_vat_mo above) exactly offsets
        # this -opex_input_vat_mo reduction in the payable. BS stays balanced.
        # Note: this is the INTERNAL signed state — may be negative when input VAT
        # exceeds output VAT. Gross BS presentation handled below (M-01).
        operational_vat_payable = op_vat_collected - opex_input_vat_mo
        tax_provision_bal += tax_exp_mo - tax_paid_mo
        cum_net_income += net_inc_mo
        
        kfw_loan_bal = sum(c["loan_bal"] for c in cohorts if current_month >= c["start_month"])
        
        # =====================================================================
        # === M-01 FIX: Gross BS presentation for operational VAT position ===
        # Internal state `operational_vat_payable` carries the signed net
        # (can be negative when Vorsteuerüberhang exists). For BS reporting,
        # § 246 III HGB Bruttoprinzip requires gross presentation: split into
        # a payable (liability, ≥ 0) and a receivable (asset, ≥ 0).
        # === M-02 FIX: Same pattern for tax_provision_bal — when prepayments
        # exceed accrual (e.g., declining-profit year), a Steuerforderung exists.
        # =====================================================================
        op_vat_payable_bs = max(0.0, operational_vat_payable)       # liability
        op_vat_receivable_bs = max(0.0, -operational_vat_payable)   # asset
        tax_provision_bs = max(0.0, tax_provision_bal)              # liability
        tax_receivable_bs = max(0.0, -tax_provision_bal)            # asset
        
        total_assets = nfa + vat_receivable + op_vat_receivable_bs + thg_receivable + tax_receivable_bs + current_cash
        total_equity = stammkapital + cum_net_income
        total_prov = tax_provision_bs + legal_provision_bal
        total_liab_bal = kfw_loan_bal + vat_loan_bal + overdraft_facility_bal + op_vat_payable_bs + shareholder_loan
        total_liab_eq = total_equity + total_prov + total_liab_bal
        bs_check_val = round(total_assets - total_liab_eq, STANDARD_TAX_ROUNDING)
        
        # Append Metrics out cleanly to insulated dictionaries
        pnl_m[P_GBV].append(gbv_mo)
        pnl_m[P_VAT].append(-vat_owed_mo)
        pnl_m[P_NET].append(net_rev_mo)
        pnl_m[P_TFEE].append(-tesla_fee_mo)
        pnl_m[P_MNET].append(mrrg_net_mo)
        pnl_m[P_EN].append(-energy_mo)
        pnl_m[P_WR].append(-wear_mo)
        pnl_m[P_CL].append(-clean_mo)
        pnl_m[P_DB1].append(db1_mo)
        pnl_m[P_INS].append(-ins_mo)
        pnl_m[P_PK].append(-park_mo)
        pnl_m[P_API].append(-tel_mo)
        pnl_m[P_TV].append(-tuev_mo)
        pnl_m[P_SUB].append(-sub_mo)
        pnl_m[P_DB2].append(db2_mo)
        pnl_m[P_HQ].append(-hq_lease_mo)
        pnl_m[P_IT].append(-it_cloud_mo)
        pnl_m[P_LEG].append(-legal_mo)
        pnl_m[P_HINS].append(-hq_ins_mo)
        pnl_m[P_FEE].append(-fees_mo)
        pnl_m[P_BNK].append(-bank_fees_pm)
        pnl_m[P_LPR].append(-legal_provision_mo)
        pnl_m[P_THG].append(thg_rev_mo)
        pnl_m[P_EB].append(ebitda_mo)
        # H-07 FIX: HGB-view EBITDA = Mgmt EBITDA + Anlagenabgang (per § 275 II Nr.4 HGB)
        pnl_m[P_EB_HGB].append(ebitda_mo + fleet_sale_rev)
        pnl_m[P_AF_V].append(-current_veh_afa)
        pnl_m[P_AF_I].append(-current_it_afa)
        pnl_m[P_SAL].append(fleet_sale_rev)
        pnl_m[P_EBIT].append(ebit_mo)
        pnl_m[P_I_IN].append(int_inc_mo)
        pnl_m[P_I_EX].append(-int_exp)
        pnl_m[P_EBT].append(ebt_mo)
        pnl_m[P_TX].append(-tax_exp_mo)
        pnl_m[P_NI].append(net_inc_mo)

        cf_m[C_NI].append(net_inc_mo)
        cf_m[C_DP].append(total_afa_this_mo)
        cf_m[C_GS].append(-fleet_sale_rev)
        cf_m[C_TP].append(tax_exp_mo)
        cf_m[C_TPD].append(-tax_paid_mo)
        cf_m[C_LPR].append(legal_provision_mo)
        cf_m[C_WCT].append(thg_wc_delta)
        cf_m[C_VCOL].append(op_vat_collected)
        cf_m[C_VPD].append(op_vat_paid_total)
        cf_m[C_OP].append(op_cf_mo)
        cf_m[C_CAP].append(-(capex_this_mo + vat_draw_mo))
        cf_m[C_VRF].append(vat_refund_inflow)
        cf_m[C_SLE].append(fleet_sale_rev)
        cf_m[C_INV].append(inv_cf_mo)
        cf_m[C_EQ].append(eq_in)
        cf_m[C_SH].append(sh_in)
        cf_m[C_KFW].append(kfw_draw)
        cf_m[C_PRN].append(-prin_pay)
        cf_m[C_VDR].append(vat_draw_mo)
        cf_m[C_VRP].append(-vat_repay_mo)
        cf_m[C_OD].append(overdraft_net_flow)
        cf_m[C_FIN].append(fin_cf_mo_excl_od + overdraft_net_flow)
        cf_m[C_NET].append(net_before_overdraft + overdraft_net_flow)
        # === FIX 4 (Logic Bug 2): Use beg_cash saved at top of loop ===
        cf_m[C_BEG].append(beg_cash)
        cf_m[C_END].append(current_cash)

        bs_m[B_GF].append(cum_gfa)
        bs_m[B_AD].append(-cum_depr)
        bs_m[B_NF].append(nfa)
        bs_m[B_VR].append(vat_receivable)
        bs_m[B_OPVRX].append(op_vat_receivable_bs)          # M-01: gross asset side
        bs_m[B_TR].append(thg_receivable)
        bs_m[B_TRX].append(tax_receivable_bs)               # M-02: gross asset side
        bs_m[B_CS].append(current_cash)
        bs_m[B_TC].append(vat_receivable + op_vat_receivable_bs + thg_receivable + tax_receivable_bs + current_cash)
        bs_m[B_TA].append(total_assets)
        bs_m[B_ES].append(stammkapital)
        bs_m[B_ER].append(cum_net_income)
        bs_m[B_TEQ].append(total_equity)
        bs_m[B_PT].append(tax_provision_bs)                 # M-02: gross liability side (≥ 0)
        bs_m[B_PL].append(legal_provision_bal)
        bs_m[B_TPV].append(total_prov)
        bs_m[B_DK].append(kfw_loan_bal)
        bs_m[B_DV].append(vat_loan_bal)
        bs_m[B_DO].append(overdraft_facility_bal)
        bs_m[B_PV].append(op_vat_payable_bs)                # M-01: gross liability side (≥ 0)
        bs_m[B_SL].append(shareholder_loan)
        bs_m[B_TL].append(total_liab_bal)
        bs_m[B_TLEQ].append(total_liab_eq)
        bs_m[B_CH].append(bs_check_val)

    return pnl_m, cf_m, bs_m, month_col_names, cash_breach_months, net_liq_breach_months, insolvency_months, active_fleet_by_month, utilization_by_month, total_capex_per_car, bs_keys_internal

# --- EXECUTING COMPUTER MATRIX WITH SAFELY WRAPPED ISOLATION LOGIC ---
# === FIX 5 STEP D (Logic Bug 1): is_dynamic passed as positional arg before lang_choice ===
pnl_monthly, cf_monthly, bs_monthly, month_col_names, cash_breach_months, net_liq_breach_months, insolvency_months, active_fleet_by_month, utilization_by_month, total_capex_per_car, bs_keys_isolated = execute_financial_simulation(
    y1_adds_str, y2_adds_str, y3_adds_str, y4_adds_str, y5_adds_str,
    active_hours_per_day, avg_speed_kmh, deadhead_rate, util_mode,
    target_util, init_util, rec_rate, can_fac, flat_util, avg_trip_distance_km,
    dwell_time_mins, base_fare_eur, price_per_km_eur, tesla_take_rate,
    cleaning_cost_per_day, wear_and_tear_rate, energy_rate, insurance_pm,
    parking_pm, telemetry_pm, tuev_pm, charging_sub_pm, hq_lease_pm, it_cloud_pm,
    legal_bookkeeping_pm, hq_insurance_pm, legal_scaling_pm,
    insurance_scaling_pm, bank_fees_pm, ihk_pm, gez_pm_per_car, setup_costs_y1,
    cybercab_base_usd, usd_eur_rate, import_freight_eur, customs_duty_rate,
    it_hardware_capex_y1, imp_month, imp_pct_val, stammkapital, shareholder_loan,
    sh_loan_rate, vehicle_ltv, y1_loan_rate, y2_loan_rate, vat_bridge_rate,
    vat_lag_months, min_cash_buffer, legal_provision_rate, interest_income_rate,
    thg_quote_per_car_py, salvage_value_per_car_y4, max_overdraft_limit, is_dynamic, lang_choice
)

# ============================================================
# === L-02 + M-04 FIX: Day-1 Sources/Uses Display
# Use the engine-returned total_capex_per_car (instead of duplicating
# the calculation in the dashboard).
# Day-1 Liquidity metric now shows ACTUAL end-of-Month-1 cash from the
# engine — previously the metric was a sources-uses snapshot that
# ignored first-month opex, revenue, and VAT bridge flows, and could
# read €19K when actual was €27K.
# ============================================================
def _quick_parse(s):
    try:
        arr = [int(x.strip()) for x in s.split(',')]
        return (arr + [0]*12)[:12]
    except:
        return [0]*12

_y1_count = sum(_quick_parse(y1_adds_str))
day_1_loan = _y1_count * total_capex_per_car * vehicle_ltv  # uses returned scalar (L-02)
# M-04 FIX: actual end-of-Month-1 cash from engine, not sources-uses snapshot
day_1_cash_ui = bs_monthly["bs_cash"][0]

# --- POST-LOOP SYSTEM AGGREGATIONS ---
def agg_to_yearly(monthly_dict):
    yearly_dict = {}
    for key, arr in monthly_dict.items():
        yearly_arr = []
        for y in range(5):
            chunk = arr[y*12 : (y+1)*12]
            # F-19 Fix Applied: Structural set definitions completely clean aggregation pathways
            if key == "cf_end" or key in bs_keys_isolated:
                yearly_arr.append(chunk[-1])
            elif key == "cf_beg":
                yearly_arr.append(chunk[0])
            else:
                yearly_arr.append(sum(chunk))
        yearly_dict[key] = yearly_arr
    return yearly_dict

pnl_yearly = agg_to_yearly(pnl_monthly)
cf_yearly = agg_to_yearly(cf_monthly)
bs_yearly = agg_to_yearly(bs_monthly)

year_cols = [f"Year {y+1} ({2028+y})" if lang_choice == "English" else f"Jahr {y+1} ({2028+y})" for y in range(5)]

df_pnl_mo = pd.DataFrame(pnl_monthly, index=month_col_names).T
df_pnl_yr = pd.DataFrame(pnl_yearly, index=year_cols).T
df_pnl_combined = pd.concat([df_pnl_mo, df_pnl_yr], axis=1)

df_cf_mo = pd.DataFrame(cf_monthly, index=month_col_names).T
df_cf_yr = pd.DataFrame(cf_yearly, index=year_cols).T
df_cf_combined = pd.concat([df_cf_mo, df_cf_yr], axis=1)

df_bs_mo = pd.DataFrame(bs_monthly, index=month_col_names).T
df_bs_yr = pd.DataFrame(bs_yearly, index=year_cols).T
df_bs_combined = pd.concat([df_bs_mo, df_bs_yr], axis=1)

# Language Loc Mapper for final output tables
# NOTE: Only the *_combined frames are renamed. df_pnl_yr / df_cf_yr / df_bs_yr
# retain raw short keys ("pnl_net_rev" etc.) and must be looked up using
# those raw keys in the visualizations tab below.
df_pnl_combined.rename(index=lambda x: loc.get(x, x), inplace=True)
df_cf_combined.rename(index=lambda x: loc.get(x, x), inplace=True)
df_bs_combined.rename(index=lambda x: loc.get(x, x), inplace=True)

# --- F-22 STATUTORY GERMAN GUV ACCORDIONS (§ 275 HGB Gesamtkostenverfahren) ---
# === Layer 17 (post TM removal): Geschäftsführer also holds Verkehrsleiter
# mandate (no separate fee). Personalaufwand = 0. No TM strip-out needed
# in pos6, since pnl_fees no longer contains a TM component.
# === C-01 FIX: pnl_tesla_fee (bezogene Leistung — Tesla dispatch platform)
# now flows into pos3 Materialaufwand; pnl_legal_prov (Zuführung Rückstellung
# § 249 HGB) now flows into pos6. Both were previously missing from HGB sum.
hgb_structure = {}
hgb_structure[loc["hgb_pos1"]] = df_pnl_combined.loc[loc["pnl_net_rev"]].values
hgb_structure[loc["hgb_pos2"]] = (df_pnl_combined.loc[loc["pnl_thg"]] + df_pnl_combined.loc[loc["pnl_salvage"]]).values
# Materialaufwand: Aufwendungen für Roh-/Hilfsstoffe UND für bezogene Leistungen (Tesla platform)
hgb_structure[loc["hgb_pos3"]] = (df_pnl_combined.loc[loc["pnl_energy"]] + df_pnl_combined.loc[loc["pnl_wear"]] + df_pnl_combined.loc[loc["pnl_clean"]] + df_pnl_combined.loc[loc["pnl_ins"]] + df_pnl_combined.loc[loc["pnl_park"]] + df_pnl_combined.loc[loc["pnl_api"]] + df_pnl_combined.loc[loc["pnl_tuev"]] + df_pnl_combined.loc[loc["pnl_sub"]] + df_pnl_combined.loc[loc["pnl_tesla_fee"]]).values
# Personalaufwand: zero — GF holds Verkehrsleiter mandate without separate compensation
hgb_structure[loc["hgb_pos4"]] = np.zeros(len(df_pnl_combined.columns))
hgb_structure[loc["hgb_pos5"]] = (df_pnl_combined.loc[loc["pnl_afa_veh"]] + df_pnl_combined.loc[loc["pnl_afa_it"]]).values
# Sonstige betriebliche Aufwendungen: clean sum incl. Zuführung Rückstellung Rechtsrisiken
hgb_structure[loc["hgb_pos6"]] = (df_pnl_combined.loc[loc["pnl_hq_lease"]] + df_pnl_combined.loc[loc["pnl_it"]] + df_pnl_combined.loc[loc["pnl_legal"]] + df_pnl_combined.loc[loc["pnl_hq_ins"]] + df_pnl_combined.loc[loc["pnl_bank"]] + df_pnl_combined.loc[loc["pnl_fees"]] + df_pnl_combined.loc[loc["pnl_legal_prov"]]).values
hgb_structure[loc["hgb_pos7"]] = (df_pnl_combined.loc[loc["pnl_int_inc"]] + df_pnl_combined.loc[loc["pnl_int_exp"]]).values
hgb_structure[loc["hgb_pos8"]] = df_pnl_combined.loc[loc["pnl_tax"]].values
hgb_structure[loc["hgb_pos9"]] = df_pnl_combined.loc[loc["pnl_ni"]].values

df_hgb_pnl = pd.DataFrame(hgb_structure, index=df_pnl_combined.columns).T

# --- KPI ENGINE RATIOS ---
def safe_div(n, d):
    return np.divide(n.astype(float), d.astype(float), out=np.zeros_like(n.astype(float)), where=d.astype(float)!=0)

rev_top = df_pnl_combined.loc[loc["pnl_net_rev"]]
ebitda = df_pnl_combined.loc[loc["pnl_ebitda"]]
db2 = df_pnl_combined.loc[loc["pnl_db2"]]
ta = df_bs_combined.loc[loc["bs_ta"]]
teq = df_bs_combined.loc[loc["bs_teq"]]
cash = df_bs_combined.loc[loc["bs_cash"]]
nfa = df_bs_combined.loc[loc["bs_nfa"]]

# F-15 Fix Applied: Operational pass-through accounts purged from debt metrics evaluation
fin_debt = df_bs_combined.loc[loc["bs_debt_kfw"]] + df_bs_combined.loc[loc["bs_debt_vat"]] + df_bs_combined.loc[loc["bs_debt_overdraft"]] + df_bs_combined.loc[loc["bs_sh_loan"]]

var_costs = rev_top - df_pnl_combined.loc[loc["pnl_db1"]]
fix_costs = df_pnl_combined.loc[loc["pnl_db1"]] - ebitda + df_pnl_combined.loc[loc["pnl_thg"]]
tot_costs = var_costs + fix_costs
debt_service = -(df_cf_combined.loc[loc["cf_prin"]] + df_pnl_combined.loc[loc["pnl_int_exp"]])
other_inc = df_pnl_combined.loc[loc["pnl_thg"]]

kpi_dict = {}
kpi_dict[loc["kpi_db2_m"]] = [f"{x*100:.1f}%" for x in safe_div(db2, rev_top)]
kpi_dict[loc["kpi_var_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(var_costs, rev_top)]
kpi_dict[loc["kpi_fix_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(fix_costs, rev_top)]
kpi_dict[loc["kpi_tot_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(tot_costs, rev_top)]
kpi_dict[loc["kpi_other_inc_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(other_inc, rev_top)]
kpi_dict[loc["kpi_ebitda_m"]] = [f"{x*100:.1f}%" for x in safe_div(ebitda, rev_top)]
kpi_dict[loc["kpi_dscr"]] = [f"{x:.1f}x" if x > 0 else "n/a" for x in safe_div(ebitda, debt_service)]
kpi_dict[loc["kpi_eq_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(teq, ta)]

runway_arr = []
for col in df_pnl_combined.columns:
    is_year = "Year" in col or "Jahr" in col
    div = (fix_costs[col] + debt_service[col]) / 12 if is_year else (fix_costs[col] + debt_service[col])
    rw = cash[col] / div if div > 0 else 999
    runway_arr.append(f"{rw:.1f} Mo." if rw < 999 else "Infinite")
kpi_dict[loc["kpi_runway"]] = runway_arr

net_debt = fin_debt - cash
kpi_dict[loc["kpi_net_ltv"]] = [f"{x*100:.1f}%" for x in safe_div(net_debt, nfa)]

df_kpi_combined = pd.DataFrame(kpi_dict, index=df_pnl_combined.columns).T


# --- 7. VISUALIZATION CANVAS ENGINE ---
def create_mrrg_chart(x_labels, y_values, title, prefix="€", suffix="", hide_cagr=False):
    beg = y_values[0]
    end = y_values[-1]
    
    if not hide_cagr:
        if beg > 0 and end > 0:
            cagr = (end / beg) ** (1/4) - 1
            cagr_text = f"CAGR {cagr*100:.0f}%"
        elif beg <= 0 and end > 0:
            cagr_text = "CAGR N/A"
        else:
            cagr_text = "CAGR N/A"
            
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=x_labels, y=y_values,
        marker=dict(color='rgba(255,255,255,0.9)', pattern=dict(shape='/', fgcolor='#4DA8DA')),
        name=title
    ))
    
    fig.add_trace(go.Scatter(
        x=x_labels, y=y_values,
        mode='lines+markers', line=dict(color='#FFFFFF', width=3, shape='spline'),
        marker=dict(size=8, color='#FFFFFF'), name='Trend'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=20, color='white')),
        plot_bgcolor='#DE6B28', paper_bgcolor='#DE6B28',
        font=dict(color='white', family='Urbanist'), showlegend=False,
        margin=dict(l=40, r=40, t=60, b=40)
    )
    
    if not hide_cagr:
        fig.add_annotation(
            x=1, y=1.05, xref='paper', yref='paper',
            text=f"<b>{cagr_text}</b>", showarrow=False,
            font=dict(color='white', size=14), bgcolor='#4A86E8', borderpad=6
        )
    
    fig.update_yaxes(tickprefix=prefix, ticksuffix=suffix, showgrid=True, gridcolor='rgba(255,255,255,0.2)', zeroline=False)
    fig.update_xaxes(showgrid=False)
    return fig


# --- 8. DASHBOARD RECONCILIATION LAYOUT ---
# H-01 + H-02: Stacked liquidity-stress warnings
if len(insolvency_months) > 0:
    st.error(f"{loc['insolv_warn']}{', '.join(insolvency_months)}")
if len(net_liq_breach_months) > 0:
    st.warning(f"{loc['net_liq_warn']}{', '.join(net_liq_breach_months)}")
if len(cash_breach_months) > 0:
    st.error(f"{loc['cash_warn']}{', '.join(cash_breach_months)}")

st.subheader(loc["sources_title"])
colA, colB, colC, colD = st.columns(4)
colA.metric(loc["src_stamm"], f"€ {stammkapital:,.0f}")
colB.metric(loc["src_sh"], f"€ {shareholder_loan:,.0f}")
colC.metric(f"{loc['src_veh']} ({vehicle_ltv*100:.0f}%)", f"€ {day_1_loan:,.0f}")
colD.metric(loc["liquidity"], f"€ {day_1_cash_ui:,.0f}")

st.divider()
st.subheader(loc["output_title"])

st.markdown(f"**{loc['view_mode']}**")
t_col1, t_col2, t_col3, t_col4, t_col5 = st.columns(5)
exp_y1 = t_col1.toggle(loc["exp_y1"])
exp_y2 = t_col2.toggle(loc["exp_y2"])
exp_y3 = t_col3.toggle(loc["exp_y3"])
exp_y4 = t_col4.toggle(loc["exp_y4"])
exp_y5 = t_col5.toggle(loc["exp_y5"])
expands = [exp_y1, exp_y2, exp_y3, exp_y4, exp_y5]

display_cols = []
for y in range(5):
    if expands[y]: display_cols.extend(month_col_names[y*12 : (y+1)*12])
    display_cols.append(year_cols[y])

fleet_cols = st.columns(5)
for i in range(5):
    yr_fleet_val = active_fleet_by_month[(i*12)+11]
    yr_util_val = np.mean(utilization_by_month[i*12 : (i+1)*12])
    fleet_cols[i].metric(
        f"{loc['active_fleet']} (Y{i+1} End)", 
        f"{yr_fleet_val:.0f} {loc['cars']}", 
        delta=f"Ø {yr_util_val*100:.1f}% {loc['util_label']}",
        delta_color="off"
    )

st.write("") 

tabs = st.tabs([loc["tab_pnl"], loc["tab_hgb_pnl"], loc["tab_cf"], loc["tab_bs"], loc["tab_kpi"], loc["tab_charts"], loc["tab_readme"]])

def style_pnl_rows(row):
    if loc["pnl_mrrg_net"] in row.name: return ['font-weight: 600; color: #4DA8DA;'] * len(row)
    if loc["pnl_ebitda"] in row.name and "HGB" not in row.name: return ['font-weight: 700; background-color: #2b2b2b; color: #F2A900;'] * len(row)
    if loc["pnl_ebitda_hgb"] in row.name: return ['font-weight: 600; background-color: #1a2b3a; color: #87CEEB; font-style: italic;'] * len(row)
    if loc["pnl_ni"] in row.name: return ['font-weight: 700; background-color: #0b2e13; color: #38c172; border-top: 2px solid #38c172;'] * len(row)
    return [''] * len(row)

def style_bs_rows(row):
    if loc["bs_nfa"] in row.name or loc["bs_tca"] in row.name or loc["bs_teq"] in row.name or loc["bs_tprov"] in row.name or loc["bs_tliab"] in row.name:
        return ['font-weight: 600; border-top: 1px solid #ffffff40;'] * len(row)
    elif loc["bs_ta"] in row.name:
        return ['font-weight: 700; background-color: #1e1e1e; color: #4DA8DA; border-top: 2px solid #4DA8DA;'] * len(row)
    elif loc["bs_tleq"] in row.name:
        return ['font-weight: 700; background-color: #1e1e1e; color: #F2A900; border-top: 2px solid #F2A900;'] * len(row)
    elif loc["bs_check"] in row.name:
        return ['font-weight: 700; color: #38c172;'] * len(row)
    return [''] * len(row)

def style_kpi_rows(row):
    if loc["kpi_db2_m"] in row.name:
        return ['font-weight: 700; color: #4DA8DA; border-bottom: 1px solid #ffffff40;'] * len(row)
    elif loc["kpi_ebitda_m"] in row.name:
        return ['font-weight: 700; background-color: #1e1e1e; color: #F2A900; border-top: 1px solid #ffffff40; border-bottom: 2px solid #F2A900;'] * len(row)
    elif loc["kpi_dscr"] in row.name:
        return ['font-weight: 700; color: #38c172;'] * len(row)
    elif loc["kpi_net_ltv"] in row.name:
        return ['font-weight: 700; border-top: 1px solid #ffffff40;'] * len(row)
    return [''] * len(row)

with tabs[0]: st.dataframe(df_pnl_combined[display_cols].style.format("{:,.0f} €").apply(style_pnl_rows, axis=1), use_container_width=True)
with tabs[1]: st.dataframe(df_hgb_pnl[display_cols].style.format("{:,.0f} €").apply(style_pnl_rows, axis=1), use_container_width=True)
with tabs[2]: st.dataframe(df_cf_combined[display_cols].style.format("{:,.0f} €").apply(style_pnl_rows, axis=1), use_container_width=True)
with tabs[3]: st.dataframe(df_bs_combined[display_cols].style.format("{:,.0f} €").apply(style_bs_rows, axis=1), use_container_width=True)
with tabs[4]:
    st.dataframe(df_kpi_combined[display_cols].style.apply(style_kpi_rows, axis=1), use_container_width=True)
    st.write("")
    with st.expander(loc["glossary_title"]):
        if lang_choice == "English":
            st.markdown("""
            * **Debt Service Coverage Ratio (DSCR):** Measures our capacity to clear required bank loan installments. Calculated as *EBITDA / Total Debt Service (Principal + Interest)*.
            * **Equity Ratio:** Shows what share of corporate assets are owned directly by the shareholders rather than financed via third-party bank debt. Calculated as *Total Equity / Total Assets*.
            * **Liquidity Runway:** A worst-case stress test tracking survival time if revenues instantly drop to zero. Calculated as *Cash Balance / (Monthly Fixed Overhead + Monthly Debt Service Liabilities)*.
            * **Net LTV:** Measures structural asset leverage net of our treasury cushion. Calculated as *(Total Financial Debt - Cash) / Net Fixed Assets*. Excludes operational pass-through liabilities like VAT.
            * **Variable Expense Ratio:** Measures proportional cost exposure running the cars. Calculated as *Total Variable Operating Costs / Top-line Net Revenue*.
            * **Fixed Expense Ratio:** Tracks the margin impact of baseline corporate infrastructure. Calculated as *Total Fixed Operating Costs / Top-line Net Revenue*.
            * **Total Expense Ratio:** Measures total combined efficiency overhead drag against top-line revenues. Calculated as *Total Operational Expenses / Top-line Net Revenue*.
            * **Other Income Ratio:** The non-core revenue margin (THG Quota payouts) generated as a byproduct of operations.
            * **Contribution Margin Ratio (DB2):** Measures stand-alone asset portfolio performance before accounting for corporate headquarters drag. Calculated as *Deckungsbeitrag 2 / Top-line Net Revenue*.
            * **EBITDA Margin:** Core cash profitability metric monitoring standardized operating efficiency. Formula explicitly foots to the other ratios: *EBITDA Margin = 100% - Variable Ratio - Fixed Ratio + Other Income Ratio*.
            """)
        else:
            st.markdown("""
            * **Schuldendienstdeckungsgrad (DSCR):** Misst die Fähigkeit des Unternehmens, Zinsen und Tilgungen für Bankkredite zu bedienen. Berechnung: *EBITDA / (Zinsaufwand + Tilgung)*.
            * **Eigenkapitalquote:** Zeigt den prozentualen Anteil des durch Gesellschafter finanzierten Vermögens. Berechnung: *Summe Eigenkapital / Bilanzsumme*.
            * **Liquiditätsreichweite:** Ein Stress-Test-Szenario, das die Überlebenszeit bei plötzlichem Umsatzausfall prognostiziert. Berechnung: *Kassenbestand / (Monatliche Fixkosten + Monatlicher Schuldendienst)*.
            * **Netto-LTV:** Misst den Netto-Verschuldungsgrad unseres Anlagevermögens unter Berücksichtigung des Cash-Bestands. Berechnung: *(Summe Finanzverbindlichkeiten - Kasse) / Netto-Sachanlagen*.
            * **Variable Kostenquote:** Gibt an, wie viel Prozent jedes erwirtschafteten Euros direkt für den Betrieb der Fahrzeuge aufgewendet werden. Berechnung: *Variable Kosten / Netto-Umsatzerlöse*.
            * **Fixkostenquote:** Zeigt den prozentualen Anteil des Umsatzes, der durch die feste Unternehmensinfrastruktur aufgezehrt wird. Berechnung: *Fixkosten / Netto-Umsatzerlöse*.
            * **Gesamtkostenquote:** Bildet die gesamte betriebliche Kostenstruktur des operativen Geschäfts ab. Berechnung: *Gesamte betriebliche Kosten / Netto-Umsatzerlöse*.
            * **Sonstige Ertragsquote:** Die Nicht-Kernumsatzmarge (THG-Prämien), die als Nebenprodukt des Betriebs generiert wird.
            * **Deckungsbeitragsmarge (DB2):** Zeigt die reine Rentabilität der Fahrzeugflotte vor Abzug der HQ-Verwaltungskosten. Berechnung: *Deckungsbeitrag 2 / Netto-Umsatzerlöse*.
            * **EBITDA-Marge:** Der zentrale Indikator für die operative Cash-Rentabilität des Unternehmens. Mathematische Abstimmung: *EBITDA-Marge = 100% - Variable Quote - Fixe Quote + Sonstige Ertragsquote*.
            """)

with tabs[5]:
    # NOTE: df_pnl_yr / df_cf_yr / df_bs_yr were never renamed (only df_*_combined were).
    # They retain the raw short keys ("pnl_net_rev" etc.), so we MUST look up by raw key
    # rather than by loc[...]. Using loc[...] here would KeyError.
    y_rev_v = df_pnl_yr.loc["pnl_net_rev"].values
    y_eb_v  = df_pnl_yr.loc["pnl_ebitda"].values
    y_ni_v  = df_pnl_yr.loc["pnl_ni"].values
    y_fl_v  = [active_fleet_by_month[(i*12)+11] for i in range(5)]
    y_ta_v  = df_bs_yr.loc["bs_ta"].values
    y_fcf_v = (df_cf_yr.loc["cf_op"] + df_cf_yr.loc["cf_inv"]).values
    
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(create_mrrg_chart(year_cols, y_rev_v, loc["chart_rev"]), use_container_width=True)
    with c2: st.plotly_chart(create_mrrg_chart(year_cols, y_eb_v, loc["chart_ebitda"]), use_container_width=True)
    c3, c4 = st.columns(2)
    with c3: st.plotly_chart(create_mrrg_chart(year_cols, y_ni_v, loc["chart_ni"]), use_container_width=True)
    with c4: st.plotly_chart(create_mrrg_chart(year_cols, y_fl_v, loc["chart_fleet"]), use_container_width=True)
    c5, c6 = st.columns(2)
    with c5:
        uc = st.toggle(loc["toggle_fcf"])
        st.plotly_chart(create_mrrg_chart(year_cols, np.cumsum(y_fcf_v) if uc else y_fcf_v, loc["chart_fcf"], hide_cagr=uc), use_container_width=True)
    with c6:
        st.plotly_chart(create_mrrg_chart(year_cols, y_ta_v, loc["chart_ta"]), use_container_width=True)

with tabs[6]:
    if lang_choice == "English":
        st.markdown("""
        ### 🚕 MRRG Cybercab Fleet: Master Financial Engine
        
        Welcome to the MRRG Master Financial Engine. This application is a fully integrated, institutional-grade financial model designed to simulate the operations, scaling, and accounting of an automated robotaxi (TaaS) fleet operating in Germany.

        Built on **Streamlit** and written in **Python**, this dashboard moves beyond basic spreadsheet math. It uses a **60-month cohort engine** to simulate real-world physics: from the exact number of days in a month (accounting for leap years) to winter battery penalties and fleet cannibalization. It outputs a fully balanced, HGB-compliant 3-Statement financial model.

        ---

        #### 🧠 TaaS & Finance 101: Core Concepts to Know
        * **TaaS (Transportation-as-a-Service):** The business model of providing rides using automated vehicles routed by an algorithmic platform.
        * **CapEx (Capital Expenditure):** The massive upfront cost of buying the vehicles. You don't "expense" a car in month 1; you put it on the Balance Sheet as an asset.
        * **AfA (Absetzung für Abnutzung / Depreciation):** Because cars lose value over time, the government allows us to deduct a portion of the car's value from our taxable profit every month.
        * **Deadhead:** The percentage of kilometers a vehicle drives *without* a paying passenger. 
        * **HGB (Handelsgesetzbuch):** The German Commercial Code. This model strictly follows German accounting rules, specifically regarding how taxes are provisioned and paid.
        * **Shareholder Loans:** If a founder lends money to the company, German tax law generally expects a market interest rate to avoid hidden profit distributions (vGA). Since banks usually require this loan to act as equity buffer, the principal is locked (subordinated) while interest is accrued or paid monthly.

        ---

        #### 🎛️ How to Use the Sidebar (Input Levers)
        The left sidebar is your "control room." Any change you make here instantly recalculates all 60 months of the simulation. 
        
        * **Fleet Scaling:** Instead of adding cars once a year, you type a comma-separated list to drop cars into specific months (e.g., `2, 0, 0, 0, 2` means 2 cars in Jan, 2 in May). 
        * **Utilization Mode:** If set to *Dynamic*, the model simulates reality: when you drop new cars into a city, they temporarily "cannibalize" rides from your existing cars. Your overall utilization drops, and then slowly recovers.
        * **Variable Costs:** The engine automatically multiplies base energy costs by **1.4x in Winter** and **1.3x in Shoulder months** because batteries are less efficient in the cold.
        * **VAT Bridge Loan:** When you buy a €30k car, you must pay 19% VAT immediately. The engine automatically draws a short-term bridge loan (rate configured in sidebar) to cover this VAT and pays it off automatically based on the configured refund lag.
        * **OpEx Input VAT (Vorsteuerabzug, Layer 17):** When you pay vendors for energy, maintenance, parking, telemetry, IT, HQ lease, legal services, etc., you pay them gross (net + 19% VAT). That 19% is **deductible input VAT** that offsets your monthly Umsatzsteuerzahllast to the Finanzamt. The model now correctly: (1) drains vendor VAT as cash this month, (2) reduces the next month's VAT remittance by the same amount. The P&L stays unchanged — costs are always booked net — but the Cash Flow and Balance Sheet now reflect real UStG mechanics. VAT-exempt items (insurance, IHK, GEZ, bank fees) are excluded per § 4 UStG.
        * **Layer 18 fixes:** (a) **Vehicle AfA is now 60 months** (5 Jahre, aligned with BMF AfA-Tabelle for Mietwagen/Taxi per § 7 EStG). (b) **Overdraft is now capped** at a user-defined Kontokorrentlinie; if the model needs more, **INSOLVENCY** is flagged. (c) **Three distinct liquidity warnings:** Insolvency (line exceeded), Net Liquidity Negative (Cash − Overdraft below buffer = bank-grade Effektive Liquidität check), Raw Cash Floor Breached (traditional check). (d) **Cleaning cost** now depends on calendar days × fleet only, not on utilization. (e) **EBITDA HGB View** memo row added below Mgmt EBITDA showing the salvage bridge per § 275 II Nr. 4 HGB.

        ---

        #### 🎯 Operational Calibration & Benchmarking (Layer 20)
        Operational and variable cost assumptions in this model reflect mature-state central-case values benchmarked against published European mobility operator data (Sixt+, Free Now, MOIA/Volkswagen Group, Waymo Phoenix). Throughput calibration assumes **30-34 trips/day per vehicle at steady-state (Y3+)**, built up from 13.5h blended weekday/weekend productive shift, 19 km/h Munich average speed, 3.5 min per-trip dwell, and 22% empty repositioning. Energy and wear cost recalibrations land at **€0.085/km and €0.10/km** respectively — below Waymo benchmarks due to simpler Cybercab sensor stack and German labor rates, above earlier optimistic estimates that did not survive bank-grade Due Diligence. Y1-Y2 ramp-state will run below mature numbers; the engine's **Dynamic Utilization** mode (set as default) models this naturally through the cannibalization + recovery mechanics. For aggressive bull-case modeling, adjust sidebar inputs upward and document the rationale separately.

        **Empirical sources:** TomTom Traffic Index 2024 (Munich congestion); ADAC Wintertest 2023 + Geotab fleet study (EV winter consumption); Waymo NHTSA filings (sensor reliability, dwell time, ramp curves); Sixt+ / Free Now / MOIA published operator data (€/km maintenance benchmarks); Uber/Lyft Marketplace blog data (mature European deadhead rates).

        ---

        #### 📊 Understanding the Outputs (The Tabs)
        * **Income Statement (P&L):** Measures paper profitability. Start at the top (Customer bookings) and watch the money cascade down to EBITDA (Operational profit before loans/depreciation) and Net Income.
        * **Cash Flow Statement:** The actual cash entering and leaving your bank account. This tab shows your CapEx cash burns, your loan drawdowns, and exactly when you pay your corporate taxes. 
        * **Balance Sheet:** A snapshot of what the company owns vs. what it owes. Look at the **BALANCE CHECK** line at the very bottom. It dynamically proves the math is perfect by always showing 0 €.
        * **KPIs & Ratios:** The metrics banks and Venture Capitalists look at to judge the health of your business (like DSCR and Liquidity Runway).
        * **Visualizations & Dashboards:** A suite of institutional charts showing the scaling trajectory. Toggle Free Cash Flow to "Cumulative" to see the exact "J-Curve" of your business.
        """)
    else:
        st.markdown("""
        ### 🚕 MRRG Cybercab-Flotte: Master-Finanzmodell
        
        Willkommen beim MRRG Master-Finanzmodell. Diese Anwendung ist ein vollständig integriertes, institutionelles Finanzmodell, das den Betrieb, die Skalierung und die Buchhaltung einer automatisierten Robotaxi-Flotte (TaaS) in Deutschland simuliert.

        Dieses auf **Streamlit** und **Python** basierende Dashboard geht weit über grundlegende Tabellenkalkulationen hinaus. Es nutzt eine **60-monatige Kohorten-Logik**, um reale physikalische und wirtschaftliche Gegebenheiten zu simulieren: von der exakten Anzahl an Tagen pro Monat (inkl. Schaltjahren) über Winterzuschläge beim Stromverbrauch bis hin zur Flotten-Kannibalisierung. Das Ergebnis ist ein vollständig bilanziertes, HGB-konformes 3-Statement-Modell.

        ---

        #### 🧠 TaaS & Finance 101: Die wichtigsten Grundkonzepte
        * **TaaS (Transportation-as-a-Service):** Das Geschäftsmodell zur Bereitstellung von Fahrten durch automatisierte Fahrzeuge, die über eine algorithmische Plattform gesteuert werden.
        * **CapEx (Investitionsausgaben):** Die massiven Vorlaufkosten für den Kauf der Fahrzeuge. Ein Auto wird nicht im ersten Monat als Aufwand verbucht; es wird als Vermögenswert in der Bilanz aktiviert.
        * **AfA (Absetzung für Abnutzung):** Da Autos im Laufe der Zeit an Wert verlieren, dürfen wir jeden Monat einen Teil des Fahrzeugwerts von unserem steuerpflichtigen Gewinn abziehen.
        * **Leerfahrten (Deadhead):** Der prozentuale Anteil der gefahrenen Kilometer *ohne* zahlenden Fahrgast.
        * **HGB (Handelsgesetzbuch):** Dieses Modell folgt strikt den deutschen Rechnungslegungsvorschriften, insbesondere im Hinblick auf die Bildung und Auszahlung von Steuerrückstellungen.
        * **Gesellschafterdarlehen:** Gibt ein Gründer dem Unternehmen einen Kredit, erwartet das Finanzamt in der Regel einen Marktzins, um verdeckte Gewinnausschüttungen (vGA) zu vermeiden. Da Banken meist einen Rangrücktritt fordern, bleibt die Kreditsumme gebunden, während die Zinsen monatlich anfallen oder gezahlt werden.

        ---

        #### 🎛️ Bedienung der Seitenleiste (Eingabeparameter)
        Die linke Seitenleiste ist Ihr Kontrollzentrum. Jede Änderung, die Sie hier vornehmen, berechnet sofort alle 60 Monate der Simulation neu.
        
        * **Flottenskalierung:** Anstatt Autos nur einmal pro Jahr hinzuzufügen, geben Sie eine durch Kommas getrennte Liste ein, um Autos in bestimmten Monaten einzuflotten (z. B. `2, 0, 0, 0, 2` bedeutet 2 Autos im Jan, 2 im Mai).
        * **Auslastungsmodell:** Wenn auf *Dynamisch* gesetzt, simuliert das Modell die Realität: Wenn neue Autos in die Flotte kommen, "kannibalisieren" sie vorübergehend die Fahrten der bestehenden Flotte. Die Gesamtauslastung sinkt und erholt sich dann allmählich.
        * **Variable Kosten:** Das System multipliziert die Basis-Stromkosten automatisch mit **1,4x im Winter** und **1,3x in den Übergangsmonaten**, da Batterien bei Kälte weniger effizient sind.
        * **USt-Überbrückungskredit:** Wenn Sie ein Auto für 30.000 € kaufen, müssen Sie sofort 19% Umsatzsteuer zahlen. Das System nimmt automatisch einen kurzfristigen Überbrückungskredit auf (Zinssatz in Seitenleiste konfigurierbar), um diese Vorsteuer zu decken, und zahlt ihn nach der konfigurierten Erstattungsdauer zurück, wenn die Erstattung vom Finanzamt eintrifft.
        * **OpEx-Vorsteuerabzug (Layer 17):** Wenn Sie Lieferanten für Energie, Wartung, Stellplätze, Telemetrie, IT, Raumkosten, Rechts- und Beratungsleistungen usw. bezahlen, zahlen Sie brutto (netto + 19% USt). Diese 19% sind **abzugsfähige Vorsteuer**, die mit der monatlichen Umsatzsteuerzahllast verrechnet wird. Das Modell bildet nun korrekt ab: (1) Vorsteuer fließt in diesem Monat als Cash-Abfluss zum Lieferanten ab, (2) die Zahllast an das Finanzamt im Folgemonat wird um genau diesen Betrag reduziert. Die GuV bleibt unverändert — Kosten werden stets netto gebucht — aber Kapitalflussrechnung und Bilanz spiegeln nun die echten UStG-Mechanik wider. Nicht abzugsfähige Posten (Versicherung, IHK, GEZ, Bankgebühren) sind gemäß § 4 UStG ausgenommen.
        * **Layer 18 Verbesserungen:** (a) **Fahrzeug-AfA jetzt 60 Monate** (5 Jahre, BMF AfA-Tabelle Mietwagen/Taxi gem. § 7 EStG). (b) **Kontokorrent gedeckelt** auf eine benutzerdefinierte Linie; bei Überschreitung wird **INSOLVENZ** angezeigt. (c) **Drei separate Liquiditätssignale:** Insolvenz (Linie überschritten), Netto-Liquidität negativ (Kasse − Kontokorrent unter Puffer = bankübliche Effektive Liquidität), Mindestliquidität unterschritten (klassische Prüfung). (d) **Reinigungskosten** abhängig nur von Kalendertagen × Flotte, nicht von Auslastung. (e) **EBITDA HGB-Sicht** als Memo-Zeile unter Management-EBITDA mit Anlagenabgang-Brücke gem. § 275 II Nr. 4 HGB.

        ---

        #### 🎯 Operative Kalibrierung & Benchmarking (Layer 20)
        Operative und variable Kostenannahmen reflektieren Mature-State-Basisfall-Werte mit Benchmarks gegen veröffentlichte Daten europäischer Mobilitätsbetreiber (Sixt+, Free Now, MOIA/Volkswagen Group, Waymo Phoenix). Durchsatzkalibrierung: **30-34 Fahrten/Tag pro Fahrzeug im Steady-State (J3+)**, aufgebaut aus 13,5h gemischter Werktag/Wochenend-produktiver Schicht, 19 km/h Münchner Durchschnittsgeschwindigkeit, 3,5 Min Standzeit pro Fahrt, 22% Leerfahrtenquote. Energie- und Verschleißkosten neu kalibriert auf **€0,085/km bzw. €0,10/km** — unter Waymo-Benchmarks wegen einfacherem Cybercab-Sensorstack und deutschen Arbeitskosten, über früheren optimistischen Schätzungen, die einer bankgerechten Due Diligence nicht standhielten. J1-J2 Ramp-State läuft unter den Mature-Zahlen; der **Dynamic Utilization Modus** des Engines (Standard) modelliert dies natürlich über Kannibalisierungs- und Erholungsmechanik. Für aggressive Bull-Case-Modellierung Sidebar-Inputs nach oben anpassen und Begründung separat dokumentieren.

        **Empirische Quellen:** TomTom Traffic Index 2024 (Münchner Verkehrsdichte); ADAC Wintertest 2023 + Geotab Flottenstudie (EV-Winterverbrauch); Waymo NHTSA-Meldungen (Sensorzuverlässigkeit, Standzeit, Ramp-Kurven); Sixt+ / Free Now / MOIA veröffentlichte Betreiberdaten (€/km Wartungs-Benchmarks); Uber/Lyft Marketplace-Blog (mature europäische Leerfahrtenquoten).

        ---

        #### 📊 Verständnis der Auswertungen (Die Reiter)
        * **Gewinn- und Verlustrechnung (GuV):** Misst die buchhalterische Rentabilität. Oben stehen die Kundenbuchungen, unten bleiben EBITDA (operativer Gewinn vor Zinsen/Abschreibungen) und der Jahresüberschuss.
        * **Kapitalflussrechnung:** Die tatsächlichen Zahlungsströme auf Ihrem Bankkonto. Hier sehen Sie die CapEx-Mittelabflüsse, die Kreditaufnahmen und exakt, wann Sie Ihre Unternehmenssteuern zahlen.
        * **Bilanz:** Eine Momentaufnahme dessen, was das Unternehmen besitzt und wem es was schuldet. Achten Sie auf die **BILANZKONTROLLE** ganz unten. Sie beweist dynamisch, dass die Mathematik perfekt aufgeht, indem sie immer 0 € anzeigt.
        * **KPIs & Kennzahlen:** Die Kennzahlen, die Banken und Venture-Capital-Investoren heranziehen, um die Gesundheit Ihres Unternehmens zu beurteilen (wie DSCR und Liquiditätsreichweite).
        * **Visualisierungen & Dashboards:** Institutionelle Diagramme, die den Skalierungsverlauf zeigen. Wenn Sie den Free Cash Flow auf "Kumuliert" umstellen, sehen Sie die exakte "J-Kurve" Ihres Unternehmens.
        """)
