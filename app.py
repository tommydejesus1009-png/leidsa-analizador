import streamlit as st
import pandas as pd
import datetime
import pytz
import os
from streamlit_gsheets import GSheetsConnection
import modulos.scraper as scraper
import modulos.fisica_filtros as filtros

st.set_page_config(page_title="Leidsa Analyzer PRO v6.5", page_icon="🎯", layout="wide")

# --- DEFINICIÓN ESTRICTA DE COLUMNAS (Para evitar el ValueError) ---
COLS_BOVEDA = ['Fecha Generada', 'Socio', 'Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6', 'Loto_Mas', 'Super_Mas', 'Suma']

# --- CONEXIÓN A LA BÓVEDA INMORTAL (Google Sheets) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_sheet = st.secrets["GSHEET_URL"]
    df_raw = conn.read(spreadsheet=url_sheet)
    
    # Limpiamos nombres y filtramos solo las columnas que necesitamos
    df_raw.columns = [c.strip() for c in df_raw.columns]
    # Si la hoja tiene columnas de más, las ignoramos. Si le faltan, las crea vacías.
    df_boveda = df_raw.reindex(columns=COLS_BOVEDA)
except Exception as e:
    st.error(f"⚠️ Error de conexión con Google Sheets: {e}")
    df_boveda = pd.DataFrame(columns=COLS_BOVEDA)

st.title("🎯 Centro de Mando: Leidsa Analyzer")
st.markdown("### Motor de Análisis Físico + Sindicato + Bóveda Inmortal")
st.divider()

tz_rd = pytz.timezone('America/Santo_Domingo')
hoy_rd = datetime.datetime.now(tz_rd)
hoy_str = hoy_rd.strftime("%Y-%m-%d")

# Carga de datos oficiales (Scraper)
df_historial = scraper.cargar_datos()

# --- PANEL LATERAL: CONFIGURACIÓN Y FILTROS ---
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
    filtro_historico = st.checkbox("Filtro Anti-Clones (No repetir ganadores pasados)", value=True)
    st.caption("Nota: El filtro Anti-Clones descarta automáticamente cualquier combinación que ya haya ganado los 6 números en la historia real de Leidsa.")

# --- EL ORÁCULO: RADAR DE IMPACTOS (Aciertos de 3 o más) ---
if not df_historial.empty and not df_boveda.empty:
    st.subheader("👁️ El Oráculo: Radar de Aciertos")
    aciertos_detectados = []
    
    # Revisamos cada jugada en nuestra bóveda contra los sorteos reales
    for _, mi_j in df_boveda.dropna(subset=['Bola_1']).iterrows():
        try:
            mis_nums = {int(mi_j['Bola_1']), int(mi_j['Bola_2']), int(mi_j['Bola_3']), 
                        int(mi_j['Bola_4']), int(mi_j['Bola_5']), int(mi_j['Bola_6'])}
            
            # Solo comparamos con sorteos desde la fecha en que se generó la jugada
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
        st.info("Radar vigilando... Sin aciertos de 3 o más números detectados recientemente.")
    st.divider()

# --- SISTEMA DE PESTAÑAS (TODAS LAS FUNCIONES) ---
tab1, tab2, tab3, tab4 = st.tabs(["🔮 Jugador Individual", "🤝 Sindicato Colectivo", "📂 Bóveda e Historial", "📊 Análisis y Caja Negra"])

with tab1:
    st.subheader("Modo Francotirador (Individual)")
    if st.button("🚀 Generar 5 Jugadas para Tommy", use_container_width=True):
        with st.spinner("Procesando matrices..."):
            df_nuevas = filtros.generar_predicciones(df_historial, 5, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, filtro_historico, [])
            
            filas_nuevas = []
            for _, r in df_nuevas.iterrows():
                filas_nuevas.append([hoy_str, "Tommy", r['Bola_1'], r['Bola_2'], r['Bola_3'], r['Bola_4'], r['Bola_5'], r['Bola_6'], r['Loto_Mas'], r['Super_Mas'], r['Suma']])
            
            # Creamos el DataFrame con la estructura exacta de COLS_BOVEDA
            df_append = pd.DataFrame(filas_nuevas, columns=COLS_BOVEDA)
            df_final = pd.concat([df_boveda, df_append], ignore_index=True)
            conn.update(spreadsheet=url_sheet, data=df_final)
            
            st.table(df_nuevas)
            st.balloons()
            st.success("✅ Jugadas guardadas exitosamente en Google Sheets.")

with tab2:
    st.subheader("Sindicato de Socios")
    nombres_in = st.text_input("Nombres de Socios (Tommy, Carlos, Juan...)", "Tommy, Socio 1")
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
        
        # Guardado masivo con estructura protegida
        df_append = pd.DataFrame(filas_sindicato, columns=COLS_BOVEDA)
        df_final = pd.concat([df_boveda, df_append], ignore_index=True)
        conn.update(spreadsheet=url_sheet, data=df_final)
        st.success("✅ Bloque del sindicato registrado en la Bóveda.")

with tab3:
    st.subheader("📂 Bóveda Histórica (Google Sheets)")
    if not df_boveda.empty:
        # Función de Estilo para resaltar aciertos y "Quemadas"
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
                    if col in bolas_cols and int(row[col]) in ganadores:
                        estilos[i] = 'background-color: #FFD700; color: black; font-weight: bold' # Dorado
                        aciertos += 1
                
                if aciertos == 6: # MATRIZ QUEMADA
                    return ['background-color: #FF4B4B; color: white; font-weight: bold'] * len(row)
            return estilos

        df_styled = df_boveda.sort_values(by="Fecha Generada", ascending=False).style.apply(resaltar_resultados, axis=1)
        st.dataframe(df_styled, use_container_width=True)
        st.caption("🟡 Dorado: Número acertado | 🔴 Rojo: MATRIZ QUEMADA (Ya salió en Leidsa)")
    else:
        st.info("La bóveda está esperando tu primera jugada.")

with tab4:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📊 Mapa de Calor (Frecuencias)")
        if not df_historial.empty:
            df_frec = filtros.analizar_frecuencias(df_historial)
            st.bar_chart(df_frec.set_index('Bola'))
    with col_b:
        st.subheader("📜 Historial Real Leidsa")
        st.dataframe(df_historial.head(30), hide_index=True)
