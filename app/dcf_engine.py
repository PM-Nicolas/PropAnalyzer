import numpy as np
import numpy_financial as npf


DEFAULT_ASSUMPTIONS = {
    "rent_growth_rate": 0.025,
    "expense_growth_rate": 0.02,
    "vacancy_rate": 0.05,
    "exit_cap_rate_increase": 0.005,
    "hold_period_years": 10,
    "ltv": 0.60,
    "interest_rate": 0.045,
    "amortization_years": 30,
    "transaction_costs": 0.025,
    "discount_rate": 0.08
}


def calculate_noi_if_missing(property_data):
    """Berechnet NOI falls nicht vorhanden."""
    financials = property_data["financials"]
    if financials.get("current_noi") is not None:
        return financials["current_noi"]
    
    gross_income = financials.get("gross_rental_income")
    op_ex = financials.get("operating_expenses")
    
    if gross_income is not None and op_ex is not None:
        return gross_income - op_ex
    
    return None


def estimate_purchase_price(noi, target_cap_rate=0.07):
    """Schaetzt Kaufpreis basierend auf NOI und Cap Rate."""
    if noi is None:
        return None
    return noi / target_cap_rate


def calculate_debt_service(loan_amount, interest_rate, amortization_years):
    """Berechnet jaehrlichen Kapitaldienst (Annuitaet)."""
    monthly_rate = interest_rate / 12
    n_payments = amortization_years * 12
    monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** n_payments) / \
                     ((1 + monthly_rate) ** n_payments - 1)
    return monthly_payment * 12


def calculate_remaining_loan(loan_amount, interest_rate, amortization_years, years_paid):
    """Berechnet verbleibenden Kredit nach X Jahren."""
    monthly_rate = interest_rate / 12
    n_payments = amortization_years * 12
    payments_made = years_paid * 12
    
    if monthly_rate == 0:
        return loan_amount * (1 - payments_made / n_payments)
    
    remaining = loan_amount * ((1 + monthly_rate) ** n_payments - (1 + monthly_rate) ** payments_made) / \
                ((1 + monthly_rate) ** n_payments - 1)
    return remaining


def calculate_dcf(property_data, assumptions=None):
    """Berechnet komplettes DCF-Modell."""
    if assumptions is None:
        assumptions = DEFAULT_ASSUMPTIONS
    
    # NOI bestimmen
    noi = calculate_noi_if_missing(property_data)
    if noi is None:
        return {"error": "NOI konnte nicht ermittelt werden"}
    
    # Purchase Price bestimmen
    purchase_price = property_data["financials"].get("purchase_price")
    if purchase_price is None:
        purchase_price = estimate_purchase_price(noi)
        if purchase_price is None:
            return {"error": "Purchase Price konnte nicht bestimmt werden"}
    
    # Initial Investment
    transaction_costs = purchase_price * assumptions["transaction_costs"]
    total_acquisition = purchase_price + transaction_costs
    loan_amount = purchase_price * assumptions["ltv"]
    initial_equity = total_acquisition - loan_amount
    
    # Debt Service
    annual_debt_service = calculate_debt_service(
        loan_amount,
        assumptions["interest_rate"],
        assumptions["amortization_years"]
    )
    
    # Year-by-Year Cash Flows
    cash_flows = []
    noi_projections = []
    
    for year in range(1, assumptions["hold_period_years"] + 1):
        # NOI wachsen lassen
        gross_noi = noi * (1 + assumptions["rent_growth_rate"]) ** year
        # Vacancy abziehen
        effective_noi = gross_noi * (1 - assumptions["vacancy_rate"])
        # Operating Expenses wachsen schneller
        # (vereinfacht - hier nehmen wir an NOI ist nach Vacancy bereits berechnet)
        
        noi_projections.append(effective_noi)
        
        # Cash Flow nach Debt Service
        cf = effective_noi - annual_debt_service
        cash_flows.append(cf)
    
    # Exit im letzten Jahr
    exit_noi = noi * (1 + assumptions["rent_growth_rate"]) ** assumptions["hold_period_years"]
    entry_cap_rate = noi / purchase_price
    exit_cap_rate = entry_cap_rate + assumptions["exit_cap_rate_increase"]
    exit_value = exit_noi / exit_cap_rate
    
    remaining_loan = calculate_remaining_loan(
        loan_amount,
        assumptions["interest_rate"],
        assumptions["amortization_years"],
        assumptions["hold_period_years"]
    )
    
    exit_proceeds = exit_value - remaining_loan
    cash_flows[-1] += exit_proceeds
    
    # IRR und NPV berechnen
    full_cash_flow = [-initial_equity] + cash_flows
    
    try:
        irr = npf.irr(full_cash_flow)
    except:
        irr = None
    
    npv = npf.npv(assumptions["discount_rate"], full_cash_flow)
    equity_multiple = sum(cash_flows) / initial_equity if initial_equity > 0 else None
    
    return {
        "purchase_price": round(purchase_price, 2),
        "initial_equity": round(initial_equity, 2),
        "loan_amount": round(loan_amount, 2),
        "annual_debt_service": round(annual_debt_service, 2),
        "current_noi": round(noi, 2),
        "exit_value": round(exit_value, 2),
        "exit_proceeds": round(exit_proceeds, 2),
        "irr": round(irr, 4) if irr is not None else None,
        "equity_multiple": round(equity_multiple, 2) if equity_multiple is not None else None,
        "npv": round(npv, 2),
        "noi_projections": [round(x, 2) for x in noi_projections],
        "cash_flows": [round(x, 2) for x in cash_flows]
    }

def calculate_sensitivity(property_data, base_assumptions=None):
    """Berechnet IRR fuer verschiedene Szenarien."""
    if base_assumptions is None:
        base_assumptions = DEFAULT_ASSUMPTIONS.copy()
    
    # Cap Rate Expansion: -50bps bis +200bps
    cap_rate_changes = [-0.005, 0.0, 0.005, 0.01, 0.015, 0.02]
    # Vacancy: 5% bis 25%
    vacancy_rates = [0.05, 0.10, 0.15, 0.20, 0.25]
    
    results = {
        "cap_rate_changes": cap_rate_changes,
        "vacancy_rates": vacancy_rates,
        "irr_matrix": []
    }
    
    for vacancy in vacancy_rates:
        row = []
        for cap_change in cap_rate_changes:
            scenario_assumptions = base_assumptions.copy()
            scenario_assumptions["exit_cap_rate_increase"] = cap_change
            scenario_assumptions["vacancy_rate"] = vacancy
            
            dcf_result = calculate_dcf(property_data, scenario_assumptions)
            
            if "error" in dcf_result or dcf_result.get("irr") is None:
                row.append(None)
            else:
                row.append(round(dcf_result["irr"] * 100, 2))
        
        results["irr_matrix"].append(row)
    
    return results


def print_sensitivity_table(sensitivity_results):
    """Druckt Sensitivitaets-Tabelle."""
    cap_changes = sensitivity_results["cap_rate_changes"]
    vacancies = sensitivity_results["vacancy_rates"]
    matrix = sensitivity_results["irr_matrix"]
    
    print("\n=== SENSITIVITAETSANALYSE: IRR (%) ===")
    print("Zeilen: Vacancy | Spalten: Cap Rate Change (bps)")
    print()
    
    # Header
    header = "Vacancy"
    for cc in cap_changes:
        header += f" | {int(cc*10000):+d}bps"
    print(header)
    print("-" * len(header))
    
    # Daten
    for i, vacancy in enumerate(vacancies):
        row_str = f"{int(vacancy*100):3d}%   "
        for irr in matrix[i]:
            if irr is None:
                row_str += " |   N/A "
            else:
                row_str += f" | {irr:+6.2f}"
        print(row_str)

if __name__ == "__main__":
    # Test mit den extrahierten Daten von vorhin
    test_data = {
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
        "building_specs": {}
    }
    
    result = calculate_dcf(test_data)
    
    print("=== DCF ERGEBNISSE ===")
    if "error" in result:
        print(f"Fehler: {result['error']}")
    else:
        print(f"Purchase Price (geschaetzt): ${result['purchase_price']:,.0f}")
        print(f"Initial Equity: ${result['initial_equity']:,.0f}")
        print(f"Loan Amount: ${result['loan_amount']:,.0f}")
        print(f"Current NOI: ${result['current_noi']:,.0f}")
        print(f"Annual Debt Service: ${result['annual_debt_service']:,.0f}")
        print(f"\n--- 10-Jahres-Cashflows ---")
        for i, cf in enumerate(result['cash_flows'], 1):
            print(f"Jahr {i}: ${cf:,.0f}")
        print(f"\n--- Exit (Jahr 10) ---")
        print(f"Exit Value: ${result['exit_value']:,.0f}")
        print(f"Exit Proceeds: ${result['exit_proceeds']:,.0f}")
        print(f"\n--- RETURNS ---")
        print(f"IRR: {result['irr']*100:.2f}%" if result['irr'] else "IRR: N/A")
        print(f"Equity Multiple: {result['equity_multiple']:.2f}x")
        print(f"NPV: ${result['npv']:,.0f}")
# Sensitivitaetsanalyse
    sensitivity = calculate_sensitivity(test_data)
    print_sensitivity_table(sensitivity)