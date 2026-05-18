import streamlit as st
import pandas as pd
import numpy as np
import calendar

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
        "subtitle": "*(HGB 3-Statement Model - Layer 11: Institutional KPIs & Ratios)*",
        "sec1": "1a. FLEET SCALING SCHEDULE",
        "y1_adds": "Year 1 Additions (Jan-Dec)",
        "y2_adds": "Year 2 Additions (Jan-Dec)",
        "y3_adds": "Year 3 Additions (Jan-Dec)",
        "y4_adds": "Year 4 Additions (Jan-Dec)",
        "y5_adds": "Year 5 Additions (Jan-Dec)",
        "sec1b": "1b. OPERATIONAL PHYSICS",
        "active_hours": "Active Hours / Day",
        "speed": "Average Speed (km/h)",
        "deadhead": "Deadhead Rate (%)",
        "help_deadhead": "Percentage of total kilometers driven without a paying passenger (e.g., driving to chargers, parking, or the next pickup).",
        "sec1c": "1c. UTILIZATION DYNAMICS",
        "util_mode": "Utilization Mode",
        "util_dyn": "Dynamic (Ramp & Cannibalization)",
        "util_fix": "Fixed Rate",
        "target_util": "Target Utilization (%)",
        "help_target": "The optimal, steady-state utilization your fleet achieves when supply and demand are perfectly balanced.",
        "init_util": "Month 1 Launch Util. (%)",
        "help_init": "The lower utilization expected in the very first month of business as algorithms map the city and demand is new.",
        "rec_rate": "Monthly Recovery (+%)",
        "help_rec": "How much the fleet utilization naturally climbs each month (+%) after a new vehicle drop, as demand catches up.",
        "can_fac": "Cannibalization Factor",
        "help_can": "Measures how much new cars steal rides from existing cars. e.g., A 0.5 factor means a 10% increase in total cars causes a 5% temporary drop in fleet-wide utilization.",
        "util_label": "Avg Util",
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
        "wear_help": "Covers tires, fluids, and suspension. Excludes 'black swan' contingency (held in liquidity reserve).",
        "energy_rate": "Base Energy Cost per km (€)",
        "energy_help": "Un-blended summer rate. Winter/Shoulder penalties (1.4x / 1.3x) are applied dynamically by month.",
        "sec5": "5. VEHICLE FIXED COSTS (€ / Month, Net)",
        "insurance": "Insurance",
        "parking": "APCOA Parking",
        "telemetry": "Telemetry & API",
        "tuev": "TÜV / BO-Kraft Accrual",
        "help_tuev": "Monthly accrual for mandatory commercial passenger transport (BO-Kraft) technical inspections.",
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
        "help_ltv": "Percentage of total vehicle landing costs (including freight and customs) financed via bank debt.",
        "y1_loan_rate": "KfW Gründerkredit Rate (Y1) %",
        "y2_loan_rate": "Standard Bank Rate (Y2+) %",
        "int_rate": "Cash Interest Rate (%)",
        "sec9": "9. OTHER INCOME / SALVAGE",
        "thg": "THG Quote per vehicle/yr",
        "help_thg": "Greenhouse Gas (GHG) Reduction Quota. Tradable certificates sold to oil companies for operating zero-emission vehicles.",
        "salvage": "Vehicle Sale Price (Y4)",
        
        "pnl_gbv": "Gross Booking Value (Customer Pays incl. 19% VAT)",
        "pnl_vat": "Less: 19% VAT (Finanzamt)",
        "pnl_net_rev": "Net Revenue (Umsatzerlöse excl. VAT)",
        "pnl_tesla_fee": "Less: Tesla Platform Fee (Take-Rate on GBV)",
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
        
        "cf_ni": "+ Net Income",
        "cf_depr": "+ Depreciation & Amortization",
        "cf_gain_sale": "- Gain on Sale of Assets",
        "cf_tax_prov": "+ Tax Provision Increase",
        "cf_tax_paid": "- Taxes Paid (Month 5)",
        "cf_vat_coll": "+ VAT Collected (Operations)",
        "cf_vat_paid": "- VAT Paid (Operations)",
        "cf_op": "Net Cash from Operations",
        "cf_capex": "- Net CapEx (Vehicles & HW, incl. VAT)",
        "cf_vat_ref": "+ VAT Refund from Finanzamt (CapEx)",
        "cf_sale": "+ Proceeds from Asset Sale",
        "cf_inv": "Net Cash from Investing",
        "cf_eq": "+ Founder Equity Injection",
        "cf_sh": "+ Shareholder Loan Injection",
        "cf_kfw_draw": "+ Debt Drawdown (Vehicles)",
        "cf_prin": "- Principal Repayment",
        "cf_vat_draw": "+ VAT Bridge Loan Drawdown",
        "cf_vat_repay": "- VAT Bridge Loan Repayment",
        "cf_fin": "Net Cash from Financing",
        "cf_net": "Net Change in Cash",
        "cf_beg": "+ Beginning Cash Balance",
        "cf_end": "Ending Cash Balance",
        
        "bs_gfa": "Gross Fixed Assets",
        "bs_acc_depr": "- Accumulated Depreciation",
        "bs_nfa": "Net Fixed Assets",
        "bs_vat_rec": "VAT Receivable (Finanzamt)",
        "bs_cash": "Ending Cash Balance",
        "bs_tca": "Total Current Assets",
        "bs_ta": "TOTAL ASSETS",
        "bs_eq_share": "Share Capital (Stammkapital)",
        "bs_eq_ret": "Retained Earnings / Net Income",
        "bs_teq": "Total Equity",
        "bs_prov_tax": "Steuerrückstellungen (Tax Provision)",
        "bs_tprov": "Total Provisions",
        "bs_debt_kfw": "Long-Term Debt (Vehicle Loans)",
        "bs_debt_vat": "Short-Term Debt (VAT Bridge)",
        "bs_pay_vat": "Umsatzsteuer-Zahllast (VAT Payable)",
        "bs_sh_loan": "Shareholder Loan",
        "bs_tliab": "Total Liabilities (Debt)",
        "bs_tleq": "TOTAL LIAB. & EQUITY",
        "bs_check": "BALANCE CHECK (Assets - Liab & Eq)",

        "tab_kpi": "KPIs & Ratios",
        "kpi_dscr": "Debt Service Coverage Ratio (DSCR)",
        "kpi_eq_ratio": "Equity Ratio",
        "kpi_runway": "Liquidity Runway (Months)",
        "kpi_net_ltv": "Net LTV (Adj. for Cash Shield)",
        "kpi_var_ratio": "Variable Expense Ratio",
        "kpi_fix_ratio": "Fixed Expense Ratio",
        "kpi_tot_ratio": "Total Expense Ratio",
        "kpi_db2_m": "Contribution Margin Ratio (DB2)",
        "kpi_ebitda_m": "EBITDA Margin",

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
        "monthly": "Monthly Drilldown",
        "exp_y1": "Expand Y1",
        "exp_y2": "Expand Y2",
        "exp_y3": "Expand Y3",
        "exp_y4": "Expand Y4",
        "exp_y5": "Expand Y5",
        "glossary_title": "Financial Metric Definitions & Methodology"
    }
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
else:
    loc = {
        "title": "MRRG Cybercab-Flotte: Master-Finanzmodell",
        "subtitle": "*(HGB 3-Statement Model - Layer 11: Institutionelle KPIs & Ratios)*",
        "sec1": "1a. FLOTTENSKALIERUNG",
        "y1_adds": "Jahr 1 Zugänge (Jan-Dez)",
        "y2_adds": "Jahr 2 Zugänge (Jan-Dez)",
        "y3_adds": "Jahr 3 Zugänge (Jan-Dez)",
        "y4_adds": "Jahr 4 Zugänge (Jan-Dez)",
        "y5_adds": "Jahr 5 Zugänge (Jan-Dez)",
        "sec1b": "1b. OPERATIVE PHYSIK",
        "active_hours": "Aktive Stunden / Tag",
        "speed": "Durchschnittsgeschwindigkeit (km/h)",
        "deadhead": "Leerfahrten-Quote (%)",
        "help_deadhead": "Prozentsatz der gefahrenen Kilometer ohne zahlenden Fahrgast (z.B. Fahrt zum Ladepark, Parkplatz oder zum nächsten Kunden).",
        "sec1c": "1c. AUSLASTUNGSDYNAMIK",
        "util_mode": "Auslastungsmodell",
        "util_dyn": "Dynamisch (Anlauf & Kannibalisierung)",
        "util_fix": "Fester Wert",
        "target_util": "Ziel-Auslastung (%)",
        "help_target": "Die optimale Dauer-Auslastung der Flotte, wenn Angebot und Nachfrage im Gleichgewicht sind.",
        "init_util": "Start-Auslastung Monat 1 (%)",
        "help_init": "Niedrigere Auslastung im ersten Geschäftsmonat, da die Algorithmen den Markt erst mappen müssen.",
        "rec_rate": "Monatliche Erholung (+%)",
        "help_rec": "Um wie viel Prozent die Auslastung monatlich wieder ansteigt, nachdem neue Fahrzeuge hinzugefügt wurden.",
        "can_fac": "Kannibalisierungsfaktor",
        "help_can": "Bestimmt den Auslastungseinbruch bei Neuzugängen. Ein Faktor von 0,5 bedeutet, dass ein 10%iges Flottenwachstum zu einem temporären Auslastungsrückgang von 5% führt.",
        "util_label": "Ø Auslastung",
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
        "wear_help": "Deckt Reifen, Flüssigkeiten und Fahrwerk ab. Exklusive 'Black Swan'-Rücklage (im Liquiditätspuffer gehalten).",
        "energy_rate": "Basis-Energiekosten pro km (€)",
        "energy_help": "Reiner Sommer-Basistarif. Winter-/Übergangszuschläge (1,4x / 1,3x) werden je nach Monat dynamisch aufgeschlagen.",
        "sec5": "5. FAHRZEUG-FIXKOSTEN (€ / Monat, Netto)",
        "insurance": "Kfz-Versicherung",
        "parking": "APCOA Stellplätze",
        "telemetry": "Telemetrie & API",
        "tuev": "TÜV / BO-Kraft Rückstellung",
        "help_tuev": "Monatliche Rückstellung für die gesetzlich vorgeschriebene BO-Kraft Untersuchung zur Fahrgastbeförderung.",
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
        "help_ltv": "Prozentualer Anteil der gesamten Fahrzeuganschaffungskosten (inkl. Fracht und Zoll), der über Bankdarlehen finanziert wird.",
        "y1_loan_rate": "KfW Gründerkredit Zins (J1) %",
        "y2_loan_rate": "Standard Bankzins (J2+) %",
        "int_rate": "Guthabenzinsen (%)",
        "sec9": "9. SONSTIGE ERTRÄGE / RESTWERT",
        "thg": "THG-Quote pro Fahrzeug/Jahr",
        "help_thg": "Treibhausgasminderungsquote. Handelbare Zertifikate für den Betrieb von Elektrofahrzeugen.",
        "salvage": "Fahrzeugverkaufspreis (J4)",
        
        "pnl_gbv": "Bruttobuchungswert (Kunde zahlt inkl. 19% USt)",
        "pnl_vat": "Abzüglich: 19% Umsatzsteuer (Finanzamt)",
        "pnl_net_rev": "Umsatzerlöse (netto)",
        "pnl_tesla_fee": "Abzüglich: Tesla-Plattformgebühr (auf BBW)",
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
        
        "cf_ni": "+ Jahresüberschuss",
        "cf_depr": "+ Abschreibungen (AfA)",
        "cf_gain_sale": "- Buchgewinn aus Anlagenabgang",
        "cf_tax_prov": "+ Zunahme Steuerrückstellungen",
        "cf_tax_paid": "- Gezahlte Steuern (Monat 5 des Folgejahres)",
        "cf_vat_coll": "+ Erhaltene Umsatzsteuer (laufender Betrieb)",
        "cf_vat_paid": "- Gezahlte Umsatzsteuer (laufender Betrieb)",
        "cf_op": "Operativer Cashflow",
        "cf_capex": "- Auszahlungen für Sachanlagen (CapEx inkl. USt)",
        "cf_vat_ref": "+ USt-Erstattung vom Finanzamt (auf CapEx)",
        "cf_sale": "+ Einzahlungen aus Anlagenabgängen",
        "cf_inv": "Cashflow aus Investitionstätigkeit",
        "cf_eq": "+ Einzahlungen Eigenkapital",
        "cf_sh": "+ Einzahlungen Gesellschafterdarlehen",
        "cf_kfw_draw": "+ Einzahlungen Fahrzeugdarlehen",
        "cf_prin": "- Tilgung Darlehen",
        "cf_vat_draw": "+ Einzahlungen USt-Überbrückungskredit",
        "cf_vat_repay": "- Tilgung USt-Überbrückungskredit",
        "cf_fin": "Cashflow aus Finanzierungstätigkeit",
        "cf_net": "Nettoveränderung Finanzmittel",
        "cf_beg": "+ Anfangsbestand Finanzmittel",
        "cf_end": "Endbestand Finanzmittel",
        
        "bs_gfa": "Brutto-Sachanlagen",
        "bs_acc_depr": "- Kumulierte Abschreibungen",
        "bs_nfa": "Netto-Sachanlagen (Anlagevermögen)",
        "bs_vat_rec": "Umsatzsteuerforderungen (Finanzamt)",
        "bs_cash": "Kassenbestand / Bankguthaben",
        "bs_tca": "Summe Umlaufvermögen",
        "bs_ta": "SUMME AKTIVA",
        "bs_eq_share": "Gezeichnetes Kapital (Stammkapital)",
        "bs_eq_ret": "Gewinnvortrag / Jahresüberschuss",
        "bs_teq": "Summe Eigenkapital",
        "bs_prov_tax": "Steuerrückstellungen",
        "bs_tprov": "Summe Rückstellungen",
        "bs_debt_kfw": "Verbindlichkeiten ggü. Kreditinstituten",
        "bs_debt_vat": "Kurzfristige Verbindlichkeiten (USt-Kredit)",
        "bs_pay_vat": "Umsatzsteuer-Zahllast",
        "bs_sh_loan": "Gesellschafterdarlehen",
        "bs_tliab": "Summe Verbindlichkeiten",
        "bs_tleq": "SUMME PASSIVA",
        "bs_check": "BILANZKONTROLLE (Aktiva - Passiva)",

        "tab_kpi": "KPIs & Kennzahlen",
        "kpi_dscr": "Schuldendienstdeckungsgrad (DSCR)",
        "kpi_eq_ratio": "Eigenkapitalquote",
        "kpi_runway": "Liquiditätsreichweite (Monate)",
        "kpi_net_ltv": "Netto-LTV (Cash-bereinigt)",
        "kpi_var_ratio": "Variable Kostenquote",
        "kpi_fix_ratio": "Fixkostenquote",
        "kpi_tot_ratio": "Gesamtkostenquote",
        "kpi_db2_m": "Deckungsbeitragsmarge (DB2)",
        "kpi_ebitda_m": "EBITDA-Marge",
        
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
        "monthly": "Monatlich (Detailansicht)",
        "exp_y1": "J1 Aufklappen",
        "exp_y2": "J2 Aufklappen",
        "exp_y3": "J3 Aufklappen",
        "exp_y4": "J4 Aufklappen",
        "exp_y5": "J5 Aufklappen",
        "glossary_title": "Erläuterungen der Kennzahlen & Methodik"
    }
    month_names = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

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

st.sidebar.header(loc["sec1b"])
active_hours_per_day = st.sidebar.number_input(loc["active_hours"], value=16.0)
avg_speed_kmh = st.sidebar.number_input(loc["speed"], value=22.0)
deadhead_rate = st.sidebar.number_input(loc["deadhead"], value=30.0, help=loc["help_deadhead"]) / 100

st.sidebar.header(loc["sec1c"])
util_mode = st.sidebar.radio(loc["util_mode"], [loc["util_dyn"], loc["util_fix"]])
if util_mode == loc["util_dyn"]:
    target_util = st.sidebar.number_input(loc["target_util"], value=90.0, help=loc["help_target"]) / 100
    init_util = st.sidebar.number_input(loc["init_util"], value=60.0, help=loc["help_init"]) / 100
    rec_rate = st.sidebar.number_input(loc["rec_rate"], value=5.0, help=loc["help_rec"]) / 100
    can_fac = st.sidebar.number_input(loc["can_fac"], value=0.5, step=0.1, help=loc["help_can"])
    flat_util = target_util
else:
    flat_util = st.sidebar.number_input(loc["util_fix"], value=90.0) / 100
    target_util, init_util, rec_rate, can_fac = flat_util, flat_util, 0, 0

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
energy_rate = st.sidebar.number_input(loc["energy_rate"], value=0.0424, format="%.4f", step=0.0001, help=loc["energy_help"])

st.sidebar.header(loc["sec5"])
insurance_pm = st.sidebar.number_input(loc["insurance"], value=300.0)
parking_pm = st.sidebar.number_input(loc["parking"], value=150.0)
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

st.sidebar.header(loc["sec8"])
stammkapital = st.sidebar.number_input(loc["stamm"], value=25000.0)
shareholder_loan = st.sidebar.number_input(loc["sh_loan"], value=15000.0)
vehicle_ltv = st.sidebar.number_input(loc["ltv"], value=80.0, help=loc["help_ltv"]) / 100
y1_loan_rate = st.sidebar.number_input(loc["y1_loan_rate"], value=4.5, step=0.1) / 100
y2_loan_rate = st.sidebar.number_input(loc["y2_loan_rate"], value=5.5, step=0.1) / 100
interest_income_rate = st.sidebar.number_input(loc["int_rate"], value=2.2) / 100

st.sidebar.header(loc["sec9"])
thg_quote_per_car_py = st.sidebar.number_input(loc["thg"], value=200.0, help=loc["help_thg"])
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
        rate = y1_loan_rate if m < 12 else y2_loan_rate
        cohorts.append({
            "start_month": m + 1,
            "size": mo_val,
            "capex": capex,
            "original_loan": loan,
            "loan_bal": loan,
            "rate": rate,
            "afa_per_mo": capex / 48
        })

# Day 1 Math for UI Cards
day_1_loan = sum(c["original_loan"] for c in cohorts if c["start_month"] == 1)
day_1_uses = (day_1_loan / vehicle_ltv) + it_hardware_capex_y1 if day_1_loan > 0 else 0
day_1_cash_ui = stammkapital + shareholder_loan + day_1_loan - day_1_uses

# --- 3. TRIP PHYSICS BASE ---
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

# --- 4. 60-MONTH DYNAMIC MATRIX ---
pnl_keys = [
    loc["pnl_gbv"], loc["pnl_vat"], loc["pnl_net_rev"], loc["pnl_tesla_fee"], loc["pnl_mrrg_net"],
    loc["pnl_energy"], loc["pnl_wear"], loc["pnl_clean"], loc["pnl_db1"], loc["pnl_ins"], loc["pnl_park"],
    loc["pnl_api"], loc["pnl_tuev"], loc["pnl_sub"], loc["pnl_db2"], loc["pnl_hq_lease"], loc["pnl_it"],
    loc["pnl_legal"], loc["pnl_hq_ins"], loc["pnl_fees"], loc["pnl_bank"], loc["pnl_thg"], loc["pnl_salvage"],
    loc["pnl_ebitda"], loc["pnl_afa_veh"], loc["pnl_afa_it"], loc["pnl_ebit"], loc["pnl_int_inc"], loc["pnl_int_exp"],
    loc["pnl_ebt"], loc["pnl_tax"], loc["pnl_ni"]
]

cf_keys = [
    loc["cf_ni"], loc["cf_depr"], loc["cf_gain_sale"], loc["cf_tax_prov"], loc["cf_tax_paid"], 
    loc["cf_vat_coll"], loc["cf_vat_paid"], loc["cf_op"], 
    loc["cf_capex"], loc["cf_vat_ref"], loc["cf_sale"], loc["cf_inv"], 
    loc["cf_eq"], loc["cf_sh"], loc["cf_kfw_draw"], loc["cf_prin"], loc["cf_vat_draw"], loc["cf_vat_repay"], loc["cf_fin"], 
    loc["cf_net"], loc["cf_beg"], loc["cf_end"]
]

bs_keys = [
    loc["bs_gfa"], loc["bs_acc_depr"], loc["bs_nfa"], loc["bs_vat_rec"], loc["bs_cash"], loc["bs_tca"], loc["bs_ta"],
    loc["bs_eq_share"], loc["bs_eq_ret"], loc["bs_teq"], loc["bs_prov_tax"], loc["bs_tprov"],
    loc["bs_debt_kfw"], loc["bs_debt_vat"], loc["bs_pay_vat"], loc["bs_sh_loan"], loc["bs_tliab"], loc["bs_tleq"], loc["bs_check"]
]

pnl_monthly = {k: [] for k in pnl_keys}
cf_monthly = {k: [] for k in cf_keys}
bs_monthly = {k: [] for k in bs_keys}

tax_schedule = {1: 0.23520, 2: 0.22465, 3: 0.21410, 4: 0.20355, 5: 0.19300}

# Dynamic Trackers
current_cash = 0
vat_loan_bal = 0
operational_vat_payable = 0
vat_receivable = 0
tax_provision_bal = 0
cum_ebt_year = 0
cum_gfa = 0
cum_depr = 0
cum_net_income = 0
kfw_loan_bal = 0

vat_repay_schedule = [0]*70 
tax_payment_schedule = [0]*70
active_fleet_by_month = []
utilization_by_month = []
month_col_names = []

current_u = init_util if util_mode == loc["util_dyn"] else flat_util
prev_fleet = 0

for m in range(60):
    current_month = m + 1
    current_year_cal = 2028 + (m // 12)
    current_month_index = (m % 12) + 1
    current_year = (m // 12) + 1
    
    month_col_names.append(f"{month_names[current_month_index-1]} '{str(current_year_cal)[-2:]}")
    
    days_in_mo = calendar.monthrange(current_year_cal, current_month_index)[1]
    
    if current_month_index in [12, 1, 2]: season_mult = 1.4
    elif current_month_index in [11, 3]: season_mult = 1.3
    else: season_mult = 1.0
        
    active_fleet = 0
    current_veh_afa = 0
    fleet_sale_rev = 0
    int_exp = 0
    prin_pay = 0
    kfw_draw = 0
    capex_this_mo = 0
    capex_sold_this_mo = 0
    
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
            capex_sold_this_mo += c["capex"]

    # --- DYNAMIC UTILIZATION LOGIC ---
    if util_mode == loc["util_dyn"]:
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
    current_it_afa = (it_hardware_capex_y1 / 36) if current_month <= 36 else 0
    total_afa_this_mo = current_veh_afa + current_it_afa
    
    gbv_mo = gross_booking_value_per_day_per_car * op_days * active_fleet
    net_rev_mo = gbv_mo / (1 + vat_rate)
    vat_owed_mo = gbv_mo - net_rev_mo
    tesla_fee_mo = gbv_mo * tesla_take_rate
    mrrg_net_mo = net_rev_mo - tesla_fee_mo
    
    total_km_mo = actual_total_km_per_day * op_days * active_fleet
    wear_mo = total_km_mo * wear_and_tear_rate
    energy_mo = total_km_mo * (energy_rate * season_mult)
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
    ebit_mo = ebitda_mo - total_afa_this_mo
    
    int_inc_mo = current_cash * (interest_income_rate / 12) if current_cash > 0 else 0
    
    # VAT Bridge Loan
    vat_draw_mo = capex_this_mo * vat_rate
    vat_loan_bal += vat_draw_mo
    vat_repay_schedule[current_month + 6] += vat_draw_mo
    
    vat_refund_inflow = vat_repay_schedule[current_month]
    vat_repay_mo = vat_refund_inflow
    vat_loan_bal -= vat_repay_mo
    vat_int_mo = vat_loan_bal * (0.08 / 12)
    int_exp += vat_int_mo
    
    ebt_mo = ebit_mo + int_inc_mo - int_exp
    cum_ebt_year += ebt_mo
    
    tax_exp_mo = 0
    if current_month % 12 == 0:
        tax_exp_mo = max(0, cum_ebt_year) * tax_schedule[current_year]
        cum_ebt_year = 0
        tax_payment_schedule[current_month + 5] = tax_exp_mo
        
    net_inc_mo = ebt_mo - tax_exp_mo
    
    # WORKING CAPITAL & CASH FLOW
    tax_paid_mo = -tax_payment_schedule[current_month]
    op_vat_collected = vat_owed_mo
    op_vat_paid = -operational_vat_payable
    
    op_cf_mo = net_inc_mo + total_afa_this_mo - fleet_sale_rev + tax_exp_mo + tax_paid_mo + op_vat_collected + op_vat_paid
    inv_cf_mo = -(capex_this_mo + vat_draw_mo) + vat_refund_inflow + fleet_sale_rev
    
    eq_in = stammkapital if current_month == 1 else 0
    sh_in = shareholder_loan if current_month == 1 else 0
    fin_cf_mo = eq_in + sh_in + kfw_draw - prin_pay + vat_draw_mo - vat_repay_mo
    
    net_cf_mo = op_cf_mo + inv_cf_mo + fin_cf_mo
    beg_cash = current_cash
    end_cash = beg_cash + net_cf_mo
    
    # UPDATE BALANCE SHEET STATE
    cum_gfa += capex_this_mo - capex_sold_this_mo
    cum_depr += total_afa_this_mo - capex_sold_this_mo 
    nfa = cum_gfa - cum_depr
    vat_receivable += vat_draw_mo - vat_refund_inflow
    current_cash = end_cash
    operational_vat_payable = op_vat_collected
    tax_provision_bal += tax_exp_mo + tax_paid_mo
    cum_net_income += net_inc_mo
    
    kfw_loan_bal = sum(c["loan_bal"] for c in cohorts if current_month >= c["start_month"])
    
    total_assets = nfa + vat_receivable + current_cash
    total_equity = stammkapital + cum_net_income
    total_prov = tax_provision_bal
    total_liab = kfw_loan_bal + vat_loan_bal + operational_vat_payable + shareholder_loan
    total_liab_eq = total_equity + total_prov + total_liab
    bs_check_val = round(total_assets - total_liab_eq, 2)
    
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
    cf_monthly[loc["cf_depr"]].append(total_afa_this_mo)
    cf_monthly[loc["cf_gain_sale"]].append(-fleet_sale_rev)
    cf_monthly[loc["cf_tax_prov"]].append(tax_exp_mo)
    cf_monthly[loc["cf_tax_paid"]].append(tax_paid_mo)
    cf_monthly[loc["cf_vat_coll"]].append(op_vat_collected)
    cf_monthly[loc["cf_vat_paid"]].append(op_vat_paid)
    cf_monthly[loc["cf_op"]].append(op_cf_mo)
    cf_monthly[loc["cf_capex"]].append(-(capex_this_mo + vat_draw_mo))
    cf_monthly[loc["cf_vat_ref"]].append(vat_refund_inflow)
    cf_monthly[loc["cf_sale"]].append(fleet_sale_rev)
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

    # Append BS
    bs_monthly[loc["bs_gfa"]].append(cum_gfa)
    bs_monthly[loc["bs_acc_depr"]].append(-cum_depr)
    bs_monthly[loc["bs_nfa"]].append(nfa)
    bs_monthly[loc["bs_vat_rec"]].append(vat_receivable)
    bs_monthly[loc["bs_cash"]].append(current_cash)
    bs_monthly[loc["bs_tca"]].append(vat_receivable + current_cash)
    bs_monthly[loc["bs_ta"]].append(total_assets)
    bs_monthly[loc["bs_eq_share"]].append(stammkapital)
    bs_monthly[loc["bs_eq_ret"]].append(cum_net_income)
    bs_monthly[loc["bs_teq"]].append(total_equity)
    bs_monthly[loc["bs_prov_tax"]].append(tax_provision_bal)
    bs_monthly[loc["bs_tprov"]].append(total_prov)
    bs_monthly[loc["bs_debt_kfw"]].append(kfw_loan_bal)
    bs_monthly[loc["bs_debt_vat"]].append(vat_loan_bal)
    bs_monthly[loc["bs_pay_vat"]].append(operational_vat_payable)
    bs_monthly[loc["bs_sh_loan"]].append(shareholder_loan)
    bs_monthly[loc["bs_tliab"]].append(total_liab)
    bs_monthly[loc["bs_tleq"]].append(total_liab_eq)
    bs_monthly[loc["bs_check"]].append(bs_check_val)

# --- 5. AGGREGATE TO YEARLY & BUILD UNIFIED DATA ---
def agg_to_yearly(monthly_dict):
    yearly_dict = {}
    for key, arr in monthly_dict.items():
        yearly_arr = []
        for y in range(5):
            chunk = arr[y*12 : (y+1)*12]
            if loc["cf_end"] in key or key in bs_keys:
                yearly_arr.append(chunk[-1])
            elif loc["cf_beg"] in key:
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

# --- 6. KPI CALCULATION ENGINE ---
def safe_div(n, d):
    return np.divide(n.astype(float), d.astype(float), out=np.zeros_like(n.astype(float)), where=d.astype(float)!=0)

# FIXED: EBITDA Margin pinned to top-line Corporate Revenue (pnl_net_rev)
rev_top = df_pnl_combined.loc[loc["pnl_net_rev"]]
ebitda = df_pnl_combined.loc[loc["pnl_ebitda"]]
db2 = df_pnl_combined.loc[loc["pnl_db2"]]
ta = df_bs_combined.loc[loc["bs_ta"]]
teq = df_bs_combined.loc[loc["bs_teq"]]
tliab = df_bs_combined.loc[loc["bs_tliab"]]
cash = df_bs_combined.loc[loc["bs_cash"]]
nfa = df_bs_combined.loc[loc["bs_nfa"]]

var_costs = rev_top - df_pnl_combined.loc[loc["pnl_db1"]]
fix_costs = df_pnl_combined.loc[loc["pnl_db1"]] - ebitda + df_pnl_combined.loc[loc["pnl_thg"]] + df_pnl_combined.loc[loc["pnl_salvage"]]
tot_costs = var_costs + fix_costs
debt_service = -(df_cf_combined.loc[loc["cf_prin"]] + df_pnl_combined.loc[loc["pnl_int_exp"]])

kpi_dict = {}
# FIXED: DSCR formatted to one decimal point
kpi_dict[loc["kpi_dscr"]] = [f"{x:.1f}x" if x > 0 else "n/a" for x in safe_div(ebitda, debt_service)]
kpi_dict[loc["kpi_eq_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(teq, ta)]

runway_arr = []
for col in df_pnl_combined.columns:
    is_year = "Year" in col or "Jahr" in col
    div = (fix_costs[col] + debt_service[col]) / 12 if is_year else (fix_costs[col] + debt_service[col])
    rw = cash[col] / div if div > 0 else 999
    runway_arr.append(f"{rw:.1f} Mo." if rw < 999 else "Infinite")
kpi_dict[loc["kpi_runway"]] = runway_arr

# FIXED: Net LTV allows cash buffer to fully offset liability balance natively
net_debt = tliab - cash
kpi_dict[loc["kpi_net_ltv"]] = [f"{x*100:.1f}%" for x in safe_div(net_debt, nfa)]

kpi_dict[loc["kpi_var_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(var_costs, rev_top)]
kpi_dict[loc["kpi_fix_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(fix_costs, rev_top)]
kpi_dict[loc["kpi_tot_ratio"]] = [f"{x*100:.1f}%" for x in safe_div(tot_costs, rev_top)]
kpi_dict[loc["kpi_db2_m"]] = [f"{x*100:.1f}%" for x in safe_div(db2, rev_top)]
kpi_dict[loc["kpi_ebitda_m"]] = [f"{x*100:.1f}%" for x in safe_div(ebitda, rev_top)]

df_kpi_combined = pd.DataFrame(kpi_dict, index=df_pnl_combined.columns).T

# --- 7. DASHBOARD RENDER ---
st.subheader(loc["sources_title"])
colA, colB, colC, colD = st.columns(4)
colA.metric(loc["src_stamm"], f"€ {stammkapital:,.0f}")
colB.metric(loc["src_sh"], f"€ {shareholder_loan:,.0f}")
colC.metric(f"{loc['src_veh']} ({vehicle_ltv*100:.0f}%)", f"€ {day_1_loan:,.0f}")
colD.metric(loc["liquidity"], f"€ {day_1_cash_ui:,.0f}")

st.divider()
st.subheader(loc["output_title"])

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

tabs = st.tabs([loc["tab_pnl"], loc["tab_cf"], loc["tab_bs"], loc["tab_kpi"]])

def style_pnl_rows(row):
    if loc["pnl_mrrg_net"] in row.name:
        return ['font-weight: 600; border-top: 1px solid #ffffff40; color: #4DA8DA;'] * len(row)
    elif loc["pnl_db1"] in row.name or loc["pnl_db2"] in row.name:
        return ['font-weight: 600; background-color: #1e1e1e; border-top: 1px solid #ffffff40;'] * len(row)
    elif loc["pnl_ebitda"] in row.name:
        return ['font-weight: 700; background-color: #2b2b2b; color: #F2A900;'] * len(row)
    elif loc["pnl_ebit"] in row.name:
        return ['font-weight: 600; background-color: #1e1e1e;'] * len(row)
    elif loc["pnl_ebt"] in row.name:
        return ['font-weight: 600; border-top: 1px solid #ffffff40;'] * len(row)
    elif loc["pnl_ni"] in row.name:
        return ['font-weight: 700; background-color: #0b2e13; color: #38c172; font-size: 1.05em; border-top: 2px solid #38c172;'] * len(row)
    return [''] * len(row)

def style_cf_rows(row):
    if loc["cf_op"] in row.name or loc["cf_inv"] in row.name or loc["cf_fin"] in row.name:
        return ['font-weight: 700; background-color: #1e1e1e; color: #4DA8DA; border-top: 1px solid #ffffff40;'] * len(row)
    elif loc["cf_net"] in row.name:
        return ['font-weight: 700; background-color: #2b2b2b; color: #F2A900;'] * len(row)
    elif loc["cf_end"] in row.name:
        return ['font-weight: 700; background-color: #0b2e13; color: #38c172; font-size: 1.05em; border-top: 2px solid #38c172;'] * len(row)
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
    if loc["kpi_dscr"] in row.name or loc["kpi_ebitda_m"] in row.name or loc["kpi_runway"] in row.name:
        return ['font-weight: 700; background-color: #1e1e1e; color: #F2A900;'] * len(row)
    return [''] * len(row)

with tabs[0]:
    st.dataframe(df_pnl_combined[display_cols].style.format("{:,.0f} €").apply(style_pnl_rows, axis=1), use_container_width=True)

with tabs[1]:
    st.dataframe(df_cf_combined[display_cols].style.format("{:,.0f} €").apply(style_cf_rows, axis=1), use_container_width=True)

with tabs[2]:
    st.dataframe(df_bs_combined[display_cols].style.format("{:,.0f} €").apply(style_bs_rows, axis=1), use_container_width=True)

with tabs[3]:
    st.dataframe(df_kpi_combined[display_cols].style.apply(style_kpi_rows, axis=1), use_container_width=True)
    
    # Layman KPI Glossary Expanders
    st.write("")
    with st.expander(loc["glossary_title"]):
        if lang_choice == "English":
            st.markdown("""
            * **Debt Service Coverage Ratio (DSCR):** Measures our capacity to clear required bank loan installments. Calculated as *EBITDA / Total Debt Service (Principal + Interest)*. A value of 1.5x means we have 50% more operational cash than needed to satisfy current bank collections.
            * **Equity Ratio:** Shows what share of corporate assets are owned directly by the shareholders rather than financed via third-party bank debt. Calculated as *Total Equity / Total Assets*.
            * **Liquidity Runway:** A worst-case stress test tracking survival time if revenues instantly drop to zero. Calculated as *Cash Balance / (Monthly Fixed Overhead + Monthly Debt Service Liabilities)*.
            * **Net LTV:** Measures structural asset leverage net of our treasury cushion. Calculated as *(Total Liabilities - Cash) / Net Fixed Assets*. A negative percentage indicates that company liquidity fully shields outstanding corporate liabilities.
            * **Variable Expense Ratio:** Measures proportional cost exposure running the cars. Calculated as *Total Variable Operating Costs / Top-line Net Revenue*.
            * **Fixed Expense Ratio:** Tracks the margin impact of baseline corporate infrastructure. Calculated as *Total Fixed Operating Costs / Top-line Net Revenue*.
            * **Total Expense Ratio:** Measures total combined efficiency overhead drag against top-line revenues. Calculated as *Total Operational Expenses / Top-line Net Revenue*.
            * **Contribution Margin Ratio (DB2):** Measures stand-alone asset portfolio performance before accounting for corporate headquarters drag. Calculated as *Deckungsbeitrag 2 / Top-line Net Revenue*.
            * **EBITDA Margin:** Core cash profitability metric monitoring standardized operating efficiency before accounting for non-cash asset depreciation, financing structures, or sovereign tax loads. Calculated as *EBITDA / Top-line Net Revenue*.
            """)
        else:
            st.markdown("""
            * **Schuldendienstdeckungsgrad (DSCR):** Misst die Fähigkeit des Unternehmens, Zinsen und Tilgungen für Bankkredite zu bedienen. Berechnung: *EBITDA / (Zinsaufwand + Tilgung)*. Ein Wert von 1,5x bedeutet, dass 50% mehr operativer Cashflow generiert wird, als für den Bankendienst nötig ist.
            * **Eigenkapitalquote:** Zeigt den prozentualen Anteil des durch Gesellschafter finanzierten Vermögens im Vergleich zur Fremdkapitalfinanzierung. Berechnung: *Summe Eigenkapital / Bilanzsumme*.
            * **Liquiditätsreichweite:** Ein Stress-Test-Szenario, das die Überlebenszeit bei plötzlichem Umsatzausfall prognostiziert. Berechnung: *Kassenbestand / (Monatliche Fixkosten + Monatlicher Schuldendienst)*.
            * **Netto-LTV:** Misst den Netto-Verschuldungsgrad unseres Anlagevermögens unter Berücksichtigung des Cash-Bestands. Berechnung: *(Summe Verbindlichkeiten - Kasse) / Netto-Sachanlagen*. Ein negativer Prozentsatz bedeutet, dass die Kassenbestände alle Verbindlichkeiten vollständig abdecken.
            * **Variable Kostenquote:** Gibt an, wie viel Prozent jedes erwirtschafteten Euros direkt für den Betrieb der Fahrzeuge aufgewendet werden (Plattformgebühren, Strom, Reinigung). Berechnung: *Variable Kosten / Netto-Umsatzerlöse*.
            * **Fixkostenquote:** Zeigt den prozentualen Anteil des Umsatzes, der durch die feste Unternehmensinfrastruktur aufgezehrt wird. Berechnung: *Fixkosten / Netto-Umsatzerlöse*.
            * **Gesamtkostenquote:** Bildet die gesamte betriebliche Kostenstruktur des operativen Geschäfts ab. Berechnung: *Gesamte betriebliche Kosten / Netto-Umsatzerlöse*.
            * **Deckungsbeitragsmarge (DB2):** Zeigt die reine Rentabilität der Fahrzeugflotte vor Abzug der HQ-Verwaltungskosten. Berechnung: *Deckungsbeitrag 2 / Netto-Umsatzerlöse*.
            * **EBITDA-Marge:** Der zentrale Indikator für die operative Cash-Rentabilität des Unternehmens, unabhängig von Abschreibungen, Zinsen oder Steuern. Berechnung: *EBITDA / Netto-Umsatzerlöse*.
            """)
