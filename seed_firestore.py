#!/usr/bin/env python3
"""
Seed script for populating the Firestore tax_rates_catalog collection.
Project ID is explicitly hardcoded as a string per deployment guidelines.
"""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-01-2576b95a29b1"

SEED_TAX_RATES = [
    {
        "id": "profit_tax_standard",
        "tax_name": "Impozit pe profit - Cota Standard",
        "rate_percent": 16.0,
        "rate_display": "16%",
        "category": "profit",
        "legal_basis": "Art. 17 din Codul Fiscal (Legea 227/2015)",
        "applicability": "Se aplică asupra profitului impozabil pentru societățile plătitoare de impozit pe profit.",
        "due_date": "25 iunie a anului următor"
    },
    {
        "id": "micro_tax_low",
        "tax_name": "Impozit venit microîntreprinderi (venituri <= 60.000 EUR)",
        "rate_percent": 1.0,
        "rate_display": "1%",
        "category": "micro",
        "legal_basis": "Art. 51 din Codul Fiscal",
        "applicability": "Se aplică asupra veniturilor totale realizate de microîntreprinderi cu cel puțin 1 angajat și venituri sub 60.000 EUR.",
        "due_date": "Trimestrial, până la data de 25 a lunii următoare trimestrului"
    },
    {
        "id": "micro_tax_high",
        "tax_name": "Impozit venit microîntreprinderi (venituri > 60.000 EUR)",
        "rate_percent": 3.0,
        "rate_display": "3%",
        "category": "micro",
        "legal_basis": "Art. 51 din Codul Fiscal",
        "applicability": "Se aplică asupra veniturilor totale realizate de microîntreprinderi care depășesc 60.000 EUR sau desfășoară anumite activități specifice.",
        "due_date": "Trimestrial, până la data de 25 a lunii următoare trimestrului"
    },
    {
        "id": "vat_standard",
        "tax_name": "Taxa pe Valoarea Adăugată (TVA) - Cota Standard",
        "rate_percent": 19.0,
        "rate_display": "19%",
        "category": "vat",
        "legal_basis": "Art. 291 alin. (1) din Codul Fiscal",
        "applicability": "Cota generală de TVA aplicabilă livrărilor de bunuri și prestărilor de servicii.",
        "due_date": "Lunar / Trimestrial (Formular 300)"
    },
    {
        "id": "cam_payroll",
        "tax_name": "Contribuția Asiguratorie pentru Muncă (CAM)",
        "rate_percent": 2.25,
        "rate_display": "2.25%",
        "category": "payroll",
        "legal_basis": "Art. 220^3 din Codul Fiscal",
        "applicability": "Datorată de angajator asupra fondului brut de salarii.",
        "due_date": "Lunar, până la data de 25 a lunii următoare (Formular 112)"
    }
]

def seed_database():
    print(f"Connecting to Firestore with hardcoded project ID: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("tax_rates_catalog")

    for item in SEED_TAX_RATES:
        doc_id = item["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(item)
        print(f"  [+] Seeded tax rate: {doc_id} -> {item['tax_name']} ({item['rate_display']})")

    print("✅ Firestore seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
