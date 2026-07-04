import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime, timedelta

RUTA_CSV_KINO = os.path.join(os.path.dirname(__file__), '..', 'data', 'historial_kino.csv')
URL_YELU_KINO = "https://www.yelu.do/leidsa/results/super-kino-tv"
HOJA_NUBE_KINO = "Historial_Kino"
COLS_KINO = ["Fecha"] + [f"B{i}" for i in range(1, 21)]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

MESES_ES = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
}


def extraer_de_yelu_kino():
    r = requests.get(URL_YELU_KINO, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code} en yelu.do")

    soup = BeautifulSoup(r.text, 'html.parser')
    texto = soup.get_text(separator='\n')

    patron = re.compile(
        r'(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+(\d{4})[^\d]{0,80}?'
        r'((?:\d{1,2}\s+){19}\d{1,2})',
        re.IGNORECASE
    )

    historial = []
    fechas_vistas = set()

    for m in patron.finditer(texto):
        dia, mes_nombre, anio = m.group(1), m.group(2).lower(), m.group(3)
        mes = MESES_ES.get(mes_nombre)
        if not mes:
            continue
        # Yelu publica con fecha del día siguiente al sorteo
        fecha_pub = datetime.strptime(f"{anio}-{mes}-{dia.zfill(2)}", '%Y-%m-%d')
        fecha_iso = (fecha_pub - timedelta(days=1)).strftime('%Y-%m-%d')
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
        raise Exception("yelu.do Kino: sin coincidencias (¿cambió el formato?)")
    return historial


# ============ NUBE ============

def _leer_nube():
    try:
        import modulos.gsheets_helper as gsh
        ws, _ = gsh.conectar_worksheet(HOJA_NUBE_KINO)
        if ws is None:
            return pd.DataFrame()
        regs = ws.get_all_records()
        df = pd.DataFrame(regs)
        if df.empty:
            return pd.DataFrame()
        df = df.reindex(columns=COLS_KINO)
        df['Fecha'] = df['Fecha'].astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame()


def _escribir_nube(df):
    try:
        import modulos.gsheets_helper as gsh
        ws, _ = gsh.conectar_worksheet(HOJA_NUBE_KINO)
        if ws is None:
            return False
        ws.clear()
        ws.update([COLS_KINO] + df[COLS_KINO].astype(str).values.tolist())
        return True
    except Exception:
        return False


# ============ SYNC PRINCIPAL ============

def actualizar_csv_kino():
    fuentes = []
    nota_web = ""

    try:
        df_web = pd.DataFrame(extraer_de_yelu_kino(), columns=COLS_KINO)
        fuentes.append(df_web)
    except Exception as e:
        nota_web = f" (web falló: {e})"

    if os.path.exists(RUTA_CSV_KINO):
        try:
            fuentes.append(pd.read_csv(RUTA_CSV_KINO))
        except Exception:
            pass

    df_nube = _leer_nube()
    if not df_nube.empty:
        fuentes.append(df_nube)

    if not fuentes:
        return False, f"Sin datos de ninguna fuente.{nota_web}"

    previas = set()
    for f in fuentes[1:] if nota_web == "" else fuentes:
        previas.update(f['Fecha'].astype(str).str.strip().tolist())

    df = pd.concat(fuentes, ignore_index=True)
    df['Fecha'] = df['Fecha'].astype(str).str.strip()
    df = df[df['Fecha'].str.match(r'^\d{4}-\d{2}-\d{2}$', na=False)]
    for col in COLS_KINO[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=COLS_KINO)
    for col in COLS_KINO[1:]:
        df[col] = df[col].astype(int)

    df = df.drop_duplicates(subset=['Fecha']).sort_values(by='Fecha', ascending=False).reset_index(drop=True)

    os.makedirs(os.path.dirname(RUTA_CSV_KINO), exist_ok=True)
    df.to_csv(RUTA_CSV_KINO, index=False)
    nube_ok = _escribir_nube(df)

    nuevos = len([f for f in df['Fecha'] if f not in previas])
    icono_nube = "☁️" if nube_ok else "⚠️ nube no disponible"
    if nuevos > 0:
        return True, f"✅ {nuevos} sorteos Kino nuevos. Total: {len(df)} {icono_nube}{nota_web}"
    return True, f"Kino al día. Total: {len(df)} sorteos {icono_nube}{nota_web}"


def cargar_datos_kino():
    if not os.path.exists(RUTA_CSV_KINO):
        return pd.DataFrame()
    df = pd.read_csv(RUTA_CSV_KINO)
    df['Fecha'] = df['Fecha'].astype(str).str.strip()
    for col in [f"B{i}" for i in range(1, 21)]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df.sort_values(by='Fecha', ascending=False).reset_index(drop=True)