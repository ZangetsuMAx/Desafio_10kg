# app_perda_peso_colaborativo.py
import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime
import io

# ---------- CONFIG ----------
USERS_FILE = "users.csv"
PESAGENS_FILE = "pesagens.csv"
UPLOADS_DIR = "uploads"
META_KG = 10.0

# Pre-cadastrados: Luan = moderador (senha 240519), outros com senha '1234'
PRE_USERS = [
    {"username": "Jaqueline", "password": "1234", "is_admin": False},
    {"username": "Luan", "password": "240519", "is_admin": True},
    {"username": "Mara", "password": "1234", "is_admin": False},
    {"username": "Mateus", "password": "1234", "is_admin": False},
    {"username": "Rebeca", "password": "1234", "is_admin": False},
    {"username": "Tainara", "password": "1234", "is_admin": False},
]

# ---------- UTIL ----------

def hash_pw(plain: str) -> str:
    """Hash simples com sha256 (suficiente para este app pequeno)."""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()

def ensure_storage():
    """Garante existência de arquivos e pastas e cria usuários pré-cadastrados."""
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # criar users.csv se não existir
    if not os.path.exists(USERS_FILE):
        df_users = pd.DataFrame(columns=["username", "pw_hash", "is_admin"])
        for u in PRE_USERS:
            df_users = df_users.append({
                "username": u["username"],
                "pw_hash": hash_pw(u["password"]),
                "is_admin": bool(u["is_admin"])
            }, ignore_index=True)
        df_users.to_csv(USERS_FILE, index=False)

    # criar pesagens.csv se não existir
    if not os.path.exists(PESAGENS_FILE):
        df = pd.DataFrame(columns=["username", "datetime", "peso", "foto_path"])
        df.to_csv(PESAGENS_FILE, index=False)

def load_users():
    return pd.read_csv(USERS_FILE)

def load_pesagens():
    return pd.read_csv(PESAGENS_FILE)

def save_pesagens(df):
    df.to_csv(PESAGENS_FILE, index=False)

def check_login(username, password):
    users = load_users()
    match = users[users["username"] == username]
    if match.empty:
        return False, False
    pw_hash = hash_pw(password)
    if pw_hash == match.iloc[0]["pw_hash"]:
        return True, bool(match.iloc[0]["is_admin"])
    return False, False

def add_pesagem(username, peso, foto_file):
    df = load_pesagens()
    time_now = datetime.now().isoformat(timespec="seconds")
    foto_path = ""
    if foto_file is not None:
        ext = os.path.splitext(foto_file.name)[1]
        safe_name = f"{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        path = os.path.join(UPLOADS_DIR, safe_name)
        with open(path, "wb") as f:
            f.write(foto_file.getbuffer())
        foto_path = path
    df = df.append({"username": username, "datetime": time_now, "peso": float(peso), "foto_path": foto_path}, ignore_index=True)
    save_pesagens(df)

def delete_record(index):
    df = load_pesagens()
    if 0 <= index < len(df):
        # apagar foto (se houver)
        foto = df.loc[index, "foto_path"]
        if isinstance(foto, str) and foto and os.path.exists(foto):
            try:
                os.remove(foto)
            except:
                pass
        df = df.drop(index).reset_index(drop=True)
        save_pesagens(df)

# ---------- INICIALIZAÇÃO ----------
ensure_storage()

st.set_page_config(page_title="Controle de Peso Colaborativo", layout="wide")
st.markdown("# 🏋️ Controle de Peso - App Colaborativo")

# ---------- AUTENTICAÇÃO SIMPLES ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.is_admin = False

st.sidebar.header("Login")
if not st.session_state.logged_in:
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        ok, is_admin = check_login(username.strip(), password.strip())
        if ok:
            st.session_state.logged_in = True
            st.session_state.username = username.strip()
            st.session_state.is_admin = is_admin
            st.sidebar.success(f"Logado como {st.session_state.username} {'(moderador)' if is_admin else ''}")
            st.experimental_rerun()
        else:
            st.sidebar.error("Usuário/senha inválidos.")
    st.sidebar.write("---")
    st.sidebar.write("Se você não tem usuário, peça ao moderador para criar.")
else:
    st.sidebar.write(f"Conectado: **{st.session_state.username}**")
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.is_admin = False
        st.experimental_rerun()

# ---------- PÁGINA PRINCIPAL ----------
df_pes = load_pesagens()
# converter peso para numérico quando possível
if not df_pes.empty:
    df_pes["peso"] = pd.to_numeric(df_pes["peso"], errors="coerce")

# area para adicionar pesagem (só para logados)
if st.session_state.logged_in:
    st.subheader("➕ Registrar nova pesagem (apenas seu perfil)")
    with st.form("form_pesagem", clear_on_submit=True):
        peso = st.number_input("Peso (kg)", min_value=0.0, format="%.2f")
        foto = st.file_uploader("Foto da balança (opcional)", type=["png", "jpg", "jpeg"])
        submitted = st.form_submit_button("Salvar pesagem")
        if submitted:
            if peso <= 0:
                st.warning("Informe um peso válido maior que 0.")
            else:
                add_pesagem(st.session_state.username, peso, foto)
                st.success("Pesagem registrada!")
                st.experimental_rerun()
else:
    st.info("Faça login para registrar sua pesagem.")

# ---------- Processar dados para demonstrativo/ ranking ----------
# Se não houver registros ainda
if df_pes.empty:
    st.info("Ainda não há registros de pesagens. Assim que alguém registrar, aparecerão aqui.")
else:
    # transformar datetime
    df_pes["datetime"] = pd.to_datetime(df_pes["datetime"])
    # lista de usuários conhecidos (unir users.csv e quem registrou)
    users_df = load_users()
    user_list = sorted(set(list(users_df["username"]) + list(df_pes["username"].unique())))
    # construir demonstrativo agregando primeiros e ultimos
    rows = []
    for u in user_list:
        df_u = df_pes[df_pes["username"] == u].sort_values("datetime")
        if df_u.empty:
            first = None
            last = None
        else:
            first = float(df_u.iloc[0]["peso"])
            last = float(df_u.iloc[-1]["peso"])
        kg_lost = None
        pct_meta = None
        if (first is not None) and (last is not None):
            kg_lost = first - last
            pct_meta = (kg_lost / META_KG) * 100
        rows.append({
            "username": u,
            "first": first,
            "last": last,
            "kg_lost": kg_lost,
            "pct_meta": pct_meta
        })
    demo_df = pd.DataFrame(rows)
    # ordenar ranking por kg_lost desc (NaN para o final)
    demo_df["kg_lost_sort"] = demo_df["kg_lost"].fillna(-99999)
    ranking = demo_df.sort_values("kg_lost_sort", ascending=False).reset_index(drop=True)
    # remover a coluna auxiliar
    ranking = ranking.drop(columns=["kg_lost_sort"])

    # ---------- Ranking (expander) ----------
    with st.expander("🏆 Ranking - clique para expandir"):
        st.markdown("#### Top — quem mais perdeu (kg)")
        # exibir top 5 resumido com coroa
        topN = ranking.head(10)
        for i, r in topN.iterrows():
            nome = r["username"]
            kg = r["kg_lost"]
            pct = r["pct_meta"]
            if i == 0:
                display_name = f"👑 **{nome}**"
                st.markdown(f"- {display_name} — **{kg:.2f} kg** perdidos — {None if pd.isna(pct) else f'{pct:.1f}%'}")
            else:
                st.markdown(f"- {nome} — {'' if pd.isna(kg) else f'**{kg:.2f} kg**'} — {None if pd.isna(pct) else f'{pct:.1f}%'}")
        st.write("---")
        st.markdown("##### Ranking completo (detalhado)")
        # tabela completa com opção de expandir detalhes
        st.dataframe(ranking[["username", "first", "last", "kg_lost", "pct_meta"]].rename(columns={
            "username":"Nome", "first":"Primeira Pesagem", "last":"Última Pesagem", "kg_lost":"Kg Perdidos", "pct_meta":"% da Meta"
        }).style.format({
            "Primeira Pesagem": "{:.2f}",
            "Última Pesagem": "{:.2f}",
            "Kg Perdidos": "{:.2f}",
            "% da Meta": "{:.1f}%"
        }), use_container_width=True)

    # ---------- Mostrar tabela geral de registros (todos podem ver) ----------
    st.subheader("📋 Histórico de todas as pesagens (todos podem ver)")
    # exibir com fotos como links ou thumbnails
    df_show = df_pes.sort_values(["username", "datetime"], ascending=[True, True]).reset_index(drop=True)
    # mostrar índice para moderador poder apagar
    df_show_display = df_show.copy()
    df_show_display["datetime"] = df_show_display["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    st.dataframe(df_show_display[["username", "datetime", "peso", "foto_path"]].rename(columns={
        "username":"Nome", "datetime":"Data/Hora", "peso":"Peso (kg)", "foto_path":"Foto (caminho)"
    }), use_container_width=True)

    # Moderador: controle de exclusão
    if st.session_state.logged_in and st.session_state.is_admin:
        st.markdown("---")
        st.subheader("⚙️ Painel do Moderador")
        st.write("Apague registros problemáticos abaixo (informe o índice da tabela acima).")
        idx_to_del = st.number_input("Índice do registro (0 = primeiro)", min_value=0, value=0, step=1)
        if st.button("Apagar registro selecionado"):
            # confirmar
            delete_record(int(idx_to_del))
            st.success("Registro apagado (se o índice existia).")
            st.experimental_rerun()

    # ---------- Mostrar painel pessoal (histórico do usuário) ----------
    if st.session_state.logged_in:
        st.subheader("👤 Seu histórico e evolução")
        df_user = df_pes[df_pes["username"] == st.session_state.username].sort_values("datetime")
        if df_user.empty:
            st.info("Você ainda não registrou nenhuma pesagem.")
        else:
            # tabela pessoal
            st.table(df_user[["datetime", "peso", "foto_path"]].rename(columns={"datetime":"Data/Hora", "peso":"Peso (kg)", "foto_path":"Foto (caminho)"}).assign(**{
                "Data/Hora": df_user["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
            }))
            # mostrar fotos (pequenas)
            st.write("Fotos registradas (clique para ampliar):")
            cols = st.columns(3)
            for i, row in df_user.iterrows():
                path = row.get("foto_path", "")
                if isinstance(path, str) and path and os.path.exists(path):
                    with cols[i % 3]:
                        st.image(path, use_column_width=True, caption=f"{row['datetime'].strftime('%Y-%m-%d %H:%M:%S')}")
            # calcular evolução pessoal simples
            first = float(df_user.iloc[0]["peso"])
            last = float(df_user.iloc[-1]["peso"])
            kg_lost = first - last
            pct = (kg_lost / META_KG) * 100
            st.markdown(f"**Kg perdidos:** {kg_lost:.2f} kg")
            st.markdown(f"**% da meta (10 kg):** {pct:.1f}%")

# ---------- Exportar planilha consolidada (qualquer um pode baixar) ----------
st.markdown("---")
st.write("📥 Exportar dados (planilha Excel com todos os registros e demonstrativo)")
if st.button("Gerar e baixar .xlsx"):
    # criar excel em memória
    import openpyxl
    from openpyxl import Workbook
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Pesagens"
    # cabeçalho
    ws1.append(["Nome", "DataHora", "Peso (kg)", "Foto (caminho)"])
    df_export = df_pes.sort_values(["username", "datetime"])
    for _, r in df_export.iterrows():
        ws1.append([r["username"], r["datetime"].strftime("%Y-%m-%d %H:%M:%S"), float(r["peso"]), r.get("foto_path","")])
    # demonstrativo
    demo_ws = wb.create_sheet("Demonstrativo")
    demo_ws.append(["Nome", "Primeira Pesagem", "Última Pesagem", "Kg Perdidos", "% da Meta (10kg)"])
    for _, r in ranking.iterrows():
        demo_ws.append([
            r["username"],
            r["first"] if pd.notna(r["first"]) else "",
            r["last"] if pd.notna(r["last"]) else "",
            r["kg_lost"] if pd.notna(r["kg_lost"]) else "",
            r["pct_meta"] if pd.notna(r["pct_meta"]) else ""
        ])
    # salvar em bytes
    bio = io.BytesIO()
    wb.save(bio)
    st.download_button("📥 Baixar Excel", data=bio.getvalue(), file_name="controle_peso_consolidado.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
