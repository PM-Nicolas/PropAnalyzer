# PropAnalyzer Reloaded

**Automated Real Estate Underwriting with ESG Layer**

A web-based tool that automates the entire underwriting process for commercial real estate investments. Upload a property document (Offering Memorandum, Property Condition Report, etc.) and receive a complete investment analysis in under 60 seconds - including 10-year DCF, sensitivity analysis, and ESG risk assessment based on CRREM methodology.

---

## The Problem

REPE analysts typically spend 3-6 hours per property extracting data from PDFs and building DCF models in Excel. With 20 properties in the pipeline, that's 60-120 hours per month on tasks that can be automated. Existing tools like Argus Enterprise are powerful but lack integrated ESG analysis - critical for European real estate given EU Taxonomy and CSRD requirements.

## The Solution

PropAnalyzer combines three layers in one tool:

1. **AI-powered PDF extraction** using Claude API
2. **Standard underwriting** with IRR, NPV, Equity Multiple, and Sensitivity Analysis
3. **ESG analysis** using CRREM methodology to assess Stranded Asset risk and renovation economics

---

## Screenshots

### Property Information
![Property Info](docs/screenshots/01_property_info.png)

### DCF Underwriting Results
![DCF Results](docs/screenshots/02_dcf_results.png)

### Sensitivity Analysis
![Sensitivity Heatmap](docs/screenshots/03_sensitivity_heatmap.png)

### ESG Analysis with CRREM Stranding
![ESG Analysis](docs/screenshots/04_esg_analysis.png)

### Adjustable Assumptions
![Sidebar](docs/screenshots/05_assumptions_sidebar.png)

---

## Features

### PDF Extraction (Claude API)
- Extracts structured data from property documents
- Handles US and European formats
- Auto-converts USD/EUR and sqft/sqm

### DCF Engine
- 10-year projection with NOI growth, vacancy, debt service
- Exit value calculation with cap rate expansion
- Returns: IRR, NPV, Equity Multiple, Cash-on-Cash

### Sensitivity Analysis
- 30 scenarios across Cap Rate Change x Vacancy Rate
- Color-coded heatmap for quick risk assessment

### ESG Layer (Unique USP)
- Energy class estimation when not provided
- CRREM 1.5°C pathway calculation for Stranding Year
- Brown Discount on property value
- Renovation CapEx estimation
- Net benefit analysis (renovation costs vs value uplift)
- Investment recommendation: Renovate / Hold / Exit

---

## Tech Stack

- **Backend:** Python, FastAPI
- **Frontend:** Streamlit
- **AI:** Anthropic Claude API (claude-sonnet-4-6)
- **Data Processing:** pandas, numpy, numpy_financial
- **PDF Generation:** reportlab
- **PDF Reading:** pypdf

---

## Methodology Sources

The tool's assumptions are based on industry-standard sources:

- **CRREM Pathway:** Carbon Risk Real Estate Monitor (crrem.eu) for stranding year calculations
- **Green Premium (7%):** JLL "Decarbonising Real Estate" Report 2024, CBRE Research
- **Renovation Costs:** German construction industry benchmarks (Statistisches Bundesamt)
- **Cap Rates:** Real Capital Analytics European market data
- **DCF Standards:** ULI, INREV best practices

---

## Demo

Live demo available on request. Contact: [zinnnicolas@gmail.com](mailto:zinnnicolas@gmail.com)

For local installation, see Setup section below.

---

## Setup

```bash
# Clone repository
git clone https://github.com/PM-Nicolas/PropAnalyzer.git
cd PropAnalyzer

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Setup environment
echo ANTHROPIC_API_KEY=your-key-here > .env
mkdir .streamlit
echo APP_PASSWORD = "your-password" > .streamlit/secrets.toml

# Run
streamlit run streamlit_app.py
```

---

## Why This Project

This tool was built as part of my preparation for entering the Distressed Real Estate / ESG investment space. The European commercial real estate market is in a structural transition driven by:

1. **Cap Rate expansion** from 2022 interest rate hikes
2. **Distressed asset opportunities** in office and retail
3. **EU regulatory pressure** (CSRD, SFDR, EU Taxonomy)
4. **Stranded asset risk** for non-compliant buildings

Tools that integrate underwriting with ESG analysis will be increasingly critical for investment teams navigating this transition. PropAnalyzer is a working prototype demonstrating this integration.

---

## Author

**Nico Zinn**
Banking apprentice (Volksbank Kraichgau) with focus on Real Estate Tech and Quantitative Analysis.

GitHub: [@PM-Nicolas](https://github.com/PM-Nicolas)

---

## License

MIT - Free to use and modify.

---

*Built in 4 weeks as part of a Real Estate Tech portfolio. Production version would add: news sentiment integration, multi-property portfolio analysis, full CRREM API integration, and German market-specific cap rate adjustments.*