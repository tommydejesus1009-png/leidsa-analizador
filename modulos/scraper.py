import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime, timedelta

RUTA_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'historial_loto.csv')

URL_YELU = "https://www.yelu.do/leidsa/results/loto-mas"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

MESES_ES = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}


def ajustar_a_dia_sorteo(fecha_iso):
    """Yelu publica con la fecha del DÍA SIGUIENTE al sorteo.
    El Loto solo sortea miércoles y sábado: retrocedemos al más cercano."""
    f = datetime.strptime(fecha_iso, '%Y-%m-%d')
    while f.weekday() not in (2, 5):  # 2=miércoles, 5=sábado
        f -= timedelta(days=1)
    return f.strftime('%Y-%m-%d')


def extraer_de_yelu():
    r = requests.get(URL_YELU, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code} en yelu.do")

    soup = BeautifulSoup(r.text, 'html.parser')
    texto = soup.get_text(separator='\n')

    # "DD de Mes YYYY" + texto sin dígitos (- Jueves / Loto Más...) + 8 números
    patron = re.compile(
        r'(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+(\d{4})[^\d]{0,80}?'
        r'(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+'
        r'(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})',
        re.IGNORECASE
    )

    historial = []
    fechas_vistas = set()

    for m in patron.finditer(texto):
        dia, mes_nombre, anio = m.group(1), m.group(2).lower(), m.group(3)
        mes = MESES_ES.get(mes_nombre)
        if not mes:
            continue
        fecha_pub = f"{anio}-{mes}-{dia.zfill(2)}"
        fecha_iso = ajustar_a_dia_sorteo(fecha_pub)
        if fecha_iso in fechas_vistas:
            continue

        bolas = [int(m.group(i)) for i in range(4, 12)]
        if not all(1 <= b <= 40 for b in bolas[:6]):
            continue
        if not (1 <= bolas[6] <= 12):
            continue
        if not (1 <= bolas[7] <= 15):
            continue
        if len(set(bolas[:6])) != 6:
            continue

        fechas_vistas.add(fecha_iso)
        historial.append([fecha_iso] + bolas)

    if not historial:
        raise Exception("yelu.do: sin coincidencias (¿cambió el formato?)")
    return historial


def actualizar_csv():
    try:
        resultados = extraer_de_yelu()
        columnas = ["Fecha", "Bola_1", "Bola_2", "Bola_3", "Bola_4",
                    "Bola_5", "Bola_6", "Loto_Mas", "Super_Mas"]
        df_nuevos = pd.DataFrame(resultados, columns=columnas)
        df_nuevos['Fecha'] = df_nuevos['Fecha'].astype(str)

        os.makedirs(os.path.dirname(RUTA_CSV), exist_ok=True)

        if os.path.exists(RUTA_CSV):
            df_hist = pd.read_csv(RUTA_CSV)
            df_hist['Fecha'] = df_hist['Fecha'].astype(str)
            df_filtrado = df_nuevos[~df_nuevos['Fecha'].isin(df_hist['Fecha'])]
            if not df_filtrado.empty:
                df_final = pd.concat([df_filtrado, df_hist], ignore_index=True)
                df_final = df_final.drop_duplicates(subset=['Fecha']).sort_values(by='Fecha', ascending=False)
                df_final.to_csv(RUTA_CSV, index=False)
                fechas = ", ".join(df_filtrado['Fecha'].head(5).tolist())
                extra = f" (+{len(df_filtrado)-5} más)" if len(df_filtrado) > 5 else ""
                return True, f"✅ {len(df_filtrado)} sorteos nuevos: {fechas}{extra}"
            return True, f"Todo al día ({len(df_nuevos)} en web, ya estaban)."
        else:
            df_nuevos = df_nuevos.sort_values(by='Fecha', ascending=False)
            df_nuevos.to_csv(RUTA_CSV, index=False)
            return True, f"Archivo creado con {len(df_nuevos)} sorteos."
    except Exception as e:
        return False, f"Error al extraer: {e}"


def cargar_datos():
    if not os.path.exists(RUTA_CSV):
        return pd.DataFrame()
    df = pd.read_csv(RUTA_CSV)
    if 'Fecha' in df.columns:
        df['Fecha'] = df['Fecha'].astype(str).str.strip()
    for col in ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df.sort_values(by='Fecha', ascending=False).reset_index(drop=True)