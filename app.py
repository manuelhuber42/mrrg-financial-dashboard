import streamlit as st
import pandas as pd
import numpy as np

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="MRRG 3-Statement Financial Engine", layout="wide")
st.title("MRRG Cybercab Fleet: Master Financial Engine")
st.markdown("*(Layer 3: Corporate Overhead, Other Income & EBITDA)*")

# --- 1. THE PHYSICS & REVENUE ASSUMPTIONS (From Excel) ---
st.sidebar.header("1. FLEET PHYSICS (Realistic)")
fleet_size = st.sidebar.slider("Fleet Size (Num Cars)", 1, 50, 3)
vehicle_utilization = st.sidebar.number_input("Vehicle Utilization / Uptime (%)", value=95.0) / 100
active_hours_per_day = st.sidebar.number_input("Active Hours / Day", value=16.0)
avg_speed_kmh = st.sidebar.number_input("Average Speed (km/h)", value=22.0)
deadhead_rate = st.sidebar.number_input("Deadhead Rate (%)", value=30.0) / 100

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

st.sidebar.header("6. CORPORATE HQ (€ / Month, Net)")
hq_lease_pm = st.sidebar.number_input("HQ Lease (Raumkosten)", value=450.0)
it_cloud_pm = st.sidebar.number_input("IT, Cloud & AI Services", value=320.0)
legal_bookkeeping_pm = st.sidebar.number_input("Legal & Bookkeeping", value=230.0)
hq_insurance_pm = st.sidebar.number_input("HQ Insurance (Liability, D&O)", value=250.0)
bank_fees_pm = st.sidebar.number_input("Bank Fees", value=20.0)
ihk_pm = st.sidebar.number_input("IHK Membership", value=35.0)
gez_pm_per_car = st.sidebar.number_input("GEZ (per car)", value=7.0)
setup_costs_y1 = st.sidebar.number_input("One-off Setup Costs (Y1)", value=1700.0)

st.sidebar.header("7. OTHER INCOME / SALVAGE")
thg_quote_per_car_py = st.sidebar.number_input("THG Quote per car/yr", value=200.0)
salvage_value_per_car_y4 = st.sidebar.number_input("Vehicle Sale Price (Y4)", value=10000.0)

# --- 2. THE SCHEDULE ENGINE (Daily Math per Car) ---
max_theoretical_km = active_hours_per_day * avg_speed_kmh
theoretical_deadhead_km = max_theoretical_km * deadhead_rate
max_billable_km_theoretical = max_theoretical_km - theoretical_deadhead_km
distance_lost_per_dwell_km = (avg_speed_kmh / 60) * dwell_time_mins
effective_trip_distance_km = avg_trip_distance_km + distance_lost_per_dwell_km

actual_trips_per_day = np.floor(max_billable_km_theoretical / effective_trip_distance_km)
actual_billable_km_per_day = actual_trips_per_day * avg_trip_distance_km
actual_total_km_per_day = actual_billable_km_per_day / (1 - deadhead_rate)
actual_deadhead_km = actual_total_km_per_day - actual_billable_km_per_day

base_fare_rev_per_day_gross = actual_trips_per_day * base_fare_eur
distance_rev_per_day_gross = actual_billable_km_per_day * price_per_km_eur
gross_booking_value_per_day_per_car = base_fare_rev_per_day_gross + distance_rev_per_day_gross

# --- 3. MULTI-YEAR P&L GENERATOR ---
years = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
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
    "Less: Legal, Tax & Bookkeeping": [],
    "Less: Corporate Insurance (Liability, D&O)": [],
    "Less: Subscriptions & Fees (IHK, GEZ)": [],
    "Less: Bank Fees": [],
    "Add: THG Quote (Other Operating Income)": [],
    "Add: Fleet Liquidation (Asset Sale)": [],
    "EBITDA": []
}

wear_and_tear_rate = 0.03 
energy_rate = 0.05
months_per_year = 12

for year in range(1, 6):
    # Fleet is sold end of Year 4. Therefore, Year 5 operations are zero.
    active_fleet = fleet_size if year <= 4 else 0
    operating_days = (365 * vehicle_utilization) if year <= 4 else 0
    
    # Revenue Math
    annual_gbv_fleet = gross_booking_value_per_day_per_car * operating_days * active_fleet
    annual_net_revenue_fleet = annual_gbv_fleet / (1 + vat_rate)
    annual_vat_owed = annual_gbv_fleet - annual_net_revenue_fleet
    annual_tesla_fees = annual_gbv_fleet * tesla_take_rate
    mrrg_net_revenue = annual_net_revenue_fleet - annual_tesla_fees
    
    # Variable Costs Math
    total_km_annual_fleet = actual_total_km_per_day * operating_days * active_fleet
    annual_wear_cost = total_km_annual_fleet * wear_and_tear_rate
    annual_energy_cost = total_km_annual_fleet * energy_rate
    annual_cleaning_cost = cleaning_cost_per_day * operating_days * active_fleet
    deckungsbeitrag_1 = mrrg_net_revenue - annual_energy_cost - annual_wear_cost - annual_cleaning_cost
    
    # Vehicle Fixed Costs Math
    annual_insurance = insurance_pm * months_per_year * active_fleet
    annual_parking = parking_pm * months_per_year * active_fleet
    annual_telemetry = telemetry_pm * months_per_year * active_fleet
    annual_tuev = tuev_pm * months_per_year * active_fleet
    annual_charging_sub = charging_sub_pm * months_per_year * active_fleet
    total_annual_vehicle_fixed_costs = annual_insurance + annual_parking + annual_telemetry + annual_tuev + annual_charging_sub
    deckungsbeitrag_2 = deckungsbeitrag_1 - total_annual_vehicle_fixed_costs
    
    # Corporate HQ Math (Costs run regardless of fleet being active)
    annual_hq_lease = hq_lease_pm * months_per_year
    annual_it_cloud = it_cloud_pm * months_per_year
    annual_hq_insurance = hq_insurance_pm * months_per_year
    
    # Legal has a one-off setup cost in Year 1
    annual_legal = (legal_bookkeeping_pm * months_per_year) + (setup_costs_y1 if year == 1 else 0)
    
    # IHK is flat HQ cost, GEZ is tied to cars
    annual_fees = (ihk_pm * months_per_year) + (gez_pm_per_car * months_per_year * active_fleet)
    annual_bank = bank_fees_pm * months_per_year
    
    # Other Income
    annual_thg = thg_quote_per_car_py * active_fleet
    fleet_sale_revenue = (salvage_value_per_car_y4 * active_fleet) if year == 4 else 0
    
    # EBITDA Calculation
    ebitda = (deckungsbeitrag_2 
              - annual_hq_lease 
              - annual_it_cloud 
              - annual_legal 
              - annual_hq_insurance
              - annual_fees 
              - annual_bank 
              + annual_thg 
              + fleet_sale_revenue)
    
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
    pnl_data_dict["Less: Legal, Tax & Bookkeeping"].append(-annual_legal)
    pnl_data_dict["Less: Corporate Insurance (Liability, D&O)"].append(-annual_hq_insurance)
    pnl_data_dict["Less: Subscriptions & Fees (IHK, GEZ)"].append(-annual_fees)
    pnl_data_dict["Less: Bank Fees"].append(-annual_bank)
    pnl_data_dict["Add: THG Quote (Other Operating Income)"].append(annual_thg)
    pnl_data_dict["Add: Fleet Liquidation (Asset Sale)"].append(fleet_sale_revenue)
    pnl_data_dict["EBITDA"].append(ebitda)

# --- 4. DASHBOARD RENDER ---
st.subheader("Daily Unit Economics Verification (Per Car / Per Day)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Actual Trips / Day", f"{actual_trips_per_day:.0f}")
col2.metric("Billable km / Day", f"{actual_billable_km_per_day:.1f}")
col3.metric("Total km / Day", f"{actual_total_km_per_day:.1f}")
col4.metric("GBV / Day (Incl. VAT)", f"€ {gross_booking_value_per_day_per_car:.2f}")

st.divider()

st.subheader("5-Year Cohort P&L (Fleet Aggregate)")

tabs = st.tabs(["Income Statement (P&L)", "Cash Flow Statement", "Balance Sheet"])

with tabs[0]:
    st.markdown("### Profit & Loss down to EBITDA")
    df_pnl = pd.DataFrame(pnl_data_dict, index=years).T
    st.dataframe(df_pnl.style.format("{:,.0f} €"), use_container_width=True)

with tabs[1]:
    st.markdown("*(Cash Flow integration will be built in Layer 4 after Debt/AfA)*")

with tabs[2]:
    st.markdown("*(Balance Sheet integration will be built in Layer 5 after Asset/Liability setup)*")
