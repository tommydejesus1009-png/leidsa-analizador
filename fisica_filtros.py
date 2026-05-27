import random
import pandas as pd
from collections import Counter

# ============ ANÁLISIS ============

def analizar_frecuencias(df, ventana_dias=None):
    """Cuenta apariciones de cada bola. Si ventana_dias se da, solo últimos N sorteos."""
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
    """Devuelve cuántos sorteos lleva cada número sin salir."""
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
    """Devuelve media, std, min, max de la suma de los 6 números."""
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
        'std': round(float(sumas.std()), 1),
        'min': int(sumas.min()),
        'max': int(sumas.max())
    }


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

    # Paridad: solo descartar 6-0 o 0-6. 5-1 SÍ es válido (sale en Loto real).
    if descartar_pares:
        pares = sum(1 for n in combinacion if n % 2 == 0)
        if pares == 0 or pares == 6:
            return False

    # Terminaciones: no más de 3 con misma terminación
    if descartar_terminaciones:
        terminaciones = [n % 10 for n in combinacion]
        if max(Counter(terminaciones).values()) >= 4:
            return False

    # Consecutivos: descarta cuando hay 4+ seguidos
    if descartar_consecutivos:
        ordenada = sorted(combinacion)
        consec = 1
        max_consec = 1
        for i in range(1, 6):
            if ordenada[i] == ordenada[i-1] + 1:
                consec += 1
                max_consec = max(max_consec, consec)
            else:
                consec = 1
        if max_consec >= 4:
            return False

    # Balance bajos/altos: descartar todos bajos (≤20) o todos altos
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

    # Calcular pools de calientes y atrasados
    calientes = list(range(1, 41))
    atrasados = list(range(1, 41))

    if not df_historial.empty:
        df_frec = analizar_frecuencias(df_historial, ventana_dias=30)
        if not df_frec.empty:
            df_ord = df_frec.sort_values(by='Apariciones', ascending=False)
            calientes = df_ord['Bola'].head(18).astype(int).tolist()

        df_atr = analizar_atrasados(df_historial)
        if not df_atr.empty:
            atrasados = df_atr['Bola'].head(15).astype(int).tolist()

    todos = list(range(1, 41))

    while len(jugadas_aprobadas) < cantidad and intentos < 200000:
        intentos += 1

        # 4 estrategias rotativas
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

        # Garantizar 6 únicos
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
            suma_total = sum(bolas)
            jugadas_aprobadas.append(bolas + [loto_mas, super_mas, suma_total])
            jugadas_previas_sets.append(set(bolas))

    columnas = ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas', 'Suma']
    return pd.DataFrame(jugadas_aprobadas, columns=columnas)