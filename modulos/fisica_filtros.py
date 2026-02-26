import random
import pandas as pd
from collections import Counter

def analizar_frecuencias(df):
    if df is None or df.empty: return pd.DataFrame()
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha']) 
    df_moderno = df[df['Fecha'] >= '2024-03-01']
    if df_moderno.empty: return pd.DataFrame()
    bolas = df_moderno[['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']].values.flatten()
    conteo = Counter(bolas)
    for i in range(1, 41):
        if i not in conteo: conteo[i] = 0
    df_frec = pd.DataFrame(conteo.items(), columns=['Bola', 'Apariciones'])
    df_frec['Bola'] = df_frec['Bola'].astype(str)
    return df_frec.sort_values(by='Bola', key=lambda col: col.astype(int)).reset_index(drop=True)

def evaluar_combinacion(combinacion, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, historial_sets, jugadas_previas_sets):
    if set(combinacion) in historial_sets: return False
    if set(combinacion) in jugadas_previas_sets: return False
    
    suma = sum(combinacion)
    if not (rango_suma[0] <= suma <= rango_suma[1]): return False
        
    pares = sum(1 for n in combinacion if n % 2 == 0)
    impares = 6 - pares
    if descartar_pares and (pares == 6 or impares == 6 or pares == 5 or impares == 5): return False
        
    if descartar_terminaciones:
        terminaciones = [n % 10 for n in combinacion]
        conteo_term = Counter(terminaciones)
        if any(count >= 3 for count in conteo_term.values()): return False
            
    if descartar_consecutivos:
        consecutivos = 1
        max_consecutivos = 1
        for i in range(1, 6):
            if combinacion[i] == combinacion[i-1] + 1:
                consecutivos += 1
                if consecutivos > max_consecutivos: max_consecutivos = consecutivos
            else:
                consecutivos = 1
        if max_consecutivos >= 3: return False
            
    return True

def generar_predicciones(df_historial, cantidad, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, filtro_historico, jugadas_previas_sets):
    jugadas_aprobadas = []
    intentos = 0
    historial_sets = []
    
    if filtro_historico and not df_historial.empty:
        bolas_hist = df_historial[['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']].values
        historial_sets = [set(fila) for fila in bolas_hist]
    
    if not df_historial.empty:
        df_frec = analizar_frecuencias(df_historial)
        if not df_frec.empty:
            df_ordenado = df_frec.sort_values(by='Apariciones', ascending=False)
            bolas_calientes = df_ordenado['Bola'].head(15).astype(int).tolist()
            bolas_restantes = df_ordenado['Bola'].tail(25).astype(int).tolist()
        else:
            bolas_calientes, bolas_restantes = list(range(1, 41)), list(range(1, 41))
    else:
        bolas_calientes, bolas_restantes = list(range(1, 41)), list(range(1, 41))

    while len(jugadas_aprobadas) < cantidad and intentos < 150000:
        intentos += 1
        seleccion = random.sample(bolas_calientes, 4) + random.sample(bolas_restantes, 2)
        bolas = sorted(seleccion)
        
        if evaluar_combinacion(bolas, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, historial_sets, jugadas_previas_sets):
            loto_mas = random.randint(1, 12)
            super_mas = random.randint(1, 15)
            suma_total = sum(bolas)
            jugadas_aprobadas.append(bolas + [loto_mas, super_mas, suma_total])
            jugadas_previas_sets.append(set(bolas))
            
    columnas = ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas', 'Suma']
    return pd.DataFrame(jugadas_aprobadas, columns=columnas)
