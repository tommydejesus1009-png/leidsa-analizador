import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import re
import datetime

RUTA_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'historial_loto.csv')

def extraer_historial_web():
    url = "https://www.conectate.com.do/loterias/leidsa"
    headers = {'User-Agent': 'Mozilla/5.0'}
    respuesta = requests.get(url, headers=headers)
    if respuesta.status_code != 200: raise Exception("Error de red")
    
    soup = BeautifulSoup(respuesta.text, 'html.parser')
    texto_pagina = soup.get_text(separator=" ").lower()
    anio_match = re.search(r'(202[4-9])', texto_pagina)
    anio_global = anio_match.group(1) if anio_match else str(datetime.datetime.now().year)

    dict_sorteos = {}
    for div in soup.find_all('div'):
        texto_div = div.get_text(separator=" ").lower()
        if 'loto' in texto_div and 'más' in texto_div and 'pool' not in texto_div:
            bolas = div.find_all(class_=lambda c: c and 'score' in c)
            nums = [int(b.text.strip()) for b in bolas if b.text.strip().isdigit()]
            if 6 <= len(nums) <= 8:
                matches = re.findall(r'(?<!\d)(\d{1,2})[-/](\d{1,2})(?!\d)', texto_div)
                if matches:
                    dia, mes = matches[-1] 
                    fecha = f"{anio_global}-{mes.zfill(2)}-{dia.zfill(2)}"
                    if datetime.datetime.strptime(fecha, "%Y-%m-%d").weekday() in [0, 1, 4]: continue
                    dict_sorteos["-".join(map(str, nums))] = [fecha] + nums[0:6] + [nums[6] if len(nums)>6 else 0, nums[7] if len(nums)>7 else 0]
    return list(dict_sorteos.values())

def actualizar_csv():
    try:
        data = extraer_historial_web()
        df_n = pd.DataFrame(data, columns=["Fecha", "Bola_1", "Bola_2", "Bola_3", "Bola_4", "Bola_5", "Bola_6", "Loto_Mas", "Super_Mas"])
        if os.path.exists(RUTA_CSV):
            df_h = pd.read_csv(RUTA_CSV)
            df_f = df_n[~df_n['Fecha'].isin(df_h['Fecha'])]
            if not df_f.empty:
                pd.concat([df_f, df_h], ignore_index=True).to_csv(RUTA_CSV, index=False)
                return True, f"Se agregaron {len(df_f)} sorteos."
            return True, "Al día."
        df_n.to_csv(RUTA_CSV, index=False)
        return True, "Archivo creado."
    except Exception as e: return False, str(e)

def cargar_datos():
    if os.path.exists(RUTA_CSV): return pd.read_csv(RUTA_CSV)
    return pd.DataFrame()
