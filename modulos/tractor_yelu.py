import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
import time

RUTA_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'historial_loto.csv')

def limpiar_fecha(fecha_texto):
    meses = {'enero':'01', 'febrero':'02', 'marzo':'03', 'abril':'04',
             'mayo':'05', 'junio':'06', 'julio':'07', 'agosto':'08',
             'septiembre':'09', 'octubre':'10', 'noviembre':'11', 'diciembre':'12'}
    match = re.search(r'(\d{1,2})\s+de\s+([a-zA-Z]+)\s+(\d{4})', fecha_texto.lower())
    if match: return f"{match.group(3)}-{meses.get(match.group(2), '01')}-{match.group(1).zfill(2)}"
    return None

def generar_lista_meses():
    """Genera la lista de meses SOLO para la Era Moderna (Marzo 2024 en adelante)"""
    meses = []
    for anio in range(2024, 2027):
        for mes in range(1, 13):
            # No buscar en el futuro (después de febrero 2026)
            if anio == 2026 and mes > 2: 
                break
            # IGNORAR todo lo que sea antes de Marzo 2024 (cuando eran 38 bolos)
            if anio == 2024 and mes < 3: 
                continue
                
            meses.append(f"{anio}-{mes:02d}")
            
    return sorted(meses, reverse=True)

def encender_tractor_payload():
    print("🚜 Encendiendo Tractor (Modo Era Moderna: Marzo 2024+)...")
    url_base = "https://www.yelu.do/leidsa/results/history"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    meses_a_buscar = generar_lista_meses()
    historial_masivo = []
    
    for mes in meses_a_buscar:
        print(f"📡 Inyectando Payload: {mes}...")
        payload = {'_method': 'POST', 'data[Lottery][name]': 'Loto Más', 'data[Lottery][date]': mes}
        
        try:
            respuesta = requests.post(url_base, data=payload, headers=headers, timeout=10)
        except:
            continue
            
        if respuesta.status_code != 200: continue
            
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        for fila in soup.find_all('tr'):
            columnas = fila.find_all('td')
            if len(columnas) >= 3:
                texto_juego = columnas[1].text.lower()
                
                if 'loto' in texto_juego and 'pool' not in texto_juego:
                    fecha_limpia = limpiar_fecha(columnas[0].text.strip())
                    
                    texto_bruto = columnas[2].get_text(separator=" ").strip()
                    bolas = [int(num) for num in texto_bruto.split() if num.isdigit()]
                    
                    if fecha_limpia and len(bolas) >= 6:
                        historial_masivo.append([fecha_limpia] + bolas[0:6] + [bolas[6] if len(bolas) > 6 else 0, bolas[7] if len(bolas) > 7 else 0])
        
        time.sleep(1) 
        
    return historial_masivo

def vaciar_en_caja_negra():
    datos = encender_tractor_payload()
    if not datos:
        print("❌ Error. La página no devolvió datos legibles.")
        return
        
    columnas = ["Fecha", "Bola_1", "Bola_2", "Bola_3", "Bola_4", "Bola_5", "Bola_6", "Loto_Mas", "Super_Mas"]
    df_masivo = pd.DataFrame(datos, columns=columnas)
    
    df_masivo = df_masivo.drop_duplicates(subset=['Fecha']).sort_values(by='Fecha').reset_index(drop=True)
    df_masivo.to_csv(RUTA_CSV, index=False)
    
    print("="*60)
    print(f"✅ ¡CORONAMOS! Se inyectaron {len(df_masivo)} sorteos de la ERA MODERNA a la Caja Negra.")
    print("="*60)

if __name__ == "__main__":
    vaciar_en_caja_negra()