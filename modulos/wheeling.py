"""
Sistema de Rueda (Wheeling / Covering Design) para Loto Leidsa.
Reparte un grupo de números favoritos en varios boletos de forma que,
SI cierta cantidad de tus números sale, se garantiza al menos un premio.

Importante: NO aumenta la probabilidad de que tus números salgan (sigue
siendo azar). Optimiza cómo cubres la inversión que ya vas a gastar.
"""
import random
from itertools import combinations


def _cubre(boleto, combos_ganadores, garantia):
    """Marca qué combinaciones-objetivo quedan cubiertas por un boleto."""
    set_b = set(boleto)
    cubiertos = set()
    for i, combo in enumerate(combos_ganadores):
        if len(set_b & combo) >= garantia:
            cubiertos.add(i)
    return cubiertos


def generar_rueda(numeros, garantia=3, aciertos_objetivo=4, max_boletos=60):
    """
    numeros: lista de números favoritos (7 a 20 recomendado).
    garantia: cuántos aciertos garantizamos en al menos 1 boleto (3, 4 o 5).
    aciertos_objetivo: SI salen esta cantidad de tus números...
    max_boletos: tope de boletos a generar.

    Devuelve (boletos, info). Usa algoritmo greedy de covering design.
    """
    numeros = sorted(set(int(n) for n in numeros))
    n = len(numeros)

    if n < 6:
        return [], {"error": "Necesitas al menos 6 números."}
    if garantia > aciertos_objetivo:
        return [], {"error": "La garantía no puede ser mayor que los aciertos objetivo."}
    if aciertos_objetivo > n:
        return [], {"error": f"Los aciertos objetivo ({aciertos_objetivo}) no pueden superar tu grupo ({n})."}

    # Todas las formas en que pueden salir 'aciertos_objetivo' de tus números
    combos_ganadores = [set(c) for c in combinations(numeros, aciertos_objetivo)]
    # Todos los boletos posibles (6 números de tu grupo)
    todos_boletos = list(combinations(numeros, 6))

    total_objetivos = len(combos_ganadores)
    pendientes = set(range(total_objetivos))
    boletos = []

    # Cobertura pre-calculada por boleto
    cache = {}

    intentos_sin_mejora = 0
    while pendientes and len(boletos) < max_boletos:
        mejor_boleto = None
        mejor_cobertura = set()

        # Muestreo para no explotar en grupos grandes
        candidatos = todos_boletos
        if len(todos_boletos) > 3000:
            candidatos = random.sample(todos_boletos, 3000)

        for boleto in candidatos:
            if boleto in cache:
                cubiertos = cache[boleto]
            else:
                cubiertos = _cubre(boleto, combos_ganadores, garantia)
                cache[boleto] = cubiertos
            nuevos = cubiertos & pendientes
            if len(nuevos) > len(mejor_cobertura):
                mejor_cobertura = nuevos
                mejor_boleto = boleto
                if len(nuevos) == len(pendientes):
                    break

        if mejor_boleto is None or not mejor_cobertura:
            intentos_sin_mejora += 1
            if intentos_sin_mejora > 3:
                break
            continue

        boletos.append(sorted(mejor_boleto))
        pendientes -= mejor_cobertura
        intentos_sin_mejora = 0

    cobertura_pct = round(100 * (total_objetivos - len(pendientes)) / total_objetivos, 1)
    info = {
        "grupo": numeros,
        "n_numeros": n,
        "garantia": garantia,
        "aciertos_objetivo": aciertos_objetivo,
        "n_boletos": len(boletos),
        "costo": len(boletos) * 50,  # RD$50 por boleto Loto
        "cobertura_pct": cobertura_pct,
        "objetivos_totales": total_objetivos,
        "objetivos_cubiertos": total_objetivos - len(pendientes),
        "completa": len(pendientes) == 0,
    }
    return boletos, info