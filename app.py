import streamlit as st
import pandas as pd
import modulos.scraper as scraper
import modulos.fisica_filtros as filtros

st.set_page_config(page_title="Leidsa Analyzer", page_icon="🎯", layout="wide")

st.title("🎯 Analizador Estadístico Loto Leidsa")
st.markdown("### Motor de Análisis por Desgaste Físico y Filtros Matemáticos")
st.divider()

df_historial = scraper.cargar_datos()

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
    rango_suma = st.slider("Límites de Suma (Campana Gauss)", 21, 213, (80, 150))
    filtro_terminaciones = st.checkbox("Descartar 3 terminaciones iguales", value=True)
    filtro_pares = st.checkbox("Descartar matrices 100% pares/impares", value=True)
    
    # LOS NUEVOS FILTROS EN EL PANEL
    st.markdown("**Filtros Avanzados**")
    filtro_consecutivos = st.checkbox("Descartar 3 números consecutivos (Ej: 4,5,6)", value=True)
    filtro_historico = st.checkbox("Descartar jugadas pasadas (Anti-Clones)", value=True, help="Evita generar combinaciones exactas que ya salieron en el historial.")
    
    st.divider()
    
    if st.button("🚀 Generar Jugadas Óptimas", type="primary", use_container_width=True):
        st.session_state['generar'] = True

# --- PANTALLA PRINCIPAL ---
tab1, tab2 = st.tabs(["📊 Análisis del Historial y Gráficos", "🧠 Matrices Sugeridas"])

with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Caja Negra")
        if not df_historial.empty:
            st.dataframe(df_historial.head(50), use_container_width=True, hide_index=True)
            st.caption(f"Total de sorteos en la bóveda: {len(df_historial)}")
        else:
            st.warning("La base de datos está vacía.")
            
    with col2:
        st.subheader("🔥 Mapa de Calor Físico (Era Moderna: 40 Bolos)")
        if not df_historial.empty:
            df_frec = filtros.analizar_frecuencias(df_historial)
            if not df_frec.empty:
                top_5 = df_frec.sort_values(by='Apariciones', ascending=False).head(5)
                bolas_top = " - ".join(top_5['Bola'].tolist())
                st.info(f"**Top 5 Bolas Más Calientes Ahora Mismo:** {bolas_top}")
                st.bar_chart(df_frec.set_index('Bola')['Apariciones'], color="#FF4B4B")
                st.caption("Picos altos indican bolas con mayor probabilidad de desgaste físico o tendencia mecánica.")
            else:
                st.warning("Aún no hay suficientes sorteos desde marzo 2024 para mostrar el mapa.")

with tab2:
    st.subheader("Sugerencias Basadas en Tendencias Reales")
    if st.session_state.get('generar'):
        if not df_historial.empty:
            with st.spinner("Escaneando bóveda, esquivando clones y aplicando guillotina matemática..."):
                df_optimas = filtros.generar_jugadas_optimas(
                    df_historial=df_historial,
                    cantidad=5,
                    rango_suma=rango_suma,
                    descartar_pares=filtro_pares,
                    descartar_terminaciones=filtro_terminaciones,
                    descartar_consecutivos=filtro_consecutivos, # Se inyecta el nuevo filtro
                    descartar_historico=filtro_historico        # Se inyecta el nuevo filtro
                )
                st.success("¡Listo! Estas matrices purificadas sobrevivieron a todos los filtros:")
                st.dataframe(df_optimas, use_container_width=True, hide_index=True)
        else:
            st.error("Necesitas historial en la Caja Negra para generar predicciones.")
    else:
        st.info("Ajusta los parámetros en el panel izquierdo y presiona **Generar Jugadas Óptimas**.")