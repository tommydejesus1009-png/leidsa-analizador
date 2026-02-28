import streamlit as st
import pandas as pd
import datetime
import pytz
import os
import json
from streamlit_gsheets import GSheetsConnection
import modulos.scraper as scraper
import modulos.fisica_filtros as filtros

st.set_page_config(page_title="Leidsa Analyzer PRO (Modo Móvil)", page_icon="🎯", layout="wide")

COLS_BOVEDA = ['Fecha Generada', 'Socio', 'Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas', 'Suma']

# Memoria temporal para cuando usamos el celular sin la llave de Google
if 'memoria_temporal' not in st.session_state:
    st.session_state.memoria_temporal = pd.DataFrame(columns=COLS_BOVEDA)

# --- CONEXIÓN A LA BÓVEDA INMORTAL ---
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
except Exception as e:
    df_gsheets = pd.DataFrame(columns=COLS_BOVEDA)

# Unimos lo que hay en Google con lo que generes hoy en tu celular
df_boveda = pd.concat([df_gsheets, st.session_state.memoria_temporal], ignore_index=True)
df_boveda = df_boveda.dropna(subset=['Bola_1']).drop_duplicates()

st.title("🎯 Centro de Mando: Leidsa Analyzer")
st.markdown("### Motor de Análisis Físico + Sindicato")
st.divider()

tz_rd = pytz.timezone('America/Santo_Domingo')
hoy_rd = datetime.datetime.now(tz_rd)
hoy_str = hoy_rd.strftime("%Y-%m-%d")

df_historial = scraper.cargar_datos()

# --- PANEL LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración")
    if st.button("🔄 Sincronizar Leidsa", use_container_width=True):
        with st.spinner("Actualizando base de datos..."):
            exito, mensaje = scraper.actualizar_csv()
            if exito: st.success(mensaje); st.rerun()
    
    st.divider()
    st.subheader("🛡️ La Guillotina de Filtros")
    rango_suma = st.slider("Rango de Suma (Gauss)", 60, 180, (80, 150))
    descartar_pares = st.checkbox("Filtro Paridad", value=True)
    descartar_terminaciones = st.checkbox("Filtro Terminaciones", value=True)
    descartar_consecutivos = st.checkbox("Filtro Consecutivos", value=True)
    filtro_historico = st.checkbox("Filtro Anti-Clones (No repetir ganadores)", value=True)

# --- EL ORÁCULO ---
if not df_historial.empty and not df_boveda.empty:
    st.subheader("👁️ El Oráculo: Radar de Aciertos")
    aciertos_detectados = []
    
    for _, mi_j in df_boveda.iterrows():
        try:
            mis_nums = {int(mi_j['Bola_1']), int(mi_j['Bola_2']), int(mi_j['Bola_3']), 
                        int(mi_j['Bola_4']), int(mi_j['Bola_5']), int(mi_j['Bola_6'])}
            
            f_gen = str(mi_j['Fecha Generada']).split(' ')[0]
            sorteos_post = df_historial[df_historial['Fecha'] >= f_gen]
            
            for _, oficial in sorteos_post.iterrows():
                bolas_oficiales = {oficial['Bola_1'], oficial['Bola_2'], oficial['Bola_3'], 
                                   oficial['Bola_4'], oficial['Bola_5'], oficial['Bola_6']}
                hits = mis_nums.intersection(bolas_oficiales)
                if len(hits) >= 3:
                    aciertos_detectados.append({
                        "Fecha Sorteo": oficial['Fecha'],
                        "Socio": mi_j.get('Socio', 'Tommy'),
                        "Aciertos": len(hits),
                        "Números": sorted(list(hits))
                    })
        except: continue
            
    if aciertos_detectados:
        for a in aciertos_detectados:
            st.success(f"🔥 **¡PEGAMOS!** El {a['Fecha Sorteo']}, **{a['Socio']}** pegó {a['Aciertos']} números: {a['Números']}")
    else:
        st.info("Radar vigilando... Sin aciertos de 3 o más números detectados.")
    st.divider()

# --- PESTAÑAS ---
tab1, tab2, tab3, tab4 = st.tabs(["🔮 Jugador Individual", "🤝 Sindicato Colectivo", "📂 Bóveda e Historial", "📊 Análisis y Caja Negra"])

with tab1:
    st.subheader("Modo Francotirador (Individual)")
    if st.button("🚀 Generar 5 Jugadas para Tommy", use_container_width=True):
        with st.spinner("Procesando matrices..."):
            df_nuevas = filtros.generar_predicciones(df_historial, 5, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, filtro_historico, [])
            
            filas_nuevas = []
            for _, r in df_nuevas.iterrows():
                filas_nuevas.append([hoy_str, "Tommy", r['Bola_1'], r['Bola_2'], r['Bola_3'], r['Bola_4'], r['Bola_5'], r['Bola_6'], r['Loto_Mas'], r['Super_Mas'], r['Suma']])
            
            df_append = pd.DataFrame(filas_nuevas, columns=COLS_BOVEDA)
            st.session_state.memoria_temporal = pd.concat([st.session_state.memoria_temporal, df_append], ignore_index=True)
            
            try:
                df_final = pd.concat([df_gsheets, st.session_state.memoria_temporal], ignore_index=True)
                conn.update(spreadsheet=url_sheet, data=df_final)
                st.success("✅ Jugadas guardadas exitosamente en Google Sheets.")
            except Exception:
                st.warning("⚠️ **Modo Celular Activado**: Te generé las jugadas, pero toma un Screenshot ahora. Para que se guarden en Google para siempre, necesitas poner la llave desde una computadora luego.")
            
            st.table(df_nuevas)

with tab2:
    st.subheader("Sindicato de Socios")
    nombres_in = st.text_input("Nombres (Tommy, Socio1...)", "Tommy, Amigo")
    cant_in = st.number_input("Jugadas por Socio", 1, 10, 2)
    
    lista_socios = [n.strip() for n in nombres_in.split(",") if n.strip()]
    
    if st.button("🔥 Forjar Bloque para Sindicato", use_container_width=True):
        total = len(lista_socios) * cant_in
        df_nuevas = filtros.generar_predicciones(df_historial, total, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, filtro_historico, [])
        
        filas_sindicato = []
        for i, socio in enumerate(lista_socios):
            sub_df = df_nuevas.iloc[i*cant_in : (i+1)*cant_in]
            st.markdown(f"#### 👤 Socio: **{socio}**")
            st.table(sub_df)
            for _, r in sub_df.iterrows():
                filas_sindicato.append([hoy_str, socio, r['Bola_1'], r['Bola_2'], r['Bola_3'], r['Bola_4'], r['Bola_5'], r['Bola_6'], r['Loto_Mas'], r['Super_Mas'], r['Suma']])
        
        df_append = pd.DataFrame(filas_sindicato, columns=COLS_BOVEDA)
        st.session_state.memoria_temporal = pd.concat([st.session_state.memoria_temporal, df_append], ignore_index=True)
        
        try:
            df_final = pd.concat([df_gsheets, st.session_state.memoria_temporal], ignore_index=True)
            conn.update(spreadsheet=url_sheet, data=df_final)
            st.success("✅ Bloque del sindicato registrado en la Bóveda de Google.")
        except Exception:
            st.warning("⚠️ **Modo Celular Activado**: Tómale captura (Screenshot) a las jugadas de tus socios para enviárselas. El guardado en la nube requiere la llave desde una computadora.")

with tab3:
    st.subheader("📂 Bóveda Histórica")
    if not df_boveda.empty:
        def resaltar_resultados(row):
            f_gen = str(row['Fecha Generada']).split(' ')[0]
            sorteos_validos = df_historial[df_historial['Fecha'] >= f_gen]
            if sorteos_validos.empty: return [''] * len(row)
            
            estilos = [''] * len(row)
            bolas_cols = ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']
            
            for _, sorteo in sorteos_validos.iterrows():
                ganadores = {int(sorteo[c]) for c in bolas_cols}
                aciertos = 0
                for i, col in enumerate(row.index):
                    if col in bolas_cols and pd.notnull(row[col]) and int(row[col]) in ganadores:
                        estilos[i] = 'background-color: #FFD700; color: black; font-weight: bold'
                        aciertos += 1
                
                if aciertos >= 6: 
                    return ['background-color: #FF4B4B; color: white; font-weight: bold'] * len(row)
            return estilos

        df_styled = df_boveda.sort_values(by="Fecha Generada", ascending=False).style.apply(resaltar_resultados, axis=1)
        st.dataframe(df_styled, use_container_width=True)
        st.caption("🟡 Dorado: Acierto | 🔴 Rojo: MATRIZ QUEMADA")
    else:
        st.info("La bóveda está vacía.")

with tab4:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📊 Mapa de Calor")
        if not df_historial.empty:
            df_frec = filtros.analizar_frecuencias(df_historial)
            st.bar_chart(df_frec.set_index('Bola'))
    with col_b:
        st.subheader("📜 Historial Real Leidsa")
        st.dataframe(df_historial.head(30), hide_index=True)
