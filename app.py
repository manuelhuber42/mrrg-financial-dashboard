import streamlit as st
import pandas as pd
import numpy as np

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="MRRG 3-Statement Financial Engine", layout="wide")
st.title("MRRG Cybercab Fleet: Master Financial Engine")
st.markdown("*(Layer 2: Vehicle Unit Economics & Deckungsbeitrag 2)*")

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

# --- 2. THE SCHEDULE ENGINE (Daily Math per Car) ---
# 1. Total theoretical distance if driving non-stop
max_theoretical_km = active_hours_per_day * avg_speed_kmh
theoretical_deadhead_km = max_theoretical_km * deadhead_rate
max_billable_km_theoretical = max_theoretical_km - theoretical_deadhead_km

# 2. Dwell Penalty (Distance lost while passengers get in/out)
distance_lost_per_dwell_km = (avg_speed_kmh / 60) * dwell_time_mins
effective_trip_distance_km = avg_trip_distance_km + distance_lost_per_dwell_km

# 3. Total Trips & Actual Billable Distance
actual_trips_per_day = np.floor(max_billable_km_theoretical / effective_trip_distance_km)
actual_billable_km_per_day = actual_trips_per_day * avg_trip_distance_km

# 4. Actual Total KM (Maintaining the strict 30% deadhead ratio)
actual_total_km_per_day = actual_billable_km_per_day / (1 - deadhead_rate)
actual_deadhead_km = actual_total_km_per_day - actual_billable_km_per_day

# 5. Daily Revenue Math (per car) - CUSTOMER PAYS GROSS
base_fare_rev_per_day_gross = actual_trips_per_day * base_fare_eur
distance_rev_per_day_gross = actual_billable_km_per_day * price_per_km_eur
gross_booking_value_per_day_per_car = base_fare_rev_per_day_gross + distance_rev_per_day_gross

# 6. Annual Fleet Topline
operating_days = 365 * vehicle_utilization
annual_gbv_fleet = gross_booking_value_per_day_per_car * operating_days * fleet_size

# VAT and Net Revenue Math
annual_net_revenue_fleet = annual_gbv_fleet / (1 + vat_rate)
annual_vat_owed = annual_gbv_fleet - annual_net_revenue_fleet

# Tesla Fee (Calculated aggressively on GBV)
annual_tesla_fees = annual_gbv_fleet * tesla_take_rate

# MRRG Operating Revenue (After Platform Fee)
mrrg_net_revenue = annual_net_revenue_fleet - annual_tesla_fees

# --- 3. LAYER 1: VARIABLE COSTS (Deckungsbeitrag 1) ---
wear_and_tear_rate = 0.03 
energy_rate = 0.05
total_km_annual_fleet = actual_total_km_per_day * operating_days * fleet_size

annual_wear_cost = total_km_annual_fleet * wear_and_tear_rate
annual_energy_cost = total_km_annual_fleet * energy_rate
annual_cleaning_cost = cleaning_cost_per_day * operating_days * fleet_size

deckungsbeitrag_1 = mrrg_net_revenue - annual_energy_cost - annual_wear_cost - annual_cleaning_cost

# --- 4. LAYER 2: VEHICLE FIXED COSTS (Deckungsbeitrag 2) ---
months_per_year = 12
annual_insurance = insurance_pm * months_per_year * fleet_size
annual_parking = parking_pm * months_per_year * fleet_size
annual_telemetry = telemetry_pm * months_per_year * fleet_size
annual_tuev = tuev_pm * months_per_year * fleet_size
annual_charging_sub = charging_sub_pm * months_per_year * fleet_size

total_annual_vehicle_fixed_costs = annual_insurance + annual_parking + annual_telemetry + annual_tuev + annual_charging_sub

deckungsbeitrag_2 = deckungsbeitrag_1 - total_annual_vehicle_fixed_costs

# --- 5. DASHBOARD RENDER ---
st.subheader("Daily Unit Economics Verification (Per Car / Per Day)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Actual Trips / Day", f"{actual_trips_per_day:.0f}")
col2.metric("Billable km / Day", f"{actual_billable_km_per_day:.1f}")
col3.metric("Total km / Day", f"{actual_total_km_per_day:.1f}")
col4.metric("GBV / Day (Incl. VAT)", f"€ {gross_booking_value_per_day_per_car:.2f}")

st.divider()

st.subheader("Annual 3-Statement Model (Fleet Aggregate)")

tabs = st.tabs(["Income Statement (P&L)", "Cash Flow Statement", "Balance Sheet"])

with tabs[0]:
    st.markdown("### Year 1 Profit & Loss")
    pnl_data = {
        "Line Item": [
            "Gross Booking Value (Customer Pays incl. 19% VAT)", 
            "Less: 19% VAT (Finanzamt)",
            "Net Revenue (Umsatzerlöse excl. VAT)",
            "Less: Tesla Platform Fee (30% on GBV)",
            "MRRG Net Revenue (After Platform Fee)",
            "Less: Direct Energy (Variable)",
            "Less: Direct Maintenance/Wear (Variable)",
            "Less: Cleaning Cost (Variable)",
            "Deckungsbeitrag 1 (DB1)",
            "Less: Insurance (Fixed)",
            "Less: APCOA Parking (Fixed)",
            "Less: Telemetry & API (Fixed)",
            "Less: TÜV / BO-Kraft (Fixed)",
            "Less: Tesla Charging Sub (Fixed)",
            "Deckungsbeitrag 2 (DB2)"
        ],
        "Year 1 (€)": [
            annual_gbv_fleet,
            -annual_vat_owed,
            annual_net_revenue_fleet,
            -annual_tesla_fees,
            mrrg_net_revenue,
            -annual_energy_cost,
            -annual_wear_cost,
            -annual_cleaning_cost,
            deckungsbeitrag_1,
            -annual_insurance,
            -annual_parking,
            -annual_telemetry,
            -annual_tuev,
            -annual_charging_sub,
            deckungsbeitrag_2
        ]
    }
    st.dataframe(pd.DataFrame(pnl_data).set_index("Line Item").style.format("{:,.0f} €"), use_container_width=True)

with tabs[1]:
    st.markdown("*(Cash Flow integration will be built in Layer 3 after Debt/AfA)*")

with tabs[2]:
    st.markdown("*(Balance Sheet integration will be built in Layer 4 after Asset/Liability setup)*")
