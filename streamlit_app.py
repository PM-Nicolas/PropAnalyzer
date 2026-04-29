import streamlit as st
import sys
import os
import json
import pandas as pd

# Pfade hinzufuegen damit Imports funktionieren
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.pdf_extractor import extract_property_data
from app.dcf_engine import calculate_dcf, calculate_sensitivity, DEFAULT_ASSUMPTIONS
from app.esg_layer import analyze_esg

# ============= PASSWORT-SCHUTZ =============
def check_password():
    """Returns True wenn der User das richtige Passwort eingegeben hat."""
    
    def password_entered():
        if st.session_state["password"] == st.secrets.get("APP_PASSWORD", "demo2026"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    
    if "password_correct" not in st.session_state:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.info("Diese App ist passwortgeschuetzt. Bitte Passwort eingeben.")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("Falsches Passwort")
        return False
    else:
        return True


if not check_password():
    st.stop()
# ============= ENDE PASSWORT-SCHUTZ =============

# Page Config
st.set_page_config(
    page_title="PropAnalyzer Reloaded",
    page_icon="building",
    layout="wide"
)

# Header
st.title("PropAnalyzer Reloaded")
st.markdown("**Automated Real Estate Underwriting with ESG Layer**")
st.markdown("---")

# Sidebar - Assumptions
st.sidebar.header("DCF Assumptions")
rent_growth = st.sidebar.slider("Rent Growth Rate", 0.0, 0.05, 0.025, 0.005, format="%.3f")
vacancy = st.sidebar.slider("Vacancy Rate", 0.0, 0.30, 0.05, 0.01, format="%.2f")
cap_rate_change = st.sidebar.slider("Exit Cap Rate Change (bps)", -100, 300, 50, 25)
ltv = st.sidebar.slider("Loan-to-Value", 0.4, 0.8, 0.6, 0.05, format="%.2f")
interest_rate = st.sidebar.slider("Interest Rate", 0.02, 0.08, 0.045, 0.005, format="%.3f")
hold_period = st.sidebar.slider("Hold Period (Years)", 5, 15, 10)

custom_assumptions = DEFAULT_ASSUMPTIONS.copy()
custom_assumptions["rent_growth_rate"] = rent_growth
custom_assumptions["vacancy_rate"] = vacancy
custom_assumptions["exit_cap_rate_increase"] = cap_rate_change / 10000
custom_assumptions["ltv"] = ltv
custom_assumptions["interest_rate"] = interest_rate
custom_assumptions["hold_period_years"] = hold_period

# Main: PDF Upload
uploaded_file = st.file_uploader(
    "Upload Property Document (PDF)",
    type="pdf",
    help="Lade ein Offering Memorandum, Property Condition Report oder aehnliches PDF hoch"
)

# Test-Daten Option
use_test_data = st.checkbox(
    "Test-Daten nutzen (Detroit Property)",
    value=False,
    help="Falls kein PDF zur Hand - nutze Beispieldaten zum Testen"
)

# Verarbeitung
if uploaded_file or use_test_data:
    
    if use_test_data:
        property_data = {
            "property_info": {
                "address": "400 Bagley, Detroit, MI 48226",
                "year_built": 1927,
                "property_type": "mixed",
                "total_sqm": 32143.7,
                "occupancy_rate": 0.137
            },
            "financials": {
                "current_noi": None,
                "operating_expenses": 3218815.0,
                "gross_rental_income": 7339788.0,
                "rent_per_sqm": 35.31,
                "purchase_price": None
            },
            "lease_info": {},
            "building_specs": {
                "energy_certificate_class": None,
                "heating_type": "other",
                "last_renovation_year": 1964
            }
        }
    else:
        # Datei temporaer speichern und extrahieren
        with st.spinner("Extracting data with Claude API..."):
            temp_path = "temp_upload.pdf"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())
            
            try:
                property_data = extract_property_data(temp_path)
                if property_data is None:
                    st.error("Extraktion fehlgeschlagen. Bitte anderes PDF probieren.")
                    st.stop()
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
    
    # Property Info Section
    st.header("Property Information")
    
    info = property_data["property_info"]
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Address", info.get("address", "N/A"))
        st.metric("Year Built", info.get("year_built", "N/A"))
    with col2:
        st.metric("Property Type", (info.get("property_type") or "N/A").upper())
        st.metric("Size", f"{info.get('total_sqm', 0):,.0f} sqm" if info.get("total_sqm") else "N/A")
    with col3:
        occupancy = info.get("occupancy_rate", 0)
        st.metric("Occupancy", f"{occupancy*100:.1f}%" if occupancy else "N/A")
        building = property_data.get("building_specs", {})
        st.metric("Last Renovation", building.get("last_renovation_year", "N/A"))
    
    st.markdown("---")
    
    # DCF Section
    st.header("Underwriting Analysis")
    
    with st.spinner("Running DCF calculations..."):
        dcf_results = calculate_dcf(property_data, custom_assumptions)
    
    if "error" in dcf_results:
        st.error(f"DCF Error: {dcf_results['error']}")
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "IRR",
                f"{dcf_results['irr']*100:.2f}%" if dcf_results.get('irr') else "N/A"
            )
        with col2:
            st.metric(
                "Equity Multiple",
                f"{dcf_results['equity_multiple']:.2f}x" if dcf_results.get('equity_multiple') else "N/A"
            )
        with col3:
            st.metric(
                "NPV",
                f"${dcf_results['npv']/1e6:.2f}M" if dcf_results.get('npv') else "N/A"
            )
        with col4:
            st.metric(
                "Purchase Price",
                f"${dcf_results['purchase_price']/1e6:.1f}M"
            )
        
        # Cash Flow Tabelle
        st.subheader("10-Year Cash Flow Projection")
        
        cf_df = pd.DataFrame({
            "Year": list(range(1, len(dcf_results["cash_flows"]) + 1)),
            "NOI": dcf_results["noi_projections"],
            "Cash Flow": dcf_results["cash_flows"]
        })
        cf_df["NOI"] = cf_df["NOI"].apply(lambda x: f"${x:,.0f}")
        cf_df["Cash Flow"] = cf_df["Cash Flow"].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(cf_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Sensitivity Section
    st.header("Sensitivity Analysis")
    
    with st.spinner("Computing scenarios..."):
        sensitivity = calculate_sensitivity(property_data, custom_assumptions)
    
    sens_df = pd.DataFrame(
        sensitivity["irr_matrix"],
        index=[f"{int(v*100)}%" for v in sensitivity["vacancy_rates"]],
        columns=[f"{int(c*10000):+d}bps" for c in sensitivity["cap_rate_changes"]]
    )
    sens_df.index.name = "Vacancy"
    sens_df.columns.name = "Cap Rate Change"
    
    # Heatmap mit Streamlit
    st.dataframe(
        sens_df.style.background_gradient(cmap="RdYlGn", axis=None).format("{:.2f}%"),
        use_container_width=True
    )
    st.caption("IRR (%) by Vacancy Rate and Cap Rate Expansion")
    
    st.markdown("---")
    
    # ESG Section - Der USP!
    st.header("ESG Analysis")
    
    with st.spinner("Analyzing ESG factors..."):
        esg_results = analyze_esg(property_data)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        energy_class = esg_results['energy_class']
        estimated_label = " (est.)" if esg_results['energy_class_was_estimated'] else ""
        st.metric(f"Energy Class{estimated_label}", energy_class)
    with col2:
        stranding = esg_results['stranding_year']
        st.metric("Stranding Year", stranding if stranding else "Not stranded")
    with col3:
        st.metric("Brown Discount", f"{esg_results['brown_discount_pct']:.1f}%")
    with col4:
        emissions = esg_results['current_emissions_kgco2_per_sqm']
        st.metric("Emissions", f"{emissions} kgCO2/m2/yr")
    
    st.subheader("Renovation Scenario")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Renovation CapEx",
            f"${esg_results['renovation_capex_usd']/1e6:.2f}M"
        )
    with col2:
        st.metric(
            "Value Uplift",
            f"${esg_results['value_uplift_after_renovation_usd']/1e6:.2f}M"
        )
    with col3:
        net = esg_results['net_benefit_usd']
        st.metric(
            "Net Benefit",
            f"${net/1e6:.2f}M",
            delta=f"{'Profitable' if net > 0 else 'Loss-making'}"
        )
    
    # Recommendation Box
    st.subheader("Recommendation")
    rec = esg_results['recommendation']
    
    if "RENOVATE" in rec:
        st.success(rec)
    elif "EXIT" in rec:
        st.error(rec)
    else:
        st.info(rec)
    
    st.markdown("---")
    
    # Raw Data (optional)
    with st.expander("View Raw Extracted Data"):
        st.json(property_data)
    
else:
    st.info("Bitte PDF hochladen oder Test-Daten aktivieren um zu starten")
    
    st.markdown("---")
    st.subheader("How it works")
    st.markdown("""
    1. **Upload PDF** - Property Brochure, Offering Memorandum oder Condition Report
    2. **Claude API extrahiert** strukturierte Daten aus dem PDF
    3. **DCF Engine** berechnet IRR, NPV, Equity Multiple ueber 10 Jahre
    4. **Sensitivitaetsanalyse** zeigt Returns unter verschiedenen Szenarien
    5. **ESG Layer** bewertet Stranding-Risiko und Sanierungs-Wirtschaftlichkeit
    6. **Empfehlung** basierend auf kombinierten Faktoren
    """)