import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import pytz
import modulos.scraper as scraper
import modulos.fisica_filtros as filtros
import modulos.gsheets_helper as gsh

COLS_BOVEDA = ['Fecha Generada', 'Socio', 'Bola_1', 'Bola_2', 'Bola_3',
               'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas', 'Suma']
BOLAS_COLS = ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']
DIAS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

if 'memoria_loto' not in st.session_state:
    st.session_state.memoria_loto = pd.DataFrame(columns=COLS_BOVEDA)

tz_rd = pytz.timezone('America/Santo_Domingo')
ahora = datetime.datetime.now(tz_rd)
hoy_str = ahora.strftime("%Y-%m-%d")


def normalizar_fecha_iso(texto):
    try:
        f = pd.to_datetime(str(texto), errors='coerce')
        return None if pd.isna(f) else f.strftime('%Y-%m-%d')
    except Exception:
        return None


def proximo_sorteo(ahora):
    for delta in range(0, 8):
        cand = (ahora + timedelta(days=delta)).replace(hour=20, minute=55, second=0, microsecond=0)
        if cand.weekday() in (2, 5) and cand > ahora:
            return cand
    return None


def ultimo_sorteo_esperado(ahora):
    for delta in range(0, 8):
        cand = (ahora - timedelta(days=delta)).replace(hour=20, minute=55, second=0, microsecond=0)
        if cand.weekday() in (2, 5) and cand <= ahora:
            return cand
    return None


# --- MEJORA #4: AUTO-SYNC (una vez por sesión) ---
if 'auto_sync_loto' not in st.session_state:
    st.session_state.auto_sync_loto = True
    with st.spinner("🔄 Sincronizando sorteos Leidsa..."):
        try:
            scraper.actualizar_csv()
        except Exception:
            pass

# --- CONEXIÓN ---
ws, err_conn = gsh.conectar_worksheet(None)
modo_celular = ws is None
df_gsheets = gsh.leer_df(ws, COLS_BOVEDA) if not modo_celular else pd.DataFrame(columns=COLS_BOVEDA)

df_boveda = pd.concat([df_gsheets, st.session_state.memoria_loto], ignore_index=True)
df_boveda = df_boveda.dropna(subset=['Bola_1']).drop_duplicates().reset_index(drop=True)

st.title("🎯 Loto Leidsa")
if modo_celular:
    st.caption("📱 Modo Celular — guardado local")
    with st.expander("⚠️ Error de conexión Google Sheets"):
        st.code(err_conn or "Sin detalles")
else:
    st.caption("☁️ Conectado a Google Sheets")

df_historial = scraper.cargar_datos()
if not df_historial.empty:
    df_historial['Fecha'] = df_historial['Fecha'].apply(normalizar_fecha_iso)
    df_historial = df_historial.dropna(subset=['Fecha'])

# --- MEJORA #5: BANNER DE SORTEO ---
prox = proximo_sorteo(ahora)
if prox:
    faltan = prox - ahora
    h, m = divmod(int(faltan.total_seconds()) // 60, 60)
    st.info(f"⏳ Próximo sorteo: **{DIAS_ES[prox.weekday()]} {prox.strftime('%d-%m')}** a las 8:55 PM — faltan **{h}h {m}m**")

ult = ultimo_sorteo_esperado(ahora)
if ult is not None and not df_historial.empty:
    fecha_max = df_historial['Fecha'].max()
    if fecha_max < ult.strftime('%Y-%m-%d'):
        st.warning(f"📡 El sorteo del **{ult.strftime('%d-%m')}** aún no aparece en la base. Dale a Sincronizar en unos minutos.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración Loto")
    if st.button("🔄 Sincronizar Leidsa", width='stretch'):
        with st.spinner("Actualizando..."):
            exito, mensaje = scraper.actualizar_csv()
            st.success(mensaje) if exito else st.error(mensaje)
            if exito:
                st.rerun()

    st.divider()
    st.subheader("📊 Stats en vivo")
    if not df_historial.empty:
        stats = filtros.estadisticas_suma(df_historial)
        st.metric("Suma media", f"{stats['media']}")
        st.metric("Rango típico (±1σ)",
                  f"{int(stats['media']-stats['std'])} - {int(stats['media']+stats['std'])}")
        st.caption(f"Base: {len(df_historial)} sorteos")

    st.divider()
    st.subheader("🛡️ Filtros de Generación")
    suma_default = (80, 150)
    if not df_historial.empty:
        stats = filtros.estadisticas_suma(df_historial)
        suma_default = (max(60, int(stats['media'] - stats['std'])),
                        min(200, int(stats['media'] + stats['std'])))
    rango_suma = st.slider("Rango de Suma", 60, 200, suma_default)
    descartar_pares = st.checkbox("Filtro Paridad (descarta 6-0)", value=True)
    descartar_terminaciones = st.checkbox("Filtro Terminaciones", value=True)
    descartar_consecutivos = st.checkbox("Filtro Consecutivos", value=True)
    filtro_historico = st.checkbox("Anti-Clones (no repetir ganadores)", value=True)

    st.divider()
    if st.button("🧹 Limpiar memoria temporal", width='stretch'):
        st.session_state.memoria_loto = pd.DataFrame(columns=COLS_BOVEDA)
        st.rerun()

# --- ORÁCULO ---
st.subheader("👁️ El Oráculo: Radar de Aciertos")
aciertos_detectados = []
if not df_historial.empty and not df_boveda.empty:
    for _, mi_j in df_boveda.iterrows():
        try:
            mis_nums = {int(mi_j[c]) for c in BOLAS_COLS}
            f_gen = normalizar_fecha_iso(mi_j['Fecha Generada'])
            if not f_gen:
                continue
            for _, oficial in df_historial[df_historial['Fecha'] >= f_gen].iterrows():
                hits = mis_nums & {int(oficial[c]) for c in BOLAS_COLS}
                if len(hits) >= 3:
                    aciertos_detectados.append({
                        "Fecha Sorteo": oficial['Fecha'],
                        "Socio": mi_j.get('Socio', 'Tommy'),
                        "Aciertos": len(hits),
                        "Números": sorted(hits)
                    })
        except Exception:
            continue

if aciertos_detectados:
    aciertos_detectados.sort(key=lambda x: x['Aciertos'], reverse=True)
    for a in aciertos_detectados[:10]:
        emoji = "🔥🔥🔥" if a['Aciertos'] >= 5 else "🔥🔥" if a['Aciertos'] == 4 else "🔥"
        st.success(f"{emoji} **{a['Fecha Sorteo']}** — **{a['Socio']}** pegó {a['Aciertos']}: {a['Números']}")
    if len(aciertos_detectados) > 10:
        st.caption(f"... y {len(aciertos_detectados) - 10} más")
else:
    st.info("Radar vigilando... sin aciertos de 3+ números aún.")

st.divider()
tab1, tab2, tab3, tab4 = st.tabs(["🔮 Individual", "🤝 Sindicato", "📂 Historial", "📊 Análisis"])


def guardar_jugadas(df_append, etiqueta="jugadas"):
    st.session_state.memoria_loto = pd.concat(
        [st.session_state.memoria_loto, df_append], ignore_index=True)
    if not modo_celular and ws is not None:
        df_final = pd.concat([df_gsheets, st.session_state.memoria_loto],
                             ignore_index=True).drop_duplicates().reset_index(drop=True)
        ok, err = gsh.escribir_df(ws, df_final, COLS_BOVEDA)
        if ok:
            st.success(f"✅ {len(df_append)} {etiqueta} guardadas en Google Sheets.")
        else:
            st.warning(f"⚠️ Guardado local. Error nube: {err}")
    else:
        st.warning("⚠️ Modo Celular: en memoria. Toma screenshot.")


def mostrar_con_score(df):
    """Tabla con columna Score coloreada."""
    def color_score(v):
        if v >= 75:
            return 'background-color: #1B5E20; color: white'
        if v >= 50:
            return 'background-color: #F9A825; color: black'
        return 'background-color: #B71C1C; color: white'
    st.dataframe(df.style.map(color_score, subset=['Score']),
                 hide_index=True, width='stretch')
    st.caption("🎯 Score: 🟢 75+ alineada con el análisis | 🟡 50-74 | 🔴 <50")


with tab1:
    st.subheader("Modo Francotirador")
    c1, c2 = st.columns([2, 1])
    with c1:
        nombre_jug = st.text_input("Nombre del jugador", "Tommy")
    with c2:
        cant_jug = st.number_input("Cantidad", 1, 20, 5)

    if st.button("🚀 Generar Jugadas", width='stretch', type="primary"):
        with st.spinner("Procesando matrices..."):
            df_nuevas = filtros.generar_predicciones(
                df_historial, cant_jug, rango_suma, descartar_pares,
                descartar_terminaciones, descartar_consecutivos, filtro_historico, [])
        if df_nuevas.empty:
            st.error("⚠️ No se pudieron generar jugadas. Afloja los filtros.")
        else:
            filas = [[hoy_str, nombre_jug] + [int(r[c]) for c in BOLAS_COLS] +
                     [int(r['Loto_Mas']), int(r['Super_Mas']), int(r['Suma'])]
                     for _, r in df_nuevas.iterrows()]
            guardar_jugadas(pd.DataFrame(filas, columns=COLS_BOVEDA))
            mostrar_con_score(df_nuevas)

with tab2:
    st.subheader("Sindicato de Socios")
    nombres_in = st.text_input("Nombres separados por coma", "Tommy, Amigo")
    cant_in = st.number_input("Jugadas por socio", 1, 10, 2)
    lista_socios = [n.strip() for n in nombres_in.split(",") if n.strip()]

    if st.button("🔥 Forjar Bloque", width='stretch', type="primary"):
        total = len(lista_socios) * cant_in
        with st.spinner(f"Generando {total} jugadas..."):
            df_nuevas = filtros.generar_predicciones(
                df_historial, total, rango_suma, descartar_pares,
                descartar_terminaciones, descartar_consecutivos, filtro_historico, [])
        if len(df_nuevas) < total:
            st.error(f"⚠️ Solo salieron {len(df_nuevas)} de {total}. Afloja filtros.")
        else:
            filas = []
            for i, socio in enumerate(lista_socios):
                sub = df_nuevas.iloc[i*cant_in:(i+1)*cant_in]
                st.markdown(f"#### 👤 **{socio}**")
                mostrar_con_score(sub)
                for _, r in sub.iterrows():
                    filas.append([hoy_str, socio] + [int(r[c]) for c in BOLAS_COLS] +
                                 [int(r['Loto_Mas']), int(r['Super_Mas']), int(r['Suma'])])
            guardar_jugadas(pd.DataFrame(filas, columns=COLS_BOVEDA), "jugadas del sindicato")

with tab3:
    st.subheader("📂 Bóveda de Jugadas")
    if df_boveda.empty:
        st.info("Bóveda vacía.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total jugadas", len(df_boveda))
        c2.metric("Socios", df_boveda['Socio'].nunique())
        c3.metric("Aciertos", len(aciertos_detectados))
        c4.metric("Mejor pegada", f"{max([a['Aciertos'] for a in aciertos_detectados], default=0)} nums")

        st.divider()
        f1, f2 = st.columns(2)
        with f1:
            filtro_socio = st.selectbox("Filtrar por socio",
                ['Todos'] + sorted(df_boveda['Socio'].dropna().unique().tolist()))
        with f2:
            filtro_fecha = st.selectbox("Filtrar por fecha",
                ['Todas'] + sorted(df_boveda['Fecha Generada'].dropna().astype(str).unique().tolist(), reverse=True))

        df_filtrado = df_boveda.copy()
        if filtro_socio != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['Socio'] == filtro_socio]
        if filtro_fecha != 'Todas':
            df_filtrado = df_filtrado[df_filtrado['Fecha Generada'].astype(str) == filtro_fecha]

        st.caption(f"Mostrando {len(df_filtrado)} jugadas")

        def resaltar(row):
            f_gen = normalizar_fecha_iso(row['Fecha Generada'])
            if not f_gen or df_historial.empty:
                return [''] * len(row)
            sorteos = df_historial[df_historial['Fecha'] >= f_gen]
            estilos = [''] * len(row)
            max_ac = 0
            for _, s in sorteos.iterrows():
                gan = {int(s[c]) for c in BOLAS_COLS}
                ac = 0
                for i, col in enumerate(row.index):
                    if col in BOLAS_COLS and pd.notnull(row[col]) and int(row[col]) in gan:
                        estilos[i] = 'background-color: #FFD700; color: black; font-weight: bold'
                        ac += 1
                max_ac = max(max_ac, ac)
            if max_ac >= 6:
                return ['background-color: #FF4B4B; color: white; font-weight: bold'] * len(row)
            return estilos

        df_show = df_filtrado.sort_values(by="Fecha Generada", ascending=False)
        st.dataframe(df_show.style.apply(resaltar, axis=1), width='stretch', height=400)
        st.caption("🟡 Acierto | 🔴 MATRIZ GANADORA")

        st.divider()
        st.subheader("📈 Stats por socio")
        stats_socio = df_boveda.groupby('Socio').size().reset_index(name='Jugadas')
        ac_socio = {}
        for a in aciertos_detectados:
            ac_socio[a['Socio']] = ac_socio.get(a['Socio'], 0) + 1
        stats_socio['Aciertos'] = stats_socio['Socio'].map(lambda s: ac_socio.get(s, 0))
        st.dataframe(stats_socio.sort_values('Jugadas', ascending=False),
                     hide_index=True, width='stretch')

with tab4:
    a1, a2 = st.columns(2)
    with a1:
        st.subheader("🔥 Top 10 Calientes (30 sorteos)")
        if not df_historial.empty:
            df_frec = filtros.analizar_frecuencias(df_historial, ventana_dias=30)
            st.dataframe(df_frec.sort_values('Apariciones', ascending=False).head(10),
                         hide_index=True, width='stretch')
    with a2:
        st.subheader("❄️ Top 10 Atrasados")
        if not df_historial.empty:
            st.dataframe(filtros.analizar_atrasados(df_historial).head(10),
                         hide_index=True, width='stretch')

    st.divider()
    st.subheader("📊 Mapa de Frecuencias Histórico")
    if not df_historial.empty:
        df_ft = filtros.analizar_frecuencias(df_historial)
        df_ft['Bola'] = df_ft['Bola'].astype(str)
        st.bar_chart(df_ft.set_index('Bola'))

    st.divider()
    st.subheader("📜 Últimos 30 sorteos oficiales")
    if not df_historial.empty:
        st.dataframe(df_historial.head(30), hide_index=True, width='stretch')