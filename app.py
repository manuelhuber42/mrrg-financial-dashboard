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
        "subtitle": "*(HGB Accounting for a GmbH - Layer 8: 60-Month Cohort Scaling & CF)*",
        "sec1": "1. FLEET SCALING SCHEDULE",
        "y1_adds": "Year 1 Additions (Jan-Dec)",
        "y2_adds": "Year 2 Additions (Jan-Dec)",
        "y3_adds": "Year 3 Additions (Jan-Dec)",
        "y4_adds": "Year 4 Additions (Jan-Dec)",
        "y5_adds": "Year 5 Additions (Jan-Dec)",
        "utilization": "Vehicle Utilization / Uptime (%)",
        "active_hours": "Active Hours / Day",
        "speed": "Average Speed (km/h)",
        "deadhead": "Deadhead Rate (%)",
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
        
        "cf_ni": "Net Income (Jahresüberschuss)",
        "cf_depr": "Depreciation (AfA)",
        "cf_tax_prov": "Increase in Tax Provision",
        "cf_tax_paid": "Taxes Paid (Month 5 of Following Year)",
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
        
        "sources_title": "Day 1 Sources & Uses of Capital",
        "src_stamm": "Sources: Stammkapital",
        "src_sh": "Sources: Shareholder Loan",
        "src_veh": "Sources: Vehicle Loan",
        "liquidity": "Day 1 Liquidity Buffer",
        "output_title": "Master Financial Schedules (HGB)",
        "active_fleet": "Active Fleet",
        "cars": "Vehicles",
        "tab_pnl": "Income Statement (P&L)",
        "tab_cf": "Cash Flow Statement",
        "tab_bs": "Balance Sheet",
        "view_mode": "Display Granularity",
        "yearly": "Yearly Overview",
        "monthly": "Monthly Drilldown"
    }
else:
    loc = {
        "title": "MRRG Cybercab-Flotte: Master-Finanzmodell",
        "subtitle": "*(HGB-Rechnungslegung für eine GmbH - Layer 8: 60-Monate Kohorten-Skalierung)*",
        "sec1": "1. FLOTTENSKALIERUNG",
        "y1_adds": "Jahr 1 Zugänge (Jan-Dez)",
        "y2_adds": "Jahr 2 Zugänge (Jan-Dez)",
        "y3_adds": "Jahr 3 Zugänge (Jan-Dez)",
        "y4_adds": "Jahr 4 Zugänge (Jan-Dez)",
        "y5_adds": "Jahr 5 Zugänge (Jan-Dez)",
        "utilization": "Fahrzeugauslastung / Uptime (%)",
        "active_hours": "Aktive Stunden / Tag",
        "speed": "Durchschnittsgeschwindigkeit (km/h)",
        "deadhead": "Leerfahrten-Quote (%)",
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
        
        "cf_ni": "Jahresüberschuss",
        "cf_depr": "Abschreibungen (AfA)",
        "cf_tax_prov": "Zunahme Steuerrückstellungen",
        "cf_tax_paid": "Gezahlte Steuern (Vorjahr, fällig in Monat 5)",
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
        
        "sources_title": "Tag 1 Mittelherkunft & Mittelverwendung",
        "src_stamm": "Mittelherkunft: Stammkapital",
        "src_sh": "Mittelherkunft: Gesellschafterdarlehen",
        "src_veh": "Mittelherkunft: Fahrzeugdarlehen",
        "liquidity": "Tag 1 Liquiditätspuffer",
        "output_title": "Master-Finanzpläne (HGB)",
        "active_fleet": "Aktive Flotte",
        "cars": "Fahrzeuge",
        "tab_pnl": "Gewinn- und Verlustrechnung (GuV)",
        "tab_cf": "Kapitalflussrechnung",
        "tab_bs": "Bilanz",
        "view_mode": "Darstellung",
        "yearly": "Jährlich",
        "monthly": "Monatlich (Detailansicht)"
    }

st.title(loc["title"])
st.markdown(loc["subtitle"])

# --- 1. THE PHYSICS & REVENUE ASSUMPTIONS ---
st.sidebar.header(loc["sec1"])
st.sidebar.markdown("*Format: Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec*")
y1_adds_str = st.sidebar.text_input(loc["y1_adds"], "3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0")
y2_adds_str = st.sidebar.text_input(loc["y2_adds"], "2, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0")
y3_adds_str = st.sidebar.text_input(loc["y3_adds"], "3, 0, 0, 3, 0, 0, 3, 0, 0, 3, 0, 0")
y4_adds_str = st.sidebar.text_input(loc["y4_adds"], "4, 0, 0, 4, 0, 0, 4, 0, 0, 3, 0, 0")
y5_adds_str = st.sidebar.text_input(loc["y5_adds"], "6, 0, 0, 5, 0, 0, 5, 0, 0, 5, 0, 0")

def parse_adds(add_str):
    try:
        arr = [int(x.strip()) for x in add_str.split(',')]
        return (arr + [0]*12)[:12]
    except:
        return [0]*12

all_adds = parse_adds(y1_adds_str) + parse_adds(y2_adds_str) + parse_adds(y3_adds_str) + parse_adds(y4_adds_str) + parse_adds(y5_adds_str)
base_fleet_size = sum(parse_adds(y1_adds_str))

vehicle_utilization = st.sidebar.number_input(loc["utilization"], value=90.0) / 100
active_hours_per_day = st.sidebar.number_input(loc["active_hours"], value=16.0)
avg_speed_kmh = st.sidebar.number_input(loc["speed"], value=22.0)
deadhead_rate = st.sidebar.number_input(loc["deadhead"], value=30.0) / 100

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

# --- 2. CAPEX & COHORT ENGINE ---
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
        rate = 0.045 if m < 12 else 0.055
        cohorts.append({
            "start_month": m + 1,
            "size": mo_val,
            "capex": capex,
            "original_loan": loan,
            "loan_bal": loan,
            "rate": rate,
            "afa_per_mo": capex / 48
        })

# --- 3. UNIT ECONOMICS ---
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

# --- 4. 60-MONTH LOOP MATRIX ---
pnl_keys = [
    loc["pnl_gbv"], loc["pnl_vat"], loc["pnl_net_rev"], loc["pnl_tesla_fee"], loc["pnl_mrrg_net"],
    loc["pnl_energy"], loc["pnl_wear"], loc["pnl_clean"], loc["pnl_db1"], loc["pnl_ins"], loc["pnl_park"],
    loc["pnl_api"], loc["pnl_tuev"], loc["pnl_sub"], loc["pnl_db2"], loc["pnl_hq_lease"], loc["pnl_it"],
    loc["pnl_legal"], loc["pnl_hq_ins"], loc["pnl_fees"], loc["pnl_bank"], loc["pnl_thg"], loc["pnl_salvage"],
    loc["pnl_ebitda"], loc["pnl_afa_veh"], loc["pnl_afa_it"], loc["pnl_ebit"], loc["pnl_int_inc"], loc["pnl_int_exp"],
    loc["pnl_ebt"], loc["pnl_tax"], loc["pnl_ni"]
]

cf_keys = [
    loc["cf_ni"], loc["cf_depr"], loc["cf_tax_prov"], loc["cf_tax_paid"], loc["cf_op"], loc["cf_capex"],
    loc["cf_inv"], loc["cf_eq"], loc["cf_sh"], loc["cf_kfw_draw"], loc["cf_prin"], loc["cf_vat_draw"],
    loc["cf_vat_repay"], loc["cf_fin"], loc["cf_net"], loc["cf_beg"], loc["cf_end"]
]

pnl_monthly = {k: [] for k in pnl_keys}
cf_monthly = {k: [] for k in cf_keys}

tax_schedule = {1: 0.23520, 2: 0.22465, 3: 0.21410, 4: 0.20355, 5: 0.19300}

current_cash = 0
vat_loan_bal = 0
vat_repay_schedule = [0]*70 
tax_payment_schedule = [0]*70
cum_ebt_year = 0

active_fleet_by_month = []

# Day 1 Math for UI Cards (M1 Only)
day_1_loan = sum(c["original_loan"] for c in cohorts if c["start_month"] == 1)
day_1_uses = (day_1_loan / vehicle_ltv) + it_hardware_capex_y1 if day_1_loan > 0 else 0
day_1_cash_ui = stammkapital + shareholder_loan + day_1_loan - day_1_uses

for m in range(60):
    current_month = m + 1
    current_year = (m // 12) + 1
    
    active_fleet = 0
    current_veh_afa = 0
    fleet_sale_rev = 0
    int_exp = 0
    prin_pay = 0
    kfw_draw = 0
    capex_this_mo = 0
    
    for c in cohorts:
        c_start = c["start_month"]
        if current_month == c_start:
            kfw_draw += c["original_loan"]
            capex_this_mo += c["capex"]
            
        if current_month >= c_start and current_month < c_start + 48:
            active_fleet += c["size"]
            current_veh_afa += c["afa_per_mo"]
            int_exp += c["loan_bal"] * (c["rate"] / 12)
            
            if current_month > c_start + 12:
                prin = c["original_loan"] / 48
                if c["loan_bal"] - prin < 0: prin = c["loan_bal"]
                prin_pay += prin
                c["loan_bal"] -= prin
                
        if current_month == c_start + 48:
            fleet_sale_rev += c["size"] * salvage_value_per_car_y4

    active_fleet_by_month.append(active_fleet)
    
    if current_month == 1:
        capex_this_mo += it_hardware_capex_y1
    current_it_afa = (it_hardware_capex_y1 / 36) if current_month <= 36 else 0
    
    days_in_mo = 365 / 12
    op_days = days_in_mo * vehicle_utilization
    
    gbv_mo = gross_booking_value_per_day_per_car * op_days * active_fleet
    net_rev_mo = gbv_mo / (1 + vat_rate)
    vat_owed_mo = gbv_mo - net_rev_mo
    tesla_fee_mo = gbv_mo * tesla_take_rate
    mrrg_net_mo = net_rev_mo - tesla_fee_mo
    
    total_km_mo = actual_total_km_per_day * op_days * active_fleet
    wear_mo = total_km_mo * wear_and_tear_rate
    energy_mo = total_km_mo * energy_rate
    clean_mo = cleaning_cost_per_day * op_days * active_fleet
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
    
    thg_mo = (thg_quote_per_car_py * active_fleet) if (current_month % 12 == 0) else 0
    
    ebitda_mo = db2_mo - hq_lease_mo - it_cloud_mo - legal_mo - hq_ins_mo - fees_mo - bank_fees_pm + thg_mo + fleet_sale_rev
    ebit_mo = ebitda_mo - current_veh_afa - current_it_afa
    
    int_inc_mo = current_cash * (interest_income_rate / 12) if current_cash > 0 else 0
    
    # VAT Bridge Loan (Drawn on CapEx, repaid 6 months later)
    vat_draw_mo = capex_this_mo * vat_rate
    vat_loan_bal += vat_draw_mo
    vat_repay_schedule[current_month + 6] += vat_draw_mo
    
    vat_repay_mo = vat_repay_schedule[current_month]
    vat_loan_bal -= vat_repay_mo
    vat_int_mo = vat_loan_bal * (0.08 / 12)
    int_exp += vat_int_mo
    
    ebt_mo = ebit_mo + int_inc_mo - int_exp
    cum_ebt_year += ebt_mo
    
    # Year-End Tax Provision
    tax_exp_mo = 0
    if current_month % 12 == 0:
        tax_exp_mo = max(0, cum_ebt_year) * tax_schedule[current_year]
        cum_ebt_year = 0
        tax_payment_schedule[current_month + 5] = tax_exp_mo # Paid in M5 of following year
        
    net_inc_mo = ebt_mo - tax_exp_mo
    
    # Cash Flow Logic
    tax_prov_mo = tax_exp_mo
    tax_paid_mo = -tax_payment_schedule[current_month]
    
    op_cf_mo = net_inc_mo + current_veh_afa + current_it_afa + tax_prov_mo + tax_paid_mo
    inv_cf_mo = -capex_this_mo
    
    eq_in = stammkapital if current_month == 1 else 0
    sh_in = shareholder_loan if current_month == 1 else 0
    fin_cf_mo = eq_in + sh_in + kfw_draw - prin_pay + vat_draw_mo - vat_repay_mo
    
    net_cf_mo = op_cf_mo + inv_cf_mo + fin_cf_mo
    beg_cash = current_cash
    end_cash = beg_cash + net_cf_mo
    current_cash = end_cash
    
    # Append P&L
    pnl_monthly[loc["pnl_gbv"]].append(gbv_mo)
    pnl_monthly[loc["pnl_vat"]].append(-vat_owed_mo)
    pnl_monthly[loc["pnl_net_rev"]].append(net_rev_mo)
    pnl_monthly[loc["pnl_tesla_fee"]].append(-tesla_fee_mo)
    pnl_monthly[loc["pnl_mrrg_net"]].append(mrrg_net_mo)
    pnl_monthly[loc["pnl_energy"]].append(-energy_mo)
    pnl_monthly[loc["pnl_wear"]].append(-wear_mo)
    pnl_monthly[loc["pnl_clean"]].append(-clean_mo)
    pnl_monthly[loc["pnl_db1"]].append(db1_mo)
    pnl_monthly[loc["pnl_ins"]].append(-ins_mo)
    pnl_monthly[loc["pnl_park"]].append(-park_mo)
    pnl_monthly[loc["pnl_api"]].append(-tel_mo)
    pnl_monthly[loc["pnl_tuev"]].append(-tuev_mo)
    pnl_monthly[loc["pnl_sub"]].append(-sub_mo)
    pnl_monthly[loc["pnl_db2"]].append(db2_mo)
    pnl_monthly[loc["pnl_hq_lease"]].append(-hq_lease_mo)
    pnl_monthly[loc["pnl_it"]].append(-it_cloud_mo)
    pnl_monthly[loc["pnl_legal"]].append(-legal_mo)
    pnl_monthly[loc["pnl_hq_ins"]].append(-hq_ins_mo)
    pnl_monthly[loc["pnl_fees"]].append(-fees_mo)
    pnl_monthly[loc["pnl_bank"]].append(-bank_fees_pm)
    pnl_monthly[loc["pnl_thg"]].append(thg_mo)
    pnl_monthly[loc["pnl_salvage"]].append(fleet_sale_rev)
    pnl_monthly[loc["pnl_ebitda"]].append(ebitda_mo)
    pnl_monthly[loc["pnl_afa_veh"]].append(-current_veh_afa)
    pnl_monthly[loc["pnl_afa_it"]].append(-current_it_afa)
    pnl_monthly[loc["pnl_ebit"]].append(ebit_mo)
    pnl_monthly[loc["pnl_int_inc"]].append(int_inc_mo)
    pnl_monthly[loc["pnl_int_exp"]].append(-int_exp)
    pnl_monthly[loc["pnl_ebt"]].append(ebt_mo)
    pnl_monthly[loc["pnl_tax"]].append(-tax_exp_mo)
    pnl_monthly[loc["pnl_ni"]].append(net_inc_mo)
    
    # Append CF
    cf_monthly[loc["cf_ni"]].append(net_inc_mo)
    cf_monthly[loc["cf_depr"]].append(current_veh_afa + current_it_afa)
    cf_monthly[loc["cf_tax_prov"]].append(tax_prov_mo)
    cf_monthly[loc["cf_tax_paid"]].append(tax_paid_mo)
    cf_monthly[loc["cf_op"]].append(op_cf_mo)
    cf_monthly[loc["cf_capex"]].append(inv_cf_mo)
    cf_monthly[loc["cf_inv"]].append(inv_cf_mo)
    cf_monthly[loc["cf_eq"]].append(eq_in)
    cf_monthly[loc["cf_sh"]].append(sh_in)
    cf_monthly[loc["cf_kfw_draw"]].append(kfw_draw)
    cf_monthly[loc["cf_prin"]].append(-prin_pay)
    cf_monthly[loc["cf_vat_draw"]].append(vat_draw_mo)
    cf_monthly[loc["cf_vat_repay"]].append(-vat_repay_mo)
    cf_monthly[loc["cf_fin"]].append(fin_cf_mo)
    cf_monthly[loc["cf_net"]].append(net_cf_mo)
    cf_monthly[loc["cf_beg"]].append(beg_cash)
    cf_monthly[loc["cf_end"]].append(end_cash)

# --- 5. AGGREGATE TO YEARLY ---
def agg_to_yearly(monthly_dict, is_balances=False):
    yearly_dict = {}
    for key, arr in monthly_dict.items():
        yearly_arr = []
        for y in range(5):
            chunk = arr[y*12 : (y+1)*12]
            if loc["cf_end"] in key:
                yearly_arr.append(chunk[-1])
            elif loc["cf_beg"] in key:
                yearly_arr.append(chunk[0])
            else:
                yearly_arr.append(sum(chunk))
        yearly_dict[key] = yearly_arr
    return yearly_dict

pnl_yearly = agg_to_yearly(pnl_monthly)
cf_yearly = agg_to_yearly(cf_monthly)

year_cols = [f"Year {y+1}" for y in range(5)]
month_cols = [f"Y{(m//12)+1}-M{(m%12)+1}" for m in range(60)]

# --- 6. DASHBOARD RENDER ---
st.subheader(loc["sources_title"])
colA, colB, colC, colD = st.columns(4)
colA.metric(loc["src_stamm"], f"€ {stammkapital:,.0f}")
colB.metric(loc["src_sh"], f"€ {shareholder_loan:,.0f}")
colC.metric(f"{loc['src_veh']} ({vehicle_ltv*100:.0f}%)", f"€ {day_1_loan:,.0f}")
colD.metric(loc["liquidity"], f"€ {day_1_cash_ui:,.0f}")

st.divider()

col_title, col_toggle = st.columns([1, 1])
col_title.subheader(loc["output_title"])
view_choice = col_toggle.radio(loc["view_mode"], [loc["yearly"], loc["monthly"]], horizontal=True)

fleet_cols = st.columns(5)
for i in range(5):
    yr_fleet_val = active_fleet_by_month[(i*12)+11]
    fleet_cols[i].metric(f"{loc['active_fleet']} (Y{i+1} End)", f"{yr_fleet_val:.0f} {loc['cars']}")

st.write("") 

tabs = st.tabs([loc["tab_pnl"], loc["tab_cf"], loc["tab_bs"]])

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

def style_cf_rows(row):
    style = [''] * len(row)
    if loc["cf_op"] in row.name or loc["cf_inv"] in row.name or loc["cf_fin"] in row.name:
        style = ['font-weight: 700; background-color: #1e1e1e; color: #4DA8DA; border-top: 1px solid #ffffff40;'] * len(row)
    elif loc["cf_net"] in row.name:
        style = ['font-weight: 700; background-color: #2b2b2b; color: #F2A900;'] * len(row)
    elif loc["cf_end"] in row.name:
        style = ['font-weight: 700; background-color: #0b2e13; color: #38c172; font-size: 1.05em; border-top: 2px solid #38c172;'] * len(row)
    return style

with tabs[0]:
    if view_choice == loc["yearly"]:
        df_pnl = pd.DataFrame(pnl_yearly, index=year_cols).T
    else:
        df_pnl = pd.DataFrame(pnl_monthly, index=month_cols).T
    st.dataframe(df_pnl.style.format("{:,.0f} €").apply(style_pnl_rows, axis=1), use_container_width=True)

with tabs[1]:
    if view_choice == loc["yearly"]:
        df_cf = pd.DataFrame(cf_yearly, index=year_cols).T
    else:
        df_cf = pd.DataFrame(cf_monthly, index=month_cols).T
    st.dataframe(df_cf.style.format("{:,.0f} €").apply(style_cf_rows, axis=1), use_container_width=True)

with tabs[2]:
    st.markdown(loc["bs_note"])
