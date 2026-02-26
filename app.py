import streamlit as st
import pandas as pd
import datetime
import pytz
import os
from streamlit_gsheets import GSheetsConnection
import modulos.scraper as scraper
import modulos.fisica_filtros as filtros

st.set_page_config(page_title="Leidsa Analyzer PRO", page_icon="🎯", layout="wide")

# --- CONEXIÓN A LA BÓVEDA INMORTAL (Google Sheets) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_sheet = st.secrets["GSHEET_URL"]
    # Leemos la bóveda y limpiamos nombres de columnas
    df_boveda = conn.read(spreadsheet=url_sheet)
    df_boveda.columns = [c.strip() for c in df_boveda.columns]
except Exception as e:
    st.error("⚠️ Error de conexión con Google Sheets. Verifica el enlace en Secrets.")
    df_boveda = pd.DataFrame()

st.title("🎯 Analizador Leidsa: Centro de Mando")
st.markdown("### Motor de Análisis Físico + Sindicato + Bóveda Inmortal")
st.divider()

tz_rd = pytz.timezone('America/Santo_Domingo')
hoy_rd = datetime.datetime.now(tz_rd)
hoy_str = hoy_rd.strftime("%Y-%m-%d")

# Cargar Historial Real de Leidsa (Scraper)
df_historial = scraper.cargar_datos()

# --- PANEL LATERAL: CONFIGURACIÓN Y FILTROS ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    if st.button("🔄 Actualizar Base de Datos", use_container_width=True):
        with st.spinner("Sincronizando con Leidsa..."):
            exito, mensaje = scraper.actualizar_csv()
            if exito: st.success(mensaje); st.rerun()
    
    st.divider()
    st.subheader("🛡️ La Guillotina de Filtros")
    rango_suma = st.slider("Rango de Suma (Gauss)", 60, 180, (80, 150))
    descartar_pares = st.checkbox("Filtro Paridad (Evitar puros pares/impares)", value=True)
    descartar_terminaciones = st.checkbox("Filtro Terminaciones (Máx 2 iguales)", value=True)
    descartar_consecutivos = st.checkbox("Filtro Consecutivos (Máx 2 seguidos)", value=True)
    filtro_historico = st.checkbox("Filtro Anti-Clones (No repetir sorteos reales)", value=True)

# --- EL ORÁCULO: RASTREADOR DE ACIERTOS DETALLADO ---
if not df_historial.empty and not df_boveda.empty:
    cols_nec = ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']
    if all(c in df_boveda.columns for c in cols_nec):
        st.subheader("👁️ El Oráculo: Radar de Aciertos")
        aciertos_encontrados = []
        
        for _, mi_j in df_boveda.iterrows():
            try:
                mis_bolas = {int(mi_j['Bola_1']), int(mi_j['Bola_2']), int(mi_j['Bola_3']), 
                             int(mi_j['Bola_4']), int(mi_j['Bola_5']), int(mi_j['Bola_6'])}
                
                fecha_gen_str = str(mi_j['Fecha Generada']).split(' ')[0]
                sorteos_post = df_historial[df_historial['Fecha'] >= fecha_gen_str]
                
                for _, oficial in sorteos_post.iterrows():
                    bolas_oficiales = {oficial['Bola_1'], oficial['Bola_2'], oficial['Bola_3'], 
                                       oficial['Bola_4'], oficial['Bola_5'], oficial['Bola_6']}
                    hits = mis_bolas.intersection(bolas_oficiales)
                    
                    if len(hits) >= 3:
                        aciertos_encontrados.append({
                            "Fecha": oficial['Fecha'],
                            "Socio": mi_j.get('Socio', 'Tommy'),
                            "Cantidad": len(hits),
                            "Numeros": sorted(list(hits))
                        })
            except: continue
            
        if aciertos_encontrados:
            for a in aciertos_encontrados:
                st.success(f"🎯 **¡ACIERTO!** El {a['Fecha']}, el socio **{a['Socio']}** pegó **{a['Cantidad']}** números: {a['Numeros']}")
        else:
            st.info("Radar vigilando... Sin aciertos de 3+ números en los sorteos recientes.")
    st.divider()

# --- SISTEMA DE PESTAÑAS (TODAS LAS FUNCIONES) ---
tab1, tab2, tab3, tab4 = st.tabs(["🔮 Generador", "🤝 Sindicato", "📂 Bóveda Histórica", "📊 Análisis de Datos"])

with tab1:
    st.subheader("Modo Francotirador (Individual)")
    if st.button("🚀 Generar 5 Jugadas Personales", use_container_width=True):
        with st.spinner("Calculando trayectorias..."):
            df_nuevas = filtros.generar_predicciones(df_historial, 5, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, filtro_historico, [])
            
            # Preparar para guardar
            filas = []
            for _, r in df_nuevas.iterrows():
                filas.append([hoy_str, "Tommy", r['Bola_1'], r['Bola_2'], r['Bola_3'], r['Bola_4'], r['Bola_5'], r['Bola_6'], r['Loto_Mas'], r['Super_Mas'], r['Suma']])
            
            df_append = pd.DataFrame(filas, columns=['Fecha Generada', 'Socio', 'Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas', 'Suma'])
            df_final = pd.concat([df_boveda, df_append], ignore_index=True)
            conn.update(spreadsheet=url_sheet, data=df_final)
            
            st.table(df_nuevas)
            st.balloons()
            st.success("✅ Jugadas guardadas en la Bóveda Inmortal.")

with tab2:
    st.subheader("🤝 Sindicato Colectivo")
    nombres_input = st.text_input("Nombres de Socios (separados por coma)", "Tommy, Socio 1, Socio 2")
    jugadas_por_socio = st.number_input("Matrices por Socio", 1, 10, 2)
    
    lista_socios = [n.strip() for n in nombres_input.split(",") if n.strip()]
    
    if st.button("🔥 Forjar Bloque Colectivo", use_container_width=True):
        total_necesario = len(lista_socios) * jugadas_por_socio
        df_nuevas = filtros.generar_predicciones(df_historial, total_necesario, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, filtro_historico, [])
        
        filas_sindicato = []
        for i, socio in enumerate(lista_socios):
            sub_df = df_nuevas.iloc[i*jugadas_por_socio : (i+1)*jugadas_por_socio]
            st.markdown(f"#### 👤 Socio: **{socio}**")
            st.table(sub_df)
            for _, r in sub_df.iterrows():
                filas_sindicato.append([hoy_str, socio, r['Bola_1'], r['Bola_2'], r['Bola_3'], r['Bola_4'], r['Bola_5'], r['Bola_6'], r['Loto_Mas'], r['Super_Mas'], r['Suma']])
        
        df_append = pd.DataFrame(filas_sindicato, columns=['Fecha Generada', 'Socio', 'Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas', 'Suma'])
        df_final = pd.concat([df_boveda, df_append], ignore_index=True)
        conn.update(spreadsheet=url_sheet, data=df_final)
        st.success("✅ Bloque del Sindicato registrado.")

with tab3:
    st.subheader("📂 Bóveda de Jugadas (Google Sheets)")
    if not df_boveda.empty:
        st.dataframe(df_boveda.sort_values(by="Fecha Generada", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.warning("La bóveda está esperando datos.")

with tab4:
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("📊 Mapa de Calor (Desgaste)")
        if not df_historial.empty:
            df_frec = filtros.analizar_frecuencias(df_historial)
            st.bar_chart(df_frec.set_index('Bola'), use_container_width=True)
    with col_der:
        st.subheader("📜 Historial Real Leidsa")
        st.dataframe(df_historial.head(30), use_container_width=True, hide_index=True)
