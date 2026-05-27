import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
import time
from datetime import datetime

RUTA_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'historial_loto.csv')

def limpiar_fecha(fecha_texto):
    meses = {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
             'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
             'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'}
    match = re.search(r'(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(?:de\s+)?(\d{4})', fecha_texto.lower())
    if match:
        return f"{match.group(3)}-{meses.get(match.group(2), '01')}-{match.group(1).zfill(2)}"
    return None

def generar_lista_meses():
    """Meses desde Marzo 2024 (Era Moderna 40 bolos) hasta hoy."""
    hoy = datetime.now()
    meses = []
    for anio in range(2024, hoy.year + 1):
        for mes in range(1, 13):
            if anio == 2024 and mes < 3:
                continue
            if anio == hoy.year and mes > hoy.month:
                break
            meses.append(f"{anio}-{mes:02d}")
    return sorted(meses, reverse=True)

def encender_tractor_payload():
    print("🚜 Encendiendo Tractor (Era Moderna: Marzo 2024+)...")
    url_base = "https://www.yelu.do/leidsa/results/history"
    headers = {'User-Agent': 'Mozilla/5.0'}

    meses = generar_lista_meses()
    historial = []

    for mes in meses:
        print(f"📡 Inyectando: {mes}...")
        payload = {'_method': 'POST', 'data[Lottery][name]': 'Loto Más', 'data[Lottery][date]': mes}
        try:
            r = requests.post(url_base, data=payload, headers=headers, timeout=15)
            if r.status_code != 200:
                continue
        except Exception as e:
            print(f"  ❌ {e}")
            continue

        soup = BeautifulSoup(r.text, 'html.parser')
        for fila in soup.find_all('tr'):
            cols = fila.find_all('td')
            if len(cols) >= 3:
                texto = cols[1].text.lower()
                if 'loto' in texto and 'pool' not in texto:
                    fecha = limpiar_fecha(cols[0].text.strip())
                    bruto = cols[2].get_text(separator=" ").strip()
                    bolas = [int(n) for n in bruto.split() if n.isdigit()]
                    if fecha and len(bolas) >= 6:
                        historial.append([fecha] + bolas[0:6] +
                                         [bolas[6] if len(bolas) > 6 else 0,
                                          bolas[7] if len(bolas) > 7 else 0])
        time.sleep(1)
    return historial

def vaciar_en_caja_negra():
    datos = encender_tractor_payload()
    if not datos:
        print("❌ La página no devolvió datos legibles.")
        return
    cols = ["Fecha", "Bola_1", "Bola_2", "Bola_3", "Bola_4", "Bola_5", "Bola_6", "Loto_Mas", "Super_Mas"]
    df = pd.DataFrame(datos, columns=cols)
    df = df.drop_duplicates(subset=['Fecha']).sort_values(by='Fecha', ascending=False).reset_index(drop=True)
    os.makedirs(os.path.dirname(RUTA_CSV), exist_ok=True)
    df.to_csv(RUTA_CSV, index=False)
    print("=" * 60)
    print(f"✅ ¡CORONAMOS! {len(df)} sorteos inyectados a la Caja Negra.")
    print("=" * 60)

if __name__ == "__main__":
    vaciar_en_caja_negra()