import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import re

RUTA_CSV_KINO = os.path.join(os.path.dirname(__file__), '..', 'data', 'historial_kino.csv')

URL_YELU_KINO = "https://www.yelu.do/leidsa/results/super-kino-tv"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

MESES_ES = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}

COLS_KINO = ["Fecha"] + [f"B{i}" for i in range(1, 21)]


def extraer_de_yelu_kino():
    r = requests.get(URL_YELU_KINO, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code} en yelu.do")

    soup = BeautifulSoup(r.text, 'html.parser')
    texto = soup.get_text(separator='\n')

    # Fecha "DD de Mes YYYY" seguida (pocas líneas después) de 20 números
    patron = re.compile(
        r'(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+(\d{4})[^\n]*\n'
        r'(?:[^\n]*\n){0,3}?'
        r'\s*((?:\d{1,2}[\s\n]+){19}\d{1,2})',
        re.IGNORECASE
    )

    historial = []
    fechas_vistas = set()

    for m in patron.finditer(texto):
        dia, mes_nombre, anio = m.group(1), m.group(2).lower(), m.group(3)
        mes = MESES_ES.get(mes_nombre)
        if not mes:
            continue
        fecha_iso = f"{anio}-{mes}-{dia.zfill(2)}"
        if fecha_iso in fechas_vistas:
            continue

        nums = [int(x) for x in re.findall(r'\d{1,2}', m.group(4))][:20]
        if len(nums) != 20:
            continue
        if not all(1 <= n <= 80 for n in nums):
            continue
        if len(set(nums)) != 20:
            continue

        fechas_vistas.add(fecha_iso)
        historial.append([fecha_iso] + sorted(nums))

    if not historial:
        raise Exception("yelu.do: sin coincidencias de Kino")
    return historial


def actualizar_csv_kino():
    try:
        resultados = extraer_de_yelu_kino()
        df_nuevos = pd.DataFrame(resultados, columns=COLS_KINO)
        df_nuevos['Fecha'] = df_nuevos['Fecha'].astype(str)

        os.makedirs(os.path.dirname(RUTA_CSV_KINO), exist_ok=True)

        if os.path.exists(RUTA_CSV_KINO):
            df_hist = pd.read_csv(RUTA_CSV_KINO)
            df_hist['Fecha'] = df_hist['Fecha'].astype(str)
            df_filtrado = df_nuevos[~df_nuevos['Fecha'].isin(df_hist['Fecha'])]
            if not df_filtrado.empty:
                df_final = pd.concat([df_filtrado, df_hist], ignore_index=True)
                df_final = df_final.drop_duplicates(subset=['Fecha']).sort_values(by='Fecha', ascending=False)
                df_final.to_csv(RUTA_CSV_KINO, index=False)
                return True, f"✅ {len(df_filtrado)} sorteos Kino nuevos."
            return True, f"Kino al día ({len(df_nuevos)} en web, ya estaban)."
        else:
            df_nuevos = df_nuevos.sort_values(by='Fecha', ascending=False)
            df_nuevos.to_csv(RUTA_CSV_KINO, index=False)
            return True, f"Archivo Kino creado con {len(df_nuevos)} sorteos."
    except Exception as e:
        return False, f"Error al extraer Kino: {e}"


def cargar_datos_kino():
    if not os.path.exists(RUTA_CSV_KINO):
        return pd.DataFrame()
    df = pd.read_csv(RUTA_CSV_KINO)
    df['Fecha'] = df['Fecha'].astype(str).str.strip()
    for col in [f"B{i}" for i in range(1, 21)]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df.sort_values(by='Fecha', ascending=False).reset_index(drop=True)