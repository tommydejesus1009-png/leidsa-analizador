import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import pytz
import modulos.scraper_kino as sk
import modulos.kino_filtros as kf
import modulos.gsheets_helper as gsh

COLS_BOVEDA_K = ['Fecha Generada', 'Socio'] + [f"N{i}" for i in range(1, 11)]
NUM_COLS = [f"N{i}" for i in range(1, 11)]
DIAS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

if 'memoria_kino' not in st.session_state:
    st.session_state.memoria_kino = pd.DataFrame(columns=COLS_BOVEDA_K)

tz_rd = pytz.timezone('America/Santo_Domingo')
ahora = datetime.datetime.now(tz_rd)
hoy_str = ahora.strftime("%Y-%m-%d")


def proximo_sorteo_kino(ahora):
    """Diario: L-S 8:55 PM, Domingo 3:55 PM."""
    for delta in range(0, 3):
        d = ahora + timedelta(days=delta)
        hora = 15 if d.weekday() == 6 else 20
        cand = d.replace(hour=hora, minute=55, second=0, microsecond=0)
        if cand > ahora:
            return cand
    return None


# AUTO-SYNC Kino
if 'auto_sync_kino' not in st.session_state:
    st.session_state.auto_sync_kino = True
    with st.spinner("🔄 Sincronizando Super Kino TV..."):
        try:
            sk.actualizar_csv_kino()
        except Exception:
            pass

# Conexión — hoja "Kino" del MISMO spreadsheet (se crea sola)
ws, err_conn = gsh.conectar_worksheet("Kino")
modo_celular = ws is None
df_gsheets = gsh.leer_df(ws, COLS_BOVEDA_K) if not modo_celular else pd.DataFrame(columns=COLS_BOVEDA_K)

df_boveda = pd.concat([df_gsheets, st.session_state.memoria_kino], ignore_index=True)
df_boveda = df_boveda.dropna(subset=['N1']).drop_duplicates().reset_index(drop=True)

st.title("📺 Super Kino TV")
if modo_celular:
    st.caption("📱 Modo Celular — guardado local")
    with st.expander("⚠️ Error de conexión Google Sheets"):
        st.code(err_conn or "Sin detalles")
else:
    st.caption("☁️ Conectado a Google Sheets (hoja Kino)")

df_hist = sk.cargar_datos_kino()

prox = proximo_sorteo_kino(ahora)
if prox:
    faltan = prox - ahora
    h, m = divmod(int(faltan.total_seconds()) // 60, 60)
    hora_txt = "3:55 PM" if prox.weekday() == 6 else "8:55 PM"
    st.info(f"⏳ Próximo Kino: **{DIAS_ES[prox.weekday()]} {prox.strftime('%d-%m')}** a las {hora_txt} — faltan **{h}h {m}m**")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración Kino")
    if st.button("🔄 Sincronizar Kino", width='stretch'):
        with st.spinner("Actualizando..."):
            exito, msg = sk.actualizar_csv_kino()
            st.success(msg) if exito else st.error(msg)
            if exito:
                st.rerun()
    st.divider()
    if not df_hist.empty:
        st.metric("Sorteos en base", len(df_hist))
        st.caption(f"Último: {df_hist['Fecha'].max()}")
    st.divider()
    if st.button("🧹 Limpiar memoria Kino", width='stretch'):
        st.session_state.memoria_kino = pd.DataFrame(columns=COLS_BOVEDA_K)
        st.rerun()

# --- ORÁCULO KINO ---
st.subheader("👁️ Oráculo Kino: Radar de Premios")
aciertos_k = []
if not df_hist.empty and not df_boveda.empty:
    for _, j in df_boveda.iterrows():
        try:
            mis = [int(j[c]) for c in NUM_COLS]
            f_gen = str(j['Fecha Generada']).split(' ')[0]
            for _, s in df_hist[df_hist['Fecha'] >= f_gen].iterrows():
                sorteo = [int(s[c]) for c in sk.COLS_KINO[1:]]
                ac = kf.contar_aciertos(mis, sorteo)
                premio = kf.premio_por_aciertos(ac)
                if premio > 0:
                    aciertos_k.append({
                        "Fecha": s['Fecha'], "Socio": j.get('Socio', 'Tommy'),
                        "Aciertos": ac, "Premio": premio
                    })
        except Exception:
            continue

if aciertos_k:
    aciertos_k.sort(key=lambda x: x['Premio'], reverse=True)
    total_premios = sum(a['Premio'] for a in aciertos_k)
    st.metric("💰 Premios estimados acumulados", f"RD$ {total_premios:,}")
    for a in aciertos_k[:10]:
        emoji = "🏆" if a['Aciertos'] >= 8 else "🔥" if a['Aciertos'] >= 6 else "✨"
        detalle = f"{a['Aciertos']} aciertos" if a['Aciertos'] > 0 else "0 aciertos (¡también paga!)"
        st.success(f"{emoji} **{a['Fecha']}** — **{a['Socio']}**: {detalle} → RD$ {a['Premio']:,}")
    st.caption("⚠️ Montos referenciales — verifica en tu banca")
else:
    st.info("Radar vigilando... sin premios detectados aún.")

st.divider()
t1, t2, t3 = st.tabs(["🎲 Generador", "📂 Bóveda", "📊 Análisis"])

with t1:
    st.subheader("Generar Jugadas Kino (10 de 80)")
    c1, c2 = st.columns([2, 1])
    with c1:
        socio_k = st.text_input("Nombre del jugador", "Tommy", key="socio_kino")
    with c2:
        cant_k = st.number_input("Cantidad", 1, 20, 3, key="cant_kino")

    if st.button("🚀 Generar Kino", width='stretch', type="primary"):
        with st.spinner("Generando..."):
            df_nuevas = kf.generar_kino(df_hist, cant_k, [])
        if df_nuevas.empty:
            st.error("No se pudieron generar jugadas.")
        else:
            filas = [[hoy_str, socio_k] + [int(r[c]) for c in NUM_COLS]
                     for _, r in df_nuevas.iterrows()]
            df_append = pd.DataFrame(filas, columns=COLS_BOVEDA_K)
            st.session_state.memoria_kino = pd.concat(
                [st.session_state.memoria_kino, df_append], ignore_index=True)

            if not modo_celular and ws is not None:
                df_final = pd.concat([df_gsheets, st.session_state.memoria_kino],
                                     ignore_index=True).drop_duplicates().reset_index(drop=True)
                ok, err = gsh.escribir_df(ws, df_final, COLS_BOVEDA_K)
                if ok:
                    st.success(f"✅ {len(df_append)} jugadas Kino guardadas en Google Sheets.")
                else:
                    st.warning(f"⚠️ Local. Error: {err}")
            else:
                st.warning("⚠️ Modo Celular: en memoria.")

            def color_score(v):
                if v >= 70:
                    return 'background-color: #1B5E20; color: white'
                if v >= 45:
                    return 'background-color: #F9A825; color: black'
                return 'background-color: #B71C1C; color: white'
            st.dataframe(df_nuevas.style.map(color_score, subset=['Score']),
                         hide_index=True, width='stretch')

    with st.expander("💰 Tabla de premios (10 números jugados)"):
        df_premios = pd.DataFrame(
            [(k, f"RD$ {v:,}") for k, v in sorted(kf.PREMIOS_KINO.items(), reverse=True)],
            columns=['Aciertos', 'Premio'])
        st.dataframe(df_premios, hide_index=True, width='stretch')
        st.caption("⚠️ Montos referenciales. Verifica en tu banca — pueden cambiar.")

with t2:
    st.subheader("📂 Bóveda Kino")
    if df_boveda.empty:
        st.info("Sin jugadas Kino aún.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Jugadas", len(df_boveda))
        c2.metric("Socios", df_boveda['Socio'].nunique())
        c3.metric("Premios detectados", len(aciertos_k))
        st.dataframe(df_boveda.sort_values('Fecha Generada', ascending=False),
                     hide_index=True, width='stretch', height=350)

with t3:
    a1, a2 = st.columns(2)
    with a1:
        st.subheader("🔥 Top 15 Calientes (30 sorteos)")
        if not df_hist.empty:
            f = kf.analizar_frecuencias_kino(df_hist, 30)
            st.dataframe(f.sort_values('Apariciones', ascending=False).head(15),
                         hide_index=True, width='stretch')
    with a2:
        st.subheader("❄️ Top 15 Atrasados")
        if not df_hist.empty:
            st.dataframe(kf.analizar_atrasados_kino(df_hist).head(15),
                         hide_index=True, width='stretch')

    st.divider()
    st.subheader("📊 Frecuencias 1-80")
    if not df_hist.empty:
        f = kf.analizar_frecuencias_kino(df_hist, 999)
        f['Numero'] = f['Numero'].astype(str)
        st.bar_chart(f.set_index('Numero'))

    st.divider()
    st.subheader("📜 Últimos sorteos Kino")
    if not df_hist.empty:
        st.dataframe(df_hist.head(15), hide_index=True, width='stretch')