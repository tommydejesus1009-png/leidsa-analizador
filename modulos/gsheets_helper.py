import streamlit as st
import pandas as pd
import json
import re
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _extraer_sheet_id(url):
    if not url:
        return None
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    return m.group(1) if m else url


@st.cache_resource(ttl=300)
def _cliente():
    creds_raw = st.secrets["GCP_JSON"]
    if isinstance(creds_raw, str):
        creds_dict = json.loads(creds_raw)
    else:
        creds_dict = dict(creds_raw)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def conectar_worksheet(nombre=None):
    """nombre=None -> primera hoja (Loto). Devuelve (ws, error)."""
    try:
        if "GSHEET_URL" not in st.secrets:
            return None, "Falta GSHEET_URL en Secrets"
        if "GCP_JSON" not in st.secrets:
            return None, "Falta GCP_JSON en Secrets"
        client = _cliente()
        sh = client.open_by_key(_extraer_sheet_id(st.secrets["GSHEET_URL"]))
        if nombre is None:
            return sh.sheet1, None
        try:
            return sh.worksheet(nombre), None
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=nombre, rows=2000, cols=25)
            return ws, None
    except json.JSONDecodeError as e:
        return None, f"JSON mal formado en Secrets: {e}"
    except gspread.exceptions.APIError as e:
        return None, f"API Google: {e}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def leer_df(ws, columnas):
    try:
        registros = ws.get_all_records()
        df = pd.DataFrame(registros)
        if df.empty:
            return pd.DataFrame(columns=columnas)
        return df.reindex(columns=columnas)
    except Exception:
        return pd.DataFrame(columns=columnas)


def escribir_df(ws, df, columnas):
    try:
        ws.clear()
        if df.empty:
            ws.update([columnas])
        else:
            data = [columnas] + df[columnas].astype(object).where(
                pd.notnull(df[columnas]), "").values.tolist()
            ws.update(data)
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"