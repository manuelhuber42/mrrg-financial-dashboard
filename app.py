import streamlit as st
import pandas as pd
import numpy as np
import calendar
import plotly.graph_objects as go
import time

# --- GLOBAL MODELING CONSTANTS & FINANCIAL ARCHITECTURE ---
VAT_RATE = 0.19
# AfA period aligned to BMF AfA-Tabellen for Mietwagen/Taxi (intensive use).
# 60 months = 5 Jahre Nutzungsdauer per § 7 EStG. Loan term = 60 months TOTAL,
# structured as 12-month tilgungsfreie Anlaufzeit + 48 amortizing annuity payments
# ( fix: annuity sized over the 48 amortizing installments so the loan fully
# amortizes exactly at end of useful life — KfW Universell + commercial
# Kfz-Finanzierung both support this 1+4y structure).
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

# --- RESET TO DEFAULTS BUTTON ---
# This button restores every sidebar input to the default value declared in the
# code. Each sidebar widget carries an explicit key beginning with "sb_"; the
# callback below deletes those keys from session state, so on the next rerun every
# widget falls back to its declared default. The on_click callback runs before
# Streamlit's automatic rerun, so no explicit st.rerun is needed. The chosen
# language and any already-computed Monte Carlo results are preserved.
def _reset_sidebar_to_defaults():
    # Every sidebar input is registered in Streamlit's session state under a key
    # that starts with "sb_". Deleting those keys makes each widget re-read its
    # declared default `value=` on the next rerun, which is what actually resets
    # the inputs. (Simply clearing session state does NOT reset a widget that has
    # no key, which is why the earlier version of this button appeared to do
    # nothing.) The language selector ("lang_choice") and any Monte Carlo results
    # ("mc_results") are deliberately NOT prefixed with "sb_", so they survive a
    # reset — the user keeps their chosen language and their computed simulation.
    for _k in [k for k in list(st.session_state.keys()) if k.startswith("sb_")]:
        del st.session_state[_k]

st.sidebar.button(
    "🔄 Reset to default settings",
    on_click=_reset_sidebar_to_defaults,
    use_container_width=True,
    help="Restore every sidebar input back to the value declared in code. Preserves any Monte Carlo simulation results already computed in the Risk & Variance tab."
)
st.sidebar.divider()

# --- LANGUAGE DICTIONARY ---
lang_choice = st.sidebar.selectbox("Language / Sprache", ["English", "Deutsch"], key="lang_choice")

if lang_choice == "English":
    loc = {
        "title": "MRRG Cybercab Fleet: Master Financial Engine",
        "subtitle": "*(HGB-compliant 3-statement financial model — a 60-month cohort engine with an integrated Monte Carlo risk analysis)*",
        "sec1": "1a. FLEET SCALING SCHEDULE",
        "y1_adds": "Year 1 Additions (Jan-Dec)",
        "y2_adds": "Year 2 Additions (Jan-Dec)",
        "y3_adds": "Year 3 Additions (Jan-Dec)",
        "y4_adds": "Year 4 Additions (Jan-Dec)",
        "y5_adds": "Year 5 Additions (Jan-Dec)",
        "launch_delay": "Regulatory Launch Delay (months)",
        "help_launch_delay": "A stress lever that shifts the ENTIRE fleet-addition schedule right by N months while fixed HQ costs, one-off setup costs, and Y1 IT capex keep burning from month 1 with zero revenue — modeling the most probable real-world deviation for a Jan-2028 Cybercab launch: AFGBV Level-4 operating permission, EU type-approval/homologation, or Munich PBefG concession slippage. Additions pushed past the 60-month horizon are never purchased (no capex, no debt). 0 = launch on plan. A configured delay applies to BOTH the deterministic statements and every Monte Carlo run.",
        "sec1b": "1b. OPERATIONAL PHYSICS",
        "active_hours": "Active Hours / Day",
        "help_active_hours": "Blended weekly-average productive shift hours. Weekday 15h (sustained demand 6am-11pm minus brief charging/cleaning windows), weekend 18h (longer demand window 8am-2am next day, more lucrative late-night routes), blended weekly average ≈ 16h. Excludes the 2am-6am Tesla Robotaxi Network inductive charging window, which runs in parallel to depot return and onboard sensor cleaning (Cybercab spec, Cybertruck-derived) — eliminating the depot-cleaning shift penalty assumed in earlier Waymo-benchmark estimates. Onboard inductive charging + autonomous sensor cleaning shortens non-productive windows materially below the 13.5h benchmark used for human-driver fleets.",
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
        "help_init": "Month-1 launch utilization. 55% reflects three demand catalysts unique to MRRG's go-to-market: (a) price elasticity from 30-45% undercut vs. Uber/Free Now drives ~25-35% volume lift vs. mature-market launches (Cohen Uber/MIT 2016 elasticity studies), (b) novelty effect from first European Cybercab deployment generates PR-driven trial demand (Cruise SF early-week data showed >70% utilization spikes), (c) supply-constrained Month-1 fleet (3 cars) concentrated in 1-2 high-density zones (Maxvorstadt/Schwabing) operates at structurally higher utilization than market-scale operations. On 24h calendar basis this equals ~37% asset utilization (55% × 16h ÷ 24h).",
        "rec_rate": "Monthly Recovery (+%)",
        "help_rec": "How fast a car's utilization climbs back each month after a dip. New cars arrive in batches of 3-6 every quarter, and each batch briefly pulls utilization down while demand catches up; this is the speed of the recovery. 5% per month keeps utilization rising faster than new cars dilute it. This is in line with observed ride-hailing and robotaxi ramp-up data of roughly 4-6% per month during active fleet expansion.",
        "can_fac": "Cannibalization Factor",
        "help_can": "When new cars join the fleet they briefly compete with existing cars for the same riders. 0.35 means each new batch temporarily takes 35% of its capacity from existing cars' utilization, while the rest is genuinely new demand. A smart dispatch system with months of Munich demand data sends new cars to under-served areas rather than overlapping existing routes, which keeps this number moderate. 0.35 is in line with European fleet-expansion data showing 30-40% cannibalization during similar growth phases.",
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
        "help_delivery_hours": "Incremental productive hours per day when delivery stream is active. 4.0h fills low-passenger-demand windows (lunch 11am-2pm partial overlap, late-evening 10pm-1am, early-morning B2B 5-7am). Combined with the 16h passenger shift = 20h Tesla Network active per 24h day (83% 24h asset utilization), leaving a 4h overnight inductive charging window. Cross-field guardrail enforces active + delivery ≤ 20h.",
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
        "cleaning": "Cleaning cost per car / day (€, after passenger fees)",
        "cleaning_fee": "Passenger cleaning fees collected (€/day per car)",
        "help_cleaning_fee": "What this is: when a passenger leaves a Cybercab dirty, Tesla's in-cabin cameras automatically charge that passenger a cleaning fee and forward the money to MRRG. This field is how much of that fee income MRRG collects per car per day, averaged across all cars over a typical year. Why it is in the model: German accounting rules (the 'gross principle', Section 246 HGB) do not allow showing cleaning as a single small net figure. The full cleaning cost must appear as an expense, and the fees collected from passengers must appear separately as income, even though the two largely cancel out. This field adds that fee income as its own line so the accounts are presented correctly. It does not change profit, cash, or VAT: the extra expense it creates is exactly matched by the fee income added back. Set it to 0 if you would rather show cleaning as a single net cost.",
        "help_cleaning": "How much MRRG actually spends, per car per day, to keep a Cybercab clean — depot deep-cleaning, sensor-lens washer fluid, and odour treatment — after subtracting the cleaning fees collected from passengers who leave a car dirty (see the next field). In plain terms, this is the cleaning cost the company is left carrying once messy-passenger fees have covered their share. The default of €3/day per car reflects a mature operation. Dirty cars are sent to the depot during the overnight charging window, so cleaning never interrupts a paying shift.",
        "wear_rate": "Maintenance/Wear per km (€)",
        "wear_help": "Management-view levelized rate reflecting 4-5y vehicle scrap strategy (post-AfA exhaustion). Breakdown: tires €0.027, sensor maintenance €0.034 (Cybercab onboard cleaning reduces vs Waymo benchmark), body wear €0.012, fluids/suspension €0.005, HVAC/inspections €0.005, accident reserve €0.008, contingency €0.005. Benchmarked vs Sixt+, Free Now, MOIA published data. Below Waymo (€0.12-0.16) due to simpler Cybercab sensor stack and German labor rates.",
        # === Energy 3-slider build ===
        "energy_kwh": "Cybercab Consumption (kWh/km)",
        "help_energy_kwh": "Real-world Cybercab energy consumption at the wheel (kWh per km driven, including deadhead). Anchored on Tesla VP Lars Moravy's May 21, 2026 announcement at Model S/X SE event: Cybercab certified at 165 Wh/mile = 0.103 kWh/km (most efficient EV ever certified, 40% better than Model 3). Real-world urban operation typically adds 8-15% over EPA-style certified rating due to HVAC load, accessories, stop-and-go traffic, and elevation changes. **Default 0.115 kWh/km applies a 12% real-world derate.** Cybercab achieves this efficiency via: teardrop aerodynamics (Cd estimated <0.20), 2-seat layout (no rear seats/structure), no steering wheel/pedals/mirrors, narrower purpose-built tires, sub-50 kWh battery pack, and a smooth autonomous driving profile that avoids the energy waste of human-style acceleration/braking. Munich's mild urban grade (mostly flat) supports the lower end of the derate range.",
        "energy_eur": "Energy Price Blended (€/kWh)",
        "help_energy_eur": "Cost per kWh at the inductive charging pad. Cybercabs charge exclusively on Tesla's robotaxi network inductive pads during the 2am-6am low-demand window when German wholesale prices are at their cheapest. Bottom-up estimate of Tesla's pricing: (a) German wholesale spot 2am-6am consistently €0.06-0.10/kWh (EPEX day-ahead 00:00-04:00 CEST routinely the cheapest hours; Q1-2026 average ~€0.08), (b) Tesla bulk procurement contract likely at the low end, (c) Tesla's cost stack adds grid fees + EEG + Stromsteuer (€0.06-0.09), hardware amortization (€0.04-0.07), and target operating margin (€0.06-0.12). Bottom-up cost-to-Tesla: €0.18-0.28/kWh; Tesla's likely fleet rate: €0.24-0.32/kWh. Triangulation with observed Supercharger night rates (€0.26-0.32/kWh) provides a market ceiling — inductive should price BELOW this since it avoids dedicated DC fast charging hardware. **Default €0.27/kWh = center of defensible band.** Stress range: €0.24 (optimistic, aggressive Tesla penetration pricing) to €0.32 (conservative, Tesla extracts maximum margin) to €0.38 (adverse, energy crisis recurrence). Adjust based on bilateral negotiation outcomes with Tesla Energy team.",
        "charging_eff": "Charging Efficiency (0.50-1.00)",
        "help_charging_eff": "Energy delivered to battery as a fraction of energy drawn from the grid. Tesla has stated Cybercab inductive charging efficiency will be over 90%. We take a conservative stance and use 0.90 as the default.",
        "energy_derived_caption": "→ Derived Energy Cost: €{rate:.4f}/km (before seasonality)",
        # === Section 5 vehicle fixed costs ===
        "sec5": "5. VEHICLE FIXED COSTS (€ / Month, Net)",
        "insurance": "Insurance",
        "help_insurance": "What MRRG pays to insure each car per month. Built up from the parts: theft is near zero (a Cybercab cannot be driven outside the Tesla Network), with the premium instead covering vandalism (€20), battery/fire (€20), weather (€12), passenger damage (€15), cyber liability (€40), a legal reserve (€30), residual injury and property liability after the FSD safety credit (€55), and mandatory passenger-transport cover under PBefG (€18) — about €210, less a ~15% Tesla Insurance bundling discount and 5-year averaging, giving €180. The first year or two may run higher (€250-300) until Munich claims history builds up. Risk: if Tesla's own insurer is delayed and MRRG must buy standard German third-party cover, the premium could rise to €280-350.",
        "parking": "APCOA Charging Capable Space (Munich)",
        "help_parking": "Monthly cost of a charging-capable parking space per car. Published 2024 Munich rates are €120-180 for parking plus a €40-80 charging premium (€160-220 in the middle). At a Year-5 fleet of 57 cars, a 15-25% bulk discount brings this down to €140-180; €170 is the midpoint of a negotiable fleet rate. Includes access to the inductive charging pad at depot locations — wired charging is not used in robotaxi operations.",
        "telemetry": "Telemetry & API",
        "tuev": "TÜV / BO-Kraft Accrual",
        "help_tuev": "Monthly accrual for mandatory passenger transport inspections.",
        "charging_sub": "Tesla Charging Sub",
        "cargo_ins": "Cargo Insurance (Verkehrshaftungsversicherung)",
        "help_cargo_ins": "Mandatory transport-liability insurance, charged only when the B2B delivery stream is switched on. It covers the value of goods carried, theft in transit, weather damage, and handling claims — risks that do not depend on driving behaviour, so they get no FSD safety credit. €20 per car per month reflects 2024 German rates for low-value parcel and food courier work. Billed only while delivery is active.",
        # === Monthly seasonality multipliers (12 months adjustable) ===
        "sec_season": "1d. SEASONAL ENERGY MODIFIER",
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
        "sh_rangruecktritt": "SH loan with Rangrücktritt (treat as economic equity for KPIs)",
        "help_rangruecktritt": "Toggle ON when the shareholder loan is formally subordinated via a notarized Rangrücktrittserklärung — standard under KfW Universell covenants and required to avoid Eigenkapitalersatz-Risiko under §§ 39, 135 InsO. With Rangrücktritt, banks treat the SH loan as Eigenkapital-Ersatz für die Kreditwürdigkeitsprüfung (economic equity for creditworthiness). Effect: SH loan moves from financial debt to equity in Equity Ratio + Net LTV KPI computations ONLY. Engine numbers, balance sheet line items, and HGB statutory P&L are UNCHANGED — this is purely a bank-style economic recharacterization.",
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
        "hebesatz": "Gewerbesteuer-Hebesatz (%)",
        "help_hebesatz": (
            "**Municipal trade tax multiplier (Hebesatz) applied to the federal Gewerbesteuer base rate of 3.5% per § 16 GewStG.** "
            "Default 250% reflects Gräfelfing (Landkreis München), one of the most tax-attractive municipalities in the Munich metropolitan area — significantly below Munich City (490%), Pullach (240% as of 2025), Unterföhring (295%), Bayern average (~360%), and Berlin (410%). "
            "Verified via Statistisches Landesamt Bayern 2024 Hebesatzliste.\n\n"
            "**Combined corporate tax methodology used in this engine** (§ 23 KStG n.F. + § 4 SolzG + § 16 GewStG):\n\n"
            "Total Tax Rate = KSt × (1 + 5.5% Soli) + 3.5% × (Hebesatz / 100)\n\n"
            "**KSt declining schedule per Wachstumsbooster-Gesetz** (in Kraft seit 19.07.2025, § 23 Abs. 1 KStG n.F.) — annual 1pp reduction starting VZ 2028:\n"
            "• Y1 (2028): 14%  •  Y2 (2029): 13%  •  Y3 (2030): 12%  •  Y4 (2031): 11%  •  Y5 (2032): 10%\n\n"
            "**At default 250% Hebesatz, total combined effective rate by year:**\n"
            "• Y1: 23.52%  •  Y2: 22.47%  •  Y3: 21.41%  •  Y4: 20.36%  •  Y5: 19.30%\n\n"
            "Sources: BMF Wachstumsbooster portal, IHK München, EY Tax Law Magazine, BDO Insights, Bird & Bird tax analysis (all confirm 5-step KSt reduction 15%→10% over VZ 2028-2032). "
            "Adjust this slider to model alternative locations or stress-test the Hebesatz assumption. The engine auto-rebuilds the 5-year tax schedule each time the value changes — no hardcoded numbers downstream."
        ),
        "sec9": "9. OTHER INCOME / SALVAGE",
        "thg": "THG Quote per vehicle/yr",
        "help_thg": "The net amount (after VAT) that MRRG keeps per car per year from selling its Greenhouse-Gas (THG) reduction quota. Because MRRG is a business, the quota sale is subject to VAT: the model adds 19% output VAT through the monthly VAT return when the income is earned and collects the gross amount at the quarterly settlement with the quota buyer. The THG quota (§ 7 Abs. 1 38. BImSchV) is a flat yearly payment per registered electric vehicle, paid in full no matter when in the year the car was registered, as long as it is registered before the 15 November deadline; cars registered in Nov-Dec roll into the following January. Default €280 reflects 2024 German market levels (range €150-450 by provider); future pricing is volatile. Sources: ADAC, EnBW, Finanztip, Klima-Quote, elektrovorteil.",
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
        "pnl_clean_fee": "Add: Cleaning Fee Pass-Through (Section 246 II HGB)",
        "pnl_thg": "Add: THG Quote (Other Operating Income)",
        "pnl_ebitda": "EBITDA (Management View)",
        "pnl_ebitda_hgb": "EBITDA (HGB View, incl. Anlagenabgang per § 275 II Nr.4 HGB)",
        "pnl_afa_veh": "Less: Vehicle Depreciation (AfA)",
        "pnl_afa_it": "Less: IT Hardware Depreciation (AfA)",
        "pnl_salvage": "Add: Fleet Liquidation (Asset Sale)",
        "pnl_ebit": "EBIT (Operating Income)",
        "pnl_int_inc": "Add: Interest Income (Zinserträge)",
        "pnl_int_exp": "Less: Interest Expense (Loans & Overdraft)",
        "pnl_int_exp_sh": "  ↳ Memo: Shareholder Loan Interest (subset of above)",
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
        "bs_kap_ruecklage": "Capital Reserves (Kapitalrücklage § 272 II Nr. 4)",
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
        "tab_ops": "🚗 Vehicle & Operational KPIs",
        "ops_header": "Vehicle & Operational KPIs",
        "ops_caption": "Per-vehicle, per-kilometre and per-trip operating metrics derived directly from the simulation — the unit economics underneath the financial statements. Columns follow the same monthly / yearly view as the other tabs (use the year toggles above to drill into months).",
        "ops_total_km": "Total km driven (fleet)",
        "ops_billable_km": "Loaded km (carrying a passenger / goods)",
        "ops_deadhead_km": "Empty km (deadhead repositioning)",
        "ops_deadhead_ratio": "Deadhead ratio (empty / total)",
        "ops_pax_trips": "Passenger trips",
        "ops_delivery_trips": "Delivery trips",
        "ops_km_per_veh": "Km per vehicle (in the period)",
        "ops_trips_per_veh": "Trips per vehicle (in the period)",
        "ops_avg_fleet": "Average active vehicles",
        "ops_netrev_veh": "Net revenue per vehicle",
        "ops_ebitda_veh": "EBITDA per vehicle",
        "ops_rev_km": "Net revenue per km",
        "ops_gbv_km": "Gross fare per km (incl. VAT)",
        "ops_energy_km": "Energy cost per km",
        "ops_wear_km": "Maintenance / wear per km",
        "ops_clean_km": "Cleaning cost per km (net)",
        "ops_varcost_km": "Total variable cost per km",
        "ops_contrib_km": "Contribution per km (revenue - variable cost)",
        "ops_rev_trip": "Net revenue per trip",
        "ops_energy_kwh": "Energy consumed (kWh, nameplate)",
        "ops_m_total_km": "Lifetime km driven (5Y)",
        "ops_m_km_veh_day": "Km per vehicle / day (realized)",
        "ops_m_deadhead": "Deadhead ratio (5Y)",
        "ops_m_rev_km": "Net revenue per km (5Y)",
        "ops_chart_total_km": "Total km driven per year",
        "ops_chart_km_veh": "Km per vehicle per year",
        "tab_readme": "README & User Manual",
        # === Monte Carlo Risk & Variance Analysis ===
        "tab_mc": "🎲 Risk & Variance Analysis (Monte Carlo)",
        "mc_header": "Risk & Variance Analysis — Stochastic Monte Carlo",
        "mc_intro": "This module wraps the deterministic 60-month engine in a Monte Carlo simulation. On each of the N runs, the model re-draws its full set of variance-driving inputs — operating physics, pricing, capital and financing costs, and operating costs — together with a shared year-by-year economic (macro) factor, a six-way mix of day types, and eight categories of one-off disruption events, each from an empirically-anchored probability distribution. The deterministic central case shown in the other tabs is never changed; this is a supplementary risk analysis for bank credit committees and project-finance review.",
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
        # === Capital Structure & Fleet Financing Matrix ===
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
        # === / macro coupling controls ===
        "mc_macro_header": "🌍 Macro Coupling — correlated crisis engine",
        "mc_macro_help": "A single shared macro-environment factor is drawn once per simulated YEAR. A positive draw represents a crisis year; it pushes energy prices UP, loan rates UP, and customer demand DOWN — all together, in the same year. Each year's factor is injected directly into that year's months of the 60-month ledger, so a single catastrophic year collapses cash in real time. Set the betas below to control how strongly each variable reacts. Set all betas to 0 to recover fully-independent behavior.",
        "mc_beta_energy": "Energy sensitivity βₑ (€/kWh per +1σ crisis)",
        "mc_beta_rate": "Loan-rate sensitivity βᵣ (rate pp per +1σ crisis)",
        "mc_beta_demand": "Demand sensitivity β_d (util pts per +1σ crisis)",
        "mc_beta_fx": "FX sensitivity β_fx (EUR weakening per +1σ crisis)",
        "mc_macro_sigma": "Macro shock σ (annual volatility, 1.0 = standard)",
        "mc_shock_demand_collapse": "Demand Collapse (pandemic/lockdown)",
        # === dynamic narrative panel ===
        "mc_narr_header": "🧭 What these results mean (plain-language read-out)",
        "mc_narr_caption": "This explanation is generated from the actual numbers your simulation just produced and from your current sidebar settings. It updates every time you re-run or change inputs.",
        "mc_narr_profit_h": "**The profit picture.**",
        "mc_narr_survival_h": "**The survival picture (the one that matters most).**",
        "mc_narr_drivers_h": "**What actually drives your fate.**",
        "mc_narr_implication_h": "**Implication for the business.**",
        # === simulation provenance panel (surfaces simulation_settings) ===
        "mc_provenance_header": "🧾 Simulation Provenance & Settings (reproducibility)",
        "mc_provenance_caption": "The exact inputs behind the percentile tables above — iteration count, RNG seed, macro-coupling betas, and every baseline center the simulation sampled around. Captured so any Monte Carlo run is fully reproducible and auditable by a bank credit committee.",

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
        "kpi_dscr": "Debt Service Coverage Ratio (DSCR — total)",
        "kpi_dscr_senior": "Senior DSCR (bank debt only, ex-shareholder loan)",
        "kpi_dscr_senior_help": "Bank-standard DSCR using SENIOR debt service only — KfW/commercial Kfz loan principal+interest plus Kontokorrent interest, EXCLUDING shareholder-loan interest. Subordinated shareholder loans function as economic equity for credit purposes (most KfW Universell facilities require formal Rangrücktritt). Including SH interest in the denominator artificially understates the bank-relevant DSCR — this row shows the metric the credit committee actually computes.",
        "kpi_fccr": "Fixed-Charge Coverage Ratio (FCCR — lease-adjusted)",
        "kpi_fccr_help": "Bank-grade lease-adjusted coverage metric: (EBITDA + Lease Expense) / (Principal + Interest + Lease Expense). Operating lease commitments are non-discretionary contractual obligations economically identical to senior debt service — bank credit committees compute this internally even though German GAAP does not require lease capitalization (unlike IFRS 16). FCCR is the right metric when comparing capital structures with different loan/lease mixes. Target: >1.5× for senior debt covenants; >2.0× for strong rating.",
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
        "err_init_util": "❌ **Input conflict:** Month-1 Launch Utilization ({init:.0f}%) cannot exceed Target Utilization ({target:.0f}%). The init-utilization is the *starting point* on the ramp-up curve; the target is the *mature-state ceiling*. Please lower init or raise target before continuing.",
        "err_combined_hours": "❌ **Operational ceiling breached:** Active Hours/Day ({active:.1f}h) + Delivery Hours/Day ({delivery:.1f}h) = {total:.1f}h exceeds the 20h/day operational ceiling. The remaining 4+ hours of the 24h calendar day are required for inductive overnight charging, sensor cleaning, and depot maintenance windows. Reduce one of the two hour inputs.",
        "net_liq_warn": "⚠️  Net Liquidity Negative (Cash − Overdraft < Min Buffer) in month: ",
        "insolv_warn": "💀 INSOLVENCY: Required cash shortfall exceeds the bank-approved overdraft ceiling in month: ",
        "legal_insolv_warn": "⚖️ § 15a InsO ANTRAGSPFLICHT: 3+ consecutive months of unfunded shortfall first triggered in month: ",
        "insolv_severity_label": "Total cumulative unfunded shortfall over breach period",
        "insolv_diagnostic_note": "Note: simulation continues past the legal insolvency trigger for diagnostic visibility into the cash recovery path. In real operations, the Geschäftsführung would be legally required to file an Insolvenzantrag within 3 weeks of Zahlungsunfähigkeit per § 15a InsO. Use this disclosure to size additional equity/debt required to maintain going-concern status.",
        "ebitda_recon_title": "EBITDA Reconciliation Bridge (Mgmt View → HGB View)",
        "ebitda_recon_caption": "Management EBITDA is operations-only. The HGB view adds end-of-life fleet disposal gains recognised as sonstige betriebliche Erträge under § 275 Abs. 2 Nr. 4 HGB. The bridge foots exactly: Mgmt EBITDA + Anlagenabgang = HGB EBITDA."
    }
else:
    loc = {
        "title": "MRRG Cybercab-Flotte: Master-Finanzmodell",
        "subtitle": "*(HGB-konformes 3-Statement-Finanzmodell — eine 60-Monats-Kohorten-Engine mit integrierter Monte-Carlo-Risikoanalyse)*",
        "sec1": "1a. FLOTTENSKALIERUNG",
        "y1_adds": "Jahr 1 Zugänge (Jan-Dez)",
        "y2_adds": "Jahr 2 Zugänge (Jan-Dez)",
        "y3_adds": "Jahr 3 Zugänge (Jan-Dez)",
        "y4_adds": "Jahr 4 Zugänge (Jan-Dez)",
        "y5_adds": "Jahr 5 Zugänge (Jan-Dez)",
        "launch_delay": "Regulatorische Launch-Verzögerung (Monate)",
        "help_launch_delay": "Ein Stress-Hebel, der den GESAMTEN Flottenzugangsplan um N Monate nach hinten, während fixe HQ-Kosten, einmalige Gründungskosten und J1-IT-Capex ab Monat 1 ohne Umsatz weiterlaufen — das wahrscheinlichste reale Abweichungsszenario für einen Cybercab-Start Jan 2028: AFGBV-Level-4-Betriebserlaubnis, EU-Typgenehmigung/Homologation oder Münchner PBefG-Konzession. Über den 60-Monats-Horizont hinausgeschobene Zugänge werden nie gekauft (kein Capex, keine Schulden). 0 = Start nach Plan. Eine konfigurierte Verzögerung gilt für die deterministischen Statements UND jeden Monte-Carlo-Lauf.",
        "sec1b": "1b. OPERATIVE PHYSIK",
        "active_hours": "Aktive Stunden / Tag",
        "help_active_hours": "Gemischter Wochendurchschnitt produktiver Schichtstunden. Werktag 15h (Nachfrage 6-23 Uhr abzüglich kurzer Lade-/Reinigungsfenster), Wochenende 18h (längeres Nachfragefenster 8-2 Uhr Folgetag, lukrativere Nachtstrecken), gemischter Wochendurchschnitt ≈ 16h. Ausgeschlossen ist das 2-6 Uhr Tesla Robotaxi-Netzwerk-Induktionsladefenster, das parallel zur Depotrückkehr und autonomen Sensorreinigung läuft (Cybercab Spec, Cybertruck-abgeleitet) — entfällt die Depot-Reinigungsschicht älterer Waymo-Benchmark-Schätzungen. Induktivladen + autonome Sensorreinigung verkürzen die unproduktiven Fenster wesentlich unter den 13,5h-Benchmark menschengeführter Flotten.",
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
        "help_init": "Auslastung Monat 1. 55% reflektiert drei nachfragetreibende Faktoren der MRRG Go-to-Market: (a) Preiselastizität durch 30-45% Unterbietung von Uber/Free Now bewirkt ~25-35% Mehrvolumen ggü. preisgleichen Launches (Cohen Uber/MIT 2016 Elastizitätsstudien), (b) Novelty-Effekt durch ersten europäischen Cybercab-Launch erzeugt PR-getriebene Probefahrtnachfrage (Cruise SF Frühwochen-Daten >70% Auslastungsspitzen), (c) versorgungsbeschränkte Startflotte (3 Fahrzeuge) konzentriert in 1-2 Hochdichtezonen (Maxvorstadt/Schwabing) operiert strukturell höher als marktbreite Operationen. Auf 24h-Kalenderbasis entspricht dies ~37% Asset-Auslastung (55% × 16h ÷ 24h).",
        "rec_rate": "Monatliche Erholung (+%)",
        "help_rec": "Wie schnell die Auslastung eines Fahrzeugs nach einem Einbruch monatlich wieder steigt. Neue Fahrzeuge kommen vierteljährlich in Tranchen von 3-6 hinzu, und jede Tranche drückt die Auslastung kurz nach unten, bis die Nachfrage nachzieht; dies ist das Tempo der Erholung. 5% pro Monat halten die Auslastung schneller steigend, als neue Fahrzeuge sie verdünnen. Das entspricht beobachteten Ride-Hailing- und Robotaxi-Hochlaufdaten von etwa 4-6% pro Monat während aktiver Flottenexpansion.",
        "can_fac": "Kannibalisierungsfaktor",
        "help_can": "Wenn neue Fahrzeuge zur Flotte stoßen, konkurrieren sie kurzzeitig mit bestehenden Fahrzeugen um dieselben Fahrgäste. 0,35 bedeutet, dass jede neue Tranche vorübergehend 35% ihrer Kapazität von der Auslastung bestehender Fahrzeuge abzieht; der Rest ist echte Zusatznachfrage. Ein intelligentes Dispatching mit monatelangen Münchner Nachfragedaten schickt neue Fahrzeuge in unterversorgte Gebiete statt bestehende Routen zu überlappen, was diesen Wert moderat hält. 0,35 entspricht europäischen Flottenexpansionsdaten mit 30-40% Kannibalisierung in vergleichbaren Wachstumsphasen.",
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
        "help_delivery_hours": "Inkrementelle produktive Stunden pro Tag bei aktivem Lieferstrom. 4,0h füllen Schwachlast-Fenster (Mittag 11-14 Uhr Teilüberlapp, Spätabend 22-1 Uhr, Frühmorgen B2B 5-7 Uhr). Kombiniert mit der 16h Personenschicht = 20h Tesla Network aktiv pro 24h-Tag (83% 24h-Asset-Auslastung), mit 4h Nacht-Induktivladefenster. Querfeld-Guardrail erzwingt aktive + Lieferstunden ≤ 20h.",
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
        "cleaning": "Reinigungskosten pro Fahrzeug / Tag (€, nach Fahrgastgebühren)",
        "cleaning_fee": "Eingenommene Fahrgast-Reinigungsgebühren (€/Tag pro Fahrzeug)",
        "help_cleaning_fee": "Worum es geht: Wenn ein Fahrgast einen Cybercab verschmutzt hinterlässt, berechnet Teslas Innenraumkamera-System diesem Fahrgast automatisch eine Reinigungsgebühr und leitet das Geld an MRRG weiter. Dieses Feld ist der Betrag dieser Gebühreneinnahmen pro Fahrzeug und Tag, über alle Fahrzeuge eines typischen Jahres gemittelt. Warum es im Modell ist: Das deutsche Bruttoprinzip (§ 246 HGB) erlaubt es nicht, die Reinigung als eine einzige kleine Nettozahl auszuweisen. Die vollen Reinigungskosten müssen als Aufwand und die von Fahrgästen eingenommenen Gebühren getrennt als Ertrag erscheinen, auch wenn sich beide weitgehend ausgleichen. Dieses Feld fügt die Gebühreneinnahme als eigene Zeile hinzu, damit die Buchhaltung korrekt dargestellt ist. Es ändert weder Gewinn noch Cash noch USt: Der zusätzliche Aufwand wird exakt durch die hinzugerechnete Gebühreneinnahme ausgeglichen. Auf 0 setzen, um die Reinigung als einzelne Nettokosten zu zeigen.",
        "help_cleaning": "Wie viel MRRG tatsächlich pro Fahrzeug und Tag ausgibt, um einen Cybercab sauber zu halten — Depot-Tiefenreinigung, Sensor-Waschflüssigkeit und Geruchsbehandlung — nach Abzug der Reinigungsgebühren, die von Fahrgästen eingenommen werden, die ein Fahrzeug verschmutzt hinterlassen (siehe nächstes Feld). Klartext: Dies sind die Reinigungskosten, die dem Unternehmen verbleiben, nachdem die Gebühren verschmutzender Fahrgäste ihren Anteil gedeckt haben. Der Standardwert von €3/Tag pro Fahrzeug entspricht einem eingespielten Betrieb. Verschmutzte Fahrzeuge fahren während des nächtlichen Ladefensters zum Depot, sodass die Reinigung nie eine bezahlte Schicht unterbricht.",
        "wear_rate": "Instandhaltung/Verschleiß pro km (€)",
        "wear_help": "Management-Sicht: nivellierter Verschleißsatz für 4-5j Scrap-Strategie (nach AfA-Schild). Aufschlüsselung: Reifen €0,027, Sensorwartung €0,034 (Cybercab Onboard-Reinigung reduziert ggü. Waymo-Benchmark), Innenraumverschleiß €0,012, Flüssigkeiten/Fahrwerk €0,005, HVAC/Inspektionen €0,005, Unfallrückstellung €0,008, Reserve €0,005. Benchmarks: Sixt+, Free Now, MOIA. Unter Waymo (€0,12-0,16) wegen einfacherem Cybercab-Sensorstack und deutschen Arbeitskosten.",
        # === Energie 3-Slider-Aufbau ===
        "energy_kwh": "Cybercab Verbrauch (kWh/km)",
        "help_energy_kwh": "Realer Cybercab-Energieverbrauch am Rad (kWh pro gefahrenem km, inkl. Leerfahrten). Verankert in der Ankündigung von Tesla-VP Lars Moravy am 21. Mai 2026 beim Model S/X SE Event: Cybercab zertifiziert mit 165 Wh/Meile = 0,103 kWh/km (effizientestes EV aller Zeiten, 40% besser als Model 3). Real-Verbrauch im Stadtverkehr typisch 8-15% über EPA-Zertifizierung wegen HVAC-Last, Verbrauchern, Stop-and-Go-Verkehr und Höhenmetern. **Standard 0,115 kWh/km wendet 12% Real-Aufschlag an.** Cybercab erreicht diese Effizienz durch: Tropfenform-Aerodynamik (Cd geschätzt <0,20), 2-Sitzer-Layout (keine Rücksitze/Struktur), kein Lenkrad/Pedale/Spiegel, schmalere Spezial-Reifen, Sub-50 kWh-Batterie und ein sanftes autonomes Fahrprofil ohne menschliches Beschleunigen/Bremsen. Münchens flacher urbaner Gradient unterstützt das untere Ende der Aufschlagsspanne.",
        "energy_eur": "Energie-Mischpreis (€/kWh)",
        "help_energy_eur": "Kosten pro kWh an der induktiven Ladepad. Cybercabs laden ausschließlich auf Teslas Robotaxi-Netzwerk-Induktionspads im 2-6 Uhr Niedrigtarif-Fenster, wenn deutsche Großhandelspreise am günstigsten sind. Bottom-up-Schätzung der Tesla-Preise: (a) deutscher Großhandels-Spot 2-6 Uhr konstant €0,06-0,10/kWh (EPEX Day-Ahead 00:00-04:00 CEST regelmäßig die günstigsten Stunden; Q1-2026 Ø ~€0,08), (b) Tesla-Großmengen-Beschaffung wahrscheinlich am unteren Ende, (c) Tesla-Kostenstack zzgl. Netzentgelte + EEG + Stromsteuer (€0,06-0,09), Hardware-Amortisation (€0,04-0,07), Zielmarge (€0,06-0,12). Bottom-up Tesla-Kosten: €0,18-0,28/kWh; wahrscheinlicher Flottensatz: €0,24-0,32/kWh. Triangulation mit beobachteten Supercharger-Nachttarifen (€0,26-0,32/kWh) liefert Marktobergrenze — induktiv sollte UNTER diesem Wert preisen, da keine dedizierte DC-Schnelllade-Hardware benötigt wird. **Standard €0,27/kWh = Mitte des vertretbaren Bandes.** Stress-Bereich: €0,24 (optimistisch, Tesla aggressive Penetrationsstrategie) bis €0,32 (konservativ, Tesla maximiert Marge) bis €0,38 (negativ, Energiekrise-Rezidiv). Je nach bilateralen Verhandlungsergebnissen mit Tesla Energy anpassen.",
        "charging_eff": "Ladewirkungsgrad (0,50-1,00)",
        "help_charging_eff": "Energie in den Akku als Bruchteil der aus dem Netz bezogenen Energie. Tesla hat angegeben, dass die Cybercab-Induktivladeeffizienz über 90% liegen wird. Wir gehen konservativ vor und verwenden 0,90 als Standardwert.",
        "energy_derived_caption": "→ Abgeleitete Energiekosten: €{rate:.4f}/km (vor Saisonalität)",
        # === Abschnitt 5 Fixkosten — Versicherung/Stellplatz rekalibriert ===
        "sec5": "5. FAHRZEUG-FIXKOSTEN (€ / Monat, Netto)",
        "insurance": "Kfz-Versicherung",
        "help_insurance": "Was MRRG pro Fahrzeug und Monat für die Versicherung zahlt. Von Grund auf aufgebaut: Diebstahl ist nahezu null (ein Cybercab ist außerhalb des Tesla Network nicht fahrbar); die Prämie deckt stattdessen Vandalismus (€20), Batterie/Brand (€20), Wetter (€12), Passagierschäden (€15), Cyber-Haftung (€40), eine Rechtsrücklage (€30), Rest-Personen- und Sachschadenshaftung nach dem FSD-Sicherheitsbonus (€55) und die gesetzliche Passagiertransport-Deckung gem. PBefG (€18) — rund €210, abzüglich ~15% Tesla-Insurance-Bündelrabatt und 5-Jahres-Mittelung, ergibt €180. Die ersten ein bis zwei Jahre können höher liegen (€250-300), bis sich Münchner Schadensdaten aufbauen. Risiko: Verzögert sich Teslas eigene Versicherung und MRRG muss eine normale deutsche Haftpflicht abschließen, könnte die Prämie auf €280-350 steigen.",
        "parking": "Münchner Stellplatz (APCOA Lade-Infrastruktur)",
        "help_parking": "Monatliche Kosten eines ladefähigen Stellplatzes pro Fahrzeug. Veröffentlichte Münchner Tarife 2024 liegen bei €120-180 fürs Parken plus €40-80 Ladeaufschlag (€160-220 in der Mitte). Bei einer J5-Flotte von 57 Fahrzeugen senkt ein Mengenrabatt von 15-25% dies auf €140-180; €170 ist der Mittelpunkt eines verhandelbaren Flottentarifs. Beinhaltet den Zugang zum induktiven Ladepad an Depotstandorten — kabelgebundenes Laden wird im Robotaxi-Betrieb nicht verwendet.",
        "telemetry": "Telemetrie & API",
        "tuev": "TÜV / BO-Kraft Rückstellung",
        "help_tuev": "Monatliche Rückstellung für die BO-Kraft Untersuchung.",
        "charging_sub": "Tesla Lade-Abo",
        "cargo_ins": "Verkehrshaftungsversicherung (Frachtgut)",
        "help_cargo_ins": "Gesetzliche Transporthaftpflicht, nur berechnet, wenn der B2B-Lieferdienst eingeschaltet ist. Sie deckt den Wert der beförderten Güter, Diebstahl während des Transports, Wetterschäden und Handhabungsansprüche — Risiken, die nicht vom Fahrverhalten abhängen und daher keinen FSD-Sicherheitsbonus erhalten. €20 pro Fahrzeug und Monat entspricht deutschen Tarifen 2024 für niedrigwertige Paket- und Food-Kurierdienste. Nur fakturiert, solange der Lieferdienst aktiv ist.",
        # === Monatliche Saisonalitäts-Multiplikatoren ===
        "sec_season": "1d. SAISONALER ENERGIE-MODIFIKATOR",
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
        "sh_rangruecktritt": "Gesellschafterdarlehen mit Rangrücktritt (KPI-seitig als wirtschaftliches EK)",
        "help_rangruecktritt": "Aktivieren, wenn das Gesellschafterdarlehen formal über eine notarielle Rangrücktrittserklärung subordiniert ist — Standard bei KfW-Universell-Auflagen und erforderlich zur Vermeidung von Eigenkapitalersatz-Risiken gem. §§ 39, 135 InsO. Mit Rangrücktritt behandeln Banken das Gesellschafterdarlehen kreditseitig als Eigenkapital-Ersatz für die Kreditwürdigkeitsprüfung. Wirkung: Gesellschafterdarlehen verschiebt sich von Finanzverbindlichkeit zu Eigenkapital NUR bei Eigenkapitalquote- und Netto-LTV-Berechnung. Engine-Zahlen, Bilanzposten und gesetzliche HGB-GuV bleiben UNVERÄNDERT — rein bankseitige wirtschaftliche Umklassifikation.",
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
        "hebesatz": "Gewerbesteuer-Hebesatz (%)",
        "help_hebesatz": (
            "**Kommunaler Gewerbesteuer-Hebesatz auf den Steuermessbetrag gem. § 16 GewStG (Basis: 3,5%).** "
            "Standardwert 250% reflektiert Gräfelfing (Landkreis München), eine der steuerlich attraktivsten Gemeinden im Münchner Großraum — deutlich unter München-Stadt (490%), Pullach (240% Stand 2025), Unterföhring (295%), Bayern-Durchschnitt (~360%) und Berlin (410%). "
            "Verifiziert über Statistisches Landesamt Bayern 2024 Hebesatzliste.\n\n"
            "**Kombinierte Körperschaftsteuer-Methodik dieser Engine** (§ 23 KStG n.F. + § 4 SolzG + § 16 GewStG):\n\n"
            "Gesamt-Steuersatz = KSt × (1 + 5,5% Soli) + 3,5% × (Hebesatz / 100)\n\n"
            "**KSt-Senkungsplan gem. Wachstumsbooster-Gesetz** (in Kraft seit 19.07.2025, § 23 Abs. 1 KStG n.F.) — jährliche 1pp-Reduktion ab VZ 2028:\n"
            "• J1 (2028): 14%  •  J2 (2029): 13%  •  J3 (2030): 12%  •  J4 (2031): 11%  •  J5 (2032): 10%\n\n"
            "**Bei Standard-Hebesatz 250% — kombinierter Effektivsteuersatz pro Jahr:**\n"
            "• J1: 23,52%  •  J2: 22,47%  •  J3: 21,41%  •  J4: 20,36%  •  J5: 19,30%\n\n"
            "Quellen: BMF Wachstumsbooster-Portal, IHK München, EY Tax Law Magazine, BDO Insights, Bird & Bird Steueranalyse (alle bestätigen 5-stufige KSt-Senkung 15%→10% über VZ 2028-2032). "
            "Schieberegler anpassen, um alternative Standorte zu modellieren oder die Hebesatz-Annahme zu stress-testen. Die Engine rekalkuliert den 5-Jahres-Steuerplan automatisch bei jeder Änderung — keine hardcoded Werte stromabwärts."
        ),
        "sec9": "9. SONSTIGE ERTRÄGE / RESTWERT",
        "thg": "THG-Quote pro Fahrzeug/Jahr",
        "help_thg": "Der Nettobetrag (nach USt), den MRRG pro Fahrzeug und Jahr aus dem Verkauf seiner Treibhausgas-(THG-)Minderungsquote behält. Da MRRG ein Unternehmen ist, ist der Quotenverkauf umsatzsteuerpflichtig: Das Modell führt 19% Umsatzsteuer über die monatliche Voranmeldung bei Entstehung ab und vereinnahmt den Bruttobetrag bei der quartalsweisen Abrechnung mit dem Quotenkäufer. Die THG-Quote (§ 7 Abs. 1 38. BImSchV) ist eine jährliche Pauschalzahlung pro zugelassenem Elektrofahrzeug, voll ausgezahlt unabhängig vom Zulassungszeitpunkt im Jahr, sofern die Zulassung vor dem Stichtag 15. November erfolgt; im Nov-Dez zugelassene Fahrzeuge verschieben sich auf den Folgejahr-Januar. Standard €280 entspricht deutschen Marktwerten 2024 (Bandbreite €150-450 je nach Anbieter); künftige Preise sind volatil. Quellen: ADAC, EnBW, Finanztip, Klima-Quote, elektrovorteil.",
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
        "pnl_clean_fee": "Zuzüglich: Reinigungsgebühren-Durchleitung (§ 246 II HGB)",
        "pnl_thg": "Zuzüglich: THG-Quote (Sonstige betriebliche Erträge)",
        "pnl_ebitda": "EBITDA (Management View)",
        "pnl_ebitda_hgb": "EBITDA (HGB-Sicht, inkl. Anlagenabgang gem. § 275 II Nr.4 HGB)",
        "pnl_afa_veh": "Abzüglich: Abschreibung Fahrzeuge (AfA)",
        "pnl_afa_it": "Abzüglich: Abschreibung IT Hardware (AfA)",
        "pnl_salvage": "Zuzüglich: Flottenliquidation (Anlagenverkauf)",
        "pnl_ebit": "EBIT (Betriebsergebnis)",
        "pnl_int_inc": "Zuzüglich: Zinserträge",
        "pnl_int_exp": "Abzüglich: Zinsaufwendungen (Kredite & Überzug)",
        "pnl_int_exp_sh": "  ↳ Memo: Gesellschafterdarlehen-Zinsen (Teilmenge von oben)",
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
        "bs_kap_ruecklage": "Kapitalrücklage (§ 272 Abs. 2 Nr. 4 HGB)",
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
        "tab_ops": "🚗 Fahrzeug- & Betriebskennzahlen",
        "ops_header": "Fahrzeug- & Betriebskennzahlen",
        "ops_caption": "Kennzahlen pro Fahrzeug, pro Kilometer und pro Fahrt, direkt aus der Simulation abgeleitet — die Stückkostenrechnung hinter den Finanzberichten. Die Spalten folgen derselben Monats-/Jahresansicht wie die übrigen Tabs (mit den Jahres-Schaltern oben in Monate aufklappen).",
        "ops_total_km": "Gesamt gefahrene km (Flotte)",
        "ops_billable_km": "Beladene km (mit Fahrgast / Ware)",
        "ops_deadhead_km": "Leer-km (Leerfahrten / Repositionierung)",
        "ops_deadhead_ratio": "Leerfahrtenquote (leer / gesamt)",
        "ops_pax_trips": "Fahrgastfahrten",
        "ops_delivery_trips": "Lieferfahrten",
        "ops_km_per_veh": "km pro Fahrzeug (in der Periode)",
        "ops_trips_per_veh": "Fahrten pro Fahrzeug (in der Periode)",
        "ops_avg_fleet": "Durchschnittlich aktive Fahrzeuge",
        "ops_netrev_veh": "Nettoerlös pro Fahrzeug",
        "ops_ebitda_veh": "EBITDA pro Fahrzeug",
        "ops_rev_km": "Nettoerlös pro km",
        "ops_gbv_km": "Bruttofahrpreis pro km (inkl. USt)",
        "ops_energy_km": "Energiekosten pro km",
        "ops_wear_km": "Instandhaltung / Verschleiß pro km",
        "ops_clean_km": "Reinigungskosten pro km (netto)",
        "ops_varcost_km": "Variable Kosten gesamt pro km",
        "ops_contrib_km": "Deckungsbeitrag pro km (Erlös - variable Kosten)",
        "ops_rev_trip": "Nettoerlös pro Fahrt",
        "ops_energy_kwh": "Energieverbrauch (kWh, nominal)",
        "ops_m_total_km": "Gesamt gefahrene km (5J)",
        "ops_m_km_veh_day": "km pro Fahrzeug / Tag (realisiert)",
        "ops_m_deadhead": "Leerfahrtenquote (5J)",
        "ops_m_rev_km": "Nettoerlös pro km (5J)",
        "ops_chart_total_km": "Gesamt gefahrene km pro Jahr",
        "ops_chart_km_veh": "km pro Fahrzeug pro Jahr",
        "tab_readme": "Handbuch & Dokumentation",
        # === Monte Carlo Risiko- & Varianzanalyse ===
        "tab_mc": "🎲 Risiko- & Varianzanalyse (Monte Carlo)",
        "mc_header": "Risiko- & Varianzanalyse — Stochastische Monte-Carlo-Simulation",
        "mc_intro": "Dieses Modul kapselt die deterministische 60-Monats-Engine in einer Monte-Carlo-Simulation. In jedem der N Läufe zieht das Modell seinen gesamten Satz varianztreibender Eingaben neu — Betriebsphysik, Preisgestaltung, Kapital- und Finanzierungskosten sowie Betriebskosten — zusammen mit einem gemeinsamen jährlichen Wirtschafts-(Makro-)Faktor, einer sechsfachen Mischung von Tagestypen und acht Kategorien einmaliger Störereignisse, jeweils aus einer empirisch verankerten Wahrscheinlichkeitsverteilung. Der deterministische Basisfall in den anderen Tabs bleibt unverändert; dies ist eine ergänzende Risikoanalyse für Bank-Kreditkomitees und die Project-Finance-Prüfung.",
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
        # === / Makro-Kopplung ===
        "mc_macro_header": "🌍 Makro-Kopplung — korrelierte Krisen-Engine",
        "mc_macro_help": "Ein gemeinsamer Makro-Umfeld-Faktor wird einmal pro simuliertem JAHR gezogen. Ein positiver Wert steht für ein Krisenjahr; er treibt Energiepreise HOCH, Kreditzinsen HOCH und Nachfrage RUNTER — gemeinsam, im selben Jahr. Jeder Jahresfaktor wird direkt in die Monate dieses Jahres im 60-Monats-Ledger injiziert, sodass ein einzelnes Katastrophenjahr die Liquidität in Echtzeit kollabieren lässt. Mit den Betas unten steuern Sie die Reaktionsstärke. Alle Betas auf 0 stellt unabhängiges Verhalten wieder her.",
        "mc_beta_energy": "Energie-Sensitivität βₑ (€/kWh pro +1σ Krise)",
        "mc_beta_rate": "Zins-Sensitivität βᵣ (Zins-pp pro +1σ Krise)",
        "mc_beta_demand": "Nachfrage-Sensitivität β_d (Auslastungspunkte pro +1σ Krise)",
        "mc_beta_fx": "FX-Sensitivität β_fx (EUR-Schwäche pro +1σ Krise)",
        "mc_macro_sigma": "Makro-Shock σ (jährliche Volatilität, 1,0 = Standard)",
        "mc_shock_demand_collapse": "Nachfrage-Kollaps (Pandemie/Lockdown)",
        # === dynamisches Narrativ-Panel ===
        "mc_narr_header": "🧭 Was diese Ergebnisse bedeuten (Klartext-Erläuterung)",
        "mc_narr_caption": "Diese Erläuterung wird aus den tatsächlichen Zahlen Ihrer soeben durchgeführten Simulation und Ihren aktuellen Seitenleisten-Einstellungen generiert. Sie aktualisiert sich bei jedem erneuten Lauf oder jeder Eingabeänderung.",
        "mc_narr_profit_h": "**Das Gewinnbild.**",
        "mc_narr_survival_h": "**Das Überlebensbild (das wichtigste).**",
        "mc_narr_drivers_h": "**Was Ihr Schicksal tatsächlich bestimmt.**",
        "mc_narr_implication_h": "**Implikation für das Geschäft.**",
        # === Simulations-Provenienz-Panel (zeigt simulation_settings) ===
        "mc_provenance_header": "🧾 Simulations-Provenienz & Einstellungen (Reproduzierbarkeit)",
        "mc_provenance_caption": "Die exakten Eingaben hinter den obigen Perzentiltabellen — Iterationszahl, RNG-Seed, Makro-Kopplungs-Betas und jeder Basiswert, um den die Simulation gezogen hat. Erfasst, damit jeder Monte-Carlo-Lauf vollständig reproduzierbar und für ein Bank-Kreditkomitee prüfbar ist.",

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
        "kpi_dscr": "Schuldendienstdeckungsgrad (DSCR — gesamt)",
        "kpi_dscr_senior": "Senior-DSCR (nur Bankschulden, ohne Gesellschafterdarlehen)",
        "kpi_dscr_senior_help": "Bank-konformer DSCR mit SENIOR-Schuldendienst — KfW/kommerzielles Kfz-Darlehen Tilgung+Zinsen plus Kontokorrent-Zinsen, OHNE Gesellschafterdarlehens-Zinsen. Nachrangige Gesellschafterdarlehen fungieren kreditseitig als wirtschaftliches Eigenkapital (die meisten KfW-Universell-Linien fordern formale Rangrücktrittserklärung). Einschluss von SH-Zinsen im Nenner verzerrt den bankrelevanten DSCR künstlich nach unten — diese Zeile zeigt die Kennzahl, die das Kreditkomitee tatsächlich berechnet.",
        "kpi_fccr": "Fixed-Charge Coverage Ratio (FCCR — leasing-adjustiert)",
        "kpi_fccr_help": "Bank-konformer leasing-adjustierter Deckungsgrad: (EBITDA + Leasingaufwand) / (Tilgung + Zinsen + Leasingaufwand). Operating-Leasing-Verpflichtungen sind nicht-diskretionäre vertragliche Zahlungsströme, wirtschaftlich identisch zum Senior-Schuldendienst — Bank-Kreditkomitees berechnen dies intern, auch wenn HGB im Gegensatz zu IFRS 16 keine Leasingbilanzierung verlangt. FCCR ist die richtige Kennzahl beim Vergleich von Kapitalstrukturen mit unterschiedlichem Darlehens-/Leasingmix. Ziel: >1,5× für Senior-Debt-Covenants; >2,0× für starkes Rating.",
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
        "err_init_util": "❌ **Eingabekonflikt:** Start-Auslastung Monat 1 ({init:.0f}%) darf nicht über der Ziel-Auslastung ({target:.0f}%) liegen. Die Start-Auslastung ist der *Ausgangspunkt* der Hochlaufkurve; das Ziel ist die *Mature-State-Obergrenze*. Bitte Start senken oder Ziel anheben.",
        "err_combined_hours": "❌ **Betriebliche Obergrenze überschritten:** Aktive Stunden/Tag ({active:.1f}h) + Lieferstunden/Tag ({delivery:.1f}h) = {total:.1f}h überschreitet die 20h/Tag-Betriebsobergrenze. Die restlichen 4+ Stunden des 24h-Kalendertages werden für induktive Nachtladung, Sensorreinigung und Depot-Wartungsfenster benötigt. Einer der beiden Stundenwerte muss reduziert werden.",
        "net_liq_warn": "⚠️  Netto-Liquidität negativ (Kasse − Kontokorrent < Mindestpuffer) in Monat: ",
        "insolv_warn": "💀 INSOLVENZ: Erforderlicher Liquiditätsbedarf übersteigt die genehmigte Kontokorrentlinie in Monat: ",
        "legal_insolv_warn": "⚖️ § 15a InsO ANTRAGSPFLICHT: 3+ aufeinanderfolgende Monate ungedeckten Liquiditätsbedarfs erstmals erreicht in Monat: ",
        "insolv_severity_label": "Kumulierter ungedeckter Liquiditätsbedarf über den Verletzungszeitraum",
        "insolv_diagnostic_note": "Hinweis: Die Simulation läuft über den gesetzlichen Insolvenzauslöser hinaus weiter — zur diagnostischen Sichtbarkeit des Liquiditätsverlaufs. In der Realität müsste die Geschäftsführung gemäß § 15a InsO innerhalb von 3 Wochen ab Zahlungsunfähigkeit Insolvenzantrag stellen. Diese Offenlegung dient der Quantifizierung des Kapitalbedarfs zur Sicherung der Fortführungsfähigkeit (Going Concern).",
        "ebitda_recon_title": "EBITDA-Überleitung (Management-Sicht → HGB-Sicht)",
        "ebitda_recon_caption": "Das Management-EBITDA ist rein operativ. Die HGB-Sicht ergänzt die Anlagenabgangsgewinne am Nutzungsende, die als sonstige betriebliche Erträge gem. § 275 Abs. 2 Nr. 4 HGB erfasst werden. Die Überleitung stimmt exakt: Management-EBITDA + Anlagenabgang = HGB-EBITDA."
    }

# --- SIDEBAR INTERFACE CONTROLS ---
# UI Inputs defined first to prevent NameErrors in cache engine
st.sidebar.header(loc["sec1"])
y1_adds_str = st.sidebar.text_input(loc["y1_adds"], "3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0", key="sb_y1_adds_str")
y2_adds_str = st.sidebar.text_input(loc["y2_adds"], "2, 0, 0, 0, 2, 0, 0, 0, 0, 2, 0, 0", key="sb_y2_adds_str")
y3_adds_str = st.sidebar.text_input(loc["y3_adds"], "3, 0, 0, 3, 0, 0, 3, 0, 0, 3, 0, 0", key="sb_y3_adds_str")
y4_adds_str = st.sidebar.text_input(loc["y4_adds"], "4, 0, 0, 4, 0, 0, 4, 0, 0, 3, 0, 0", key="sb_y4_adds_str")
y5_adds_str = st.sidebar.text_input(loc["y5_adds"], "6, 0, 0, 5, 0, 0, 5, 0, 0, 5, 0, 0", key="sb_y5_adds_str")

# === Hardened Fleet Validation ===
# Fleet-addition inputs are validated as hard guardrails: bad input → sidebar
# error + st.stop. The length check stays
# soft (warning only) because the engine handles padding/truncation gracefully
# and 12-value cohort schedules can sometimes legitimately be shortened.
# Also clamps individual additions to 0–500 (defensible commercial fleet
# scaling cap — beyond this, scenario testing should explicitly justify).
_fleet_errors = []
_fleet_warnings = []
def _validate_fleet_str(label, s):
    try:
        arr = [int(x.strip()) for x in s.split(',') if x.strip() != ""]
    except ValueError:
        _fleet_errors.append(
            f"❌ **{label}:** invalid input — must be comma-separated integers (e.g., '3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0')."
        )
        return
    if any(x < 0 for x in arr):
        _fleet_errors.append(
            f"❌ **{label}:** negative additions detected. Fleet additions must be ≥ 0."
        )
        return
    if any(x > 500 for x in arr):
        _fleet_errors.append(
            f"❌ **{label}:** individual monthly addition exceeds the 500-vehicle sanity ceiling. "
            "If this is intentional, lower the ceiling locally — but verify capex, financing capacity, "
            "and depot footprint can support this scale."
        )
        return
    if len(arr) != 12:
        _fleet_warnings.append(
            f"ℹ️ {label}: expected 12 values, got {len(arr)}. Engine will pad with zeros or truncate to 12."
        )

for _label, _s in [(loc["y1_adds"], y1_adds_str), (loc["y2_adds"], y2_adds_str),
                   (loc["y3_adds"], y3_adds_str), (loc["y4_adds"], y4_adds_str),
                   (loc["y5_adds"], y5_adds_str)]:
    _validate_fleet_str(_label, _s)

# Surface warnings (non-fatal), then halt on errors so the user can correct
# before the engine sees the bad input.
for _w in _fleet_warnings:
    st.sidebar.warning(_w)
if _fleet_errors:
    for _e in _fleet_errors:
        st.sidebar.error(_e)
    st.stop()

# === first-class regulatory launch-delay stress parameter ===
launch_delay_months = st.sidebar.number_input(
    loc["launch_delay"], value=0, min_value=0, max_value=24, step=1,
    help=loc["help_launch_delay"]
, key="sb_launch_delay_months")

st.sidebar.header(loc["sec1b"])
active_hours_per_day = st.sidebar.number_input(loc["active_hours"], value=16.0, min_value=10.0, max_value=20.0, step=0.5, help=loc["help_active_hours"], key="sb_active_hours_per_day")
avg_speed_kmh = st.sidebar.number_input(loc["speed"], value=19.0, min_value=15.0, max_value=35.0, step=0.5, help=loc["help_speed"], key="sb_avg_speed_kmh")
deadhead_rate = st.sidebar.number_input(loc["deadhead"], value=22.0, min_value=15.0, max_value=50.0, step=0.5, help=loc["help_deadhead"], key="sb_deadhead_rate") / 100

st.sidebar.header(loc["sec1c"])
util_mode = st.sidebar.radio(loc["util_mode"], [loc["util_dyn"], loc["util_fix"]], key="sb_util_mode")
if util_mode == loc["util_dyn"]:
    target_util = st.sidebar.number_input(loc["target_util"], value=75.0, min_value=40.0, max_value=100.0, step=1.0, help=loc["help_target"], key="sb_target_util") / 100
    init_util = st.sidebar.number_input(loc["init_util"], value=55.0, min_value=40.0, max_value=100.0, step=1.0, help=loc["help_init"], key="sb_init_util") / 100
    # ===== CROSS-FIELD GUARDRAIL: init_util must not exceed target_util =====
    # Conceptual integrity: init = launch month starting point on the ramp-up
    # curve; target = mature-state ceiling. init > target inverts the curve
    # semantics and breaks the cannibalization recovery logic in the engine.
    # Halt execution with a clear sidebar error so the user can self-correct.
    if init_util > target_util:
        st.sidebar.error(loc["err_init_util"].format(init=init_util * 100, target=target_util * 100))
        st.stop()
    rec_rate = st.sidebar.number_input(loc["rec_rate"], value=5.0, min_value=1.0, max_value=25.0, step=0.5, help=loc["help_rec"], key="sb_rec_rate") / 100
    can_fac = st.sidebar.number_input(loc["can_fac"], value=0.35, min_value=0.10, max_value=0.50, step=0.05, help=loc["help_can"], key="sb_can_fac")
    flat_util = target_util
else:
    flat_util = st.sidebar.number_input(loc["util_fix"], value=90.0, min_value=40.0, max_value=100.0, step=1.0, key="sb_flat_util") / 100
    target_util, init_util, rec_rate, can_fac = flat_util, flat_util, 0, 0

# === Compute is_dynamic boolean from localized radio selection ===
# This replaces the hardcoded English string comparison inside the function,
# which would silently fail in German mode.
is_dynamic = (util_mode == loc["util_dyn"])

# === Seasonality (1d) — moved into the Section-1 operational block ====
# Empirical anchors and rationale are documented in the loc tooltips
# (loc["season_caption"]). Sits between 1c Utilization Dynamics and Section 2
# Trip Dynamics because it is an operational/physics-side input, not a cost.
st.sidebar.header(loc["sec_season"])
with st.sidebar.expander(loc["season_expander"], expanded=False):
    st.caption(loc["season_caption"])
    season_jan = st.number_input(loc["month_jan"], value=1.45, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_jan")
    season_feb = st.number_input(loc["month_feb"], value=1.45, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_feb")
    season_mar = st.number_input(loc["month_mar"], value=1.30, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_mar")
    season_apr = st.number_input(loc["month_apr"], value=1.05, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_apr")
    season_may = st.number_input(loc["month_may"], value=1.10, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_may")
    season_jun = st.number_input(loc["month_jun"], value=1.10, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_jun")
    season_jul = st.number_input(loc["month_jul"], value=1.10, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_jul")
    season_aug = st.number_input(loc["month_aug"], value=1.10, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_aug")
    season_sep = st.number_input(loc["month_sep"], value=1.10, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_sep")
    season_oct = st.number_input(loc["month_oct"], value=1.05, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_oct")
    season_nov = st.number_input(loc["month_nov"], value=1.30, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_nov")
    season_dec = st.number_input(loc["month_dec"], value=1.45, format="%.2f", step=0.01, min_value=1.00, max_value=2.00, key="sb_season_dec")
# Assemble lookup dict (month index 1-12 → multiplier)
seasonality_by_month = {
    1: season_jan, 2: season_feb, 3: season_mar, 4: season_apr,
    5: season_may, 6: season_jun, 7: season_jul, 8: season_aug,
    9: season_sep, 10: season_oct, 11: season_nov, 12: season_dec
}
_season_blend = sum(seasonality_by_month.values()) / 12
st.sidebar.caption(loc["season_blend_caption"].format(blend=_season_blend))

st.sidebar.header(loc["sec2"])
avg_trip_distance_km = st.sidebar.number_input(loc["trip_dist"], value=5.0, min_value=1.5, max_value=15.0, step=0.5, key="sb_avg_trip_distance_km")
dwell_time_mins = st.sidebar.number_input(loc["dwell"], value=3.5, min_value=1.0, max_value=10.0, step=0.5, help=loc["help_dwell"], key="sb_dwell_time_mins")

st.sidebar.header(loc["sec3"])
base_fare_eur = st.sidebar.number_input(loc["base_fare"], value=2.50, min_value=0.0, max_value=5.0, step=0.10, key="sb_base_fare_eur")
price_per_km_eur = st.sidebar.number_input(loc["price_km"], value=1.49, min_value=0.50, max_value=4.0, step=0.05, key="sb_price_per_km_eur")
tesla_take_rate = st.sidebar.number_input(loc["tesla_take"], value=25.0, min_value=15.0, max_value=50.0, step=1.0, key="sb_tesla_take_rate") / 100

# === B2B Delivery Stream sidebar section ===
st.sidebar.header(loc["sec3b"])
delivery_enabled = st.sidebar.checkbox(loc["delivery_toggle"], value=False, help=loc["help_delivery_toggle"], key="sb_delivery_enabled")
if delivery_enabled:
    delivery_hours_per_day = st.sidebar.number_input(loc["delivery_hours"], value=4.0, min_value=0.0, max_value=10.0, step=0.5, help=loc["help_delivery_hours"], key="sb_delivery_hours_per_day")
    # ===== CROSS-FIELD GUARDRAIL: active_hours + delivery_hours ≤ 20h =====
    # Operational ceiling: a 24h calendar day must reserve ≥4h for inductive
    # overnight charging + sensor cleaning + depot maintenance windows. The
    # asset is physically incapable of producing revenue during that window.
    # Halt with clear sidebar error rather than silently producing nonsensical
    # "23h Tesla Network active" outputs.
    _combined_hours = active_hours_per_day + delivery_hours_per_day
    if _combined_hours > 20.0:
        st.sidebar.error(loc["err_combined_hours"].format(
            active=active_hours_per_day, delivery=delivery_hours_per_day, total=_combined_hours
        ))
        st.stop()
    delivery_rev_per_trip = st.sidebar.number_input(loc["delivery_revenue_per_trip"], value=6.00, min_value=1.0, max_value=20.0, step=0.50, help=loc["help_delivery_rev"], key="sb_delivery_rev_per_trip")
    delivery_trips_per_hour = st.sidebar.number_input(loc["delivery_trips_per_active_hour"], value=3.0, min_value=0.5, max_value=6.0, step=0.5, help=loc["help_delivery_trips"], key="sb_delivery_trips_per_hour")
    delivery_take_rate = st.sidebar.number_input(loc["delivery_take_rate"], value=25.0, min_value=15.0, max_value=50.0, step=1.0, help=loc["help_delivery_take"], key="sb_delivery_take_rate") / 100
    delivery_ramp_y1 = st.sidebar.number_input(loc["delivery_ramp_y1"], value=0.0, min_value=0.0, max_value=100.0, step=10.0, help=loc["help_delivery_ramp"], key="sb_delivery_ramp_y1") / 100
    delivery_ramp_y2 = st.sidebar.number_input(loc["delivery_ramp_y2"], value=0.0, min_value=0.0, max_value=100.0, step=10.0, key="sb_delivery_ramp_y2") / 100
    delivery_ramp_y3 = st.sidebar.number_input(loc["delivery_ramp_y3"], value=30.0, min_value=0.0, max_value=100.0, step=10.0, key="sb_delivery_ramp_y3") / 100
    delivery_ramp_y4 = st.sidebar.number_input(loc["delivery_ramp_y4"], value=70.0, min_value=0.0, max_value=100.0, step=10.0, key="sb_delivery_ramp_y4") / 100
    delivery_ramp_y5 = st.sidebar.number_input(loc["delivery_ramp_y5"], value=100.0, min_value=0.0, max_value=100.0, step=10.0, key="sb_delivery_ramp_y5") / 100
else:
    # Zero-out all delivery params when toggle is OFF — engine never sees delivery revenue
    delivery_hours_per_day = 0.0
    delivery_rev_per_trip = 0.0
    delivery_trips_per_hour = 0.0
    delivery_take_rate = 0.0
    delivery_ramp_y1 = delivery_ramp_y2 = delivery_ramp_y3 = delivery_ramp_y4 = delivery_ramp_y5 = 0.0


st.sidebar.header(loc["sec4"])
cleaning_cost_per_day = st.sidebar.number_input(loc["cleaning"], value=3.00, min_value=0.0, max_value=25.0, step=0.5, help=loc["help_cleaning"], key="sb_cleaning_cost_per_day")
# === gross-up of the cleaning fee pass-through (Bruttoprinzip) ===
cleaning_fee_passthrough_per_day = st.sidebar.number_input(loc["cleaning_fee"], value=3.00, min_value=0.0, max_value=25.0, step=0.5, help=loc["help_cleaning_fee"], key="sb_cleaning_fee_passthrough_per_day")
wear_and_tear_rate = st.sidebar.number_input(loc["wear_rate"], value=0.10, min_value=0.07, max_value=0.25, format="%.2f", step=0.01, help=loc["wear_help"], key="sb_wear_and_tear_rate")
# === Energy decomposed into 3 sliders ===
# Energy is decomposed into three independent drivers, so each is visible and
# adjustable for stress-testing.
# Operating assumption: PURE INDUCTIVE on Tesla Robotaxi Network 2-6am window.
# Combined: 0.115 * 0.27 / 0.90 = €0.0345/km.
# Reflects realistic Tesla pricing — see help tooltips for the full
# bottom-up derivation including wholesale + grid fees + Tesla margin stack.
energy_kwh_per_km = st.sidebar.number_input(loc["energy_kwh"], value=0.115, min_value=0.100, max_value=0.150, format="%.3f", step=0.005, help=loc["help_energy_kwh"], key="sb_energy_kwh_per_km")
energy_eur_per_kwh = st.sidebar.number_input(loc["energy_eur"], value=0.270, min_value=0.150, max_value=0.500, format="%.3f", step=0.01, help=loc["help_energy_eur"], key="sb_energy_eur_per_kwh")
charging_efficiency = st.sidebar.number_input(loc["charging_eff"], value=0.90, format="%.2f", step=0.01, min_value=0.80, max_value=0.96, help=loc["help_charging_eff"], key="sb_charging_efficiency")
# Derived: effective €/km consumed (before seasonality multiplier in engine)
energy_rate = (energy_kwh_per_km * energy_eur_per_kwh) / charging_efficiency
# Visible read-out in sidebar so user can see the combined number
st.sidebar.caption(loc["energy_derived_caption"].format(rate=energy_rate))

st.sidebar.header(loc["sec5"])
# Insurance €180/mo (Tesla bundling thesis, FSD safety credit, theft-zero)
insurance_pm = st.sidebar.number_input(loc["insurance"], value=180.0, min_value=0.0, max_value=1000.0, step=10.0, help=loc["help_insurance"], key="sb_insurance_pm")
# APCOA parking €170/mo (published APCOA rates + bulk discount)
parking_pm = st.sidebar.number_input(loc["parking"], value=170.0, min_value=0.0, max_value=1000.0, step=10.0, help=loc["help_parking"], key="sb_parking_pm")
telemetry_pm = st.sidebar.number_input(loc["telemetry"], value=100.0, min_value=0.0, max_value=500.0, step=5.0, key="sb_telemetry_pm")
tuev_pm = st.sidebar.number_input(loc["tuev"], value=15.0, min_value=0.0, max_value=100.0, step=1.0, help=loc["help_tuev"], key="sb_tuev_pm")
charging_sub_pm = st.sidebar.number_input(loc["charging_sub"], value=10.0, min_value=0.0, max_value=200.0, step=1.0, key="sb_charging_sub_pm")
# === Cargo insurance — only applies when delivery toggle ON ===
# Verkehrshaftungsversicherung for B2B goods transport. Doesn't benefit from FSD
# safety credit (covers cargo theft, weather damage, in-transit handling claims).
if delivery_enabled:
    delivery_cargo_insurance_pm = st.sidebar.number_input(loc["cargo_ins"], value=20.0, min_value=0.0, max_value=100.0, step=1.0, help=loc["help_cargo_ins"], key="sb_delivery_cargo_insurance_pm")
else:
    delivery_cargo_insurance_pm = 0.0

st.sidebar.header(loc["sec6"])
hq_lease_pm = st.sidebar.number_input(loc["hq_lease"], value=450.0, min_value=0.0, max_value=5000.0, step=25.0, key="sb_hq_lease_pm")
it_cloud_pm = st.sidebar.number_input(loc["it_cloud"], value=320.0, min_value=0.0, max_value=5000.0, step=10.0, key="sb_it_cloud_pm")
legal_bookkeeping_pm = st.sidebar.number_input(loc["base_legal"], value=230.0, min_value=0.0, max_value=5000.0, step=10.0, key="sb_legal_bookkeeping_pm")
hq_insurance_pm = st.sidebar.number_input(loc["base_hq_ins"], value=250.0, min_value=0.0, max_value=5000.0, step=10.0, key="sb_hq_insurance_pm")
legal_scaling_pm = st.sidebar.number_input(loc["legal_scale"], value=25.0, min_value=0.0, max_value=500.0, step=1.0, key="sb_legal_scaling_pm")
insurance_scaling_pm = st.sidebar.number_input(loc["ins_scale"], value=40.0, min_value=0.0, max_value=500.0, step=1.0, key="sb_insurance_scaling_pm")
bank_fees_pm = st.sidebar.number_input(loc["bank_fees"], value=20.0, min_value=0.0, max_value=500.0, step=1.0, key="sb_bank_fees_pm")
ihk_pm = st.sidebar.number_input(loc["ihk"], value=35.0, min_value=0.0, max_value=500.0, step=1.0, key="sb_ihk_pm")
gez_pm_per_car = st.sidebar.number_input(loc["gez"], value=7.0, min_value=0.0, max_value=50.0, step=0.5, key="sb_gez_pm_per_car")
setup_costs_y1 = st.sidebar.number_input(loc["setup_costs"], value=1700.0, min_value=0.0, max_value=50000.0, step=100.0, key="sb_setup_costs_y1")

st.sidebar.header(loc["sec7"])
cybercab_base_usd = st.sidebar.number_input(loc["base_price"], value=30000.0, min_value=10000.0, max_value=100000.0, step=500.0, key="sb_cybercab_base_usd")
usd_eur_rate = st.sidebar.number_input(loc["fx"], value=1.15, min_value=0.50, max_value=3.00, step=0.01, key="sb_usd_eur_rate")
import_freight_eur = st.sidebar.number_input(loc["freight"], value=1800.0, min_value=0.0, max_value=10000.0, step=50.0, key="sb_import_freight_eur")
customs_duty_rate = st.sidebar.number_input(loc["duty"], value=10.0, min_value=0.0, max_value=50.0, step=0.5, key="sb_customs_duty_rate") / 100
it_hardware_capex_y1 = st.sidebar.number_input(loc["it_hw"], value=2500.0, min_value=0.0, max_value=50000.0, step=100.0, key="sb_it_hardware_capex_y1")
imp_month = st.sidebar.number_input(loc["imp_trigger"], value=0, min_value=0, max_value=60, key="sb_imp_month")
imp_pct_val = st.sidebar.number_input(loc["imp_pct"], value=0.0, min_value=0.0, max_value=100.0, step=5.0, key="sb_imp_pct_val") / 100

st.sidebar.header(loc["sec8"])
#
# === CAPITAL ALLOCATION & VEHICLE FINANCING STRATEGY MATRIX =====
# === (moved to top of sec8 — the per-vehicle financing strategy
# === is the FIRST decision under capital structure, dictating debt
# === drawdowns, ARAP/lease flows, and equity capital calls)
#
# Per-year (Y1-Y5) financing mix configuration. Each year's vehicle
# cohort additions are split into three tranches with independent HGB
# accounting treatment:
# • Tranche A (Loan) → Capitalize asset; AfA; debt drawn @ LTV;
# interest+principal flows; full salvage
# • Tranche B (Lease) → Operating lease per HGB; NO capitalization
# (lessor owns); ARAP for Sonderzahlung;
# monthly lease expense in pos3; NO salvage
# • Tranche C (Equity) → Capitalize asset; AfA; FULL cash drain;
# optional founder capital-call on shortfall;
# NO debt; full salvage
# Defaults: 100% Loan / 0% Lease / 0% Equity per year.
#
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
                min_value=0, max_value=100, value=100, step=5, key=f"sb_fin_loan_y{_y_idx}"
            )
        with _cl2:
            _pct_lease = st.number_input(
                f"{loc['fin_pct_lease']} (Y{_y_idx})",
                min_value=0, max_value=100, value=0, step=5, key=f"sb_fin_lease_y{_y_idx}"
            )
        with _cl3:
            _pct_equity = st.number_input(
                f"{loc['fin_pct_equity']} (Y{_y_idx})",
                min_value=0, max_value=100, value=0, step=5, key=f"sb_fin_equity_y{_y_idx}"
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
    , key="sb_lease_money_factor")
    lease_downpayment_pct = st.number_input(
        loc["fin_lease_downpayment_pct"],
        value=15.0, min_value=0.0, max_value=50.0, step=1.0,
        help=loc["fin_lease_downpayment_help"]
    , key="sb_lease_downpayment_pct") / 100
    lease_term_months = st.number_input(
        loc["fin_lease_term_months"],
        value=60, min_value=24, max_value=72, step=12
    , key="sb_lease_term_months")

    # Global equity policy
    st.markdown(f"**{loc['fin_equity_section']}**")
    equity_capital_call_enabled = st.checkbox(
        loc["fin_equity_capital_call"],
        value=True,
        help=loc["fin_equity_capital_call_help"]
    , key="sb_equity_capital_call_enabled")

stammkapital = st.sidebar.number_input(loc["stamm"], value=25000.0, min_value=25000.0, max_value=1000000.0, step=1000.0, key="sb_stammkapital")
shareholder_loan = st.sidebar.number_input(loc["sh_loan"], value=15000.0, min_value=0.0, max_value=1000000.0, step=1000.0, key="sb_shareholder_loan")
sh_loan_rate = st.sidebar.number_input(loc["sh_loan_rate"], value=5.0, min_value=0.0, max_value=20.0, step=0.1, help=loc["help_sh_rate"], key="sb_sh_loan_rate") / 100
# === SH loan Rangrücktritt toggle (KPI-only reclassification) ===
# Under KfW Universell financing covenants, the shareholder loan typically must be
# formally subordinated via a notarized Rangrücktrittserklärung. Banks then treat
# the subordinated loan as Eigenkapital-Ersatz for the Kreditwürdigkeitsprüfung
# (creditworthiness assessment). This toggle reclassifies the SH loan as "economic
# equity" for KPI computation purposes only (Equity Ratio + Net LTV) — engine
# numbers, BS presentation, and HGB statutory P&L are UNCHANGED. The reclassification
# matches what bank credit committees compute internally for Mittelstand GmbHs.
sh_loan_rangruecktritt = st.sidebar.checkbox(
    loc["sh_rangruecktritt"], value=True, help=loc["help_rangruecktritt"]
, key="sb_sh_loan_rangruecktritt")
vehicle_ltv = st.sidebar.number_input(loc["ltv"], value=80.0, min_value=0.0, max_value=100.0, step=1.0, help=loc["help_ltv"], key="sb_vehicle_ltv") / 100
y1_loan_rate = st.sidebar.number_input(loc["y1_loan_rate"], value=4.5, min_value=0.0, max_value=20.0, step=0.1, key="sb_y1_loan_rate") / 100
y2_loan_rate = st.sidebar.number_input(loc["y2_loan_rate"], value=5.5, min_value=0.0, max_value=20.0, step=0.1, key="sb_y2_loan_rate") / 100

vat_bridge_rate = st.sidebar.number_input(loc["vat_rate_input"], value=6.5, min_value=0.0, max_value=20.0, step=0.1, key="sb_vat_bridge_rate") / 100
vat_lag_months = st.sidebar.number_input(loc["vat_lag_input"], value=3, min_value=1, max_value=12, step=1, key="sb_vat_lag_months")
min_cash_buffer = st.sidebar.number_input(loc["cash_buffer_input"], value=10000.0, min_value=0.0, max_value=1000000.0, step=5000.0, key="sb_min_cash_buffer")
max_overdraft_limit = st.sidebar.number_input(loc["max_overdraft_input"], value=50000.0, min_value=0.0, max_value=2000000.0, step=10000.0, help=loc["help_max_od"], key="sb_max_overdraft_limit")
legal_provision_rate = st.sidebar.number_input(loc["legal_provision_input"], value=200.0, min_value=0.0, max_value=5000.0, step=50.0, key="sb_legal_provision_rate")
interest_income_rate = st.sidebar.number_input(loc["int_rate"], value=2.2, min_value=0.0, max_value=15.0, step=0.1, key="sb_interest_income_rate") / 100
# === Parameterized municipal trade tax multiplier (Hebesatz) ===
# Default 250% = Gräfelfing (registered Sitz). Slider lets user stress-test
# alternative locations (Munich City 490%, Pullach 240%, Berlin 410%, etc.).
# Engine combines this with the legally-anchored declining KSt schedule
# (15→10% over VZ 2028-2032 per Wachstumsbooster-Gesetz § 23 Abs. 1 KStG n.F.)
# and 5.5% Soli to produce a fully transparent total-tax-rate schedule.
hebesatz_pct = st.sidebar.number_input(
    loc["hebesatz"], value=250.0, min_value=200.0, max_value=600.0, step=5.0,
    help=loc["help_hebesatz"]
, key="sb_hebesatz_pct")

st.sidebar.header(loc["sec9"])
thg_quote_per_car_py = st.sidebar.number_input(loc["thg"], value=280.0, min_value=0.0, max_value=1000.0, step=10.0, help=loc["help_thg"], key="sb_thg_quote_per_car_py")
salvage_value_per_car_eol = st.sidebar.number_input(loc["salvage"], value=10000.0, min_value=0.0, max_value=50000.0, step=500.0, key="sb_salvage_value_per_car_eol")


# --- 5. COMPREHENSIVE COMPUTATIONAL ENGINE FUNCTION ===
# This raw engine function is intentionally NOT cached. Inside the Monte Carlo loop
# (10K+ iterations with unique randomized floats), caching would create 10K unique
# cache entries — each holding full pnl/cf/bs result matrices — and exhaust memory.
# A thin cached wrapper below (execute_financial_simulation) caches ONLY the
# deterministic dashboard call; the MC harness calls this uncached function directly,
# so each iteration's results are garbage-collected normally.
def _execute_financial_simulation_uncached(
    y1_adds_str, y2_adds_str, y3_adds_str, y4_adds_str, y5_adds_str,
    active_hours_per_day, avg_speed_kmh, deadhead_rate, util_mode,
    target_util, init_util, rec_rate, can_fac, flat_util, avg_trip_distance_km,
    dwell_time_mins, base_fare_eur, price_per_km_eur, tesla_take_rate,
    cleaning_cost_per_day, cleaning_fee_passthrough_per_day, wear_and_tear_rate, energy_rate, insurance_pm,
    parking_pm, telemetry_pm, tuev_pm, charging_sub_pm, hq_lease_pm, it_cloud_pm,
    legal_bookkeeping_pm, hq_insurance_pm, legal_scaling_pm,
    insurance_scaling_pm, bank_fees_pm, ihk_pm, gez_pm_per_car, setup_costs_y1,
    cybercab_base_usd, usd_eur_rate, import_freight_eur, customs_duty_rate,
    it_hardware_capex_y1, imp_month, imp_pct_val, stammkapital, shareholder_loan,
    sh_loan_rate, vehicle_ltv, y1_loan_rate, y2_loan_rate, vat_bridge_rate,
    vat_lag_months, min_cash_buffer, legal_provision_rate, interest_income_rate,
    thg_quote_per_car_py, salvage_value_per_car_eol, max_overdraft_limit,
    delivery_enabled, delivery_hours_per_day, delivery_rev_per_trip,
    delivery_trips_per_hour, delivery_take_rate,
    delivery_ramp_y1, delivery_ramp_y2, delivery_ramp_y3, delivery_ramp_y4, delivery_ramp_y5,
    delivery_cargo_insurance_pm, seasonality_by_month,
    is_dynamic, lang_choice,
    fin_mix_by_year=None,
    lease_money_factor=0.015, lease_downpayment_pct=0.15, lease_term_months=60,
    equity_capital_call_enabled=True,
    hebesatz_pct=250.0,
    # === path-dependency fix: per-YEAR macro shock injection ========
    # macro_demand_mult_by_year / macro_energy_mult_by_year are optional
    # 5-element sequences (index 0 = Year 1... index 4 = Year 5). They let
    # the Monte Carlo harness push a DIFFERENT macro shock into each operating
    # year IN-PLACE inside the 60-month ledger, instead of averaging the five
    # crisis-years into one number before the engine sees them.
    # • macro_demand_mult_by_year[y] scales that year's utilization/op-days
    # (a crisis year < 1.0 suppresses ridership for months 12y..12y+11 only)
    # • macro_energy_mult_by_year[y] scales that year's energy cost
    # (a crisis year > 1.0 raises €/km energy for that year's months only)
    # DEFAULT None → both treated as all-1.0 → the deterministic engine is unaffected.
    # The per-year channel is dormant unless the MC harness supplies non-neutral arrays.
    macro_demand_mult_by_year=None,
    macro_energy_mult_by_year=None,
    # === first-class regulatory launch-delay stress parameter ===
    # Shifts the ENTIRE fleet-addition schedule right by N months while fixed
    # HQ costs, one-off setup costs, and Y1 IT capex correctly burn from
    # month 1 — modeling the single most probable real-world deviation for a
    # Jan-2028 Cybercab launch: AFGBV Level-4 operating permission, EU
    # type-approval/homologation, or Munich PBefG concession slippage.
    # Additions pushed past the 60-month horizon are simply never purchased
    # (no capex, no debt — you do not buy cars you cannot deploy). Default 0
    # leaves the schedule unshifted.
    launch_delay_months=0,
    # === per-year overdraft (Kontokorrent) rate add-on =======
    # The overdraft is the model's ONE genuinely floating-rate liability — and
    # it is drawn precisely in crisis scenarios, so its rate carries the macro factor
    # per year (fixed loan rates lock at origination and are tugged per cohort year;
    # the floating line reprices continuously). This optional 5-element array
    # (percentage-point adders, index 0 = Year 1) lets the Monte Carlo push
    # each year's macro shock into the floating rate IN-PLACE. None → zeros →
    # deterministic engine unaffected. Effective rate is
    # floored at 0.5% (banks do not pay you to draw a Kontokorrent).
    overdraft_rate_addon_by_year=None
):
    #
    # is_dynamic parameter added before lang_choice
    # Replaces the buggy hardcoded English string comparison that
    # silently failed in German mode and forced flat utilization.
    #
    
    # Pure Static Keys to Prevent Variable Reference Errors in Cache Mapping
    # === P&L static keys — additional rows for delivery stream ===
    # P_DGBV = Delivery Gross Booking Value (gross of VAT)
    # P_DVAT = Delivery VAT remitted to Finanzamt
    # P_DNET = Delivery Net Revenue (excl VAT)
    # P_DTFEE = Tesla Network fee on delivery net
    # P_DMNET = MRRG Net Revenue from Delivery (after Tesla fee)
    # P_TMNET = Total MRRG Net Revenue (Passenger + Delivery)
    P_GBV, P_VAT, P_NET, P_TFEE, P_MNET, P_DGBV, P_DVAT, P_DNET, P_DTFEE, P_DMNET, P_TMNET, P_EN, P_WR, P_CL, P_LSE, P_DB1, P_INS, P_PK, P_API, P_TV, P_SUB, P_DB2, P_HQ, P_IT, P_LEG, P_HINS, P_FEE, P_BNK, P_LPR, P_THG, P_CFR, P_EB, P_EB_HGB, P_AF_V, P_AF_I, P_SAL, P_EBIT, P_I_IN, P_I_EX, P_I_EX_SH, P_EBT, P_TX, P_NI = [
        "pnl_gbv", "pnl_vat", "pnl_net_rev", "pnl_tesla_fee", "pnl_mrrg_net",
        "pnl_delivery_gbv", "pnl_delivery_vat", "pnl_delivery_net_rev", "pnl_delivery_tesla_fee", "pnl_delivery_mrrg_net", "pnl_total_mrrg_net",
        "pnl_energy", "pnl_wear", "pnl_clean", "pnl_lease", "pnl_db1", "pnl_ins", "pnl_park",
        "pnl_api", "pnl_tuev", "pnl_sub", "pnl_db2", "pnl_hq_lease", "pnl_it", "pnl_legal", "pnl_hq_ins", "pnl_fees", "pnl_bank", "pnl_legal_prov", "pnl_thg", "pnl_clean_fee",
        "pnl_ebitda", "pnl_ebitda_hgb", "pnl_afa_veh", "pnl_afa_it", "pnl_salvage", "pnl_ebit", "pnl_int_inc", "pnl_int_exp", "pnl_int_exp_sh", "pnl_ebt", "pnl_tax", "pnl_ni"
    ]

    C_NI, C_DP, C_GS, C_TP, C_TPD, C_LPR, C_WCT, C_VCOL, C_VPD, C_LSE, C_OP, C_CAP, C_VRF, C_SLE, C_INV, C_EQ, C_CC, C_SH, C_KFW, C_PRN, C_VDR, C_VRP, C_OD, C_FIN, C_NET, C_BEG, C_END = [
        "cf_ni", "cf_depr", "cf_gain_sale", "cf_tax_prov", "cf_tax_paid", "cf_legal_prov", "cf_wc_thg", "cf_vat_coll", "cf_vat_paid", "cf_lease", "cf_op",
        "cf_capex", "cf_vat_ref", "cf_sale", "cf_inv", "cf_eq", "cf_capital_call", "cf_sh", "cf_kfw_draw", "cf_prin", "cf_vat_draw", "cf_vat_repay", "cf_overdraft_delta",
        "cf_fin", "cf_net", "cf_beg", "cf_end"
    ]

    B_GF, B_AD, B_NF, B_VR, B_OPVRX, B_TR, B_TRX, B_ARAP, B_CS, B_TC, B_TA, B_ES, B_KR, B_ER, B_TEQ, B_PT, B_PL, B_TPV, B_DK, B_DV, B_DO, B_PV, B_SL, B_TL, B_TLEQ, B_CH = [
        "bs_gfa", "bs_acc_depr", "bs_nfa", "bs_vat_rec", "bs_vat_rec_op", "bs_thg_rec", "bs_tax_rec", "bs_arap", "bs_cash", "bs_tca", "bs_ta", "bs_eq_share", "bs_kap_ruecklage", "bs_eq_ret", "bs_teq",
        "bs_prov_tax", "bs_prov_legal", "bs_tprov", "bs_debt_kfw", "bs_debt_vat", "bs_debt_overdraft", "bs_pay_vat", "bs_sh_loan", "bs_tliab", "bs_tleq", "bs_check"
    ]
    bs_keys_internal = [B_GF, B_AD, B_NF, B_VR, B_OPVRX, B_TR, B_TRX, B_ARAP, B_CS, B_TC, B_TA, B_ES, B_KR, B_ER, B_TEQ, B_PT, B_PL, B_TPV, B_DK, B_DV, B_DO, B_PV, B_SL, B_TL, B_TLEQ, B_CH]

    def parse_adds(add_str):
        try:
            arr = [int(x.strip()) for x in add_str.split(',')]
            return (arr + [0]*12)[:12]
        except:
            return [0]*12

    all_adds = parse_adds(y1_adds_str) + parse_adds(y2_adds_str) + parse_adds(y3_adds_str) + parse_adds(y4_adds_str) + parse_adds(y5_adds_str)
    # === regulatory launch-delay shift =================
    # Prepend N zero-addition months and truncate back to the 60-month
    # horizon: every cohort lands N months later; additions displaced past
    # month 60 are never purchased. Fixed corporate costs (HQ lease, IT cloud,
    # legal base, setup costs, Y1 IT hardware capex) intentionally remain
    # anchored to month 1 — they burn through the delay window with zero
    # revenue, which is exactly the regulatory-slippage stress this parameter
    # exists to expose. base_fleet_size (the scaling-cost anchor) stays on the
    # NOMINAL Y1 plan: per-vehicle legal/insurance scaling premiums apply to
    # growth beyond the originally-planned base fleet, delay or not.
    _delay = int(max(0, launch_delay_months))
    if _delay > 0:
        all_adds = ([0] * _delay + all_adds)[:60]
    # === base_fleet_size restored inside cached function scope ===
    base_fleet_size = sum(parse_adds(y1_adds_str))
    
    cybercab_base_eur = cybercab_base_usd / usd_eur_rate
    zollwert_cif_eur = cybercab_base_eur + import_freight_eur
    zollkosten_eur = zollwert_cif_eur * customs_duty_rate
    total_capex_per_car = zollwert_cif_eur + zollkosten_eur

    # === Default financing mix fallback ===
    if fin_mix_by_year is None:
        fin_mix_by_year = {y: (1.0, 0.0, 0.0) for y in range(1, 6)}

    # === normalize the per-year overdraft rate add-on array =====
    # None → all-zero (deterministic engine unaffected);
    # defensive length-pad to 5 so a short array cannot IndexError mid-horizon.
    if overdraft_rate_addon_by_year is None:
        _od_addon_yr = [0.0, 0.0, 0.0, 0.0, 0.0]
    else:
        _od_addon_yr = list(overdraft_rate_addon_by_year)[:5]
        _od_addon_yr += [0.0] * (5 - len(_od_addon_yr))

    # === normalize per-year macro arrays. None → neutral (all 1.0) so the
    # deterministic engine is unchanged. Defensive length-pad to 5 so a short
    # array can't IndexError mid-horizon. ===
    if macro_demand_mult_by_year is None:
        _macro_dem_yr = [1.0, 1.0, 1.0, 1.0, 1.0]
    else:
        _macro_dem_yr = list(macro_demand_mult_by_year)[:5]
        _macro_dem_yr += [1.0] * (5 - len(_macro_dem_yr))
    if macro_energy_mult_by_year is None:
        _macro_en_yr = [1.0, 1.0, 1.0, 1.0, 1.0]
    else:
        _macro_en_yr = list(macro_energy_mult_by_year)[:5]
        _macro_en_yr += [1.0] * (5 - len(_macro_en_yr))

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
            # === FIX: annuity sized over the AMORTIZING window, not the full term ===
            # Loan structure: 12-month tilgungsfreie Anlaufzeit (interest-only grace, standard
            # KfW Gründerkredit / commercial Kfz-Finanzierung) + amortizing installments from
            # month c_start+12 through c_start+59 = 48 principal payments. The annuity is sized
            # over these 48 amortizing payments (not the full 60 periods), giving full
            # amortization exactly at the
            # end of the 60-month useful life: grace (12) + annuity (48) = 60-month maturity,
            # synchronized with the AfA schedule and the end-of-life salvage event below.
            _amortizing_payments = VEHICLE_AMORTIZATION_PERIOD - 12  # 48 at the 60-month default
            if _amortizing_payments <= 0:
                _amortizing_payments = VEHICLE_AMORTIZATION_PERIOD  # defensive: no-grace fallback
            if monthly_rate > 0:
                pmt = loan * (monthly_rate * (1 + monthly_rate)**_amortizing_payments) / ((1 + monthly_rate)**_amortizing_payments - 1)
            else:
                pmt = loan / _amortizing_payments if _amortizing_payments > 0 else 0.0

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

    #
    # === B2B Delivery Stream Physics ===============
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
    #
    avg_delivery_distance_km = 4.0  # blended food/parcel/medical
    delivery_trips_per_day_full = delivery_hours_per_day * delivery_trips_per_hour
    delivery_billable_km_per_day_full = delivery_trips_per_day_full * avg_delivery_distance_km
    delivery_total_km_per_day_full = delivery_billable_km_per_day_full / (1.0 - deadhead_rate) if deadhead_rate < 1.0 else 0.0
    delivery_gbv_per_day_per_car_full = delivery_trips_per_day_full * delivery_rev_per_trip
    delivery_ramp_by_year = {1: delivery_ramp_y1, 2: delivery_ramp_y2, 3: delivery_ramp_y3, 4: delivery_ramp_y4, 5: delivery_ramp_y5}

    pnl_m = {k: [] for k in [P_GBV, P_VAT, P_NET, P_TFEE, P_MNET, P_DGBV, P_DVAT, P_DNET, P_DTFEE, P_DMNET, P_TMNET, P_EN, P_WR, P_CL, P_LSE, P_DB1, P_INS, P_PK, P_API, P_TV, P_SUB, P_DB2, P_HQ, P_IT, P_LEG, P_HINS, P_FEE, P_BNK, P_LPR, P_THG, P_CFR, P_EB, P_EB_HGB, P_AF_V, P_AF_I, P_SAL, P_EBIT, P_I_IN, P_I_EX, P_I_EX_SH, P_EBT, P_TX, P_NI]}
    cf_m = {k: [] for k in [C_NI, C_DP, C_GS, C_TP, C_TPD, C_LPR, C_WCT, C_VCOL, C_VPD, C_LSE, C_OP, C_CAP, C_VRF, C_SLE, C_INV, C_EQ, C_CC, C_SH, C_KFW, C_PRN, C_VDR, C_VRP, C_OD, C_FIN, C_NET, C_BEG, C_END]}
    bs_m = {k: [] for k in [B_GF, B_AD, B_NF, B_VR, B_OPVRX, B_TR, B_TRX, B_ARAP, B_CS, B_TC, B_TA, B_ES, B_KR, B_ER, B_TEQ, B_PT, B_PL, B_TPV, B_DK, B_DV, B_DO, B_PV, B_SL, B_TL, B_TLEQ, B_CH]}
    # Operational distance / throughput volumes (KPI-only series; never feed the
    # financial statements, so they are financially inert by construction).
    ops_m = {k: [] for k in ["ops_total_km", "ops_billable_km", "ops_deadhead_km",
                             "ops_pax_billable_km", "ops_delivery_billable_km",
                             "ops_pax_trips", "ops_delivery_trips"]}

    #
    # === GERMAN CORPORATE TAX SCHEDULE — parameterized by Hebesatz ====
    #
    # Per "Gesetz für ein steuerliches Investitionssofortprogramm zur Stärkung
    # des Wirtschaftsstandorts Deutschland" (Wachstumsbooster-Gesetz, in Kraft
    # seit 19.07.2025, BGBl. I Nr. 161, § 23 Abs. 1 KStG n.F.): KSt reduces by
    # 1pp per Veranlagungszeitraum starting VZ 2028, reaching 10% in VZ 2032.
    # Business launch VZ 2028 → Y1=2028, Y5=2032 maps directly to this schedule.
    #
    # Tax stack per year = KSt + Solidaritätszuschlag + Gewerbesteuer
    # KSt by VZ: Y1(2028) 14%, Y2 13%, Y3 12%, Y4 11%, Y5(2032) 10%
    # Soli: constant 5.5% × KSt (§ 4 SolzG)
    # Gewerbesteuer: 3.5% × (Hebesatz / 100) (§ 16 GewStG)
    # Total = KSt × (1 + 5.5%) + 3.5% × (Hebesatz / 100)
    #
    # Gräfelfing default Hebesatz: 250% (one of the lowest in Munich metro;
    # significantly below Munich City 490%, Berlin 410%, Bayern average ~360%).
    # The municipality has retained this rate to attract corporate establishments
    # to the south-western suburbs. Verified via Statistisches Landesamt Bayern
    # 2024 Hebesatzliste. At default 250%, the combined effective rate schedule is
    # {Y1: 23.520%, Y2: 22.465%, Y3: 21.410%, Y4: 20.355%, Y5: 19.300%}.
    #
    _kst_by_year = {1: 0.14, 2: 0.13, 3: 0.12, 4: 0.11, 5: 0.10}
    _soli_factor = 0.055
    _gewst_base = 0.035
    _gewst_rate = _gewst_base * (hebesatz_pct / 100.0)
    tax_schedule = {
        y: _kst_by_year[y] * (1.0 + _soli_factor) + _gewst_rate
        for y in range(1, 6)
    }

    #
    # === Loss carryforward (Verlustvortrag) parameters ========
    # § 10d Abs. 2 EStG (via § 8 Abs. 1 KStG) and § 10a GewStG: losses carry
    # forward indefinitely; in a profit year they offset the positive base in
    # full up to the €1M Sockelbetrag, and only at a capped percentage of the
    # base above €1M (Mindestbesteuerung). The percentage is 60% from VZ 2028
    # (the Wachstumschancengesetz's temporary 70% applied only to VZ 2024-2027
    # and does not reach this model's horizon). No carryback is modeled
    # (§ 10d Abs. 1 carryback is KSt-only, capped, and GewSt has none —
    # omitting it is the conservative simplification).
    # SIMPLIFICATION (documented): KSt and GewSt loss pots are tracked as ONE
    # combined Verlustvortrag applied against the single combined-rate base,
    # consistent with the engine's combined tax-rate architecture. The two
    # statutory pots evolve nearly identically for this business (no material
    # Hinzurechnungen/Kürzungen at this interest scale), so the combined pot
    # is a faithful approximation; a Steuerberater build-out would split them.
    #
    _NOL_SOCKEL_EUR = 1_000_000.0
    _NOL_OFFSET_PCT_ABOVE_SOCKEL = 0.60

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
    # Klima-Quote, elektrovorteil (all confirm). The payment is a flat annual
    # amount per vehicle and is NOT pro-rated within the year, so it is booked in
    # full (with Nov/Dec registrations deferred to January).
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
    # === annual-basis tax state ===
    # ytd_ebt accumulates the current Veranlagungszeitraum's EBT so the tax
    # accrual can be computed on the ANNUAL base (German corporate tax is
    # assessed per VZ, not per month). verlustvortrag carries the combined
    # NOL pot across years; it is READ during the year for the progressive
    # accrual and CONSUMED/EXTENDED only at the December year-end assessment.
    ytd_ebt = 0.0
    verlustvortrag = 0.0
    
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
    # === Audit Finding 4: Enhanced insolvency tracking ===
    # Per § 15a InsO, Antragspflicht triggers on Zahlungsunfähigkeit + 3-week grace period.
    # In a monthly simulation, we approximate this as 3+ consecutive months of unfunded
    # breach (capturing the legal grace window with conservative monthly resolution).
    # `insolvency_severity` tracks the cumulative € shortfall over the breach period.
    # `legal_insolvency_month` records the first month meeting § 15a InsO criteria.
    insolvency_severity = []     # Cumulative unfunded € shortfall per breach month
    consecutive_breach_count = 0 # Running counter of consecutive breach months
    legal_insolvency_month = None  # First month at which § 15a InsO Antragspflicht triggers

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
        # === fix: capture beginning-of-period overdraft balance for interest offset
        # In real treasury management, a bank with both positive deposits and an open
        # Kontokorrent line would automatically offset (positive cash sweeps reduce the
        # drawn overdraft). Interest income is therefore computed only on the NET positive
        # balance (cash minus drawn overdraft), avoiding a non-realistic frictional cost.
        # Used downstream in the int_inc_mo formula.
        beg_overdraft = overdraft_facility_bal
        
        month_col_names.append(f"{m_names[current_month_index-1]} '{str(current_year_cal)[-2:]}")
        days_in_mo = calendar.monthrange(current_year_cal, current_month_index)[1]
        
        #
        # === Seasonality is a 12-month lookup ===
        # Reads from `seasonality_by_month` dict (1-12 → multiplier) populated from
        # 12 individual sidebar sliders (annual blend 1.2125× at defaults). The user
        # can stress-test (e.g. a dry-cathode 4680 cell reduces the winter penalty
        # 10-15%) by adjusting individual month sliders.
        # Empirical defaults:
        # - Winter (Dec-Feb) 1.45×: ADAC Wintertest 2023, Munich Dec-Feb avg low -3 to -5°C
        # - Shoulder (Nov, Mar) 1.30×: partial battery thermal load
        # - Cool summer (Apr, Oct) 1.05×: minimal HVAC load
        # - Hot summer (May-Sep) 1.10×: A/C draw 8-15% per Geotab fleet data
        #
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

            # === FIX: tranche-aware operational fleet membership ========
            # Operational fleet membership is tranche-aware:
            # • Loan + equity cars (MRRG-owned): active for the full useful life
            # (60 months), then sold at the end-of-life event.
            # • Lease cars (lessor-owned): active only while the lease contract
            # runs, i.e. within BOTH the useful-life window AND the lease term.
            # When the term ends before month 60, the cars are physically
            # returned and stop producing revenue, costs, and THG claims.
            # A term > 60 is capped by the useful-life window. The default mix of
            # 100% loan keeps the whole cohort active for the full useful life.
            # Note: with mixed tranches the fleet count becomes fractional after a
            # short lease expires — consistent with the engine's existing
            # continuous tranche-fraction arithmetic (costs, THG, and revenue all
            # scale per-car linearly).
            _in_life_window = (current_month >= c_start and current_month < c_start + VEHICLE_AMORTIZATION_PERIOD)
            _in_lease_window = (current_month >= c_start and current_month < c_start + c_lease_term)
            if _in_life_window:
                active_fleet += c["size"] * (c["loan_frac"] + c["equity_frac"])
                if _in_lease_window:
                    active_fleet += c["size"] * c["lease_frac"]
                # === Tranche A (Loan): interest expense on outstanding loan balance ===
                int_for_this_loan = c["loan_bal"] * (c["rate"] / 12)
                int_exp += int_for_this_loan

                # === FIX: HGB Impairment per § 253 Abs. 3 HGB (carrying-amount base) ===
                # HGB treatment of an extraordinary impairment (§ 253 Abs. 3 HGB):
                # (a) Impairment base = CARRYING AMOUNT (Buchwert) = capitalized cost − accum.
                # AfA, measured BEFORE this month's planned charge (§ 253 Abs. 3 S. 5/6:
                # außerplanmäßige Abschreibung auf den niedrigeren beizulegenden Wert).
                # (b) Planned AfA must be RE-PLANNED on the reduced carrying amount over the
                # REMAINING useful life — an asset can never depreciate below zero.
                # Invariant enforced: cohort cumulative depreciation ≤ capitalized cost, NBV → 0
                # exactly at end of useful life (which also keeps the disposal gain clean).
                if current_month == imp_month and not c["impaired"]:
                    _carrying_amount = max(0.0, c["capex_capitalized"] - c["accum_afa"])
                    extra_afa = _carrying_amount * imp_pct_val
                    current_veh_afa += extra_afa
                    c["accum_afa"] += extra_afa
                    # Re-plan: spread the post-impairment NBV over the months remaining in the
                    # useful life INCLUDING the current month (this month's planned charge below
                    # already uses the new rate). remaining = (c_start + LIFE) − current_month.
                    _remaining_months = (c_start + VEHICLE_AMORTIZATION_PERIOD) - current_month
                    _nbv_post_impairment = max(0.0, c["capex_capitalized"] - c["accum_afa"])
                    if _remaining_months > 0:
                        c["afa_per_mo"] = _nbv_post_impairment / _remaining_months
                    else:
                        c["afa_per_mo"] = 0.0
                    c["impaired"] = True

                # === AfA on capitalized capex (loan + equity only — lease NOT capitalized) ===
                # Defensive clamp: never depreciate past the capitalized cost (floating-point
                # guard; the impairment re-plan above makes this exact in normal operation).
                _afa_this = min(c["afa_per_mo"], max(0.0, c["capex_capitalized"] - c["accum_afa"]))
                current_veh_afa += _afa_this
                c["accum_afa"] += _afa_this

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

            # === FIX: End-of-life salvage realization (loan + equity tranches) ===
            # The vehicle is sold at the END of the FINAL month of its
            # useful life (month c_start+59, i.e. life-month 60), AFTER that month's planned AfA
            # has booked. With the impairment re-plan and the AfA clamp above, accumulated depreciation
            # equals capitalized cost at that point → NBV = 0 → the full NET sale proceeds are a
            # disposal gain per § 275 Abs. 2 Nr. 4 HGB (sonstige betriebliche Erträge).
            # `salvage_value_per_car_eol` is interpreted as the NET-of-VAT realizable price.
            # Cohorts whose life extends beyond the horizon are NOT force-sold — their NBV
            # legitimately remains on the closing balance sheet (no fictitious fire-sale).
            # The loan is fully amortized by the 48th installment in this same month, so the
            # residual payoff below is a pure floating-point safety net (~€0).
            # Lease tranche returns to lessor — zero salvage for MRRG.
            if current_month == c_start + VEHICLE_AMORTIZATION_PERIOD - 1:
                # Salvage applies pro-rata to loan + equity vehicles
                non_lease_frac = c["loan_frac"] + c["equity_frac"]
                fleet_sale_rev += c["size"] * non_lease_frac * salvage_value_per_car_eol
                # Retire capitalized capex (loan + equity portions)
                capex_sold_this_mo += c["capex_capitalized"]
                accum_afa_sold_this_mo += c["accum_afa"]
                # Pay off any residual loan balance (floating-point remnant under the annuity sizing)
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
        # === path-dependency fix (demand side) ===============
        # Apply THIS YEAR's macro demand multiplier in-place. A crisis year
        # (<1.0) suppresses op_days for only that year's 12 months, so a single
        # catastrophic year collapses revenue in months 12y..12y+11 in real time
        # — dragging cash below zero exactly when it would in reality, rather than being
        # averaged into a mild 5-year drag. Neutral (1.0) by default. op_days feeds BOTH
        # passenger and delivery revenue
        # (delivery_op_days_mo = op_days below), so demand shock propagates to
        # the full revenue stream consistently.
        _macro_dem_this_year = _macro_dem_yr[current_year - 1]
        op_days = op_days * _macro_dem_this_year
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
        
        #
        # === B2B Delivery Revenue Computation (monthly) ======
        # Same utilization (current_u) applies — delivery utilization tracks
        # passenger utilization since both are Tesla Network dispatched and
        # share the same demand-density curve.
        # Ramp factor scales activation by year (Tesla product roll-out).
        #
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
        # --- Operational distance & throughput volumes (KPI series only) ---
        # All terms below are already-derived physics; they never touch any
        # financial line, so the three statements are unchanged.
        _pax_billable_km_mo = actual_billable_km_per_day * op_days * active_fleet
        _pax_trips_mo = actual_trips_per_day * op_days * active_fleet
        _delivery_billable_km_mo = delivery_billable_km_per_day_full * delivery_op_days_mo * active_fleet * delivery_ramp_factor
        _delivery_trips_mo = delivery_trips_per_day_full * delivery_op_days_mo * active_fleet * delivery_ramp_factor
        _billable_km_mo = _pax_billable_km_mo + _delivery_billable_km_mo
        _deadhead_km_mo = total_km_mo - _billable_km_mo
        ops_m["ops_total_km"].append(total_km_mo)
        ops_m["ops_billable_km"].append(_billable_km_mo)
        ops_m["ops_deadhead_km"].append(_deadhead_km_mo)
        ops_m["ops_pax_billable_km"].append(_pax_billable_km_mo)
        ops_m["ops_delivery_billable_km"].append(_delivery_billable_km_mo)
        ops_m["ops_pax_trips"].append(_pax_trips_mo)
        ops_m["ops_delivery_trips"].append(_delivery_trips_mo)
        wear_mo = total_km_mo * wear_and_tear_rate
        # === path-dependency fix (energy/cost side) =============
        # Apply THIS YEAR's macro energy multiplier in-place. A crisis year
        # (>1.0) raises €/km energy cost for only that year's months, so an
        # energy-price spike bites during the specific year it strikes rather
        # than being smeared across the horizon average. Neutral (1.0) by
        # default. Layered on top of seasonality (season_mult)
        # multiplicatively, consistent with how seasonality already scales energy.
        _macro_en_this_year = _macro_en_yr[current_year - 1]
        energy_mo = total_km_mo * (energy_rate * season_mult * _macro_en_this_year)
        # === FIX: cleaning grossed up per § 246 Abs. 2 HGB (Bruttoprinzip) ===
        # The sidebar `cleaning_cost_per_day` is the NET cost (€2/day default) = gross
        # depot cleaning (~€5/day) LESS the Tesla in-cabin fee pass-through (~€3/day,
        # charged to the soiling rider and routed to MRRG). Booking the expense net of
        # that fee revenue violates the Saldierungsverbot (§ 246 Abs. 2 HGB): income and
        # expense may not be offset. The fee is a sonstige betrieblicher Ertrag and the
        # gross cleaning a Materialaufwand; both must appear gross.
        # • clean_net_mo — the €2/day net figure. Drives the VAT base and cash EXACTLY
        # as before (the fee pass-through is contra-settled net through the Tesla
        # platform per the working-capital disclosure), so cash/VAT/BS are untouched.
        # • clean_mo — GROSS expense (net + pass-through) → pos3 Materialaufwand.
        # • clean_fee_rev_mo — the pass-through revenue → pos2 sonstige betr. Erträge.
        # EBITDA / EBIT / EBT / NI are all unchanged: the gross expense is exactly offset
        # by the fee revenue added back into EBITDA below (parallel to thg_rev_mo). With
        # cleaning_fee_passthrough_per_day = 0 there is no gross-up.
        clean_net_mo = cleaning_cost_per_day * days_in_mo * active_fleet  # VAT/cash base — unchanged
        clean_fee_rev_mo = cleaning_fee_passthrough_per_day * days_in_mo * active_fleet  # pos2 income
        clean_mo = clean_net_mo + clean_fee_rev_mo  # GROSS expense (pos3) — calendar-driven
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
        
        #
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
        #
        vat_eligible_opex_mo = (energy_mo + wear_mo + clean_net_mo + park_mo
                                # === clean_net_mo (NOT gross clean_mo) — the fee
                                # pass-through is contra-settled net via the Tesla platform,
                                # so the recoverable input VAT base is unchanged from. ===
                                + tel_mo + tuev_mo + sub_mo + hq_lease_mo
                                + it_cloud_mo + legal_mo
                                # === Tranche B (Lease): monthly lease payments only ===
                                # Monthly lease installments are VAT-bearing per § 1 Abs. 1
                                # UStG and their input VAT is reclaimed here through the
                                # monthly Umsatzsteuer-Voranmeldung netting. ARAP amortization
                                # is a non-cash matching release and never enters the VAT base.
                                #
                                # === FIX: lease_downpayment_cash_mo REMOVED ========
                                # The Sonderzahlung's 19% input VAT flows solely through the VAT bridge loan
                                # (vat_draw_mo includes lease_downpayment_cash_mo: borrow → pay invoice →
                                # Finanzamt refund → repay), mirroring the integrated VAT-Vorfinanzierung of
                                # real German commercial lease lines. It is therefore excluded from this opex
                                # input-VAT base to avoid reclaiming the same input VAT twice (a double
                                # Vorsteuerabzug, which § 15 UStG does not permit). Dormant at the default
                                # 100%-loan mix.
                                + lease_pmt_mo_net)
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
        # The THG payment is a flat ANNUAL amount per registered vehicle and is NOT
        # pro-rated within the year ("nie nur anteilig" — Finanztip, Geld-fuer-eauto.de).
        #
        # Model:
        # (a) NEW cars added Jan-Oct → full €280 booked in addition month
        # (b) NEW cars added Nov-Dec → past Nov 15 deadline, defer to next Jan
        # (c) EXISTING fleet (carried from prior calendar year) → full €280
        # each booked once per year, in January of new calendar year
        # IMPORTANT: deferred Nov/Dec cars released in Jan must be EXCLUDED
        # from the existing-fleet count for that month, or they'd be claimed
        # twice (once as deferred release, once as existing fleet).
        # `pending_carryover_cars` tracks the count of cars whose deferral
        # has been "queued" for next January, so we can exclude them.
        # Cash collection: quarterly settlement preserved (THG
        # providers typically pay within 4-12 weeks of application).
        current_calendar_month = ((current_month - 1) % 12) + 1  # 1=Jan... 12=Dec
        thg_rev_mo = 0.0
        # (a) New cars added Jan-Oct: book full annual amount NOW
        if current_calendar_month <= 10:
            thg_rev_mo += thg_quote_per_car_py * cars_added_this_month
        else:
            # (b) Nov/Dec additions: defer €-amount AND track car-count for next-Jan exclusion
            thg_deferred_next_year += thg_quote_per_car_py * cars_added_this_month
            pending_carryover_cars += cars_added_this_month
        # (c) January carry-over: existing fleet re-claims annual THG
        # EXCLUDING (i) cars added this same month and (ii) cars already
        # "pre-claimed" via the deferred-release pathway from prior Nov/Dec.
        if current_calendar_month == 1:
            existing_fleet_carryover = active_fleet - cars_added_this_month - pending_carryover_cars
            thg_rev_mo += thg_quote_per_car_py * existing_fleet_carryover
            # Release any deferred Nov/Dec registrations from prior year
            thg_rev_mo += thg_deferred_next_year
            thg_deferred_next_year = 0.0
            pending_carryover_cars = 0  # released, reset
        #
        # === FIX: THG-Quote output VAT (Umsatzsteuer) ==========
        #
        # For an Unternehmer, the sale of the GHG quota to a pooling provider
        # is an umsatzsteuerpflichtige sonstige Leistung (BMF guidance on
        # THG-Quotenhandel; the private-individual exemption does NOT apply to
        # a GmbH fleet operator), so 19% output VAT is booked.
        # ANCHORING CONVENTION: the sidebar value (default €280) is the NET
        # premium — the amount MRRG keeps. The P&L THG row and EBITDA are unchanged;
        # what changes is the
        # statement plumbing, routed through the EXISTING Voranmeldung
        # machinery: 19% output VAT enters the monthly Umsatzsteuer-Zahllast
        # in the ACCRUAL month (Sollversteuerung — tax arises with the
        # supply, not the cash), the receivable is carried GROSS per § 246
        # HGB, and the quarterly provider settlement collects GROSS cash.
        # Net cash over the cycle = net premium, exactly as before; the
        # company briefly fronts the VAT between remittance and collection —
        # the genuine Sollversteuerung working-capital cost.
        #
        thg_output_vat_mo = thg_rev_mo * VAT_RATE
        # Receivable carried GROSS (net premium + output VAT); quarterly
        # settlement collects the gross balance — pattern otherwise unchanged.
        thg_receivable += thg_rev_mo + thg_output_vat_mo
        thg_cash_mo = 0.0
        if current_month % 3 == 0:
            thg_cash_mo = thg_receivable
            thg_receivable = 0.0
        # WC delta now reconciles GROSS cash against GROSS accrual (net + VAT),
        # so the CF identity holds: in the accrual month the +VAT in
        # op_vat_collected is exactly offset here (no cash has arrived yet);
        # in the settlement month the gross collection flows through.
        thg_wc_delta = thg_cash_mo - (thg_rev_mo + thg_output_vat_mo)
        
        # Risk Provisions allocation (§ 249 HGB)
        legal_provision_mo = legal_provision_rate if active_fleet > 0 else 0.0
        legal_provision_bal += legal_provision_mo
        
        # Capital gains stripped cleanly from operational cash line
        # === + clean_fee_rev_mo (sonstige betr. Ertrag) offsets the grossed-up
        # cleaning expense flowing through db2_mo, so management EBITDA is unchanged. ===
        ebitda_mo = db2_mo - hq_lease_mo - it_cloud_mo - legal_mo - hq_ins_mo - fees_mo - bank_fees_pm + thg_rev_mo + clean_fee_rev_mo - legal_provision_mo
        ebit_mo = ebitda_mo - total_afa_this_mo + fleet_sale_rev
        
                # Interest income accrues on Beginning-of-Period NET cash position
        # (i.e., cash minus outstanding overdraft) — see fix above where
        # beg_overdraft is captured. Rationale: in real-world German treasury
        # arrangements (Kontokorrentlinie + Geschäftskonto with the same bank),
        # any positive deposit balance automatically offsets drawn overdraft via
        # daily Zinsstaffel netting. The bank pays interest only on the NET
        # positive position; charging full overdraft interest on beg_overdraft
        # while simultaneously paying full deposit interest on beg_cash is a
        # frictional cost that does not exist in practice. Floor at zero — if
        # net position is negative (cash < overdraft), no interest income.
        # Previous projected_mid approach was abandoned in favor of BoP basis;
        # this fix refines BoP to NET BoP per CFO/treasury best practice.
        _net_beg = beg_cash - beg_overdraft
        int_inc_mo = _net_beg * (interest_income_rate / 12.0) if _net_beg > 0 else 0.0
        sh_int_mo = shareholder_loan * (sh_loan_rate / 12.0)
        int_exp += sh_int_mo
        
        # === VAT Bridge Loan extended to lease Sonderzahlung per an audit finding ===
        # Per § 1 Abs. 1 Nr. 1 UStG, lease Sonderzahlung is a taxable service delivery
        # subject to 19% German VAT. Real-world German commercial lease lines (Mercedes-
        # Benz Bank, VW Leasing, ALD Automotive) include integrated VAT-Vorfinanzierung.
        # Without bridge financing of lease VAT, large lease tranches in Y2-Y3 trigger
        # false overdraft breaches simply due to timing mismatch with VAT reclaim cycle.
        # Bridge covers BOTH capitalized capex VAT AND lease Sonderzahlung VAT; repaid
        # via the standard vat_lag_months reclaim schedule (typically 3 months).
        vat_draw_mo = (capex_this_mo + lease_downpayment_cash_mo) * VAT_RATE
        vat_loan_bal += vat_draw_mo
        vat_repay_schedule[current_month + vat_lag_months] += vat_draw_mo
        
        vat_refund_inflow = vat_repay_schedule[current_month]
        # === fix: Post-horizon VAT refund pickup at month 60 ====
        # The vat_repay_schedule[current_month + vat_lag_months] writes for months 58-60
        # land in indices 61-63 — outside the 60-month display horizon. Without this
        # pickup, the month-60 cash balance includes outstanding vat_loan_bal that the
        # Finanzamt WOULD refund within 3 months of horizon end but isn't shown.
        # Effect: typically €15-40K cash under-statement at horizon end depending on
        # late-Y5 capex cadence. Economic reality is that those refunds are receivable
        # at month 60+lag — pulling them forward to month 60 as a single settlement
        # preserves the cash identity end_cash = beg_cash + net_change without distorting
        # any prior month's mechanics. Also drains vat_loan_bal so BS doesn't end with
        # a phantom liability that has no matching receivable.
        if current_month == 60:
            _post_horizon_refunds = sum(vat_repay_schedule[61:])
            vat_refund_inflow += _post_horizon_refunds
            # Mark these as consumed to avoid any future-state confusion
            for _i in range(61, len(vat_repay_schedule)):
                vat_repay_schedule[_i] = 0.0
        # Defensive cap — vat_repay cannot exceed outstanding bridge loan.
        # Excess refund still flows through inv_cf_mo as a real cash inflow.
        vat_repay_mo = min(vat_refund_inflow, vat_loan_bal)
        vat_loan_bal -= vat_repay_mo
        vat_int_mo = vat_loan_bal * (vat_bridge_rate / 12.0)
        int_exp += vat_int_mo
        
        if overdraft_facility_bal > 0:
            # === FIX: floating Kontokorrent rate feels the macro factor ===
            # The overdraft is the one genuinely floating-rate liability and is drawn
            # exactly in crisis scenarios; its rate now carries THIS YEAR's macro
            # add-on (zeros on the deterministic path). Floored at
            # 0.5% — a negative-rate Kontokorrent does not exist commercially.
            _od_rate_eff = max(0.005, OVERDRAFT_ANNUAL_RATE + _od_addon_yr[current_year - 1])
            int_exp += overdraft_facility_bal * (_od_rate_eff / 12.0)
            
        ebt_mo = ebit_mo + int_inc_mo - int_exp
        
        #
        # === FIX: tax accrual on the ANNUAL base with Verlustvortrag ==
        #
        # Tax is accrued on the ANNUAL base (German corporate tax is assessed per
        # Veranlagungszeitraum, not per month) with loss carryforward (§ 10d EStG /
        # § 10a GewStG), so a loss year is not taxed and its loss offsets later profits.
        #
        # Mechanism — progressive annual accrual:
        # 1. ytd_ebt accumulates the year's EBT.
        # 2. The year-to-date tax TARGET = rate × max(0, ytd_ebt − offset),
        # where offset applies the carried Verlustvortrag against the
        # positive base with Mindestbesteuerung (§ 10d Abs. 2 EStG /
        # § 10a GewStG): full offset up to the €1M Sockel, 60% of the
        # base above it. The pot is only READ here (consumed at Dec).
        # 3. The MONTH's tax expense = target − accrued-so-far. This can be
        # NEGATIVE inside a year (later loss months release prior months'
        # accrual) — correct annual-basis behavior. The provision's
        # § 246 Bruttoprinzip split downstream already presents any
        # resulting net receivable position gross on the asset side.
        # Annual sums equal rate × max(0, annual EBT − offset) exactly, so the
        # existing prepayment cadence, May true-up, and provision rollforward
        # work unchanged on top of this accrual.
        #
        ytd_ebt += ebt_mo
        if ytd_ebt > 0:
            _nol_offset_ytd = min(
                verlustvortrag,
                min(ytd_ebt, _NOL_SOCKEL_EUR)
                + max(0.0, ytd_ebt - _NOL_SOCKEL_EUR) * _NOL_OFFSET_PCT_ABOVE_SOCKEL
            )
            _taxable_ytd = ytd_ebt - _nol_offset_ytd
        else:
            _taxable_ytd = 0.0
        _tax_ytd_target = _taxable_ytd * tax_schedule[current_year]
        tax_exp_mo = _tax_ytd_target - current_year_tax_accrued
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
            # === December year-end Verlustvortrag assessment ========
            # Finalize the Veranlagungszeitraum: a loss year EXTENDS the carried
            # pot by the full annual loss; a profit year CONSUMES the pot by the
            # Mindestbesteuerung-capped offset actually used in the annual base
            # (same formula as the progressive accrual above, evaluated on the
            # final annual EBT, so accrual and assessment agree to the cent).
            if ytd_ebt < 0:
                verlustvortrag += -ytd_ebt
            elif ytd_ebt > 0:
                _nol_offset_final = min(
                    verlustvortrag,
                    min(ytd_ebt, _NOL_SOCKEL_EUR)
                    + max(0.0, ytd_ebt - _NOL_SOCKEL_EUR) * _NOL_OFFSET_PCT_ABOVE_SOCKEL
                )
                verlustvortrag -= _nol_offset_final
            ytd_ebt = 0.0
            true_up_due_this_m5 = current_year_tax_accrued - prepayments_made_this_year
            prior_year_tax_actual = current_year_tax_accrued
            current_year_tax_accrued = 0.0
            prepayments_made_this_year = 0.0

        net_inc_mo = ebt_mo - tax_exp_mo
        
        # Short-Term Overdraft Linkage Mechanics
        # Output VAT includes passenger + delivery (cash-instant ride VAT) and,
        # per the fix, the THG output VAT (accrual-month Sollversteuerung;
        # the matching cash arrives at the quarterly settlement via thg_wc_delta).
        op_vat_collected = vat_owed_mo + delivery_vat_mo + thg_output_vat_mo
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
        
        #
        # === Capped Overdraft + Insolvency Detection =====
        # Overdraft draws are now capped at max_overdraft_limit (bank Linie).
        # If shortfall exceeds available headroom → INSOLVENCY flagged but
        # overdraft is still drawn to the cap (engine continues for visibility).
        # === Tranche C (Equity) — Hybrid capital call mechanism ===
        # If equity-financed acquisition occurred this month AND
        # shortfall would breach max overdraft → inject founder capital ONLY
        # for the breach amount (most realistic founder behavior: tap overdraft
        # first, capital call as last resort to avoid Insolvenzantragspflicht).
        #
        overdraft_net_flow = 0.0
        breach_this_month = False  # Did this month trigger an unfunded overdraft breach?
        if tentative_ending_cash < 0:
            needed_from_od = -tentative_ending_cash
            available_od_headroom = max(0.0, max_overdraft_limit - overdraft_facility_bal)
            actual_od_draw = min(needed_from_od, available_od_headroom)
            unfunded_shortfall = needed_from_od - actual_od_draw
            if unfunded_shortfall > 0:
                # Shortfall exceeds approved line. Tranche C policy:
                # if capital call enabled AND any equity capex this month, inject
                # the unfunded shortfall as founder equity (now routes to Kapitalrücklage).
                if equity_capital_call_enabled and equity_capex_cash_mo > 0:
                    capital_call_mo = unfunded_shortfall
                    # Capital call absorbs the unfunded portion; no insolvency flag
                else:
                    # No equity tranche this month OR capital call disabled → insolvency
                    insolvency_months.append(month_col_names[-1])
                    insolvency_severity.append(unfunded_shortfall)
                    breach_this_month = True
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

        # === § 15a InsO Antragspflicht detection (3-month grace approximation) ===
        # In real law, the 3-WEEK grace period applies — but at monthly granularity,
        # 3 consecutive breach months is the conservative legal-equivalent threshold.
        # Once triggered, the simulation continues (for diagnostic visibility into the
        # cash path), but this flag surfaces a critical legal exposure to the dashboard.
        if breach_this_month:
            consecutive_breach_count += 1
            if consecutive_breach_count >= 3 and legal_insolvency_month is None:
                legal_insolvency_month = month_col_names[-1]
        else:
            consecutive_breach_count = 0  # Reset on any non-breach month

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
        # This is what bank credit committee computes — Effektive Liquidität.
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

        #
        # === Gross BS presentation for operational VAT position ===
        # Internal state `operational_vat_payable` carries the signed net
        # (can be negative when Vorsteuerüberhang exists). For BS reporting,
        # § 246 III HGB Bruttoprinzip requires gross presentation: split into
        # a payable (liability, ≥ 0) and a receivable (asset, ≥ 0).
        # === Same pattern for tax_provision_bal — when prepayments
        # exceed accrual (e.g., declining-profit year), a Steuerforderung exists.
        #
        op_vat_payable_bs = max(0.0, operational_vat_payable)       # liability
        op_vat_receivable_bs = max(0.0, -operational_vat_payable)   # asset
        tax_provision_bs = max(0.0, tax_provision_bal)              # liability
        tax_receivable_bs = max(0.0, -tax_provision_bal)            # asset

        # === Tranche B (Lease) BS: ARAP asset (Aktiver Rechnungsabgrenzungsposten) ===
        # HGB § 250 Abs. 1: Sonderzahlung capitalized as prepaid expense.
        # === Tranche C (Equity) BS: Stammkapital STAYS CONSTANT per § 272 Abs. 1 HGB ===
        # (High): Stammkapital is a legally fixed figure registered
        # in the Handelsregister. It cannot float month-to-month to absorb cash shortfalls
        # — that would require a notarized Gesellschafterbeschluss and Handelsregister
        # filing for each adjustment, which is not a monthly operational event.
        # Ad-hoc founder capital injections are correctly classified as additions to
        # Kapitalrücklage per § 272 Abs. 2 Nr. 4 HGB ("anderer Zuzahlungen, die
        # Gesellschafter in das Eigenkapital leisten"). This preserves the legal
        # integrity of the equity structure while still recognizing the equity injection.
        total_equity_share_bs = stammkapital  # constant, matches commercial registry
        kapitalruecklage_bs = cum_capital_call  # § 272 Abs. 2 Nr. 4 HGB classification

        total_assets = nfa + vat_receivable + op_vat_receivable_bs + thg_receivable + tax_receivable_bs + cum_arap_balance + current_cash
        # Total equity = Stammkapital (constant) + Kapitalrücklage (capital calls) + Retained Earnings
        total_equity = total_equity_share_bs + kapitalruecklage_bs + cum_net_income
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
        pnl_m[P_CFR].append(clean_fee_rev_mo)  #: cleaning fee pass-through (pos2 income)
        pnl_m[P_EB].append(ebitda_mo)
        # HGB-view EBITDA = Mgmt EBITDA + Anlagenabgang (per § 275 II Nr.4 HGB)
        pnl_m[P_EB_HGB].append(ebitda_mo + fleet_sale_rev)
        pnl_m[P_AF_V].append(-current_veh_afa)
        pnl_m[P_AF_I].append(-current_it_afa)
        pnl_m[P_SAL].append(fleet_sale_rev)
        pnl_m[P_EBIT].append(ebit_mo)
        pnl_m[P_I_IN].append(int_inc_mo)
        pnl_m[P_I_EX].append(-int_exp)
        # === fix: SH-loan interest memo line for senior DSCR computation ===
        # Banks compute DSCR using SENIOR debt service only (KfW/commercial Kfz loan
        # + Kontokorrent), excluding subordinated shareholder loans which function
        # as economic equity for credit purposes. Tracking sh_int_mo as a separate
        # P&L disclosure row lets the downstream KPI engine subtract it from total
        # int_exp to derive senior int exp. SH int is INCLUDED in P_I_EX (total)
        # so total HGB Finanzergebnis presentation is unaffected — this is purely
        # a disclosure row to enable the bank-relevant subset calculation.
        pnl_m[P_I_EX_SH].append(-sh_int_mo)
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
        # === C2 FIX (audit ): capital_call_mo must enter Net Change in Cash ===
        # Identity that must hold every month:
        # end_cash - beg_cash = net_before_overdraft + overdraft_net_flow + capital_call_mo
        # The current_cash assignment in the overdraft branch above is:
        # current_cash = tentative_ending_cash + actual_od_draw + capital_call_mo
        # capital_call_mo is included in C_NET so the cash-flow identity reconciles when a
        # Tranche-C capital call fires. Under the default 100% loan config no capital call
        # occurs; under any equity mix this keeps Net Change in Cash exact.
        cf_m[C_NET].append(net_before_overdraft + overdraft_net_flow + capital_call_mo)
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
        # === HGB § 272 Abs. 2 Nr. 4: Kapitalrücklage (founder ad-hoc contributions) ===
        bs_m[B_KR].append(kapitalruecklage_bs)
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

    return pnl_m, cf_m, bs_m, month_col_names, cash_breach_months, net_liq_breach_months, insolvency_months, active_fleet_by_month, utilization_by_month, total_capex_per_car, bs_keys_internal, insolvency_severity, legal_insolvency_month, ops_m


# === CACHED WRAPPER for deterministic dashboard call (an audit finding) ===
# This wrapper IS cached — single-shot dashboard runs benefit from cache hits
# when user revisits the page with identical sidebar inputs. The MC harness
# bypasses this and calls _execute_financial_simulation_uncached directly,
# preventing cache pollution from random parameter sweeps.
_ENGINE_OUTPUT_VERSION = "mrrg-engine-schema-v1"
# Bump this string whenever the engine's pnl_m / cf_m / bs_m output schema
# changes (e.g. new row keys added), so Streamlit Cloud does not serve a stale
# cached return tuple lacking the new keys (which would raise a KeyError in the
# KPI engine). The string is hashable and participates in @st.cache_data's hash,
# so changing it forces a fresh evaluation across the deployed cache.

@st.cache_data
def execute_financial_simulation(*args, engine_version=_ENGINE_OUTPUT_VERSION, **kwargs):
    # `engine_version` is hashed by Streamlit (no underscore prefix), so
    # changing _ENGINE_OUTPUT_VERSION above invalidates all prior cached entries.
    # The argument is otherwise unused — it's a pure cache-key sentinel.
    return _execute_financial_simulation_uncached(*args, **kwargs)


# --- EXECUTING COMPUTER MATRIX WITH SAFELY WRAPPED ISOLATION LOGIC ---
# === is_dynamic passed as positional arg before lang_choice ===
pnl_monthly, cf_monthly, bs_monthly, month_col_names, cash_breach_months, net_liq_breach_months, insolvency_months, active_fleet_by_month, utilization_by_month, total_capex_per_car, bs_keys_isolated, insolvency_severity, legal_insolvency_month, ops_monthly = execute_financial_simulation(
    y1_adds_str, y2_adds_str, y3_adds_str, y4_adds_str, y5_adds_str,
    active_hours_per_day, avg_speed_kmh, deadhead_rate, util_mode,
    target_util, init_util, rec_rate, can_fac, flat_util, avg_trip_distance_km,
    dwell_time_mins, base_fare_eur, price_per_km_eur, tesla_take_rate,
    cleaning_cost_per_day, cleaning_fee_passthrough_per_day, wear_and_tear_rate, energy_rate, insurance_pm,
    parking_pm, telemetry_pm, tuev_pm, charging_sub_pm, hq_lease_pm, it_cloud_pm,
    legal_bookkeeping_pm, hq_insurance_pm, legal_scaling_pm,
    insurance_scaling_pm, bank_fees_pm, ihk_pm, gez_pm_per_car, setup_costs_y1,
    cybercab_base_usd, usd_eur_rate, import_freight_eur, customs_duty_rate,
    it_hardware_capex_y1, imp_month, imp_pct_val, stammkapital, shareholder_loan,
    sh_loan_rate, vehicle_ltv, y1_loan_rate, y2_loan_rate, vat_bridge_rate,
    vat_lag_months, min_cash_buffer, legal_provision_rate, interest_income_rate,
    thg_quote_per_car_py, salvage_value_per_car_eol, max_overdraft_limit,
    delivery_enabled, delivery_hours_per_day, delivery_rev_per_trip,
    delivery_trips_per_hour, delivery_take_rate,
    delivery_ramp_y1, delivery_ramp_y2, delivery_ramp_y3, delivery_ramp_y4, delivery_ramp_y5,
    delivery_cargo_insurance_pm, seasonality_by_month,
    is_dynamic, lang_choice,
    fin_mix_by_year, lease_money_factor, lease_downpayment_pct, lease_term_months,
    equity_capital_call_enabled,
    hebesatz_pct,
    # === deterministic launch-delay scenario lever (hashed kwarg —
    # participates in the st.cache_data key, so changing the slider recomputes)
    launch_delay_months=launch_delay_months
)

#
# === Day-1 Sources/Uses Display
# Use the engine-returned total_capex_per_car (instead of duplicating
# the calculation in the dashboard).
# The Day-1 Liquidity metric shows ACTUAL end-of-Month-1 cash from the engine,
# which reflects first-month opex, revenue, and VAT bridge flows.
#
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
ops_yearly = agg_to_yearly(ops_monthly)

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

# Operational KPI volumes (raw keys retained — looked up directly, not renamed)
df_ops_mo = pd.DataFrame(ops_monthly, index=month_col_names).T
df_ops_yr = pd.DataFrame(ops_yearly, index=year_cols).T
df_ops_combined = pd.concat([df_ops_mo, df_ops_yr], axis=1)

# Language Loc Mapper for final output tables
# NOTE: Only the *_combined frames are renamed. df_pnl_yr / df_cf_yr / df_bs_yr
# retain raw short keys ("pnl_net_rev" etc.) and must be looked up using
# those raw keys in the visualizations tab below.
df_pnl_combined.rename(index=lambda x: loc.get(x, x), inplace=True)
df_cf_combined.rename(index=lambda x: loc.get(x, x), inplace=True)
df_bs_combined.rename(index=lambda x: loc.get(x, x), inplace=True)

# --- STATUTORY GERMAN GUV ACCORDIONS (§ 275 HGB Gesamtkostenverfahren) ---
# The Geschäftsführer also holds the Verkehrsleiter mandate (no separate fee), so
# Personalaufwand = 0. pnl_tesla_fee (bezogene Leistung — Tesla dispatch platform)
# flows into pos3 Materialaufwand; pnl_legal_prov (Zuführung Rückstellung § 249 HGB)
# flows into pos6.
# === B2B delivery revenue is operating revenue from the same Tesla
# Network platform — both streams book together into pos1 Umsatzerlöse per § 275 HGB
# (same operating activity, two consumer/B2B service types). Delivery Tesla
# platform fee flows into pos3 (bezogene Leistungen) alongside passenger fee.
hgb_structure = {}
# pos1 Umsatzerlöse: passenger Net Revenue + delivery Net Revenue (both operating activity)
hgb_structure[loc["hgb_pos1"]] = (df_pnl_combined.loc[loc["pnl_net_rev"]] + df_pnl_combined.loc[loc["pnl_delivery_net_rev"]]).values
hgb_structure[loc["hgb_pos2"]] = (df_pnl_combined.loc[loc["pnl_thg"]] + df_pnl_combined.loc[loc["pnl_salvage"]] + df_pnl_combined.loc[loc["pnl_clean_fee"]]).values
# === HGB § 275 Abs. 2 Nr. 5 — Materialaufwand (strict scope per German GAAP) ===
# Per § 275 HGB, Materialaufwand is limited to:
# (a) Aufwendungen für Roh-, Hilfs- und Betriebsstoffe — energy, wear consumables, cleaning
# (b) Aufwendungen für bezogene Leistungen — operating lease pmts, Tesla platform take-rate
# Vehicle insurance, APCOA parking, telemetry, TÜV, charging subscription do NOT qualify as
# Materialaufwand — they are operating overhead and belong under § 275 Abs. 2 Nr. 8.
# Reclassified per an audit finding (Critical) to satisfy bank-grade Jahresabschluss filing.
#
# === Accounting Policy Disclosure — Operating Lease Classification ===
# Operating lease payments (`pnl_lease`) are classified as Materialaufwand pos3 under
# "bezogene Leistungen" per § 275 Abs. 2 Nr. 5 HGB. This is DEFENSIBLE but represents
# a deliberate accounting policy choice — common alternative German practice for
# Mietleasing of operational assets classifies it under Sonstige betriebliche
# Aufwendungen pos8. Two arguments support keeping pos3:
# (1) Tesla's platform take-rate is also a "bezogene Leistung" enabling the same
# revenue stream — co-locating both in pos3 keeps the operating expense
# structure internally consistent.
# (2) For a TaaS fleet operator, the vehicle IS the production asset; the lease
# fee is functionally the input cost of accessing that production capacity
# (Materialaufwand-like) rather than discretionary overhead (sonstige).
# Counter-argument: § 275 historically reserves Nr. 5 "bezogene Leistungen" for
# subcontractor/service inputs that pass through to the customer (e.g., a logistics
# company paying a subcontractor to fulfill its own client contract).
# **Decision: keep in pos3 to preserve architecture; document choice for the
# Steuerberater/Wirtschaftsprüfer to confirm before the first Jahresabschluss filing.
# If the WP requires reclassification, only the HGB pos3/pos6 mapping below changes —
# engine numbers, P&L, BS, and KPIs remain identical.**
hgb_structure[loc["hgb_pos3"]] = (df_pnl_combined.loc[loc["pnl_energy"]] + df_pnl_combined.loc[loc["pnl_wear"]] + df_pnl_combined.loc[loc["pnl_clean"]] + df_pnl_combined.loc[loc["pnl_lease"]] + df_pnl_combined.loc[loc["pnl_tesla_fee"]] + df_pnl_combined.loc[loc["pnl_delivery_tesla_fee"]]).values
# Personalaufwand: zero — GF holds Verkehrsleiter mandate without separate compensation
hgb_structure[loc["hgb_pos4"]] = np.zeros(len(df_pnl_combined.columns))
hgb_structure[loc["hgb_pos5"]] = (df_pnl_combined.loc[loc["pnl_afa_veh"]] + df_pnl_combined.loc[loc["pnl_afa_it"]]).values
# === HGB § 275 Abs. 2 Nr. 8 — Sonstige betriebliche Aufwendungen ===
# Absorbs all operating overhead reclassified out of Materialaufwand:
# - pnl_ins: Versicherungsaufwand Fahrzeuge (vehicle insurance)
# - pnl_park: Mietaufwand Stellplätze (APCOA parking rental)
# - pnl_api: Sonstige Betriebsaufwendungen (telemetry / API fees)
# - pnl_tuev: Behördliche Gebühren (mandatory TÜV inspections)
# - pnl_sub: Sonstige (charging subscription)
# Plus original Nr. 8 items: HQ lease, IT cloud, legal/bookkeeping, HQ insurance,
# bank fees, GEZ/IHK fees, legal provisions (Zuführung Rückstellung Rechtsrisiken).
hgb_structure[loc["hgb_pos6"]] = (df_pnl_combined.loc[loc["pnl_ins"]] + df_pnl_combined.loc[loc["pnl_park"]] + df_pnl_combined.loc[loc["pnl_api"]] + df_pnl_combined.loc[loc["pnl_tuev"]] + df_pnl_combined.loc[loc["pnl_sub"]] + df_pnl_combined.loc[loc["pnl_hq_lease"]] + df_pnl_combined.loc[loc["pnl_it"]] + df_pnl_combined.loc[loc["pnl_legal"]] + df_pnl_combined.loc[loc["pnl_hq_ins"]] + df_pnl_combined.loc[loc["pnl_bank"]] + df_pnl_combined.loc[loc["pnl_fees"]] + df_pnl_combined.loc[loc["pnl_legal_prov"]]).values
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

# === fix: Rangrücktritt KPI reclassification ===
# When the SH loan toggle is on (notarized Rangrücktritt), banks treat it as
# wirtschaftliches Eigenkapital for Equity Ratio + Net LTV. We compute KPI-only
# adjusted figures: subtract SH balance from fin_debt; add to teq. The BS
# presentation itself remains unchanged — bs_sh_loan still sits under
# Verbindlichkeiten as required by HGB § 266 III C — this is purely a bank-
# style economic recharacterization for credit-relevant ratios.
sh_loan_bs_series = df_bs_combined.loc[loc["bs_sh_loan"]]
if sh_loan_rangruecktritt:
    fin_debt_kpi = fin_debt - sh_loan_bs_series  # remove from debt
    teq_kpi = teq + sh_loan_bs_series             # add to economic equity
else:
    fin_debt_kpi = fin_debt
    teq_kpi = teq

var_costs = rev_top - df_pnl_combined.loc[loc["pnl_db1"]]
fix_costs = df_pnl_combined.loc[loc["pnl_db1"]] - ebitda + df_pnl_combined.loc[loc["pnl_thg"]]
tot_costs = var_costs + fix_costs
debt_service = -(df_cf_combined.loc[loc["cf_prin"]] + df_pnl_combined.loc[loc["pnl_int_exp"]])
# === fix: Senior DSCR (bank debt only) ===
# `debt_service` above is the TOTAL fixed-charge denominator (principal + ALL interest
# including SH loan, VAT bridge, Kontokorrent). Banks compute DSCR using SENIOR debt
# service only — they treat subordinated shareholder loans as economic equity for credit
# purposes. Backing out SH-loan interest from the total int_exp gives the bank-relevant
# senior DSCR denominator. P_I_EX_SH is signed negative in the P&L (it's an expense),
# so we ADD it (i.e., subtract its magnitude) to remove it from debt_service.
# Result: senior_debt_service = (principal + total_int_exp - SH_int) flipped sign.
sh_int_exp_pos = -df_pnl_combined.loc[loc["pnl_int_exp_sh"]]  # P_I_EX_SH is negative, so this is positive
senior_debt_service = debt_service - sh_int_exp_pos          # remove SH from senior denominator
# === FCCR per an audit finding ===
# Operating lease expense is a fixed contractual cash obligation economically
# equivalent to senior debt service. Banks compute lease-adjusted coverage as:
# FCCR = (EBITDA + Lease Expense) / (Principal + Interest + Lease Expense)
# This is the right metric when comparing capital structures with different
# loan/lease mixes (Tranche A vs Tranche B from the capital structure
# matrix). Narrow DSCR (debt-only) preserved above for senior debt covenant tests.
lease_expense_pos = -df_pnl_combined.loc[loc["pnl_lease"]]  # P&L lease (negative) → positive expense
fixed_charges = debt_service + lease_expense_pos             # total fixed contractual obligations
ebitdar = ebitda + lease_expense_pos                          # EBITDA before lease (EBITDAR-equivalent)
other_inc = df_pnl_combined.loc[loc["pnl_thg"]]

kpi_dict = {}
kpi_dict[loc["kpi_db2_m"]] = [f"{x*100:.1f}%" for x in safe_div(db2, rev_top)]
kpi_dict[loc["kpi_var_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(var_costs, rev_top)]
kpi_dict[loc["kpi_fix_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(fix_costs, rev_top)]
kpi_dict[loc["kpi_tot_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(tot_costs, rev_top)]
kpi_dict[loc["kpi_other_inc_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(other_inc, rev_top)]
kpi_dict[loc["kpi_ebitda_m"]] = [f"{x*100:.1f}%" for x in safe_div(ebitda, rev_top)]
kpi_dict[loc["kpi_dscr"]] = [f"{x:.1f}x" if x > 0 else "n/a" for x in safe_div(ebitda, debt_service)]
kpi_dict[loc["kpi_dscr_senior"]] = [f"{x:.1f}x" if x > 0 else "n/a" for x in safe_div(ebitda, senior_debt_service)]
kpi_dict[loc["kpi_fccr"]] = [f"{x:.1f}x" if x > 0 else "n/a" for x in safe_div(ebitdar, fixed_charges)]
kpi_dict[loc["kpi_eq_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(teq_kpi, ta)]

# === Liquidity Runway denominator (seasonally stable) ===
# A monthly column's closing cash is divided by the CONTAINING YEAR's average
# monthly burn (annual ÷ 12), not by that single month's burn. Dividing by one
# month's burn would distort the figure, because energy seasonality (winter months
# burn more) and lumpy debt service (the month a balloon/residual principal clears)
# make a single month's burn unrepresentative. Yearly columns use the same
# year-average burn. So the monthly runway reads "this month's cash ÷ a typical
# month's burn", the intended decision-useful figure.
# The first 60 combined columns are the chronological monthly cohorts
# (df_pnl_mo) followed by the 5 yearly columns (df_pnl_yr), so a monthly
# column's year index is its position // 12 (clamped defensively to 0..4).
runway_arr = []
for _ci, col in enumerate(df_pnl_combined.columns):
    is_year = "Year" in col or "Jahr" in col
    if is_year:
        div = (fix_costs[col] + debt_service[col]) / 12
    else:
        _yr_idx = min(_ci // 12, 4)
        _yr_col = year_cols[_yr_idx]
        div = (fix_costs[_yr_col] + debt_service[_yr_col]) / 12
    rw = cash[col] / div if div > 0 else 999
    runway_arr.append(f"{rw:.1f} Mo." if rw < 999 else "Infinite")
kpi_dict[loc["kpi_runway"]] = runway_arr

net_debt = fin_debt_kpi - cash
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
# === Stacked liquidity-stress warnings (an audit finding — enhanced disclosure) ===
# Per § 15a InsO Antragspflicht: 3+ consecutive breach months trigger legal duty
# to file an Insolvenzantrag. Surface this prominently above general breach flags.
if legal_insolvency_month is not None:
    total_unfunded = sum(insolvency_severity)
    n_breach_months = len(insolvency_months)
    st.error(
        f"{loc['legal_insolv_warn']}{legal_insolvency_month}\n\n"
        f"📊 **{loc['insolv_severity_label']}:** €{total_unfunded:,.0f} "
        f"across {n_breach_months} breach month(s)\n\n"
        f"ℹ️ {loc['insolv_diagnostic_note']}"
    )
elif len(insolvency_months) > 0:
    # Breach detected but not yet 3 consecutive months — still flag prominently
    total_unfunded = sum(insolvency_severity)
    n_breach_months = len(insolvency_months)
    st.error(
        f"{loc['insolv_warn']}{', '.join(insolvency_months)}\n\n"
        f"📊 **{loc['insolv_severity_label']}:** €{total_unfunded:,.0f} "
        f"across {n_breach_months} breach month(s)"
    )
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

tabs = st.tabs([loc["tab_pnl"], loc["tab_hgb_pnl"], loc["tab_cf"], loc["tab_bs"], loc["tab_kpi"], loc["tab_ops"], loc["tab_charts"], loc["tab_mc"], loc["tab_readme"]])

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
    elif loc["kpi_fccr"] in row.name:
        return ['font-weight: 700; color: #38c172;'] * len(row)
    elif loc["kpi_net_ltv"] in row.name:
        return ['font-weight: 700; border-top: 1px solid #ffffff40;'] * len(row)
    return [''] * len(row)

with tabs[0]: st.dataframe(df_pnl_combined[display_cols].style.format("{:,.0f} €").apply(style_pnl_rows, axis=1), use_container_width=True)
with tabs[1]:
    st.dataframe(df_hgb_pnl[display_cols].style.format("{:,.0f} €").apply(style_pnl_rows, axis=1), use_container_width=True)
    # === FIX: EBITDA reconciliation bridge (Mgmt View → HGB View) ===
    # The `ebitda_recon_title` bridge: end-of-life fleet disposal gains (§ 275 Abs. 2
    # Nr. 4 HGB) lift the HGB-view EBITDA above the management EBITDA, and this bridge
    # shows that reconciling item. By construction it foots exactly:
    # mgmt EBITDA + Anlagenabgang (pnl_salvage = fleet_sale_rev) = HGB EBITDA.
    st.markdown(f"**{loc['ebitda_recon_title']}**")
    _recon_bridge = pd.DataFrame({
        loc["pnl_ebitda"]: df_pnl_combined.loc[loc["pnl_ebitda"]],
        loc["pnl_salvage"]: df_pnl_combined.loc[loc["pnl_salvage"]],
        loc["pnl_ebitda_hgb"]: df_pnl_combined.loc[loc["pnl_ebitda_hgb"]],
    }).T
    st.dataframe(_recon_bridge[display_cols].style.format("{:,.0f} €").apply(style_pnl_rows, axis=1), use_container_width=True)
    st.caption(loc["ebitda_recon_caption"])
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
            * **Liquidity Runway:** A worst-case stress test tracking survival time if revenues instantly drop to zero. Calculated as *Cash Balance / Average Monthly Burn (Fixed Overhead + Debt Service)*. The **yearly columns are the reliable read** — they divide by the year's average monthly burn (annual ÷ 12). Monthly columns divide that month's closing cash by the **same containing-year average burn**, so a single seasonal month (winter energy spike, or a month a balloon/residual principal clears) no longer distorts the figure.
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
            * **Liquiditätsreichweite:** Ein Stress-Test-Szenario, das die Überlebenszeit bei plötzlichem Umsatzausfall prognostiziert. Berechnung: *Kassenbestand / durchschnittlicher monatlicher Mittelabfluss (Fixkosten + Schuldendienst)*. Die **Jahresspalten sind der maßgebliche Wert** — sie teilen durch den durchschnittlichen monatlichen Mittelabfluss des Jahres (Jahreswert ÷ 12). Monatsspalten teilen den Endbestand des Monats durch **denselben Jahresdurchschnitt**, sodass ein einzelner saisonaler Monat (Winter-Energiespitze oder ein Monat, in dem eine Ballon-/Restschuldtilgung anfällt) die Kennzahl nicht mehr verzerrt.
            * **Netto-LTV:** Misst den Netto-Verschuldungsgrad unseres Anlagevermögens unter Berücksichtigung des Cash-Bestands. Berechnung: *(Summe Finanzverbindlichkeiten - Kasse) / Netto-Sachanlagen*.
            * **Variable Kostenquote:** Gibt an, wie viel Prozent jedes erwirtschafteten Euros direkt für den Betrieb der Fahrzeuge aufgewendet werden. Berechnung: *Variable Kosten / Netto-Umsatzerlöse*.
            * **Fixkostenquote:** Zeigt den prozentualen Anteil des Umsatzes, der durch die feste Unternehmensinfrastruktur aufgezehrt wird. Berechnung: *Fixkosten / Netto-Umsatzerlöse*.
            * **Gesamtkostenquote:** Bildet die gesamte betriebliche Kostenstruktur des operativen Geschäfts ab. Berechnung: *Gesamte betriebliche Kosten / Netto-Umsatzerlöse*.
            * **Sonstige Ertragsquote:** Die Nicht-Kernumsatzmarge (THG-Prämien), die als Nebenprodukt des Betriebs generiert wird.
            * **Deckungsbeitragsmarge (DB2):** Zeigt die reine Rentabilität der Fahrzeugflotte vor Abzug der HQ-Verwaltungskosten. Berechnung: *Deckungsbeitrag 2 / Netto-Umsatzerlöse*.
            * **EBITDA-Marge:** Der zentrale Indikator für die operative Cash-Rentabilität des Unternehmens. Mathematische Abstimmung: *EBITDA-Marge = 100% - Variable Quote - Fixe Quote + Sonstige Ertragsquote*.
            """)

with tabs[5]:
    st.markdown(f"### {loc['ops_header']}")
    st.caption(loc["ops_caption"])

    _cols = df_pnl_combined.columns

    def _S(name):
        return df_ops_combined.loc[name]

    def _sd(n, d):
        return (n / d.replace(0, np.nan)).fillna(0.0)

    total_km    = _S("ops_total_km")
    billable_km = _S("ops_billable_km")
    deadhead_km = _S("ops_deadhead_km")
    pax_trips   = _S("ops_pax_trips")
    del_trips   = _S("ops_delivery_trips")
    total_trips = pax_trips + del_trips

    net_rev = df_pnl_combined.loc[loc["pnl_net_rev"]] + df_pnl_combined.loc[loc["pnl_delivery_net_rev"]]
    gbv     = df_pnl_combined.loc[loc["pnl_gbv"]] + df_pnl_combined.loc[loc["pnl_delivery_gbv"]]
    energy_c = -df_pnl_combined.loc[loc["pnl_energy"]]
    wear_c   = -df_pnl_combined.loc[loc["pnl_wear"]]
    # Cleaning cost actually borne = gross cleaning expense minus the passenger
    # fee income that offsets it (the net figure that hits EBITDA).
    clean_net_c = (-df_pnl_combined.loc[loc["pnl_clean"]]) - df_pnl_combined.loc[loc["pnl_clean_fee"]]
    ebitda_v = df_pnl_combined.loc[loc["pnl_ebitda"]]

    # Active fleet per displayed column (monthly cols -> that month; yearly -> mean)
    _fleet = []
    for _ci, _col in enumerate(_cols):
        if _col in year_cols:
            _yi = year_cols.index(_col)
            _fleet.append(float(np.mean(active_fleet_by_month[_yi * 12:(_yi + 1) * 12])))
        else:
            _fleet.append(float(active_fleet_by_month[_ci]))
    fleet_s = pd.Series(_fleet, index=_cols)

    varcost_km = _sd(energy_c + wear_c + clean_net_c, total_km)
    rev_km = _sd(net_rev, total_km)
    contrib_km = rev_km - varcost_km
    energy_kwh = total_km * energy_kwh_per_km

    ops = {}
    ops[loc["ops_total_km"]]      = [f"{x:,.0f}" for x in total_km]
    ops[loc["ops_billable_km"]]   = [f"{x:,.0f}" for x in billable_km]
    ops[loc["ops_deadhead_km"]]   = [f"{x:,.0f}" for x in deadhead_km]
    ops[loc["ops_deadhead_ratio"]] = [f"{x*100:,.1f}%" for x in _sd(deadhead_km, total_km)]
    ops[loc["ops_pax_trips"]]     = [f"{x:,.0f}" for x in pax_trips]
    ops[loc["ops_delivery_trips"]] = [f"{x:,.0f}" for x in del_trips]
    ops[loc["ops_km_per_veh"]]    = [f"{x:,.0f}" for x in _sd(total_km, fleet_s)]
    ops[loc["ops_trips_per_veh"]] = [f"{x:,.0f}" for x in _sd(total_trips, fleet_s)]
    ops[loc["ops_avg_fleet"]]     = [f"{x:,.1f}" for x in fleet_s]
    ops[loc["ops_netrev_veh"]]    = [f"€{x:,.0f}" for x in _sd(net_rev, fleet_s)]
    ops[loc["ops_ebitda_veh"]]    = [f"€{x:,.0f}" for x in _sd(ebitda_v, fleet_s)]
    ops[loc["ops_rev_km"]]        = [f"€{x:,.3f}" for x in rev_km]
    ops[loc["ops_gbv_km"]]        = [f"€{x:,.3f}" for x in _sd(gbv, total_km)]
    ops[loc["ops_energy_km"]]     = [f"€{x:,.3f}" for x in _sd(energy_c, total_km)]
    ops[loc["ops_wear_km"]]       = [f"€{x:,.3f}" for x in _sd(wear_c, total_km)]
    ops[loc["ops_clean_km"]]      = [f"€{x:,.3f}" for x in _sd(clean_net_c, total_km)]
    ops[loc["ops_varcost_km"]]    = [f"€{x:,.3f}" for x in varcost_km]
    ops[loc["ops_contrib_km"]]    = [f"€{x:,.3f}" for x in contrib_km]
    ops[loc["ops_rev_trip"]]      = [f"€{x:,.2f}" for x in _sd(net_rev, total_trips)]
    ops[loc["ops_energy_kwh"]]    = [f"{x:,.0f}" for x in energy_kwh]
    df_ops_kpi = pd.DataFrame(ops, index=_cols).T

    # Headline lifetime (5-year) metrics
    _days = []
    for _m in range(60):
        _cy = 2028 + _m // 12
        _mo = (_m % 12) + 1
        _days.append(calendar.monthrange(_cy, _mo)[1])
    _veh_days = sum(active_fleet_by_month[_m] * _days[_m] for _m in range(60))
    _life_total_km = float(sum(df_ops_combined.loc["ops_total_km"][c] for c in month_col_names))
    _life_billable = float(sum(df_ops_combined.loc["ops_billable_km"][c] for c in month_col_names))
    _life_deadhead = _life_total_km - _life_billable
    _km_veh_day = _life_total_km / _veh_days if _veh_days > 0 else 0.0
    _life_net_rev = float(sum((df_pnl_combined.loc[loc["pnl_net_rev"]][c] + df_pnl_combined.loc[loc["pnl_delivery_net_rev"]][c]) for c in month_col_names))
    _rev_km_life = _life_net_rev / _life_total_km if _life_total_km > 0 else 0.0
    _dh_life = (_life_deadhead / _life_total_km * 100) if _life_total_km > 0 else 0.0

    _hc1, _hc2, _hc3, _hc4 = st.columns(4)
    _hc1.metric(loc["ops_m_total_km"], f"{_life_total_km:,.0f} km")
    _hc2.metric(loc["ops_m_km_veh_day"], f"{_km_veh_day:,.0f} km")
    _hc3.metric(loc["ops_m_deadhead"], f"{_dh_life:,.1f}%")
    _hc4.metric(loc["ops_m_rev_km"], f"€{_rev_km_life:,.3f}")

    st.dataframe(df_ops_kpi[display_cols], use_container_width=True)

    _y_km = [float(df_ops_combined.loc["ops_total_km"][yc]) for yc in year_cols]
    _y_kmveh = []
    for _i in range(5):
        _f = np.mean(active_fleet_by_month[_i * 12:(_i + 1) * 12])
        _y_kmveh.append(float(df_ops_combined.loc["ops_total_km"][year_cols[_i]]) / _f if _f > 0 else 0.0)
    _oc1, _oc2 = st.columns(2)
    with _oc1:
        st.plotly_chart(create_mrrg_chart(year_cols, _y_km, loc["ops_chart_total_km"], prefix="", suffix=" km"), use_container_width=True)
    with _oc2:
        st.plotly_chart(create_mrrg_chart(year_cols, _y_kmveh, loc["ops_chart_km_veh"], prefix="", suffix=" km"), use_container_width=True)


with tabs[6]:
    # NOTE: df_pnl_yr / df_cf_yr / df_bs_yr were never renamed (only df_*_combined were).
    # They retain the raw short keys ("pnl_net_rev" etc.), so we MUST look up by raw key
    # rather than by loc[...]. Using loc[...] here would KeyError.
    # === Net Revenue chart matches the KPI engine ===
    # The KPI engine computes rev_top = pnl_net_rev + pnl_delivery_net_rev, and this
    # chart reads the same combined figure so the two tabs stay consistent when the
    # delivery toggle is on. When delivery_enabled=False the second term is zero and
    # the chart shows passenger revenue only.
    y_rev_v = (df_pnl_yr.loc["pnl_net_rev"] + df_pnl_yr.loc["pnl_delivery_net_rev"]).values
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


#
# === MONTE CARLO — PATH-DEPENDENT, CORRELATED, FAT-TAILED ===
#
# The simulation is path-dependent: each of the five years is rolled
# independently and its macro shock is applied IN-PLACE to that year's months,
# rather than averaging the five years into one number before the engine runs.
# Averaging would erase the single-bad-year tail — and a thinly-capitalised
# startup fails from ONE catastrophic year hitting while cash is low, not from a
# mild five-year average drag.
#
# How it works: the engine accepts two optional per-year arrays
# (macro_demand_mult_by_year, macro_energy_mult_by_year), each 5 elements,
# defaulting to neutral [1,1,1,1,1]. Inside the 60-month loop the engine applies
# THIS YEAR's multiplier in-place: a crisis in Year 2 collapses demand and spikes
# energy in months 13-24 specifically, dragging cash below zero in real time. With
# neutral arrays (the deterministic path) the engine is unaffected.
#
# The MC harness:
#   • draws 5 independent annual macro shocks
#   • rolls each of the 5 years' shock library independently
#   • converts each YEAR's macro shock + shock-cost-coupling into a per-year demand
#     multiplier and per-year energy multiplier (kept as 5-arrays, NOT averaged)
#   • builds a per-year 12-month demand-texture seasonality vector and passes the
#     worst-case-preserving per-year arrays straight into the engine
#   • applies the horizon-average macro tug to the SCALAR rate/FX inputs the engine
#     consumes by cohort (rates lock at purchase, so the cohort-year tug is applied
#     to each cohort's origination year — see per-cohort rate handling below)
#
with tabs[7]:
    st.markdown(f"### {loc['mc_header']}")
    st.caption(loc["mc_intro"])

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

    # ===== Macro coupling controls =====
    with st.expander(loc["mc_macro_header"], expanded=False):
        st.caption(loc["mc_macro_help"])
        mac1, mac2, mac3 = st.columns(3)
        with mac1:
            beta_energy = st.number_input(loc["mc_beta_energy"], value=0.060, min_value=0.0, max_value=0.30, step=0.005, format="%.3f")
            beta_fx = st.number_input(loc["mc_beta_fx"], value=0.030, min_value=0.0, max_value=0.30, step=0.005, format="%.3f")
        with mac2:
            beta_rate = st.number_input(loc["mc_beta_rate"], value=0.010, min_value=0.0, max_value=0.05, step=0.001, format="%.3f")
        with mac3:
            beta_demand = st.number_input(loc["mc_beta_demand"], value=0.050, min_value=0.0, max_value=0.30, step=0.005, format="%.3f")
            macro_sigma = st.number_input(loc["mc_macro_sigma"], value=1.0, min_value=0.0, max_value=3.0, step=0.1, format="%.1f")

    with st.expander(loc["mc_section_dist"], expanded=False):
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
            # === FIX: triangular MODE = live sidebar base (tesla_take_rate) ===
            # The triangular mode IS the live base case and the user controls only the %
            # uncertainty band, which shifts automatically when the sidebar value changes.
            # Default down/up of 0% / +20% give a band from the base to +20%.
            st.caption(f"Tesla Take-Rate mode = base case {tesla_take_rate:.2f} (tracks sidebar)")
            mc_take_down = st.number_input("Tesla Take − downside %", value=0.00, min_value=0.0, max_value=0.90, step=0.05, format="%.2f")
            mc_take_up = st.number_input("Tesla Take + upside %", value=0.20, min_value=0.0, max_value=2.0, step=0.05, format="%.2f")
            mc_take_mode = tesla_take_rate
            mc_take_min = max(0.0, mc_take_mode * (1.0 - mc_take_down))
            mc_take_max = mc_take_mode * (1.0 + mc_take_up)

        st.markdown("**Delivery Ramp Uncertainty (Triangular Y2/Y3/Y4)**")
        # === FIX: delivery-ramp triangular MODE = live sidebar base ramps ===
        # Additive bands (the base can be 0, so a % band would be degenerate).
        st.caption(f"Modes track sidebar base ramps — Y2 {delivery_ramp_y2:.2f} / Y3 {delivery_ramp_y3:.2f} / Y4 {delivery_ramp_y4:.2f}")
        d_c1, d_c2, d_c3 = st.columns(3)
        with d_c1:
            mc_dy2_down = st.number_input("Delivery Y2 − downside", value=0.00, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy2_up = st.number_input("Delivery Y2 + upside", value=0.30, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy2_mode = delivery_ramp_y2
            mc_dy2_min = max(0.0, mc_dy2_mode - mc_dy2_down)
            mc_dy2_max = min(1.0, mc_dy2_mode + mc_dy2_up)
        with d_c2:
            mc_dy3_down = st.number_input("Delivery Y3 − downside", value=0.30, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy3_up = st.number_input("Delivery Y3 + upside", value=0.30, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy3_mode = delivery_ramp_y3
            mc_dy3_min = max(0.0, mc_dy3_mode - mc_dy3_down)
            mc_dy3_max = min(1.0, mc_dy3_mode + mc_dy3_up)
        with d_c3:
            mc_dy4_down = st.number_input("Delivery Y4 − downside", value=0.40, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy4_up = st.number_input("Delivery Y4 + upside", value=0.30, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
            mc_dy4_mode = delivery_ramp_y4
            mc_dy4_min = max(0.0, mc_dy4_mode - mc_dy4_down)
            mc_dy4_max = min(1.0, mc_dy4_mode + mc_dy4_up)

        st.markdown(f"**{loc['mc_tier2_header']}**")
        t2c1, t2c2, t2c3 = st.columns(3)
        with t2c1:
            mc_sigma_capex = st.number_input(loc["mc_p_capex"], value=2500.0, min_value=500.0, max_value=10000.0, step=500.0)
            mc_sigma_fx = st.number_input(loc["mc_p_fx"], value=0.05, min_value=0.01, max_value=0.20, step=0.01, format="%.2f")
            mc_sigma_ltv = st.number_input(loc["mc_p_ltv"], value=0.05, min_value=0.01, max_value=0.20, step=0.01, format="%.2f")
        with t2c2:
            # === FIX: Y1 loan-rate mode = live base (y1_loan_rate), % band ===
            st.caption(f"Y1 Loan mode = base {y1_loan_rate:.3f}")
            mc_loan_y1_down = st.number_input("Y1 Loan − downside %", value=0.2222, min_value=0.0, max_value=0.90, step=0.01, format="%.2f")
            mc_loan_y1_up = st.number_input("Y1 Loan + upside %", value=0.6667, min_value=0.0, max_value=3.0, step=0.05, format="%.2f")
            mc_loan_y1_mode = y1_loan_rate
            mc_loan_y1_min = max(0.0, mc_loan_y1_mode * (1.0 - mc_loan_y1_down))
            mc_loan_y1_max = mc_loan_y1_mode * (1.0 + mc_loan_y1_up)
        with t2c3:
            # === FIX: Y2 loan-rate mode = live base (y2_loan_rate), % band ===
            st.caption(f"Y2 Loan mode = base {y2_loan_rate:.3f}")
            mc_loan_y2_down = st.number_input("Y2 Loan − downside %", value=0.1818, min_value=0.0, max_value=0.90, step=0.01, format="%.2f")
            mc_loan_y2_up = st.number_input("Y2 Loan + upside %", value=0.5455, min_value=0.0, max_value=3.0, step=0.05, format="%.2f")
            mc_loan_y2_mode = y2_loan_rate
            mc_loan_y2_min = max(0.0, mc_loan_y2_mode * (1.0 - mc_loan_y2_down))
            mc_loan_y2_max = mc_loan_y2_mode * (1.0 + mc_loan_y2_up)

        t2d1, t2d2, t2d3 = st.columns(3)
        with t2d1:
            # === FIX: insurance mode = live base (insurance_pm), % band ===
            # Defaults give a −22.22% / +55.56% band around the base.
            st.caption(f"Insurance mode = base €{insurance_pm:.0f}/mo")
            mc_ins_down = st.number_input("Insurance − downside %", value=0.2222, min_value=0.0, max_value=0.90, step=0.01, format="%.2f")
            mc_ins_up = st.number_input("Insurance + upside %", value=0.5556, min_value=0.0, max_value=3.0, step=0.05, format="%.2f")
            mc_ins_mode = insurance_pm
            mc_ins_min = max(0.0, mc_ins_mode * (1.0 - mc_ins_down))
            mc_ins_max = mc_ins_mode * (1.0 + mc_ins_up)
        with t2d2:
            mc_sigma_energy_eur = st.number_input(loc["mc_p_energy_eur"], value=0.040, min_value=0.001, max_value=0.20, step=0.005, format="%.3f")
            mc_sigma_kwh = st.number_input(loc["mc_p_kwh_per_km"], value=0.012, min_value=0.001, max_value=0.05, step=0.001, format="%.3f")

        st.markdown(f"**{loc['mc_tier3_header']}**")
        t3c1, t3c2, t3c3 = st.columns(3)
        with t3c1:
            # === lognormal cost sigma defaults — genuinely fat tails ===
            # The mean-preserving lognormal shape (the "exploding repair bill" curve)
            # gives the right tail real-world weight: cleaning sigma 0.80 (log-sigma
            # ~0.40), wear 0.030 (~0.30), parking 45 (~0.26) produce the 2-3x overrun
            # years that justify the skewed shape (drivetrain/sensor failure clusters,
            # vandalism waves, deep-clean seasons). Mean-preserving, so the CENTER of
            # the distribution is the sidebar value; only the right tail is heavy.
            # User-overridable.
            mc_sigma_cleaning = st.number_input(loc["mc_p_cleaning"], value=0.80, min_value=0.05, max_value=3.0, step=0.05, format="%.2f")
            mc_sigma_wear = st.number_input(loc["mc_p_wear"], value=0.030, min_value=0.001, max_value=0.05, step=0.001, format="%.3f")
        with t3c2:
            mc_sigma_parking = st.number_input(loc["mc_p_parking"], value=45.0, min_value=5.0, max_value=100.0, step=5.0, format="%.1f")
            mc_sigma_customs = st.number_input(loc["mc_p_customs"], value=0.025, min_value=0.005, max_value=0.10, step=0.005, format="%.3f")
        with t3c3:
            mc_sigma_salvage = st.number_input(loc["mc_p_salvage"], value=2500.0, min_value=500.0, max_value=10000.0, step=500.0)

    # === PHASE A — Day archetype mix UI ===
    with st.expander(loc["mc_dayarch_header"], expanded=False):
        st.caption(loc["mc_dayarch_help"])
        da_c1, da_c2, da_c3 = st.columns(3)
        with da_c1:
            st.markdown("**Days/Year (Frequency)**")
            arch_weekday_days = st.number_input(loc["mc_dayarch_weekday"] + " days/yr", value=155, min_value=100, max_value=260, step=5)
            arch_weekend_days = st.number_input(loc["mc_dayarch_weekend"] + " days/yr", value=80, min_value=40, max_value=110, step=5)
            arch_friday_days = st.number_input(loc["mc_dayarch_friday"] + " days/yr", value=40, min_value=20, max_value=80, step=5)
            arch_holiday_days = st.number_input(loc["mc_dayarch_holiday"] + " days/yr", value=30, min_value=10, max_value=80, step=5)
            arch_oktober_days = st.number_input(loc["mc_dayarch_oktoberfest"] + " days/yr", value=16, min_value=0, max_value=20, step=1)
            arch_xmas_days = st.number_input(loc["mc_dayarch_xmas"] + " days/yr", value=28, min_value=0, max_value=40, step=2)
        with da_c2:
            st.markdown("**Demand Multiplier (mean)**")
            arch_weekday_mult = st.number_input(loc["mc_dayarch_weekday"] + " ×", value=1.00, min_value=0.50, max_value=2.00, step=0.05, format="%.2f")
            arch_weekend_mult = st.number_input(loc["mc_dayarch_weekend"] + " ×", value=0.90, min_value=0.50, max_value=2.00, step=0.05, format="%.2f")
            arch_friday_mult = st.number_input(loc["mc_dayarch_friday"] + " ×", value=1.25, min_value=0.50, max_value=2.50, step=0.05, format="%.2f")
            arch_holiday_mult = st.number_input(loc["mc_dayarch_holiday"] + " ×", value=0.70, min_value=0.30, max_value=1.50, step=0.05, format="%.2f")
            arch_oktober_mult = st.number_input(loc["mc_dayarch_oktoberfest"] + " ×", value=1.60, min_value=1.00, max_value=2.50, step=0.05, format="%.2f")
            arch_xmas_mult = st.number_input(loc["mc_dayarch_xmas"] + " ×", value=1.35, min_value=0.80, max_value=2.00, step=0.05, format="%.2f")
        with da_c3:
            st.markdown("**Demand Multiplier σ (variance)**")
            arch_weekday_sigma = st.number_input(loc["mc_dayarch_weekday"] + " σ", value=0.05, min_value=0.01, max_value=0.30, step=0.01, format="%.2f")
            arch_weekend_sigma = st.number_input(loc["mc_dayarch_weekend"] + " σ", value=0.08, min_value=0.01, max_value=0.30, step=0.01, format="%.2f")
            arch_friday_sigma = st.number_input(loc["mc_dayarch_friday"] + " σ", value=0.10, min_value=0.01, max_value=0.30, step=0.01, format="%.2f")
            arch_holiday_sigma = st.number_input(loc["mc_dayarch_holiday"] + " σ", value=0.12, min_value=0.01, max_value=0.40, step=0.01, format="%.2f")
            arch_oktober_sigma = st.number_input(loc["mc_dayarch_oktoberfest"] + " σ", value=0.20, min_value=0.05, max_value=0.50, step=0.05, format="%.2f")
            arch_xmas_sigma = st.number_input(loc["mc_dayarch_xmas"] + " σ", value=0.15, min_value=0.05, max_value=0.40, step=0.05, format="%.2f")

    # === PHASE B — Shock events UI (incl. demand-collapse) ===
    with st.expander(loc["mc_shock_header"], expanded=False):
        st.caption(loc["mc_shock_help"])
        sh_c1, sh_c2, sh_c3 = st.columns(3)
        with sh_c1:
            st.markdown("**Annual Frequency (days)**")
            shock_weather_freq = st.number_input(loc["mc_shock_severe_weather"] + " days/yr", value=12, min_value=0, max_value=40, step=1)
            shock_strike_freq = st.number_input(loc["mc_shock_transit_strike"] + " days/yr", value=2, min_value=0, max_value=15, step=1)
            shock_event_freq = st.number_input(loc["mc_shock_major_event"] + " days/yr", value=15, min_value=0, max_value=50, step=1)
            shock_tech_freq = st.number_input(loc["mc_shock_tech_outage"] + " days/yr", value=3, min_value=0, max_value=20, step=1)
            shock_heat_freq = st.number_input(loc["mc_shock_heatwave"] + " days/yr", value=10, min_value=0, max_value=30, step=1)
            shock_ice_freq = st.number_input(loc["mc_shock_black_ice"] + " days/yr", value=5, min_value=0, max_value=20, step=1)
            shock_road_freq = st.number_input(loc["mc_shock_road_closure"] + " days/yr", value=7, min_value=0, max_value=30, step=1)
            shock_collapse_freq = st.number_input(loc["mc_shock_demand_collapse"] + " days/yr", value=2, min_value=0, max_value=60, step=1)
        with sh_c2:
            st.markdown("**Demand Multiplier (mean)**")
            shock_weather_mult = st.number_input(loc["mc_shock_severe_weather"] + " ×", value=1.20, min_value=0.50, max_value=2.50, step=0.05, format="%.2f")
            shock_strike_mult = st.number_input(loc["mc_shock_transit_strike"] + " ×", value=1.50, min_value=0.50, max_value=2.50, step=0.05, format="%.2f")
            shock_event_mult = st.number_input(loc["mc_shock_major_event"] + " ×", value=1.30, min_value=0.50, max_value=2.50, step=0.05, format="%.2f")
            shock_tech_mult = st.number_input(loc["mc_shock_tech_outage"] + " ×", value=0.50, min_value=0.00, max_value=1.00, step=0.05, format="%.2f")
            shock_heat_mult = st.number_input(loc["mc_shock_heatwave"] + " ×", value=1.05, min_value=0.50, max_value=2.00, step=0.05, format="%.2f")
            shock_ice_mult = st.number_input(loc["mc_shock_black_ice"] + " ×", value=1.10, min_value=0.50, max_value=2.00, step=0.05, format="%.2f")
            shock_road_mult = st.number_input(loc["mc_shock_road_closure"] + " ×", value=0.85, min_value=0.30, max_value=1.50, step=0.05, format="%.2f")
            shock_collapse_mult = st.number_input(loc["mc_shock_demand_collapse"] + " ×", value=0.25, min_value=0.00, max_value=1.00, step=0.05, format="%.2f")
        with sh_c3:
            st.markdown("**Multiplier σ (variance)**")
            shock_weather_sigma = st.number_input(loc["mc_shock_severe_weather"] + " σ", value=0.15, min_value=0.01, max_value=0.50, step=0.05, format="%.2f")
            shock_strike_sigma = st.number_input(loc["mc_shock_transit_strike"] + " σ", value=0.20, min_value=0.05, max_value=0.50, step=0.05, format="%.2f")
            shock_event_sigma = st.number_input(loc["mc_shock_major_event"] + " σ", value=0.15, min_value=0.05, max_value=0.50, step=0.05, format="%.2f")
            shock_tech_sigma = st.number_input(loc["mc_shock_tech_outage"] + " σ", value=0.20, min_value=0.01, max_value=0.50, step=0.05, format="%.2f")
            shock_heat_sigma = st.number_input(loc["mc_shock_heatwave"] + " σ", value=0.10, min_value=0.01, max_value=0.30, step=0.05, format="%.2f")
            shock_ice_sigma = st.number_input(loc["mc_shock_black_ice"] + " σ", value=0.12, min_value=0.01, max_value=0.30, step=0.05, format="%.2f")
            shock_road_sigma = st.number_input(loc["mc_shock_road_closure"] + " σ", value=0.10, min_value=0.01, max_value=0.30, step=0.05, format="%.2f")
            shock_collapse_sigma = st.number_input(loc["mc_shock_demand_collapse"] + " σ", value=0.15, min_value=0.01, max_value=0.50, step=0.05, format="%.2f")

    # ============ MONTE CARLO EXECUTION ============
    if run_mc:
        def _sample_beta_scaled(rng, mean, a, b, concentration=10.0):
            mean_unit = (mean - a) / (b - a) if (b - a) > 0 else 0.5
            mean_unit = max(0.01, min(0.99, mean_unit))
            alpha = mean_unit * concentration
            beta_param = (1 - mean_unit) * concentration
            return a + rng.beta(alpha, beta_param) * (b - a)

        def _sample_triangular(rng, low, mode, high):
            if low > high:
                low, high = high, low
            mode = max(low, min(high, mode))
            #: a zero-width band (user set both spreads to 0) would make
            # np.triangular raise (requires left < right). Degenerate → return the mode.
            if high - low < 1e-12:
                return mode
            return rng.triangular(low, mode, high)

        # === Mean-preserving skewed (lognormal) one-sided cost draw ===
        def _sample_cost_skewed(rng, center, sigma_pct):
            if center <= 0:
                return 0.0
            sigma_log = max(1e-6, sigma_pct)
            mu_log = np.log(center) - 0.5 * sigma_log ** 2
            return float(rng.lognormal(mean=mu_log, sigma=sigma_log))

        month_arch_policy = {
            1:  [0.55, 0.27, 0.14, 0.04, 0.00, 0.00],
            2:  [0.55, 0.27, 0.14, 0.04, 0.00, 0.00],
            3:  [0.60, 0.27, 0.13, 0.00, 0.00, 0.00],
            4:  [0.55, 0.27, 0.13, 0.05, 0.00, 0.00],
            5:  [0.58, 0.27, 0.13, 0.02, 0.00, 0.00],
            6:  [0.60, 0.27, 0.13, 0.00, 0.00, 0.00],
            7:  [0.55, 0.27, 0.13, 0.05, 0.00, 0.00],
            8:  [0.45, 0.27, 0.13, 0.15, 0.00, 0.00],
            9:  [0.45, 0.20, 0.10, 0.05, 0.20, 0.00],
            10: [0.50, 0.22, 0.10, 0.03, 0.15, 0.00],
            11: [0.50, 0.25, 0.13, 0.02, 0.00, 0.10],
            12: [0.30, 0.20, 0.13, 0.07, 0.00, 0.30],
        }
        days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

        shock_month_weights = [
            np.ones(12) / 12.0,
            np.ones(12) / 12.0,
            np.ones(12) / 12.0,
            np.ones(12) / 12.0,
            np.array([0, 0, 0, 0, 0, 0.20, 0.40, 0.30, 0.10, 0, 0, 0]),
            np.array([0.30, 0.25, 0.10, 0, 0, 0, 0, 0, 0, 0, 0.05, 0.30]),
            np.ones(12) / 12.0,
            np.ones(12) / 12.0,
        ]
        shock_cost_energy_bump = [0.25, 0.0, 0.0, 0.0, 0.10, 0.30, 0.0, 0.0]
        shock_cost_wear_bump   = [0.15, 0.0, 0.0, 0.0, 0.05, 0.25, 0.0, 0.0]

        def _sample_one_year(rng, macro_shock):
            """
            Sample ONE simulated year. Returns:
              monthly_demand_mods : dict {1..12 -> demand multiplier}
              energy_cost_mult    : scalar
              wear_cost_mult      : scalar
              arch_intensities    : 6-vector
              shock_counts        : dict of this year's shock-day counts
            The macro_shock (this year's draw) tugs DEMAND down via beta_demand
            INSIDE this single year — preserved per-year (no averaging).
            """
            arch_w  = max(0.40, rng.normal(arch_weekday_mult, arch_weekday_sigma))
            arch_we = max(0.40, rng.normal(arch_weekend_mult, arch_weekend_sigma))
            arch_f  = max(0.40, rng.normal(arch_friday_mult, arch_friday_sigma))
            arch_h  = max(0.20, rng.normal(arch_holiday_mult, arch_holiday_sigma))
            arch_o  = max(0.50, rng.normal(arch_oktober_mult, arch_oktober_sigma))
            arch_x  = max(0.50, rng.normal(arch_xmas_mult, arch_xmas_sigma))
            arch_intensities = np.array([arch_w, arch_we, arch_f, arch_h, arch_o, arch_x])

            mods = {}
            for mth in range(1, 13):
                policy_row = np.array(month_arch_policy[mth])
                mods[mth] = float(np.sum(policy_row * arch_intensities))

            shock_specs = [
                (shock_weather_freq, shock_weather_mult, shock_weather_sigma),
                (shock_strike_freq,  shock_strike_mult,  shock_strike_sigma),
                (shock_event_freq,   shock_event_mult,   shock_event_sigma),
                (shock_tech_freq,    shock_tech_mult,    shock_tech_sigma),
                (shock_heat_freq,    shock_heat_mult,    shock_heat_sigma),
                (shock_ice_freq,     shock_ice_mult,     shock_ice_sigma),
                (shock_road_freq,    shock_road_mult,    shock_road_sigma),
                (shock_collapse_freq, shock_collapse_mult, shock_collapse_sigma),
            ]
            shock_type_names = ["weather", "strike", "event", "tech", "heat", "ice", "road", "collapse"]
            shock_impact_sum_by_month = np.zeros(12)
            year_energy_extra = 0.0
            year_wear_extra = 0.0
            total_shock_days = 0
            shock_counts = {}
            for idx, (freq, mult, sigma) in enumerate(shock_specs):
                count = int(rng.poisson(freq))
                shock_counts[shock_type_names[idx]] = count
                if count == 0:
                    continue
                avg_mult = max(0.0, rng.normal(mult, sigma))
                weights = shock_month_weights[idx]
                month_distribution = rng.multinomial(count, weights)
                for m_idx in range(12):
                    shock_impact_sum_by_month[m_idx] += (avg_mult - 1.0) * month_distribution[m_idx]
                year_energy_extra += shock_cost_energy_bump[idx] * count
                year_wear_extra += shock_cost_wear_bump[idx] * count
                total_shock_days += count

            for mth in range(1, 13):
                dim = days_per_month[mth - 1]
                shock_contribution = shock_impact_sum_by_month[mth - 1] / dim
                # macro crisis tugs demand DOWN inside THIS year (preserved per-year)
                macro_demand_tug = -beta_demand * macro_shock
                mods[mth] = max(0.20, mods[mth] + shock_contribution + macro_demand_tug)

            energy_cost_mult = 1.0 + (year_energy_extra / 365.0)
            wear_cost_mult = 1.0 + (year_wear_extra / 365.0)

            return mods, energy_cost_mult, wear_cost_mult, arch_intensities, shock_counts

        simulation_settings = {
            "iterations": int(n_iterations),
            "seed": 42,
            "delivery_enabled": delivery_enabled,
            "max_overdraft_limit": max_overdraft_limit,
            "min_cash_buffer": min_cash_buffer,
            "lang_choice": lang_choice,
            "util_mode": util_mode,
            "vat_lag_months": vat_lag_months,
            "macro_betas": {
                "beta_energy": beta_energy, "beta_rate": beta_rate,
                "beta_demand": beta_demand, "beta_fx": beta_fx,
                "macro_sigma": macro_sigma,
            },
            "baseline_centers": {
                "active_hours_per_day": active_hours_per_day, "avg_speed_kmh": avg_speed_kmh,
                "deadhead_rate": deadhead_rate, "target_util": target_util, "init_util": init_util,
                "rec_rate": rec_rate, "can_fac": can_fac, "avg_trip_distance_km": avg_trip_distance_km,
                "dwell_time_mins": dwell_time_mins, "price_per_km_eur": price_per_km_eur,
                "tesla_take_rate": tesla_take_rate, "cleaning_cost_per_day": cleaning_cost_per_day,
                "wear_and_tear_rate": wear_and_tear_rate, "energy_kwh_per_km": energy_kwh_per_km,
                "energy_eur_per_kwh": energy_eur_per_kwh, "charging_efficiency": charging_efficiency,
                "insurance_pm": insurance_pm, "parking_pm": parking_pm,
                "thg_quote_per_car_py": thg_quote_per_car_py, "salvage_value_per_car_eol": salvage_value_per_car_eol,
                "cybercab_base_usd": cybercab_base_usd, "usd_eur_rate": usd_eur_rate,
                "customs_duty_rate": customs_duty_rate, "vehicle_ltv": vehicle_ltv,
                "y1_loan_rate": y1_loan_rate, "y2_loan_rate": y2_loan_rate,
            },
        }

        rng = np.random.default_rng(seed=42)
        ni_cum_arr = np.zeros(n_iterations)
        y5_ebitda_arr = np.zeros(n_iterations)
        fcf_cum_arr = np.zeros(n_iterations)
        min_cash_arr = np.zeros(n_iterations)
        insolvency_flags = np.zeros(n_iterations, dtype=bool)

        param_samples = {
            "active_hours_per_day": np.zeros(n_iterations),
            "avg_speed_kmh": np.zeros(n_iterations),
            "dwell_time_mins": np.zeros(n_iterations),
            "target_util": np.zeros(n_iterations),
            "init_util": np.zeros(n_iterations),
            "rec_rate": np.zeros(n_iterations),
            "can_fac": np.zeros(n_iterations),
            "deadhead_rate": np.zeros(n_iterations),
            "avg_trip_distance_km": np.zeros(n_iterations),
            "price_per_km_eur": np.zeros(n_iterations),
            "tesla_take_rate": np.zeros(n_iterations),
            "delivery_ramp_y2": np.zeros(n_iterations),
            "delivery_ramp_y3": np.zeros(n_iterations),
            "delivery_ramp_y4": np.zeros(n_iterations),
            "cybercab_base_usd": np.zeros(n_iterations),
            "usd_eur_rate": np.zeros(n_iterations),
            "vehicle_ltv": np.zeros(n_iterations),
            "y1_loan_rate": np.zeros(n_iterations),
            "y2_loan_rate": np.zeros(n_iterations),
            "insurance_pm": np.zeros(n_iterations),
            "energy_eur_per_kwh": np.zeros(n_iterations),
            "energy_kwh_per_km": np.zeros(n_iterations),
            "cleaning_cost_per_day": np.zeros(n_iterations),
            "wear_and_tear_rate": np.zeros(n_iterations),
            "parking_pm": np.zeros(n_iterations),
            "customs_duty_rate": np.zeros(n_iterations),
            "salvage_value_per_car_eol": np.zeros(n_iterations),
            "macro_shock_avg": np.zeros(n_iterations),
            # === NEW: the WORST single-year macro shock — the path-dependency
            # metric that a horizon-average would hide. This is what should rank high
            # in the tornado for a thin-buffer startup. ===
            "macro_shock_worst": np.zeros(n_iterations),
            "arch_weekday_intensity": np.zeros(n_iterations),
            "arch_weekend_intensity": np.zeros(n_iterations),
            "arch_friday_intensity": np.zeros(n_iterations),
            "arch_holiday_intensity": np.zeros(n_iterations),
            "arch_oktober_intensity": np.zeros(n_iterations),
            "arch_xmas_intensity": np.zeros(n_iterations),
            "shock_weather_5y": np.zeros(n_iterations),
            "shock_strike_5y": np.zeros(n_iterations),
            "shock_event_5y": np.zeros(n_iterations),
            "shock_tech_5y": np.zeros(n_iterations),
            "shock_heat_5y": np.zeros(n_iterations),
            "shock_ice_5y": np.zeros(n_iterations),
            "shock_road_5y": np.zeros(n_iterations),
            "shock_collapse_5y": np.zeros(n_iterations),
        }

        progress_bar = st.progress(0.0, text=loc["mc_running_msg"])
        t_start = time.time()

        for i in range(int(n_iterations)):
            # === Draw 5 INDEPENDENT annual macro shocks ===
            annual_macro = rng.normal(0.0, macro_sigma, size=5)
            macro_avg = float(np.mean(annual_macro))      # retained only for scalar rate/FX inputs (cohort-locked)
            macro_worst = float(np.max(annual_macro))     #: worst single year (path-dependency provenance)
            # === macro_avg (mean) and macro_worst (max) are two summary
            # statistics of the SAME 5-draw vector and are therefore mechanically
            # collinear. They are used downstream ONLY as independent univariate
            # tornado bars — never together in a joint attribution. See the
            # GUARD comment at the tornado correlation loop before changing this. ===

            # === Roll each of the 5 years INDEPENDENTLY ===
            per_year_mods = []
            per_year_energy_mult = []
            per_year_wear_mult = []
            arch_intensity_accum = np.zeros(6)
            shock_counts_5y = {k: 0 for k in ["weather", "strike", "event", "tech", "heat", "ice", "road", "collapse"]}
            for yr in range(5):
                mods_y, e_mult_y, w_mult_y, arch_int_y, sc_y = _sample_one_year(rng, annual_macro[yr])
                per_year_mods.append(mods_y)
                per_year_energy_mult.append(e_mult_y)
                per_year_wear_mult.append(w_mult_y)
                arch_intensity_accum += arch_int_y
                for k in shock_counts_5y:
                    shock_counts_5y[k] += sc_y.get(k, 0)
            arch_intensity_avg = arch_intensity_accum / 5.0

            # === PATH-DEPENDENCY FIX ====================
            # Build a SINGLE 12-month seasonality vector that the engine takes for
            # the whole horizon, BUT carry the per-year demand/energy texture into
            # the engine via the new per-year multiplier arrays so each year's
            # crisis hits IN-PLACE (months 12y..12y+11), not averaged away.
            #
            # seasonality_iter: base seasonality × the YEAR-1 demand texture (the
            # intra-year monthly shape; the cross-year level is carried by the
            # per-year demand multipliers below so it isn't double-counted).
            # macro_demand_mult_by_year[y]: that year's demand level relative to a
            # neutral year — built as the ratio of year-y's average monthly mod to
            # the cross-year average, so the ENGINE applies year-specific demand.
            # macro_energy_mult_by_year[y]: that year's energy cost multiplier.
            #
            # Per-year average demand level (mean of that year's 12 monthly mods)
            per_year_demand_level = np.array([
                float(np.mean([per_year_mods[yr][mth] for mth in range(1, 13)]))
                for yr in range(5)
            ])
            cross_year_avg_level = float(np.mean(per_year_demand_level)) if np.mean(per_year_demand_level) > 0 else 1.0

            # The intra-year SHAPE (seasonality vector) uses the horizon-average
            # monthly texture so month-to-month seasonality is represented; the
            # cross-year LEVEL differences are carried by the demand multipliers.
            blended_monthly_shape = {}
            for mth in range(1, 13):
                _mth_avg = float(np.mean([per_year_mods[yr][mth] for yr in range(5)]))
                # normalize the shape so its own mean is ~cross_year_avg_level,
                # keeping the seasonality vector at the same overall scale as before
                blended_monthly_shape[mth] = _mth_avg
            seasonality_iter = {mth: seasonality_by_month[mth] * blended_monthly_shape[mth] for mth in range(1, 13)}

            # Per-year demand multiplier the ENGINE applies (year level ÷ cross-year
            # level). A crisis year sits below 1.0 and suppresses that year's months
            # IN-PLACE; a boom year sits above 1.0. Product of (shape level × this
            # ratio) reconstructs the true per-year demand, restoring path dependency.
            macro_demand_mult_by_year = [
                float(per_year_demand_level[yr] / cross_year_avg_level) if cross_year_avg_level > 0 else 1.0
                for yr in range(5)
            ]
            # === FIX: the per-year ENERGY multiplier is now built AFTER ==
            # Tier-2 sampling (see below), because the additive macro tug
            # (beta_energy × shock, in €/kWh) must be converted to a multiplier
            # using the SAMPLED energy price of this iteration — not the sidebar
            # base price. Using the base price made the effective additive shock
            # drift whenever the lognormal price draw deviated from base (a low
            # price draw silently amplified the crisis, a high draw damped it).
            # Only deterministic arithmetic moved — the RNG call sequence is
            # unchanged, so all draws remain stream-identical.
            # Per-year wear multiplier — applied to the scalar wear input via the
            # horizon average (wear is not a per-year engine channel; its cost
            # coupling is modest and symmetric enough that the average is acceptable).
            wear_cost_mult_iter = float(np.mean(per_year_wear_mult))

            # ===== TIER 1 sampling (structural physics — drawn once, locked) =====
            active_hours_sampled = max(8.0, min(22.0, rng.normal(active_hours_per_day, mc_sigma_active_hours)))
            speed_sampled = max(10.0, min(30.0, rng.normal(avg_speed_kmh, mc_sigma_speed)))
            dwell_sampled = max(0.5, min(8.0, rng.normal(dwell_time_mins, mc_sigma_dwell)))
            # === FIX: the Monte Carlo target-utilization distribution now
            # centers on the SIDEBAR target-utilization value, so the deterministic and
            # stochastic views stay aligned when the sidebar value changes. The
            # beta-scaled sampler clamps the mean into the (Min, Max) band, so an
            # off-band sidebar value degrades gracefully to the edge.
            target_util_sampled = _sample_beta_scaled(rng, target_util, mc_target_util_min, mc_target_util_max)
            init_util_sampled = max(0.10, min(0.95, rng.normal(init_util, mc_sigma_init_util)))
            if init_util_sampled > target_util_sampled:
                init_util_sampled = target_util_sampled
            rec_rate_sampled = max(0.001, min(0.20, rng.normal(rec_rate, mc_sigma_rec_rate)))
            can_fac_sampled = max(0.05, min(0.95, rng.normal(can_fac, mc_sigma_can_fac)))
            deadhead_sampled = max(0.05, min(0.50, rng.normal(deadhead_rate, mc_sigma_dh)))
            trip_dist_sampled = max(1.0, rng.normal(avg_trip_distance_km, mc_sigma_trip))
            price_sampled = max(0.10, rng.normal(price_per_km_eur, mc_sigma_price))
            take_sampled = _sample_triangular(rng, mc_take_min, mc_take_mode, mc_take_max)
            dy2_sampled = _sample_triangular(rng, mc_dy2_min, mc_dy2_mode, mc_dy2_max)
            dy3_sampled = _sample_triangular(rng, mc_dy3_min, mc_dy3_mode, mc_dy3_max)
            dy4_sampled = _sample_triangular(rng, mc_dy4_min, mc_dy4_mode, mc_dy4_max)

            # ===== TIER 2 sampling =====
            capex_sampled = max(5000.0, rng.normal(cybercab_base_usd, mc_sigma_capex))
            # FX gets macro tug (EUR weakens in crisis → more EUR per USD car).
            # Rates lock at cohort origination, so the horizon-average tug is an
            # acceptable proxy for the scalar rate inputs (most German auto/KfW
            # finance is Festzins; the floating exposure is the overdraft, handled
            # inside the engine at a fixed 9.5%).
            fx_sampled = max(0.50, min(2.50, rng.normal(usd_eur_rate, mc_sigma_fx) - beta_fx * macro_avg))
            ltv_sampled = max(0.20, min(0.95, rng.normal(vehicle_ltv, mc_sigma_ltv)))
            loan_y1_sampled = _sample_triangular(rng, mc_loan_y1_min, mc_loan_y1_mode, mc_loan_y1_max)
            loan_y2_sampled = _sample_triangular(rng, mc_loan_y2_min, mc_loan_y2_mode, mc_loan_y2_max)
            # Y1 loans originate in Year 1 → tug by Year-1 macro; Y2+ loans originate
            # across Years 2-5 → tug by the Years 2-5 average. This is sharper than
            # a single horizon-average and respects cohort rate-locking.
            _macro_y1 = float(annual_macro[0])
            _macro_y2plus = float(np.mean(annual_macro[1:]))
            loan_y1_sampled = max(0.005, loan_y1_sampled + beta_rate * _macro_y1)
            loan_y2_sampled = max(0.005, loan_y2_sampled + beta_rate * _macro_y2plus)
            insurance_sampled = _sample_triangular(rng, mc_ins_min, mc_ins_mode, mc_ins_max)
            mu_log = np.log(max(0.01, energy_eur_per_kwh))
            sigma_log = mc_sigma_energy_eur / max(0.01, energy_eur_per_kwh)
            energy_eur_sampled = float(rng.lognormal(mean=mu_log, sigma=sigma_log))
            # NOTE: the macro energy tug is now applied PER YEAR inside the engine
            # via macro_energy_mult_by_year — NOT baked into this scalar. The scalar
            # energy_eur_sampled carries only the cross-iteration price-level draw.
            kwh_per_km_sampled = max(0.05, rng.normal(energy_kwh_per_km, mc_sigma_kwh))

            # === per-year ENERGY multiplier — built with the SAMPLED price ==
            # Shock-cost coupling (per_year_energy_mult, from this iteration's per-year
            # shock library) × the macro tug converted additive→multiplicative using
            # energy_eur_sampled, this iteration's actual price level. A crisis year
            # raises that year's €/km IN-PLACE inside the engine ( architecture).
            macro_energy_mult_by_year = [
                float(per_year_energy_mult[yr]) * float(1.0 + (beta_energy * annual_macro[yr]) / max(0.01, energy_eur_sampled))
                for yr in range(5)
            ]
            # === per-year FLOATING-RATE (Kontokorrent) add-on ========
            # The overdraft rate follows each year's macro shock with the same
            # beta_rate transmission used for cohort loan rates — but applied
            # PER YEAR, because the floating line reprices continuously rather than
            # locking at origination. This closes the last macro transmission gap:
            # the line you draw in a crisis now also costs more in that crisis.
            overdraft_rate_addon_by_year_iter = [
                float(beta_rate * annual_macro[yr]) for yr in range(5)
            ]

            # ===== TIER 3 sampling — skewed one-sided costs =====
            cleaning_sampled = _sample_cost_skewed(rng, cleaning_cost_per_day, mc_sigma_cleaning / max(0.01, cleaning_cost_per_day))
            wear_sampled = _sample_cost_skewed(rng, wear_and_tear_rate, mc_sigma_wear / max(0.001, wear_and_tear_rate))
            parking_sampled = _sample_cost_skewed(rng, parking_pm, mc_sigma_parking / max(1.0, parking_pm))
            customs_sampled = max(0.0, min(0.40, rng.normal(customs_duty_rate, mc_sigma_customs)))
            salvage_sampled = max(0.0, rng.normal(salvage_value_per_car_eol, mc_sigma_salvage))

            # Wear horizon-average cost coupling (modest; symmetric enough to average)
            wear_sampled = wear_sampled * wear_cost_mult_iter

            # Base energy rate (price-level draw only). The per-year energy crisis
            # multiplier is applied INSIDE the engine via macro_energy_mult_by_year.
            energy_rate_sampled = (kwh_per_km_sampled * energy_eur_sampled) / charging_efficiency

            # ---- record samples for tornado ----
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
            param_samples["salvage_value_per_car_eol"][i] = salvage_sampled
            param_samples["macro_shock_avg"][i] = macro_avg
            param_samples["macro_shock_worst"][i] = macro_worst
            param_samples["arch_weekday_intensity"][i] = arch_intensity_avg[0]
            param_samples["arch_weekend_intensity"][i] = arch_intensity_avg[1]
            param_samples["arch_friday_intensity"][i] = arch_intensity_avg[2]
            param_samples["arch_holiday_intensity"][i] = arch_intensity_avg[3]
            param_samples["arch_oktober_intensity"][i] = arch_intensity_avg[4]
            param_samples["arch_xmas_intensity"][i] = arch_intensity_avg[5]
            param_samples["shock_weather_5y"][i] = shock_counts_5y["weather"]
            param_samples["shock_strike_5y"][i] = shock_counts_5y["strike"]
            param_samples["shock_event_5y"][i] = shock_counts_5y["event"]
            param_samples["shock_tech_5y"][i] = shock_counts_5y["tech"]
            param_samples["shock_heat_5y"][i] = shock_counts_5y["heat"]
            param_samples["shock_ice_5y"][i] = shock_counts_5y["ice"]
            param_samples["shock_road_5y"][i] = shock_counts_5y["road"]
            param_samples["shock_collapse_5y"][i] = shock_counts_5y["collapse"]

            try:
                pnl_mc, cf_mc, bs_mc, _mn, _cb, _nlb, insolvency_mc, _fl, _ut, _tcc, _bsk, _is, _lim, _ops = _execute_financial_simulation_uncached(
                    y1_adds_str, y2_adds_str, y3_adds_str, y4_adds_str, y5_adds_str,
                    active_hours_sampled, speed_sampled, deadhead_sampled, util_mode,
                    target_util_sampled, init_util_sampled, rec_rate_sampled, can_fac_sampled, flat_util, trip_dist_sampled,
                    dwell_sampled, base_fare_eur, price_sampled, take_sampled,
                    cleaning_sampled, cleaning_fee_passthrough_per_day, wear_sampled, energy_rate_sampled, insurance_sampled,
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
                    fin_mix_by_year, lease_money_factor, lease_downpayment_pct,
                    lease_term_months, equity_capital_call_enabled,
                    hebesatz_pct,
                    # === pass the per-year arrays (NOT averaged) ===
                    macro_demand_mult_by_year,
                    macro_energy_mult_by_year,
                    # === a configured launch delay applies to every MC run ===
                    launch_delay_months,
                    # === per-year floating-rate macro transmission ===
                    overdraft_rate_addon_by_year_iter
                )
                ni_cum_arr[i] = float(sum(pnl_mc["pnl_ni"]))
                y5_ebitda_arr[i] = float(sum(pnl_mc["pnl_ebitda"][48:60]))
                cf_op_arr = np.array(cf_mc["cf_op"])
                cf_inv_arr = np.array(cf_mc["cf_inv"])
                fcf_cum_arr[i] = float(np.sum(cf_op_arr + cf_inv_arr))
                min_cash_arr[i] = float(min(bs_mc["bs_cash"]))
                insolvency_flags[i] = (len(insolvency_mc) > 0)
            except Exception:
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

        st.divider()
        metric_view = st.selectbox(
            loc["mc_metric_selector"],
            [loc["mc_metric_fcf"], loc["mc_metric_ebitda"], loc["mc_metric_ni"]],
            index=2
        )
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
        else:
            target_arr_full = ni_arr
            target_valid = ni_valid
            chart_title = loc["mc_chart_ni_title"]
            xaxis_label = "5-Year Cumulative Net Income (€)"

        st.subheader(loc["mc_section_outputs"])

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
            title=chart_title, xaxis_title=xaxis_label, yaxis_title="Frequency",
            template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1a1a",
            font=dict(color="#FAFAFA", family="Inter, sans-serif"),
            showlegend=False, height=420
        )
        st.plotly_chart(fig_target, use_container_width=True)

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
            xaxis_title="Minimum Cash Balance Over 60 Months (€)", yaxis_title="Frequency",
            template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1a1a",
            font=dict(color="#FAFAFA", family="Inter, sans-serif"),
            showlegend=False, height=420
        )
        st.plotly_chart(fig_cash, use_container_width=True)

        valid_mask = ~np.isnan(target_arr_full)
        corrs = {}
        param_label_map = {
            "active_hours_per_day": "Active Hours per Day [T1]",
            "avg_speed_kmh": "Average Speed (km/h) [T1]",
            "dwell_time_mins": "Dwell Time (min) [T1]",
            "target_util": "Target Utilization [T1]",
            "init_util": "Init Utilization [T1]",
            "rec_rate": "Recovery Rate [T1]",
            "can_fac": "Cannibalization Factor [T1]",
            "deadhead_rate": "Deadhead Rate [T1]",
            "avg_trip_distance_km": "Avg Trip Distance (km) [T1]",
            "price_per_km_eur": "Price per km (€) [T1]",
            "tesla_take_rate": "Tesla Take-Rate [T1]",
            "delivery_ramp_y2": "Delivery Ramp Y2 [T1]",
            "delivery_ramp_y3": "Delivery Ramp Y3 [T1]",
            "delivery_ramp_y4": "Delivery Ramp Y4 [T1]",
            "cybercab_base_usd": "Cybercab Base Capex USD [T2]",
            "usd_eur_rate": "USD/EUR FX Rate [T2]",
            "vehicle_ltv": "Vehicle LTV [T2]",
            "y1_loan_rate": "Y1 Loan Rate [T2]",
            "y2_loan_rate": "Y2 Loan Rate [T2]",
            "insurance_pm": "Insurance (€/mo) [T2]",
            "energy_eur_per_kwh": "Energy Price (€/kWh) [T2]",
            "energy_kwh_per_km": "Cybercab Consumption (kWh/km) [T2]",
            "cleaning_cost_per_day": "Cleaning Cost (€/day) [T3]",
            "wear_and_tear_rate": "Wear & Tear (€/km) [T3]",
            "parking_pm": "Parking (€/mo) [T3]",
            "customs_duty_rate": "Customs Duty Rate [T3]",
            "salvage_value_per_car_eol": "Salvage Value (€) [T3]",
            "macro_shock_avg": "🌍 MACRO ENVIRONMENT — horizon avg [MACRO]",
            "macro_shock_worst": "🌍 MACRO — WORST single year [MACRO]",
            "arch_weekday_intensity": "Weekday Demand Intensity [DA]",
            "arch_weekend_intensity": "Weekend Demand Intensity [DA]",
            "arch_friday_intensity": "Fri/Sat Evening Intensity [DA]",
            "arch_holiday_intensity": "Holiday Demand Intensity [DA]",
            "arch_oktober_intensity": "Oktoberfest Demand Intensity [DA]",
            "arch_xmas_intensity": "Christmas Markets Intensity [DA]",
            "shock_weather_5y": "Severe Weather Days (5Y) [SH]",
            "shock_strike_5y": "Transit Strike Days (5Y) [SH]",
            "shock_event_5y": "Major Event Days (5Y) [SH]",
            "shock_tech_5y": "Tech Outage Days (5Y) [SH]",
            "shock_heat_5y": "Heat Wave Days (5Y) [SH]",
            "shock_ice_5y": "Black Ice Days (5Y) [SH]",
            "shock_road_5y": "Road Closure Days (5Y) [SH]",
            "shock_collapse_5y": "Demand-Collapse Days (5Y) [SH]",
        }
        # === GUARD: macro_shock_avg vs macro_shock_worst collinearity ===
        # `macro_shock_avg` (mean of the 5 annual draws) and `macro_shock_worst`
        # (max of the SAME 5 draws) are mechanically correlated by construction —
        # they are two summary statistics of one underlying vector, so their
        # cross-correlation is high and largely artefactual. That is harmless
        # HERE because every entry below is an INDEPENDENT, UNIVARIATE Pearson r
        # between one input and the target: each tornado bar stands alone, and the
        # collinearity between the two macro bars never enters a single estimator.
        # DO NOT change that. Specifically, never feed both `macro_shock_avg` and
        # `macro_shock_worst` into ANY *joint* attribution (multiple regression,
        # Shapley/variance decomposition, partial-correlation, or a covariance
        # matrix) — the collinearity would split/flip their coefficients and make
        # the attribution uninterpretable. If a joint model is ever added, keep
        # exactly ONE of the two (the worst-single-year bar is the path-dependency
        # signal the credit committee wants) and drop the other from that model.
        for param_key, samples_arr in param_samples_stored.items():
            samples_valid_sub = samples_arr[valid_mask]
            target_valid_for_corr = target_arr_full[valid_mask]
            if len(samples_valid_sub) > 2 and np.std(samples_valid_sub) > 1e-12 and np.std(target_valid_for_corr) > 1e-12:
                r = float(np.corrcoef(samples_valid_sub, target_valid_for_corr)[0, 1])
                if np.isnan(r):
                    r = 0.0
            else:
                r = 0.0
            corrs[param_label_map.get(param_key, param_key)] = r
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
            xaxis_title=loc["mc_tornado_xaxis"], yaxis_title="",
            template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#1a1a1a",
            font=dict(color="#FAFAFA", family="Inter, sans-serif"),
            showlegend=False, height=1180, xaxis=dict(range=[-1.0, 1.0])
        )
        st.plotly_chart(fig_tornado, use_container_width=True)

        st.caption(
            "**Interpretation guide:** Pearson r magnitude shows how strongly each "
            "stochastic input drives variance in the selected target metric "
            f"({metric_view}). Positive r (green) = higher input → higher target; "
            "negative r (red) = higher input → lower target. Magnitudes < 0.1 are "
            "essentially noise; > 0.3 indicates a dominant variance driver. "
            "**Two macro bars appear** — 🌍 MACRO horizon-avg AND "
            "🌍 MACRO WORST-single-year. Because crises now hit IN-PLACE (not averaged), "
            "the WORST-single-year bar is the path-dependency signal: it should rank "
            "among the strongest drivers of the minimum-cash / insolvency tail, which "
            "is exactly the risk a credit committee scrutinises first. **Tier legend:** "
            "[MACRO]=shared crisis factor, [T1]=Operating Physics, [T2]=Capex/Debt, "
            "[T3]=Operating Costs, [DA]=Day Archetype (Phase A), [SH]=Shock Events "
            "(Phase B, sampled per-year)."
        )

        #
        # === DYNAMIC NARRATIVE PANEL ====================
        #
        st.divider()
        st.markdown(f"### {loc['mc_narr_header']}")
        st.caption(loc["mc_narr_caption"])

        ni_p5 = _pct(ni_valid, 5); ni_p50 = _pct(ni_valid, 50); ni_p95 = _pct(ni_valid, 95)
        cash_p5 = _pct(cash_valid, 5); cash_p50 = _pct(cash_valid, 50)
        fcf_p5 = _pct(fcf_valid, 5); fcf_p50 = _pct(fcf_valid, 50)
        n_runs = mcr["n"]
        ni_loss_share = float(np.mean(ni_valid < 0)) * 100 if len(ni_valid) > 0 else 0.0
        below_buffer_share = float(np.mean(cash_valid < buffer_threshold)) * 100 if len(cash_valid) > 0 else 0.0
        below_zero_share = float(np.mean(cash_valid < 0)) * 100 if len(cash_valid) > 0 else 0.0

        _ranked = sorted(corrs.items(), key=lambda kv: abs(kv[1]), reverse=True)
        _top3 = _ranked[:3]
        _macro_label = next((lbl for lbl in corrs if "WORST single year" in lbl), None)
        if _macro_label is None:
            _macro_label = next((lbl for lbl in corrs if "MACRO ENVIRONMENT" in lbl), None)
        _macro_r = corrs.get(_macro_label, 0.0) if _macro_label else 0.0
        _macro_rank = next((idx + 1 for idx, (lbl, _) in enumerate(_ranked) if lbl == _macro_label), None)
        _shock_rs = [abs(v) for lbl, v in corrs.items() if "[SH]" in lbl or "[DA]" in lbl]
        _max_shock_r = max(_shock_rs) if _shock_rs else 0.0

        def _eur(x):
            return f"€{x:,.0f}"
        def _clean_label(lbl):
            for tag in [" [T1]", " [T2]", " [T3]", " [MACRO]", " [DA]", " [SH]"]:
                lbl = lbl.replace(tag, "")
            return lbl.replace("🌍 ", "").strip()

        if lang_choice == "English":
            profit_txt = (
                f"{loc['mc_narr_profit_h']} Across {n_runs:,} simulated versions of your 5-year journey, "
                f"the typical (median) outcome is **{_eur(ni_p50)}** of cumulative net income. "
                f"In the unluckiest 5% of runs you still end at **{_eur(ni_p5)}**, and in the luckiest 5% you reach **{_eur(ni_p95)}**. "
            )
            if ni_loss_share < 1.0:
                profit_txt += f"Essentially every run stays profitable on a 5-year cumulative basis (only {ni_loss_share:.1f}% end below zero) — a wide range of bad luck still leaves the business in the black."
            elif ni_loss_share < 10.0:
                profit_txt += f"About {ni_loss_share:.1f}% of runs end with a cumulative loss — a real but minority tail worth understanding before you commit capital."
            else:
                profit_txt += f"⚠️ A material {ni_loss_share:.1f}% of runs end with a cumulative loss. The downside is not a rare fluke under your current settings — revisit the assumptions driving it before relying on the median."

            survival_txt = (
                f"{loc['mc_narr_survival_h']} Profit is meaningless if you run out of cash first, so this looks at the *lowest* point your bank balance hits over 60 months. "
                f"Your typical worst-moment balance is **{_eur(cash_p50)}**, and even the unluckiest 5% of runs bottom out around **{_eur(cash_p5)}** "
                f"(your safety cushion is set to {_eur(buffer_threshold)}). "
            )
            if below_zero_share >= 0.5:
                survival_txt += f"⚠️ **{below_zero_share:.1f}% of runs actually hit zero cash** — that is a genuine bankruptcy-risk signal. Because a single bad year can strike in real time, this number reflects true path-dependent risk, not a smoothed average. Your overdraft line and/or opening capital may be too thin for the volatility in these settings."
            elif below_buffer_share >= 5.0:
                survival_txt += f"In {below_buffer_share:.1f}% of runs the worst-month balance dips below your {_eur(buffer_threshold)} cushion — you never hit zero, but you lean on the safety margin often enough that shrinking the overdraft line would be unwise."
            elif below_buffer_share >= 0.5:
                survival_txt += f"Only about {below_buffer_share:.1f}% of runs ever touch your {_eur(buffer_threshold)} cushion, and none hit zero — liquidity looks robust under these settings, with the overdraft line providing the backstop for the worst tails."
            else:
                survival_txt += "Virtually no run comes close to your cushion or to zero — liquidity is very robust under these settings. (If this looks *too* comfortable, your variance inputs may be set conservatively.)"

            top_str = "; ".join(
                f"**{_clean_label(lbl)}** ({'+' if r >= 0 else ''}{r:.2f})"
                for lbl, r in _top3
            )
            drivers_txt = (
                f"{loc['mc_narr_drivers_h']} For your selected metric (**{metric_view}**), the strongest levers are: {top_str}. "
                "Green-direction levers lift the metric when they rise; red-direction levers drag it down. "
                "Bars near zero are statistical noise — they do not meaningfully change the outcome. "
            )
            if _macro_rank is not None:
                if abs(_macro_r) >= 0.15:
                    drivers_txt += (
                        f"The 🌍 **worst-single-year macro factor ranks #{_macro_rank}** (r = {_macro_r:+.2f}) — meaning a *correlated* downturn "
                        "(energy spike + rate hike + demand drop hitting together in one year) is one of your more serious threats, larger than any single cost line. "
                        "That is the path-dependent risk a credit committee scrutinises first, because crises are applied in the year they strike rather than averaged away."
                    )
                else:
                    drivers_txt += (
                        f"The 🌍 worst-single-year macro factor is currently a minor driver (r = {_macro_r:+.2f}, rank #{_macro_rank}) — "
                        "your coupling sensitivities (betas) are set low, so even a concentrated bad year barely moves the result. Raise the betas in the Macro Coupling panel to stress-test a harsher correlated crisis."
                    )
            if _max_shock_r < 0.05:
                drivers_txt += (
                    " Notably, **every weather, strike, and event shock sits at essentially zero** — day-to-day operational chaos does *not* decide your success. "
                    "Your destiny is set by structural, management-controllable levers (throughput per car-hour and pricing), not by luck. That is a fundable story."
                )

            _top_pos = next(((lbl, r) for lbl, r in _ranked if r > 0), None)
            _top_neg = next(((lbl, r) for lbl, r in _ranked if r < 0), None)
            impl_bits = []
            if _top_pos:
                impl_bits.append(
                    f"Your single highest-value investment is anything that improves **{_clean_label(_top_pos[0])}** — "
                    "it has the largest positive pull on the outcome, so management attention and capital spent here compound faster than anywhere else."
                )
            if _top_neg:
                impl_bits.append(
                    f"On the defensive side, **{_clean_label(_top_neg[0])}** is your most damaging risk; hedging or contractually capping it (e.g. a fixed-price supply agreement, an interest-rate hedge, or an operational buffer) buys the most downside protection per euro."
                )
            if below_zero_share >= 0.5 or below_buffer_share >= 5.0:
                impl_bits.append(
                    f"Given the liquidity tail above, treat the {_eur(max_overdraft_limit)} overdraft line as load-bearing — do not reduce it, and consider a modest increase in opening capital to push the worst-case cash balance further from zero."
                )
            else:
                impl_bits.append(
                    f"Liquidity looks solid, so the {_eur(max_overdraft_limit)} overdraft line is adequate as a backstop rather than a crutch — capital is better deployed accelerating the fleet than padding the buffer."
                )
            implication_txt = f"{loc['mc_narr_implication_h']} " + " ".join(impl_bits)

        else:  # Deutsch
            profit_txt = (
                f"{loc['mc_narr_profit_h']} Über {n_runs:,} simulierte Versionen Ihrer 5-Jahres-Reise liegt das typische (mittlere) Ergebnis bei "
                f"**{_eur(ni_p50)}** kumuliertem Jahresüberschuss. Im ungünstigsten 5%-Fall enden Sie noch bei **{_eur(ni_p5)}**, im günstigsten 5%-Fall bei **{_eur(ni_p95)}**. "
            )
            if ni_loss_share < 1.0:
                profit_txt += f"Praktisch jeder Lauf bleibt auf 5-Jahres-Basis profitabel (nur {ni_loss_share:.1f}% enden negativ) — selbst breites Pech lässt das Geschäft in den schwarzen Zahlen."
            elif ni_loss_share < 10.0:
                profit_txt += f"Etwa {ni_loss_share:.1f}% der Läufe enden mit kumuliertem Verlust — ein realer, aber kleiner Tail, den man vor Kapitalbindung verstehen sollte."
            else:
                profit_txt += f"⚠️ Erhebliche {ni_loss_share:.1f}% der Läufe enden mit kumuliertem Verlust. Das Downside ist bei diesen Einstellungen kein Ausreißer — prüfen Sie die treibenden Annahmen."

            survival_txt = (
                f"{loc['mc_narr_survival_h']} Gewinn ist wertlos, wenn vorher die Liquidität ausgeht — daher hier der *tiefste* Kassenstand über 60 Monate. "
                f"Ihr typischer Tiefststand liegt bei **{_eur(cash_p50)}**, und selbst die ungünstigsten 5% fallen nur auf ca. **{_eur(cash_p5)}** "
                f"(Ihr Sicherheitspuffer beträgt {_eur(buffer_threshold)}). "
            )
            if below_zero_share >= 0.5:
                survival_txt += f"⚠️ **{below_zero_share:.1f}% der Läufe erreichen tatsächlich null Kasse** — ein echtes Insolvenzrisiko-Signal. Da ein einzelnes schlechtes Jahr in Echtzeit zuschlägt, spiegelt diese Zahl echtes pfadabhängiges Risiko wider, keinen geglätteten Durchschnitt. Kontokorrentlinie und/oder Anfangskapital könnten zu dünn sein."
            elif below_buffer_share >= 5.0:
                survival_txt += f"In {below_buffer_share:.1f}% der Läufe unterschreitet der Tiefststand den Puffer von {_eur(buffer_threshold)} — null wird nie erreicht, aber der Sicherheitsabstand wird oft genug beansprucht, dass eine Verkleinerung der Linie unklug wäre."
            elif below_buffer_share >= 0.5:
                survival_txt += f"Nur ca. {below_buffer_share:.1f}% der Läufe berühren den Puffer von {_eur(buffer_threshold)}, keiner erreicht null — die Liquidität wirkt robust, die Kontokorrentlinie sichert die schlimmsten Tails ab."
            else:
                survival_txt += "Praktisch kein Lauf nähert sich Puffer oder null — die Liquidität ist sehr robust. (Wirkt das *zu* komfortabel, sind Ihre Varianz-Eingaben evtl. konservativ gesetzt.)"

            top_str = "; ".join(
                f"**{_clean_label(lbl)}** ({'+' if r >= 0 else ''}{r:.2f})"
                for lbl, r in _top3
            )
            drivers_txt = (
                f"{loc['mc_narr_drivers_h']} Für die gewählte Kennzahl (**{metric_view}**) sind die stärksten Hebel: {top_str}. "
                "Grüne Hebel heben die Kennzahl beim Anstieg; rote ziehen sie nach unten. Balken nahe null sind Rauschen. "
            )
            if _macro_rank is not None:
                if abs(_macro_r) >= 0.15:
                    drivers_txt += (
                        f"Der 🌍 **Schlimmstes-Einzeljahr-Makrofaktor steht auf Rang #{_macro_rank}** (r = {_macro_r:+.2f}) — ein *korrelierter* Abschwung "
                        "(Energiepreis + Zinsen + Nachfrageeinbruch gleichzeitig in einem Jahr) ist eine Ihrer ernstesten Bedrohungen, größer als jede einzelne Kostenposition. Das prüft ein Kreditkomitee zuerst — und es ist sichtbar, weil Krisen in dem Jahr wirken, in dem sie auftreten, statt weggemittelt zu werden."
                    )
                else:
                    drivers_txt += (
                        f"Der 🌍 Schlimmstes-Einzeljahr-Makrofaktor ist derzeit nebensächlich (r = {_macro_r:+.2f}, Rang #{_macro_rank}) — Ihre Kopplungs-Betas sind niedrig gesetzt. Erhöhen Sie sie im Makro-Kopplungs-Panel für einen härteren Stresstest."
                    )
            if _max_shock_r < 0.05:
                drivers_txt += (
                    " Bemerkenswert: **alle Wetter-, Streik- und Event-Shocks liegen praktisch bei null** — operatives Tagesgeschäft-Chaos entscheidet *nicht* über Ihren Erfolg. "
                    "Ihr Schicksal bestimmen strukturelle, vom Management steuerbare Hebel (Durchsatz pro Fahrzeugstunde und Preis), nicht Glück. Das ist eine finanzierbare Story."
                )

            _top_pos = next(((lbl, r) for lbl, r in _ranked if r > 0), None)
            _top_neg = next(((lbl, r) for lbl, r in _ranked if r < 0), None)
            impl_bits = []
            if _top_pos:
                impl_bits.append(
                    f"Ihre wertvollste Investition ist alles, was **{_clean_label(_top_pos[0])}** verbessert — der größte positive Hebel auf das Ergebnis."
                )
            if _top_neg:
                impl_bits.append(
                    f"Defensiv ist **{_clean_label(_top_neg[0])}** Ihr schädlichstes Risiko; Absicherung oder vertragliche Deckelung (Fixpreisvertrag, Zins-Hedge, operativer Puffer) bringt den meisten Downside-Schutz pro Euro."
                )
            if below_zero_share >= 0.5 or below_buffer_share >= 5.0:
                impl_bits.append(
                    f"Angesichts des Liquiditäts-Tails ist die Kontokorrentlinie von {_eur(max_overdraft_limit)} tragend — nicht reduzieren, ggf. Anfangskapital leicht erhöhen."
                )
            else:
                impl_bits.append(
                    f"Die Liquidität wirkt solide, daher ist die Linie von {_eur(max_overdraft_limit)} ein Backstop statt eine Krücke — Kapital beschleunigt die Flotte besser als den Puffer."
                )
            implication_txt = f"{loc['mc_narr_implication_h']} " + " ".join(impl_bits)

        st.markdown(profit_txt)
        st.markdown(survival_txt)
        st.markdown(drivers_txt)
        st.markdown(implication_txt)

        # === FIX: surface the simulation provenance ==========
        # `simulation_settings` captures the full input provenance of the run
        # (iteration count, RNG seed, macro betas, and every baseline center the
        # MC sampled around). Rendering it in a collapsed expander makes every
        # Monte Carlo run reproducible and auditable without cluttering the view.
        # Guarded with.get so older cached results (pre-, lacking the key)
        # degrade gracefully instead of raising a KeyError.
        _provenance = mcr.get("simulation_settings")
        if _provenance is not None:
            with st.expander(loc["mc_provenance_header"], expanded=False):
                st.caption(loc["mc_provenance_caption"])
                st.json(_provenance)
    else:
        st.info(loc["mc_no_results"])

with tabs[8]:
    if lang_choice == "English":
        st.markdown("""
        ### 🚕 MRRG Cybercab Fleet: Master Financial Engine

        Welcome to the MRRG Master Financial Engine. This application is a fully integrated, institutional-grade financial model designed to simulate the operations, scaling, and accounting of an automated robotaxi (TaaS) fleet operating in Germany under HGB accounting rules.

        Built on **Streamlit** and written in **Python**, this dashboard uses a **60-month cohort engine** to simulate real-world physics and a fully balanced, HGB-compliant 3-Statement financial model.

        ---

        #### 🧠 TaaS & Finance 101: Core Concepts
        * **TaaS (Transportation-as-a-Service):** Providing rides via automated vehicles routed by an algorithmic platform.
        * **CapEx:** The upfront cost of buying vehicles — capitalized on the Balance Sheet, not expensed in month 1.
        * **AfA (Depreciation):** Monthly deduction of a portion of each vehicle's value from taxable profit.
        * **Deadhead:** Kilometers driven *without* a paying passenger.
        * **HGB:** The German Commercial Code; this model follows German accounting rules for tax provisioning and statement structure.
        * **Monte Carlo:** Running the model thousands of times with randomized inputs to map the *range* of outcomes — not a single forecast but a probability distribution of where the business could land.
        * **Path dependency:** The order and timing of good/bad years matters, not just their average. One bad year early can be fatal even if later years are excellent.

        ---

        #### 📊 Understanding the Outputs (The Tabs)
        * **Income Statement (P&L):** Paper profitability from customer bookings down to EBITDA and Net Income.
        * **Cash Flow Statement:** Actual cash in/out — CapEx burns, loan drawdowns, tax payment timing.
        * **Balance Sheet:** What the company owns vs. owes; the **BALANCE CHECK** line always reads 0 €.
        * **KPIs & Ratios:** DSCR (total + senior), FCCR, Equity Ratio, Liquidity Runway, Net LTV.
        * **Visualizations:** Scaling trajectory charts; toggle Free Cash Flow to cumulative to see the J-Curve.
        * **Risk & Variance (Monte Carlo):** The path-dependent simulation engine — percentile distributions, a dynamic metric selector (FCF/EBITDA/NI), and the macro-coupled sensitivity tornado with the worst-single-year bar.

        ---

        *Disclaimer: forward-looking projection on user-set assumptions; a decision-support tool, not an audited financial statement, and not investment, legal, or tax advice.*
        """)
    else:
        st.markdown("""
        ### 🚕 MRRG Cybercab-Flotte: Master-Finanzmodell

        Willkommen beim MRRG Master-Finanzmodell — ein vollständig integriertes, institutionelles Finanzmodell, das Betrieb, Skalierung und Buchhaltung einer automatisierten Robotaxi-Flotte (TaaS) in Deutschland nach HGB simuliert.

        Auf **Streamlit** und **Python** basierend, nutzt das Dashboard eine **60-monatige Kohorten-Logik** und ein vollständig bilanziertes, HGB-konformes 3-Statement-Modell.

        ---

        *Haftungsausschluss: zukunftsgerichtete Projektion auf Basis benutzergesetzter Annahmen; Entscheidungsunterstützung, kein geprüfter Jahresabschluss, keine Anlage-, Rechts- oder Steuerberatung.*
        """)
