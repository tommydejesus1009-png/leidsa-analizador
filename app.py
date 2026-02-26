import streamlit as st
import pandas as pd
import datetime
import pytz
import os
import modulos.scraper as scraper
import modulos.fisica_filtros as filtros

st.set_page_config(page_title="Leidsa Analyzer", page_icon="🎯", layout="wide")

st.title("🎯 Analizador Estadístico Loto Leidsa")
st.markdown("### Motor de Análisis por Desgaste Físico y Filtros Matemáticos")
st.divider()

tz_rd = pytz.timezone('America/Santo_Domingo')
hoy_rd = datetime.datetime.now(tz_rd)
hoy_str = hoy_rd.strftime("%Y-%m-%d")

df_historial = scraper.cargar_datos()

# Cargar la Bóveda de Jugadas Propias
ruta_boveda = os.path.join('data', 'mis_jugadas_generadas.csv')
df_mis_jugadas = pd.DataFrame()
jugadas_previas_sets = []

if os.path.exists(ruta_boveda):
    try:
        df_mis_jugadas = pd.read_csv(ruta_boveda)
        for _, row in df_mis_jugadas.iterrows():
            bolas = {row['Bola_1'], row['Bola_2'], row['Bola_3'], row['Bola_4'], row['Bola_5'], row['Bola_6']}
            jugadas_previas_sets.append(bolas)
    except: pass

# --- PANEL LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    st.subheader("1. Base de Datos")
    if st.button("🔄 Actualizar Último Sorteo", use_container_width=True):
        with st.spinner("Buscando en la web..."):
            exito, mensaje = scraper.actualizar_csv()
            if exito:
                st.success(mensaje)
                st.rerun() 
            else:
                st.error(mensaje)
    
    st.divider()
    
    st.subheader("2. Guillotina de Filtros")
    rango_suma = st.slider("Límite de Suma (Gauss)", 60, 180, (80, 150))
    descartar_pares = st.checkbox("Filtrar por Paridad", value=True)
    descartar_terminaciones = st.checkbox("Filtrar Terminaciones", value=True)
    descartar_consecutivos = st.checkbox("Filtrar Consecutivos", value=True)
    filtro_historico = st.checkbox("Filtro Anti-Clones (Leidsa)", value=True)
    filtro_propio = st.checkbox("Filtro Anti-Repetición Propia", value=True)

# --- ORÁCULO DE COLISIONES (Radar de Aciertos Exactos) ---
if not df_historial.empty and not df_mis_jugadas.empty:
    st.markdown("### 👁️ El Oráculo (Radar de Aciertos)")
    aciertos_encontrados = False
    
    for idx, mi_jugada in df_mis_jugadas.iterrows():
        mis_bolas = {mi_jugada['Bola_1'], mi_jugada['Bola_2'], mi_jugada['Bola_3'], mi_jugada['Bola_4'], mi_jugada['Bola_5'], mi_jugada['Bola_6']}
        fecha_gen = mi_jugada['Fecha Generada'].split(' ')[0]
        
        # Filtramos para comparar solo con sorteos que ocurrieron en la fecha de generación o después
        sorteos_validos = df_historial[df_historial['Fecha'] >= fecha_gen]
        
        for j, oficial in sorteos_validos.iterrows():
            bolas_oficiales = {oficial['Bola_1'], oficial['Bola_2'], oficial['Bola_3'], oficial['Bola_4'], oficial['Bola_5'], oficial['Bola_6']}
            numeros_pegados = mis_bolas.intersection(bolas_oficiales)
            
            # Avisar si pegó 3 números o más
            if len(numeros_pegados) >= 3:
                aciertos_encontrados = True
                if len(numeros_pegados) == 6:
                    st.error(f"🚨 **¡PREMIO MAYOR DETECTADO!** Pegaste los 6 números el {oficial['Fecha']}: {sorted(list(numeros_pegados))}")
                else:
                    st.success(f"🎯 **Acierto de {len(numeros_pegados)} números:** Sorteo del **{oficial['Fecha']}** | Tu jugada: {sorted(list(mis_bolas))} | **Pegaste: {sorted(list(numeros_pegados))}**")
                    
    if not aciertos_encontrados:
        st.info("El radar está vigilando. Aún no hay aciertos de 3 o más números en tus jugadas guardadas.")
    st.divider()

# --- SISTEMA DE PESTAÑAS ---
tab1, tab2, tab3, tab4 = st.tabs(["🔮 Jugador Solitario", "🤝 Sindicato Colectivo", "📂 Mis Jugadas", "📊 Análisis y Caja Negra"])

with tab1:
    st.subheader("Modo Francotirador (Individual)")
    st.markdown("Genera tus 5 jugadas clásicas protegidas por el candado diario.")
    
    ya_genero_hoy = False
    if not df_mis_jugadas.empty:
        df_hoy = df_mis_jugadas[df_mis_jugadas['Fecha Generada'].str.contains(hoy_str, na=False)]
        if not df_hoy.empty:
            ya_genero_hoy = True

    if ya_genero_hoy:
        st.warning(f"🔒 El motor detecta jugadas para hoy ({hoy_str}). Revisa tus pestañas.")
    else:
        if st.button("🚀 Generar 5 Jugadas Personales", use_container_width=True):
            if not df_historial.empty:
                with st.spinner("Procesando..."):
                    memoria = jugadas_previas_sets if filtro_propio else []
                    df_optimas = filtros.generar_predicciones(df_historial, 5, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, filtro_historico, memoria)
                    
                    df_guardar = df_optimas.copy()
                    df_guardar.insert(0, 'Fecha Generada', hoy_rd.strftime("%Y-%m-%d %H:%M:%S"))
                    
                    if not os.path.exists('data'): os.makedirs('data')
                    if os.path.exists(ruta_boveda):
                        df_guardar.to_csv(ruta_boveda, mode='a', header=False, index=False)
                    else:
                        df_guardar.to_csv(ruta_boveda, mode='w', header=True, index=False)
                    st.rerun()
            else:
                st.error("Faltan datos en la Caja Negra.")

with tab2:
    st.subheader("🤝 Sindicato de Jugadores")
    st.markdown("Crea bloques de jugadas y asígnalas por nombre a cada socio de tu comité.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        nombres_input = st.text_input("📝 Nombres de los Socios (separados por coma)", "Tommy, Socio 1, Socio 2")
    with col_b:
        jugadas_por_amigo = st.number_input("🎫 Jugadas por Socio", min_value=1, max_value=10, value=2)
        
    lista_nombres = [nombre.strip() for nombre in nombres_input.split(",") if nombre.strip()]
    num_amigos = len(lista_nombres)
    total_sindicato = num_amigos * jugadas_por_amigo
    
    if num_amigos > 0:
        st.info(f"🎯 El motor purificará **{total_sindicato} matrices** en total ({jugadas_por_amigo} para cada uno de los {num_amigos} socios).")
        
        if st.button("🚀 Generar Bloque para el Sindicato", use_container_width=True):
            if not df_historial.empty:
                with st.spinner("Forjando armadura colectiva..."):
                    memoria = jugadas_previas_sets if filtro_propio else []
                    df_optimas = filtros.generar_predicciones(df_historial, total_sindicato, rango_suma, descartar_pares, descartar_terminaciones, descartar_consecutivos, filtro_historico, memoria)
                    
                    df_guardar = df_optimas.copy()
                    df_guardar.insert(0, 'Fecha Generada', hoy_rd.strftime("%Y-%m-%d %H:%M:%S"))
                    
                    if not os.path.exists('data'): os.makedirs('data')
                    if os.path.exists(ruta_boveda):
                        df_guardar.to_csv(ruta_boveda, mode='a', header=False, index=False)
                    else:
                        df_guardar.to_csv(ruta_boveda, mode='w', header=True, index=False)
                    
                    st.success("¡Sindicato armado con éxito! Todas las jugadas están siendo vigiladas por el Oráculo.")
                    
                    # Proyectar las jugadas divididas con el nombre de cada socio
                    for i, nombre in enumerate(lista_nombres):
                        inicio = i * jugadas_por_amigo
                        fin = inicio + jugadas_por_amigo
                        df_amigo = df_optimas.iloc[inicio:fin].copy()
                        df_amigo = df_amigo.rename(columns={'Bola_1': 'B1', 'Bola_2': 'B2', 'Bola_3': 'B3', 'Bola_4': 'B4', 'Bola_5': 'B5', 'Bola_6': 'B6', 'Loto_Mas': 'Loto+', 'Super_Mas': 'Super+', 'Suma': 'Suma'})
                        
                        st.markdown(f"#### 👤 Matrices asignadas a: **{nombre}**")
                        st.table(df_amigo)
            else:
                st.error("Faltan datos en la Caja Negra.")
    else:
        st.warning("Por favor, escribe al menos un nombre en la lista.")

with tab3:
    st.subheader("📂 Tu Historial y Matrices de Hoy")
    st.markdown("Todas tus jugadas y las de tu sindicato están guardadas aquí.")
    if not df_mis_jugadas.empty:
        df_mostrar_historial = df_mis_jugadas.sort_values(by="Fecha Generada", ascending=False)
        st.dataframe(df_mostrar_historial, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no tienes jugadas guardadas en la bóveda.")

with tab4:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("📊 Mapa de Calor")
        if not df_historial.empty:
            df_frec = filtros.analizar_frecuencias(df_historial)
            if not df_frec.empty:
                st.bar_chart(df_frec.set_index('Bola'), use_container_width=True)
    with col2:
        st.subheader("📜 Historial Real Leidsa")
        if not df_historial.empty:
            st.dataframe(df_historial, use_container_width=True, hide_index=True)
