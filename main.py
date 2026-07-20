import sqlite3
import tempfile
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import streamlit as st

st.set_page_config(page_title="Controle de Custos", page_icon="💰", layout="centered")

# Banco de dados persistente na pasta do projeto
DB_NAME = "controle_gastos_v4.db"

def inicializar_banco():
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            senha TEXT
        )
    """)
    cursor.execute("CREATE TABLE IF NOT EXISTS configuracoes (usuario TEXT, chave TEXT, valor TEXT, PRIMARY KEY (usuario, chave))")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            data TEXT,
            mes_ano TEXT,
            tipo TEXT,
            cartao TEXT,
            descricao TEXT,
            valor REAL,
            status TEXT,
            observacao TEXT
        )
    """)
    conexao.commit()
    conexao.close()

inicializar_banco()

# Gerenciamento de Sessão de Login
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

# --- TELA DE LOGIN / CADASTRO ---
if not st.session_state["usuario_logado"]:
    st.title("💰 Controle de Custos")
    
    aba1, aba2 = st.tabs(["🔑 Entrar", "📝 Cadastrar"])
    
    with aba1:
        u = st.text_input("Usuário", key="login_user")
        s = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar", type="primary", use_container_width=True):
            conexao = sqlite3.connect(DB_NAME)
            cursor = conexao.cursor()
            cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", (u.strip(), s.strip()))
            valido = cursor.fetchone()
            conexao.close()
            if valido:
                st.session_state["usuario_logado"] = u.strip()
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    with aba2:
        u_cad = st.text_input("Novo Usuário", key="cad_user")
        s_cad = st.text_input("Nova Senha", type="password", key="cad_pass")
        if st.button("Cadastrar", use_container_width=True):
            if u_cad and s_cad:
                try:
                    conexao = sqlite3.connect(DB_NAME)
                    cursor = conexao.cursor()
                    cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", (u_cad.strip(), s_cad.strip()))
                    conexao.commit()
                    conexao.close()
                    st.success("Cadastrado com sucesso! Volte à aba de Entrar.")
                except sqlite3.IntegrityError:
                    st.error("Este nome de usuário já existe.")
            else:
                st.warning("Preencha todos os campos.")

# --- PAINEL PRINCIPAL DO APP ---
else:
    usuario_ativo = st.session_state["usuario_logado"]
    
    # Cabeçalho
    col_t, col_l = st.columns([3, 1])
    col_t.title(f"Finanças de {usuario_ativo}")
    if col_l.button("Sair"):
        st.session_state["usuario_logado"] = None
        st.rerun()

    # Função aux de cartões
    def obter_cartoes():
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE usuario = ? AND chave = 'cartoes'", (usuario_ativo,))
        res = cursor.fetchone()
        conexao.close()
        return [c.strip() for c in res[0].split(";") if c.strip()] if res and res[0] else []

    cartoes = obter_cartoes()

    # Menu Lateral (Gerenciar Cartões)
    with st.sidebar:
        st.header("⚙️ Configurações")
        st.subheader("Contas e Cartões")
        novo_cartao = st.text_input("Adicionar Conta/Cartão")
        if st.button("Adicionar"):
            if novo_cartao.strip():
                if novo_cartao.strip() not in cartoes:
                    cartoes.append(novo_cartao.strip())
                    conexao = sqlite3.connect(DB_NAME)
                    cursor = conexao.cursor()
                    cursor.execute("INSERT OR REPLACE INTO configuracoes (usuario, chave, valor) VALUES (?, 'cartoes', ?)", (usuario_ativo, ";".join(cartoes)))
                    conexao.commit()
                    conexao.close()
                    st.success("Conta adicionada!")
                    st.rerun()
        
        if cartoes:
            st.write("**Contas cadastradas:**")
            for c in cartoes:
                st.text(f"• {c}")

    # Seleção do Mês de Visualização
    mes_atual_str = datetime.now().strftime("%m/%Y")
    mes_filtro = st.selectbox("Visualizar Mês:", [mes_atual_str] + [f"{m:02d}/{a}" for a in range(2026, 2030) for m in range(1, 13) if f"{m:02d}/{a}" != mes_atual_str])

    # Resumo Financeiro
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute("SELECT tipo, SUM(valor) FROM lancamentos WHERE usuario = ? AND mes_ano = ? GROUP BY tipo", (usuario_ativo, mes_filtro))
    totais = {t: v for t, v in cursor.fetchall()}
    conexao.close()

    receita = totais.get("Receita", 0.0)
    despesa = totais.get("Despesa", 0.0)
    saldo = receita - despesa

    c1, c2, c3 = st.columns(3)
    c1.metric("Receitas", f"R$ {receita:.2f}")
    c2.metric("Despesas", f"R$ {despesa:.2f}")
    c3.metric("Saldo", f"R$ {saldo:.2f}", delta_color="normal" if saldo >= 0 else "inverse")

    st.divider()

    # Formulário de Novo Lançamento
    st.subheader("➕ Novo Lançamento")
    with st.form("form_lancamento", clear_on_submit=True):
        desc = st.text_input("Descrição")
        val = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        dt = st.date_input("Data do Gasto", datetime.now())
        cartao_sel = st.selectbox("Conta/Cartão", cartoes if cartoes else ["Sem conta cadastrada"])
        tipo_cob = st.radio("Tipo de Cobrança", ["Única", "Parcelado"], horizontal=True)
        
        col_p1, col_p2 = st.columns(2)
        num_p = col_p1.number_input("Número de Parcelas", min_value=1, value=2) if tipo_cob == "Parcelado" else 1
        
        tipo_mov = st.radio("Tipo de Lançamento", ["Despesa", "Receita"], horizontal=True)
        submit = st.form_submit_button("Salvar Lançamento", type="primary")

        if submit:
            if not desc or val <= 0:
                st.error("Preencha a descrição e o valor corretamente.")
            else:
                conexao = sqlite3.connect(DB_NAME)
                cursor = conexao.cursor()
                if tipo_cob == "Parcelado":
                    data_curr = dt
                    for i in range(1, int(num_p) + 1):
                        m_fmt = data_curr.strftime("%m/%Y")
                        d_fmt = data_curr.strftime("%d/%m/%Y")
                        desc_p = f"{desc} ({i:02d}/{int(num_p):02d})"
                        cursor.execute("""
                            INSERT INTO lancamentos (usuario, data, mes_ano, tipo, cartao, descricao, valor, status, observacao)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (usuario_ativo, d_fmt, m_fmt, tipo_mov, cartao_sel, desc_p, val, "Pago", ""))
                        data_curr += relativedelta(months=1)
                else:
                    m_fmt = dt.strftime("%m/%Y")
                    d_fmt = dt.strftime("%d/%m/%Y")
                    cursor.execute("""
                        INSERT INTO lancamentos (usuario, data, mes_ano, tipo, cartao, descricao, valor, status, observacao)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (usuario_ativo, d_fmt, m_fmt, tipo_mov, cartao_sel, desc, val, "Pago", ""))
                
                conexao.commit()
                conexao.close()
                st.success("Lançamento salvo com sucesso!")
                st.rerun()

    # Lista de Lançamentos
    st.subheader(f"📋 Lançamentos de {mes_filtro}")
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute("SELECT id, descricao, valor, tipo, cartao, data FROM lancamentos WHERE usuario = ? AND mes_ano = ? ORDER BY id DESC", (usuario_ativo, mes_filtro))
    itens = cursor.fetchall()
    conexao.close()

    if itens:
        for id_l, d, v, t, c, dt_s in itens:
            cor = "🔴" if t == "Despesa" else "🟢"
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"{cor} **{d}** — R$ {v:.2f} ({c} em {dt_s})")
            if col_b.button("Apagar", key=f"del_{id_l}"):
                conexao = sqlite3.connect(DB_NAME)
                cursor = conexao.cursor()
                cursor.execute("DELETE FROM lancamentos WHERE id = ?", (id_l,))
                conexao.commit()
                conexao.close()
                st.rerun()
    else:
        st.info("Nenhum lançamento encontrado para este mês.")
