import random
import pandas as pd
from collections import Counter

def analizar_frecuencias(df):
    if df is None or df.empty: return pd.DataFrame()
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df_moderno = df[df['Fecha'] >= '2024-03-01']
    if df_moderno.empty: return pd.DataFrame()
    bolas = df_moderno[['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']].values.flatten()
    conteo = Counter(bolas)
    for i in range(1, 41):
        if i not in conteo: conteo[i] = 0
    df_frec = pd.DataFrame(conteo.items(), columns=['Bola', 'Apariciones'])
    df_frec['Bola'] = df_frec['Bola'].astype(str) 
    return df_frec.sort_values(by='Bola', key=lambda col: col.astype(int)).reset_index(drop=True)

def evaluar_combinacion(combinacion, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, historial_sets):
    """La guillotina de filtros matemáticos ampliada."""
    
    # 1. FILTRO ANTI-CLONES (Jugadas Ganadoras Pasadas)
    if set(combinacion) in historial_sets: 
        return False
        
    # 2. Rango de Suma
    suma = sum(combinacion)
    if not (rango_suma[0] <= suma <= rango_suma[1]): return False
    
    # 3. Pares e Impares
    if descartar_pares:
        pares = sum(1 for num in combinacion if num % 2 == 0)
        if pares == 0 or pares == 6: return False
        
    # 4. Terminaciones
    if descartar_terminaciones:
        terminaciones = [num % 10 for num in combinacion]
        for digito in range(10):
            if terminaciones.count(digito) > 2: return False
            
    # 5. FILTRO ANTI-CONSECUTIVOS (Ej: 14, 15, 16)
    if descartar_consecutivos:
        for i in range(len(combinacion) - 2):
            if combinacion[i] + 1 == combinacion[i+1] and combinacion[i] + 2 == combinacion[i+2]:
                return False
                
    return True

def generar_jugadas_optimas(df_historial, cantidad=5, rango_suma=(80, 150), descartar_pares=True, descartar_terminaciones=True, descartar_consecutivos=True, descartar_historico=True):
    jugadas_aprobadas = []
    intentos = 0
    
    # Pre-cargar el historial para el Filtro Anti-Clones
    historial_sets = []
    if descartar_historico and not df_historial.empty:
        bolas_hist = df_historial[['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']].values
        historial_sets = [set(fila) for fila in bolas_hist]
    
    if not df_historial.empty:
        df_frec = analizar_frecuencias(df_historial)
        if not df_frec.empty:
            df_ordenado = df_frec.sort_values(by='Apariciones', ascending=False)
            bolas_calientes = df_ordenado['Bola'].head(15).astype(int).tolist()
            bolas_restantes = df_ordenado['Bola'].tail(25).astype(int).tolist()
        else:
            bolas_calientes = list(range(1, 41))
            bolas_restantes = list(range(1, 41))
    else:
        bolas_calientes = list(range(1, 41))
        bolas_restantes = list(range(1, 41))

    while len(jugadas_aprobadas) < cantidad and intentos < 150000:
        intentos += 1
        seleccion = random.sample(bolas_calientes, 4) + random.sample(bolas_restantes, 2)
        bolas = sorted(seleccion)
        
        if evaluar_combinacion(bolas, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, historial_sets):
            loto_mas = random.randint(1, 12)
            super_mas = random.randint(1, 15)
            fila = {
                "B1": bolas[0], "B2": bolas[1], "B3": bolas[2], 
                "B4": bolas[3], "B5": bolas[4], "B6": bolas[5],
                "Loto Más": loto_mas, "Súper Más": super_mas,
                "Suma Total": sum(bolas)
            }
            jugadas_aprobadas.append(fila)
            
    return pd.DataFrame(jugadas_aprobadas)