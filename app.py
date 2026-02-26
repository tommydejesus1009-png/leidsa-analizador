import streamlit as st
import pandas as pd
import datetime
import pytz
import os
from streamlit_gsheets import GSheetsConnection
import modulos.scraper as scraper
import modulos.fisica_filtros as filtros

st.set_page_config(page_title="Leidsa Analyzer PRO v6.0", page_icon="🎯", layout="wide")

# --- CONEXIÓN A LA BÓVEDA INMORTAL (Google Sheets) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_sheet = st.secrets["GSHEET_URL"]
    df_boveda = conn.read(spreadsheet=url_sheet)
    df_boveda.columns = [c.strip() for c in df_boveda.columns]
except Exception as e:
    st.error("⚠️ Error de conexión con Google Sheets. Verifica el enlace en Secrets.")
    df_boveda = pd.DataFrame()

st.title("🎯 Centro de Mando: Leidsa Analyzer")
st.markdown("### Motor de Análisis Físico + Sindicato + Bóveda Inmortal")
st.divider()

tz_rd = pytz.timezone('America/Santo_Domingo')
hoy_rd = datetime.datetime.now(tz_rd)
hoy_str = hoy_rd.strftime("%Y-%m-%d")

# Carga de datos oficiales
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
    filtro_historico = st.checkbox("Filtro Anti-Clones (No repetir sorteos ganadores)", value=True)

# --- EL ORÁCULO: RADAR DE IMPACTOS ---
if not df_historial.empty and not df_boveda.empty:
    st.subheader("👁️ El Oráculo: Radar de Aciertos")
    # Comparamos con el historial real
    aciertos_detectados = []
    cols_bolas = ['Bola_1', 'Bola_2', 'Bola_3', 'Bola_4', 'Bola_5', 'Bola_6']
    
    if all(c in df_boveda.columns for c in cols_bolas):
        for _, mi_j in df_boveda.iterrows():
            try:
                mis_nums = {int(mi_j['Bola_1']), int(mi_j['Bola_2']), int(mi_j['Bola_3']), 
                            int(mi_j['Bola_4']), int(mi_j['Bola_5']), int(mi_j['Bola_6'])}
                
                # Sorteos ocurridos después de generar la jugada
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
            st.info("El radar está activo. Aún no hay aciertos de 3+ números en tus jugadas guardadas.")
    st.divider()

# --- SISTEMA DE PESTAÑAS ---
tab1, tab2, tab3, tab4 = st.tabs(["🔮 Jugador Individual", "🤝 Sindicato Colectivo", "📂 Bóveda e Historial", "📊 Análisis y Caja Negra"])

with tab1:
    st.subheader("Modo Francotirador")
    if st.button("🚀 Generar 5 Jugadas para Tommy", use_container_width=True):
        with st.spinner("Procesando..."):
            df_nuevas = filtros.generar_predicciones(df_historial, 5, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, filtro_historico, [])
            
            filas_nuevas = []
            for _, r in df_nuevas.iterrows():
                filas_nuevas.append([hoy_str, "Tommy", r['Bola_1'], r['Bola_2'], r['Bola_3'], r['Bola_4'], r['Bola_5'], r['Bola_6'], r['Loto_Mas'], r['Super_Mas'], r['Suma']])
            
            df_append = pd.DataFrame(filas_nuevas, columns=df_boveda.columns)
            df_final = pd.concat([df_boveda, df_append], ignore_index=True)
            conn.update(spreadsheet=url_sheet, data=df_final)
            
            st.table(df_nuevas)
            st.balloons()
            st.success("✅ Jugadas guardadas en Google Sheets.")

with tab2:
    st.subheader("Sindicato de Socios")
    nombres_in = st.text_input("Nombres (Tommy, Socio1, Socio2...)", "Tommy, Amigo")
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
        
        df_append = pd.DataFrame(filas_sindicato, columns=df_boveda.columns)
        df_final = pd.concat([df_boveda, df_append], ignore_index=True)
        conn.update(spreadsheet=url_sheet, data=df_final)
        st.success("✅ Bloque completo guardado en la Bóveda.")

with tab3:
    st.subheader("📂 Bóveda Histórica y Resaltado")
    if not df_boveda.empty:
        def estilo_aciertos(row):
            # Lógica para resaltar dorado y rojo (Matriz Quemada)
            f_gen = str(row['Fecha Generada']).split(' ')[0]
            sorteos_validos = df_historial[df_historial['Fecha'] >= f_gen]
            if sorteos_validos.empty: return [''] * len(row)
            
            estilos = [''] * len(row)
            for _, sorteo in sorteos_validos.iterrows():
                ganadores = {int(sorteo[c]) for c in cols_bolas}
                aciertos = 0
                for i, col in enumerate(row.index):
                    if col in cols_bolas and int(row[col]) in ganadores:
                        estilos[i] = 'background-color: #FFD700; color: black; font-weight: bold'
                        aciertos += 1
                if aciertos == 6:
                    return ['background-color: #FF4B4B; color: white; font-weight: bold'] * len(row)
            return estilos

        df_styled = df_boveda.sort_values(by="Fecha Generada", ascending=False).style.apply(estilo_aciertos, axis=1)
        st.dataframe(df_styled, use_container_width=True)
        st.caption("🟡 Dorado: Acierto | 🔴 Rojo: Matriz Quemada (6 números)")
    else:
        st.info("Bóveda vacía.")

with tab4:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📊 Mapa de Calor")
        if not df_historial.empty:
            df_frec = filtros.analizar_frecuencias(df_historial)
            st.bar_chart(df_frec.set_index('Bola'))
    with c2:
        st.subheader("📜 Historial Real Leidsa")
        st.dataframe(df_historial.head(30), hide_index=True)
