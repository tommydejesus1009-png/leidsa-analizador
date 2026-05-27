import streamlit as st
import pandas as pd
import datetime
import pytz
import json
from streamlit_gsheets import GSheetsConnection
import modulos.scraper as scraper
import modulos.fisica_filtros as filtros

st.set_page_config(page_title="Leidsa Analyzer PRO", page_icon="🎯", layout="wide")

COLS_BOVEDA = ['Fecha Generada', 'Socio', 'Bola_1', 'Bola_2', 'Bola_3',
               'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas', 'Suma']
BOLAS_COLS = ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']

if 'memoria_temporal' not in st.session_state:
    st.session_state.memoria_temporal = pd.DataFrame(columns=COLS_BOVEDA)

def normalizar_fecha_iso(texto):
    if not texto:
        return None
    try:
        f = pd.to_datetime(str(texto), errors='coerce')
        if pd.isna(f):
            return None
        return f.strftime('%Y-%m-%d')
    except Exception:
        return None

# --- CONEXIÓN GOOGLE SHEETS ---
df_gsheets = pd.DataFrame(columns=COLS_BOVEDA)
conn = None
url_sheet = None
modo_celular = True

try:
    url_sheet = st.secrets["GSHEET_URL"]
    if "GCP_JSON" in st.secrets:
        creds_json = json.loads(st.secrets["GCP_JSON"])
        conn = st.connection("gsheets", type=GSheetsConnection, service_account_info=creds_json)
    else:
        conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=url_sheet)
    df_raw.columns = [c.strip() for c in df_raw.columns]
    df_gsheets = df_raw.reindex(columns=COLS_BOVEDA)
    modo_celular = False
except Exception:
    modo_celular = True

df_boveda = pd.concat([df_gsheets, st.session_state.memoria_temporal], ignore_index=True)
df_boveda = df_boveda.dropna(subset=['Bola_1']).drop_duplicates().reset_index(drop=True)

st.title("🎯 Leidsa Analyzer PRO")
if modo_celular:
    st.caption("📱 Modo Celular — guardado local (conecta la llave Google para nube)")
else:
    st.caption("☁️ Conectado a Google Sheets — guardado permanente activo")

tz_rd = pytz.timezone('America/Santo_Domingo')
hoy_rd = datetime.datetime.now(tz_rd)
hoy_str = hoy_rd.strftime("%Y-%m-%d")

df_historial = scraper.cargar_datos()
if not df_historial.empty:
    df_historial['Fecha'] = df_historial['Fecha'].apply(normalizar_fecha_iso)
    df_historial = df_historial.dropna(subset=['Fecha'])

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    if st.button("🔄 Sincronizar Leidsa", use_container_width=True):
        with st.spinner("Actualizando..."):
            exito, mensaje = scraper.actualizar_csv()
            if exito:
                st.success(mensaje)
                st.rerun()
            else:
                st.error(mensaje)

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
        low = max(60, int(stats['media'] - stats['std']))
        high = min(200, int(stats['media'] + stats['std']))
        suma_default = (low, high)

    rango_suma = st.slider("Rango de Suma", 60, 200, suma_default)
    descartar_pares = st.checkbox("Filtro Paridad (descarta 6-0)", value=True)
    descartar_terminaciones = st.checkbox("Filtro Terminaciones", value=True)
    descartar_consecutivos = st.checkbox("Filtro Consecutivos", value=True)
    filtro_historico = st.checkbox("Anti-Clones (no repetir ganadores)", value=True)

    st.divider()
    if st.button("🧹 Limpiar memoria temporal", use_container_width=True):
        st.session_state.memoria_temporal = pd.DataFrame(columns=COLS_BOVEDA)
        st.success("Memoria limpia")
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
            sorteos_post = df_historial[df_historial['Fecha'] >= f_gen]
            for _, oficial in sorteos_post.iterrows():
                bolas_of = {int(oficial[c]) for c in BOLAS_COLS}
                hits = mis_nums.intersection(bolas_of)
                if len(hits) >= 3:
                    aciertos_detectados.append({
                        "Fecha Sorteo": oficial['Fecha'],
                        "Socio": mi_j.get('Socio', 'Tommy'),
                        "Aciertos": len(hits),
                        "Números": sorted(list(hits))
                    })
        except Exception:
            continue

if aciertos_detectados:
    aciertos_detectados.sort(key=lambda x: x['Aciertos'], reverse=True)
    for a in aciertos_detectados[:10]:
        emoji = "🔥🔥🔥" if a['Aciertos'] >= 5 else "🔥🔥" if a['Aciertos'] == 4 else "🔥"
        st.success(f"{emoji} **{a['Fecha Sorteo']}** — **{a['Socio']}** pegó {a['Aciertos']}: {a['Números']}")
    if len(aciertos_detectados) > 10:
        st.caption(f"... y {len(aciertos_detectados) - 10} aciertos más en bóveda")
else:
    st.info("Radar vigilando... sin aciertos de 3+ números aún.")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["🔮 Individual", "🤝 Sindicato", "📂 Historial", "📊 Análisis"])

# --- TAB 1 ---
with tab1:
    st.subheader("Modo Francotirador")
    col1, col2 = st.columns([2, 1])
    with col1:
        nombre_jug = st.text_input("Nombre del jugador", "Tommy")
    with col2:
        cant_jug = st.number_input("Cantidad", 1, 20, 5)

    if st.button("🚀 Generar Jugadas", use_container_width=True, type="primary"):
        with st.spinner("Procesando matrices..."):
            df_nuevas = filtros.generar_predicciones(
                df_historial, cant_jug, rango_suma,
                descartar_pares, descartar_terminaciones,
                descartar_consecutivos, filtro_historico, []
            )

        if df_nuevas.empty:
            st.error("⚠️ No se pudieron generar jugadas. Afloja los filtros.")
        else:
            filas_nuevas = []
            for _, r in df_nuevas.iterrows():
                filas_nuevas.append([hoy_str, nombre_jug,
                                     r['Bola_1'], r['Bola_2'], r['Bola_3'],
                                     r['Bola_4'], r['Bola_5'], r['Bola_6'],
                                     r['Loto_Mas'], r['Super_Mas'], r['Suma']])
            df_append = pd.DataFrame(filas_nuevas, columns=COLS_BOVEDA)
            st.session_state.memoria_temporal = pd.concat(
                [st.session_state.memoria_temporal, df_append], ignore_index=True
            )

            if not modo_celular and conn is not None:
                try:
                    df_final = pd.concat([df_gsheets, st.session_state.memoria_temporal], ignore_index=True)
                    conn.update(spreadsheet=url_sheet, data=df_final)
                    st.success(f"✅ {len(df_nuevas)} jugadas guardadas en Google Sheets.")
                except Exception as e:
                    st.warning(f"⚠️ Guardado en local. (Error nube: {e})")
            else:
                st.warning("⚠️ Modo Celular: en memoria. Toma screenshot.")

            st.table(df_nuevas)

# --- TAB 2 ---
with tab2:
    st.subheader("Sindicato de Socios")
    nombres_in = st.text_input("Nombres separados por coma", "Tommy, Amigo")
    cant_in = st.number_input("Jugadas por socio", 1, 10, 2)
    lista_socios = [n.strip() for n in nombres_in.split(",") if n.strip()]

    if st.button("🔥 Forjar Bloque", use_container_width=True, type="primary"):
        total = len(lista_socios) * cant_in
        with st.spinner(f"Generando {total} jugadas..."):
            df_nuevas = filtros.generar_predicciones(
                df_historial, total, rango_suma,
                descartar_pares, descartar_terminaciones,
                descartar_consecutivos, filtro_historico, []
            )

        if df_nuevas.empty or len(df_nuevas) < total:
            st.error(f"⚠️ Solo se generaron {len(df_nuevas)} de {total}. Afloja filtros.")
        else:
            filas_sindicato = []
            for i, socio in enumerate(lista_socios):
                sub_df = df_nuevas.iloc[i*cant_in : (i+1)*cant_in]
                st.markdown(f"#### 👤 Socio: **{socio}**")
                st.table(sub_df)
                for _, r in sub_df.iterrows():
                    filas_sindicato.append([hoy_str, socio,
                                            r['Bola_1'], r['Bola_2'], r['Bola_3'],
                                            r['Bola_4'], r['Bola_5'], r['Bola_6'],
                                            r['Loto_Mas'], r['Super_Mas'], r['Suma']])

            df_append = pd.DataFrame(filas_sindicato, columns=COLS_BOVEDA)
            st.session_state.memoria_temporal = pd.concat(
                [st.session_state.memoria_temporal, df_append], ignore_index=True
            )

            if not modo_celular and conn is not None:
                try:
                    df_final = pd.concat([df_gsheets, st.session_state.memoria_temporal], ignore_index=True)
                    conn.update(spreadsheet=url_sheet, data=df_final)
                    st.success("✅ Bloque registrado en Google Sheets.")
                except Exception as e:
                    st.warning(f"⚠️ Local. {e}")
            else:
                st.warning("⚠️ Modo Celular: screenshot a las jugadas.")

# --- TAB 3: HISTORIAL ---
with tab3:
    st.subheader("📂 Bóveda de Jugadas")

    if df_boveda.empty:
        st.info("Bóveda vacía. Genera jugadas en las pestañas anteriores.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total jugadas", len(df_boveda))
        with c2:
            st.metric("Socios únicos", df_boveda['Socio'].nunique())
        with c3:
            st.metric("Aciertos detectados", len(aciertos_detectados))
        with c4:
            mejor = max([a['Aciertos'] for a in aciertos_detectados], default=0)
            st.metric("Mejor pegada", f"{mejor} nums")

        st.divider()

        f1, f2 = st.columns(2)
        with f1:
            socios_disp = ['Todos'] + sorted(df_boveda['Socio'].dropna().unique().tolist())
            filtro_socio = st.selectbox("Filtrar por socio", socios_disp)
        with f2:
            fechas_disp = ['Todas'] + sorted(df_boveda['Fecha Generada'].dropna().astype(str).unique().tolist(), reverse=True)
            filtro_fecha = st.selectbox("Filtrar por fecha", fechas_disp)

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
            if sorteos.empty:
                return [''] * len(row)

            estilos = [''] * len(row)
            max_aciertos = 0
            for _, sorteo in sorteos.iterrows():
                ganadores = {int(sorteo[c]) for c in BOLAS_COLS}
                aciertos = 0
                for i, col in enumerate(row.index):
                    if col in BOLAS_COLS and pd.notnull(row[col]) and int(row[col]) in ganadores:
                        estilos[i] = 'background-color: #FFD700; color: black; font-weight: bold'
                        aciertos += 1
                max_aciertos = max(max_aciertos, aciertos)
            if max_aciertos >= 6:
                return ['background-color: #FF4B4B; color: white; font-weight: bold'] * len(row)
            return estilos

        df_show = df_filtrado.sort_values(by="Fecha Generada", ascending=False)
        st.dataframe(df_show.style.apply(resaltar, axis=1), use_container_width=True, height=400)
        st.caption("🟡 Acierto individual | 🔴 MATRIZ GANADORA (6 aciertos)")

        st.divider()
        st.subheader("📈 Stats por socio")
        stats_socio = df_boveda.groupby('Socio').size().reset_index(name='Jugadas')
        aciertos_por_socio = {}
        for a in aciertos_detectados:
            aciertos_por_socio[a['Socio']] = aciertos_por_socio.get(a['Socio'], 0) + 1
        stats_socio['Aciertos'] = stats_socio['Socio'].map(lambda s: aciertos_por_socio.get(s, 0))
        stats_socio = stats_socio.sort_values('Jugadas', ascending=False)
        st.dataframe(stats_socio, hide_index=True, use_container_width=True)

# --- TAB 4: ANÁLISIS ---
with tab4:
    a1, a2 = st.columns(2)
    with a1:
        st.subheader("🔥 Top 10 Calientes (30 sorteos)")
        if not df_historial.empty:
            df_frec = filtros.analizar_frecuencias(df_historial, ventana_dias=30)
            top_cal = df_frec.sort_values('Apariciones', ascending=False).head(10)
            st.dataframe(top_cal, hide_index=True, use_container_width=True)

    with a2:
        st.subheader("❄️ Top 10 Atrasados")
        if not df_historial.empty:
            df_atr = filtros.analizar_atrasados(df_historial)
            st.dataframe(df_atr.head(10), hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("📊 Mapa de Frecuencias Histórico")
    if not df_historial.empty:
        df_frec_total = filtros.analizar_frecuencias(df_historial)
        df_frec_total['Bola'] = df_frec_total['Bola'].astype(str)
        st.bar_chart(df_frec_total.set_index('Bola'))

    st.divider()
    st.subheader("📜 Últimos 30 sorteos oficiales")
    if not df_historial.empty:
        st.dataframe(df_historial.head(30), hide_index=True, use_container_width=True)