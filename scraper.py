import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import re

RUTA_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'historial_loto.csv')

MESES_ES = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}

def normalizar_fecha(texto):
    """Convierte 'Miércoles 18 de Febrero 2026' a '2026-02-18'."""
    if not texto:
        return None
    txt = texto.lower().strip()
    m = re.search(r'(\d{1,2})\s+de\s+([a-záéíóú]+)(?:\s+de)?\s+(\d{4})', txt)
    if m:
        dia, mes_nombre, anio = m.group(1), m.group(2), m.group(3)
        mes = MESES_ES.get(mes_nombre)
        if mes:
            return f"{anio}-{mes}-{dia.zfill(2)}"
    m2 = re.search(r'(\d{4})-(\d{2})-(\d{2})', txt)
    if m2:
        return m2.group(0)
    return None

def extraer_historial_web():
    """Escanea conectate.com.do y extrae sorteos del Loto Leidsa con fechas normalizadas."""
    url = "https://www.conectate.com.do/loterias/leidsa"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    respuesta = requests.get(url, headers=headers, timeout=15)
    if respuesta.status_code != 200:
        raise Exception(f"Error de conexión: Código {respuesta.status_code}")

    soup = BeautifulSoup(respuesta.text, 'html.parser')
    bloques = soup.find_all('div', class_='game-block')

    historial = []
    for bloque in bloques:
        texto = bloque.text.lower()
        if 'loto' not in texto or 'pool' in texto or 'pega' in texto:
            continue
        if 'loto leidsa' not in texto and 'loto más' not in texto and 'loto mas' not in texto:
            continue

        # Fecha (normalizada a ISO)
        texto_crudo = bloque.text
        fecha_norm = None
        m = re.search(
            r'(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)[^\d]*?(\d{1,2}\s+de\s+[a-záéíóú]+\s+(?:de\s+)?\d{4})',
            texto_crudo, re.IGNORECASE
        )
        if m:
            fecha_norm = normalizar_fecha(m.group(2))
        if not fecha_norm:
            div_fecha = bloque.find('div', class_='session-date')
            if div_fecha:
                fecha_norm = normalizar_fecha(div_fecha.text.strip())

        if not fecha_norm:
            continue

        # Bolas
        bolas_html = bloque.find_all(['span', 'div'], class_=['score', 'ball', 'numero'])
        if not bolas_html:
            bolas_html = bloque.find_all('span')

        numeros = [int(b.text.strip()) for b in bolas_html if b.text.strip().isdigit()]

        if len(numeros) >= 6:
            bolas_base = numeros[0:6]
            loto_mas = numeros[6] if len(numeros) > 6 else 0
            super_mas = numeros[7] if len(numeros) > 7 else 0
            historial.append([fecha_norm] + bolas_base + [loto_mas, super_mas])

    if not historial:
        raise Exception("No se encontraron sorteos del Loto en la página.")
    return historial

def actualizar_csv():
    """Combina sorteos nuevos con el CSV sin duplicar."""
    try:
        resultados = extraer_historial_web()
        columnas = ["Fecha", "Bola_1", "Bola_2", "Bola_3", "Bola_4", "Bola_5", "Bola_6", "Loto_Mas", "Super_Mas"]
        df_nuevos = pd.DataFrame(resultados, columns=columnas)

        os.makedirs(os.path.dirname(RUTA_CSV), exist_ok=True)

        if os.path.exists(RUTA_CSV):
            df_hist = pd.read_csv(RUTA_CSV)
            df_hist['Fecha'] = df_hist['Fecha'].astype(str)
            df_filtrado = df_nuevos[~df_nuevos['Fecha'].isin(df_hist['Fecha'])]
            if not df_filtrado.empty:
                df_final = pd.concat([df_filtrado, df_hist], ignore_index=True)
                df_final = df_final.drop_duplicates(subset=['Fecha']).sort_values(by='Fecha', ascending=False)
                df_final.to_csv(RUTA_CSV, index=False)
                return True, f"¡Éxito! {len(df_filtrado)} sorteos nuevos agregados."
            return True, "Todo al día. Sin sorteos nuevos."
        else:
            df_nuevos = df_nuevos.sort_values(by='Fecha', ascending=False)
            df_nuevos.to_csv(RUTA_CSV, index=False)
            return True, f"Archivo creado con {len(df_nuevos)} sorteos."
    except Exception as e:
        return False, f"Error al extraer: {e}"

def cargar_datos():
    """Carga el CSV histórico, asegurando que Fecha sea string ISO."""
    if not os.path.exists(RUTA_CSV):
        return pd.DataFrame()
    df = pd.read_csv(RUTA_CSV)
    if 'Fecha' in df.columns:
        df['Fecha'] = df['Fecha'].astype(str).str.strip()
    for col in ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df.sort_values(by='Fecha', ascending=False).reset_index(drop=True)