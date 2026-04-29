import os
import json
from anthropic import Anthropic
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Du bist ein Experte fuer Real Estate Underwriting.
Extrahiere aus dem PDF folgende Daten als JSON:

{
  "property_info": {
    "address": "string",
    "year_built": int,
    "property_type": "office|retail|residential|industrial|mixed",
    "total_sqm": float,
    "occupancy_rate": float
  },
  "financials": {
    "current_noi": float,
    "operating_expenses": float,
    "gross_rental_income": float,
    "rent_per_sqm": float,
    "purchase_price": float
  },
  "lease_info": {
    "weighted_average_lease_term": float,
    "tenant_count": int,
    "main_tenant_concentration": float
  },
  "building_specs": {
    "energy_certificate_class": "A|B|C|D|E|F|G|H",
    "heating_type": "gas|oil|district|heat_pump|other",
    "last_renovation_year": int
  }
}

Wenn ein Feld nicht im PDF steht, gib null zurueck. Keine Annahmen.
Wenn US-Werte (sqft, USD) angegeben sind, konvertiere zu metrisch (sqm, EUR mit Kurs 0.92).
Antworte NUR mit dem JSON, kein zusaetzlicher Text."""


def extract_text_from_pdf(pdf_path):
    """Liest Text aus PDF und gibt String zurueck."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_property_data(pdf_path):
    """Extrahiert strukturierte Property-Daten aus PDF mit Claude."""
    print(f"Lese PDF: {pdf_path}")
    pdf_text = extract_text_from_pdf(pdf_path)
    print(f"PDF-Laenge: {len(pdf_text)} Zeichen")
    
    print("Sende an Claude API...")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"PDF-Inhalt:\n\n{pdf_text}"}
        ]
    )
    
    response_text = message.content[0].text
    print("Claude Response erhalten.")

    # Markdown code blocks entfernen falls vorhanden
    if response_text.startswith("```"):
        # Erste Zeile (```json) und letzte Zeile (```) entfernen
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    # JSON parsen
    try:
        data = json.loads(response_text)
        return data
    except json.JSONDecodeError as e:
        print(f"JSON-Parse-Error: {e}")
        print(f"Raw Response: {response_text}")
        return None


if __name__ == "__main__":
    test_pdf = "test_data/sample_property.pdf"
    result = extract_property_data(test_pdf)
    
    if result:
        print("\n=== EXTRAHIERTE DATEN ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\nExtraktion fehlgeschlagen.")