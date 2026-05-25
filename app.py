import streamlit as st
import pandas as pd
import numpy as np
import calendar
import plotly.graph_objects as go
import time

# --- GLOBAL MODELING CONSTANTS & FINANCIAL ARCHITECTURE ---
VAT_RATE = 0.19
# AfA period aligned to BMF AfA-Tabellen for Mietwagen/Taxi (intensive use).
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
        "subtitle": "*(HGB 3-Statement Model — Layer 27A: Capital Structure (Loan/Lease/Equity Tranches) + Monte Carlo with Day-Archetype Topology + Stochastic Shock Events)*",
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
        "help_init": "Month-1 launch utilization. 55% reflects three demand catalysts unique to MRRG's go-to-market: (a) price elasticity from 30-45% undercut vs. Uber/Free Now drives ~25-35% volume lift vs. mature-market launches (Cohen Uber/MIT 2016 elasticity studies), (b) novelty effect from first European Cybercab deployment generates PR-driven trial demand (Cruise SF early-week data showed >70% utilization spikes), (c) supply-constrained Month-1 fleet (3 cars) concentrated in 1-2 high-density zones (Maxvorstadt/Schwabing) operates at structurally higher utilization than market-scale operations. On 24h calendar basis this equals ~31% asset utilization (55% × 13.5h ÷ 24h).",
        "rec_rate": "Monthly Recovery (+%)",
        "help_rec": "Monthly utilization recovery rate. 5%/month is required for utilization to outpace the cadence of fleet additions in Y3-Y5 (the model adds 12+ cars/year in lumps of 3-6 every quarter). Lower rates (3%/month, default) caused utilization collapse in Y5 as cannibalization hits compounded faster than recovery. 5% is benchmarked against Waymo SF scaling-phase recovery rate (4-6%/month observed during active fleet expansion); also consistent with Uber Munich 2014-2016 driver-supply recovery curves.",
        "can_fac": "Cannibalization Factor",
        "help_can": "Cannibalization factor. 0.35 means each new cohort temporarily strips 35% of incremental capacity from existing-fleet utilization. The default of 0.5 was empirically too aggressive — a mature dispatch algorithm with 12+ months of Munich demand data should geographically redistribute new cars to under-served zones rather than overlapping existing routes. 0.35 is benchmarked against MOIA Hamburg fleet expansion data 2019-2023 where cannibalization measured at 30-40% during similar ramp phases.",
        "util_label": "Avg Util",
        "sec2": "2. TRIP DYNAMICS",
        "trip_dist": "Average Trip Distance (km)",
        "dwell": "Dwell Time (Minutes)",
        "help_dwell": "Total per-trip non-productive time: passenger ingress 60-90s (locating car via app, opening door, settling) + egress 60-90s (collecting belongings, ride end confirmation) + brief AI confirmation/sensor check 15-30s. Waymo Phoenix empirical data 2.5-4 min. First 18-24 months may run higher (4-5 min) as users learn the system; central case assumes mature-state user behavior.",
        "sec3": "3. PRICING (Incl. 19% VAT)",
        "base_fare": "Base Fare (€)",
        "price_km": "Price per km (€)",
        "tesla_take": "Tesla Take-Rate (%)",
        # === B2B Delivery Stream (default OFF) ===
        "sec3b": "3b. B2B DELIVERY STREAM (Tesla Network)",
        "delivery_toggle": "Enable B2B Delivery Stream",
        "help_delivery_toggle": "Tesla Network also dispatches Cybercabs for goods delivery (food/parcel/medical) during low-passenger-demand windows. Same dispatch architecture, separate revenue stream. Default OFF for conservative passenger-only base case. Toggle ON to model the asset's full productivity envelope. Tesla controls priority (passenger trips preempt delivery when both available).",
        "delivery_hours": "Additional Active Hours / Day (Delivery)",
        "help_delivery_hours": "Incremental productive hours per day when delivery stream is active. 4.5h fills low-passenger-demand windows (lunch 11am-2pm partial overlap, late-evening 10pm-1am, early-morning B2B 5-7am). Combined with 13.5h passenger shift = 18h Tesla Network active per 24h day (75% 24h asset utilization).",
        "delivery_revenue_per_trip": "Revenue per Delivery Trip (€, gross incl. 19% VAT)",
        "help_delivery_rev": "Blended revenue per completed delivery cycle. Lieferando/Uber Eats food €4-6, B2B parcel last-mile €3-5, medical/pharmacy €8-15. €6.00 reflects food-weighted central case. Customer pays this gross; 19% VAT remitted to Finanzamt; 25% Tesla Network platform fee on net.",
        "delivery_trips_per_active_hour": "Deliveries per Active Hour",
        "help_delivery_trips": "Realistic delivery throughput. Shorter dwell (45-90s at pickup, 30-60s at dropoff) vs passenger (3.5 min) enables 3 deliveries per active hour vs passenger ~2.4 trips/hour. Implies ~14 deliveries per active 4.5h delivery shift.",
        "delivery_take_rate": "Tesla Network Take-Rate on Delivery (%)",
        "help_delivery_take": "Tesla Network platform fee on delivery gross revenue. Conservatively assumed same 25% as passenger. If Tesla partners with logistics providers (DoorDash/Lieferando), partner takes their share before Tesla; net effect to MRRG is similar to direct 25% fee.",
        "delivery_ramp_y1": "Delivery Activation % Year 1",
        "delivery_ramp_y2": "Delivery Activation % Year 2",
        "delivery_ramp_y3": "Delivery Activation % Year 3",
        "delivery_ramp_y4": "Delivery Activation % Year 4",
        "delivery_ramp_y5": "Delivery Activation % Year 5",
        "help_delivery_ramp": "Tesla Network delivery service activation by year. Default 0/0/30/70/100 reflects Tesla launching delivery as Y2H2 product, mature by Y4. Stress-test by setting all to 0% (pure passenger) or 100% (immediate launch).",
        "sec4": "4. DAILY VARIABLE COSTS (Net)",
        "cleaning": "Cleaning Cost per Vehicle/Day (€, Net of Tesla Fees)",
        "help_cleaning": "update. Cleaning cost €2/day NET reflects Tesla cleaning-fee revenue pass-through. Tesla published Robotaxi terms (Dec 2025): $50 moderate / $150 severe per incident, deducted automatically from rider via in-cabin cameras. Gross cleaning cost ~€5/day (depot deep-clean + sensor washer fluid + ozone treatment) less ~€3/day fee pass-through revenue at 12 severe + 30 moderate incidents/car/year mature state = €2/day net. Operationally, dirty cars route to depot during charging window — zero productive-shift impact.",
        "wear_rate": "Maintenance/Wear per km (€)",
        "wear_help": "Management-view levelized rate reflecting 4-5y vehicle scrap strategy (post-AfA exhaustion). Breakdown: tires €0.027, sensor maintenance €0.034 (Cybercab onboard cleaning reduces vs Waymo benchmark), body wear €0.012, fluids/suspension €0.005, HVAC/inspections €0.005, accident reserve €0.008, contingency €0.005. Benchmarked vs Sixt+, Free Now, MOIA published data. Below Waymo (€0.12-0.16) due to simpler Cybercab sensor stack and German labor rates.",
        # === Energy 3-slider build (was single energy_rate slider in L21) ===
        "energy_kwh": "Cybercab Consumption (kWh/km)",
        "help_energy_kwh": "Real-world Cybercab energy consumption. Anchored on Tesla VP Lars Moravy's May 21, 2026 announcement at Model S/X SE event: Cybercab certified at 165 Wh/mile = 0.103 kWh/km (most efficient EV ever certified, 40% better than Model 3). Real-world urban operation typically adds 8-15% over EPA-style certified rating (HVAC, accessories, stop-and-go). Default 0.115 kWh/km applies 12% real-world derate. Cybercab achieves this via: teardrop aerodynamics (Cd estimated <0.20), 2-seat layout (no rear seats/structure), no steering wheel/pedals/mirrors, narrower purpose-built tires, sub-50 kWh battery, no driver-aggressive driving profile.",
        "energy_eur": "Energy Price Blended (€/kWh)",
        "help_energy_eur": "Blended cost per kWh at the meter. Anchored on (a) German wholesale 2am-6am charging window historically €0.04-0.09/kWh (EPEX off-peak base 2025: €0.088/kWh average), (b) Tesla Supercharger Germany 2026 off-peak rates €0.31-0.46/kWh, (c) fleet operator subscription discount (parallel to Tesla Insurance fleet model). Central case €0.22/kWh = 70% depot inductive overnight at €0.18 (wholesale + 8ct grid/margin) + 30% V4 Supercharger off-peak at €0.32 (with fleet subscription). Tesla incentive structure supports this: they extract more via 25% platform take-rate than they'd lose offering near-wholesale energy.",
        "charging_eff": "Charging Efficiency (0.50-1.00)",
        "help_charging_eff": "Energy delivered to battery as fraction of energy drawn from grid. Anchored on Tesla's October 2024 statement that Cybercab inductive charging is 'well over 90%' efficient (responding to Marques Brownlee's 75% estimate). Wired V4 Supercharger achieves 96-97%. Default 0.94 reflects 70% inductive (92%) + 30% wired (96%) blend. Wiferion tech Tesla acquired supports 22 kW wireless. Tesla received FCC waiver Feb 2026 for UWB positioning enabling precise pad alignment.",
        "energy_derived_caption": "→ Derived Energy Cost: €{rate:.4f}/km (before seasonality)",
        # === Section 5 fixed costs — insurance/parking recalibrated, cargo insurance added ===
        "sec5": "5. VEHICLE FIXED COSTS (€ / Month, Net)",
        "insurance": "Insurance",
        "help_insurance": "recalibration: €300 → €180/month. Bottom-up build: theft component ~€0 (Cybercab cannot be driven outside Tesla Network — Waymo Phoenix 7yr data shows ~0 successful thefts), but vandalism (€20), battery/fire (€20), weather (€12), passenger damage (€15), cyber liability (€40), legal reserve (€30), residual bodily injury/property damage liability after 70% FSD safety credit (€55), passenger transport mandatory coverage per PBefG (€18) sum to ~€210, less ~15% Tesla Insurance bundling discount and 5-year averaging = €180. Y1-Y2 actuals may run €250-300 before declining as Munich-specific claims data accumulates. Risk: if Tesla Insurance Europe GmbH licensing delays force pure third-party German insurance, premium could rise to €280-350.",
        "parking": "APCOA Charging Capable Space (Munich)",
        "help_parking": "recalibration: €250 → €170/month. APCOA published 2024 Munich monthly parking €120-180 + charging-capable premium €40-80 = central case €160-220. At Y5 fleet of 57 cars, bulk discount 15-25% reduces to €140-180 range. €170 sits at midpoint of negotiable bulk-fleet rate. Includes inductive charging pad access where deployed Y3+, wired V4 fallback in Y1-Y2.",
        "telemetry": "Telemetry & API",
        "tuev": "TÜV / BO-Kraft Accrual",
        "help_tuev": "Monthly accrual for mandatory passenger transport inspections.",
        "charging_sub": "Tesla Charging Sub",
        "cargo_ins": "Cargo Insurance (Verkehrshaftungsversicherung)",
        "help_cargo_ins": "NEW LINE. Mandatory transport liability insurance when B2B delivery toggle is ON. Covers cargo value, theft in transit, weather damage, in-transit handling claims. Doesn't benefit from FSD safety credit (these risks don't depend on driver behavior). €20/car/month reflects 2024 German Verkehrshaftungsversicherung rates for low-value parcel/food courier operations. Only billed when delivery stream is active.",
        # === Monthly seasonality multipliers (12 months adjustable) ===
        "sec_season": "1d. SEASONALITY (Winter Penalty)",
        "season_expander": "📅 Monthly Energy Multipliers",
        "season_caption": "Adjust per-month energy cost multipliers. Affects energy line in P&L. Empirical anchors: ADAC Wintertest 2023 (-35-55% EV range Dec-Feb), Geotab fleet study (+8-15% summer A/C). Tesla 4680 dry-cathode reduces winter penalty 10-15% vs 2170 cells.",
        "month_jan": "January Multiplier",
        "month_feb": "February Multiplier",
        "month_mar": "March Multiplier",
        "month_apr": "April Multiplier",
        "month_may": "May Multiplier",
        "month_jun": "June Multiplier",
        "month_jul": "July Multiplier",
        "month_aug": "August Multiplier",
        "month_sep": "September Multiplier",
        "month_oct": "October Multiplier",
        "month_nov": "November Multiplier",
        "month_dec": "December Multiplier",
        "season_blend_caption": "→ Annual blend: {blend:.4f}× (1.0 = no seasonality)",
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
        "help_thg": "Greenhouse Gas (GHG) Reduction Quota certificates per § 7 Abs. 1 38. BImSchV. Flat annual payment per registered EV per calendar year, paid in FULL regardless of when in the year vehicle was registered, provided registration is before Nov 15 deadline. Vehicles registered Nov-Dec defer to following January. Default €280 reflects 2024 German market actuals (range €150-450 depending on provider). 2025-2028 forward pricing volatile. Source: ADAC, EnBW, Finanztip, Klima-Quote, elektrovorteil.",
        "salvage": "Vehicle Sale Price (End of 5-Yr Useful Life)",
        
        "pnl_gbv": "Gross Booking Value (Customer Pays incl. 19% VAT)",
        "pnl_vat": "Less: 19% VAT (Finanzamt)",
        "pnl_net_rev": "Net Revenue (Umsatzerlöse excl. VAT)",
        "pnl_tesla_fee": "Less: Tesla Platform Fee (Take-Rate on Net Rev)",
        "pnl_mrrg_net": "MRRG Net Revenue (After Platform Fee) — Passenger",
        # === B2B Delivery revenue stream (Tesla Network) ===
        "pnl_delivery_gbv": "Gross Delivery Bookings (Tesla Network B2B, incl. 19% VAT)",
        "pnl_delivery_vat": "Less: 19% VAT on Deliveries (Finanzamt)",
        "pnl_delivery_net_rev": "Net Delivery Revenue (Umsatzerlöse excl. VAT)",
        "pnl_delivery_tesla_fee": "Less: Tesla Platform Fee on Delivery",
        "pnl_delivery_mrrg_net": "MRRG Net Revenue (After Platform Fee) — Delivery",
        "pnl_total_mrrg_net": "TOTAL MRRG Net Revenue (Passenger + Delivery)",
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
        # === Monte Carlo Risk & Variance Analysis ===
        "tab_mc": "🎲 Risk & Variance Analysis (Monte Carlo)",
        "mc_header": "Risk & Variance Analysis — Stochastic Monte Carlo",
        "mc_intro": "This module wraps the deterministic 60-month engine in a stochastic Monte Carlo simulation. The 12 most variance-driving parameters are sampled from empirically-anchored probability distributions across N iterations. The deterministic central case in the other tabs remains unchanged — this analysis is supplementary risk decomposition for bank credit committees and project finance evaluation.",
        "mc_run_button": "🎲 Run Monte Carlo Simulation",
        "mc_n_iterations": "Number of Iterations (N)",
        "mc_n_help": "5,000 produces stable percentiles in ~30-60 seconds. 10,000 produces near-final convergence in ~60-120 seconds. Below 1,000 is statistically unreliable.",
        "mc_section_dist": "📊 Distribution Parameters (Override Defaults)",
        "mc_section_outputs": "📈 Simulation Results",
        "mc_progress_label": "Running Monte Carlo iteration {i} of {n}...",
        "mc_no_results": "ℹ️ Click the **Run Monte Carlo Simulation** button above to generate stochastic risk analysis.",
        "mc_kpi_header": "Key Risk Indicators — Percentile Distribution",
        "mc_kpi_p5": "P5 (Severe Downside)",
        "mc_kpi_p25": "P25 (Conservative)",
        "mc_kpi_p50": "P50 (Median)",
        "mc_kpi_p75": "P75 (Optimistic)",
        "mc_kpi_p95": "P95 (Blue Sky)",
        "mc_kpi_ni_cum": "5-Year Cumulative Net Income (€)",
        "mc_kpi_y5_ebitda": "Year 5 EBITDA (€)",
        "mc_kpi_min_cash": "Minimum Cash Balance (€)",
        "mc_kpi_insolvency": "Probability of Insolvency Event",
        "mc_chart_ni_title": "Distribution: 5-Year Cumulative Net Income",
        "mc_chart_cash_title": "Distribution: Minimum Cash Balance vs. Buffer Threshold",
        "mc_chart_tornado_title": "Sensitivity Tornado — Pearson r vs. 5Y Cumulative Net Income",
        "mc_tornado_xaxis": "Pearson Correlation Coefficient (r)",
        "mc_buffer_line_label": "Min Cash Buffer Threshold",
        "mc_p5_label": "P5",
        "mc_p95_label": "P95",
        "mc_p50_label": "P50 (Median)",
        # MC parameter labels for sliders + tornado
        "mc_p_wear": "Wear & Tear σ (€/km)",
        "mc_p_energy_eur": "Energy Price σ (€/kWh)",
        "mc_p_target_util": "Target Util Range",
        "mc_p_insurance": "Insurance €/mo (Min/Mode/Max)",
        "mc_p_take_rate": "Tesla Take-Rate (Min/Mode/Max)",
        "mc_p_kwh_per_km": "Cybercab Consumption σ (kWh/km)",
        "mc_p_deadhead": "Deadhead Rate σ",
        "mc_p_trip_dist": "Trip Distance σ (km)",
        "mc_p_delivery_y3": "Delivery Y3 Ramp (Min/Mode/Max)",
        "mc_p_price": "Price per km σ (€)",
        "mc_p_salvage": "Salvage Value σ (€)",
        "mc_p_winter": "Winter Seasonality σ (×)",
        # === Expanded parameter set (22+) per Tier 1/2/3 spec ===
        "mc_p_active_hours": "Active Hours σ (h/day)",
        "mc_p_speed": "Average Speed σ (km/h)",
        "mc_p_dwell": "Dwell Time σ (min)",
        "mc_p_init_util": "Init Utilization σ",
        "mc_p_rec_rate": "Recovery Rate σ",
        "mc_p_can_fac": "Cannibalization Factor σ",
        "mc_p_dy2": "Delivery Y2 (Min/Mode/Max)",
        "mc_p_dy4": "Delivery Y4 (Min/Mode/Max)",
        "mc_p_capex": "Cybercab Base USD σ",
        "mc_p_fx": "USD/EUR FX Rate σ",
        "mc_p_ltv": "Vehicle LTV σ",
        "mc_p_loan_y1": "Y1 Loan Rate (Min/Mode/Max)",
        "mc_p_loan_y2": "Y2 Loan Rate (Min/Mode/Max)",
        "mc_p_cleaning": "Cleaning €/day σ",
        "mc_p_parking": "Parking €/mo σ",
        "mc_p_customs": "Customs Duty Rate σ",
        "mc_metric_selector": "Select Target Analysis Metric",
        "mc_metric_fcf": "Free Cash Flow",
        "mc_metric_ebitda": "EBITDA",
        "mc_metric_ni": "Net Income",
        "mc_kpi_fcf_cum": "5-Year Cumulative Free Cash Flow (€)",
        "mc_chart_fcf_title": "Distribution: 5-Year Cumulative Free Cash Flow",
        "mc_chart_ebitda_title": "Distribution: Year 5 EBITDA",
        # Tier section headers
        "mc_tier1_header": "🔥 Tier 1 — High Variance Drivers (Operating Physics)",
        "mc_tier2_header": "⚡ Tier 2 — Material Variance (Capex, Debt, Costs)",
        "mc_tier3_header": "💧 Tier 3 — Smaller Variance (Operational Costs)",
        "mc_running_msg": "🔄 Monte Carlo simulation in progress. Please wait...",
        # === Capital Structure & Fleet Financing Matrix (Layer 27A) ===
        "fin_matrix_header": "💳 Capital Allocation & Vehicle Financing Strategy",
        "fin_matrix_help": "Configure financing mix per year. Each year's vehicle additions are split into three tranches: Bank Loan (debt-financed, asset capitalized), Operating Lease (off-balance-sheet, ARAP for downpayment), and 100% Cash/Equity (full capex from cash with optional capital call). Sliders auto-normalize to 100% per year.",
        "fin_year_label": "Year {y} Financing Mix",
        "fin_pct_loan": "% Loan",
        "fin_pct_lease": "% Lease",
        "fin_pct_equity": "% Equity",
        "fin_loan_section": "🏦 Bank Loan Parameters (Tranche A)",
        "fin_lease_section": "📋 Operating Lease Parameters (Tranche B) — Global",
        "fin_equity_section": "💰 Equity/Cash Allocation (Tranche C)",
        "fin_lease_money_factor": "Monthly Lease Factor (×capex)",
        "fin_lease_money_factor_help": "Monthly lease payment as a fraction of vehicle gross acquisition cost. Default 0.015 = 1.5%/mo, typical for 60-month German auto leases. Includes financing cost + lessor margin + residual risk premium.",
        "fin_lease_downpayment_pct": "Leasingsonderzahlung (% of capex)",
        "fin_lease_downpayment_help": "Upfront special payment (Sonderzahlung) at lease inception. Under HGB § 250, capitalized as ARAP (Aktiver Rechnungsabgrenzungsposten) and amortized linearly over the lease term. Default 15% reflects standard German commercial vehicle lease terms.",
        "fin_lease_term_months": "Lease Term (months)",
        "fin_equity_capital_call": "Auto Capital Call on Cash Shortfall",
        "fin_equity_capital_call_help": "When equity-financed vehicle additions would push corporate cash below zero (after max overdraft utilization), trigger automated founder equity injection to keep balance sheet funded. Disabled = treat shortfall as overdraft breach (insolvency flag).",
        "fin_norm_warning": "⚠️ Year {y} percentages sum to {s}% — will be auto-normalized to 100%.",
        "bs_arap": "ARAP (Prepaid Lease)",
        "pnl_lease": "Lease Expense (Mietleasing)",
        "cf_lease": "Lease Payments + ARAP Setup",
        "cf_capital_call": "Founder Capital Call (Equity Injection)",
        # Day-archetype + shock event labels
        "mc_dayarch_header": "📅 Day Archetype Mix (Phase A) — daily demand variance topology",
        "mc_shock_header": "⚡ Stochastic Shock Events (Phase B) — annual frequency × impact",
        "mc_dayarch_help": "The annual operating year is composed of distinct day types, each with their own demand intensity multiplier. Adjust the relative frequency (days per year) and demand intensity (×) for each type. Defaults reflect Munich-specific patterns.",
        "mc_shock_help": "Stochastic events that perturb a single day's operations. Each event has an annual frequency (days per year) and a demand/cost impact multiplier. Events are sampled independently across the 60-month horizon.",
        "mc_dayarch_weekday": "Regular Weekday",
        "mc_dayarch_weekend": "Regular Weekend",
        "mc_dayarch_friday": "Friday/Saturday Evening",
        "mc_dayarch_holiday": "Public/School Holiday",
        "mc_dayarch_oktoberfest": "Oktoberfest (Sep 20-Oct 5)",
        "mc_dayarch_xmas": "Christmas Markets (Nov 25-Dec 23)",
        "mc_shock_severe_weather": "Severe Weather Day",
        "mc_shock_transit_strike": "Transit Strike",
        "mc_shock_major_event": "Major Event (concert/derby)",
        "mc_shock_tech_outage": "Tech/Network Outage",
        "mc_shock_heatwave": "Heat Wave (>32°C)",
        "mc_shock_black_ice": "Black Ice Morning (winter)",
        "mc_shock_road_closure": "Road/Bridge Closure",
        "mc_complete_msg": "✅ Monte Carlo simulation complete: {n} iterations processed in {t:.1f} seconds.",

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
        "subtitle": "*(HGB 3-Statement Model — Schicht 27A: Kapitalstruktur (Darlehen/Leasing/Eigenkapital-Tranchen) + Monte Carlo mit Tagestyp-Topologie + Stochastische Shock-Ereignisse)*",
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
        "help_init": "Auslastung Monat 1. 55% reflektiert drei nachfragetreibende Faktoren der MRRG Go-to-Market: (a) Preiselastizität durch 30-45% Unterbietung von Uber/Free Now bewirkt ~25-35% Mehrvolumen ggü. preisgleichen Launches (Cohen Uber/MIT 2016 Elastizitätsstudien), (b) Novelty-Effekt durch ersten europäischen Cybercab-Launch erzeugt PR-getriebene Probefahrtnachfrage (Cruise SF Frühwochen-Daten >70% Auslastungsspitzen), (c) versorgungsbeschränkte Startflotte (3 Fahrzeuge) konzentriert in 1-2 Hochdichtezonen (Maxvorstadt/Schwabing) operiert strukturell höher als marktbreite Operationen. Auf 24h-Kalenderbasis entspricht dies ~31% Asset-Auslastung (55% × 13,5h ÷ 24h).",
        "rec_rate": "Monatliche Erholung (+%)",
        "help_rec": "Monatliche Auslastungs-Erholungsrate. 5%/Monat ist erforderlich, damit die Auslastung mit der Kadenz der Flottenzugänge in J3-J5 mithalten kann (12+ Fahrzeuge/Jahr in Tranchen von 3-6 pro Quartal). Niedrigere Raten (3%/Monat, ) führten zum Auslastungseinbruch in J5, da Kannibalisierungseffekte schneller als die Erholung kumulierten. 5% benchmarked gegen Waymo SF Scaling-Phase-Erholungsrate (4-6%/Monat während aktiver Flottenexpansion); konsistent mit Uber Münchner 2014-2016 Fahrerangebots-Erholungskurven.",
        "can_fac": "Kannibalisierungsfaktor",
        "help_can": "Kannibalisierungsfaktor. 0,35 bedeutet, dass jede neue Kohorte vorübergehend 35% der inkrementellen Kapazität der Bestandsflotten-Auslastung abzieht. Der Standardwert 0,5 war empirisch zu aggressiv — ein ausgereiftes Dispatching mit 12+ Monaten Münchner Nachfragedaten sollte neue Fahrzeuge geografisch in unterversorgte Zonen umverteilen statt bestehende Routen zu überlappen. 0,35 benchmarked gegen MOIA Hamburg Flottenexpansionsdaten 2019-2023, wo Kannibalisierung in vergleichbaren Ramp-Phasen bei 30-40% gemessen wurde.",
        "util_label": "Ø Auslastung",
        "sec2": "2. FAHRTDYNAMIK",
        "trip_dist": "Durchschnittliche Fahrstrecke (km)",
        "dwell": "Standzeit pro Fahrt (Minuten)",
        "help_dwell": "Gesamte unproduktive Zeit pro Fahrt: Einstieg 60-90s (App-Verifizierung, Tür öffnen, hinsetzen) + Ausstieg 60-90s (Sachen sammeln, Fahrt beenden) + KI-Bestätigung/Sensor-Check 15-30s. Waymo Phoenix Empirik 2,5-4 Min. Erste 18-24 Monate ggf. höher (4-5 Min); Basisfall: eingespielte Nutzer.",
        "sec3": "3. PREISGESTALTUNG (inkl. 19% USt)",
        "base_fare": "Grundgebühr (€)",
        "price_km": "Preis pro km (€)",
        "tesla_take": "Tesla Plattformgebühr (%)",
        # === B2B-Lieferdienst-Strom (Standard AUS) ===
        "sec3b": "3b. B2B-LIEFERDIENST (Tesla Network)",
        "delivery_toggle": "B2B-Lieferdienst aktivieren",
        "help_delivery_toggle": "Tesla Network dispatched Cybercabs auch für Warenlieferungen (Food/Paket/Medizinprodukte) in Schwachlast-Phasen des Personenverkehrs. Selbe Dispatching-Architektur, separater Erlösstrom. Standard AUS für konservativen Basisfall. Bei Aktivierung wird die vollständige Asset-Produktivität abgebildet. Tesla steuert die Priorisierung (Personenfahrten haben Vorrang).",
        "delivery_hours": "Zusätzliche aktive Stunden / Tag (Lieferdienst)",
        "help_delivery_hours": "Inkrementelle produktive Stunden pro Tag bei aktivem Lieferstrom. 4,5h füllen Schwachlast-Fenster (Mittag 11-14 Uhr Teilüberlapp, Spätabend 22-1 Uhr, Frühmorgen B2B 5-7 Uhr). Kombiniert mit 13,5h Personenschicht = 18h Tesla Network aktiv pro 24h-Tag (75% 24h-Asset-Auslastung).",
        "delivery_revenue_per_trip": "Erlös pro Lieferfahrt (€, brutto inkl. 19% USt)",
        "help_delivery_rev": "Mischerlös pro abgeschlossenem Lieferzyklus. Lieferando/Uber Eats Food €4-6, B2B-Paket Last-Mile €3-5, Medizin/Pharmazie €8-15. €6,00 spiegelt Food-gewichteten Basisfall wider. Kunde zahlt brutto; 19% USt ans Finanzamt; 25% Tesla-Plattformgebühr auf netto.",
        "delivery_trips_per_active_hour": "Lieferungen pro aktiver Stunde",
        "help_delivery_trips": "Realistischer Lieferdurchsatz. Kürzere Standzeit (45-90s bei Abholung, 30-60s bei Zustellung) ggü. Personenverkehr (3,5 Min) ermöglicht 3 Lieferungen pro aktiver Stunde ggü. Personenverkehr ~2,4 Fahrten/Stunde. Impliziert ~14 Lieferungen pro 4,5h aktive Lieferschicht.",
        "delivery_take_rate": "Tesla Network Take-Rate auf Lieferungen (%)",
        "help_delivery_take": "Tesla Network Plattformgebühr auf Liefer-Bruttoerlös. Konservativ gleiche 25% wie Personenverkehr angenommen. Bei Tesla-Partnerschaft mit Logistikanbietern (DoorDash/Lieferando) nimmt der Partner seinen Anteil vor Tesla; Nettoeffekt für MRRG ähnlich direkter 25% Gebühr.",
        "delivery_ramp_y1": "Lieferdienst-Aktivierung % Jahr 1",
        "delivery_ramp_y2": "Lieferdienst-Aktivierung % Jahr 2",
        "delivery_ramp_y3": "Lieferdienst-Aktivierung % Jahr 3",
        "delivery_ramp_y4": "Lieferdienst-Aktivierung % Jahr 4",
        "delivery_ramp_y5": "Lieferdienst-Aktivierung % Jahr 5",
        "help_delivery_ramp": "Tesla Network Lieferdienst-Aktivierung nach Jahr. Standard 0/0/30/70/100 reflektiert Tesla Lieferdienst-Launch J2H2, reif J4. Stresstest: alle 0% (reiner Personenverkehr) oder 100% (sofortiger Start).",
        "sec4": "4. TÄGLICHE VARIABLE KOSTEN (Netto)",
        "cleaning": "Reinigungskosten pro Fahrzeug/Tag (€, netto Tesla-Gebühren)",
        "help_cleaning": "Update. Reinigungskosten €2/Tag NETTO unter Berücksichtigung der Tesla-Reinigungsgebühr-Erlöse. Tesla Robotaxi AGB (Dez 2025): $50 mittlere / $150 schwere Verschmutzungen pro Vorfall, automatisch über Innenraumkameras dem Fahrgast belastet. Bruttoreinigungskosten ~€5/Tag (Depot-Tiefenreinigung + Sensor-Waschflüssigkeit + Ozonbehandlung) abzüglich ~€3/Tag Gebührenerlöse bei 12 schweren + 30 mittleren Vorfällen pro Fahrzeug/Jahr im Reifezustand = €2/Tag netto. Verschmutzte Fahrzeuge fahren während des Ladefensters zum Depot — null Auswirkung auf die produktive Schicht.",
        "wear_rate": "Instandhaltung/Verschleiß pro km (€)",
        "wear_help": "Management-Sicht: nivellierter Verschleißsatz für 4-5j Scrap-Strategie (nach AfA-Schild). Aufschlüsselung: Reifen €0,027, Sensorwartung €0,034 (Cybercab Onboard-Reinigung reduziert ggü. Waymo-Benchmark), Innenraumverschleiß €0,012, Flüssigkeiten/Fahrwerk €0,005, HVAC/Inspektionen €0,005, Unfallrückstellung €0,008, Reserve €0,005. Benchmarks: Sixt+, Free Now, MOIA. Unter Waymo (€0,12-0,16) wegen einfacherem Cybercab-Sensorstack und deutschen Arbeitskosten.",
        # === Energie 3-Slider-Aufbau ===
        "energy_kwh": "Cybercab Verbrauch (kWh/km)",
        "help_energy_kwh": "Realer Cybercab-Energieverbrauch. Verankert in der Ankündigung von Tesla-VP Lars Moravy am 21. Mai 2026 beim Model S/X SE Event: Cybercab zertifiziert mit 165 Wh/Meile = 0,103 kWh/km (effizientestes EV aller Zeiten, 40% besser als Model 3). Real-Verbrauch im Stadtverkehr typisch 8-15% über EPA-Zertifizierung (HVAC, Verbraucher, Stop-and-Go). Standard 0,115 kWh/km wendet 12% Real-Aufschlag an. Cybercab erreicht dies durch: Tropfenform-Aerodynamik (Cd geschätzt <0,20), 2-Sitzer (keine Rücksitze/Struktur), kein Lenkrad/Pedale/Spiegel, schmalere Spezial-Reifen, Sub-50 kWh-Batterie, kein aggressives Fahrprofil.",
        "energy_eur": "Energie-Mischpreis (€/kWh)",
        "help_energy_eur": "Mischkosten pro kWh am Zähler. Verankert in (a) deutschem Großhandel 2-6 Uhr historisch €0,04-0,09/kWh (EPEX Off-Peak Base 2025: Ø €0,088/kWh), (b) Tesla Supercharger Deutschland 2026 Off-Peak €0,31-0,46/kWh, (c) Flotten-Abonnement-Rabatt (parallel zu Tesla Insurance Flotten-Modell). Basisfall €0,22/kWh = 70% Depot-Induktion über Nacht zu €0,18 (Großhandel + 8ct Netz/Marge) + 30% V4 Supercharger Off-Peak zu €0,32 (mit Flotten-Abo). Tesla-Anreizstruktur unterstützt dies: Tesla generiert mehr über 25% Plattform-Take-Rate als beim Nahe-Großhandel-Preis verloren ginge.",
        "charging_eff": "Ladewirkungsgrad (0,50-1,00)",
        "help_charging_eff": "Energie ins Akkupack als Bruchteil der aus dem Netz bezogenen Energie. Verankert in Teslas Aussage Oktober 2024: Cybercab-Induktivladung 'deutlich über 90%' effizient (auf Marques Brownlees 75%-Schätzung antwortend). Kabel-V4-Supercharger erreicht 96-97%. Standard 0,94 reflektiert 70% Induktion (92%) + 30% Kabel (96%) Mischung. Wiferion-Technologie (Tesla erworben) unterstützt 22 kW kabellos. Tesla erhielt FCC-Waiver Feb 2026 für UWB-Positionierung zur präzisen Pad-Ausrichtung.",
        "energy_derived_caption": "→ Abgeleitete Energiekosten: €{rate:.4f}/km (vor Saisonalität)",
        # === Abschnitt 5 Fixkosten — Versicherung/Stellplatz rekalibriert ===
        "sec5": "5. FAHRZEUG-FIXKOSTEN (€ / Monat, Netto)",
        "insurance": "Kfz-Versicherung",
        "help_insurance": "Rekalibrierung: €300 → €180/Monat. Bottom-up-Aufbau: Diebstahl-Komponente ~€0 (Cybercab außerhalb Tesla Network nicht fahrbar — Waymo Phoenix 7J-Daten zeigen ~0 erfolgreiche Diebstähle), aber Vandalismus (€20), Batterie/Brand (€20), Wetter (€12), Passagierschäden (€15), Cyber-Haftung (€40), Rechtsrücklage (€30), Rest-Personen-/Sachschadenshaftung nach 70% FSD-Sicherheitsbonus (€55), gesetzliche Passagiertransport-Deckung gem. PBefG (€18) = ~€210, abzüglich ~15% Tesla Insurance-Bundle-Rabatt und 5-Jahres-Mittelung = €180. J1-J2 Ist-Werte können €250-300 betragen, bevor sie mit aufgebauter Münchener Schadensdatenhistorie sinken. Risiko: bei Verzögerungen der Tesla Insurance Europe-Lizenzierung könnte die Prämie auf €280-350 steigen.",
        "parking": "Münchner Stellplatz (APCOA Lade-Infrastruktur)",
        "help_parking": "Rekalibrierung: €250 → €170/Monat. APCOA veröffentlichte 2024 Münchner Monatsparkplätze €120-180 + Ladefähigkeits-Aufschlag €40-80 = Basisfall €160-220. Bei J5 Flotte von 57 Fahrzeugen reduziert Mengenrabatt 15-25% auf €140-180. €170 entspricht Mittelpunkt verhandelbarer Flotten-Mengenrabatt-Rate. Beinhaltet induktiven Ladepad-Zugang ab J3+, kabelgebundene V4-Backup in J1-J2.",
        "telemetry": "Telemetrie & API",
        "tuev": "TÜV / BO-Kraft Rückstellung",
        "help_tuev": "Monatliche Rückstellung für die BO-Kraft Untersuchung.",
        "charging_sub": "Tesla Lade-Abo",
        "cargo_ins": "Verkehrshaftungsversicherung (Frachtgut)",
        "help_cargo_ins": "NEUE POSITION. Gesetzliche Transporthaftpflicht bei aktivem B2B-Lieferdienst-Toggle. Deckt Frachtwert, Diebstahl in Transit, Wetterschäden, Handhabungsansprüche. Profitiert NICHT vom FSD-Sicherheitsbonus (Risiken hängen nicht vom Fahrverhalten ab). €20/Fahrzeug/Monat entspricht 2024 deutschen Verkehrshaftungsversicherungs-Tarifen für niedrigwertige Paket-/Food-Kurier-Operationen. Nur fakturiert wenn Lieferstrom aktiv.",
        # === Monatliche Saisonalitäts-Multiplikatoren ===
        "sec_season": "1d. SAISONALITÄT (Winter-Aufschlag)",
        "season_expander": "📅 Monatliche Energie-Multiplikatoren",
        "season_caption": "Pro-Monat Energiekosten-Multiplikatoren anpassen. Wirkt auf Energieposten in GuV. Empirische Anker: ADAC Wintertest 2023 (-35-55% EV-Reichweite Dez-Feb), Geotab Flottenstudie (+8-15% Sommer-Klimaanlage). Tesla 4680 Trocken-Kathode reduziert Winter-Aufschlag um 10-15% ggü. 2170-Zellen.",
        "month_jan": "Januar Multiplikator",
        "month_feb": "Februar Multiplikator",
        "month_mar": "März Multiplikator",
        "month_apr": "April Multiplikator",
        "month_may": "Mai Multiplikator",
        "month_jun": "Juni Multiplikator",
        "month_jul": "Juli Multiplikator",
        "month_aug": "August Multiplikator",
        "month_sep": "September Multiplikator",
        "month_oct": "Oktober Multiplikator",
        "month_nov": "November Multiplikator",
        "month_dec": "Dezember Multiplikator",
        "season_blend_caption": "→ Jahresmittel: {blend:.4f}× (1,0 = keine Saisonalität)",
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
        "help_thg": "Treibhausgasminderungsquote gem. § 7 Abs. 1 38. BImSchV. Jährliche Pauschalzahlung pro zugelassenes E-Fahrzeug pro Kalenderjahr, VOLL ausgezahlt unabhängig vom Zulassungszeitpunkt im Jahr, sofern Zulassung vor Stichtag 15. November. Nov-Dez-Zulassungen werden auf Folgejahr-Januar verschoben. Standard €280 entspricht 2024 deutschen Markt-Ist-Werten (Bandbreite €150-450 je nach Anbieter). 2025-2028 Forward-Preise volatil. Quelle: ADAC, EnBW, Finanztip, Klima-Quote, elektrovorteil.",
        "salvage": "Fahrzeugverkaufspreis (Ende 5-J. Nutzungsdauer)",
        
        "pnl_gbv": "Bruttobuchungswert (Kunde zahlt inkl. 19% USt)",
        "pnl_vat": "Abzüglich: 19% Umsatzsteuer (Finanzamt)",
        "pnl_net_rev": "Umsatzerlöse (netto)",
        "pnl_tesla_fee": "Abzüglich: Tesla-Plattformgebühr (auf Netto)",
        "pnl_mrrg_net": "MRRG Nettoerlöse (nach Plattformgebühr) — Personenverkehr",
        # === B2B-Lieferdienst-Erlöse (Tesla Network) ===
        "pnl_delivery_gbv": "Bruttobuchungen Lieferdienst (Tesla Network B2B, inkl. 19% USt)",
        "pnl_delivery_vat": "Abzüglich: 19% USt auf Lieferungen (Finanzamt)",
        "pnl_delivery_net_rev": "Netto-Lieferumsatzerlöse",
        "pnl_delivery_tesla_fee": "Abzüglich: Tesla-Plattformgebühr Lieferdienst",
        "pnl_delivery_mrrg_net": "MRRG Nettoerlöse (nach Plattformgebühr) — Lieferdienst",
        "pnl_total_mrrg_net": "GESAMT MRRG Nettoerlöse (Personenverkehr + Lieferdienst)",
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
        # === Monte Carlo Risiko- & Varianzanalyse ===
        "tab_mc": "🎲 Risiko- & Varianzanalyse (Monte Carlo)",
        "mc_header": "Risiko- & Varianzanalyse — Stochastische Monte-Carlo-Simulation",
        "mc_intro": "Dieses Modul kapselt die deterministische 60-Monats-Engine in einer stochastischen Monte-Carlo-Simulation. Die 12 varianztreibenden Parameter werden aus empirisch verankerten Wahrscheinlichkeitsverteilungen über N Iterationen gezogen. Der deterministische Basisfall in den anderen Tabs bleibt unverändert — diese Analyse ist eine ergänzende Risikozerlegung für Bank-Kreditkomitees und Project-Finance-Bewertung.",
        "mc_run_button": "🎲 Monte-Carlo-Simulation starten",
        "mc_n_iterations": "Anzahl Iterationen (N)",
        "mc_n_help": "5.000 produziert stabile Perzentile in ~30-60 Sek. 10.000 produziert nahezu finale Konvergenz in ~60-120 Sek. Unter 1.000 statistisch unzuverlässig.",
        "mc_section_dist": "📊 Verteilungsparameter (Standardwerte anpassen)",
        "mc_section_outputs": "📈 Simulationsergebnisse",
        "mc_progress_label": "Monte-Carlo-Iteration {i} von {n} läuft...",
        "mc_no_results": "ℹ️ Klicken Sie oben auf **Monte-Carlo-Simulation starten**, um die stochastische Risikoanalyse zu generieren.",
        "mc_kpi_header": "Schlüssel-Risikoindikatoren — Perzentilverteilung",
        "mc_kpi_p5": "P5 (Severer Downside)",
        "mc_kpi_p25": "P25 (Konservativ)",
        "mc_kpi_p50": "P50 (Median)",
        "mc_kpi_p75": "P75 (Optimistisch)",
        "mc_kpi_p95": "P95 (Blue Sky)",
        "mc_kpi_ni_cum": "5-Jahres Kumulierter Jahresüberschuss (€)",
        "mc_kpi_y5_ebitda": "Jahr 5 EBITDA (€)",
        "mc_kpi_min_cash": "Minimaler Kassenstand (€)",
        "mc_kpi_insolvency": "Insolvenz-Wahrscheinlichkeit",
        "mc_chart_ni_title": "Verteilung: 5-Jahres Kumulierter Jahresüberschuss",
        "mc_chart_cash_title": "Verteilung: Minimaler Kassenstand ggü. Pufferschwelle",
        "mc_chart_tornado_title": "Sensitivitäts-Tornado — Pearson r ggü. 5J Kumuliertem Jahresüberschuss",
        "mc_tornado_xaxis": "Pearson-Korrelationskoeffizient (r)",
        "mc_buffer_line_label": "Mindestkassen-Pufferschwelle",
        "mc_p5_label": "P5",
        "mc_p95_label": "P95",
        "mc_p50_label": "P50 (Median)",
        "mc_p_wear": "Verschleiß σ (€/km)",
        "mc_p_energy_eur": "Energiepreis σ (€/kWh)",
        "mc_p_target_util": "Zielauslastung Bereich",
        "mc_p_insurance": "Versicherung €/Mo (Min/Mode/Max)",
        "mc_p_take_rate": "Tesla Plattformgebühr (Min/Mode/Max)",
        "mc_p_kwh_per_km": "Cybercab Verbrauch σ (kWh/km)",
        "mc_p_deadhead": "Leerfahrtenrate σ",
        "mc_p_trip_dist": "Fahrtdistanz σ (km)",
        "mc_p_delivery_y3": "Lieferdienst J3 Ramp (Min/Mode/Max)",
        "mc_p_price": "Preis pro km σ (€)",
        "mc_p_salvage": "Restwert σ (€)",
        "mc_p_winter": "Winter-Saisonalität σ (×)",
        # === Erweiterte Parameter (22+) gem. Tier 1/2/3-Spezifikation ===
        "mc_p_active_hours": "Aktive Stunden σ (h/Tag)",
        "mc_p_speed": "Durchschnittsgeschwindigkeit σ (km/h)",
        "mc_p_dwell": "Standzeit σ (Min)",
        "mc_p_init_util": "Init-Auslastung σ",
        "mc_p_rec_rate": "Erholungsrate σ",
        "mc_p_can_fac": "Kannibalisierungsfaktor σ",
        "mc_p_dy2": "Lieferdienst J2 (Min/Mode/Max)",
        "mc_p_dy4": "Lieferdienst J4 (Min/Mode/Max)",
        "mc_p_capex": "Cybercab Basispreis USD σ",
        "mc_p_fx": "USD/EUR Wechselkurs σ",
        "mc_p_ltv": "Fahrzeug-LTV σ",
        "mc_p_loan_y1": "J1 Kreditzins (Min/Mode/Max)",
        "mc_p_loan_y2": "J2 Kreditzins (Min/Mode/Max)",
        "mc_p_cleaning": "Reinigung €/Tag σ",
        "mc_p_parking": "Stellplatz €/Mo σ",
        "mc_p_customs": "Zollsatz σ",
        # Metric Dropdown
        "mc_metric_selector": "Ziel-Analysemetrik auswählen",
        "mc_metric_fcf": "Free Cash Flow",
        "mc_metric_ebitda": "EBITDA",
        "mc_metric_ni": "Jahresüberschuss",
        "mc_kpi_fcf_cum": "5-Jahres Kumulierter Free Cash Flow (€)",
        "mc_chart_fcf_title": "Verteilung: 5-Jahres Kumulierter Free Cash Flow",
        "mc_chart_ebitda_title": "Verteilung: Jahr 5 EBITDA",
        # Tier-Section-Header
        "mc_tier1_header": "🔥 Tier 1 — Hauptvarianztreiber (Operative Physik)",
        "mc_tier2_header": "⚡ Tier 2 — Materielle Varianz (Capex, Schulden, Kosten)",
        "mc_tier3_header": "💧 Tier 3 — Geringere Varianz (Betriebskosten)",
        "mc_running_msg": "🔄 Monte-Carlo-Simulation läuft. Bitte warten...",
        # === Kapitalstruktur & Flotten-Finanzierungs-Matrix ===
        "fin_matrix_header": "💳 Kapitalallokation & Fahrzeug-Finanzierungsstrategie",
        "fin_matrix_help": "Finanzierungsmix pro Jahr konfigurieren. Fahrzeugzugänge werden in drei Tranchen aufgeteilt: Bankdarlehen (Schulden-finanziert, Aktivierung), Operating Leasing (off-balance, ARAP für Sonderzahlung), und 100% Eigenkapital (vollständige Capex aus Cash mit optionalem Capital Call). Slider normalisieren automatisch auf 100% pro Jahr.",
        "fin_year_label": "Jahr {y} Finanzierungs-Mix",
        "fin_pct_loan": "% Darlehen",
        "fin_pct_lease": "% Leasing",
        "fin_pct_equity": "% Eigenkapital",
        "fin_loan_section": "🏦 Bankdarlehen-Parameter (Tranche A)",
        "fin_lease_section": "📋 Operating-Leasing-Parameter (Tranche B) — Global",
        "fin_equity_section": "💰 Eigenkapital/Cash-Allokation (Tranche C)",
        "fin_lease_money_factor": "Monatlicher Leasing-Faktor (×Capex)",
        "fin_lease_money_factor_help": "Monatliche Leasingrate als Bruchteil der Bruttoanschaffungskosten. Standard 0,015 = 1,5%/Monat, typisch für 60-Monats-Gewerbeleasing in DE. Enthält Finanzierungskosten + Leasinggebermarge + Restwertrisikoprämie.",
        "fin_lease_downpayment_pct": "Leasingsonderzahlung (% der Capex)",
        "fin_lease_downpayment_help": "Einmalige Sonderzahlung bei Leasingbeginn. Gem. HGB § 250 als ARAP (Aktiver Rechnungsabgrenzungsposten) aktiviert und linear über die Leasinglaufzeit abgeschrieben. Standard 15% entspricht üblichen deutschen Gewerbe-Fahrzeugleasingverträgen.",
        "fin_lease_term_months": "Leasing-Laufzeit (Monate)",
        "fin_equity_capital_call": "Auto-Capital-Call bei Liquiditätsengpass",
        "fin_equity_capital_call_help": "Wenn eigenkapital-finanzierte Fahrzeugzugänge den Kassenbestand unter null drücken würden (nach maximaler Kontokorrent-Nutzung), automatische Gründer-Eigenkapital-Injektion zur Bilanzfinanzierung. Deaktiviert = Engpass als Kontokorrent-Verletzung (Insolvenz-Flag) behandeln.",
        "fin_norm_warning": "⚠️ Jahr {y} Prozentwerte summieren auf {s}% — werden auf 100% normalisiert.",
        "bs_arap": "ARAP (Vorausgezahltes Leasing)",
        "pnl_lease": "Leasing-Aufwand (Mietleasing)",
        "cf_lease": "Leasing-Zahlungen + ARAP-Setup",
        "cf_capital_call": "Gründer Capital-Call (Eigenkapital-Injektion)",
        # Tagestyp + Shock-Ereignis-Labels
        "mc_dayarch_header": "📅 Tagestyp-Mix (Phase A) — tägliche Nachfrage-Varianztopologie",
        "mc_shock_header": "⚡ Stochastische Shock-Ereignisse (Phase B) — Jahresfrequenz × Wirkung",
        "mc_dayarch_help": "Das jährliche Betriebsjahr besteht aus unterschiedlichen Tagestypen mit jeweils eigenem Nachfrageintensitäts-Multiplikator. Häufigkeit (Tage/Jahr) und Nachfrageintensität (×) je Typ anpassbar.",
        "mc_shock_help": "Stochastische Ereignisse, die einzelne Betriebstage stören. Jedes Ereignis hat eine Jahresfrequenz (Tage/Jahr) und einen Nachfrage-/Kostenfaktor. Ereignisse werden unabhängig über den 60-Monats-Horizont gezogen.",
        "mc_dayarch_weekday": "Regulärer Werktag",
        "mc_dayarch_weekend": "Reguläres Wochenende",
        "mc_dayarch_friday": "Freitag/Samstag Abend",
        "mc_dayarch_holiday": "Feiertag/Schulferien",
        "mc_dayarch_oktoberfest": "Oktoberfest (20. Sep - 5. Okt)",
        "mc_dayarch_xmas": "Weihnachtsmärkte (25. Nov - 23. Dez)",
        "mc_shock_severe_weather": "Wetter-Extremtag",
        "mc_shock_transit_strike": "ÖPNV-Streik",
        "mc_shock_major_event": "Großevent (Konzert/Derby)",
        "mc_shock_tech_outage": "Tech-/Netzwerk-Ausfall",
        "mc_shock_heatwave": "Hitzewelle (>32°C)",
        "mc_shock_black_ice": "Glatteis-Morgen (Winter)",
        "mc_shock_road_closure": "Straßen-/Brückensperrung",
        "mc_complete_msg": "✅ Monte-Carlo-Simulation abgeschlossen: {n} Iterationen in {t:.1f} Sek. verarbeitet.",

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

# Surface bad fleet input to the user (rather than silently zeroing out).
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
active_hours_per_day = st.sidebar.number_input(loc["active_hours"], value=16.0, help=loc["help_active_hours"])
avg_speed_kmh = st.sidebar.number_input(loc["speed"], value=19.0, help=loc["help_speed"])
deadhead_rate = st.sidebar.number_input(loc["deadhead"], value=22.0, help=loc["help_deadhead"]) / 100

st.sidebar.header(loc["sec1c"])
util_mode = st.sidebar.radio(loc["util_mode"], [loc["util_dyn"], loc["util_fix"]])
if util_mode == loc["util_dyn"]:
    target_util = st.sidebar.number_input(loc["target_util"], value=75.0, help=loc["help_target"]) / 100
    init_util = st.sidebar.number_input(loc["init_util"], value=55.0, help=loc["help_init"]) / 100
    rec_rate = st.sidebar.number_input(loc["rec_rate"], value=5.0, help=loc["help_rec"]) / 100
    can_fac = st.sidebar.number_input(loc["can_fac"], value=0.35, step=0.05, help=loc["help_can"])
    flat_util = target_util
else:
    flat_util = st.sidebar.number_input(loc["util_fix"], value=90.0) / 100
    target_util, init_util, rec_rate, can_fac = flat_util, flat_util, 0, 0

# === Compute is_dynamic boolean from localized radio selection ===
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

# === B2B Delivery Stream sidebar section ===
st.sidebar.header(loc["sec3b"])
delivery_enabled = st.sidebar.checkbox(loc["delivery_toggle"], value=False, help=loc["help_delivery_toggle"])
if delivery_enabled:
    delivery_hours_per_day = st.sidebar.number_input(loc["delivery_hours"], value=4.5, help=loc["help_delivery_hours"])
    delivery_rev_per_trip = st.sidebar.number_input(loc["delivery_revenue_per_trip"], value=6.00, step=0.50, help=loc["help_delivery_rev"])
    delivery_trips_per_hour = st.sidebar.number_input(loc["delivery_trips_per_active_hour"], value=3.0, step=0.5, help=loc["help_delivery_trips"])
    delivery_take_rate = st.sidebar.number_input(loc["delivery_take_rate"], value=25.0, step=1.0, help=loc["help_delivery_take"]) / 100
    delivery_ramp_y1 = st.sidebar.number_input(loc["delivery_ramp_y1"], value=0.0, min_value=0.0, max_value=100.0, step=10.0, help=loc["help_delivery_ramp"]) / 100
    delivery_ramp_y2 = st.sidebar.number_input(loc["delivery_ramp_y2"], value=0.0, min_value=0.0, max_value=100.0, step=10.0) / 100
    delivery_ramp_y3 = st.sidebar.number_input(loc["delivery_ramp_y3"], value=30.0, min_value=0.0, max_value=100.0, step=10.0) / 100
    delivery_ramp_y4 = st.sidebar.number_input(loc["delivery_ramp_y4"], value=70.0, min_value=0.0, max_value=100.0, step=10.0) / 100
    delivery_ramp_y5 = st.sidebar.number_input(loc["delivery_ramp_y5"], value=100.0, min_value=0.0, max_value=100.0, step=10.0) / 100
else:
    # Zero-out all delivery params when toggle is OFF — engine never sees delivery revenue
    delivery_hours_per_day = 0.0
    delivery_rev_per_trip = 0.0
    delivery_trips_per_hour = 0.0
    delivery_take_rate = 0.0
    delivery_ramp_y1 = delivery_ramp_y2 = delivery_ramp_y3 = delivery_ramp_y4 = delivery_ramp_y5 = 0.0

# === Monthly Seasonality Multipliers — fully adjustable ===
# Prior Layers 20/21 hardcoded 4-tier (Dec-Feb 1.45, Nov/Mar 1.30, Apr/Oct 1.05, May-Sep 1.10).
# exposes all 12 months as individual sliders so user can stress-test
# winter penalty assumptions (e.g., dry-cathode 4680 battery reduces winter penalty).
# Annual blend computed at runtime; default values preserve 1.2125× blend.
st.sidebar.header(loc["sec_season"])
with st.sidebar.expander(loc["season_expander"], expanded=False):
    st.caption(loc["season_caption"])
    season_jan = st.number_input(loc["month_jan"], value=1.45, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_feb = st.number_input(loc["month_feb"], value=1.45, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_mar = st.number_input(loc["month_mar"], value=1.30, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_apr = st.number_input(loc["month_apr"], value=1.05, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_may = st.number_input(loc["month_may"], value=1.10, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_jun = st.number_input(loc["month_jun"], value=1.10, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_jul = st.number_input(loc["month_jul"], value=1.10, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_aug = st.number_input(loc["month_aug"], value=1.10, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_sep = st.number_input(loc["month_sep"], value=1.10, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_oct = st.number_input(loc["month_oct"], value=1.05, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_nov = st.number_input(loc["month_nov"], value=1.30, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
    season_dec = st.number_input(loc["month_dec"], value=1.45, format="%.2f", step=0.01, min_value=0.50, max_value=2.50)
# Assemble lookup dict (month index 1-12 → multiplier)
seasonality_by_month = {
    1: season_jan, 2: season_feb, 3: season_mar, 4: season_apr,
    5: season_may, 6: season_jun, 7: season_jul, 8: season_aug,
    9: season_sep, 10: season_oct, 11: season_nov, 12: season_dec
}
_season_blend = sum(seasonality_by_month.values()) / 12
st.sidebar.caption(loc["season_blend_caption"].format(blend=_season_blend))

st.sidebar.header(loc["sec4"])
cleaning_cost_per_day = st.sidebar.number_input(loc["cleaning"], value=2.00, help=loc["help_cleaning"])
wear_and_tear_rate = st.sidebar.number_input(loc["wear_rate"], value=0.10, format="%.2f", step=0.01, help=loc["wear_help"])
# === Energy decomposed into 3 sliders ===
# Prior had a single energy_rate = €0.085/km combining all three.
# makes each driver visible and adjustable for stress-testing.
# Combined: 0.115 * 0.22 / 0.94 = €0.0269/km (vs prior €0.085 — 68% reduction).
# Empirical anchors documented in tooltips and README section.
energy_kwh_per_km = st.sidebar.number_input(loc["energy_kwh"], value=0.115, format="%.3f", step=0.005, help=loc["help_energy_kwh"])
energy_eur_per_kwh = st.sidebar.number_input(loc["energy_eur"], value=0.220, format="%.3f", step=0.01, help=loc["help_energy_eur"])
charging_efficiency = st.sidebar.number_input(loc["charging_eff"], value=0.94, format="%.2f", step=0.01, min_value=0.50, max_value=1.00, help=loc["help_charging_eff"]) 
# Derived: effective €/km consumed (before seasonality multiplier in engine)
energy_rate = (energy_kwh_per_km * energy_eur_per_kwh) / charging_efficiency
# Visible read-out in sidebar so user can see the combined number
st.sidebar.caption(loc["energy_derived_caption"].format(rate=energy_rate))

st.sidebar.header(loc["sec5"])
# Insurance recalibrated €300 → €180 (Tesla bundling thesis, FSD safety credit, theft-zero)
insurance_pm = st.sidebar.number_input(loc["insurance"], value=180.0, help=loc["help_insurance"])
# APCOA parking recalibrated €250 → €170 (published APCOA rates + bulk discount)
parking_pm = st.sidebar.number_input(loc["parking"], value=170.0, help=loc["help_parking"])
telemetry_pm = st.sidebar.number_input(loc["telemetry"], value=100.0)
tuev_pm = st.sidebar.number_input(loc["tuev"], value=15.0, help=loc["help_tuev"])
charging_sub_pm = st.sidebar.number_input(loc["charging_sub"], value=10.0)
# === Cargo insurance — only applies when delivery toggle ON ===
# Verkehrshaftungsversicherung for B2B goods transport. Doesn't benefit from FSD
# safety credit (covers cargo theft, weather damage, in-transit handling claims).
if delivery_enabled:
    delivery_cargo_insurance_pm = st.sidebar.number_input(loc["cargo_ins"], value=20.0, help=loc["help_cargo_ins"])
else:
    delivery_cargo_insurance_pm = 0.0

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

# ===================================================================
# === CAPITAL ALLOCATION & VEHICLE FINANCING STRATEGY MATRIX ========
# ===================================================================
# Per-year (Y1-Y5) financing mix configuration. Each year's vehicle
# cohort additions are split into three tranches with independent HGB
# accounting treatment:
#   • Tranche A (Loan) → Capitalize asset; AfA; debt drawn @ LTV;
#                        interest+principal flows; full salvage
#   • Tranche B (Lease) → Operating lease per HGB; NO capitalization
#                         (lessor owns); ARAP for Sonderzahlung;
#                         monthly lease expense in pos3; NO salvage
#   • Tranche C (Equity) → Capitalize asset; AfA; FULL cash drain;
#                          optional founder capital-call on shortfall;
#                          NO debt; full salvage
# Defaults: 100% Loan / 0% Lease / 0% Equity per year — preserves
# backward compatibility (zero regression vs prior layers when
# defaults unchanged).
# ===================================================================
with st.sidebar.expander(loc["fin_matrix_header"], expanded=False):
    st.caption(loc["fin_matrix_help"])
    # Per-year financing mix matrix
    fin_mix_by_year = {}  # year -> (loan_pct, lease_pct, equity_pct)
    for _y_idx in range(1, 6):
        st.markdown(f"**{loc['fin_year_label'].format(y=_y_idx)}**")
        _cl1, _cl2, _cl3 = st.columns(3)
        with _cl1:
            _pct_loan = st.number_input(
                f"{loc['fin_pct_loan']} (Y{_y_idx})",
                min_value=0, max_value=100, value=100, step=5, key=f"fin_loan_y{_y_idx}"
            )
        with _cl2:
            _pct_lease = st.number_input(
                f"{loc['fin_pct_lease']} (Y{_y_idx})",
                min_value=0, max_value=100, value=0, step=5, key=f"fin_lease_y{_y_idx}"
            )
        with _cl3:
            _pct_equity = st.number_input(
                f"{loc['fin_pct_equity']} (Y{_y_idx})",
                min_value=0, max_value=100, value=0, step=5, key=f"fin_equity_y{_y_idx}"
            )
        # Auto-normalize: if sum != 100, scale proportionally; if all zero, default 100% loan
        _sum = _pct_loan + _pct_lease + _pct_equity
        if _sum == 0:
            _pct_loan, _pct_lease, _pct_equity = 100, 0, 0
            _sum = 100
        if _sum != 100:
            st.caption(loc["fin_norm_warning"].format(y=_y_idx, s=_sum))
        fin_mix_by_year[_y_idx] = (
            _pct_loan / _sum,
            _pct_lease / _sum,
            _pct_equity / _sum,
        )

    # Global lease parameters (apply to all years' lease tranches)
    st.markdown(f"**{loc['fin_lease_section']}**")
    lease_money_factor = st.number_input(
        loc["fin_lease_money_factor"],
        value=0.015, min_value=0.005, max_value=0.050, step=0.001, format="%.3f",
        help=loc["fin_lease_money_factor_help"]
    )
    lease_downpayment_pct = st.number_input(
        loc["fin_lease_downpayment_pct"],
        value=15.0, min_value=0.0, max_value=50.0, step=1.0,
        help=loc["fin_lease_downpayment_help"]
    ) / 100
    lease_term_months = st.number_input(
        loc["fin_lease_term_months"],
        value=60, min_value=24, max_value=72, step=12
    )

    # Global equity policy
    st.markdown(f"**{loc['fin_equity_section']}**")
    equity_capital_call_enabled = st.checkbox(
        loc["fin_equity_capital_call"],
        value=True,
        help=loc["fin_equity_capital_call_help"]
    )

vat_bridge_rate = st.sidebar.number_input(loc["vat_rate_input"], value=6.5, step=0.1) / 100
vat_lag_months = st.sidebar.number_input(loc["vat_lag_input"], value=3, min_value=1, max_value=12)
min_cash_buffer = st.sidebar.number_input(loc["cash_buffer_input"], value=10000.0, step=5000.0)
max_overdraft_limit = st.sidebar.number_input(loc["max_overdraft_input"], value=50000.0, step=10000.0, help=loc["help_max_od"])
legal_provision_rate = st.sidebar.number_input(loc["legal_provision_input"], value=200.0, step=50.0)
interest_income_rate = st.sidebar.number_input(loc["int_rate"], value=2.2) / 100

st.sidebar.header(loc["sec9"])
thg_quote_per_car_py = st.sidebar.number_input(loc["thg"], value=280.0, help=loc["help_thg"])
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
    thg_quote_per_car_py, salvage_value_per_car_y4, max_overdraft_limit,
    delivery_enabled, delivery_hours_per_day, delivery_rev_per_trip,
    delivery_trips_per_hour, delivery_take_rate,
    delivery_ramp_y1, delivery_ramp_y2, delivery_ramp_y3, delivery_ramp_y4, delivery_ramp_y5,
    delivery_cargo_insurance_pm, seasonality_by_month,
    is_dynamic, lang_choice,
    fin_mix_by_year=None,
    lease_money_factor=0.015, lease_downpayment_pct=0.15, lease_term_months=60,
    equity_capital_call_enabled=True
):
    # ============================================================
    # is_dynamic parameter added before lang_choice
    # Replaces the buggy hardcoded English string comparison that
    # silently failed in German mode and forced flat utilization.
    # ============================================================
    
    # Pure Static Keys to Prevent Variable Reference Errors in Cache Mapping
    # === P&L static keys — additional rows for delivery stream ===
    # P_DGBV  = Delivery Gross Booking Value (gross of VAT)
    # P_DVAT  = Delivery VAT remitted to Finanzamt
    # P_DNET  = Delivery Net Revenue (excl VAT)
    # P_DTFEE = Tesla Network fee on delivery net
    # P_DMNET = MRRG Net Revenue from Delivery (after Tesla fee)
    # P_TMNET = Total MRRG Net Revenue (Passenger + Delivery)
    P_GBV, P_VAT, P_NET, P_TFEE, P_MNET, P_DGBV, P_DVAT, P_DNET, P_DTFEE, P_DMNET, P_TMNET, P_EN, P_WR, P_CL, P_LSE, P_DB1, P_INS, P_PK, P_API, P_TV, P_SUB, P_DB2, P_HQ, P_IT, P_LEG, P_HINS, P_FEE, P_BNK, P_LPR, P_THG, P_EB, P_EB_HGB, P_AF_V, P_AF_I, P_SAL, P_EBIT, P_I_IN, P_I_EX, P_EBT, P_TX, P_NI = [
        "pnl_gbv", "pnl_vat", "pnl_net_rev", "pnl_tesla_fee", "pnl_mrrg_net",
        "pnl_delivery_gbv", "pnl_delivery_vat", "pnl_delivery_net_rev", "pnl_delivery_tesla_fee", "pnl_delivery_mrrg_net", "pnl_total_mrrg_net",
        "pnl_energy", "pnl_wear", "pnl_clean", "pnl_lease", "pnl_db1", "pnl_ins", "pnl_park",
        "pnl_api", "pnl_tuev", "pnl_sub", "pnl_db2", "pnl_hq_lease", "pnl_it", "pnl_legal", "pnl_hq_ins", "pnl_fees", "pnl_bank", "pnl_legal_prov", "pnl_thg",
        "pnl_ebitda", "pnl_ebitda_hgb", "pnl_afa_veh", "pnl_afa_it", "pnl_salvage", "pnl_ebit", "pnl_int_inc", "pnl_int_exp", "pnl_ebt", "pnl_tax", "pnl_ni"
    ]

    C_NI, C_DP, C_GS, C_TP, C_TPD, C_LPR, C_WCT, C_VCOL, C_VPD, C_LSE, C_OP, C_CAP, C_VRF, C_SLE, C_INV, C_EQ, C_CC, C_SH, C_KFW, C_PRN, C_VDR, C_VRP, C_OD, C_FIN, C_NET, C_BEG, C_END = [
        "cf_ni", "cf_depr", "cf_gain_sale", "cf_tax_prov", "cf_tax_paid", "cf_legal_prov", "cf_wc_thg", "cf_vat_coll", "cf_vat_paid", "cf_lease", "cf_op",
        "cf_capex", "cf_vat_ref", "cf_sale", "cf_inv", "cf_eq", "cf_capital_call", "cf_sh", "cf_kfw_draw", "cf_prin", "cf_vat_draw", "cf_vat_repay", "cf_overdraft_delta",
        "cf_fin", "cf_net", "cf_beg", "cf_end"
    ]

    B_GF, B_AD, B_NF, B_VR, B_OPVRX, B_TR, B_TRX, B_ARAP, B_CS, B_TC, B_TA, B_ES, B_ER, B_TEQ, B_PT, B_PL, B_TPV, B_DK, B_DV, B_DO, B_PV, B_SL, B_TL, B_TLEQ, B_CH = [
        "bs_gfa", "bs_acc_depr", "bs_nfa", "bs_vat_rec", "bs_vat_rec_op", "bs_thg_rec", "bs_tax_rec", "bs_arap", "bs_cash", "bs_tca", "bs_ta", "bs_eq_share", "bs_eq_ret", "bs_teq",
        "bs_prov_tax", "bs_prov_legal", "bs_tprov", "bs_debt_kfw", "bs_debt_vat", "bs_debt_overdraft", "bs_pay_vat", "bs_sh_loan", "bs_tliab", "bs_tleq", "bs_check"
    ]
    bs_keys_internal = [B_GF, B_AD, B_NF, B_VR, B_OPVRX, B_TR, B_TRX, B_ARAP, B_CS, B_TC, B_TA, B_ES, B_ER, B_TEQ, B_PT, B_PL, B_TPV, B_DK, B_DV, B_DO, B_PV, B_SL, B_TL, B_TLEQ, B_CH]

    def parse_adds(add_str):
        try:
            arr = [int(x.strip()) for x in add_str.split(',')]
            return (arr + [0]*12)[:12]
        except:
            return [0]*12

    all_adds = parse_adds(y1_adds_str) + parse_adds(y2_adds_str) + parse_adds(y3_adds_str) + parse_adds(y4_adds_str) + parse_adds(y5_adds_str)
    # === base_fleet_size restored inside cached function scope ===
    base_fleet_size = sum(parse_adds(y1_adds_str))
    
    cybercab_base_eur = cybercab_base_usd / usd_eur_rate
    zollwert_cif_eur = cybercab_base_eur + import_freight_eur
    zollkosten_eur = zollwert_cif_eur * customs_duty_rate
    total_capex_per_car = zollwert_cif_eur + zollkosten_eur

    # === Default financing mix fallback (preserves backward compat) ===
    if fin_mix_by_year is None:
        fin_mix_by_year = {y: (1.0, 0.0, 0.0) for y in range(1, 6)}

    cohorts = []
    for m in range(60):
        mo_val = all_adds[m]
        if mo_val > 0:
            # Determine which year this cohort falls into (Y1..Y5)
            year_of_cohort = (m // 12) + 1  # m in [0..59] -> year 1..5
            mix = fin_mix_by_year.get(year_of_cohort, (1.0, 0.0, 0.0))
            loan_frac, lease_frac, equity_frac = mix
            capex_full = mo_val * total_capex_per_car

            # Tranche A: Loan-financed (capitalize + AfA + debt)
            capex_loan = capex_full * loan_frac
            loan = capex_loan * vehicle_ltv  # debt = capex × LTV (only on loan tranche)
            rate = y1_loan_rate if m < 12 else y2_loan_rate
            monthly_rate = rate / 12
            if monthly_rate > 0:
                pmt = loan * (monthly_rate * (1 + monthly_rate)**VEHICLE_AMORTIZATION_PERIOD) / ((1 + monthly_rate)**VEHICLE_AMORTIZATION_PERIOD - 1)
            else:
                pmt = loan / VEHICLE_AMORTIZATION_PERIOD if VEHICLE_AMORTIZATION_PERIOD > 0 else 0.0

            # Tranche B: Operating Lease (HGB: NO capitalization, lessor owns)
            # Sonderzahlung capitalized as ARAP per HGB § 250; linear amortization
            # over lease term. Monthly lease pmt = capex × money_factor.
            capex_lease = capex_full * lease_frac
            lease_downpayment = capex_lease * lease_downpayment_pct  # paid at month c_start
            lease_monthly_pmt_net = capex_lease * lease_money_factor  # monthly base lease (net of VAT)
            arap_initial = lease_downpayment  # full Sonderzahlung becomes ARAP at inception
            arap_amort_per_mo = arap_initial / lease_term_months if lease_term_months > 0 else 0.0

            # Tranche C: Equity/Cash (capitalize + AfA + FULL cash drain, NO debt)
            capex_equity = capex_full * equity_frac

            # Capitalize loan + equity portions only (lease excluded per HGB)
            capitalized_capex = capex_loan + capex_equity
            afa_per_mo_total = capitalized_capex / VEHICLE_AMORTIZATION_PERIOD if VEHICLE_AMORTIZATION_PERIOD > 0 else 0.0

            cohorts.append({
                "start_month": m + 1,
                "size": mo_val,
                # Tranche-aware capex breakdown
                "capex_total": capex_full,
                "capex_loan": capex_loan,
                "capex_lease": capex_lease,
                "capex_equity": capex_equity,
                # Tranche A (Loan)
                "original_loan": loan,
                "loan_bal": loan,
                "rate": rate,
                "pmt": pmt,
                # Tranche B (Lease) — HGB off-balance, ARAP for Sonderzahlung
                "lease_downpayment": lease_downpayment,
                "lease_monthly_pmt_net": lease_monthly_pmt_net,
                "arap_balance": 0.0,  # initialized to 0; set to arap_initial at c_start
                "arap_initial": arap_initial,
                "arap_amort_per_mo": arap_amort_per_mo,
                "lease_term_months": int(lease_term_months),
                "lease_size": mo_val * lease_frac,  # for fleet count
                # Tranche A+C combined capitalization (drives AfA + BS GFA + salvage)
                "capex_capitalized": capitalized_capex,
                "afa_per_mo": afa_per_mo_total,
                "accum_afa": 0,
                "impaired": False,
                # Mix metadata
                "loan_frac": loan_frac,
                "lease_frac": lease_frac,
                "equity_frac": equity_frac,
                "year": year_of_cohort,
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

    # =========================================================================
    # === B2B Delivery Stream Physics ==============================
    # Tesla Network dispatches Cybercabs for goods delivery during low-passenger
    # demand windows. Same dispatch architecture, separate revenue stream.
    # Engine reads delivery_enabled flag — if False, all delivery params are 0
    # and this entire stream produces no revenue/cost.
    #
    # Daily delivery throughput at FULL ACTIVATION:
    # deliveries/day = delivery_hours × trips/hour × utilization (passenger util applied)
    # Per-year ramp factor scales this down for Y1-Y3 (Tesla product not yet mature).
    # Variable cost: delivery_km/day adds to total_km for energy + wear (asset-driven costs).
    # Cleaning: NO incremental cost (calendar-driven, fleet-driven, not per-trip).
    # Delivery deadhead: assumed same 22% ratio as passenger.
    # Trip distance assumption: average delivery cycle = 4 km billable
    # (shorter than passenger 5km — food/parcel deliveries are typically intra-district).
    # =========================================================================
    avg_delivery_distance_km = 4.0  # blended food/parcel/medical
    delivery_trips_per_day_full = delivery_hours_per_day * delivery_trips_per_hour
    delivery_billable_km_per_day_full = delivery_trips_per_day_full * avg_delivery_distance_km
    delivery_total_km_per_day_full = delivery_billable_km_per_day_full / (1.0 - deadhead_rate) if deadhead_rate < 1.0 else 0.0
    delivery_gbv_per_day_per_car_full = delivery_trips_per_day_full * delivery_rev_per_trip
    delivery_ramp_by_year = {1: delivery_ramp_y1, 2: delivery_ramp_y2, 3: delivery_ramp_y3, 4: delivery_ramp_y4, 5: delivery_ramp_y5}

    pnl_m = {k: [] for k in [P_GBV, P_VAT, P_NET, P_TFEE, P_MNET, P_DGBV, P_DVAT, P_DNET, P_DTFEE, P_DMNET, P_TMNET, P_EN, P_WR, P_CL, P_LSE, P_DB1, P_INS, P_PK, P_API, P_TV, P_SUB, P_DB2, P_HQ, P_IT, P_LEG, P_HINS, P_FEE, P_BNK, P_LPR, P_THG, P_EB, P_EB_HGB, P_AF_V, P_AF_I, P_SAL, P_EBIT, P_I_IN, P_I_EX, P_EBT, P_TX, P_NI]}
    cf_m = {k: [] for k in [C_NI, C_DP, C_GS, C_TP, C_TPD, C_LPR, C_WCT, C_VCOL, C_VPD, C_LSE, C_OP, C_CAP, C_VRF, C_SLE, C_INV, C_EQ, C_CC, C_SH, C_KFW, C_PRN, C_VDR, C_VRP, C_OD, C_FIN, C_NET, C_BEG, C_END]}
    bs_m = {k: [] for k in [B_GF, B_AD, B_NF, B_VR, B_OPVRX, B_TR, B_TRX, B_ARAP, B_CS, B_TC, B_TA, B_ES, B_ER, B_TEQ, B_PT, B_PL, B_TPV, B_DK, B_DV, B_DO, B_PV, B_SL, B_TL, B_TLEQ, B_CH]}

    tax_schedule = {1: 0.23520, 2: 0.22465, 3: 0.21410, 4: 0.20355, 5: 0.19300}

    # State Loops Configuration
    current_cash = 0.0
    vat_loan_bal = 0.0
    overdraft_facility_bal = 0.0
    operational_vat_payable = 0.0
    vat_receivable = 0.0
    thg_receivable = 0.0
    # === THG Quote legal mechanics state variable ===
    # Per § 7 Abs. 1 38. BImSchV: THG-Quote is a flat annual payment per
    # registered vehicle per calendar year, paid in full regardless of how
    # late in the year vehicle was registered, PROVIDED registration is
    # before the November 15 deadline. Sources: ADAC, EnBW, Finanztip,
    # Klima-Quote, elektrovorteil (all confirm). Prior logic
    # ((thg_quote/12) * active_fleet) was incorrect — it pro-rated the flat
    # annual payment, which the law explicitly says doesn't happen.
    # `thg_deferred_next_year` tracks deferred €-amount from Nov/Dec adds.
    # `pending_carryover_cars` tracks the COUNT of cars whose deferral has
    # already been released in next-year January, so the existing-fleet
    # carryover formula doesn't double-count them.
    thg_deferred_next_year = 0.0
    pending_carryover_cars = 0
    tax_provision_bal = 0.0
    legal_provision_bal = 0.0
    
    prior_year_tax_actual = 0.0
    current_year_tax_accrued = 0.0
    prepayments_made_this_year = 0.0
    true_up_due_this_m5 = 0.0
    
    cum_gfa = 0.0
    cum_depr = 0.0
    cum_net_income = 0.0
    # === Tranche C (Equity): cumulative founder capital call tracker ===
    # Increments BS equity share (stammkapital extended) over the simulation.
    cum_capital_call = 0.0
    # === Tranche B (Lease): aggregate ARAP balance across all cohorts ===
    # Computed each month as sum over cohorts; tracked here for BS reporting.
    cum_arap_balance = 0.0

    vat_repay_schedule = [0.0]*120 
    active_fleet_by_month = []
    utilization_by_month = []
    month_col_names = []
    cash_breach_months = []
    # Distinct liquidity-stress signals
    net_liq_breach_months = []   # Cash − Overdraft < min_buffer (going concern stress)
    insolvency_months = []       # Required draw exceeds bank-approved ceiling

    # === use is_dynamic flag instead of hardcoded English string ===
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
        
        # === Save beginning cash BEFORE any mutations.
        # Without this, when the overdraft draws and resets current_cash to 0.0,
        # the CF statement records beg_cash = 0 instead of the actual prior period balance. ===
        beg_cash = current_cash
        
        month_col_names.append(f"{m_names[current_month_index-1]} '{str(current_year_cal)[-2:]}")
        days_in_mo = calendar.monthrange(current_year_cal, current_month_index)[1]
        
        # ============================================================
        # === Seasonality is now a 12-month lookup ===
        # Prior hardcoded 4-tier (Dec-Feb 1.45, Nov/Mar 1.30, Apr/Oct 1.05,
        # May-Sep 1.10) — annual blend 1.2125×.
        # Reads from `seasonality_by_month` dict (1-12 → multiplier)
        # populated from 12 individual sidebar sliders. Defaults preserve # blend exactly. User can stress-test (e.g., dry-cathode 4680 reduces
        # winter penalty 10-15%) by adjusting individual month sliders.
        # Empirical defaults:
        # - Winter (Dec-Feb) 1.45×: ADAC Wintertest 2023, Munich Dec-Feb avg low -3 to -5°C
        # - Shoulder (Nov, Mar) 1.30×: partial battery thermal load
        # - Cool summer (Apr, Oct) 1.05×: minimal HVAC load
        # - Hot summer (May-Sep) 1.10×: A/C draw 8-15% per Geotab fleet data
        # ============================================================
        season_mult = seasonality_by_month.get(current_month_index, 1.0)
            
        active_fleet = 0
        current_veh_afa = 0
        fleet_sale_rev = 0
        int_exp = 0
        prin_pay = 0
        kfw_draw = 0
        capex_this_mo = 0          # capitalized capex (loan + equity) — flows to BS GFA
        capex_sold_this_mo = 0     # capitalized capex retired at month 60 (loan + equity)
        accum_afa_sold_this_mo = 0
        # === Tranche B (Lease) per-month flows ===
        lease_pmt_mo_net = 0.0          # P&L: monthly lease payment net of VAT (cash)
        lease_downpayment_cash_mo = 0.0 # cash paid at lease inception (Sonderzahlung)
        arap_amort_mo = 0.0             # ARAP amortization to P&L (lease expense, non-cash)
        arap_setup_mo = 0.0             # ARAP asset created at lease inception
        # Note: VAT on lease pmts + Sonderzahlung is handled centrally below by
        # adding `lease_pmt_mo_net + lease_downpayment_cash_mo` to vat_eligible_opex_mo.
        # === Tranche C (Equity) per-month flows ===
        equity_capex_cash_mo = 0.0      # full cash drain for equity-financed acquisitions
        # Track cars added THIS month for THG accrual
        cars_added_this_month = 0

        for c in cohorts:
            c_start = c["start_month"]
            c_lease_term = c["lease_term_months"]

            if current_month == c_start:
                # === Tranche A (Loan): draw debt + capitalize loan-portion capex ===
                kfw_draw += c["original_loan"]
                capex_this_mo += c["capex_loan"]
                # === Tranche B (Lease): pay Sonderzahlung in cash, set up ARAP asset ===
                if c["capex_lease"] > 0:
                    lease_downpayment_cash_mo += c["lease_downpayment"]
                    c["arap_balance"] = c["arap_initial"]
                    arap_setup_mo += c["arap_initial"]
                # === Tranche C (Equity): capitalize equity-portion capex (drives BS GFA + AfA) ===
                # Cash drain handled separately below (does NOT enter capex_this_mo for
                # the existing cash-flow logic, which already counts capex via cf_capex)
                capex_this_mo += c["capex_equity"]
                equity_capex_cash_mo += c["capex_equity"]
                # Cars added (any tranche) — drives THG accrual
                cars_added_this_month += c["size"]

            # Active fleet: ALL tranches count toward operational fleet
            # (lease tranche operates same as loan/equity, just different financing).
            if current_month >= c_start and current_month < c_start + VEHICLE_AMORTIZATION_PERIOD:
                active_fleet += c["size"]
                # === Tranche A (Loan): interest expense on outstanding loan balance ===
                int_for_this_loan = c["loan_bal"] * (c["rate"] / 12)
                int_exp += int_for_this_loan

                # === HGB Impairment (loan + equity tranches — capitalized assets only) ===
                if current_month == imp_month and not c["impaired"]:
                    # Base for impairment: outstanding loan if any, otherwise capitalized capex
                    if c["loan_bal"] > 0:
                        extra_afa = c["loan_bal"] * imp_pct_val
                    else:
                        extra_afa = c["capex_capitalized"] * imp_pct_val
                    current_veh_afa += extra_afa
                    c["accum_afa"] += extra_afa
                    c["impaired"] = True

                # === AfA on capitalized capex (loan + equity only — lease NOT capitalized) ===
                current_veh_afa += c["afa_per_mo"]
                c["accum_afa"] += c["afa_per_mo"]

                # === Tranche A (Loan): principal amortization starting month c_start+12 ===
                if current_month >= c_start + 12:
                    prin = c["pmt"] - int_for_this_loan
                    if c["loan_bal"] - prin < 0:
                        prin = c["loan_bal"]
                    prin_pay += prin
                    c["loan_bal"] -= prin

            # === Tranche B (Lease): monthly lease payment + ARAP amortization ===
            # Active during the lease term (typically 60 months from c_start).
            if c["capex_lease"] > 0 and current_month >= c_start and current_month < c_start + c_lease_term:
                lease_pmt_mo_net += c["lease_monthly_pmt_net"]
                # ARAP amortization (Sonderzahlung released proportionally to P&L lease expense)
                if c["arap_balance"] > 0:
                    arap_release = min(c["arap_amort_per_mo"], c["arap_balance"])
                    arap_amort_mo += arap_release
                    c["arap_balance"] -= arap_release

            # === End-of-life month 60: salvage realization (loan + equity tranches only) ===
            # Lease tranche returns to lessor — zero salvage for MRRG.
            if current_month == c_start + VEHICLE_AMORTIZATION_PERIOD:
                # Salvage applies pro-rata to loan + equity vehicles
                non_lease_frac = c["loan_frac"] + c["equity_frac"]
                fleet_sale_rev += c["size"] * non_lease_frac * salvage_value_per_car_y4
                # Retire capitalized capex (loan + equity portions)
                capex_sold_this_mo += c["capex_capitalized"]
                accum_afa_sold_this_mo += c["accum_afa"]
                # Pay off any residual loan balance (loan tranche)
                prin_pay += c["loan_bal"]
                c["loan_bal"] = 0
                c["accum_afa"] = 0

            # === Tranche B (Lease) end-of-term: lessor reclaims vehicles ===
            # Note: lease_term_months may differ from VEHICLE_AMORTIZATION_PERIOD.
            # At end of lease term, ARAP balance should be fully amortized (sanity).
            # No salvage; lessor takes back asset.

        # === use is_dynamic flag for cannibalization branch ===
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
        # Net Revenue Correction: Platform take fee maps off Net instead of Gross
        tesla_fee_mo = net_rev_mo * tesla_take_rate
        mrrg_net_mo = net_rev_mo - tesla_fee_mo
        
        # =====================================================================
        # === B2B Delivery Revenue Computation (monthly) ============
        # Same utilization (current_u) applies — delivery utilization tracks
        # passenger utilization since both are Tesla Network dispatched and
        # share the same demand-density curve.
        # Ramp factor scales activation by year (Tesla product roll-out).
        # =====================================================================
        delivery_ramp_factor = delivery_ramp_by_year.get(current_year, 0.0) if delivery_enabled else 0.0
        # Per-month delivery operations
        delivery_op_days_mo = op_days  # tracks passenger utilization (same dispatch)
        delivery_gbv_mo = delivery_gbv_per_day_per_car_full * delivery_op_days_mo * active_fleet * delivery_ramp_factor
        delivery_net_rev_mo = delivery_gbv_mo / (1.0 + VAT_RATE) if delivery_gbv_mo > 0 else 0.0
        delivery_vat_mo = delivery_gbv_mo - delivery_net_rev_mo
        delivery_tesla_fee_mo = delivery_net_rev_mo * delivery_take_rate
        delivery_mrrg_net_mo = delivery_net_rev_mo - delivery_tesla_fee_mo
        # Delivery total km adds to asset-driven variable cost base (energy + wear)
        delivery_total_km_mo = delivery_total_km_per_day_full * delivery_op_days_mo * active_fleet * delivery_ramp_factor
        
        # Combined variable cost: passenger km + delivery km feed into same energy/wear formulas
        total_km_mo = (actual_total_km_per_day * op_days * active_fleet) + delivery_total_km_mo
        wear_mo = total_km_mo * wear_and_tear_rate
        energy_mo = total_km_mo * (energy_rate * season_mult)
        clean_mo = cleaning_cost_per_day * days_in_mo * active_fleet  # calendar-driven, unchanged
        # DB1 includes BOTH passenger and delivery MRRG net revenue
        total_mrrg_net_mo = mrrg_net_mo + delivery_mrrg_net_mo
        # === Tranche B (Lease): Total lease P&L expense for this month ===
        # Per HGB § 275 Abs. 2 Nr. 5 — Sonstige bezogene Leistungen
        # Composition: monthly cash payment (net of VAT) + ARAP amortization
        # (matching of Sonderzahlung over lease term). Flows into pos3 (Cost
        # of Materials), thus reducing DB1.
        lease_expense_mo = lease_pmt_mo_net + arap_amort_mo
        db1_mo = total_mrrg_net_mo - wear_mo - energy_mo - clean_mo - lease_expense_mo
        
        # === Cargo insurance (Verkehrshaftungsversicherung) ===
        # Only billed when delivery toggle is ON AND delivery is ramped > 0 in current year.
        # Doesn't benefit from FSD safety credit (covers cargo theft, weather, handling).
        # Scales with active fleet × ramp factor — partial-year ramp = partial-month billing.
        cargo_ins_mo = delivery_cargo_insurance_pm * active_fleet * delivery_ramp_factor
        ins_mo = (insurance_pm * active_fleet) + cargo_ins_mo
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
        # === FEATURE A: OpEx Input VAT (Vorsteuerabzug) ====
        # Under German UStG, input VAT on eligible operating expenses
        # is deductible against output VAT. Vendors are paid GROSS;
        # the 19% VAT portion offsets the monthly Umsatzsteuerzahllast.
        #
        # VAT-Eligible OpEx (services charging 19% USt):
        # energy, wear, clean, park, telemetry, TÜV, charging sub,
        # HQ lease, IT/cloud, legal/bookkeeping
        #
        # VAT-Exempt OpEx (per UStG):
        # - Insurance: § 4 Nr. 10 UStG
        # - HQ Insurance: § 4 Nr. 10 UStG
        # - Bank fees: § 4 Nr. 8 UStG
        # - IHK contributions: Mitgliedsbeitrag (no VAT)
        # - GEZ broadcast fee: öffentliche Abgabe (no VAT)
        # ============================================================
        vat_eligible_opex_mo = (energy_mo + wear_mo + clean_mo + park_mo
                                + tel_mo + tuev_mo + sub_mo + hq_lease_mo
                                + it_cloud_mo + legal_mo
                                # === Tranche B (Lease): monthly lease pmts + Sonderzahlung
                                # All VAT-bearing per § 1 Abs. 1 UStG. Note: only the cash
                                # outflows enter the VAT base — ARAP amortization is a
                                # non-cash matching release (the VAT was already paid at
                                # Sonderzahlung inception and is reclaimed in that month).
                                + lease_pmt_mo_net + lease_downpayment_cash_mo)
        opex_input_vat_mo = vat_eligible_opex_mo * VAT_RATE
        # P&L impact: ZERO (P&L always books net of VAT — Feature A invariant)
        # CF impact: -opex_input_vat_mo (vendors paid gross this month)
        # BS impact: operational_vat_payable netted by -opex_input_vat_mo below
        
        # === THG Quote per German legal mechanics ===
        # § 7 Abs. 1 38. BImSchV + 38. BImSchV § 6: per-vehicle annual flat
        # payment, paid in full regardless of registration timing within the
        # calendar year. Deadline for current-year claim: November 15.
        # Sources verified: ADAC (rund-ums-fahrzeug/elektromobilitaet/thg-quote),
        # EnBW (elektromobilitaet/thg-quote), Finanztip (thg-quote),
        # Klima-Quote (klima-quote.de), elektrovorteil.de.
        #
        # Prior implementation (Layers 17-22): (thg_quote/12) * active_fleet
        # was incorrect — it pro-rated the annual flat payment, which the law
        # explicitly says doesn't happen ("nie nur anteilig" — Finanztip,
        # Geld-fuer-eauto.de). Under-booked Y2 example: 9 cars × €280 should
        # yield €2,520 but old code computed €1,913 (€607 under-booking in Y2;
        # ~€9K cumulative 5Y under-booking).
        #
        # Correct model:
        # (a) NEW cars added Jan-Oct → full €280 booked in addition month
        # (b) NEW cars added Nov-Dec → past Nov 15 deadline, defer to next Jan
        # (c) EXISTING fleet (carried from prior calendar year) → full €280
        #     each booked once per year, in January of new calendar year
        # IMPORTANT: deferred Nov/Dec cars released in Jan must be EXCLUDED
        # from the existing-fleet count for that month, or they'd be claimed
        # twice (once as deferred release, once as existing fleet).
        # `pending_carryover_cars` tracks the count of cars whose deferral
        # has been "queued" for next January, so we can exclude them.
        # Cash collection: quarterly settlement preserved (THG
        # providers typically pay within 4-12 weeks of application).
        current_calendar_month = ((current_month - 1) % 12) + 1  # 1=Jan ... 12=Dec
        thg_rev_mo = 0.0
        # (a) New cars added Jan-Oct: book full annual amount NOW
        if current_calendar_month <= 10:
            thg_rev_mo += thg_quote_per_car_py * cars_added_this_month
        else:
            # (b) Nov/Dec additions: defer €-amount AND track car-count for next-Jan exclusion
            thg_deferred_next_year += thg_quote_per_car_py * cars_added_this_month
            pending_carryover_cars += cars_added_this_month
        # (c) January carry-over: existing fleet re-claims annual THG
        #   EXCLUDING (i) cars added this same month and (ii) cars already
        #   "pre-claimed" via the deferred-release pathway from prior Nov/Dec.
        if current_calendar_month == 1:
            existing_fleet_carryover = active_fleet - cars_added_this_month - pending_carryover_cars
            thg_rev_mo += thg_quote_per_car_py * existing_fleet_carryover
            # Release any deferred Nov/Dec registrations from prior year
            thg_rev_mo += thg_deferred_next_year
            thg_deferred_next_year = 0.0
            pending_carryover_cars = 0  # released, reset
        # Receivable + quarterly cash collection (unchanged pattern)
        thg_receivable += thg_rev_mo
        thg_cash_mo = 0.0
        if current_month % 3 == 0:
            thg_cash_mo = thg_receivable
            thg_receivable = 0.0
        thg_wc_delta = thg_cash_mo - thg_rev_mo
        
        # Risk Provisions allocation (§ 249 HGB)
        legal_provision_mo = legal_provision_rate if active_fleet > 0 else 0.0
        legal_provision_bal += legal_provision_mo
        
        # Capital gains stripped cleanly from operational cash line
        ebitda_mo = db2_mo - hq_lease_mo - it_cloud_mo - legal_mo - hq_ins_mo - fees_mo - bank_fees_pm + thg_rev_mo - legal_provision_mo
        ebit_mo = ebitda_mo - total_afa_this_mo + fleet_sale_rev
        
                # Interest income accrues on Beginning-of-Period cash balance.
        # Rationale: previous projected_mid hack used only capex/financing flows,
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
        # Defensive cap — vat_repay cannot exceed outstanding bridge loan.
        # Excess refund still flows through inv_cf_mo as a real cash inflow.
        vat_repay_mo = min(vat_refund_inflow, vat_loan_bal)
        vat_loan_bal -= vat_repay_mo
        vat_int_mo = vat_loan_bal * (vat_bridge_rate / 12.0)
        int_exp += vat_int_mo
        
        if overdraft_facility_bal > 0:
            int_exp += overdraft_facility_bal * (OVERDRAFT_ANNUAL_RATE / 12.0)
            
        ebt_mo = ebit_mo + int_inc_mo - int_exp
        
        # Monthly HGB tax provision accruals (fixed matrix)
        tax_exp_mo = max(0.0, ebt_mo) * tax_schedule[current_year]
        current_year_tax_accrued += tax_exp_mo
        
        tax_paid_mo = 0.0
        if current_month_index == 5:
            tax_paid_mo += true_up_due_this_m5
            true_up_due_this_m5 = 0.0
            
        # Compliance Calendar Loop
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
        
        # Short-Term Overdraft Linkage Mechanics
        # Output VAT now includes BOTH passenger and delivery
        op_vat_collected = vat_owed_mo + delivery_vat_mo
        # === FEATURE A: VAT cash flow ===
        # op_vat_paid = prior month's NETTED payable being remitted to Finanzamt
        # opex_input_vat_mo = vendors paid gross THIS month (separate cash drain)
        # Combine both into op_vat_paid_total for the CF statement.
        op_vat_paid = -operational_vat_payable
        op_vat_paid_total = op_vat_paid - opex_input_vat_mo
        
        # === Tranche B (Lease) cash flow integration ===
        # - lease_pmt_mo_net is in net_inc_mo (P&L expense via DB1) and IS a cash drain → no adjustment
        # - arap_amort_mo is in net_inc_mo (P&L expense) but is NON-cash → add back to op CF
        # - lease_downpayment_cash_mo is a CASH drain in setup month but NOT yet in P&L → subtract
        # Sonderzahlung VAT flows through opex_input_vat_mo (already counted in op_vat_paid_total).
        lease_cf_adjustment = arap_amort_mo - lease_downpayment_cash_mo

        op_cf_mo = net_inc_mo + total_afa_this_mo - fleet_sale_rev + tax_exp_mo - tax_paid_mo + thg_wc_delta + op_vat_collected + op_vat_paid_total + legal_provision_mo + lease_cf_adjustment
        inv_cf_mo = -(capex_this_mo + vat_draw_mo) + vat_refund_inflow + fleet_sale_rev
        # Initialize capital_call_mo to zero; populated downstream if shortfall
        # exceeds overdraft headroom AND equity tranche capex hit this month.
        capital_call_mo = 0.0
        fin_cf_mo_excl_od = (stammkapital if current_month == 1 else 0.0) + (shareholder_loan if current_month == 1 else 0.0) + kfw_draw - prin_pay + vat_draw_mo - vat_repay_mo

        net_before_overdraft = op_cf_mo + inv_cf_mo + fin_cf_mo_excl_od
        tentative_ending_cash = current_cash + net_before_overdraft
        
        # =====================================================================
        # === Capped Overdraft + Insolvency Detection ========
        # Overdraft draws are now capped at max_overdraft_limit (bank Linie).
        # If shortfall exceeds available headroom → INSOLVENCY flagged but
        # overdraft is still drawn to the cap (engine continues for visibility).
        # === Tranche C (Equity) — Hybrid capital call mechanism ===
        # If equity-financed acquisition occurred this month AND
        # shortfall would breach max overdraft → inject founder capital ONLY
        # for the breach amount (most realistic founder behavior: tap overdraft
        # first, capital call as last resort to avoid Insolvenzantragspflicht).
        # =====================================================================
        overdraft_net_flow = 0.0
        if tentative_ending_cash < 0:
            needed_from_od = -tentative_ending_cash
            available_od_headroom = max(0.0, max_overdraft_limit - overdraft_facility_bal)
            actual_od_draw = min(needed_from_od, available_od_headroom)
            unfunded_shortfall = needed_from_od - actual_od_draw
            if unfunded_shortfall > 0:
                # Shortfall exceeds approved line. Tranche C policy:
                # if capital call enabled AND any equity capex this month, inject
                # the unfunded shortfall as founder equity (Stammkapital erhöht).
                if equity_capital_call_enabled and equity_capex_cash_mo > 0:
                    capital_call_mo = unfunded_shortfall
                    # Capital call absorbs the unfunded portion; no insolvency flag
                else:
                    # No equity tranche this month OR capital call disabled → insolvency
                    insolvency_months.append(month_col_names[-1])
            overdraft_net_flow = actual_od_draw
            overdraft_facility_bal += actual_od_draw
            current_cash = tentative_ending_cash + actual_od_draw + capital_call_mo
        else:
            if overdraft_facility_bal > 0:
                repay_amt = min(tentative_ending_cash, overdraft_facility_bal)
                overdraft_net_flow = -repay_amt
                overdraft_facility_bal -= repay_amt
                current_cash = tentative_ending_cash - repay_amt
            else:
                current_cash = tentative_ending_cash

        # Fold capital call into financing CF (after it's been determined above).
        # This keeps the CF statement clean: capital call shows as a separate
        # financing inflow on the C_CC line, and net_before_overdraft already
        # excludes it (so cash reconciles correctly through the overdraft branch).
        fin_cf_mo_excl_od = fin_cf_mo_excl_od + capital_call_mo
                
        # Dual-track liquidity-stress signals
        # (a) Raw cash floor: traditional "do we have €X on hand?"
        if current_cash < min_cash_buffer and active_fleet > 0:
            cash_breach_months.append(month_col_names[-1])
        # (b) Net liquidity (cash − overdraft): "are we net positive after debt?"
        #   This is what bank credit committee computes — Effektive Liquidität.
        effective_cash = current_cash - overdraft_facility_bal
        if effective_cash < min_cash_buffer and active_fleet > 0:
            net_liq_breach_months.append(month_col_names[-1])

        # === Define eq_in and sh_in BEFORE the CF appends section ===
        eq_in = stammkapital if current_month == 1 else 0.0
        sh_in = shareholder_loan if current_month == 1 else 0.0

        # Commit State Adjustments to Objects
        cum_gfa += capex_this_mo - capex_sold_this_mo
        cum_depr += total_afa_this_mo - accum_afa_sold_this_mo 
        nfa = cum_gfa - cum_depr
        vat_receivable += vat_draw_mo - vat_refund_inflow
        # === FEATURE A: NET VAT Payable ===
        # operational_vat_payable = Output VAT − OpEx Input VAT (Vorsteuer offset)
        # The cash drain to vendors (-opex_input_vat_mo above) exactly offsets
        # this -opex_input_vat_mo reduction in the payable. BS stays balanced.
        # Note: this is the INTERNAL signed state — may be negative when input VAT
        # exceeds output VAT. Gross BS presentation handled below.
        operational_vat_payable = op_vat_collected - opex_input_vat_mo
        tax_provision_bal += tax_exp_mo - tax_paid_mo
        cum_net_income += net_inc_mo
        # === Tranche C (Equity): accumulate founder capital calls ===
        cum_capital_call += capital_call_mo
        # === Tranche B (Lease): aggregate ARAP balance across all active cohorts ===
        # Each cohort tracks its own arap_balance; sum gives total prepaid lease asset.
        cum_arap_balance = sum(c["arap_balance"] for c in cohorts)

        kfw_loan_bal = sum(c["loan_bal"] for c in cohorts if current_month >= c["start_month"])

        # =====================================================================
        # === Gross BS presentation for operational VAT position ===
        # Internal state `operational_vat_payable` carries the signed net
        # (can be negative when Vorsteuerüberhang exists). For BS reporting,
        # § 246 III HGB Bruttoprinzip requires gross presentation: split into
        # a payable (liability, ≥ 0) and a receivable (asset, ≥ 0).
        # === Same pattern for tax_provision_bal — when prepayments
        # exceed accrual (e.g., declining-profit year), a Steuerforderung exists.
        # =====================================================================
        op_vat_payable_bs = max(0.0, operational_vat_payable)       # liability
        op_vat_receivable_bs = max(0.0, -operational_vat_payable)   # asset
        tax_provision_bs = max(0.0, tax_provision_bal)              # liability
        tax_receivable_bs = max(0.0, -tax_provision_bal)            # asset

        # === Tranche B (Lease) BS: ARAP asset (Aktiver Rechnungsabgrenzungsposten) ===
        # HGB § 250 Abs. 1: Sonderzahlung capitalized as prepaid expense.
        # === Tranche C (Equity) BS: Stammkapital + cumulative capital calls ===
        # Founder capital injections during the simulation horizon add to equity share.
        total_equity_share_bs = stammkapital + cum_capital_call

        total_assets = nfa + vat_receivable + op_vat_receivable_bs + thg_receivable + tax_receivable_bs + cum_arap_balance + current_cash
        total_equity = total_equity_share_bs + cum_net_income
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
        # === B2B Delivery revenue stream P&L appends ===
        pnl_m[P_DGBV].append(delivery_gbv_mo)
        pnl_m[P_DVAT].append(-delivery_vat_mo)
        pnl_m[P_DNET].append(delivery_net_rev_mo)
        pnl_m[P_DTFEE].append(-delivery_tesla_fee_mo)
        pnl_m[P_DMNET].append(delivery_mrrg_net_mo)
        pnl_m[P_TMNET].append(mrrg_net_mo + delivery_mrrg_net_mo)
        pnl_m[P_EN].append(-energy_mo)
        pnl_m[P_WR].append(-wear_mo)
        pnl_m[P_CL].append(-clean_mo)
        # === Tranche B (Lease): monthly P&L lease expense ===
        # HGB § 275 Abs. 2 Nr. 5 (Sonstige bezogene Leistungen, Cost of Materials pos3)
        # Composition: lease_pmt_mo_net (cash) + arap_amort_mo (ARAP release, non-cash)
        pnl_m[P_LSE].append(-lease_expense_mo)
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
        # HGB-view EBITDA = Mgmt EBITDA + Anlagenabgang (per § 275 II Nr.4 HGB)
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
        # === Tranche B (Lease) CF line ===
        # Reports the lease-related cash flow adjustment: ARAP non-cash add-back
        # MINUS lease Sonderzahlung cash drain in setup month. Together with the
        # P&L lease_expense_mo (already in net_inc_mo above), this fully reconciles
        # P&L vs cash for the lease tranche.
        cf_m[C_LSE].append(lease_cf_adjustment)
        cf_m[C_OP].append(op_cf_mo)
        cf_m[C_CAP].append(-(capex_this_mo + vat_draw_mo))
        cf_m[C_VRF].append(vat_refund_inflow)
        cf_m[C_SLE].append(fleet_sale_rev)
        cf_m[C_INV].append(inv_cf_mo)
        cf_m[C_EQ].append(eq_in)
        # === Tranche C (Equity) CF line: founder capital call this month ===
        cf_m[C_CC].append(capital_call_mo)
        cf_m[C_SH].append(sh_in)
        cf_m[C_KFW].append(kfw_draw)
        cf_m[C_PRN].append(-prin_pay)
        cf_m[C_VDR].append(vat_draw_mo)
        cf_m[C_VRP].append(-vat_repay_mo)
        cf_m[C_OD].append(overdraft_net_flow)
        cf_m[C_FIN].append(fin_cf_mo_excl_od + overdraft_net_flow)
        cf_m[C_NET].append(net_before_overdraft + overdraft_net_flow)
        # === Use beg_cash saved at top of loop ===
        cf_m[C_BEG].append(beg_cash)
        cf_m[C_END].append(current_cash)

        bs_m[B_GF].append(cum_gfa)
        bs_m[B_AD].append(-cum_depr)
        bs_m[B_NF].append(nfa)
        bs_m[B_VR].append(vat_receivable)
        bs_m[B_OPVRX].append(op_vat_receivable_bs)          # gross asset side
        bs_m[B_TR].append(thg_receivable)
        bs_m[B_TRX].append(tax_receivable_bs)               # gross asset side
        # === Tranche B (Lease) BS: ARAP asset (Aktiver Rechnungsabgrenzungsposten) ===
        bs_m[B_ARAP].append(cum_arap_balance)
        bs_m[B_CS].append(current_cash)
        # Total Current Assets now includes ARAP
        bs_m[B_TC].append(vat_receivable + op_vat_receivable_bs + thg_receivable + tax_receivable_bs + cum_arap_balance + current_cash)
        bs_m[B_TA].append(total_assets)
        # === Tranche C (Equity) BS: Stammkapital + cumulative capital calls ===
        bs_m[B_ES].append(total_equity_share_bs)
        bs_m[B_ER].append(cum_net_income)
        bs_m[B_TEQ].append(total_equity)
        bs_m[B_PT].append(tax_provision_bs)                 # gross liability side (≥ 0)
        bs_m[B_PL].append(legal_provision_bal)
        bs_m[B_TPV].append(total_prov)
        bs_m[B_DK].append(kfw_loan_bal)
        bs_m[B_DV].append(vat_loan_bal)
        bs_m[B_DO].append(overdraft_facility_bal)
        bs_m[B_PV].append(op_vat_payable_bs)                # gross liability side (≥ 0)
        bs_m[B_SL].append(shareholder_loan)
        bs_m[B_TL].append(total_liab_bal)
        bs_m[B_TLEQ].append(total_liab_eq)
        bs_m[B_CH].append(bs_check_val)

    return pnl_m, cf_m, bs_m, month_col_names, cash_breach_months, net_liq_breach_months, insolvency_months, active_fleet_by_month, utilization_by_month, total_capex_per_car, bs_keys_internal

# --- EXECUTING COMPUTER MATRIX WITH SAFELY WRAPPED ISOLATION LOGIC ---
# === is_dynamic passed as positional arg before lang_choice ===
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
    thg_quote_per_car_py, salvage_value_per_car_y4, max_overdraft_limit,
    delivery_enabled, delivery_hours_per_day, delivery_rev_per_trip,
    delivery_trips_per_hour, delivery_take_rate,
    delivery_ramp_y1, delivery_ramp_y2, delivery_ramp_y3, delivery_ramp_y4, delivery_ramp_y5,
    delivery_cargo_insurance_pm, seasonality_by_month,
    is_dynamic, lang_choice,
    fin_mix_by_year, lease_money_factor, lease_downpayment_pct, lease_term_months,
    equity_capital_call_enabled
)

# ============================================================
# === Day-1 Sources/Uses Display
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
day_1_loan = _y1_count * total_capex_per_car * vehicle_ltv  # uses returned scalar
# actual end-of-Month-1 cash from engine, not sources-uses snapshot
day_1_cash_ui = bs_monthly["bs_cash"][0]

# --- POST-LOOP SYSTEM AGGREGATIONS ---
def agg_to_yearly(monthly_dict):
    yearly_dict = {}
    for key, arr in monthly_dict.items():
        yearly_arr = []
        for y in range(5):
            chunk = arr[y*12 : (y+1)*12]
            # Structural set definitions completely clean aggregation pathways
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

# --- STATUTORY GERMAN GUV ACCORDIONS (§ 275 HGB Gesamtkostenverfahren) ---
# === (post TM removal): Geschäftsführer also holds Verkehrsleiter
# mandate (no separate fee). Personalaufwand = 0. No TM strip-out needed
# in pos6, since pnl_fees no longer contains a TM component.
# === pnl_tesla_fee (bezogene Leistung — Tesla dispatch platform)
# now flows into pos3 Materialaufwand; pnl_legal_prov (Zuführung Rückstellung
# § 249 HGB) now flows into pos6. Both were previously missing from HGB sum.
# === B2B delivery revenue is operating revenue from the same Tesla
# Network platform — both streams book together into pos1 Umsatzerlöse per § 275 HGB
# (same operating activity, two consumer/B2B service types). Delivery Tesla
# platform fee flows into pos3 (bezogene Leistungen) alongside passenger fee.
hgb_structure = {}
# pos1 Umsatzerlöse: passenger Net Revenue + delivery Net Revenue (both operating activity)
hgb_structure[loc["hgb_pos1"]] = (df_pnl_combined.loc[loc["pnl_net_rev"]] + df_pnl_combined.loc[loc["pnl_delivery_net_rev"]]).values
hgb_structure[loc["hgb_pos2"]] = (df_pnl_combined.loc[loc["pnl_thg"]] + df_pnl_combined.loc[loc["pnl_salvage"]]).values
# Materialaufwand: Aufwendungen für Roh-/Hilfsstoffe UND für bezogene Leistungen (Tesla platform — passenger AND delivery)
hgb_structure[loc["hgb_pos3"]] = (df_pnl_combined.loc[loc["pnl_energy"]] + df_pnl_combined.loc[loc["pnl_wear"]] + df_pnl_combined.loc[loc["pnl_clean"]] + df_pnl_combined.loc[loc["pnl_lease"]] + df_pnl_combined.loc[loc["pnl_ins"]] + df_pnl_combined.loc[loc["pnl_park"]] + df_pnl_combined.loc[loc["pnl_api"]] + df_pnl_combined.loc[loc["pnl_tuev"]] + df_pnl_combined.loc[loc["pnl_sub"]] + df_pnl_combined.loc[loc["pnl_tesla_fee"]] + df_pnl_combined.loc[loc["pnl_delivery_tesla_fee"]]).values
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

# rev_top = TOTAL Net Revenue (passenger + delivery) for KPI denominators
rev_top = df_pnl_combined.loc[loc["pnl_net_rev"]] + df_pnl_combined.loc[loc["pnl_delivery_net_rev"]]
ebitda = df_pnl_combined.loc[loc["pnl_ebitda"]]
db2 = df_pnl_combined.loc[loc["pnl_db2"]]
ta = df_bs_combined.loc[loc["bs_ta"]]
teq = df_bs_combined.loc[loc["bs_teq"]]
cash = df_bs_combined.loc[loc["bs_cash"]]
nfa = df_bs_combined.loc[loc["bs_nfa"]]

# Operational pass-through accounts purged from debt metrics evaluation
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
# Stacked liquidity-stress warnings
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

tabs = st.tabs([loc["tab_pnl"], loc["tab_hgb_pnl"], loc["tab_cf"], loc["tab_bs"], loc["tab_kpi"], loc["tab_charts"], loc["tab_mc"], loc["tab_readme"]])

def style_pnl_rows(row):
    if loc["pnl_mrrg_net"] in row.name: return ['font-weight: 600; color: #4DA8DA;'] * len(row)
    if loc["pnl_delivery_mrrg_net"] in row.name: return ['font-weight: 600; color: #B0E0E6;'] * len(row)
    if loc["pnl_total_mrrg_net"] in row.name: return ['font-weight: 700; color: #4DA8DA; border-top: 1px solid #4DA8DA;'] * len(row)
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

# ==========================================================================
# === EXPANDED MONTE CARLO — 22+ PARAMETERS ACROSS 3 TIERS =======
# ==========================================================================
# Major upgrade from (12 parameters):
# • Tier 1 (High Variance): adds active_hours, speed, dwell, init_util,
#   rec_rate, can_fac, delivery_ramp_y2, delivery_ramp_y4 (now full
#   delivery roll-out uncertainty Y2+Y3+Y4)
# • Tier 2 (Material Variance): adds cybercab_base_usd, usd_eur_rate,
#   vehicle_ltv, y1_loan_rate, y2_loan_rate (capex/debt structure variance)
# • Tier 3 (Smaller Variance): adds cleaning_cost_per_day, parking_pm,
#   customs_duty_rate (operating cost variance)
# • NEW: 5-Year Cumulative Free Cash Flow tracked alongside NI/EBITDA
# • NEW: simulation_settings metadata snapshot captured before loop
# • NEW: Interactive metric dropdown (FCF/EBITDA/Net Income) dynamically
#   reshapes Chart 1 + tornado target
# • Outputs persisted as nested {simulation_settings, simulation_outputs}
#   for data provenance and reproducibility audit trails
# The deterministic engine logic itself remains fully unchanged.
# ==========================================================================
with tabs[6]:
    st.markdown(f"### {loc['mc_header']}")
    st.caption(loc["mc_intro"])

    # --- Configuration row ---
    mc_col1, mc_col2 = st.columns([1, 2])
    with mc_col1:
        n_iterations = st.number_input(
            loc["mc_n_iterations"], min_value=500, max_value=10000,
            value=5000, step=500, help=loc["mc_n_help"]
        )
    with mc_col2:
        st.write("")
        st.write("")
        run_mc = st.button(loc["mc_run_button"], type="primary", use_container_width=True)

    # --- Distribution overrides matrix (collapsible, 3 tiers) ---
    with st.expander(loc["mc_section_dist"], expanded=False):
        # ===== TIER 1: HIGH VARIANCE DRIVERS (operating physics) =====
        st.markdown(f"**{loc['mc_tier1_header']}**")
        t1c1, t1c2, t1c3 = st.columns(3)
        with t1c1:
            mc_sigma_active_hours = st.number_input(loc["mc_p_active_hours"], value=1.2, min_value=0.1, max_value=4.0, step=0.1, format="%.1f")
            mc_sigma_speed = st.number_input(loc["mc_p_speed"], value=2.0, min_value=0.5, max_value=8.0, step=0.5, format="%.1f")
            mc_sigma_dwell = st.number_input(loc["mc_p_dwell"], value=0.7, min_value=0.1, max_value=2.5, step=0.1, format="%.1f")
            mc_sigma_dh = st.number_input(loc["mc_p_deadhead"], value=0.025, min_value=0.005, max_value=0.10, step=0.005, format="%.3f")
            mc_sigma_trip = st.number_input(loc["mc_p_trip_dist"], value=0.5, min_value=0.1, max_value=2.0, step=0.1, format="%.1f")
        with t1c2:
            mc_target_util_min = st.number_input("Target Util Min", value=0.65, min_value=0.40, max_value=0.95, step=0.01, format="%.2f")
            mc_target_util_max = st.number_input("Target Util Max", value=0.82, min_value=0.50, max_value=0.99, step=0.01, format="%.2f")
            mc_sigma_init_util = st.number_input(loc["mc_p_init_util"], value=0.05, min_value=0.01, max_value=0.20, step=0.01, format="%.2f")
            mc_sigma_rec_rate = st.number_input(loc["mc_p_rec_rate"], value=0.01, min_value=0.001, max_value=0.05, step=0.001, format="%.3f")
            mc_sigma_can_fac = st.number_input(loc["mc_p_can_fac"], value=0.08, min_value=0.01, max_value=0.25, step=0.01, format="%.2f")
        with t1c3:
            mc_sigma_price = st.number_input(loc["mc_p_price"], value=0.10, min_value=0.01, max_value=0.50, step=0.01, format="%.2f")
            mc_take_min = st.number_input("Tesla Take Min", value=0.25, min_value=0.10, max_value=0.50, step=0.01, format="%.2f")
            mc_take_mode = st.number_input("Tesla Take Mode", value=0.25, min_value=0.10, max_value=0.50, step=0.01, format="%.2f")
            mc_take_max = st.number_input("Tesla Take Max", value=0.30, min_value=0.10, max_value=0.50, step=0.01, format="%.2f")

        st.markdown("**Delivery Ramp Uncertainty (Triangular Y2/Y3/Y4)**")
        d_c1, d_c2, d_c3 = st.columns(3)
        with d_c1:
            mc_dy2_min = st.number_input("Delivery Y2 Min", value=0.00, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy2_mode = st.number_input("Delivery Y2 Mode", value=0.00, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy2_max = st.number_input("Delivery Y2 Max", value=0.30, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
        with d_c2:
            mc_dy3_min = st.number_input("Delivery Y3 Min", value=0.00, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy3_mode = st.number_input("Delivery Y3 Mode", value=0.30, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy3_max = st.number_input("Delivery Y3 Max", value=0.60, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
        with d_c3:
            mc_dy4_min = st.number_input("Delivery Y4 Min", value=0.30, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy4_mode = st.number_input("Delivery Y4 Mode", value=0.70, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy4_max = st.number_input("Delivery Y4 Max", value=1.00, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")

        # ===== TIER 2: MATERIAL VARIANCE (capex, debt, costs) =====
        st.markdown(f"**{loc['mc_tier2_header']}**")
        t2c1, t2c2, t2c3 = st.columns(3)
        with t2c1:
            mc_sigma_capex = st.number_input(loc["mc_p_capex"], value=2500.0, min_value=500.0, max_value=10000.0, step=500.0)
            mc_sigma_fx = st.number_input(loc["mc_p_fx"], value=0.05, min_value=0.01, max_value=0.20, step=0.01, format="%.2f")
            mc_sigma_ltv = st.number_input(loc["mc_p_ltv"], value=0.05, min_value=0.01, max_value=0.20, step=0.01, format="%.2f")
        with t2c2:
            mc_loan_y1_min = st.number_input("Y1 Loan Min", value=0.035, min_value=0.01, max_value=0.20, step=0.005, format="%.3f")
            mc_loan_y1_mode = st.number_input("Y1 Loan Mode", value=0.045, min_value=0.01, max_value=0.20, step=0.005, format="%.3f")
            mc_loan_y1_max = st.number_input("Y1 Loan Max", value=0.075, min_value=0.01, max_value=0.20, step=0.005, format="%.3f")
        with t2c3:
            mc_loan_y2_min = st.number_input("Y2 Loan Min", value=0.045, min_value=0.01, max_value=0.20, step=0.005, format="%.3f")
            mc_loan_y2_mode = st.number_input("Y2 Loan Mode", value=0.055, min_value=0.01, max_value=0.20, step=0.005, format="%.3f")
            mc_loan_y2_max = st.number_input("Y2 Loan Max", value=0.085, min_value=0.01, max_value=0.20, step=0.005, format="%.3f")

        t2d1, t2d2, t2d3 = st.columns(3)
        with t2d1:
            mc_ins_min = st.number_input("Insurance Min €/mo", value=140.0, min_value=50.0, max_value=500.0, step=10.0)
            mc_ins_mode = st.number_input("Insurance Mode €/mo", value=180.0, min_value=50.0, max_value=500.0, step=10.0)
            mc_ins_max = st.number_input("Insurance Max €/mo", value=280.0, min_value=50.0, max_value=600.0, step=10.0)
        with t2d2:
            mc_sigma_energy_eur = st.number_input(loc["mc_p_energy_eur"], value=0.040, min_value=0.001, max_value=0.20, step=0.005, format="%.3f")
            mc_sigma_kwh = st.number_input(loc["mc_p_kwh_per_km"], value=0.012, min_value=0.001, max_value=0.05, step=0.001, format="%.3f")

        # ===== TIER 3: SMALLER VARIANCE (operating costs) =====
        st.markdown(f"**{loc['mc_tier3_header']}**")
        t3c1, t3c2, t3c3 = st.columns(3)
        with t3c1:
            mc_sigma_cleaning = st.number_input(loc["mc_p_cleaning"], value=0.50, min_value=0.05, max_value=3.0, step=0.05, format="%.2f")
            mc_sigma_wear = st.number_input(loc["mc_p_wear"], value=0.012, min_value=0.001, max_value=0.05, step=0.001, format="%.3f")
        with t3c2:
            mc_sigma_parking = st.number_input(loc["mc_p_parking"], value=25.0, min_value=5.0, max_value=100.0, step=5.0, format="%.1f")
            mc_sigma_customs = st.number_input(loc["mc_p_customs"], value=0.025, min_value=0.005, max_value=0.10, step=0.005, format="%.3f")
        with t3c3:
            mc_sigma_salvage = st.number_input(loc["mc_p_salvage"], value=2500.0, min_value=500.0, max_value=10000.0, step=500.0)

    # =========================================================================
    # === PHASE A: DAY ARCHETYPE MIX UI (intraday demand topology) ===========
    # =========================================================================
    # Each day in the operating year is assigned to an archetype with its own
    # demand intensity multiplier. The annual mix determines the realized
    # seasonality multiplier for each calendar month, with stochastic variance
    # in both the COUNT (days per year) and the INTENSITY (multiplier) of each
    # archetype. This captures the "good day vs bad day" lottery that drives
    # cash flow variance beyond simple monthly averages.
    # =========================================================================
    with st.expander(loc["mc_dayarch_header"], expanded=False):
        st.caption(loc["mc_dayarch_help"])
        da_c1, da_c2, da_c3 = st.columns(3)
        with da_c1:
            st.markdown("**Days/Year (Frequency)**")
            arch_weekday_days = st.number_input(loc["mc_dayarch_weekday"] + " days/yr",
                value=155, min_value=100, max_value=260, step=5)
            arch_weekend_days = st.number_input(loc["mc_dayarch_weekend"] + " days/yr",
                value=80, min_value=40, max_value=110, step=5)
            arch_friday_days = st.number_input(loc["mc_dayarch_friday"] + " days/yr",
                value=40, min_value=20, max_value=80, step=5)
            arch_holiday_days = st.number_input(loc["mc_dayarch_holiday"] + " days/yr",
                value=30, min_value=10, max_value=80, step=5)
            arch_oktober_days = st.number_input(loc["mc_dayarch_oktoberfest"] + " days/yr",
                value=16, min_value=0, max_value=20, step=1)
            arch_xmas_days = st.number_input(loc["mc_dayarch_xmas"] + " days/yr",
                value=28, min_value=0, max_value=40, step=2)
        with da_c2:
            st.markdown("**Demand Multiplier (mean)**")
            arch_weekday_mult = st.number_input(loc["mc_dayarch_weekday"] + " ×",
                value=1.00, min_value=0.50, max_value=2.00, step=0.05, format="%.2f")
            arch_weekend_mult = st.number_input(loc["mc_dayarch_weekend"] + " ×",
                value=0.90, min_value=0.50, max_value=2.00, step=0.05, format="%.2f")
            arch_friday_mult = st.number_input(loc["mc_dayarch_friday"] + " ×",
                value=1.25, min_value=0.50, max_value=2.50, step=0.05, format="%.2f")
            arch_holiday_mult = st.number_input(loc["mc_dayarch_holiday"] + " ×",
                value=0.70, min_value=0.30, max_value=1.50, step=0.05, format="%.2f")
            arch_oktober_mult = st.number_input(loc["mc_dayarch_oktoberfest"] + " ×",
                value=1.60, min_value=1.00, max_value=2.50, step=0.05, format="%.2f")
            arch_xmas_mult = st.number_input(loc["mc_dayarch_xmas"] + " ×",
                value=1.35, min_value=0.80, max_value=2.00, step=0.05, format="%.2f")
        with da_c3:
            st.markdown("**Demand Multiplier σ (variance)**")
            arch_weekday_sigma = st.number_input(loc["mc_dayarch_weekday"] + " σ",
                value=0.05, min_value=0.01, max_value=0.30, step=0.01, format="%.2f")
            arch_weekend_sigma = st.number_input(loc["mc_dayarch_weekend"] + " σ",
                value=0.08, min_value=0.01, max_value=0.30, step=0.01, format="%.2f")
            arch_friday_sigma = st.number_input(loc["mc_dayarch_friday"] + " σ",
                value=0.10, min_value=0.01, max_value=0.30, step=0.01, format="%.2f")
            arch_holiday_sigma = st.number_input(loc["mc_dayarch_holiday"] + " σ",
                value=0.12, min_value=0.01, max_value=0.40, step=0.01, format="%.2f")
            arch_oktober_sigma = st.number_input(loc["mc_dayarch_oktoberfest"] + " σ",
                value=0.20, min_value=0.05, max_value=0.50, step=0.05, format="%.2f")
            arch_xmas_sigma = st.number_input(loc["mc_dayarch_xmas"] + " σ",
                value=0.15, min_value=0.05, max_value=0.40, step=0.05, format="%.2f")
        # Calendar-month assignment policy (which months get which archetypes)
        # is hard-coded in the sampler. Defaults: Oktoberfest concentrates in Sep-Oct,
        # Christmas in Nov-Dec, holidays spread across school break periods.

    # =========================================================================
    # === PHASE B: STOCHASTIC SHOCK EVENTS UI =================================
    # =========================================================================
    # Independent stochastic events that perturb individual operating days.
    # Each event has annual frequency (Poisson-ish) and a demand impact
    # multiplier. Shocks layer ON TOP of the day-archetype base demand,
    # capturing asymmetric upside (transit strike → demand surge) and downside
    # (tech outage → lost revenue) risks that banks specifically care about.
    # =========================================================================
    with st.expander(loc["mc_shock_header"], expanded=False):
        st.caption(loc["mc_shock_help"])
        sh_c1, sh_c2, sh_c3 = st.columns(3)
        with sh_c1:
            st.markdown("**Annual Frequency (days)**")
            shock_weather_freq = st.number_input(loc["mc_shock_severe_weather"] + " days/yr",
                value=12, min_value=0, max_value=40, step=1)
            shock_strike_freq = st.number_input(loc["mc_shock_transit_strike"] + " days/yr",
                value=2, min_value=0, max_value=15, step=1)
            shock_event_freq = st.number_input(loc["mc_shock_major_event"] + " days/yr",
                value=15, min_value=0, max_value=50, step=1)
            shock_tech_freq = st.number_input(loc["mc_shock_tech_outage"] + " days/yr",
                value=3, min_value=0, max_value=20, step=1)
            shock_heat_freq = st.number_input(loc["mc_shock_heatwave"] + " days/yr",
                value=10, min_value=0, max_value=30, step=1)
            shock_ice_freq = st.number_input(loc["mc_shock_black_ice"] + " days/yr",
                value=5, min_value=0, max_value=20, step=1)
            shock_road_freq = st.number_input(loc["mc_shock_road_closure"] + " days/yr",
                value=7, min_value=0, max_value=30, step=1)
        with sh_c2:
            st.markdown("**Demand Multiplier (mean)**")
            shock_weather_mult = st.number_input(loc["mc_shock_severe_weather"] + " ×",
                value=1.20, min_value=0.50, max_value=2.50, step=0.05, format="%.2f")
            shock_strike_mult = st.number_input(loc["mc_shock_transit_strike"] + " ×",
                value=1.50, min_value=0.50, max_value=2.50, step=0.05, format="%.2f")
            shock_event_mult = st.number_input(loc["mc_shock_major_event"] + " ×",
                value=1.30, min_value=0.50, max_value=2.50, step=0.05, format="%.2f")
            shock_tech_mult = st.number_input(loc["mc_shock_tech_outage"] + " ×",
                value=0.50, min_value=0.00, max_value=1.00, step=0.05, format="%.2f")
            shock_heat_mult = st.number_input(loc["mc_shock_heatwave"] + " ×",
                value=1.05, min_value=0.50, max_value=2.00, step=0.05, format="%.2f")
            shock_ice_mult = st.number_input(loc["mc_shock_black_ice"] + " ×",
                value=1.10, min_value=0.50, max_value=2.00, step=0.05, format="%.2f")
            shock_road_mult = st.number_input(loc["mc_shock_road_closure"] + " ×",
                value=0.85, min_value=0.30, max_value=1.50, step=0.05, format="%.2f")
        with sh_c3:
            st.markdown("**Multiplier σ (variance)**")
            shock_weather_sigma = st.number_input(loc["mc_shock_severe_weather"] + " σ",
                value=0.15, min_value=0.01, max_value=0.50, step=0.05, format="%.2f")
            shock_strike_sigma = st.number_input(loc["mc_shock_transit_strike"] + " σ",
                value=0.20, min_value=0.05, max_value=0.50, step=0.05, format="%.2f")
            shock_event_sigma = st.number_input(loc["mc_shock_major_event"] + " σ",
                value=0.15, min_value=0.05, max_value=0.50, step=0.05, format="%.2f")
            shock_tech_sigma = st.number_input(loc["mc_shock_tech_outage"] + " σ",
                value=0.20, min_value=0.01, max_value=0.50, step=0.05, format="%.2f")
            shock_heat_sigma = st.number_input(loc["mc_shock_heatwave"] + " σ",
                value=0.10, min_value=0.01, max_value=0.30, step=0.05, format="%.2f")
            shock_ice_sigma = st.number_input(loc["mc_shock_black_ice"] + " σ",
                value=0.12, min_value=0.01, max_value=0.30, step=0.05, format="%.2f")
            shock_road_sigma = st.number_input(loc["mc_shock_road_closure"] + " σ",
                value=0.10, min_value=0.01, max_value=0.30, step=0.05, format="%.2f")

    # --- Execute Monte Carlo if button pressed ---
    if run_mc:
        # ---- Statistical sampling helpers ----
        def _sample_beta_scaled(rng, mean, a, b, concentration=10.0):
            """Beta distribution with method-of-moments mean, linearly scaled to [a, b]."""
            mean_unit = (mean - a) / (b - a) if (b - a) > 0 else 0.5
            mean_unit = max(0.01, min(0.99, mean_unit))
            alpha = mean_unit * concentration
            beta_param = (1 - mean_unit) * concentration
            return a + rng.beta(alpha, beta_param) * (b - a)

        def _sample_triangular(rng, low, mode, high):
            if low > high: low, high = high, low
            mode = max(low, min(high, mode))
            return rng.triangular(low, mode, high)

        # ====================================================================
        # PHASE A+B HELPER: monthly demand modifier from day-archetype mix +
        # shock event sampling. Returns 12-month vector (Jan-Dec) of composite
        # demand multipliers that mutate the base seasonality_by_month dict.
        # ====================================================================
        # Calendar policy: which months get which archetype "share" of days.
        # Months × archetypes — fraction of days in that month that fall into
        # each archetype before shock events. Rows sum to 1.0 per month.
        # Defaults reflect Munich calendar (Oktoberfest Sep/Oct, Xmas Nov/Dec).
        month_arch_policy = {
            #       weekday  weekend  friday   holiday  oktober  xmas
            1:  [0.55,    0.27,    0.14,    0.04,    0.00,    0.00],  # Jan (post-NYE)
            2:  [0.55,    0.27,    0.14,    0.04,    0.00,    0.00],  # Feb (Karneval week)
            3:  [0.60,    0.27,    0.13,    0.00,    0.00,    0.00],  # Mar
            4:  [0.55,    0.27,    0.13,    0.05,    0.00,    0.00],  # Apr (Easter)
            5:  [0.58,    0.27,    0.13,    0.02,    0.00,    0.00],  # May
            6:  [0.60,    0.27,    0.13,    0.00,    0.00,    0.00],  # Jun
            7:  [0.55,    0.27,    0.13,    0.05,    0.00,    0.00],  # Jul (summer holidays)
            8:  [0.45,    0.27,    0.13,    0.15,    0.00,    0.00],  # Aug (peak summer holidays)
            9:  [0.45,    0.20,    0.10,    0.05,    0.20,    0.00],  # Sep (Oktoberfest starts)
            10: [0.50,    0.22,    0.10,    0.03,    0.15,    0.00],  # Oct (Oktoberfest ends)
            11: [0.50,    0.25,    0.13,    0.02,    0.00,    0.10],  # Nov (Christmas markets start)
            12: [0.30,    0.20,    0.13,    0.07,    0.00,    0.30],  # Dec (Christmas markets + holidays)
        }
        # Approx days per month
        days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

        def _sample_monthly_demand_modifiers(rng):
            """
            Returns dict {1..12 -> demand_modifier}. Each value is a composite
            multiplier reflecting: (1) day-archetype mix for that month,
            weighted by each archetype's sampled intensity, plus (2) shock
            events that landed in that month, weighted by their impact.

            Result is mean-1.0-centered so that a "normal" simulation produces
            modifiers near 1.0 across all months. Mutates the base
            seasonality_by_month multiplicatively.
            """
            # Sample one intensity per archetype (constant across the year for this iteration)
            arch_w = max(0.40, rng.normal(arch_weekday_mult, arch_weekday_sigma))
            arch_we = max(0.40, rng.normal(arch_weekend_mult, arch_weekend_sigma))
            arch_f = max(0.40, rng.normal(arch_friday_mult, arch_friday_sigma))
            arch_h = max(0.20, rng.normal(arch_holiday_mult, arch_holiday_sigma))
            arch_o = max(0.50, rng.normal(arch_oktober_mult, arch_oktober_sigma))
            arch_x = max(0.50, rng.normal(arch_xmas_mult, arch_xmas_sigma))
            arch_intensities = np.array([arch_w, arch_we, arch_f, arch_h, arch_o, arch_x])

            # Compute base demand modifier per month from policy mix × intensities
            mods = {}
            for m in range(1, 13):
                policy_row = np.array(month_arch_policy[m])
                # Weighted average demand intensity for this month
                base_mod = float(np.sum(policy_row * arch_intensities))
                mods[m] = base_mod

            # Sample shock events for the year
            # Use Poisson to sample actual count per shock type per year
            shock_specs = [
                (shock_weather_freq, shock_weather_mult, shock_weather_sigma),
                (shock_strike_freq,  shock_strike_mult,  shock_strike_sigma),
                (shock_event_freq,   shock_event_mult,   shock_event_sigma),
                (shock_tech_freq,    shock_tech_mult,    shock_tech_sigma),
                (shock_heat_freq,    shock_heat_mult,    shock_heat_sigma),
                (shock_ice_freq,     shock_ice_mult,     shock_ice_sigma),
                (shock_road_freq,    shock_road_mult,    shock_road_sigma),
            ]
            # Heat wave: concentrate in Jun-Aug; Black ice: concentrate in Dec-Feb
            # All others: uniform across 12 months
            shock_month_weights = [
                np.ones(12) / 12.0,                                                          # weather: uniform
                np.ones(12) / 12.0,                                                          # strike: uniform
                np.ones(12) / 12.0,                                                          # event: uniform
                np.ones(12) / 12.0,                                                          # tech outage: uniform
                np.array([0, 0, 0, 0, 0, 0.20, 0.40, 0.30, 0.10, 0, 0, 0]),                  # heat: Jun-Sep concentrated
                np.array([0.30, 0.25, 0.10, 0, 0, 0, 0, 0, 0, 0, 0.05, 0.30]),               # ice: Dec-Feb concentrated
                np.ones(12) / 12.0,                                                          # road: uniform
            ]

            # For each shock type, sample count and distribute across months
            shock_counts_by_month = np.zeros(12)
            shock_impact_sum_by_month = np.zeros(12)
            shock_total_counts = {}
            shock_type_names = ["weather", "strike", "event", "tech", "heat", "ice", "road"]
            for idx, (freq, mult, sigma) in enumerate(shock_specs):
                # Poisson sampling for count realization
                count = int(rng.poisson(freq))
                shock_total_counts[shock_type_names[idx]] = count
                if count == 0:
                    continue
                # Sample multiplier intensity (each day's shock has its own draw)
                # We use the average shock impact across the count for tractability
                avg_mult = max(0.0, rng.normal(mult, sigma))
                # Distribute count across months by weight
                weights = shock_month_weights[idx]
                # Probabilistic distribution: multinomial draw
                month_distribution = rng.multinomial(count, weights)
                for m_idx in range(12):
                    shock_counts_by_month[m_idx] += month_distribution[m_idx]
                    # Impact = (avg_mult - 1.0) × count, scaled per-day later
                    shock_impact_sum_by_month[m_idx] += (avg_mult - 1.0) * month_distribution[m_idx]

            # Apply shock impacts: per-day deviation from 1.0, averaged over month
            for m in range(1, 13):
                dim = days_per_month[m-1]
                # Shock contributes (deviation × shock_days) / total_days to the month average
                shock_contribution = shock_impact_sum_by_month[m-1] / dim
                mods[m] = mods[m] + shock_contribution
                # Floor at 0.20 to prevent degenerate negative cases
                mods[m] = max(0.20, mods[m])

            return mods, arch_intensities, shock_total_counts

        # ============================================================
        # === SIMULATION SETTINGS METADATA SNAPSHOT (provenance) ====
        # Captured BEFORE the loop so reruns of the analysis show
        # exactly which configuration produced the cached results.
        # ============================================================
        simulation_settings = {
            "iterations": int(n_iterations),
            "seed": 42,
            "delivery_enabled": delivery_enabled,
            "max_overdraft_limit": max_overdraft_limit,
            "min_cash_buffer": min_cash_buffer,
            "lang_choice": lang_choice,
            "util_mode": util_mode,
            "vat_lag_months": vat_lag_months,
            # Baseline central-case values (μ for Normal distributions)
            "baseline_centers": {
                "active_hours_per_day": active_hours_per_day,
                "avg_speed_kmh": avg_speed_kmh,
                "deadhead_rate": deadhead_rate,
                "target_util": target_util,
                "init_util": init_util,
                "rec_rate": rec_rate,
                "can_fac": can_fac,
                "avg_trip_distance_km": avg_trip_distance_km,
                "dwell_time_mins": dwell_time_mins,
                "price_per_km_eur": price_per_km_eur,
                "tesla_take_rate": tesla_take_rate,
                "cleaning_cost_per_day": cleaning_cost_per_day,
                "wear_and_tear_rate": wear_and_tear_rate,
                "energy_kwh_per_km": energy_kwh_per_km,
                "energy_eur_per_kwh": energy_eur_per_kwh,
                "charging_efficiency": charging_efficiency,
                "insurance_pm": insurance_pm,
                "parking_pm": parking_pm,
                "thg_quote_per_car_py": thg_quote_per_car_py,
                "salvage_value_per_car_y4": salvage_value_per_car_y4,
                "cybercab_base_usd": cybercab_base_usd,
                "usd_eur_rate": usd_eur_rate,
                "customs_duty_rate": customs_duty_rate,
                "vehicle_ltv": vehicle_ltv,
                "y1_loan_rate": y1_loan_rate,
                "y2_loan_rate": y2_loan_rate,
            },
            # Distribution bounds/sigmas selected by user
            "distribution_bounds": {
                "sigma_active_hours": mc_sigma_active_hours,
                "sigma_speed": mc_sigma_speed,
                "sigma_dwell": mc_sigma_dwell,
                "sigma_deadhead": mc_sigma_dh,
                "sigma_trip_distance": mc_sigma_trip,
                "target_util_min": mc_target_util_min,
                "target_util_max": mc_target_util_max,
                "sigma_init_util": mc_sigma_init_util,
                "sigma_rec_rate": mc_sigma_rec_rate,
                "sigma_can_fac": mc_sigma_can_fac,
                "sigma_price": mc_sigma_price,
                "take_min": mc_take_min, "take_mode": mc_take_mode, "take_max": mc_take_max,
                "dy2_min": mc_dy2_min, "dy2_mode": mc_dy2_mode, "dy2_max": mc_dy2_max,
                "dy3_min": mc_dy3_min, "dy3_mode": mc_dy3_mode, "dy3_max": mc_dy3_max,
                "dy4_min": mc_dy4_min, "dy4_mode": mc_dy4_mode, "dy4_max": mc_dy4_max,
                "sigma_capex": mc_sigma_capex, "sigma_fx": mc_sigma_fx, "sigma_ltv": mc_sigma_ltv,
                "loan_y1_min": mc_loan_y1_min, "loan_y1_mode": mc_loan_y1_mode, "loan_y1_max": mc_loan_y1_max,
                "loan_y2_min": mc_loan_y2_min, "loan_y2_mode": mc_loan_y2_mode, "loan_y2_max": mc_loan_y2_max,
                "ins_min": mc_ins_min, "ins_mode": mc_ins_mode, "ins_max": mc_ins_max,
                "sigma_energy_eur": mc_sigma_energy_eur, "sigma_kwh": mc_sigma_kwh,
                "sigma_cleaning": mc_sigma_cleaning, "sigma_wear": mc_sigma_wear,
                "sigma_parking": mc_sigma_parking, "sigma_customs": mc_sigma_customs,
                "sigma_salvage": mc_sigma_salvage,
            }
        }

        rng = np.random.default_rng(seed=42)  # deterministic seed for reproducibility
        ni_cum_arr = np.zeros(n_iterations)
        y5_ebitda_arr = np.zeros(n_iterations)
        fcf_cum_arr = np.zeros(n_iterations)  # NEW: 5Y cumulative FCF
        min_cash_arr = np.zeros(n_iterations)
        insolvency_flags = np.zeros(n_iterations, dtype=bool)

        # Tier-organized parameter sample storage (22 params)
        param_samples = {
            # Tier 1
            "active_hours_per_day":    np.zeros(n_iterations),
            "avg_speed_kmh":           np.zeros(n_iterations),
            "dwell_time_mins":         np.zeros(n_iterations),
            "target_util":             np.zeros(n_iterations),
            "init_util":               np.zeros(n_iterations),
            "rec_rate":                np.zeros(n_iterations),
            "can_fac":                 np.zeros(n_iterations),
            "deadhead_rate":           np.zeros(n_iterations),
            "avg_trip_distance_km":    np.zeros(n_iterations),
            "price_per_km_eur":        np.zeros(n_iterations),
            "tesla_take_rate":         np.zeros(n_iterations),
            "delivery_ramp_y2":        np.zeros(n_iterations),
            "delivery_ramp_y3":        np.zeros(n_iterations),
            "delivery_ramp_y4":        np.zeros(n_iterations),
            # Tier 2
            "cybercab_base_usd":       np.zeros(n_iterations),
            "usd_eur_rate":            np.zeros(n_iterations),
            "vehicle_ltv":             np.zeros(n_iterations),
            "y1_loan_rate":            np.zeros(n_iterations),
            "y2_loan_rate":            np.zeros(n_iterations),
            "insurance_pm":            np.zeros(n_iterations),
            "energy_eur_per_kwh":      np.zeros(n_iterations),
            "energy_kwh_per_km":       np.zeros(n_iterations),
            # Tier 3
            "cleaning_cost_per_day":   np.zeros(n_iterations),
            "wear_and_tear_rate":      np.zeros(n_iterations),
            "parking_pm":              np.zeros(n_iterations),
            "customs_duty_rate":       np.zeros(n_iterations),
            "salvage_value_per_car_y4": np.zeros(n_iterations),
            # === PHASE A: Day-archetype intensity tracking ===
            "arch_weekday_intensity":   np.zeros(n_iterations),
            "arch_weekend_intensity":   np.zeros(n_iterations),
            "arch_friday_intensity":    np.zeros(n_iterations),
            "arch_holiday_intensity":   np.zeros(n_iterations),
            "arch_oktober_intensity":   np.zeros(n_iterations),
            "arch_xmas_intensity":      np.zeros(n_iterations),
            # === PHASE B: Shock event count tracking (per 5Y horizon) ===
            "shock_weather_5y":         np.zeros(n_iterations),
            "shock_strike_5y":          np.zeros(n_iterations),
            "shock_event_5y":           np.zeros(n_iterations),
            "shock_tech_5y":            np.zeros(n_iterations),
            "shock_heat_5y":            np.zeros(n_iterations),
            "shock_ice_5y":             np.zeros(n_iterations),
            "shock_road_5y":            np.zeros(n_iterations),
        }

        progress_bar = st.progress(0.0, text=loc["mc_running_msg"])
        t_start = time.time()

        for i in range(int(n_iterations)):
            # ===== TIER 1 — HIGH VARIANCE OPERATING PHYSICS =====
            active_hours_sampled = max(8.0, min(22.0, rng.normal(active_hours_per_day, mc_sigma_active_hours)))
            speed_sampled = max(10.0, min(30.0, rng.normal(avg_speed_kmh, mc_sigma_speed)))
            dwell_sampled = max(0.5, min(8.0, rng.normal(dwell_time_mins, mc_sigma_dwell)))
            target_util_sampled = _sample_beta_scaled(rng, 0.75, mc_target_util_min, mc_target_util_max)
            init_util_sampled = max(0.10, min(0.95, rng.normal(init_util, mc_sigma_init_util)))
            rec_rate_sampled = max(0.001, min(0.20, rng.normal(rec_rate, mc_sigma_rec_rate)))
            can_fac_sampled = max(0.05, min(0.95, rng.normal(can_fac, mc_sigma_can_fac)))
            deadhead_sampled = max(0.05, min(0.50, rng.normal(deadhead_rate, mc_sigma_dh)))
            trip_dist_sampled = max(1.0, rng.normal(avg_trip_distance_km, mc_sigma_trip))
            price_sampled = max(0.10, rng.normal(price_per_km_eur, mc_sigma_price))
            take_sampled = _sample_triangular(rng, mc_take_min, mc_take_mode, mc_take_max)
            dy2_sampled = _sample_triangular(rng, mc_dy2_min, mc_dy2_mode, mc_dy2_max)
            dy3_sampled = _sample_triangular(rng, mc_dy3_min, mc_dy3_mode, mc_dy3_max)
            dy4_sampled = _sample_triangular(rng, mc_dy4_min, mc_dy4_mode, mc_dy4_max)

            # ===== TIER 2 — MATERIAL VARIANCE (capex, debt, costs) =====
            capex_sampled = max(5000.0, rng.normal(cybercab_base_usd, mc_sigma_capex))
            fx_sampled = max(0.50, min(2.50, rng.normal(usd_eur_rate, mc_sigma_fx)))
            ltv_sampled = max(0.20, min(0.95, rng.normal(vehicle_ltv, mc_sigma_ltv)))
            loan_y1_sampled = _sample_triangular(rng, mc_loan_y1_min, mc_loan_y1_mode, mc_loan_y1_max)
            loan_y2_sampled = _sample_triangular(rng, mc_loan_y2_min, mc_loan_y2_mode, mc_loan_y2_max)
            insurance_sampled = _sample_triangular(rng, mc_ins_min, mc_ins_mode, mc_ins_max)
            # Log-Normal energy price: median = current sidebar value
            mu_log = np.log(max(0.01, energy_eur_per_kwh))
            sigma_log = mc_sigma_energy_eur / max(0.01, energy_eur_per_kwh)
            energy_eur_sampled = float(rng.lognormal(mean=mu_log, sigma=sigma_log))
            kwh_per_km_sampled = max(0.05, rng.normal(energy_kwh_per_km, mc_sigma_kwh))

            # ===== TIER 3 — SMALLER VARIANCE (operating costs) =====
            cleaning_sampled = max(0.50, rng.normal(cleaning_cost_per_day, mc_sigma_cleaning))
            wear_sampled = max(0.001, rng.normal(wear_and_tear_rate, mc_sigma_wear))
            parking_sampled = max(50.0, rng.normal(parking_pm, mc_sigma_parking))
            customs_sampled = max(0.0, min(0.40, rng.normal(customs_duty_rate, mc_sigma_customs)))
            salvage_sampled = max(0.0, rng.normal(salvage_value_per_car_y4, mc_sigma_salvage))

            # Record samples for tornado correlation analysis
            param_samples["active_hours_per_day"][i] = active_hours_sampled
            param_samples["avg_speed_kmh"][i] = speed_sampled
            param_samples["dwell_time_mins"][i] = dwell_sampled
            param_samples["target_util"][i] = target_util_sampled
            param_samples["init_util"][i] = init_util_sampled
            param_samples["rec_rate"][i] = rec_rate_sampled
            param_samples["can_fac"][i] = can_fac_sampled
            param_samples["deadhead_rate"][i] = deadhead_sampled
            param_samples["avg_trip_distance_km"][i] = trip_dist_sampled
            param_samples["price_per_km_eur"][i] = price_sampled
            param_samples["tesla_take_rate"][i] = take_sampled
            param_samples["delivery_ramp_y2"][i] = dy2_sampled
            param_samples["delivery_ramp_y3"][i] = dy3_sampled
            param_samples["delivery_ramp_y4"][i] = dy4_sampled
            param_samples["cybercab_base_usd"][i] = capex_sampled
            param_samples["usd_eur_rate"][i] = fx_sampled
            param_samples["vehicle_ltv"][i] = ltv_sampled
            param_samples["y1_loan_rate"][i] = loan_y1_sampled
            param_samples["y2_loan_rate"][i] = loan_y2_sampled
            param_samples["insurance_pm"][i] = insurance_sampled
            param_samples["energy_eur_per_kwh"][i] = energy_eur_sampled
            param_samples["energy_kwh_per_km"][i] = kwh_per_km_sampled
            param_samples["cleaning_cost_per_day"][i] = cleaning_sampled
            param_samples["wear_and_tear_rate"][i] = wear_sampled
            param_samples["parking_pm"][i] = parking_sampled
            param_samples["customs_duty_rate"][i] = customs_sampled
            param_samples["salvage_value_per_car_y4"][i] = salvage_sampled

            # ====================================================================
            # PHASE A + B: Sample monthly demand modifiers from day-archetype mix
            # and shock events. Mutate base seasonality_by_month multiplicatively.
            # ====================================================================
            monthly_mods, arch_intensities_iter, shock_counts_iter = _sample_monthly_demand_modifiers(rng)
            seasonality_iter = {m: seasonality_by_month[m] * monthly_mods[m] for m in range(1, 13)}

            # Record archetype intensities + shock counts (×5 for 5-year horizon)
            param_samples["arch_weekday_intensity"][i]  = arch_intensities_iter[0]
            param_samples["arch_weekend_intensity"][i]  = arch_intensities_iter[1]
            param_samples["arch_friday_intensity"][i]   = arch_intensities_iter[2]
            param_samples["arch_holiday_intensity"][i]  = arch_intensities_iter[3]
            param_samples["arch_oktober_intensity"][i]  = arch_intensities_iter[4]
            param_samples["arch_xmas_intensity"][i]     = arch_intensities_iter[5]
            # Shock counts shown per-year basis (multiply by 5 for the full horizon)
            # The Poisson sample was one-year; over 5 years, expected count is 5×freq.
            # We sample once per iteration and apply that yearly intensity for 5 years
            # (acceptable approximation that under-states tail variance slightly).
            param_samples["shock_weather_5y"][i] = shock_counts_iter.get("weather", 0) * 5
            param_samples["shock_strike_5y"][i]  = shock_counts_iter.get("strike", 0) * 5
            param_samples["shock_event_5y"][i]   = shock_counts_iter.get("event", 0) * 5
            param_samples["shock_tech_5y"][i]    = shock_counts_iter.get("tech", 0) * 5
            param_samples["shock_heat_5y"][i]    = shock_counts_iter.get("heat", 0) * 5
            param_samples["shock_ice_5y"][i]     = shock_counts_iter.get("ice", 0) * 5
            param_samples["shock_road_5y"][i]    = shock_counts_iter.get("road", 0) * 5

            # Derived energy rate from sampled components
            energy_rate_sampled = (kwh_per_km_sampled * energy_eur_sampled) / charging_efficiency

            # ---- Invoke the deterministic engine with sampled params ----
            try:
                pnl_mc, cf_mc, bs_mc, _mn, _cb, _nlb, insolvency_mc, _fl, _ut, _tcc, _bsk = execute_financial_simulation(
                    y1_adds_str, y2_adds_str, y3_adds_str, y4_adds_str, y5_adds_str,
                    active_hours_sampled, speed_sampled, deadhead_sampled, util_mode,
                    target_util_sampled, init_util_sampled, rec_rate_sampled, can_fac_sampled, flat_util, trip_dist_sampled,
                    dwell_sampled, base_fare_eur, price_sampled, take_sampled,
                    cleaning_sampled, wear_sampled, energy_rate_sampled, insurance_sampled,
                    parking_sampled, telemetry_pm, tuev_pm, charging_sub_pm, hq_lease_pm, it_cloud_pm,
                    legal_bookkeeping_pm, hq_insurance_pm, legal_scaling_pm,
                    insurance_scaling_pm, bank_fees_pm, ihk_pm, gez_pm_per_car, setup_costs_y1,
                    capex_sampled, fx_sampled, import_freight_eur, customs_sampled,
                    it_hardware_capex_y1, imp_month, imp_pct_val, stammkapital, shareholder_loan,
                    sh_loan_rate, ltv_sampled, loan_y1_sampled, loan_y2_sampled, vat_bridge_rate,
                    vat_lag_months, min_cash_buffer, legal_provision_rate, interest_income_rate,
                    thg_quote_per_car_py, salvage_sampled, max_overdraft_limit,
                    delivery_enabled, delivery_hours_per_day, delivery_rev_per_trip,
                    delivery_trips_per_hour, delivery_take_rate,
                    delivery_ramp_y1, dy2_sampled, dy3_sampled, dy4_sampled, delivery_ramp_y5,
                    delivery_cargo_insurance_pm, seasonality_iter,
                    is_dynamic, lang_choice,
                    # === Financing mix held constant during MC (sidebar settings) ===
                    fin_mix_by_year, lease_money_factor, lease_downpayment_pct,
                    lease_term_months, equity_capital_call_enabled
                )
                ni_cum_arr[i] = float(sum(pnl_mc["pnl_ni"]))
                y5_ebitda_arr[i] = float(sum(pnl_mc["pnl_ebitda"][48:60]))
                # NEW: 5-year cumulative Free Cash Flow = sum(CFO + CFI)
                cf_op_arr = np.array(cf_mc["cf_op"])
                cf_inv_arr = np.array(cf_mc["cf_inv"])
                fcf_cum_arr[i] = float(np.sum(cf_op_arr + cf_inv_arr))
                min_cash_arr[i] = float(min(bs_mc["bs_cash"]))
                insolvency_flags[i] = (len(insolvency_mc) > 0)
            except Exception as _e:
                ni_cum_arr[i] = np.nan
                y5_ebitda_arr[i] = np.nan
                fcf_cum_arr[i] = np.nan
                min_cash_arr[i] = np.nan
                insolvency_flags[i] = False

            if (i + 1) % 50 == 0 or (i + 1) == int(n_iterations):
                progress_bar.progress((i + 1) / int(n_iterations),
                                      text=loc["mc_progress_label"].format(i=i+1, n=int(n_iterations)))

        t_elapsed = time.time() - t_start
        progress_bar.empty()

        # ============================================================
        # === NESTED PERSISTENCE: settings + outputs for provenance ==
        # ============================================================
        simulation_outputs = {
            "elapsed": t_elapsed,
            "ni_cum": ni_cum_arr,
            "y5_ebitda": y5_ebitda_arr,
            "fcf_cum": fcf_cum_arr,
            "min_cash": min_cash_arr,
            "insolvency_flags": insolvency_flags,
            "param_samples": param_samples,
        }
        st.session_state["mc_results"] = {
            "simulation_settings": simulation_settings,
            "simulation_outputs": simulation_outputs,
            # Convenience flat-access keys (preserves backward-compat with prior layer)
            "n": int(n_iterations),
            "elapsed": t_elapsed,
            "min_cash_buffer": min_cash_buffer,
        }
        st.success(loc["mc_complete_msg"].format(n=int(n_iterations), t=t_elapsed))

    # --- Render results (if cached or just computed) ---
    if "mc_results" in st.session_state:
        mcr = st.session_state["mc_results"]
        sim_out = mcr["simulation_outputs"]
        ni_arr = sim_out["ni_cum"]
        eb_arr = sim_out["y5_ebitda"]
        fcf_arr = sim_out["fcf_cum"]
        cash_arr = sim_out["min_cash"]
        insol_flags = sim_out["insolvency_flags"]
        param_samples_stored = sim_out["param_samples"]
        buffer_threshold = mcr["min_cash_buffer"]
        ni_valid = ni_arr[~np.isnan(ni_arr)]
        eb_valid = eb_arr[~np.isnan(eb_arr)]
        fcf_valid = fcf_arr[~np.isnan(fcf_arr)]
        cash_valid = cash_arr[~np.isnan(cash_arr)]

        st.divider()
        st.subheader(loc["mc_kpi_header"])
        def _pct(arr, p):
            return float(np.percentile(arr, p)) if len(arr) > 0 else 0.0
        prob_insolvency = float(np.mean(insol_flags)) * 100

        # Percentile table now includes FCF row
        df_percentiles = pd.DataFrame({
            loc["mc_kpi_p5"]:  [_pct(ni_valid, 5),  _pct(eb_valid, 5),  _pct(fcf_valid, 5),  _pct(cash_valid, 5)],
            loc["mc_kpi_p25"]: [_pct(ni_valid, 25), _pct(eb_valid, 25), _pct(fcf_valid, 25), _pct(cash_valid, 25)],
            loc["mc_kpi_p50"]: [_pct(ni_valid, 50), _pct(eb_valid, 50), _pct(fcf_valid, 50), _pct(cash_valid, 50)],
            loc["mc_kpi_p75"]: [_pct(ni_valid, 75), _pct(eb_valid, 75), _pct(fcf_valid, 75), _pct(cash_valid, 75)],
            loc["mc_kpi_p95"]: [_pct(ni_valid, 95), _pct(eb_valid, 95), _pct(fcf_valid, 95), _pct(cash_valid, 95)],
        }, index=[loc["mc_kpi_ni_cum"], loc["mc_kpi_y5_ebitda"], loc["mc_kpi_fcf_cum"], loc["mc_kpi_min_cash"]])
        st.dataframe(df_percentiles.style.format("€ {:,.0f}"), use_container_width=True)

        mc_metric_c1, mc_metric_c2, mc_metric_c3 = st.columns(3)
        with mc_metric_c1:
            st.metric(loc["mc_kpi_insolvency"], f"{prob_insolvency:.2f}%",
                      delta=None, help="Fraction of MC runs producing at least one insolvency month event.")
        with mc_metric_c2:
            st.metric("Median 5Y NI", f"€ {_pct(ni_valid, 50):,.0f}")
        with mc_metric_c3:
            st.metric("P5 5Y NI (Severe Downside)", f"€ {_pct(ni_valid, 5):,.0f}")

        # ============================================================
        # === INTERACTIVE METRIC DROPDOWN — reshapes Chart 1+tornado =
        # ============================================================
        st.divider()
        metric_view = st.selectbox(
            loc["mc_metric_selector"],
            [loc["mc_metric_fcf"], loc["mc_metric_ebitda"], loc["mc_metric_ni"]],
            index=2  # default to Net Income (most familiar to non-finance audience)
        )
        # Dynamic remap of target array, percentiles, and chart title
        if metric_view == loc["mc_metric_fcf"]:
            target_arr_full = fcf_arr
            target_valid = fcf_valid
            chart_title = loc["mc_chart_fcf_title"]
            xaxis_label = "5-Year Cumulative Free Cash Flow (€)"
        elif metric_view == loc["mc_metric_ebitda"]:
            target_arr_full = eb_arr
            target_valid = eb_valid
            chart_title = loc["mc_chart_ebitda_title"]
            xaxis_label = "Year 5 EBITDA (€)"
        else:  # Net Income
            target_arr_full = ni_arr
            target_valid = ni_valid
            chart_title = loc["mc_chart_ni_title"]
            xaxis_label = "5-Year Cumulative Net Income (€)"

        st.subheader(loc["mc_section_outputs"])

        # --- Chart 1: Dynamic Histogram of selected metric ---
        tgt_p5 = _pct(target_valid, 5)
        tgt_p50 = _pct(target_valid, 50)
        tgt_p95 = _pct(target_valid, 95)
        fig_target = go.Figure()
        fig_target.add_trace(go.Histogram(
            x=target_valid, nbinsx=60,
            marker=dict(color="#4DA8DA", line=dict(color="#1a1a1a", width=0.5)),
            opacity=0.85, name=metric_view
        ))
        fig_target.add_vline(x=tgt_p5, line_dash="dash", line_color="#E74C3C", line_width=2,
                             annotation_text=f"{loc['mc_p5_label']}: €{tgt_p5:,.0f}", annotation_position="top")
        fig_target.add_vline(x=tgt_p95, line_dash="dash", line_color="#38c172", line_width=2,
                             annotation_text=f"{loc['mc_p95_label']}: €{tgt_p95:,.0f}", annotation_position="top")
        fig_target.add_vline(x=tgt_p50, line_dash="dot", line_color="#F2A900", line_width=2,
                             annotation_text=f"{loc['mc_p50_label']}: €{tgt_p50:,.0f}", annotation_position="bottom")
        fig_target.update_layout(
            title=chart_title,
            xaxis_title=xaxis_label,
            yaxis_title="Frequency",
            template="plotly_dark",
            paper_bgcolor="#0e1117", plot_bgcolor="#1a1a1a",
            font=dict(color="#FAFAFA", family="Inter, sans-serif"),
            showlegend=False, height=420
        )
        st.plotly_chart(fig_target, use_container_width=True)

        # --- Chart 2: Min Cash distribution (always tracks cash, independent of dropdown) ---
        fig_cash = go.Figure()
        fig_cash.add_trace(go.Histogram(
            x=cash_valid, nbinsx=60, marker=dict(color="#87CEEB", line=dict(color="#1a1a1a", width=0.5)),
            opacity=0.85, name="Min Cash Balance"
        ))
        fig_cash.add_vline(x=buffer_threshold, line_dash="dash", line_color="#F2A900", line_width=2.5,
                           annotation_text=f"{loc['mc_buffer_line_label']}: €{buffer_threshold:,.0f}",
                           annotation_position="top")
        fig_cash.add_vline(x=0, line_dash="solid", line_color="#E74C3C", line_width=2.5,
                           annotation_text="Zero Cash", annotation_position="bottom")
        fig_cash.update_layout(
            title=loc["mc_chart_cash_title"],
            xaxis_title="Minimum Cash Balance Over 60 Months (€)",
            yaxis_title="Frequency",
            template="plotly_dark",
            paper_bgcolor="#0e1117", plot_bgcolor="#1a1a1a",
            font=dict(color="#FAFAFA", family="Inter, sans-serif"),
            showlegend=False, height=420
        )
        st.plotly_chart(fig_cash, use_container_width=True)

        # --- Chart 3: Tornado vs DYNAMIC target metric (FCF/EBITDA/NI) ---
        valid_mask = ~np.isnan(target_arr_full)
        corrs = {}
        param_label_map = {
            # Tier 1
            "active_hours_per_day":     "Active Hours per Day [T1]",
            "avg_speed_kmh":            "Average Speed (km/h) [T1]",
            "dwell_time_mins":          "Dwell Time (min) [T1]",
            "target_util":              "Target Utilization [T1]",
            "init_util":                "Init Utilization [T1]",
            "rec_rate":                 "Recovery Rate [T1]",
            "can_fac":                  "Cannibalization Factor [T1]",
            "deadhead_rate":            "Deadhead Rate [T1]",
            "avg_trip_distance_km":    "Avg Trip Distance (km) [T1]",
            "price_per_km_eur":         "Price per km (€) [T1]",
            "tesla_take_rate":          "Tesla Take-Rate [T1]",
            "delivery_ramp_y2":         "Delivery Ramp Y2 [T1]",
            "delivery_ramp_y3":         "Delivery Ramp Y3 [T1]",
            "delivery_ramp_y4":         "Delivery Ramp Y4 [T1]",
            # Tier 2
            "cybercab_base_usd":        "Cybercab Base Capex USD [T2]",
            "usd_eur_rate":             "USD/EUR FX Rate [T2]",
            "vehicle_ltv":              "Vehicle LTV [T2]",
            "y1_loan_rate":             "Y1 Loan Rate [T2]",
            "y2_loan_rate":             "Y2 Loan Rate [T2]",
            "insurance_pm":             "Insurance (€/mo) [T2]",
            "energy_eur_per_kwh":       "Energy Price (€/kWh) [T2]",
            "energy_kwh_per_km":        "Cybercab Consumption (kWh/km) [T2]",
            # Tier 3
            "cleaning_cost_per_day":    "Cleaning Cost (€/day) [T3]",
            "wear_and_tear_rate":       "Wear & Tear (€/km) [T3]",
            "parking_pm":               "Parking (€/mo) [T3]",
            "customs_duty_rate":        "Customs Duty Rate [T3]",
            "salvage_value_per_car_y4": "Salvage Value (€) [T3]",
            # === PHASE A: Day-archetype intensity drivers ===
            "arch_weekday_intensity":   "Weekday Demand Intensity [DA]",
            "arch_weekend_intensity":   "Weekend Demand Intensity [DA]",
            "arch_friday_intensity":    "Fri/Sat Evening Intensity [DA]",
            "arch_holiday_intensity":   "Holiday Demand Intensity [DA]",
            "arch_oktober_intensity":   "Oktoberfest Demand Intensity [DA]",
            "arch_xmas_intensity":      "Christmas Markets Intensity [DA]",
            # === PHASE B: Shock event count drivers ===
            "shock_weather_5y":         "Severe Weather Days (5Y) [SH]",
            "shock_strike_5y":          "Transit Strike Days (5Y) [SH]",
            "shock_event_5y":           "Major Event Days (5Y) [SH]",
            "shock_tech_5y":            "Tech Outage Days (5Y) [SH]",
            "shock_heat_5y":            "Heat Wave Days (5Y) [SH]",
            "shock_ice_5y":             "Black Ice Days (5Y) [SH]",
            "shock_road_5y":            "Road Closure Days (5Y) [SH]",
        }
        for param_key, samples_arr in param_samples_stored.items():
            samples_valid_sub = samples_arr[valid_mask]
            target_valid_for_corr = target_arr_full[valid_mask]
            if len(samples_valid_sub) > 2 and np.std(samples_valid_sub) > 1e-12 and np.std(target_valid_for_corr) > 1e-12:
                r = float(np.corrcoef(samples_valid_sub, target_valid_for_corr)[0, 1])
                if np.isnan(r):
                    r = 0.0
            else:
                r = 0.0
            corrs[param_label_map[param_key]] = r
        sorted_corrs = sorted(corrs.items(), key=lambda kv: abs(kv[1]), reverse=False)
        tornado_labels = [k for k, _ in sorted_corrs]
        tornado_values = [v for _, v in sorted_corrs]
        tornado_colors = ["#38c172" if v >= 0 else "#E74C3C" for v in tornado_values]

        fig_tornado = go.Figure()
        fig_tornado.add_trace(go.Bar(
            x=tornado_values, y=tornado_labels, orientation="h",
            marker=dict(color=tornado_colors, line=dict(color="#1a1a1a", width=0.5)),
            text=[f"{v:+.3f}" for v in tornado_values], textposition="outside",
            cliponaxis=False
        ))
        fig_tornado.add_vline(x=0, line_color="#666666", line_width=1)
        fig_tornado.update_layout(
            title=f"{loc['mc_chart_tornado_title']} — Target: {metric_view}",
            xaxis_title=loc["mc_tornado_xaxis"],
            yaxis_title="",
            template="plotly_dark",
            paper_bgcolor="#0e1117", plot_bgcolor="#1a1a1a",
            font=dict(color="#FAFAFA", family="Inter, sans-serif"),
            showlegend=False, height=1100,  # tall to fit 40+ bars (params + archetypes + shocks)
            xaxis=dict(range=[-1.0, 1.0])
        )
        st.plotly_chart(fig_tornado, use_container_width=True)

        st.caption(
            "**Interpretation guide:** Pearson r magnitude shows how strongly each "
            "stochastic input drives variance in the selected target metric "
            f"({metric_view}). Positive r (green) means higher input → higher target. "
            "Negative r (red) means higher input → lower target. Magnitudes < 0.1 "
            "are essentially noise; > 0.3 indicates a dominant variance driver worth "
            "scenario-planning. Tornado is sorted by |r| with strongest drivers at top. "
            "**Tier suffix legend:** [T1]=Operating Physics, [T2]=Capex/Debt, "
            "[T3]=Operating Costs, [DA]=Day Archetype intensity (Phase A demand topology), "
            "[SH]=Shock Event frequency (Phase B asymmetric event risk). "
            "Switch the dropdown above to see how the same parameter set drives FCF vs "
            "EBITDA vs Net Income differently — useful for understanding which "
            "uncertainties matter for cash position vs operational profitability."
        )
    else:
        st.info(loc["mc_no_results"])

with tabs[7]:
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
        * **OpEx Input VAT (Vorsteuerabzug, ):** When you pay vendors for energy, maintenance, parking, telemetry, IT, HQ lease, legal services, etc., you pay them gross (net + 19% VAT). That 19% is **deductible input VAT** that offsets your monthly Umsatzsteuerzahllast to the Finanzamt. The model now correctly: (1) drains vendor VAT as cash this month, (2) reduces the next month's VAT remittance by the same amount. The P&L stays unchanged — costs are always booked net — but the Cash Flow and Balance Sheet now reflect real UStG mechanics. VAT-exempt items (insurance, IHK, GEZ, bank fees) are excluded per § 4 UStG.
        * **fixes:** (a) **Vehicle AfA is now 60 months** (5 Jahre, aligned with BMF AfA-Tabelle for Mietwagen/Taxi per § 7 EStG). (b) **Overdraft is now capped** at a user-defined Kontokorrentlinie; if the model needs more, **INSOLVENCY** is flagged. (c) **Three distinct liquidity warnings:** Insolvency (line exceeded), Net Liquidity Negative (Cash − Overdraft below buffer = bank-grade Effektive Liquidität check), Raw Cash Floor Breached (traditional check). (d) **Cleaning cost** now depends on calendar days × fleet only, not on utilization. (e) **EBITDA HGB View** memo row added below Mgmt EBITDA showing the salvage bridge per § 275 II Nr. 4 HGB.

        ---

        #### 🎯 Operational Calibration & Benchmarking ()
        Operational and variable cost assumptions in this model reflect mature-state central-case values benchmarked against published European mobility operator data (Sixt+, Free Now, MOIA/Volkswagen Group, Waymo Phoenix). Throughput calibration assumes **30-34 trips/day per vehicle at steady-state (Y3+)**, built up from 13.5h blended weekday/weekend productive shift, 19 km/h Munich average speed, 3.5 min per-trip dwell, and 22% empty repositioning. Energy and wear cost recalibrations land at **€0.085/km and €0.10/km** respectively — below Waymo benchmarks due to simpler Cybercab sensor stack and German labor rates, above earlier optimistic estimates that did not survive bank-grade Due Diligence. Y1-Y2 ramp-state will run below mature numbers; the engine's **Dynamic Utilization** mode (set as default) models this naturally through the cannibalization + recovery mechanics. For aggressive bull-case modeling, adjust sidebar inputs upward and document the rationale separately.

        **Utilization Recalibration + Two-Stream Revenue:** The initial utilization parameters (init 35%, rec 3%/month, can_fac 0.5) produced a Y5 utilization collapse — the cannibalization formula could not recover between cohort additions in Y3-Y5. recalibrates four utilization parameters as a coordinated set: init 55% (price elasticity + novelty + supply concentration), rec 5%/month (matches Y3-Y5 cohort cadence), can_fac 0.35 (mature dispatch algorithm), target 75% unchanged. On 24h calendar-day basis, Month 1 launches at ~31% asset utilization and Y5 mature state sits at ~41% — consistent with Uber NYC mature-market published Marketplace data (38-42%). **B2B Delivery toggle (default OFF):** Tesla Network dispatches Cybercabs for goods delivery during low-passenger-demand windows using the same dispatch architecture. When toggled ON, adds 4.5h of additional active hours/day with €6/delivery × 3 deliveries/hour × ramped activation (0/0/30/70/100% Y1-Y5). Conservative base case is passenger-only; delivery toggle is "upside layer" the user activates to model the asset's full 18h Tesla Network productivity (75% 24h asset utilization). Tesla controls dispatch priority — passenger trips preempt delivery when both have demand. Inference compute revenue explicitly excluded from base case (Tesla program not commercially launched).

        **— Energy Decomposition + Calibration Refinements + Adjustable Seasonality:** Six coordinated updates after detailed CFO/CPA audit conversations. (1) **Energy cost decomposed into 3 sliders:** consumption €0.115 kWh/km (anchored on Tesla VP Lars Moravy's May 21, 2026 Cybercab certification at 165 Wh/mi = 0.103 kWh/km plus 12% real-world derate), blended price €0.22/kWh (German wholesale off-peak €0.04-0.09 + Tesla Supercharger off-peak €0.31-0.46, weighted 70/30 depot inductive / V4 wired with fleet subscription), charging efficiency 0.94 (Tesla's stated "well over 90%" inductive at 22 kW × 0.70 + V4 wired 96% × 0.30). Combined effective rate: €0.027/km vs prior €0.085 — 68% reduction reflecting actual Cybercab efficiency. (2) **Insurance €300 → €180/month** via bottom-up rebuild: theft component ~€0 (Cybercab undriveable outside Tesla Network, Waymo Phoenix 7yr data confirms), Tesla Insurance bundling thesis (-15% discount), FSD safety credit (70% reduction on bodily injury/property damage liability), residual categories (vandalism €20, battery/fire €20, weather €12, passenger damage €15, cyber €40, legal reserve €30, BI/PD post-FSD €55, PBefG €18) sum to ~€210, less Tesla bundle discount and 5-year averaging = €180. (3) **APCOA parking €250 → €170/month** per published 2024 Munich monthly parking €120-180 + charging-capable premium €40-80 less 15-25% Y5 bulk discount. (4) **Cleaning €3 → €2/day net** reflecting Tesla's published Robotaxi cleaning fee policy ($50 moderate / $150 severe, live Dec 2025) — gross cost ~€5/day depot deep-clean less ~€3/day Tesla fee pass-through revenue. (5) **Active hours 13.5h → 16.0h** unlocked by corrected Cybercab efficiency math (lower kWh/km consumption + 90%+ inductive efficiency = no battery-capacity constraint on extended shifts even in winter peak weeks). (6) **NEW cargo insurance €20/car/month** Verkehrshaftungsversicherung, only billed when delivery toggle is active (covers cargo value, theft in transit, weather damage — doesn't benefit from FSD safety credit). (7) **NEW adjustable monthly seasonality:** 12 individual month sliders in collapsible expander replace the prior hardcoded 4-tier. Defaults preserve blend (1.2125×) — Dec/Jan/Feb 1.45, Nov/Mar 1.30, Apr/Oct 1.05, May-Sep 1.10. User can stress-test winter penalty assumptions (e.g., Tesla 4680 dry-cathode reduces winter penalty 10-15% vs 2170 cells). THG quote €200 → €280/car/year per 2024 German actuals also bundled in this layer.

        **Empirical sources:** TomTom Traffic Index 2024 (Munich congestion); ADAC Wintertest 2023 + Geotab fleet study (EV winter consumption); Waymo NHTSA filings (sensor reliability, dwell time, ramp curves); Sixt+ / Free Now / MOIA published operator data (€/km maintenance benchmarks); Uber/Lyft Marketplace blog data (mature European deadhead rates); Tesla May 2026 Model S/X SE event (Cybercab 165 Wh/mi certification); EPEX Spot 2025 German wholesale electricity data (off-peak hours €0.04-0.09/kWh); Tesla Supercharger pricing Germany 2026 (€0.31-0.46/kWh Tesla off-peak); Tesla Robotaxi cleaning fee policy December 2025 ($50/$150 tiers).

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
        * **OpEx-Vorsteuerabzug ():** Wenn Sie Lieferanten für Energie, Wartung, Stellplätze, Telemetrie, IT, Raumkosten, Rechts- und Beratungsleistungen usw. bezahlen, zahlen Sie brutto (netto + 19% USt). Diese 19% sind **abzugsfähige Vorsteuer**, die mit der monatlichen Umsatzsteuerzahllast verrechnet wird. Das Modell bildet nun korrekt ab: (1) Vorsteuer fließt in diesem Monat als Cash-Abfluss zum Lieferanten ab, (2) die Zahllast an das Finanzamt im Folgemonat wird um genau diesen Betrag reduziert. Die GuV bleibt unverändert — Kosten werden stets netto gebucht — aber Kapitalflussrechnung und Bilanz spiegeln nun die echten UStG-Mechanik wider. Nicht abzugsfähige Posten (Versicherung, IHK, GEZ, Bankgebühren) sind gemäß § 4 UStG ausgenommen.
        * **Verbesserungen:** (a) **Fahrzeug-AfA jetzt 60 Monate** (5 Jahre, BMF AfA-Tabelle Mietwagen/Taxi gem. § 7 EStG). (b) **Kontokorrent gedeckelt** auf eine benutzerdefinierte Linie; bei Überschreitung wird **INSOLVENZ** angezeigt. (c) **Drei separate Liquiditätssignale:** Insolvenz (Linie überschritten), Netto-Liquidität negativ (Kasse − Kontokorrent unter Puffer = bankübliche Effektive Liquidität), Mindestliquidität unterschritten (klassische Prüfung). (d) **Reinigungskosten** abhängig nur von Kalendertagen × Flotte, nicht von Auslastung. (e) **EBITDA HGB-Sicht** als Memo-Zeile unter Management-EBITDA mit Anlagenabgang-Brücke gem. § 275 II Nr. 4 HGB.

        ---

        #### 🎯 Operative Kalibrierung & Benchmarking ()
        Operative und variable Kostenannahmen reflektieren Mature-State-Basisfall-Werte mit Benchmarks gegen veröffentlichte Daten europäischer Mobilitätsbetreiber (Sixt+, Free Now, MOIA/Volkswagen Group, Waymo Phoenix). Durchsatzkalibrierung: **30-34 Fahrten/Tag pro Fahrzeug im Steady-State (J3+)**, aufgebaut aus 13,5h gemischter Werktag/Wochenend-produktiver Schicht, 19 km/h Münchner Durchschnittsgeschwindigkeit, 3,5 Min Standzeit pro Fahrt, 22% Leerfahrtenquote. Energie- und Verschleißkosten neu kalibriert auf **€0,085/km bzw. €0,10/km** — unter Waymo-Benchmarks wegen einfacherem Cybercab-Sensorstack und deutschen Arbeitskosten, über früheren optimistischen Schätzungen, die einer bankgerechten Due Diligence nicht standhielten. J1-J2 Ramp-State läuft unter den Mature-Zahlen; der **Dynamic Utilization Modus** des Engines (Standard) modelliert dies natürlich über Kannibalisierungs- und Erholungsmechanik. Für aggressive Bull-Case-Modellierung Sidebar-Inputs nach oben anpassen und Begründung separat dokumentieren.

        **Auslastungs-Rekalibrierung + Zwei-Strom-Erlöse:** Die ursprünglichen Auslastungsparameter (Init 35%, Erholung 3%/Monat, Kannibalisierungsfaktor 0,5) führten zu einem J5-Auslastungseinbruch — die Kannibalisierungsformel konnte sich zwischen Kohortenzugängen in J3-J5 nicht erholen. rekalibriert die vier Auslastungsparameter als koordiniertes Set: Init 55% (Preiselastizität + Novelty + Angebotskonzentration), Erholung 5%/Monat (entspricht J3-J5 Kohortenkadenz), Kannibalisierungsfaktor 0,35 (ausgereiftes Dispatching), Ziel 75% unverändert. Auf 24-Stunden-Kalendertag-Basis startet Monat 1 mit ~31% Asset-Auslastung und der reife Zustand in J5 liegt bei ~41% — konsistent mit veröffentlichten Uber NYC Marketplace-Daten reifer Märkte (38-42%). **B2B-Lieferdienst-Toggle (Standard AUS):** Tesla Network dispatched Cybercabs für Warenlieferungen in Schwachlast-Phasen mit identischer Dispatching-Architektur. Bei Aktivierung +4,5h aktive Stunden/Tag mit €6/Lieferung × 3 Lieferungen/Stunde × stufenweise Aktivierung (0/0/30/70/100% J1-J5). Konservativer Basisfall ist Personenverkehr; Lieferdienst-Toggle als "Upside-Layer" für volle 18h Tesla Network-Produktivität (75% 24h-Asset-Auslastung). Tesla steuert Dispatch-Priorität — Personenfahrten haben Vorrang. Inference-Rechenleistungs-Erlöse explizit aus dem Basisfall ausgeschlossen (Tesla-Programm noch nicht kommerziell verfügbar).

        **— Energie-Dekomposition + Kalibrierungs-Verfeinerungen + Anpassbare Saisonalität:** Sechs koordinierte Updates nach detaillierten CFO/CPA-Audit-Gesprächen. (1) **Energiekosten in 3 Slider zerlegt:** Verbrauch €0,115 kWh/km (verankert in Tesla-VP Lars Moravy Ankündigung 21. Mai 2026: Cybercab zertifiziert mit 165 Wh/mi = 0,103 kWh/km plus 12% Real-Aufschlag), Mischpreis €0,22/kWh (deutscher Großhandel Off-Peak €0,04-0,09 + Tesla Supercharger Off-Peak €0,31-0,46, gewichtet 70/30 Depot-Induktion / V4 kabelgebunden mit Flotten-Abo), Ladewirkungsgrad 0,94 (Teslas "deutlich über 90%" Induktion bei 22 kW × 0,70 + V4 kabelgebunden 96% × 0,30). Effektivrate kombiniert: €0,027/km ggü. zuvor €0,085 — 68% Reduktion reflektiert tatsächliche Cybercab-Effizienz. (2) **Versicherung €300 → €180/Monat** via Bottom-up: Diebstahl-Komponente ~€0 (Cybercab nicht fahrbar außerhalb Tesla Network, Waymo Phoenix 7J-Daten bestätigen), Tesla Insurance-Bundling-These (-15%), FSD-Sicherheitsbonus (70% Reduktion auf Personen-/Sachschadenshaftung), Restkategorien (Vandalismus €20, Batterie/Brand €20, Wetter €12, Passagierschäden €15, Cyber €40, Rechtsrücklage €30, P/S-Haftung post-FSD €55, PBefG €18) ≈ €210, abzüglich Tesla-Bundle-Rabatt und 5-Jahres-Mittelung = €180. (3) **APCOA Stellplatz €250 → €170/Monat** gem. veröffentlichten 2024 Münchner Monatsparkplätzen €120-180 + Ladefähigkeits-Aufschlag €40-80 abzüglich 15-25% J5 Mengenrabatt. (4) **Reinigung €3 → €2/Tag netto** unter Berücksichtigung von Teslas veröffentlichter Robotaxi-Reinigungsgebühr-Politik ($50 mittel / $150 schwer, live Dez 2025) — Bruttokosten ~€5/Tag Depot-Tiefenreinigung abzüglich ~€3/Tag Tesla-Gebühren-Erlöse. (5) **Aktive Stunden 13,5h → 16,0h** durch korrigierte Cybercab-Effizienz-Mathematik ermöglicht (geringerer kWh/km Verbrauch + 90%+ Induktions-Wirkungsgrad = keine Batteriekapazitäts-Beschränkung für verlängerte Schichten auch in Winter-Spitzenwochen). (6) **NEUE Frachtversicherung €20/Fahrzeug/Monat** Verkehrshaftungsversicherung, nur bei aktivem Lieferdienst-Toggle (deckt Frachtwert, Diebstahl im Transit, Wetterschäden — kein FSD-Sicherheitsbonus). (7) **NEUE anpassbare Monatssaisonalität:** 12 einzelne Monats-Slider im aufklappbaren Bereich ersetzen die zuvor hartcodierten 4 Stufen. Standardwerte erhalten Jahresmittel (1,2125×) — Dez/Jan/Feb 1,45, Nov/Mär 1,30, Apr/Okt 1,05, Mai-Sep 1,10. Nutzer können Winter-Aufschlags-Annahmen stresstesten (z.B. Tesla 4680 Trocken-Kathode reduziert Winter-Aufschlag um 10-15% ggü. 2170-Zellen). THG-Quote €200 → €280/Fahrzeug/Jahr gemäß 2024 deutschen Ist-Werten ebenfalls in diesem Layer enthalten.

        **Empirische Quellen:** TomTom Traffic Index 2024 (Münchner Verkehrsdichte); ADAC Wintertest 2023 + Geotab Flottenstudie (EV-Winterverbrauch); Waymo NHTSA-Meldungen (Sensorzuverlässigkeit, Standzeit, Ramp-Kurven); Sixt+ / Free Now / MOIA veröffentlichte Betreiberdaten (€/km Wartungs-Benchmarks); Uber/Lyft Marketplace-Blog (mature europäische Leerfahrtenquoten); Tesla Mai 2026 Model S/X SE Event (Cybercab 165 Wh/mi Zertifizierung); EPEX Spot 2025 deutsche Großhandels-Stromdaten (Off-Peak-Stunden €0,04-0,09/kWh); Tesla Supercharger-Preise Deutschland 2026 (€0,31-0,46/kWh Tesla Off-Peak); Tesla Robotaxi Reinigungsgebühren-Politik Dezember 2025 ($50/$150 Stufen).

        ---

        #### 📊 Verständnis der Auswertungen (Die Reiter)
        * **Gewinn- und Verlustrechnung (GuV):** Misst die buchhalterische Rentabilität. Oben stehen die Kundenbuchungen, unten bleiben EBITDA (operativer Gewinn vor Zinsen/Abschreibungen) und der Jahresüberschuss.
        * **Kapitalflussrechnung:** Die tatsächlichen Zahlungsströme auf Ihrem Bankkonto. Hier sehen Sie die CapEx-Mittelabflüsse, die Kreditaufnahmen und exakt, wann Sie Ihre Unternehmenssteuern zahlen.
        * **Bilanz:** Eine Momentaufnahme dessen, was das Unternehmen besitzt und wem es was schuldet. Achten Sie auf die **BILANZKONTROLLE** ganz unten. Sie beweist dynamisch, dass die Mathematik perfekt aufgeht, indem sie immer 0 € anzeigt.
        * **KPIs & Kennzahlen:** Die Kennzahlen, die Banken und Venture-Capital-Investoren heranziehen, um die Gesundheit Ihres Unternehmens zu beurteilen (wie DSCR und Liquiditätsreichweite).
        * **Visualisierungen & Dashboards:** Institutionelle Diagramme, die den Skalierungsverlauf zeigen. Wenn Sie den Free Cash Flow auf "Kumuliert" umstellen, sehen Sie die exakte "J-Kurve" Ihres Unternehmens.
        """)
