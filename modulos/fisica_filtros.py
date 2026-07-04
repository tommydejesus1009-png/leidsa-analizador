import random
import pandas as pd
from collections import Counter

# ============ ANÁLISIS ============

def analizar_frecuencias(df, ventana_dias=None):
    if df is None or df.empty:
        return pd.DataFrame(columns=['Bola', 'Apariciones'])
    df = df.copy()
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha'])
    df_moderno = df[df['Fecha'] >= '2024-03-01']
    if df_moderno.empty:
        return pd.DataFrame(columns=['Bola', 'Apariciones'])
    if ventana_dias is not None:
        df_moderno = df_moderno.sort_values('Fecha', ascending=False).head(ventana_dias)
    bolas = df_moderno[['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']].values.flatten()
    conteo = Counter(int(b) for b in bolas)
    for i in range(1, 41):
        if i not in conteo:
            conteo[i] = 0
    df_frec = pd.DataFrame(conteo.items(), columns=['Bola', 'Apariciones'])
    df_frec['Bola'] = df_frec['Bola'].astype(int)
    return df_frec.sort_values(by='Bola').reset_index(drop=True)


def analizar_atrasados(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=['Bola', 'Sorteos_Sin_Salir'])
    df = df.copy()
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha']).sort_values('Fecha', ascending=False)
    sin_salir = {i: 0 for i in range(1, 41)}
    visto = set()
    for _, fila in df.iterrows():
        bolas = {int(fila[c]) for c in ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']}
        for n in range(1, 41):
            if n not in visto:
                if n in bolas:
                    visto.add(n)
                else:
                    sin_salir[n] += 1
        if len(visto) == 40:
            break
    df_atr = pd.DataFrame(sin_salir.items(), columns=['Bola', 'Sorteos_Sin_Salir'])
    return df_atr.sort_values(by='Sorteos_Sin_Salir', ascending=False).reset_index(drop=True)


def estadisticas_suma(df):
    if df is None or df.empty:
        return {'media': 123, 'std': 25, 'min': 60, 'max': 180}
    df = df.copy()
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha'])
    df = df[df['Fecha'] >= '2024-03-01']
    if df.empty:
        return {'media': 123, 'std': 25, 'min': 60, 'max': 180}
    sumas = df[['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']].sum(axis=1)
    return {
        'media': round(float(sumas.mean()), 1),
        'std': round(float(sumas.std()), 1) or 1.0,
        'min': int(sumas.min()),
        'max': int(sumas.max())
    }


def calcular_score(bolas, calientes, atrasados, stats):
    """Score 0-100 de qué tan 'alineada' está la jugada con el análisis."""
    score = 0
    n_cal = sum(1 for b in bolas if b in calientes)
    score += min(n_cal, 4) * 10                      # máx 40
    n_atr = sum(1 for b in bolas if b in atrasados)
    if 1 <= n_atr <= 2:
        score += 20
    elif n_atr == 3:
        score += 10
    if stats['std'] > 0:
        z = abs(sum(bolas) - stats['media']) / stats['std']
        score += max(0, int(25 * (1 - min(z, 2) / 2)))  # máx 25
    bajos = sum(1 for b in bolas if b <= 20)
    pares = sum(1 for b in bolas if b % 2 == 0)
    if 2 <= bajos <= 4:
        score += 8
    if 2 <= pares <= 4:
        score += 7
    return min(score, 100)


# ============ EVALUACIÓN ============

def evaluar_combinacion(combinacion, rango_suma, descartar_pares, descartar_terminaciones,
                       descartar_consecutivos, historial_sets, jugadas_previas_sets):
    if set(combinacion) in historial_sets:
        return False
    if set(combinacion) in jugadas_previas_sets:
        return False
    suma = sum(combinacion)
    if not (rango_suma[0] <= suma <= rango_suma[1]):
        return False
    if descartar_pares:
        pares = sum(1 for n in combinacion if n % 2 == 0)
        if pares == 0 or pares == 6:
            return False
    if descartar_terminaciones:
        terminaciones = [n % 10 for n in combinacion]
        if max(Counter(terminaciones).values()) >= 4:
            return False
    if descartar_consecutivos:
        ordenada = sorted(combinacion)
        consec, max_consec = 1, 1
        for i in range(1, 6):
            if ordenada[i] == ordenada[i-1] + 1:
                consec += 1
                max_consec = max(max_consec, consec)
            else:
                consec = 1
        if max_consec >= 4:
            return False
    bajos = sum(1 for n in combinacion if n <= 20)
    if bajos == 0 or bajos == 6:
        return False
    return True


# ============ GENERADOR ============

def generar_predicciones(df_historial, cantidad, rango_suma, descartar_pares,
                         descartar_terminaciones, descartar_consecutivos,
                         filtro_historico, jugadas_previas_sets):
    jugadas_aprobadas = []
    intentos = 0
    historial_sets = []

    if filtro_historico and not df_historial.empty:
        bolas_hist = df_historial[['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']].values
        historial_sets = [set(int(x) for x in fila) for fila in bolas_hist]

    calientes = list(range(1, 41))
    atrasados = list(range(1, 41))
    stats = estadisticas_suma(df_historial)

    if not df_historial.empty:
        df_frec = analizar_frecuencias(df_historial, ventana_dias=30)
        if not df_frec.empty:
            calientes = df_frec.sort_values(by='Apariciones', ascending=False)['Bola'].head(18).astype(int).tolist()
        df_atr = analizar_atrasados(df_historial)
        if not df_atr.empty:
            atrasados = df_atr['Bola'].head(15).astype(int).tolist()

    todos = list(range(1, 41))

    while len(jugadas_aprobadas) < cantidad and intentos < 200000:
        intentos += 1
        modo = random.choice(['calientes', 'mixta', 'atrasados', 'libre'])
        try:
            if modo == 'calientes':
                otros = [x for x in todos if x not in calientes]
                seleccion = random.sample(calientes, min(5, len(calientes))) + random.sample(otros, 1)
            elif modo == 'atrasados':
                otros = [x for x in todos if x not in atrasados]
                seleccion = random.sample(atrasados, min(3, len(atrasados))) + random.sample(otros, 3)
            elif modo == 'mixta':
                cal_pool = [x for x in calientes if x not in atrasados[:5]]
                atr_pool = atrasados[:10]
                if len(cal_pool) >= 3 and len(atr_pool) >= 2:
                    base = random.sample(cal_pool, 3) + random.sample(atr_pool, 2)
                    resto = [x for x in todos if x not in base]
                    seleccion = base + random.sample(resto, 1)
                else:
                    seleccion = random.sample(todos, 6)
            else:
                seleccion = random.sample(todos, 6)
        except ValueError:
            seleccion = random.sample(todos, 6)

        seleccion = list(set(seleccion))
        while len(seleccion) < 6:
            extra = random.randint(1, 40)
            if extra not in seleccion:
                seleccion.append(extra)
        seleccion = seleccion[:6]
        bolas = sorted(seleccion)

        if evaluar_combinacion(bolas, rango_suma, descartar_pares, descartar_terminaciones,
                              descartar_consecutivos, historial_sets, jugadas_previas_sets):
            loto_mas = random.randint(1, 12)
            super_mas = random.randint(1, 15)
            score = calcular_score(bolas, calientes, atrasados, stats)
            jugadas_aprobadas.append(bolas + [loto_mas, super_mas, sum(bolas), score])
            jugadas_previas_sets.append(set(bolas))

    columnas = ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6',
                'Loto_Mas', 'Super_Mas', 'Suma', 'Score']
    return pd.DataFrame(jugadas_aprobadas, columns=columnas)