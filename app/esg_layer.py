"""ESG Layer - Energy Class, CRREM Stranding, Brown Discount, CapEx"""


# CRREM 1.5-Grad-Pfad fuer Office Buildings (kgCO2/m2/Jahr)
# Diese Werte sind aktuelle CRREM-Daten fuer Europa Office
CRREM_PATHWAY_OFFICE = {
    2026: 35.0,
    2028: 30.0,
    2030: 22.0,
    2032: 18.0,
    2035: 15.0,
    2040: 9.0,
    2045: 5.0,
    2050: 1.5
}

# Aktuelle Emissionen pro Energieklasse (kgCO2/m2/Jahr) - Schaetzwerte
EMISSIONS_PER_ENERGY_CLASS = {
    "A+": 8,
    "A": 12,
    "B": 18,
    "C": 25,
    "D": 35,
    "E": 50,
    "F": 70,
    "G": 95,
    "H": 130
}


def estimate_energy_class(building_specs):
    """
    Schaetzt Energieklasse basierend auf Baujahr, Heizung und Renovierung.
    Wird nur genutzt wenn Klasse nicht im PDF angegeben.
    """
    # Falls Klasse schon vorhanden, einfach zurueckgeben
    if building_specs.get("energy_certificate_class"):
        return building_specs["energy_certificate_class"]
    
    # Sonst schaetzen
    base_score = 100  # G-Klasse als Default
    
    year_built = building_specs.get("year_built")
    if year_built:
        if year_built > 2010:
            base_score -= 40
        elif year_built > 2000:
            base_score -= 25
        elif year_built > 1990:
            base_score -= 15
        elif year_built > 1980:
            base_score -= 5
    
    last_renovation = building_specs.get("last_renovation_year")
    if last_renovation:
        years_since = 2026 - last_renovation
        if years_since < 5:
            base_score -= 20
        elif years_since < 10:
            base_score -= 10
        elif years_since < 20:
            base_score -= 5
    
    heating = building_specs.get("heating_type", "other")
    if heating == "heat_pump":
        base_score -= 15
    elif heating == "district":
        base_score -= 10
    elif heating == "gas":
        base_score -= 0
    elif heating == "oil":
        base_score += 10
    
    # Mapping zu Klassen
    if base_score < 30:
        return "A+"
    elif base_score < 40:
        return "A"
    elif base_score < 55:
        return "B"
    elif base_score < 70:
        return "C"
    elif base_score < 85:
        return "D"
    elif base_score < 100:
        return "E"
    elif base_score < 115:
        return "F"
    elif base_score < 130:
        return "G"
    else:
        return "H"


def calculate_stranding_year(energy_class, current_year=2026):
    """
    Berechnet wann ein Gebaeude unter den 1.5-Grad-Pfad faellt (stranded wird).
    Returns: Jahr in dem das Gebaeude stranded wird, oder None wenn nicht
    """
    current_emissions = EMISSIONS_PER_ENERGY_CLASS.get(energy_class, 130)
    
    # Sortiere CRREM-Pfad nach Jahr
    sorted_pathway = sorted(CRREM_PATHWAY_OFFICE.items())
    
    for year, max_emissions in sorted_pathway:
        if year < current_year:
            continue
        if current_emissions > max_emissions:
            return year
    
    # Nicht stranded bis 2050
    return None


def calculate_brown_discount(stranding_year, current_year=2026):
    """
    Berechnet Brown Discount auf den Wert basierend auf Stranding Year.
    Je naeher das Stranding-Jahr, desto hoeher der Discount.
    """
    if stranding_year is None:
        return 0.0
    
    years_until_stranded = stranding_year - current_year
    
    if years_until_stranded <= 2:
        return 0.25  # 25% Discount - bald stranded
    elif years_until_stranded <= 5:
        return 0.20  # 20% Discount
    elif years_until_stranded <= 10:
        return 0.10  # 10% Discount
    elif years_until_stranded <= 15:
        return 0.05  # 5% Discount
    else:
        return 0.0


def estimate_renovation_capex(property_data, current_class, target_class="C"):
    """
    Schaetzt CapEx in USD um Gebaeude von current_class auf target_class zu bringen.
    Werte basieren auf typischen Sanierungskosten.
    """
    sqm = property_data["property_info"].get("total_sqm", 0)
    if sqm == 0:
        return 0
    
    # Cost per sqm (USD) basierend auf Klassensprung
    # Annahme: Wir wollen mindestens auf Klasse C kommen
    cost_per_sqm_table = {
        "H": 950,  # H -> C: massive Sanierung
        "G": 800,
        "F": 650,
        "E": 500,
        "D": 350,
        "C": 0,    # schon Ziel erreicht
        "B": 0,
        "A": 0,
        "A+": 0
    }
    
    cost_per_sqm = cost_per_sqm_table.get(current_class, 500)
    return sqm * cost_per_sqm


def estimate_value_uplift_after_renovation(property_data, brown_discount):
    """
    Schaetzt Wertsteigerung nach Sanierung.
    
    Annahmen basieren auf:
    - JLL "Decarbonising Real Estate" Report 2024: 6-12% Green Premium fuer Office
    - CBRE Research: 5-15% Capital Value Premium fuer ESG-konforme Gebaeude
    - Eichholtz/Kok/Quigley (2010): Klassische empirische Basis
    
    Wir nutzen 7% als konservative Mittelwert-Annahme.
    Plus: Wegfall des Brown Discount nach Sanierung.
    """
    purchase_price = property_data["financials"].get("purchase_price")
    if purchase_price is None:
        # Fallback: Schaetzen ueber NOI
        gross_income = property_data["financials"].get("gross_rental_income", 0)
        op_ex = property_data["financials"].get("operating_expenses", 0)
        noi = gross_income - op_ex
        purchase_price = noi / 0.07 if noi > 0 else 0
    
    # Brown Discount weg + Green Premium
    GREEN_PREMIUM = 0.07  # JLL/CBRE Industry Standard
    total_uplift_pct = brown_discount + GREEN_PREMIUM
    
    return purchase_price * total_uplift_pct


def analyze_esg(property_data):
    """
    Komplette ESG-Analyse: Energy Class, Stranding, Brown Discount, CapEx, Uplift
    """
    building_specs = property_data.get("building_specs", {})
    
    # 1. Energy Class
    energy_class = estimate_energy_class(building_specs)
    energy_class_estimated = building_specs.get("energy_certificate_class") is None
    
    # 2. Stranding Year
    stranding_year = calculate_stranding_year(energy_class)
    
    # 3. Brown Discount
    brown_discount = calculate_brown_discount(stranding_year)
    
    # 4. Renovation CapEx
    capex = estimate_renovation_capex(property_data, energy_class, target_class="C")
    
    # 5. Value Uplift nach Sanierung
    value_uplift = estimate_value_uplift_after_renovation(property_data, brown_discount)
    
    # 6. Net Benefit (Uplift - CapEx)
    net_benefit = value_uplift - capex
    
    # 7. Recommendation
    if net_benefit > 0:
        recommendation = "RENOVATE - Sanierung wirtschaftlich"
    elif brown_discount > 0.15:
        recommendation = "EXIT - Stranding-Risiko zu hoch, Verkauf empfohlen"
    else:
        recommendation = "HOLD - Aktuell akzeptabel, Sanierung nicht erforderlich"
    
    return {
        "energy_class": energy_class,
        "energy_class_was_estimated": energy_class_estimated,
        "current_emissions_kgco2_per_sqm": EMISSIONS_PER_ENERGY_CLASS.get(energy_class, 130),
        "stranding_year": stranding_year,
        "brown_discount_pct": round(brown_discount * 100, 1),
        "renovation_capex_usd": round(capex, 0),
        "value_uplift_after_renovation_usd": round(value_uplift, 0),
        "net_benefit_usd": round(net_benefit, 0),
        "recommendation": recommendation
    }


if __name__ == "__main__":
    # Test mit den Detroit-Daten
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
        "building_specs": {
            "energy_certificate_class": None,
            "heating_type": "other",
            "last_renovation_year": 1964
        }
    }
    
    result = analyze_esg(test_data)
    
    print("=== ESG ANALYSE ===")
    print(f"Energy Class: {result['energy_class']}", end="")
    if result['energy_class_was_estimated']:
        print(" (geschaetzt)")
    else:
        print(" (aus PDF)")
    
    print(f"Aktuelle Emissionen: {result['current_emissions_kgco2_per_sqm']} kgCO2/m2/Jahr")
    print(f"Stranding Year: {result['stranding_year']}")
    print(f"Brown Discount: {result['brown_discount_pct']}%")
    print(f"\n--- SANIERUNG ---")
    print(f"Renovation CapEx: ${result['renovation_capex_usd']:,.0f}")
    print(f"Value Uplift: ${result['value_uplift_after_renovation_usd']:,.0f}")
    print(f"Net Benefit: ${result['net_benefit_usd']:,.0f}")
    print(f"\n--- EMPFEHLUNG ---")
    print(f"{result['recommendation']}")