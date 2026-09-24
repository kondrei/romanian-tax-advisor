"""
Minimal tax liability calculation engine for Romanian business entities with automatic Memory Bank recording.
"""
from typing import Optional
from google.genai import types
from google.adk.tools import ToolContext
from google.adk.memory.memory_entry import MemoryEntry

def calculate_tax_liability(
    entity_type: str,
    annual_revenue_ron: float,
    annual_expenses_ron: float = 0.0,
    num_employees: int = 1,
    eur_rate: float = 4.97,
    tool_context: Optional[ToolContext] = None
) -> str:
    """Calculează estimativ impozitul și obligațiile fiscale pentru o firmă sau PFA din România și le salvează în memorie.

    Args:
        entity_type: Tipul entității juridice ('micro', 'srl_profit', 'pfa').
        annual_revenue_ron: Venitul anual brut realizat în RON.
        annual_expenses_ron: Cheltuielile anuale deductibile în RON (aplicabil pentru SRL Profit și PFA).
        num_employees: Numărul de angajați cu normă întreagă (relevant pentru microîntreprinderi). Default 1.
        eur_rate: Cursul de schimb EUR/RON utilizat pentru plafoane. Default 4.97.

    Returns:
        Un calcul detaliat al impozitului datorat, cota aplicată și venitul net estimat.
    """
    entity = entity_type.lower().strip()
    revenue_eur = annual_revenue_ron / eur_rate if eur_rate > 0 else annual_revenue_ron / 4.97

    result_str = ""
    summary_text = ""

    if entity in ["micro", "microintreprindere"]:
        if num_employees >= 1 and revenue_eur <= 60000:
            rate = 0.01
            rate_label = "1% (Micro <= 60.000 EUR, min. 1 angajat)"
        else:
            rate = 0.03
            rate_label = "3% (Micro > 60.000 EUR sau fără angajați)"

        tax_owed = annual_revenue_ron * rate
        net_profit = annual_revenue_ron - annual_expenses_ron - tax_owed

        result_str = (
            f"=== SIMULARE IMPOZIT MICROÎNTREPRINDERE ===\n"
            f"• Venit Anual: {annual_revenue_ron:,.2f} RON (~{revenue_eur:,.2f} EUR)\n"
            f"• Cheltuieli: {annual_expenses_ron:,.2f} RON\n"
            f"• Număr Angajați: {num_employees}\n"
            f"• Cota Aplicată: {rate_label}\n"
            f"• Impozit pe Venit Datorat: {tax_owed:,.2f} RON\n"
            f"• Venit Net Estimat: {net_profit:,.2f} RON"
        )
        summary_text = f"Calcul fiscal Microîntreprindere: Venit={annual_revenue_ron:,.2f} RON, Cheltuieli={annual_expenses_ron:,.2f} RON, Angajați={num_employees}, Impozit={tax_owed:,.2f} RON, Profit Net={net_profit:,.2f} RON."

    elif entity in ["srl_profit", "profit", "srl"]:
        taxable_profit = max(0.0, annual_revenue_ron - annual_expenses_ron)
        tax_owed = taxable_profit * 0.16
        net_profit = annual_revenue_ron - annual_expenses_ron - tax_owed

        result_str = (
            f"=== SIMULARE IMPOZIT PE PROFIT (SRL) ===\n"
            f"• Venit Anual: {annual_revenue_ron:,.2f} RON\n"
            f"• Cheltuieli Deductibile: {annual_expenses_ron:,.2f} RON\n"
            f"• Profit Impozabil: {taxable_profit:,.2f} RON\n"
            f"• Cota Impozit pe Profit: 16%\n"
            f"• Impozit pe Profit Datorat: {tax_owed:,.2f} RON\n"
            f"• Profit Net Estimat: {net_profit:,.2f} RON"
        )
        summary_text = f"Calcul fiscal SRL Profit 16%: Venit={annual_revenue_ron:,.2f} RON, Cheltuieli={annual_expenses_ron:,.2f} RON, Profit Impozabil={taxable_profit:,.2f} RON, Impozit={tax_owed:,.2f} RON, Profit Net={net_profit:,.2f} RON."

    elif entity in ["pfa"]:
        gross_profit = max(0.0, annual_revenue_ron - annual_expenses_ron)
        income_tax = gross_profit * 0.10
        net_profit = gross_profit - income_tax

        result_str = (
            f"=== SIMULARE PFA (Sistem Real) ===\n"
            f"• Venit Anual Brut: {annual_revenue_ron:,.2f} RON\n"
            f"• Cheltuieli Deductibile: {annual_expenses_ron:,.2f} RON\n"
            f"• Venit Impozabil Brut: {gross_profit:,.2f} RON\n"
            f"• Impozit pe Venit (10%): {income_tax:,.2f} RON\n"
            f"• Venit Net Estimat (înainte de contribuții sociale CAS/CASS): {net_profit:,.2f} RON"
        )
        summary_text = f"Calcul fiscal PFA Sistem Real 10%: Venit Brut={annual_revenue_ron:,.2f} RON, Cheltuieli={annual_expenses_ron:,.2f} RON, Impozit pe Venit={income_tax:,.2f} RON, Venit Net={net_profit:,.2f} RON."

    else:
        result_str = f"Tip de entitate necunoscut: '{entity_type}'. Folosiți 'micro', 'srl_profit' sau 'pfa'."

    # Record memory entry via tool_context if available
    if tool_context and summary_text:
        try:
            entry = MemoryEntry(
                content=types.Content(parts=[types.Part.from_text(text=summary_text)])
            )
            tool_context.add_memory(memories=[entry])
        except Exception:
            pass

    return result_str
