import streamlit as st
import pandas as pd
import numpy as np

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
    </style>
    """, unsafe_allow_html=True)

# --- LANGUAGE DICTIONARY ---
lang_choice = st.sidebar.selectbox("Language / Sprache", ["English", "Deutsch"])

if lang_choice == "English":
    loc = {
        "title": "MRRG Cybercab Fleet: Master Financial Engine",
        "subtitle": "*(HGB Accounting for a GmbH - Layer 8: Cash Flow Statement & VAT Bridge)*",
        "sec1a": "1a. BASE FLEET PHYSICS (Y1)",
        "fleet_size": "Base Fleet Size (Num Vehicles)",
        "utilization": "Vehicle Utilization / Uptime (%)",
        "active_hours": "Active Hours / Day",
        "speed": "Average Speed (km/h)",
        "deadhead": "Deadhead Rate (%)",
        "sec1b": "1b. FLEET SCALING (Additions)",
        "adds": "Additions",
        "sec2": "2. TRIP DYNAMICS",
        "trip_dist": "Average Trip Distance (km)",
        "dwell": "Dwell Time (Minutes)",
        "sec3": "3. PRICING (Incl. 19% VAT)",
        "base_fare": "Base Fare (€)",
        "price_km": "Price per km (€)",
        "tesla_take": "Tesla Take-Rate (%)",
        "sec4": "4. DAILY VARIABLE COSTS (Net)",
        "cleaning": "Cleaning Cost per Vehicle/Day (€)",
        "wear_rate": "Maintenance/Wear per km (€)",
        "wear_help": "Covers tires, fluids, and suspension. The €0.03 excludes 'black swan' contingency which is held in the liquidity reserve.",
        "energy_rate": "Energy Cost per km (€)",
        "energy_help": "Fully-loaded cost of electricity accounting for hardware efficiency, wireless charging loss, and smart grid procurement.",
        "sec5": "5. VEHICLE FIXED COSTS (€ / Month, Net)",
        "insurance": "Insurance",
        "parking": "APCOA Parking",
        "telemetry": "Telemetry & API",
        "tuev": "TÜV / BO-Kraft Accrual",
        "charging_sub": "Tesla Charging Sub",
        "sec6": "6. CORPORATE HQ & SCALING (€ / Month, Net)",
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
        "sec7": "7. CAPEX & DEPRECIATION",
        "base_price": "Base Cybercab Price (USD)",
        "fx": "USD to EUR Exchange Rate",
        "freight": "Import Freight & Ins. per Vehicle (€)",
        "duty": "Import Duty (Zoll) %",
        "it_hw": "IT Hardware CapEx (Y1)",
        "sec8": "8. CAPITAL STRUCTURE & FINANCING",
        "stamm": "Stammkapital (€)",
        "sh_loan": "Shareholder Loan (€)",
        "ltv": "Vehicle Loan-to-Value (LTV) %",
        "loan_type": "Y1 Loan Type",
        "int_rate": "Cash Interest Rate (%)",
        "sec9": "9. OTHER INCOME / SALVAGE",
        "thg": "THG Quote per vehicle/yr",
        "salvage": "Vehicle Sale Price (Y4)",
        
        # P&L Lines
        "pnl_gbv": "Gross Booking Value (Customer Pays incl. 19% VAT)",
        "pnl_vat": "Less: 19% VAT (Finanzamt)",
        "pnl_net_rev": "Net Revenue (Umsatzerlöse excl. VAT)",
        "pnl_tesla_fee": "Less: Tesla Platform Fee (Take-Rate on GBV)",
        "pnl_mrrg_net": "MRRG Net Revenue (After Platform Fee)",
        "pnl_energy": "Less: Direct Energy (Variable)",
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
        "pnl_thg": "Add: THG Quote (Other Operating Income)",
        "pnl_salvage": "Add: Fleet Liquidation (Asset Sale)",
        "pnl_ebitda": "EBITDA",
        "pnl_afa_veh": "Less: Vehicle Depreciation (AfA - 48 Mo.)",
        "pnl_afa_it": "Less: IT Hardware Depreciation (AfA - 36 Mo.)",
        "pnl_ebit": "EBIT (Operating Income)",
        "pnl_int_inc": "Add: Interest Income (Zinserträge)",
        "pnl_int_exp": "Less: Interest Expense (Zinsaufwendungen)",
        "pnl_ebt": "EBT (Earnings Before Tax)",
        "pnl_tax": "Less: Corporate Taxes (Ertragsteuern)",
        "pnl_ni": "Net Income (Jahresüberschuss / EAT)",
        
        # Cash Flow Lines
        "cf_ni": "Net Income (Jahresüberschuss)",
        "cf_depr": "Depreciation (AfA)",
        "cf_tax_prov": "Increase in Tax Provision",
        "cf_tax_paid": "Taxes Paid (Previous Year)",
        "cf_op": "Cash Flow from Operations",
        "cf_capex": "CapEx (Vehicles & IT)",
        "cf_inv": "Cash Flow from Investing",
        "cf_eq": "Equity Injection (Stammkapital)",
        "cf_sh": "Shareholder Loan",
        "cf_kfw_draw": "Loan Drawdown (KfW / Bank)",
        "cf_prin": "Principal Repayment",
        "cf_vat_draw": "VAT Bridge Loan Drawdown",
        "cf_vat_repay": "VAT Bridge Loan Repayment",
        "cf_fin": "Cash Flow from Financing",
        "cf_net": "Net Change in Cash",
        "cf_beg": "Beginning Cash Balance",
        "cf_end": "Ending Cash Balance",
        
        # UI Elements
        "sources_title": "Day 1 Sources & Uses of Capital (Y1 Cohort Only)",
        "src_stamm": "Sources: Stammkapital",
        "src_sh": "Sources: Shareholder Loan",
        "src_veh": "Sources: Vehicle Loan",
        "liquidity": "Day 1 Liquidity Buffer",
        "output_title": "5-Year Cohort P&L & Cash Flow Output (HGB)",
        "active_fleet": "Active Fleet",
        "cars": "Vehicles",
        "tab_pnl": "Income Statement (P&L)",
        "tab_cf": "Cash Flow Statement",
        "tab_bs": "Balance Sheet",
        "bs_note": "*(Balance Sheet integration will be built in Layer 9 after Cash Flow sign-off)*"
    }
else:
    loc = {
        "title": "MRRG Cybercab-Flotte: Master-Finanzmodell",
        "subtitle": "*(HGB-Rechnungslegung für eine GmbH - Layer 8: Kapitalflussrechnung & USt-Kredit)*",
        "sec1a": "1a. BASIS-FLOTTENPHYSIK (J1)",
        "fleet_size": "Basis-Flottengröße (Anzahl)",
        "utilization": "Fahrzeugauslastung / Uptime (%)",
        "active_hours": "Aktive Stunden / Tag",
        "speed": "Durchschnittsgeschwindigkeit (km/h)",
        "deadhead": "Leerfahrten-Quote (%)",
        "sec1b": "1b. FLOTTENSKALIERUNG (Zugänge)",
        "adds": "Zugänge",
        "sec2": "2. FAHRTDYNAMIK",
        "trip_dist": "Durchschnittliche Fahrstrecke (km)",
        "dwell": "Standzeit pro Fahrt (Minuten)",
        "sec3": "3. PREISGESTALTUNG (inkl. 19% USt)",
        "base_fare": "Grundgebühr (€)",
        "price_km": "Preis pro km (€)",
        "tesla_take": "Tesla Plattformgebühr (%)",
        "sec4": "4. TÄGLICHE VARIABLE KOSTEN (Netto)",
        "cleaning": "Reinigungskosten pro Fahrzeug/Tag (€)",
        "wear_rate": "Instandhaltung/Verschleiß pro km (€)",
        "wear_help": "Deckt Reifen, Flüssigkeiten und Fahrwerk ab. Die 0,03 € schließen die 'Black Swan'-Rücklage aus, die separat im Liquiditätspuffer gehalten wird.",
        "energy_rate": "Energiekosten pro km (€)",
        "energy_help": "Vollkosten für Strom unter Berücksichtigung der Hardware-Effizienz, Verlusten beim kabellosen Laden und intelligentem Stromeinkauf.",
        "sec5": "5. FAHRZEUG-FIXKOSTEN (€ / Monat, Netto)",
        "insurance": "Kfz-Versicherung",
        "parking": "APCOA Stellplätze",
        "telemetry": "Telemetrie & API",
        "tuev": "TÜV / BO-Kraft Rückstellung",
        "charging_sub": "Tesla Lade-Abo",
        "sec6": "6. CORPORATE HQ & SKALIERUNG (€ / Monat, Netto)",
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
        "sec7": "7. CAPEX & ABSCHREIBUNGEN (AfA)",
        "base_price": "Basis Cybercab Preis (USD)",
        "fx": "Wechselkurs USD zu EUR",
        "freight": "Importfracht & Vers. pro Fahrzeug (€)",
        "duty": "Zollsatz (%)",
        "it_hw": "IT Hardware CapEx (J1)",
        "sec8": "8. KAPITALSTRUKTUR & FINANZIERUNG",
        "stamm": "Stammkapital (€)",
        "sh_loan": "Gesellschafterdarlehen (€)",
        "ltv": "Fremdkapitalquote Fahrzeuge (LTV) %",
        "loan_type": "Kreditart J1",
        "int_rate": "Guthabenzinsen (%)",
        "sec9": "9. SONSTIGE ERTRÄGE / RESTWERT",
        "thg": "THG-Quote pro Fahrzeug/Jahr",
        "salvage": "Fahrzeugverkaufspreis (J4)",
        
        # P&L Lines
        "pnl_gbv": "Bruttobuchungswert (Kunde zahlt inkl. 19% USt)",
        "pnl_vat": "Abzüglich: 19% Umsatzsteuer (Finanzamt)",
        "pnl_net_rev": "Umsatzerlöse (netto)",
        "pnl_tesla_fee": "Abzüglich: Tesla-Plattformgebühr (auf BBW)",
        "pnl_mrrg_net": "MRRG Nettoerlöse (nach Plattformgebühr)",
        "pnl_energy": "Abzüglich: Direkte Energiekosten (variabel)",
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
        "pnl_thg": "Zuzüglich: THG-Quote (Sonstige betriebliche Erträge)",
        "pnl_salvage": "Zuzüglich: Flottenliquidation (Anlagenverkauf)",
        "pnl_ebitda": "EBITDA",
        "pnl_afa_veh": "Abzüglich: Abschreibung Fahrzeuge (AfA - 48 Mon.)",
        "pnl_afa_it": "Abzüglich: Abschreibung IT Hardware (AfA - 36 Mon.)",
        "pnl_ebit": "EBIT (Betriebsergebnis)",
        "pnl_int_inc": "Zuzüglich: Zinserträge",
        "pnl_int_exp": "Abzüglich: Zinsaufwendungen",
        "pnl_ebt": "EBT (Ergebnis vor Steuern)",
        "pnl_tax": "Abzüglich: Ertragsteuern",
        "pnl_ni": "Jahresüberschuss (EAT)",
        
        # Cash Flow Lines
        "cf_ni": "Jahresüberschuss",
        "cf_depr": "Abschreibungen (AfA)",
        "cf_tax_prov": "Zunahme Steuerrückstellungen",
        "cf_tax_paid": "Gezahlte Steuern (Vorjahr)",
        "cf_op": "Operativer Cashflow",
        "cf_capex": "Auszahlungen für Sachanlagen (CapEx)",
        "cf_inv": "Cashflow aus Investitionstätigkeit",
        "cf_eq": "Einzahlungen Eigenkapital",
        "cf_sh": "Einzahlungen Gesellschafterdarlehen",
        "cf_kfw_draw": "Einzahlungen Bankdarlehen",
        "cf_prin": "Tilgung Bankdarlehen",
        "cf_vat_draw": "Einzahlungen USt-Überbrückungskredit",
        "cf_vat_repay": "Tilgung USt-Überbrückungskredit",
        "cf_fin": "Cashflow aus Finanzierungstätigkeit",
        "cf_net": "Nettoveränderung Finanzmittel",
        "cf_beg": "Anfangsbestand Finanzmittel",
        "cf_end": "Endbestand Finanzmittel",
        
        # UI Elements
        "sources_title": "Tag 1 Mittelherkunft & Mittelverwendung (Nur Kohorte J1)",
        "src_stamm": "Mittelherkunft: Stammkapital",
        "src_sh": "Mittelherkunft: Gesellschafterdarlehen",
        "src_veh": "Mittelherkunft: Fahrzeugdarlehen",
        "liquidity": "Tag 1 Liquiditätspuffer",
        "output_title": "5-Jahres Kohorten-GuV & Kapitalflussrechnung (HGB)",
        "active_fleet": "Aktive Flotte",
        "cars": "Fahrzeuge",
        "tab_pnl": "Gewinn- und Verlustrechnung (GuV)",
        "tab_cf": "Kapitalflussrechnung",
        "tab_bs": "Bilanz",
        "bs_note": "*(Die Integration der Bilanz wird in Layer 9 nach Freigabe des Cashflows erstellt)*"
    }

st.title(loc["title"])
st.markdown(loc["subtitle"])

# --- 1. THE PHYSICS & REVENUE ASSUMPTIONS ---
st.sidebar.header(loc["sec1a"])
fleet_size = st.sidebar.slider(loc["fleet_size"], 1, 50, 3)
vehicle_utilization = st.sidebar.number_input(loc["utilization"], value=90.0) / 100
active_hours_per_day = st.sidebar.number_input(loc["active_hours"], value=16.0)
avg_speed_kmh = st.sidebar.number_input(loc["speed"], value=22.0)
deadhead_rate = st.sidebar.number_input(loc["deadhead"], value=30.0) / 100

st.sidebar.header(loc["sec1b"])
y2_adds = st.sidebar.number_input(f"Year 2 {loc['adds']}", value=6)
y3_adds = st.sidebar.number_input(f"Year 3 {loc['adds']}", value=12)
y4_adds = st.sidebar.number_input(f"Year 4 {loc['adds']}", value=15)
y5_adds = st.sidebar.number_input(f"Year 5 {loc['adds']}", value=21)

st.sidebar.header(loc["sec2"])
avg_trip_distance_km = st.sidebar.number_input(loc["trip_dist"], value=5.0)
dwell_time_mins = st.sidebar.number_input(loc["dwell"], value=2.0)

st.sidebar.header(loc["sec3"])
base_fare_eur = st.sidebar.number_input(loc["base_fare"], value=2.50)
price_per_km_eur = st.sidebar.number_input(loc["price_km"], value=1.49)
tesla_take_rate = st.sidebar.number_input(loc["tesla_take"], value=25.0) / 100
vat_rate = 0.19

st.sidebar.header(loc["sec4"])
cleaning_cost_per_day = st.sidebar.number_input(loc["cleaning"], value=3.00)
wear_and_tear_rate = st.sidebar.number_input(loc["wear_rate"], value=0.03, format="%.2f", step=0.01, help=loc["wear_help"])
energy_rate = st.sidebar.number_input(loc["energy_rate"], value=0.05, format="%.2f", step=0.01, help=loc["energy_help"])

st.sidebar.header(loc["sec5"])
insurance_pm = st.sidebar.number_input(loc["insurance"], value=300.0)
parking_pm = st.sidebar.number_input(loc["parking"], value=150.0)
telemetry_pm = st.sidebar.number_input(loc["telemetry"], value=100.0)
tuev_pm = st.sidebar.number_input(loc["tuev"], value=15.0)
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

st.sidebar.header(loc["sec8"])
stammkapital = st.sidebar.number_input(loc["stamm"], value=25000.0)
shareholder_loan = st.sidebar.number_input(loc["sh_loan"], value=15000.0)
vehicle_ltv = st.sidebar.number_input(loc["ltv"], value=80.0) / 100
loan_cohort = st.sidebar.selectbox(loc["loan_type"], ["KfW Gründerkredit (4.5%, 1yr Grace)"])
interest_income_rate = st.sidebar.number_input(loc["int_rate"], value=2.2) / 100

st.sidebar.header(loc["sec9"])
thg_quote_per_car_py = st.sidebar.number_input(loc["thg"], value=200.0)
salvage_value_per_car_y4 = st.sidebar.number_input(loc["salvage"], value=10000.0)

# --- 2. CAPEX & SOURCES/USES MATH ---
cybercab_base_eur = cybercab_base_usd / usd_eur_rate
zollwert_cif_eur = cybercab_base_eur + import_freight_eur
zollkosten_eur = zollwert_cif_eur * customs_duty_rate
total_capex_per_car = zollwert_cif_eur + zollkosten_eur

cohort_data = {}
additions = [fleet_size, y2_adds, y3_adds, y4_adds, y5_adds]

for c, size in enumerate(additions, start=1):
    capex = size * total_capex_per_car
    loan = capex * vehicle_ltv
    rate = 0.045 if c == 1 else 0.055
    cohort_data[c] = {
        "size": size,
        "original_loan": loan,
        "loan_bal": loan,
        "rate": rate,
        "afa_per_yr": capex / 4
    }

# Day 1 UI Variables
total_uses_y1 = cohort_data[1]["original_loan"] / vehicle_ltv + it_hardware_capex_y1
day_1_cash_balance_ui = stammkapital + shareholder_loan + cohort_data[1]["original_loan"] - total_uses_y1

# --- 3. UNIT ECONOMICS ENGINE ---
max_theoretical_km = active_hours_per_day * avg_speed_kmh
theoretical_deadhead_km = max_theoretical_km * deadhead_rate
max_billable_km_theoretical = max_theoretical_km - theoretical_deadhead_km
distance_lost_per_dwell_km = (avg_speed_kmh / 60) * dwell_time_mins
effective_trip_distance_km = avg_trip_distance_km + distance_lost_per_dwell_km

actual_trips_per_day = np.floor(max_billable_km_theoretical / effective_trip_distance_km)
actual_billable_km_per_day = actual_trips_per_day * avg_trip_distance_km
actual_total_km_per_day = actual_billable_km_per_day / (1 - deadhead_rate)

base_fare_rev_per_day_gross = actual_trips_per_day * base_fare_eur
distance_rev_per_day_gross = actual_billable_km_per_day * price_per_km_eur
gross_booking_value_per_day_per_car = base_fare_rev_per_day_gross + distance_rev_per_day_gross

# --- 4. MULTI-YEAR GENERATOR (P&L AND CASH FLOW) ---
years = ["Year 1 (2028)", "Year 2 (2029)", "Year 3 (2030)", "Year 4 (2031)", "Year 5 (2032)"]

pnl_data_dict = {
    loc["pnl_gbv"]: [], loc["pnl_vat"]: [], loc["pnl_net_rev"]: [], loc["pnl_tesla_fee"]: [],
    loc["pnl_mrrg_net"]: [], loc["pnl_energy"]: [], loc["pnl_wear"]: [], loc["pnl_clean"]: [],
    loc["pnl_db1"]: [], loc["pnl_ins"]: [], loc["pnl_park"]: [], loc["pnl_api"]: [],
    loc["pnl_tuev"]: [], loc["pnl_sub"]: [], loc["pnl_db2"]: [], loc["pnl_hq_lease"]: [],
    loc["pnl_it"]: [], loc["pnl_legal"]: [], loc["pnl_hq_ins"]: [], loc["pnl_fees"]: [],
    loc["pnl_bank"]: [], loc["pnl_thg"]: [], loc["pnl_salvage"]: [], loc["pnl_ebitda"]: [],
    loc["pnl_afa_veh"]: [], loc["pnl_afa_it"]: [], loc["pnl_ebit"]: [], loc["pnl_int_inc"]: [],
    loc["pnl_int_exp"]: [], loc["pnl_ebt"]: [], loc["pnl_tax"]: [], loc["pnl_ni"]: []
}

cf_data_dict = {
    loc["cf_ni"]: [], loc["cf_depr"]: [], loc["cf_tax_prov"]: [], loc["cf_tax_paid"]: [],
    loc["cf_op"]: [], loc["cf_capex"]: [], loc["cf_inv"]: [], loc["cf_eq"]: [],
    loc["cf_sh"]: [], loc["cf_kfw_draw"]: [], loc["cf_prin"]: [], loc["cf_vat_draw"]: [],
    loc["cf_vat_repay"]: [], loc["cf_fin"]: [], loc["cf_net"]: [], loc["cf_beg"]: [],
    loc["cf_end"]: []
}

months_per_year = 12
tax_schedule = {1: 0.23520, 2: 0.22465, 3: 0.21410, 4: 0.20355, 5: 0.19300}

# CF Trackers - Initialized at 0. Capital flows hit Y1 Cash Flow Statement.
current_cash_balance = 0 
previous_tax_expense = 0
it_hardware_afa_per_year = it_hardware_capex_y1 / 3  

active_fleet_by_year = []

for year in range(1, 6):
    active_cohorts = [c for c in range(1, year + 1) if year <= c + 3]
    active_fleet = sum(cohort_data[c]["size"] for c in active_cohorts)
    active_fleet_by_year.append(active_fleet)
    operating_days = (365 * vehicle_utilization)
    
    annual_gbv_fleet = gross_booking_value_per_day_per_car * operating_days * active_fleet
    annual_net_revenue_fleet = annual_gbv_fleet / (1 + vat_rate)
    annual_vat_owed = annual_gbv_fleet - annual_net_revenue_fleet
    annual_tesla_fees = annual_gbv_fleet * tesla_take_rate
    mrrg_net_revenue = annual_net_revenue_fleet - annual_tesla_fees
    
    total_km_annual_fleet = actual_total_km_per_day * operating_days * active_fleet
    annual_wear_cost = total_km_annual_fleet * wear_and_tear_rate
    annual_energy_cost = total_km_annual_fleet * energy_rate
    annual_cleaning_cost = cleaning_cost_per_day * operating_days * active_fleet
    deckungsbeitrag_1 = mrrg_net_revenue - annual_energy_cost - annual_wear_cost - annual_cleaning_cost
    
    annual_insurance = insurance_pm * months_per_year * active_fleet
    annual_parking = parking_pm * months_per_year * active_fleet
    annual_telemetry = telemetry_pm * months_per_year * active_fleet
    annual_tuev = tuev_pm * months_per_year * active_fleet
    annual_charging_sub = charging_sub_pm * months_per_year * active_fleet
    total_annual_vehicle_fixed_costs = annual_insurance + annual_parking + annual_telemetry + annual_tuev + annual_charging_sub
    deckungsbeitrag_2 = deckungsbeitrag_1 - total_annual_vehicle_fixed_costs
    
    additional_cars = max(0, active_fleet - fleet_size)
    annual_hq_lease = hq_lease_pm * months_per_year
    annual_it_cloud = it_cloud_pm * months_per_year
    annual_legal = ((legal_bookkeeping_pm + (legal_scaling_pm * additional_cars)) * months_per_year) + (setup_costs_y1 if year == 1 else 0)
    annual_hq_insurance = (hq_insurance_pm + (insurance_scaling_pm * additional_cars)) * months_per_year
    annual_fees = (ihk_pm * months_per_year) + (gez_pm_per_car * months_per_year * active_fleet)
    annual_bank = bank_fees_pm * months_per_year
    
    annual_thg = thg_quote_per_car_py * active_fleet
    fleet_sale_revenue = 0
    current_vehicle_afa = 0
    interest_expense = 0
    total_principal_payment = 0
    
    for c in range(1, year + 1):
        if cohort_data[c]["size"] == 0: continue
        if year <= c + 3: current_vehicle_afa += cohort_data[c]["afa_per_yr"]
        if year == c + 3: fleet_sale_revenue += cohort_data[c]["size"] * salvage_value_per_car_y4
            
        interest_expense += cohort_data[c]["loan_bal"] * cohort_data[c]["rate"]
        if year > c:
            prin = cohort_data[c]["original_loan"] / 4
            if cohort_data[c]["loan_bal"] - prin < 0: prin = cohort_data[c]["loan_bal"]
            total_principal_payment += prin
            cohort_data[c]["loan_bal"] -= prin

    current_it_afa = it_hardware_afa_per_year if year <= 3 else 0
    
    ebitda = (deckungsbeitrag_2 - annual_hq_lease - annual_it_cloud - annual_legal 
              - annual_hq_insurance - annual_fees - annual_bank + annual_thg + fleet_sale_revenue)
    ebit = ebitda - current_vehicle_afa - current_it_afa
    
    interest_income = current_cash_balance * interest_income_rate if current_cash_balance > 0 else 0
    
    # Y1 VAT Bridge Loan Logic
    vat_bridge_draw = 0
    vat_bridge_repay = 0
    vat_bridge_interest = 0
    
    capex_this_year = cohort_data[year]["size"] * total_capex_per_car if cohort_data[year]["size"] > 0 else 0
    if year == 1: 
        capex_this_year += it_hardware_capex_y1
        vat_on_capex = capex_this_year * vat_rate
        vat_bridge_draw = vat_on_capex
        vat_bridge_repay = -vat_on_capex
        vat_bridge_interest = vat_on_capex * 0.08 * (6/12)
        interest_expense += vat_bridge_interest
        
    ebt = ebit + interest_income - interest_expense
    current_tax_rate = tax_schedule[year]
    tax_expense = ebt * current_tax_rate if ebt > 0 else 0
    net_income = ebt - tax_expense
    
    # LAYER 8: HGB CASH FLOW STATEMENT LOGIC
    tax_provision_increase = tax_expense
    tax_paid = -previous_tax_expense
    previous_tax_expense = tax_expense
    
    operating_cf = net_income + current_vehicle_afa + current_it_afa + tax_provision_increase + tax_paid
    investing_cf = -capex_this_year
    
    equity_in = stammkapital if year == 1 else 0
    sh_loan_in = shareholder_loan if year == 1 else 0
    kfw_draw = cohort_data[year]["original_loan"] if cohort_data[year]["size"] > 0 else 0
    
    financing_cf = equity_in + sh_loan_in + kfw_draw - total_principal_payment + vat_bridge_draw + vat_bridge_repay
    
    net_cash_change = operating_cf + investing_cf + financing_cf
    beg_cash = current_cash_balance
    end_cash = beg_cash + net_cash_change
    current_cash_balance = end_cash
    
    pnl_data_dict[loc["pnl_gbv"]].append(annual_gbv_fleet)
    pnl_data_dict[loc["pnl_vat"]].append(-annual_vat_owed)
    pnl_data_dict[loc["pnl_net_rev"]].append(annual_net_revenue_fleet)
    pnl_data_dict[loc["pnl_tesla_fee"]].append(-annual_tesla_fees)
    pnl_data_dict[loc["pnl_mrrg_net"]].append(mrrg_net_revenue)
    pnl_data_dict[loc["pnl_energy"]].append(-annual_energy_cost)
    pnl_data_dict[loc["pnl_wear"]].append(-annual_wear_cost)
    pnl_data_dict[loc["pnl_clean"]].append(-annual_cleaning_cost)
    pnl_data_dict[loc["pnl_db1"]].append(deckungsbeitrag_1)
    pnl_data_dict[loc["pnl_ins"]].append(-annual_insurance)
    pnl_data_dict[loc["pnl_park"]].append(-annual_parking)
    pnl_data_dict[loc["pnl_api"]].append(-annual_telemetry)
    pnl_data_dict[loc["pnl_tuev"]].append(-annual_tuev)
    pnl_data_dict[loc["pnl_sub"]].append(-annual_charging_sub)
    pnl_data_dict[loc["pnl_db2"]].append(deckungsbeitrag_2)
    pnl_data_dict[loc["pnl_hq_lease"]].append(-annual_hq_lease)
    pnl_data_dict[loc["pnl_it"]].append(-annual_it_cloud)
    pnl_data_dict[loc["pnl_legal"]].append(-annual_legal)
    pnl_data_dict[loc["pnl_hq_ins"]].append(-annual_hq_insurance)
    pnl_data_dict[loc["pnl_fees"]].append(-annual_fees)
    pnl_data_dict[loc["pnl_bank"]].append(-annual_bank)
    pnl_data_dict[loc["pnl_thg"]].append(annual_thg)
    pnl_data_dict[loc["pnl_salvage"]].append(fleet_sale_revenue)
    pnl_data_dict[loc["pnl_ebitda"]].append(ebitda)
    pnl_data_dict[loc["pnl_afa_veh"]].append(-current_vehicle_afa)
    pnl_data_dict[loc["pnl_afa_it"]].append(-current_it_afa)
    pnl_data_dict[loc["pnl_ebit"]].append(ebit)
    pnl_data_dict[loc["pnl_int_inc"]].append(interest_income)
    pnl_data_dict[loc["pnl_int_exp"]].append(-interest_expense)
    pnl_data_dict[loc["pnl_ebt"]].append(ebt)
    pnl_data_dict[loc["pnl_tax"]].append(-tax_expense)
    pnl_data_dict[loc["pnl_ni"]].append(net_income)

    cf_data_dict[loc["cf_ni"]].append(net_income)
    cf_data_dict[loc["cf_depr"]].append(current_vehicle_afa + current_it_afa)
    cf_data_dict[loc["cf_tax_prov"]].append(tax_provision_increase)
    cf_data_dict[loc["cf_tax_paid"]].append(tax_paid)
    cf_data_dict[loc["cf_op"]].append(operating_cf)
    cf_data_dict[loc["cf_capex"]].append(investing_cf)
    cf_data_dict[loc["cf_inv"]].append(investing_cf)
    cf_data_dict[loc["cf_eq"]].append(equity_in)
    cf_data_dict[loc["cf_sh"]].append(sh_loan_in)
    cf_data_dict[loc["cf_kfw_draw"]].append(kfw_draw)
    cf_data_dict[loc["cf_prin"]].append(-total_principal_payment)
    cf_data_dict[loc["cf_vat_draw"]].append(vat_bridge_draw)
    cf_data_dict[loc["cf_vat_repay"]].append(vat_bridge_repay)
    cf_data_dict[loc["cf_fin"]].append(financing_cf)
    cf_data_dict[loc["cf_net"]].append(net_cash_change)
    cf_data_dict[loc["cf_beg"]].append(beg_cash)
    cf_data_dict[loc["cf_end"]].append(end_cash)

# --- 5. DASHBOARD RENDER ---
st.subheader(loc["sources_title"])
colA, colB, colC, colD = st.columns(4)
colA.metric(loc["src_stamm"], f"€ {stammkapital:,.0f}")
colB.metric(loc["src_sh"], f"€ {shareholder_loan:,.0f}")
colC.metric(f"{loc['src_veh']} ({vehicle_ltv*100:.0f}%)", f"€ {cohort_data[1]['original_loan']:,.0f}")
colD.metric(loc["liquidity"], f"€ {day_1_cash_balance_ui:,.0f}")

st.divider()
st.subheader(loc["output_title"])

fleet_cols = st.columns(5)
for i, year in enumerate(years):
    fleet_cols[i].metric(f"{loc['active_fleet']} ({year})", f"{active_fleet_by_year[i]:.0f} {loc['cars']}")

st.write("") 

tabs = st.tabs([loc["tab_pnl"], loc["tab_cf"], loc["tab_bs"]])

with tabs[0]:
    df_pnl = pd.DataFrame(pnl_data_dict, index=years).T
    
    def style_pnl_rows(row):
        style = [''] * len(row)
        if loc["pnl_mrrg_net"] in row.name:
            style = ['font-weight: 600; border-top: 1px solid #ffffff40; color: #4DA8DA;'] * len(row)
        elif loc["pnl_db1"] in row.name or loc["pnl_db2"] in row.name:
            style = ['font-weight: 600; background-color: #1e1e1e; border-top: 1px solid #ffffff40;'] * len(row)
        elif loc["pnl_ebitda"] in row.name:
            style = ['font-weight: 700; background-color: #2b2b2b; color: #F2A900;'] * len(row)
        elif loc["pnl_ebit"] in row.name:
            style = ['font-weight: 600; background-color: #1e1e1e;'] * len(row)
        elif loc["pnl_ebt"] in row.name:
            style = ['font-weight: 600; border-top: 1px solid #ffffff40;'] * len(row)
        elif loc["pnl_ni"] in row.name:
            style = ['font-weight: 700; background-color: #0b2e13; color: #38c172; font-size: 1.05em; border-top: 2px solid #38c172;'] * len(row)
        return style

    styled_df = df_pnl.style.format("{:,.0f} €").apply(style_pnl_rows, axis=1)
    st.dataframe(styled_df, use_container_width=True)

with tabs[1]:
    df_cf = pd.DataFrame(cf_data_dict, index=years).T
    
    def style_cf_rows(row):
        style = [''] * len(row)
        if loc["cf_op"] in row.name or loc["cf_inv"] in row.name or loc["cf_fin"] in row.name:
            style = ['font-weight: 700; background-color: #1e1e1e; color: #4DA8DA; border-top: 1px solid #ffffff40;'] * len(row)
        elif loc["cf_net"] in row.name:
            style = ['font-weight: 700; background-color: #2b2b2b; color: #F2A900;'] * len(row)
        elif loc["cf_end"] in row.name:
            style = ['font-weight: 700; background-color: #0b2e13; color: #38c172; font-size: 1.05em; border-top: 2px solid #38c172;'] * len(row)
        return style

    styled_cf = df_cf.style.format("{:,.0f} €").apply(style_cf_rows, axis=1)
    st.dataframe(styled_cf, use_container_width=True)

with tabs[2]:
    st.markdown(loc["bs_note"])
