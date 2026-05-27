import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime, timedelta

RUTA_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'historial_loto.csv')

URL_LOTO_MAS = "https://www.conectate.com.do/loterias/leidsa/loto-mas"
URL_PORTADA = "https://www.conectate.com.do/loterias/leidsa"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

MESES_ES = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}


def inferir_anio(dia, mes, hoy=None):
    """Si el (dia-mes) sería futuro con el año actual, asume año anterior."""
    if hoy is None:
        hoy = datetime.now()
    try:
        candidato = datetime(hoy.year, int(mes), int(dia))
    except ValueError:
        return None
    # Tolerancia de 2 días para que sorteos de hoy/ayer no se cuenten como año pasado
    if candidato > hoy + timedelta(days=2):
        candidato = datetime(hoy.year - 1, int(mes), int(dia))
    return candidato.strftime('%Y-%m-%d')


def normalizar_fecha_texto(texto):
    """Convierte 'Miércoles 18 de Febrero 2026' o '2026-02-18' a ISO."""
    if not texto:
        return None
    txt = str(texto).lower().strip()

    # Formato ISO ya válido
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', txt)
    if m:
        return m.group(0)

    # "18 de febrero 2026" o "18 de febrero de 2026"
    m = re.search(r'(\d{1,2})\s+de\s+([a-záéíóú]+)(?:\s+de)?\s+(\d{4})', txt)
    if m:
        dia, mes_nombre, anio = m.group(1), m.group(2), m.group(3)
        mes = MESES_ES.get(mes_nombre)
        if mes:
            return f"{anio}-{mes}-{dia.zfill(2)}"

    return None


def extraer_de_loto_mas():
    """Scraper de la página dedicada de Loto Más. Patrón: 'DD-MM\\n## ## ## ## ## ## ## ##'."""
    r = requests.get(URL_LOTO_MAS, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code} en página Loto Más")

    soup = BeautifulSoup(r.text, 'html.parser')
    texto = soup.get_text(separator='\n')

    # Patrón: fecha DD-MM seguida (con espacios/saltos) por 8 números de 2 dígitos
    patron = re.compile(
        r'(\d{1,2})-(\d{1,2})\s*\n+\s*'
        r'(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})'
    )

    historial = []
    fechas_vistas = set()
    hoy = datetime.now()

    for m in patron.finditer(texto):
        dia, mes = m.group(1), m.group(2)
        fecha_iso = inferir_anio(dia, mes, hoy)
        if not fecha_iso or fecha_iso in fechas_vistas:
            continue

        bolas = [int(m.group(i)) for i in range(3, 11)]
        # Validación: las 6 primeras entre 1-40, loto_mas 1-12, super_mas 1-15
        if not all(1 <= b <= 40 for b in bolas[:6]):
            continue
        if not (1 <= bolas[6] <= 12):
            continue
        if not (1 <= bolas[7] <= 15):
            continue
        # No duplicados internos en las 6 bolas
        if len(set(bolas[:6])) != 6:
            continue

        fechas_vistas.add(fecha_iso)
        historial.append([fecha_iso] + bolas)

    return historial


def extraer_de_portada():
    """Fallback: portada de leidsa, busca línea de Loto Más."""
    r = requests.get(URL_PORTADA, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code} en portada")

    soup = BeautifulSoup(r.text, 'html.parser')
    texto = soup.get_text(separator='\n')

    historial = []
    hoy = datetime.now()

    # En la portada: "16-05\n[Loto - Loto Más]...\n03 14 18 20 29 32 09 12"
    patron = re.compile(
        r'(\d{1,2})-(\d{1,2})[^\n]*\n[^\n]*?[Ll]oto[^\n]*?[Mm][áa]s[^\n]*\n'
        r'(?:[^\n]*\n)?'  # línea opcional intermedia
        r'(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})',
        re.IGNORECASE
    )

    for m in patron.finditer(texto):
        dia, mes = m.group(1), m.group(2)
        fecha_iso = inferir_anio(dia, mes, hoy)
        if not fecha_iso:
            continue
        bolas = [int(m.group(i)) for i in range(3, 11)]
        if not all(1 <= b <= 40 for b in bolas[:6]):
            continue
        if len(set(bolas[:6])) != 6:
            continue
        historial.append([fecha_iso] + bolas)

    return historial


def extraer_historial_web():
    """Intenta primero la página dedicada, luego la portada como fallback."""
    errores = []
    try:
        datos = extraer_de_loto_mas()
        if datos:
            return datos
        errores.append("Loto Más: sin coincidencias")
    except Exception as e:
        errores.append(f"Loto Más: {e}")

    try:
        datos = extraer_de_portada()
        if datos:
            return datos
        errores.append("Portada: sin coincidencias")
    except Exception as e:
        errores.append(f"Portada: {e}")

    raise Exception(" | ".join(errores))


def actualizar_csv():
    """Sincroniza con la web y guarda solo sorteos nuevos."""
    try:
        resultados = extraer_historial_web()
        if not resultados:
            return False, "No se extrajeron sorteos."

        columnas = ["Fecha", "Bola_1", "Bola_2", "Bola_3", "Bola_4", "Bola_5", "Bola_6", "Loto_Mas", "Super_Mas"]
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
                fechas = ", ".join(df_filtrado['Fecha'].tolist())
                return True, f"✅ {len(df_filtrado)} sorteos nuevos: {fechas}"
            return True, f"Todo al día. Web devolvió {len(df_nuevos)} sorteos, todos ya estaban."
        else:
            df_nuevos = df_nuevos.sort_values(by='Fecha', ascending=False)
            df_nuevos.to_csv(RUTA_CSV, index=False)
            return True, f"Archivo creado con {len(df_nuevos)} sorteos."

    except Exception as e:
        return False, f"Error al extraer: {e}"


def cargar_datos():
    """Carga el CSV histórico con tipos correctos."""
    if not os.path.exists(RUTA_CSV):
        return pd.DataFrame()
    df = pd.read_csv(RUTA_CSV)
    if 'Fecha' in df.columns:
        df['Fecha'] = df['Fecha'].astype(str).str.strip()
    for col in ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df.sort_values(by='Fecha', ascending=False).reset_index(drop=True)