import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import re

RUTA_CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'historial_loto.csv')

def extraer_historial_web():
    """Escanea la página y extrae TODOS los sorteos del Loto Leidsa con sus fechas web reales."""
    url = "https://www.conectate.com.do/loterias/leidsa"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    respuesta = requests.get(url, headers=headers)
    if respuesta.status_code != 200:
        raise Exception(f"Error de conexión: Código {respuesta.status_code}")
        
    soup = BeautifulSoup(respuesta.text, 'html.parser')
    bloques_loteria = soup.find_all('div', class_='game-block')
    
    historial_extraido = []
    
    for bloque in bloques_loteria:
        texto_bloque = bloque.text.lower()
        
        # Filtramos estrictamente el Loto principal
        if 'loto leidsa' in texto_bloque and 'pool' not in texto_bloque and 'pega' not in texto_bloque:
            
            # 1. ESCÁNER DE FECHA WEB (Busca patrones como "Miércoles 18 de Febrero 2026")
            texto_crudo = bloque.text
            # Regex para atrapar el formato de fecha típico en español
            patron_fecha = re.search(r'(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo).*?\d{4}', texto_crudo, re.IGNORECASE)
            
            if patron_fecha:
                fecha_web = patron_fecha.group(0).strip()
            else:
                # Si falla el regex, intenta buscar la clase específica de conectate
                div_fecha = bloque.find('div', class_='session-date')
                fecha_web = div_fecha.text.strip() if div_fecha else "Fecha Web No Encontrada"
            
            # 2. ESCÁNER DE NÚMEROS
            bolas = bloque.find_all(['span', 'div'], class_=['score', 'ball', 'numero'])
            if not bolas:
                bolas = bloque.find_all('span')
                
            numeros = [int(b.text.strip()) for b in bolas if b.text.strip().isdigit()]
            
            # 3. GUARDAR SI ESTÁ COMPLETO
            if len(numeros) >= 6:
                bolas_base = numeros[0:6]
                loto_mas = numeros[6] if len(numeros) > 6 else 0
                super_mas = numeros[7] if len(numeros) > 7 else 0
                
                # Armamos la fila con la fecha real de la web
                fila = [fecha_web] + bolas_base + [loto_mas, super_mas]
                historial_extraido.append(fila)
    
    if not historial_extraido:
         raise Exception("No se encontraron sorteos del Loto en la página.")
         
    return historial_extraido

def actualizar_csv():
    """Recibe la lista de sorteos web y los guarda sin duplicar."""
    try:
        resultados_web = extraer_historial_web()
        columnas = ["Fecha", "Bola_1", "Bola_2", "Bola_3", "Bola_4", "Bola_5", "Bola_6", "Loto_Mas", "Super_Mas"]
        df_nuevos = pd.DataFrame(resultados_web, columns=columnas)
        
        if os.path.exists(RUTA_CSV):
            df_historial = pd.read_csv(RUTA_CSV)
            
            # Filtramos para guardar solo los sorteos (fechas) que no tengamos ya en el CSV
            df_filtrado = df_nuevos[~df_nuevos['Fecha'].isin(df_historial['Fecha'])]
            
            if not df_filtrado.empty:
                df_final = pd.concat([df_filtrado, df_historial], ignore_index=True)
                df_final.to_csv(RUTA_CSV, index=False)
                return True, f"¡Éxito! Se agregaron {len(df_filtrado)} sorteos nuevos desde la web."
            else:
                return True, "Todo al día. No hay sorteos nuevos en la web."
        else:
            df_nuevos.to_csv(RUTA_CSV, index=False)
            return True, f"Archivo creado con los últimos {len(df_nuevos)} sorteos reales de la web."
            
    except Exception as e:
        return False, f"Error al extraer: {e}"

def cargar_datos():
    if os.path.exists(RUTA_CSV):
        return pd.read_csv(RUTA_CSV)
    return pd.DataFrame()