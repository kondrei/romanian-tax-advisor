# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from pathlib import Path

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.rag_engine import RomanianFiscalCodeRAG
from app.firestore_tools import get_tax_rates_catalog, save_tax_rate
from app.tax_calculator import calculate_tax_liability
from app.exchange_rate_tool import get_latest_exchange_rates
from app.image_generator_tool import generate_tax_infographic

PROJECT_ID = "qwiklabs-gcp-01-2576b95a29b1"
LOCATION = "us-east1"
MEMORY_BANK_ID = "3680573392538304512"

# Memory service configuration for deployment / app code
memory_service = VertexAiMemoryBankService(
    project=PROJECT_ID,
    location=LOCATION,
    agent_engine_id=MEMORY_BANK_ID,
)

# Load Agent Engine resource name from deployment_metadata.json if available
_metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
_agent_engine_resource_name = None
if _metadata_path.exists():
    try:
        with open(_metadata_path, "r", encoding="utf-8") as f:
            _meta = json.load(f)
            _agent_engine_resource_name = _meta.get("remote_agent_runtime_id")
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=_agent_engine_resource_name
)

# Build A2UI System Instruction (version 0.8)
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "Ești un Consultant Fiscal Expert în Legislația Fiscală a României (Legea nr. 227/2015 cu Normele Metodologice 2023).\n"
        "Obiectivul tău este să oferi consultanță fiscală exactă, profesională și bine fundamentată legal, bazată pe Codul Fiscal și pe catalogul de obligații/cote fiscale stocate în Firestore.\n\n"
        "Instrucțiuni de lucru:\n"
        "1. Pentru căutarea prevederilor legale din Codul Fiscal, folosește `search_fiscal_code` sau `lookup_fiscal_article`.\n"
        "2. Pentru interogarea catalogului oficial de cote fiscale și termene din Firestore, folosește `get_tax_rates_catalog`.\n"
        "3. Pentru salvarea sau adăugarea unei noi obligații/cote fiscale în catalogul Firestore, folosește `save_tax_rate`.\n"
        "4. Pentru simulări numerice și calcularea exactă a impozitului datorat pentru microîntreprinderi (1%/3%), SRL pe profit (16%) sau PFA, folosește `calculate_tax_liability`.\n"
        "5. Pentru obținerea cursului valutar în timp real (EUR/RON, USD/RON) necesar pentru verficarea plafoanelor fiscale (ex: 60.000 EUR microîntreprinderi), folosește `get_latest_exchange_rates`.\n"
        "6. Pentru generarea unei imagini/infografic fiscal vizual, folosește `generate_tax_infographic`.\n"
        "7. Ai la dispoziție un mediu de executare Python securizat (sandbox) pentru rularea calculelor financiare complexe.\n"
        "8. Răspunde clar și structurat în limba română (sau limba în care întreabă utilizatorul), citând articolele aplicabile.\n"
        "9. Folosește serviciul de memorie (Memory Bank) pentru a reține toate simulările și calculele fiscale ale utilizatorului și a le referenția în conversațiile viitoare."
    ),
    workflow_description="Analizează solicitarea utilizatorului și returnează un UI structurat A2UI (Card, Column, Row, Text) când este adecvat pentru afișarea clară a simulărilor și consultărilor fiscale.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

# Initialize lazy RAG instance
_rag_instance = None

def _get_rag():
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RomanianFiscalCodeRAG()
    return _rag_instance

def search_fiscal_code(query: str) -> str:
    """Caută în Codul Fiscal al României și în Normele Metodologice 2023 articole relevante pentru o întrebare fiscală.

    Args:
        query: Întrebarea sau cuvintele cheie căutate în limba română sau engleză (ex: 'cota impozit profit', 'microintreprinderi', 'scutiri TVA').

    Returns:
        Articolele și normele relevante extrase din Codul Fiscal al României.
    """
    rag = _get_rag()
    results = rag.search(query, top_k=4)
    if not results:
        return "Nu s-au găsit articole relevante în Codul Fiscal pentru această căutare."

    output = []
    for r in results:
        output.append(f"=== {r['header']} (Scor relevanță: {r['score']}) ===\n{r['content']}\n")
    return "\n---\n".join(output)

def lookup_fiscal_article(article_number: str) -> str:
    """Caută direct un articol specific din Codul Fiscal după număr.

    Args:
        article_number: Numărul articolului căutat (ex: '17', '42', '220', '291').

    Returns:
        Conținutul exact al articolului și normelor aferente.
    """
    rag = _get_rag()
    results = rag.get_article(article_number)
    if not results:
        return f"Articolul {article_number} nu a fost găsit în Codul Fiscal."

    output = []
    for r in results:
        output.append(f"=== {r['header']} ===\n{r['content']}\n")
    return "\n---\n".join(output)


root_agent = Agent(
    name="romanian_tax_advisor",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        search_fiscal_code,
        lookup_fiscal_article,
        get_tax_rates_catalog,
        save_tax_rate,
        calculate_tax_liability,
        get_latest_exchange_rates,
        generate_tax_infographic,
    ],
    code_executor=code_executor,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
