import random
import pandas as pd
from collections import Counter

BOLAS_KINO_COLS = [f"B{i}" for i in range(1, 21)]

# ⚠️ MONTOS REFERENCIALES — verifícalos en tu banca, pueden cambiar
PREMIOS_KINO = {10: 5000000, 9: 100000, 8: 2500, 7: 550, 6: 125, 5: 25, 0: 80}


def analizar_frecuencias_kino(df, ventana=30):
    if df is None or df.empty:
        return pd.DataFrame(columns=['Numero', 'Apariciones'])
    df = df.sort_values('Fecha', ascending=False).head(ventana)
    nums = df[BOLAS_KINO_COLS].values.flatten()
    conteo = Counter(int(n) for n in nums if n > 0)
    for i in range(1, 81):
        if i not in conteo:
            conteo[i] = 0
    out = pd.DataFrame(conteo.items(), columns=['Numero', 'Apariciones'])
    return out.sort_values('Numero').reset_index(drop=True)


def analizar_atrasados_kino(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=['Numero', 'Sorteos_Sin_Salir'])
    df = df.sort_values('Fecha', ascending=False)
    sin_salir = {i: 0 for i in range(1, 81)}
    visto = set()
    for _, fila in df.iterrows():
        bolas = {int(fila[c]) for c in BOLAS_KINO_COLS}
        for n in range(1, 81):
            if n not in visto:
                if n in bolas:
                    visto.add(n)
                else:
                    sin_salir[n] += 1
        if len(visto) == 80:
            break
    out = pd.DataFrame(sin_salir.items(), columns=['Numero', 'Sorteos_Sin_Salir'])
    return out.sort_values('Sorteos_Sin_Salir', ascending=False).reset_index(drop=True)


def evaluar_kino(sel):
    """Reglas suaves de forma para una jugada de 10 números."""
    decenas = Counter((n - 1) // 10 for n in sel)
    if max(decenas.values()) > 3:          # máx 3 por decena
        return False
    mitad_baja = sum(1 for n in sel if n <= 40)
    if not (3 <= mitad_baja <= 7):          # balance 1-40 vs 41-80
        return False
    orden = sorted(sel)
    consec = 1
    for i in range(1, len(orden)):
        if orden[i] == orden[i-1] + 1:
            consec += 1
            if consec >= 4:
                return False
        else:
            consec = 1
    return True


def generar_kino(df_hist, cantidad, jugadas_previas):
    calientes = list(range(1, 81))
    atrasados = list(range(1, 81))

    if df_hist is not None and not df_hist.empty:
        f = analizar_frecuencias_kino(df_hist, 30)
        calientes = f.sort_values('Apariciones', ascending=False)['Numero'].head(30).astype(int).tolist()
        a = analizar_atrasados_kino(df_hist)
        atrasados = a['Numero'].head(25).astype(int).tolist()

    todos = list(range(1, 81))
    jugadas = []
    intentos = 0

    while len(jugadas) < cantidad and intentos < 150000:
        intentos += 1
        modo = random.choice(['calientes', 'atrasados', 'mixta', 'libre'])
        try:
            if modo == 'calientes':
                otros = [x for x in todos if x not in calientes]
                sel = random.sample(calientes, 7) + random.sample(otros, 3)
            elif modo == 'atrasados':
                otros = [x for x in todos if x not in atrasados]
                sel = random.sample(atrasados, 5) + random.sample(otros, 5)
            elif modo == 'mixta':
                base = random.sample(calientes, 5) + random.sample(atrasados, 3)
                base = list(set(base))
                resto = [x for x in todos if x not in base]
                sel = base + random.sample(resto, 10 - len(base))
            else:
                sel = random.sample(todos, 10)
        except ValueError:
            sel = random.sample(todos, 10)

        sel = list(set(sel))
        while len(sel) < 10:
            x = random.randint(1, 80)
            if x not in sel:
                sel.append(x)
        sel = sorted(sel[:10])

        if set(sel) in jugadas_previas:
            continue
        if not evaluar_kino(sel):
            continue

        n_cal = sum(1 for n in sel if n in calientes)
        n_atr = sum(1 for n in sel if n in atrasados)
        score = min(100, n_cal * 8 + (20 if 2 <= n_atr <= 4 else 5))

        jugadas.append(sel + [score])
        jugadas_previas.append(set(sel))

    cols = [f"N{i}" for i in range(1, 11)] + ['Score']
    return pd.DataFrame(jugadas, columns=cols)


def contar_aciertos(mis_10, sorteo_20):
    return len(set(mis_10) & set(sorteo_20))


def premio_por_aciertos(aciertos):
    return PREMIOS_KINO.get(aciertos, 0)