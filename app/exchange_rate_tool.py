"""
Tool for fetching live financial exchange rates from a free public API.
Supports optional API key from environment variable EXCHANGE_RATE_API_KEY if configured.
"""
import os
import requests

def get_latest_exchange_rates(base_currency: str = "EUR") -> str:
    """Obține cursul de schimb valutar în timp real pentru RON și alte monede de referință.

    Args:
        base_currency: Moneda de bază (ex: 'EUR', 'USD', 'GBP'). Default este 'EUR'.

    Returns:
        Cotațiile valutare oficiale actualizate și conversia pentru RON.
    """
    base = base_currency.strip().upper()
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")

    if api_key:
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}"
    else:
        url = f"https://open.er-api.com/v6/latest/{base}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("result") != "success":
            return f"Eroare la preluarea cursului valutar pentru {base}."

        rates = data.get("rates", {})
        ron_rate = rates.get("RON", "N/A")
        usd_rate = rates.get("USD", "N/A")
        gbp_rate = rates.get("GBP", "N/A")
        chf_rate = rates.get("CHF", "N/A")
        last_update = data.get("time_last_update_utc", "N/A")

        return (
            f"=== CURS VALUTAR ÎN TIMP REAL (Bază: {base}) ===\n"
            f"• Data actualizării: {last_update}\n"
            f"• 1 {base} = {ron_rate} RON\n"
            f"• 1 {base} = {usd_rate} USD\n"
            f"• 1 {base} = {gbp_rate} GBP\n"
            f"• 1 {base} = {chf_rate} CHF\n\n"
            f"💡 Relevanță fiscală: Plafonul de 60.000 EUR pentru microîntreprinderi (Art. 51 Cod Fiscal) "
            f"echivalează cu ~{60000 * ron_rate:,.2f} RON la cursul actual."
            if isinstance(ron_rate, (int, float)) else f"1 {base} = {ron_rate} RON"
        )

    except Exception as e:
        return f"A apărut o eroare la conectarea la API-ul de curs valutar: {str(e)}"
