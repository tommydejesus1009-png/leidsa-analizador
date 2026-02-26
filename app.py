import streamlit as st
import pandas as pd
import datetime
import pytz
import os
from streamlit_gsheets import GSheetsConnection
import modulos.scraper as scraper
import modulos.fisica_filtros as filtros

st.set_page_config(page_title="Leidsa Analyzer v5.1", page_icon="🎯", layout="wide")

# --- CONEXIÓN A LA BÓVEDA INMORTAL (Google Sheets) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_sheet = st.secrets["GSHEET_URL"]
    df_boveda = conn.read(spreadsheet=url_sheet)
except Exception as e:
    st.error("⚠️ Error conectando a la Bóveda de Google Sheets. Revisa los Secrets.")
    df_boveda = pd.DataFrame()

st.title("🎯 Analizador Leidsa: Modo Sindicato")
st.markdown("### Centro de Mando de Tommy - Historial Blindado")
st.divider()

tz_rd = pytz.timezone('America/Santo_Domingo')
hoy_rd = datetime.datetime.now(tz_rd)
hoy_str = hoy_rd.strftime("%Y-%m-%d")

df_historial = scraper.cargar_datos()

# --- PANEL LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración")
    if st.button("🔄 Actualizar Datos Leidsa", use_container_width=True):
        with st.spinner("Sincronizando con la tómbola..."):
            exito, mensaje = scraper.actualizar_csv()
            if exito: st.success(mensaje); st.rerun()
    
    st.divider()
    rango_suma = st.slider("Límite de Suma (Gauss)", 60, 180, (80, 150))
    descartar_pares = st.checkbox("Filtrar por Paridad", value=True)
    descartar_terminaciones = st.checkbox("Filtrar Terminaciones", value=True)
    descartar_consecutivos = st.checkbox("Filtrar Consecutivos", value=True)

# --- EL ORÁCULO (Rastreador de Aciertos) ---
if not df_historial.empty and not df_boveda.empty:
    st.subheader("👁️ Radar de Aciertos en Historial")
    aciertos_totales = []
    
    for _, mi_j in df_boveda.iterrows():
        mis_bolas = {int(mi_j['Bola_1']), int(mi_j['Bola_2']), int(mi_j['Bola_3']), int(mi_j['Bola_4']), int(mi_j['Bola_5']), int(mi_j['Bola_6'])}
        # Solo comparar con sorteos posteriores a la creación de la jugada
        sorteos_post = df_historial[df_historial['Fecha'] >= str(mi_j['Fecha Generada']).split(' ')[0]]
        
        for _, oficial in sorteos_post.iterrows():
            bolas_oficiales = {oficial['Bola_1'], oficial['Bola_2'], oficial['Bola_3'], oficial['Bola_4'], oficial['Bola_5'], oficial['Bola_6']}
            hits = mis_bolas.intersection(bolas_oficiales)
            if len(hits) >= 3:
                aciertos_totales.append({
                    "Fecha Sorteo": oficial['Fecha'],
                    "Socio": mi_j['Socio'],
                    "Aciertos": len(hits),
                    "Números": sorted(list(hits))
                })
    
    if aciertos_totales:
        for a in aciertos_totales:
            st.success(f"🔥 **¡PEGAMOS!** El {a['Fecha Sorteo']}, **{a['Socio']}** pegó {a['Aciertos']} números: {a['Números']}")
    else:
        st.info("Radar limpio. Esperando el próximo sorteo para validar las matrices.")

# --- PESTAÑAS ---
t1, t2, t3 = st.tabs(["🤝 Sindicato Colectivo", "📂 Historial Inmortal", "📊 Caja Negra"])

with t1:
    st.subheader("Generar para el Comité")
    nombres = st.text_input("Nombres de Socios (ej: Tommy, Carlos, Juan)", "Tommy")
    cant_jugadas = st.number_input("Jugadas por cada uno", 1, 10, 2)
    
    lista_socios = [n.strip() for n in nombres.split(",") if n.strip()]
    
    if st.button("🚀 Forjar y Guardar Matrices", use_container_width=True):
        total = len(lista_socios) * cant_jugadas
        df_nuevas = filtros.generar_predicciones(df_historial, total, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, True, [])
        
        # Asignar socios y preparar para Google Sheets
        filas_nuevas = []
        for i, socio in enumerate(lista_socios):
            sub_df = df_nuevas.iloc[i*cant_jugadas : (i+1)*cant_jugadas]
            st.markdown(f"#### 👤 Socio: {socio}")
            st.table(sub_df)
            
            for _, r in sub_df.iterrows():
                filas_nuevas.append([hoy_str, socio, r['Bola_1'], r['Bola_2'], r['Bola_3'], r['Bola_4'], r['Bola_5'], r['Bola_6'], r['Loto_Mas'], r['Super_Mas'], r['Suma']])
        
        # GUARDAR EN GOOGLE SHEETS
        if filas_nuevas:
            df_append = pd.DataFrame(filas_nuevas, columns=['Fecha Generada', 'Socio', 'Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas', 'Suma'])
            df_final = pd.concat([df_boveda, df_append], ignore_index=True)
            conn.update(spreadsheet=url_sheet, data=df_final)
            st.balloons()
            st.success("✅ ¡Jugadas guardadas para siempre en la Bóveda!")

with t2:
    st.subheader("📂 Registro Permanente")
    if not df_boveda.empty:
        st.dataframe(df_boveda.sort_values(by="Fecha Generada", ascending=False), use_container_width=True)
        st.download_button("📥 Descargar Respaldo CSV", df_boveda.to_csv(index=False), "historial_respaldo.csv")
    else:
        st.warning("La bóveda está vacía.")

with t3:
    st.subheader("Datos de la Tómbola")
    st.dataframe(df_historial.head(20), use_container_width=True)
