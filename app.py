import streamlit as st
import pandas as pd
import numpy as np

# --- 1. DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="MRRG 5-Year Financial Engine", layout="wide")
st.title("MRRG Cybercab Fleet: 5-Year Financial Projections")

# --- 2. SIDEBAR INPUTS (Like your screenshot) ---
st.sidebar.header("CORE ECONOMICS")
fleet_size = st.sidebar.slider("Fleet Size (Num Cars)", min_value=1, max_value=100, value=7)
utilization = st.sidebar.slider("Utilization % (Active Hours)", min_value=10, max_value=80, value=30, step=1) / 100
price_per_km = st.sidebar.slider("Price Per km (€)", min_value=0.50, max_value=3.00, value=1.49, step=0.01)

st.sidebar.header("NETWORK DYNAMICS")
paid_fraction = st.sidebar.slider("Paid Miles Fraction", min_value=30, max_value=90, value=60, step=1) / 100
tesla_take_rate = st.sidebar.slider("Tesla Base Take-Rate %", min_value=10, max_value=50, value=30, step=1) / 100

st.sidebar.header("COSTS & TAXES")
capex_per_car = st.sidebar.slider("Car Purchase Price (€)", min_value=20000, max_value=50000, value=28000, step=1000)
wear_accrual_per_km = 0.06 # Hardcoded COO metric
annual_fixed_opex = st.sidebar.slider("Annual Fixed OpEx per Car (Hubs, Insurance)", min_value=1000, max_value=10000, value=4000, step=500)
tax_rate = st.sidebar.slider("Corporate Tax Rate % (Gräfelfing)", min_value=15, max_value=35, value=24, step=1) / 100

# --- 3. THE CFO FINANCIAL ENGINE (Calculations) ---
# Assuming a car could drive max 50,000 km a year at 100% utilization
max_annual_km_per_car = 50000 
actual_annual_km = max_annual_km_per_car * utilization
paid_annual_km = actual_annual_km * paid_fraction

# Unit Economics per Car
gross_revenue_per_car = paid_annual_km * price_per_km
tesla_fee_per_car = gross_revenue_per_car * tesla_take_rate
wear_cost_per_car = actual_annual_km * wear_accrual_per_km
total_opex_per_car = annual_fixed_opex + wear_cost_per_car

# Fleet Calculations
total_gross_revenue = gross_revenue_per_car * fleet_size
total_tesla_fees = tesla_fee_per_car * fleet_size
total_opex = total_opex_per_car * fleet_size
ebitda = total_gross_revenue - total_tesla_fees - total_opex

# 5-Year Projection Loop (Simplified straight-line depreciation for 5 years)
depreciation = (capex_per_car * fleet_size) / 5 

years = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
financials = []

for year in years:
    ebit = ebitda - depreciation
    taxes = max(0, ebit * tax_rate)
    net_income = ebit - taxes
    operating_cash_flow = net_income + depreciation # Add back non-cash
    
    financials.append({
        "Metric": year,
        "Gross Revenue (€)": total_gross_revenue,
        "Tesla Take-Rate (€)": -total_tesla_fees,
        "Operating Expenses (€)": -total_opex,
        "EBITDA (€)": ebitda,
        "Depreciation (€)": -depreciation,
        "EBIT (€)": ebit,
        "Taxes (€)": -taxes,
        "Net Income (€)": net_income,
        "Free Cash Flow (€)": operating_cash_flow
    })

# --- 4. MAIN DASHBOARD RENDER ---
df_financials = pd.DataFrame(financials).set_index("Metric").T

st.subheader("5-Year Fleet P&L and Cash Flow Projection")
st.dataframe(df_financials.style.format("{:,.0f} €"))

st.divider()
st.subheader("Key CFO Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("EBITDA Margin", f"{(ebitda / total_gross_revenue) * 100:.1f}%")
col2.metric("Total CapEx Required", f"{capex_per_car * fleet_size:,.0f} €")
col3.metric("Payback Period (Years)", f"{(capex_per_car * fleet_size) / (ebitda if ebitda > 0 else 1):.2f}")
