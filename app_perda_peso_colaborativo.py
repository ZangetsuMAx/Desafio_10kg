# app_perda_peso_colaborativo.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import io
from openpyxl import Workbook

# -----------------------
# Configurações iniciais
# -----------------------
st.set_page_config(page_title="Desafio 10kg - Colaborativo", layout="wide")
DATA_DIR = "data"
UPLOAD_DIR = "uploads"
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
PESOS_FILE = os.path.join(DATA_DIR, "pesos.csv")
META_KG = 10.0

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -----------------------
# Função: garante usuários iniciais e arquivos
# -----------------------
def ensure_users_file():
    users_default = [
        {"username": "Luan", "password": "240519", "role": "moderator"},
        {"username": "Jaqueline", "password": "jaqueline", "role": "user"},
        {"username": "Mara", "password": "mara", "role": "user"},
        {"username": "Mateus", "password": "mateus", "role": "user"},
        {"username": "Rebeca", "password": "rebeca", "role": "user"},
        {"username": "Tainara", "password": "tainara", "role": "user"}
    ]
    # Cria arquivo users se não existir ou estiver vazio; garante que todos default existam
    if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) == 0:
        df_users = pd.DataFrame(users_default)
        df_users.to_csv(USERS_FILE, index=False)
    else:
        try:
            df_users = pd.read_csv(USERS_FILE)
        except Exception:
            df_users = pd.DataFrame(columns=["username", "password", "role"])
        # adicionar faltantes
        for u in users_default:
            if u["username"] not in df_users.get("username", []).astype(str).values:
                df_users = pd.concat([df_users, pd.DataFrame([u])], ignore_index=True)
        df_users.to_csv(USERS_FILE, index=False)

def ensure_pesos_file():
    if not os.path.exists(PESOS_FILE) or os.path.getsize(PESOS_FILE) == 0:
        df = pd.DataFrame(columns=["username", "datetime", "peso", "foto_path"])
        df.to_csv(PESOS_FILE, index=False)

ensure_users_file()
ensure_pesos_file()

# -----------------------
# Auxiliares: carregar / salvar
# -----------------------
def load_users():
    try:
        return pd.read_csv(USERS_FILE)
    except Exception:
        return pd.DataFrame(columns=["username", "password", "role"])

def load_pesos():
    try:
        df = pd.read_csv(PESOS_FILE)
        if not df.empty:
            # garantir tipos
            df["peso"] = pd.to_numeric(df["peso"], errors="coerce")
            df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame(columns=["username", "datetime", "peso", "foto_path"])

def save_pesos(df):
    df.to_csv(PESOS_FILE, index=False)

# -----------------------
# Autenticação simples
# -----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

st.sidebar.title("Login")
if not st.session_state.logged_in:
    input_user = st.sidebar.text_input("Usuário")
    input_pass = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        users = load_users()
        match = users[(users["username"] == str(input_user)) & (users["password"] == str(input_pass))]
        if not match.empty:
            st.session_state.logged_in = True
            st.session_state.username = str(input_user)
            st.session_state.role = match.iloc[0]["role"]
            st.sidebar.success(f"Logado como {st.session_state.username} ({st.session_state.role})")
            st.experimental_rerun()
        else:
            st.sidebar.error("Usuário ou senha incorretos!")
    st.sidebar.markdown("---")
    st.sidebar.info("Usuários pré-criados: Luan (moderador) e os demais. Peça a senha se precisar.")
else:
    st.sidebar.markdown(f"**Conectado:** {st.session_state.username} — {st.session_state.role}")
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.experimental_rerun()

# -----------------------
# Função: adicionar pesagem
# -----------------------
def add_pesagem(username, peso, foto_file):
    df = load_pesos()
    tnow = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    foto_path = ""
    if foto_file is not None:
        ext = os.path.splitext(foto_file.name)[1]
        safe = f"{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        foto_path = os.path.join(UPLOAD_DIR, safe)
        with open(foto_path, "wb") as f:
            f.write(foto_file.getbuffer())
    novo = pd.DataFrame([{
        "username": username,
        "datetime": tnow,
        "peso": float(peso),
        "foto_path": foto_path
    }])
    df = pd.concat([df, novo], ignore_index=True)
    save_pesos(df)

def delete_record(index):
    df = load_pesos()
    if 0 <= index < len(df):
        foto = df.loc[index, "foto_path"]
        if isinstance(foto, str) and foto and os.path.exists(foto):
            try:
                os.remove(foto)
            except Exception:
                pass
        df = df.drop(index).reset_index(drop=True)
        save_pesos(df)
        return True
    return False

# -----------------------
# Página principal (após login)
# -----------------------
st.title("🏋️ Desafio 10kg — App Colaborativo")

if not st.session_state.logged_in:
    st.info("Faça login pelo painel lateral para registrar sua pesagem.")
    st.stop()

# Carregar dados
df_pesos = load_pesos()
users_df = load_users()
all_usernames = users_df["username"].astype(str).tolist()

# Area de registro (apenas para usuário logado)
st.header("📥 Registrar nova pesagem (apenas você pode adicionar suas pesagens)")
with st.form("form_peso", clear_on_submit=True):
    peso_val = st.number_input("Peso (kg)", min_value=0.0, format="%.2f")
    foto = st.file_uploader("Foto da balança (opcional)", type=["png", "jpg", "jpeg"])
    submitted = st.form_submit_button("Salvar pesagem")
    if submitted:
        if peso_val <= 0:
            st.warning("Informe um peso válido maior que 0.")
        else:
            add_pesagem(st.session_state.username, peso_val, foto)
            st.success("Pesagem salva.")
            st.experimental_rerun()

st.markdown("---")

# Se não existem registros, avisar
if df_pesos.empty:
    st.info("Ainda não há registros. Ao registrar a primeira pesagem, os demonstrativos aparecerão aqui.")
else:
    # Garantir tipos e ordenar
    df_pesos["datetime"] = pd.to_datetime(df_pesos["datetime"], errors="coerce")
    df_pesos = df_pesos.sort_values(["username", "datetime"], ascending=[True, True]).reset_index(drop=True)

    # Construir demonstrativo por usuário: primeira e última pesagem
    rows = []
    usernames = sorted(set(all_usernames + df_pesos["username"].astype(str).unique().tolist()))
    for u in usernames:
        df_u = df_pesos[df_pesos["username"] == u].sort_values("datetime")
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
    # ordenar ranking por kg_lost desc (NaN por último)
    demo_df["kg_lost_sort"] = demo_df["kg_lost"].fillna(-99999)
    ranking_df = demo_df.sort_values("kg_lost_sort", ascending=False).reset_index(drop=True)
    ranking_df = ranking_df.drop(columns=["kg_lost_sort"])

    # Se houver pelo menos 1 com valor, adicionar coroa no primeiro
    if not ranking_df.empty and pd.notna(ranking_df.loc[0, "kg_lost"]):
        ranking_df.loc[0, "display_name"] = "👑 " + ranking_df.loc[0, "username"]
    else:
        ranking_df["display_name"] = ranking_df["username"]

    # Mostrar ranking em expander
    with st.expander("🏆 Ranking — clique para expandir"):
        st.subheader("Top — quem mais perdeu (kg)")
        # mostrar top resumo
        top = ranking_df.head(10)
        for i, r in top.iterrows():
            name = r["display_name"]
            kg = r["kg_lost"]
            pct = r["pct_meta"]
            if pd.isna(kg):
                kg_text = "—"
                pct_text = "—"
            else:
                kg_text = f"{kg:.2f} kg"
                pct_text = f"{pct:.1f}%"
            st.markdown(f"- **{name}** — {kg_text} — {pct_text}")

        st.markdown("---")
        st.markdown("#### Ranking completo (detalhado)")
        show_df = ranking_df[["username", "first", "last", "kg_lost", "pct_meta"]].rename(columns={
            "username": "Nome",
            "first": "Primeira Pesagem",
            "last": "Última Pesagem",
            "kg_lost": "Kg Perdidos",
            "pct_meta": "% da Meta (10kg)"
        })
        st.dataframe(show_df.style.format({
            "Primeira Pesagem": "{:.2f}",
            "Última Pesagem": "{:.2f}",
            "Kg Perdidos": "{:.2f}",
            "% da Meta (10kg)": "{:.1f}%"
        }), use_container_width=True)

    st.markdown("---")

    # Mostrar histórico completo (todos podem ver)
    st.subheader("📋 Histórico de todas as pesagens (visível para todos)")
    df_show = df_pesos.sort_values("datetime", ascending=False).reset_index(drop=True)
    display_df = df_show.copy()
    display_df["datetime"] = display_df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    display_df = display_df.rename(columns={"username": "Nome", "datetime": "Data/Hora", "peso": "Peso (kg)", "foto_path": "Foto (caminho)"})
    st.dataframe(display_df, use_container_width=True)

    # Se for moderador: painel para apagar registros
    if st.session_state.role == "moderator":
        st.markdown("---")
        st.subheader("⚙️ Painel do Moderador")
        st.write("Apague registros problemáticos (informe o índice da tabela acima).")
        idx = st.number_input("Índice do registro (0 = primeiro da tabela mostrada)", min_value=0, value=0, step=1)
        if st.button("Apagar registro selecionado"):
            success = delete_record(int(idx))
            if success:
                st.success("Registro apagado.")
                st.experimental_rerun()
            else:
                st.error("Índice inválido.")

    st.markdown("---")

    # Painel pessoal do usuário logado
    st.subheader("👤 Seu histórico e evolução")
    df_user = df_pesos[df_pesos["username"] == st.session_state.username].sort_values("datetime")
    if df_user.empty:
        st.info("Você ainda não registrou pesagens.")
    else:
        # Mostrar tabela pessoal
        personal = df_user.copy()
        personal["datetime"] = personal["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
        personal = personal.rename(columns={"datetime": "Data/Hora", "peso": "Peso (kg)", "foto_path": "Foto (caminho)"})
        st.table(personal[["Data/Hora", "Peso (kg)", "Foto (caminho)"]])

        # Mostrar fotos em miniaturas
        st.write("Fotos registradas (clique para ampliar):")
        cols = st.columns(3)
        for idx, row in df_user.reset_index(drop=True).iterrows():
            path = row.get("foto_path", "")
            if isinstance(path, str) and path and os.path.exists(path):
                with cols[idx % 3]:
                    st.image(path, caption=row["datetime"].strftime("%Y-%m-%d %H:%M:%S"), use_column_width=True)

        # Calcular evolução pessoal: first / last / kg lost / %
        first = float(df_user.iloc[0]["peso"])
        last = float(df_user.iloc[-1]["peso"])
        kg_lost = first - last
        pct_meta = (kg_lost / META_KG) * 100
        st.markdown(f"**Kg perdidos:** {kg_lost:.2f} kg")
        st.markdown(f"**% da meta (10 kg):** {pct_meta:.1f}%")

# -----------------------
# Exportar consolidado (qualquer um pode baixar)
# -----------------------
st.markdown("---")
st.write("📥 Exportar dados (planilha Excel com todos os registros e demonstrativo)")
if st.button("Gerar e baixar .xlsx"):
    df_export = load_pesos().sort_values(["username", "datetime"])
    # criar excel em memória
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Pesagens"
    ws1.append(["Nome", "Data/Hora", "Peso (kg)", "Foto (caminho)"])
    for _, r in df_export.iterrows():
        dt = r["datetime"]
        if pd.notna(dt):
            try:
                dt_str = pd.to_datetime(dt).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                dt_str = str(dt)
        else:
            dt_str = ""
        ws1.append([r["username"], dt_str, float(r["peso"]), r.get("foto_path", "")])

    # demonstrativo
    demo_ws = wb.create_sheet("Demonstrativo")
    demo_ws.append(["Nome", "Primeira Pesagem", "Última Pesagem", "Kg Perdidos", "% da Meta (10kg)"])
    for _, r in ranking_df.iterrows():
        demo_ws.append([
            r["username"],
            r["first"] if pd.notna(r["first"]) else "",
            r["last"] if pd.notna(r["last"]) else "",
            r["kg_lost"] if pd.notna(r["kg_lost"]) else "",
            r["pct_meta"] if pd.notna(r["pct_meta"]) else ""
        ])

    bio = io.BytesIO()
    wb.save(bio)
    st.download_button("📥 Baixar Excel consolidado", data=bio.getvalue(), file_name="controle_peso_consolidado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Fim do app
