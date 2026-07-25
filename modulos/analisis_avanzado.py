"""Análisis extra para Loto Leidsa: pares frecuentes y test de imparcialidad."""
import pandas as pd
from collections import Counter
from itertools import combinations

BOLAS = ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']


def pares_frecuentes(df, top=15):
    """Cuenta qué parejas de números han salido juntas más veces."""
    if df is None or df.empty:
        return pd.DataFrame(columns=['Par', 'Veces'])
    conteo = Counter()
    for _, fila in df.iterrows():
        try:
            nums = sorted(int(fila[c]) for c in BOLAS)
        except Exception:
            continue
        for par in combinations(nums, 2):
            conteo[par] += 1
    filas = [(f"{a} - {b}", v) for (a, b), v in conteo.most_common(top)]
    return pd.DataFrame(filas, columns=['Par', 'Veces'])


def matriz_pares(df):
    """Matriz 40x40 de co-ocurrencia para heatmap."""
    import numpy as np
    m = np.zeros((40, 40), dtype=int)
    if df is None or df.empty:
        return m
    for _, fila in df.iterrows():
        try:
            nums = [int(fila[c]) for c in BOLAS]
        except Exception:
            continue
        for a, b in combinations(nums, 2):
            m[a-1][b-1] += 1
            m[b-1][a-1] += 1
    return m


def test_chi_cuadrado(df):
    """
    Test chi-cuadrado de bondad de ajuste: ¿todos los números salen
    con frecuencia parecida (sorteo justo) o hay sesgo?
    Devuelve dict con estadístico, grados de libertad y veredicto.
    """
    if df is None or df.empty or len(df) < 20:
        return {"error": "Se necesitan al menos 20 sorteos para el test."}

    conteo = Counter()
    total_sorteos = 0
    for _, fila in df.iterrows():
        try:
            nums = [int(fila[c]) for c in BOLAS]
        except Exception:
            continue
        for n in nums:
            if 1 <= n <= 40:
                conteo[n] += 1
        total_sorteos += 1

    for i in range(1, 41):
        if i not in conteo:
            conteo[i] = 0

    total_bolas = total_sorteos * 6
    esperado = total_bolas / 40.0  # cada número debería salir esto en promedio

    chi2 = sum((conteo[i] - esperado) ** 2 / esperado for i in range(1, 41))
    gl = 39  # 40 categorías - 1

    # Valores críticos chi-cuadrado para gl=39
    critico_95 = 54.572   # p=0.05
    critico_99 = 62.428   # p=0.01

    if chi2 < critico_95:
        veredicto = "✅ JUSTO"
        detalle = "Las frecuencias son consistentes con un sorteo aleatorio justo. Ningún número está favorecido ni perjudicado de forma significativa."
    elif chi2 < critico_99:
        veredicto = "🟡 LEVE DESVIACIÓN"
        detalle = "Hay una desviación menor, dentro de lo que el azar puede producir ocasionalmente. No es evidencia de trucaje."
    else:
        veredicto = "🔴 DESVIACIÓN NOTABLE"
        detalle = "Desviación estadísticamente notable. Con más sorteos suele normalizarse; en loterías reales casi siempre se debe al azar de muestras pequeñas."

    mas_sale = max(range(1, 41), key=lambda i: conteo[i])
    menos_sale = min(range(1, 41), key=lambda i: conteo[i])

    return {
        "chi2": round(chi2, 2),
        "gl": gl,
        "critico_95": critico_95,
        "esperado": round(esperado, 1),
        "veredicto": veredicto,
        "detalle": detalle,
        "sorteos": total_sorteos,
        "mas_sale": (mas_sale, conteo[mas_sale]),
        "menos_sale": (menos_sale, conteo[menos_sale]),
    }