                            
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import extra_streamlit_components as stx

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Finanças de Luna", page_icon="💰", layout="wide")


# ==========================================
# 2. GERENCIAMENTO DE SESSÃO E LOGIN (365 DIAS)
# ==========================================
# Inicializa o gerenciador de cookies
cookie_manager = stx.get_cookie_manager()

# Defina aqui o usuário e senha desejados
USUARIO_CORRETO = "luna"
SENHA_CORRETA = "123456"

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if "transacoes" not in st.session_state:
    st.session_state["transacoes"] = []

# Verifica se existe o cookie de login no navegador
auth_cookie = cookie_manager.get(cookie="financas_luna_login")

if auth_cookie == "logado_sucesso":
    st.session_state["autenticado"] = True


# --- TELA DE LOGIN ---
if not st.session_state["autenticado"]:
    st.title("🔐 Finanças de Luna - Login")
    st.caption("Faça login para acessar o painel financeiro.")

    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        lembrar = st.checkbox("Manter conectado por 365 dias", value=True)
        btn_login = st.form_submit_button("Entrar", type="primary")

        if btn_login:
            if usuario == USUARIO_CORRETO and senha == SENHA_CORRETA:
                st.session_state["autenticado"] = True
                
                # Se marcar a opção, grava cookie válido por 365 dias
                if lembrar:
                    data_expiracao = datetime.now() + timedelta(days=365)
                    cookie_manager.set(
                        "financas_luna_login", 
                        "logado_sucesso", 
                        expires_at=data_expiracao
                    )
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    st.stop()  # Interrompe a execução aqui para quem não está logado


# ==========================================
# 3. BARRA LATERAL (CONFIGURAÇÕES E LOGOUT)
# ==========================================
with st.sidebar:
    st.header("⚙️ Configurações")
    st.subheader("Contas e Cartões")
    st.button("Adicionar Conta/Cartão")
    
    st.divider()
    st.header("Finanças de Luna")
    mes_selecionado = st.text_input("Visualizar Mês:", value="07/2026")
    
    st.divider()
    if st.button("🚪 Sair (Fazer Logout)"):
        st.session_state["autenticado"] = False
        cookie_manager.delete("financas_luna_login")
        st.rerun()


# ==========================================
# 4. PAINEL RESUMO (MÉTRICAS)
# ==========================================
st.title("💰 Finanças de Luna")

df_transacoes = pd.DataFrame(st.session_state["transacoes"])

if not df_transacoes.empty:
    total_receitas = df_transacoes[df_transacoes["tipo"] == "Receita"]["valor"].sum()
    total_despesas = df_transacoes[df_transacoes["tipo"] == "Despesa"]["valor"].sum()
else:
    total_receitas = 0.00
    total_despesas = 0.00

saldo = total_receitas - total_despesas

col_rec, col_desp, col_sal = st.columns(3)
col_rec.metric("Receitas", f"R$ {total_receitas:,.2f}")
col_desp.metric("Despesas", f"R$ {total_despesas:,.2f}")
col_sal.metric("Saldo", f"R$ {saldo:,.2f}")

st.divider()


# ==========================================
# 5. LANÇAMENTO MANUAL DE TRANSAÇÕES
# ==========================================
st.subheader("✍️ Adicionar Lançamento Manual")

with st.form("form_manual", clear_on_submit=True):
    col_desc, col_val, col_tipo, col_data = st.columns([3, 2, 2, 2])
    desc = col_desc.text_input("Descrição")
    val = col_val.number_input("Valor (R$)", min_value=0.0, step=0.01)
    tipo = col_tipo.selectbox("Tipo", ["Despesa", "Receita"])
    dt = col_data.date_input("Data", value=datetime.today())
    
    btn_salvar_manual = st.form_submit_button("➕ Adicionar Lançamento", type="primary")
    if btn_salvar_manual and desc and val > 0:
        st.session_state["transacoes"].append({
            "descricao": desc,
            "valor": val,
            "tipo": tipo,
            "data": dt.strftime("%Y-%m-%d")
        })
        st.success("Lançamento adicionado com sucesso!")
        st.rerun()

st.divider()


# ==========================================
# 6. HISTÓRICO DE TRANSAÇÕES
# ==========================================
st.subheader("📊 Histórico de Transações")
if not df_transacoes.empty:
    st.dataframe(df_transacoes, use_container_width=True)
else:
    st.info("Nenhuma transação cadastrada até o momento.")
