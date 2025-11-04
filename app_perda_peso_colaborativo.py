import streamlit as st
import pandas as pd
import os
from datetime import datetime

# =========================
# CONFIGURAÇÕES INICIAIS
# =========================
st.set_page_config(page_title="Desafio 10kg", layout="wide")

# Diretórios de dados
DATA_DIR = "data"
UPLOAD_DIR = "uploads"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "usuarios.csv")
PESOS_FILE = os.path.join(DATA_DIR, "pesos.csv")

# =========================
# CRIAÇÃO DE ARQUIVOS INICIAIS
# =========================
def ensure_storage():
    if not os.path.exists(USERS_FILE):
        df_users = pd.DataFrame(columns=["usuario", "senha", "moderador"])
        usuarios = [
            {"usuario": "Luan", "senha": "240519", "moderador": True},
            {"usuario": "Jaqueline", "senha": "1234", "moderador": False},
            {"usuario": "Mara", "senha": "1234", "moderador": False},
            {"usuario": "Mateus", "senha": "1234", "moderador": False},
            {"usuario": "Rebeca", "senha": "1234", "moderador": False},
            {"usuario": "Tainara", "senha": "1234", "moderador": False},
        ]
        df_users = pd.concat([df_users, pd.DataFrame(usuarios)], ignore_index=True)
        df_users.to_csv(USERS_FILE, index=False)

    if not os.path.exists(PESOS_FILE):
        df_pesos = pd.DataFrame(columns=["usuario", "data", "peso", "foto"])
        df_pesos.to_csv(PESOS_FILE, index=False)

ensure_storage()

# =========================
# FUNÇÕES AUXILIARES
# =========================
def load_users():
    return pd.read_csv(USERS_FILE)

def load_pesos():
    return pd.read_csv(PESOS_FILE)

def save_pesos(df):
    df.to_csv(PESOS_FILE, index=False)

# =========================
# LOGIN
# =========================
def login():
    st.sidebar.title("Login")
    usuario = st.sidebar.text_input("Usuário")
    senha = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        users = load_users()
        match = users[(users["usuario"] == usuario) & (users["senha"] == senha)]
        if not match.empty:
            st.session_state["usuario"] = usuario
            st.session_state["moderador"] = match["moderador"].values[0]
            st.sidebar.success(f"Bem-vindo(a), {usuario}!")
        else:
            st.sidebar.error("Usuário ou senha incorretos!")

# =========================
# PÁGINA PRINCIPAL
# =========================
def app():
    st.title("🏋️ Desafio dos 10kg - Controle de Peso")

    usuario = st.session_state["usuario"]
    moderador = st.session_state["moderador"]

    df_pesos = load_pesos()

    # Registro de novo peso
    st.subheader("📥 Registrar peso")
    peso = st.number_input("Seu peso atual (kg):", min_value=0.0, step=0.1)
    foto = st.file_uploader("Foto da balança (opcional):", type=["png", "jpg", "jpeg"])

    if st.button("Salvar peso"):
        if peso > 0:
            caminho_foto = ""
            if foto:
                caminho_foto = os.path.join(UPLOAD_DIR, f"{usuario}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                with open(caminho_foto, "wb") as f:
                    f.write(foto.read())

            novo_peso = pd.DataFrame([{
                "usuario": usuario,
                "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "peso": peso,
                "foto": caminho_foto
            }])
            df_pesos = pd.concat([df_pesos, novo_peso], ignore_index=True)
            save_pesos(df_pesos)
            st.success("Peso registrado com sucesso!")
        else:
            st.warning("Informe um peso válido!")

    st.divider()

    # =========================
    # DEMONSTRATIVO GERAL
    # =========================
    st.subheader("📊 Demonstrativo Geral")

    if df_pesos.empty:
        st.info("Ainda não há registros de peso.")
        return

    df_ultimos = df_pesos.sort_values("data").groupby("usuario").last().reset_index()
    df_primeiros = df_pesos.sort_values("data").groupby("usuario").first().reset_index()

    df_merge = pd.merge(df_primeiros[["usuario", "peso"]], df_ultimos[["usuario", "peso"]], on="usuario", suffixes=("_inicio", "_atual"))
    df_merge["perda_kg"] = df_merge["peso_inicio"] - df_merge["peso_atual"]
    df_merge["meta_kg"] = 10
    df_merge["porcentagem"] = (df_merge["perda_kg"] / df_merge["meta_kg"]) * 100
    df_merge["porcentagem"] = df_merge["porcentagem"].clip(lower=0)

    df_ranking = df_merge.sort_values("perda_kg", ascending=False).reset_index(drop=True)

    # 🏆 Adicionar coroa ao primeiro lugar
    if not df_ranking.empty:
        df_ranking.loc[0, "usuario"] = "👑 " + df_ranking.loc[0, "usuario"]

    st.dataframe(
        df_ranking[["usuario", "peso_inicio", "peso_atual", "perda_kg", "meta_kg", "porcentagem"]],
        use_container_width=True,
        hide_index=True
    )

    # =========================
    # TABELA COMPLETA EXPANDÍVEL
    # =========================
    with st.expander("📅 Ver histórico completo"):
        st.dataframe(df_pesos.sort_values("data", ascending=False), use_container_width=True)

# =========================
# EXECUÇÃO
# =========================
if "usuario" not in st.session_state:
    login()
else:
    app()
