"""
Firestore tools for managing the tax_rates_catalog collection.
Project ID is hardcoded as a string per user requirements and deployment rules.
"""
from typing import Optional
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

PROJECT_ID = "qwiklabs-gcp-01-2576b95a29b1"
COLLECTION_NAME = "tax_rates_catalog"

_db_instance = None

def get_firestore_client() -> firestore.Client:
    global _db_instance
    if _db_instance is None:
        _db_instance = firestore.Client(project=PROJECT_ID)
    return _db_instance

def get_tax_rates_catalog(category: Optional[str] = None) -> str:
    """Obține lista cotelor și obligațiilor fiscale din catalogul Firestore.

    Args:
        category: Categoria opțională a taxelor căutate ('profit', 'micro', 'vat', 'payroll', 'dividends'). Dacă este omisă, returnează toate taxele.

    Returns:
        Lista taxelor și cotelor din baza de date Firestore.
    """
    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)

    if category:
        query = collection_ref.where(filter=FieldFilter("category", "==", category.lower().strip()))
        docs = list(query.stream())
    else:
        docs = list(collection_ref.stream())

    if not docs:
        return f"Nu s-au găsit taxe în catalogul Firestore pentru categoria '{category}'." if category else "Catalogul de taxe Firestore este gol."

    results = []
    for doc in docs:
        data = doc.to_dict()
        results.append(
            f"• ID: {doc.id}\n"
            f"  Denumire: {data.get('tax_name', 'N/A')}\n"
            f"  Cotă: {data.get('rate_display', 'N/A')}\n"
            f"  Bază legală: {data.get('legal_basis', 'N/A')}\n"
            f"  Aplicabilitate: {data.get('applicability', 'N/A')}\n"
            f"  Termen plată: {data.get('due_date', 'N/A')}"
        )

    return "\n\n".join(results)

def save_tax_rate(
    rate_id: str,
    tax_name: str,
    rate_display: str,
    category: str,
    legal_basis: str,
    applicability: str,
    due_date: str
) -> str:
    """Salvează sau actualizează o cotă/obligație fiscală în catalogul Firestore.

    Args:
        rate_id: Identificatorul unic al taxei (ex: 'micro_tax_new', 'pfa_cass_2024').
        tax_name: Numele complet al taxei/impozitului.
        rate_display: Cota de impozitare afișată (ex: '10%', '16%', '25%').
        category: Categoria taxei ('profit', 'micro', 'vat', 'payroll', 'dividends', 'other').
        legal_basis: Temeiul legal (ex: 'Art. 64 din Codul Fiscal').
        applicability: Descrierea aplicabilității.
        due_date: Termenul de declarare/plată.

    Returns:
        Mesaj de confirmare a salvării în Firestore.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(rate_id.strip())

    data = {
        "id": rate_id.strip(),
        "tax_name": tax_name.strip(),
        "rate_display": rate_display.strip(),
        "category": category.lower().strip(),
        "legal_basis": legal_basis.strip(),
        "applicability": applicability.strip(),
        "due_date": due_date.strip()
    }

    doc_ref.set(data, merge=True)
    return f"✅ Taxa '{tax_name}' (ID: {rate_id}) a fost salvată cu succes în baza de date Firestore!"
