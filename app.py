import streamlit as st

st.set_page_config(page_title="Leidsa Analyzer PRO", page_icon="🎯", layout="wide")

pg = st.navigation([
    st.Page("paginas/loto.py", title="Loto Leidsa", icon="🎯", default=True),
    st.Page("paginas/kino.py", title="Super Kino TV", icon="📺"),
])
pg.run()