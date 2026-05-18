import streamlit as st
import pandas as pd
import numpy as np

# --- DASHBOARD CONFIGURATION & CUSTOM CSS ---
st.set_page_config(page_title="MRRG 3-Statement Financial Engine", layout="wide")

# Inject Urbanist Font and Global Styling
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

st.title("MRRG Cybercab Fleet: Master Financial Engine")
st.markdown("*(Layer 7: Multi-Cohort Fleet Scaling, Dynamic Overhead & Styling)*")

# --- 1. THE PHYSICS & REVENUE ASSUMPTIONS ---
st.sidebar.header("1a. BASE FLEET PHYSICS (Y1)")
fleet_size = st.sidebar.slider("Base Fleet Size (Num Cars)", 1, 50, 3)
vehicle_utilization = st.sidebar.number_input("Vehicle Utilization / Uptime (%)", value=95.0) / 100
active_hours_per_day = st.sidebar.number_input("Active Hours / Day", value=16.0)
avg_speed_kmh = st.sidebar.number_input("Average Speed (km/h)", value=22.0)
deadhead_rate = st.sidebar.number_input("Deadhead Rate (%)", value=30.0) / 100

st.sidebar.header("1b. FLEET SCALING (Additions)")
y2_adds = st.sidebar.number_input("Year 2 Additions", value=0)
y3_adds = st.sidebar.number_input("Year 3 Additions", value=0)
y4_adds = st.sidebar.number_input("Year 4 Additions", value=0)
y5_adds = st.sidebar.number_input("Year 5 Additions", value=0)

st.sidebar.header("2. TRIP DYNAMICS")
avg_trip_distance_km = st.sidebar.number_input("Average Trip Distance (km)", value=5.0)
dwell_time_mins = st.sidebar.number_input("Dwell Time (Minutes)", value=2.0)

st.sidebar.header("3. PRICING (Incl. 19% VAT)")
base_fare_eur = st.sidebar.number_input("Base Fare (€)", value=2.50)
price_per_km_eur = st.sidebar.number_input("Price per km (€)", value=1.49)
tesla_take_rate = st.sidebar.number_input("Tesla Take-Rate (%)", value=30.0) / 100
vat_rate = 0.19

st.sidebar.header("4. DAILY VARIABLE COSTS (Net)")
cleaning_cost_per_day = st.sidebar.number_input("Cleaning Cost per Car/Day (€)", value=3.00)

st.sidebar.header("5. VEHICLE FIXED COSTS (€ / Month, Net)")
insurance_pm = st.sidebar.number_input("Insurance", value=300.0)
parking_pm = st.sidebar.number_input("APCOA Parking", value=150.0)
telemetry_pm = st.sidebar.number_input("Telemetry & API", value=100.0)
tuev_pm = st.sidebar.number_input("TÜV / BO-Kraft Accrual", value=15.0)
charging_sub_pm = st.sidebar.number_input("Tesla Charging Sub", value=10.0)

st.sidebar.header("6. CORPORATE HQ & SCALING (€ / Month, Net)")
hq_lease_pm = st.sidebar.number_input("HQ Lease (Raumkosten)", value=450.0)
it_cloud_pm = st.sidebar.number_input("IT, Cloud & AI Services", value=320.0)
legal_bookkeeping_pm = st.sidebar.number_input("Base Legal & Bookkeeping", value=230.0)
hq_insurance_pm = st.sidebar.number_input("Base HQ Insurance (Liability)", value=250.0)
legal_scaling_pm = st.sidebar.number_input("Legal/Tax Scaling (per added car)", value=25.0)
insurance_scaling_pm = st.sidebar.number_input("Corp Insurance Scaling (per added car)", value=40.0)
bank_fees_pm = st.sidebar.number_input("Bank Fees", value=20.0)
ihk_pm = st.sidebar.number_input("IHK Membership", value=35.0)
gez_pm_per_car = st.sidebar.number_input("GEZ (per car)", value=7.0)
setup_costs_y1 = st.sidebar.number_input("One-off Setup Costs (Y1)", value=1700.0)

st.sidebar.header("7. CAPEX & DEPRECIATION")
cybercab_base_usd = st.sidebar.number_input("Base Cybercab Price (USD)", value=30000.0)
usd_eur_rate = st.sidebar.number_input("USD to EUR Exchange Rate", value=1.15)
import_freight_eur = st.sidebar.number_input("Import Freight & Ins. per Car (€)", value=1800.0)
customs_duty_rate = st.sidebar.number_input("Import Duty (Zoll) %", value=10.0) / 100
it_hardware_capex_y1 = st.sidebar.number_input("IT Hardware CapEx (Y1)", value=2500.0)

st.sidebar.header("8. CAPITAL STRUCTURE & FINANCING")
stammkapital = st.sidebar.number_input("Stammkapital (€)", value=25000.0)
shareholder_loan = st.sidebar.number_input("Shareholder Loan (€)", value=50000.0)
vehicle_ltv = st.sidebar.number_input("Vehicle Loan-to-Value (LTV) %", value=80.0) / 100
loan_cohort = st.sidebar.selectbox("Y1 Loan Type", ["KfW Gründerkredit (4.5%, 1yr Grace)"])
interest_income_rate = st.sidebar.number_input("Cash Interest Rate (%)", value=2.2) / 100

st.sidebar.header("9. OTHER INCOME / SALVAGE")
thg_quote_per_car_py = st.sidebar.number_input("THG Quote per car/yr", value=200.0)
salvage_value_per_car_y4 = st.sidebar.number_input("Vehicle Sale Price (Y4)", value=10000.0)

# --- 2. CAPEX & SOURCES/USES MATH ---
cybercab_base_eur = cybercab_base_usd / usd_eur_rate
zollwert_cif_eur = cybercab_base_eur + import_freight_eur
zollkosten_eur = zollwert_cif_eur * customs_duty_rate
total_capex_per_car = zollwert_cif_eur + zollkosten_eur

# Cohort Setup (Tracking independent sizes, loans, and AfA)
cohort_data = {}
additions = [fleet_size, y2_adds, y3_adds, y4_adds, y5_adds]

for c, size in enumerate(additions, start=1):
    capex = size * total_capex_per_car
    loan = capex * vehicle_ltv
    rate = 0.045 if c == 1 else 0.055  # Expansion loans hit the 5.5% rate
    cohort_data[c] = {
        "size": size,
        "original_loan": loan,
        "loan_bal": loan,
        "rate": rate,
        "afa_per_yr": capex / 4
    }

# Day 1 Math (Only funds Cohort 1)
total_uses_y1 = cohort_data[1]["original_loan"] / vehicle_ltv + it_hardware_capex_y1
day_1_cash_balance = stammkapital + shareholder_loan + cohort_data[1]["original_loan"] - total_uses_y1

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

# --- 4. MULTI-YEAR P&L GENERATOR ---
years = ["Year 1 (2028)", "Year 2 (2029)", "Year 3 (2030)", "Year 4 (2031)", "Year 5 (2032)"]
pnl_data_dict = {
    "Gross Booking Value (Customer Pays incl. 19% VAT)": [],
    "Less: 19% VAT (Finanzamt)": [],
    "Net Revenue (Umsatzerlöse excl. VAT)": [],
    "Less: Tesla Platform Fee (30% on GBV)": [],
    "MRRG Net Revenue (After Platform Fee)": [],
    "Less: Direct Energy (Variable)": [],
    "Less: Direct Maintenance/Wear (Variable)": [],
    "Less: Cleaning Cost (Variable)": [],
    "Deckungsbeitrag 1 (DB1)": [],
    "Less: Insurance (Fixed)": [],
    "Less: APCOA Parking (Fixed)": [],
    "Less: Telemetry & API (Fixed)": [],
    "Less: TÜV / BO-Kraft (Fixed)": [],
    "Less: Tesla Charging Sub (Fixed)": [],
    "Deckungsbeitrag 2 (DB2)": [],
    "Less: HQ Lease (Raumkosten)": [],
    "Less: IT, Cloud & AI Services": [],
    "Less: Legal, Tax & Bookkeeping (Scaled)": [],
    "Less: Corporate Insurance (Liability, D&O - Scaled)": [],
    "Less: Subscriptions & Fees (IHK, GEZ)": [],
    "Less: Bank Fees": [],
    "Add: THG Quote (Other Operating Income)": [],
    "Add: Fleet Liquidation (Asset Sale)": [],
    "EBITDA": [],
    "Less: Vehicle Depreciation (AfA - 48 Mo.)": [],
    "Less: IT Hardware Depreciation (AfA - 36 Mo.)": [],
    "EBIT (Operating Income)": [],
    "Add: Interest Income (Zinserträge)": [],
    "Less: Interest Expense (Zinsaufwendungen)": [],
    "EBT (Earnings Before Tax)": [],
    "Less: Corporate Taxes (Ertragsteuern)": [],
    "Net Income (Jahresüberschuss / EAT)": []
}

wear_and_tear_rate = 0.03 
energy_rate = 0.05
months_per_year = 12

tax_schedule = {1: 0.23520, 2: 0.22465, 3: 0.21410, 4: 0.20355, 5: 0.19300}

current_cash_balance = day_1_cash_balance
it_hardware_afa_per_year = it_hardware_capex_y1 / 3  

active_fleet_by_year = []

for year in range(1, 6):
    # Determine Active Fleet (Cohorts last 4 years. e.g. Y1 cohort active Y1-Y4)
    active_cohorts = [c for c in range(1, year + 1) if year <= c + 3]
    active_fleet = sum(cohort_data[c]["size"] for c in active_cohorts)
    active_fleet_by_year.append(active_fleet)
    
    operating_days = (365 * vehicle_utilization)
    
    # Cohort Equity Funding (Subtract from cash balance if new cohort launched this year)
    if year > 1 and cohort_data[year]["size"] > 0:
        new_capex = cohort_data[year]["size"] * total_capex_per_car
        new_loan = cohort_data[year]["original_loan"]
        new_equity_needed = new_capex - new_loan
        current_cash_balance -= new_equity_needed
    
    # Revenue
    annual_gbv_fleet = gross_booking_value_per_day_per_car * operating_days * active_fleet
    annual_net_revenue_fleet = annual_gbv_fleet / (1 + vat_rate)
    annual_vat_owed = annual_gbv_fleet - annual_net_revenue_fleet
    annual_tesla_fees = annual_gbv_fleet * tesla_take_rate
    mrrg_net_revenue = annual_net_revenue_fleet - annual_tesla_fees
    
    # Variable Costs
    total_km_annual_fleet = actual_total_km_per_day * operating_days * active_fleet
    annual_wear_cost = total_km_annual_fleet * wear_and_tear_rate
    annual_energy_cost = total_km_annual_fleet * energy_rate
    annual_cleaning_cost = cleaning_cost_per_day * operating_days * active_fleet
    deckungsbeitrag_1 = mrrg_net_revenue - annual_energy_cost - annual_wear_cost - annual_cleaning_cost
    
    # Vehicle Fixed Costs
    annual_insurance = insurance_pm * months_per_year * active_fleet
    annual_parking = parking_pm * months_per_year * active_fleet
    annual_telemetry = telemetry_pm * months_per_year * active_fleet
    annual_tuev = tuev_pm * months_per_year * active_fleet
    annual_charging_sub = charging_sub_pm * months_per_year * active_fleet
    total_annual_vehicle_fixed_costs = annual_insurance + annual_parking + annual_telemetry + annual_tuev + annual_charging_sub
    deckungsbeitrag_2 = deckungsbeitrag_1 - total_annual_vehicle_fixed_costs
    
    # Corporate HQ (Scaled Overhead Logic)
    additional_cars = max(0, active_fleet - fleet_size)
    
    annual_hq_lease = hq_lease_pm * months_per_year
    annual_it_cloud = it_cloud_pm * months_per_year
    annual_legal = ((legal_bookkeeping_pm + (legal_scaling_pm * additional_cars)) * months_per_year) + (setup_costs_y1 if year == 1 else 0)
    annual_hq_insurance = (hq_insurance_pm + (insurance_scaling_pm * additional_cars)) * months_per_year
    annual_fees = (ihk_pm * months_per_year) + (gez_pm_per_car * months_per_year * active_fleet)
    annual_bank = bank_fees_pm * months_per_year
    
    # Other Income & AfA & Financing per Cohort
    annual_thg = thg_quote_per_car_py * active_fleet
    fleet_sale_revenue = 0
    current_vehicle_afa = 0
    interest_expense = 0
    total_principal_payment = 0
    
    for c in range(1, year + 1):
        if cohort_data[c]["size"] == 0: continue
        
        # AfA (Active during 4-year lifecycle)
        if year <= c + 3:
            current_vehicle_afa += cohort_data[c]["afa_per_yr"]
            
        # Sale at end of 4th operating year
        if year == c + 3:
            fleet_sale_revenue += cohort_data[c]["size"] * salvage_value_per_car_y4
            
        # Interest paid on starting balance of the year
        interest_expense += cohort_data[c]["loan_bal"] * cohort_data[c]["rate"]
        
        # Principal (Starts 1 year after origination)
        if year > c:
            prin = cohort_data[c]["original_loan"] / 4
            if cohort_data[c]["loan_bal"] - prin < 0:
                prin = cohort_data[c]["loan_bal"]
            total_principal_payment += prin
            cohort_data[c]["loan_bal"] -= prin

    current_it_afa = it_hardware_afa_per_year if year <= 3 else 0
    
    # EBITDA & EBIT
    ebitda = (deckungsbeitrag_2 - annual_hq_lease - annual_it_cloud - annual_legal 
              - annual_hq_insurance - annual_fees - annual_bank + annual_thg + fleet_sale_revenue)
    
    ebit = ebitda - current_vehicle_afa - current_it_afa
    
    # FINANCING & TAXES
    interest_income = current_cash_balance * interest_income_rate if current_cash_balance > 0 else 0
    ebt = ebit + interest_income - interest_expense
    
    current_tax_rate = tax_schedule[year]
    tax_expense = ebt * current_tax_rate if ebt > 0 else 0
    net_income = ebt - tax_expense
    
    # Roll forward cash balance
    cash_movement = ebt + current_vehicle_afa + current_it_afa - total_principal_payment - tax_expense
    current_cash_balance += cash_movement
    
    # Append to Dictionary
    pnl_data_dict["Gross Booking Value (Customer Pays incl. 19% VAT)"].append(annual_gbv_fleet)
    pnl_data_dict["Less: 19% VAT (Finanzamt)"].append(-annual_vat_owed)
    pnl_data_dict["Net Revenue (Umsatzerlöse excl. VAT)"].append(annual_net_revenue_fleet)
    pnl_data_dict["Less: Tesla Platform Fee (30% on GBV)"].append(-annual_tesla_fees)
    pnl_data_dict["MRRG Net Revenue (After Platform Fee)"].append(mrrg_net_revenue)
    pnl_data_dict["Less: Direct Energy (Variable)"].append(-annual_energy_cost)
    pnl_data_dict["Less: Direct Maintenance/Wear (Variable)"].append(-annual_wear_cost)
    pnl_data_dict["Less: Cleaning Cost (Variable)"].append(-annual_cleaning_cost)
    pnl_data_dict["Deckungsbeitrag 1 (DB1)"].append(deckungsbeitrag_1)
    pnl_data_dict["Less: Insurance (Fixed)"].append(-annual_insurance)
    pnl_data_dict["Less: APCOA Parking (Fixed)"].append(-annual_parking)
    pnl_data_dict["Less: Telemetry & API (Fixed)"].append(-annual_telemetry)
    pnl_data_dict["Less: TÜV / BO-Kraft (Fixed)"].append(-annual_tuev)
    pnl_data_dict["Less: Tesla Charging Sub (Fixed)"].append(-annual_charging_sub)
    pnl_data_dict["Deckungsbeitrag 2 (DB2)"].append(deckungsbeitrag_2)
    pnl_data_dict["Less: HQ Lease (Raumkosten)"].append(-annual_hq_lease)
    pnl_data_dict["Less: IT, Cloud & AI Services"].append(-annual_it_cloud)
    pnl_data_dict["Less: Legal, Tax & Bookkeeping (Scaled)"].append(-annual_legal)
    pnl_data_dict["Less: Corporate Insurance (Liability, D&O - Scaled)"].append(-annual_hq_insurance)
    pnl_data_dict["Less: Subscriptions & Fees (IHK, GEZ)"].append(-annual_fees)
    pnl_data_dict["Less: Bank Fees"].append(-annual_bank)
    pnl_data_dict["Add: THG Quote (Other Operating Income)"].append(annual_thg)
    pnl_data_dict["Add: Fleet Liquidation (Asset Sale)"].append(fleet_sale_revenue)
    pnl_data_dict["EBITDA"].append(ebitda)
    pnl_data_dict["Less: Vehicle Depreciation (AfA - 48 Mo.)"].append(-current_vehicle_afa)
    pnl_data_dict["Less: IT Hardware Depreciation (AfA - 36 Mo.)"].append(-current_it_afa)
    pnl_data_dict["EBIT (Operating Income)"].append(ebit)
    pnl_data_dict["Add: Interest Income (Zinserträge)"].append(interest_income)
    pnl_data_dict["Less: Interest Expense (Zinsaufwendungen)"].append(-interest_expense)
    pnl_data_dict["EBT (Earnings Before Tax)"].append(ebt)
    pnl_data_dict["Less: Corporate Taxes (Ertragsteuern)"].append(-tax_expense)
    pnl_data_dict["Net Income (Jahresüberschuss / EAT)"].append(net_income)

# --- 5. DASHBOARD RENDER ---
st.subheader("Day 1 Sources & Uses of Capital (Y1 Cohort Only)")
colA, colB, colC, colD = st.columns(4)
colA.metric("Sources: Stammkapital", f"€ {stammkapital:,.0f}")
colB.metric("Sources: Shareholder Loan", f"€ {shareholder_loan:,.0f}")
colC.metric(f"Sources: Vehicle Loan ({vehicle_ltv*100:.0f}%)", f"€ {cohort_data[1]['original_loan']:,.0f}")
colD.metric("Day 1 Liquidity Buffer", f"€ {day_1_cash_balance:,.0f}")

st.divider()

st.subheader("5-Year Cohort P&L & Scaling Output")

# Display the Active Fleet dynamically on top of the P&L
fleet_cols = st.columns(5)
for i, year in enumerate(years):
    fleet_cols[i].metric(f"Active Fleet ({year})", f"{active_fleet_by_year[i]:.0f} Cars")

st.write("") # Spacer

tabs = st.tabs(["Income Statement (P&L)", "Cash Flow Statement", "Balance Sheet"])

with tabs[0]:
    df_pnl = pd.DataFrame(pnl_data_dict, index=years).T
    
    # Custom Formatter for the P&L rows to create a waterfall effect
    def style_pnl_rows(row):
        style = [''] * len(row)
        if "MRRG Net Revenue" in row.name:
            style = ['font-weight: 600; border-top: 1px solid #ffffff40; color: #4DA8DA;'] * len(row)
        elif "Deckungsbeitrag 1" in row.name or "Deckungsbeitrag 2" in row.name:
            style = ['font-weight: 600; background-color: #1e1e1e; border-top: 1px solid #ffffff40;'] * len(row)
        elif "EBITDA" in row.name:
            style = ['font-weight: 700; background-color: #2b2b2b; color: #F2A900;'] * len(row)
        elif "EBIT (" in row.name:
            style = ['font-weight: 600; background-color: #1e1e1e;'] * len(row)
        elif "EBT (" in row.name:
            style = ['font-weight: 600; border-top: 1px solid #ffffff40;'] * len(row)
        elif "Net Income" in row.name:
            style = ['font-weight: 700; background-color: #0b2e13; color: #38c172; font-size: 1.05em; border-top: 2px solid #38c172;'] * len(row)
        return style

    styled_df = df_pnl.style.format("{:,.0f} €").apply(style_pnl_rows, axis=1)
    st.dataframe(styled_df, use_container_width=True)

with tabs[1]:
    st.markdown("*(Cash Flow Statement integration is ready to be built from Net Income down to Free Cash Flow)*")

with tabs[2]:
    st.markdown("*(Balance Sheet integration will be built in Layer 8 after Cash Flow setup)*")
