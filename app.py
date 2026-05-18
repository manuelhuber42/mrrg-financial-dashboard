import streamlit as st
import pandas as pd
import numpy as np

# --- 1. DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="MRRG 5-Year Financial Engine", layout="wide")
st.title("MRRG Cybercab Fleet: 5-Year Cohort Projection")
st.markdown("*(Analyzing the 5-year financial lifecycle of a single vehicle cohort)*")

# --- 2. SIDEBAR INPUTS ---
st.sidebar.header("CORE ECONOMICS")
fleet_size = st.sidebar.slider("Fleet Size (Num Cars)", 1, 100, 7)
utilization = st.sidebar.slider("Utilization % (Active Hours)", 10, 80, 30, 1) / 100
price_per_km = st.sidebar.slider("Price Per km (€)", 0.50, 3.00, 1.49, 0.01)

st.sidebar.header("NETWORK DYNAMICS")
paid_fraction = st.sidebar.slider("Paid Miles Fraction", 30, 90, 60, 1) / 100
tesla_take_rate = st.sidebar.slider("Tesla Base Take-Rate %", 10, 50, 30, 1) / 100

st.sidebar.header("COSTS & AFA")
capex_per_car = st.sidebar.slider("Car Purchase Price (€)", 20000, 50000, 28000, 1000)
wear_accrual_per_km = 0.06 # Fixed physical maintenance accrual
annual_fixed_opex = st.sidebar.slider("Annual Fixed OpEx per Car", 1000, 10000, 4000, 500)
tax_rate = st.sidebar.slider("Corporate Tax Rate %", 15, 35, 24, 1) / 100

st.sidebar.header("FINANCING (LOAN)")
debt_percentage = st.sidebar.slider("Debt Financing % (LTV)", 0, 100, 80, 5) / 100
interest_rate = st.sidebar.slider("Interest Rate %", 1.0, 15.0, 6.0, 0.1) / 100
loan_term_years = 5

# --- 3. THE CFO FINANCIAL ENGINE ---
max_annual_km_per_car = 50000 
actual_annual_km = max_annual_km_per_car * utilization
paid_annual_km = actual_annual_km * paid_fraction

# Unit Economics
gross_revenue = paid_annual_km * price_per_km * fleet_size
tesla_fees = gross_revenue * tesla_take_rate
wear_costs = actual_annual_km * wear_accrual_per_km * fleet_size
total_opex = (annual_fixed_opex * fleet_size) + wear_costs
ebitda = gross_revenue - tesla_fees - total_opex

# CapEx & Financing Calcs
total_capex = capex_per_car * fleet_size
loan_amount = total_capex * debt_percentage
equity_amount = total_capex - loan_amount
annual_depreciation = total_capex / 5  # 5-Year Straight Line AfA

# PMT Calculation for Annual Debt Service
if interest_rate > 0 and loan_amount > 0:
    annual_pmt = (interest_rate * loan_amount) / (1 - (1 + interest_rate)**-loan_term_years)
elif loan_amount > 0:
    annual_pmt = loan_amount / loan_term_years
else:
    annual_pmt = 0

# Build Schedules
financials = []
loan_schedule = []
afa_schedule = []

remaining_loan = loan_amount
book_value = total_capex

for year in range(1, 6):
    # Loan Math
    interest_payment = remaining_loan * interest_rate
    principal_payment = annual_pmt - interest_payment
    if remaining_loan <= 0:
        interest_payment = 0
        principal_payment = 0
    
    loan_schedule.append({
        "Year": f"Year {year}",
        "Starting Balance": remaining_loan,
        "Interest Expense": interest_payment,
        "Principal Repayment": principal_payment,
        "Ending Balance": max(0, remaining_loan - principal_payment)
    })
    remaining_loan = max(0, remaining_loan - principal_payment)
    
    # AfA Math
    afa_schedule.append({
        "Year": f"Year {year}",
        "Starting Book Value": book_value,
        "Depreciation (AfA)": annual_depreciation,
        "Ending Book Value": max(0, book_value - annual_depreciation)
    })
    book_value = max(0, book_value - annual_depreciation)

    # P&L and Cash Flow Math
    ebit = ebitda - annual_depreciation
    ebt = ebit - interest_payment
    taxes = max(0, ebt * tax_rate)
    net_income = ebt - taxes
    
    # Free Cash Flow to Equity (Operational Cash - Debt Service)
    fcf = net_income + annual_depreciation - principal_payment
    
    financials.append({
        "Metric": f"Year {year}",
        "Gross Revenue (€)": gross_revenue,
        "Tesla Take-Rate (€)": -tesla_fees,
        "Operating Expenses (€)": -total_opex,
        "EBITDA (€)": ebitda,
        "Depreciation AfA (€)": -annual_depreciation,
        "EBIT (€)": ebit,
        "Interest Expense (€)": -interest_payment,
        "EBT (€)": ebt,
        "Taxes (€)": -taxes,
        "Net Income (€)": net_income,
        "Principal Repayment (€)": -principal_payment,
        "Free Cash Flow (€)": fcf
    })

# --- 4. MAIN DASHBOARD RENDER ---
df_financials = pd.DataFrame(financials).set_index("Metric").T
df_loan = pd.DataFrame(loan_schedule).set_index("Year")
df_afa = pd.DataFrame(afa_schedule).set_index("Year")

# Layout formatting
st.subheader("Key Return Metrics")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total CapEx", f"€ {total_capex:,.0f}")
col2.metric("Equity Required", f"€ {equity_amount:,.0f}")
col3.metric("Annual Debt Service", f"€ {annual_pmt:,.0f}")
col4.metric("EBITDA Margin", f"{(ebitda / gross_revenue) * 100:.1f}%" if gross_revenue > 0 else "0%")

st.divider()

# Create Excel-like tabs
tab1, tab2, tab3 = st.tabs(["📊 P&L & Cash Flow", "🏦 Debt Amortization Schedule", "📉 AfA Schedule"])

with tab1:
    st.dataframe(df_financials.style.format("{:,.0f} €"), use_container_width=True)

with tab2:
    st.dataframe(df_loan.style.format("€ {:,.0f}"), use_container_width=True)

with tab3:
    st.dataframe(df_afa.style.format("€ {:,.0f}"), use_container_width=True)
