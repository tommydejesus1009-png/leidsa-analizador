import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime, timedelta

RUTA_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'historial_loto.csv')
URL_YELU = "https://www.yelu.do/leidsa/results/loto-mas"
HOJA_NUBE = "Historial_Loto"
COLUMNAS = ["Fecha", "Bola_1", "Bola_2", "Bola_3", "Bola_4",
            "Bola_5", "Bola_6", "Loto_Mas", "Super_Mas"]

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
        fecha_iso = ajustar_a_dia_sorteo(f"{anio}-{mes}-{dia.zfill(2)}")
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


# ============ NUBE (Google Sheets) ============

def _leer_nube():
    try:
        import modulos.gsheets_helper as gsh
        ws, _ = gsh.conectar_worksheet(HOJA_NUBE)
        if ws is None:
            return pd.DataFrame()
        regs = ws.get_all_records()
        df = pd.DataFrame(regs)
        if df.empty:
            return pd.DataFrame()
        df = df.reindex(columns=COLUMNAS)
        df['Fecha'] = df['Fecha'].astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame()


def _escribir_nube(df):
    try:
        import modulos.gsheets_helper as gsh
        ws, _ = gsh.conectar_worksheet(HOJA_NUBE)
        if ws is None:
            return False
        ws.clear()
        ws.update([COLUMNAS] + df[COLUMNAS].astype(str).values.tolist())
        return True
    except Exception:
        return False


# ============ SYNC PRINCIPAL ============

def actualizar_csv():
    """Mezcla web + CSV local + nube, y guarda en CSV y nube."""
    fuentes = []
    nota_web = ""

    try:
        df_web = pd.DataFrame(extraer_de_yelu(), columns=COLUMNAS)
        fuentes.append(df_web)
    except Exception as e:
        nota_web = f" (web falló: {e})"

    if os.path.exists(RUTA_CSV):
        try:
            fuentes.append(pd.read_csv(RUTA_CSV))
        except Exception:
            pass

    df_nube = _leer_nube()
    if not df_nube.empty:
        fuentes.append(df_nube)

    if not fuentes:
        return False, f"Sin datos de ninguna fuente.{nota_web}"

    # Fechas que ya teníamos guardadas (local + nube) para contar nuevos
    previas = set()
    for f in fuentes[1:] if nota_web == "" else fuentes:
        previas.update(f['Fecha'].astype(str).str.strip().tolist())

    df = pd.concat(fuentes, ignore_index=True)
    df['Fecha'] = df['Fecha'].astype(str).str.strip()
    df = df[df['Fecha'].str.match(r'^\d{4}-\d{2}-\d{2}$', na=False)]
    for col in COLUMNAS[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=COLUMNAS)
    for col in COLUMNAS[1:]:
        df[col] = df[col].astype(int)

    df = df.drop_duplicates(subset=['Fecha']).sort_values(by='Fecha', ascending=False).reset_index(drop=True)

    os.makedirs(os.path.dirname(RUTA_CSV), exist_ok=True)
    df.to_csv(RUTA_CSV, index=False)
    nube_ok = _escribir_nube(df)

    nuevos = len([f for f in df['Fecha'] if f not in previas])
    icono_nube = "☁️" if nube_ok else "⚠️ nube no disponible"
    if nuevos > 0:
        return True, f"✅ {nuevos} sorteos nuevos. Total: {len(df)} {icono_nube}{nota_web}"
    return True, f"Al día. Total: {len(df)} sorteos {icono_nube}{nota_web}"


def cargar_datos():
    if not os.path.exists(RUTA_CSV):
        return pd.DataFrame()
    df = pd.read_csv(RUTA_CSV)
    if 'Fecha' in df.columns:
        df['Fecha'] = df['Fecha'].astype(str).str.strip()
    for col in COLUMNAS[1:]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    return df.sort_values(by='Fecha', ascending=False).reset_index(drop=True)