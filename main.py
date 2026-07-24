
import os
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
import streamlit as st

st.set_page_config(page_title="Controle de Custos", page_icon="💰", layout="centered")

# --- CONEXÃO COM O BANCO (PostgreSQL no Render / SQLite Local) ---
DATABASE_URL = os.getenv("DATABASE_URL")

def get_conexao():
    if DATABASE_URL:
        import psycopg2
        url = DATABASE_URL.replace("postgres://", "postgresql://")
        return psycopg2.connect(url)
    else:
        return sqlite3.connect("controle_gastos_v4.db")

def inicializar_banco():
    conexao = get_conexao()
    cursor = conexao.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(100) UNIQUE,
            senha VARCHAR(255)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            usuario VARCHAR(100),
            chave VARCHAR(100),
            valor TEXT,
            PRIMARY KEY (usuario, chave)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(100),
            data VARCHAR(20),
            mes_ano VARCHAR(10),
            tipo VARCHAR(20),
            cartao VARCHAR(100),
            descricao TEXT,
            valor REAL,
            status VARCHAR(50),
            observacao TEXT
        )
    """)
    conexao.commit()
    cursor.close()
    conexao.close()

inicializar_banco()

# --- SISTEMA DE MANTER LOGADO VIA QUERY PARAMS (Sem bibliotecas extras) ---
query_params = st.query_params

if "usuario_logado" not in st.session_state:
    # Se o parâmetro 'user' estiver na URL, loga automaticamente
    if "user" in query_params:
        st.session_state["usuario_logado"] = query_params["user"]
    else:
        st.session_state["usuario_logado"] = None

# --- TELA DE LOGIN / CADASTRO ---
if not st.session_state["usuario_logado"]:
    st.title("💰 Controle de Custos")
    
    aba1, aba2 = st.tabs(["🔑 Entrar", "📝 Cadastrar"])
    
    with aba1:
        u = st.text_input("Usuário", key="login_user")
        s = st.text_input("Senha", type="password", key="login_pass")
        manter_logado = st.checkbox("Manter-me conectado neste aparelho", value=True)
        
        if st.button("Entrar", type="primary", use_container_width=True):
            usuario_limpo = u.strip().lower()
            senha_limpa = s.strip()
            
            conexao = get_conexao()
            cursor = conexao.cursor()
            cursor.execute("SELECT usuario FROM usuarios WHERE usuario = %s AND senha = %s" if DATABASE_URL else "SELECT usuario FROM usuarios WHERE usuario = ? AND senha = ?", (usuario_limpo, senha_limpa))
            valido = cursor.fetchone()
            cursor.close()
            conexao.close()
            
            if valido:
                st.session_state["usuario_logado"] = usuario_limpo
                if manter_logado:
                    st.query_params["user"] = usuario_limpo
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    with aba2:
        u_cad = st.text_input("Novo Usuário", key="cad_user")
        s_cad = st.text_input("Nova Senha", type="password", key="cad_pass")
        
        if st.button("Cadastrar", use_container_width=True):
            if u_cad and s_cad:
                usuario_cad_limpo = u_cad.strip().lower()
                senha_cad_limpa = s_cad.strip()
                try:
                    conexao = get_conexao()
                    cursor = conexao.cursor()
                    cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (%s, %s)" if DATABASE_URL else "INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", (usuario_cad_limpo, senha_cad_limpa))
                    conexao.commit()
                    cursor.close()
                    conexao.close()
                    st.success("Cadastrado com sucesso! Volte à aba de Entrar.")
                except Exception:
                    st.error("Este nome de usuário já existe.")
            else:
                st.warning("Preencha todos os campos.")

# --- PAINEL PRINCIPAL DO APP ---
else:
    usuario_ativo = st.session_state["usuario_logado"]
    
    # Cabeçalho com Logout
    col_t, col_l = st.columns([3, 1])
    col_t.title(f"Finanças de {usuario_ativo}")
    
    if col_l.button("Sair"):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

    # Função auxiliar de cartões
    def obter_cartoes():
        conexao = get_conexao()
        cursor = conexao.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE usuario = %s AND chave = 'cartoes'" if DATABASE_URL else "SELECT valor FROM configuracoes WHERE usuario = ? AND chave = 'cartoes'", (usuario_ativo,))
        res = cursor.fetchone()
        cursor.close()
        conexao.close()
        return [c.strip() for c in res[0].split(";") if c.strip()] if res and res[0] else []

    cartoes = obter_cartoes()

    # Menu Lateral (Configurações)
    with st.sidebar:
        st.header("⚙️ Configurações")
        st.subheader("Contas e Cartões")
        novo_cartao = st.text_input("Adicionar Conta/Cartão")
        if st.button("Adicionar"):
            if novo_cartao.strip():
                if novo_cartao.strip() not in cartoes:
                    cartoes.append(novo_cartao.strip())
                    str_cartoes = ";".join(cartoes)
                    conexao = get_conexao()
                    cursor = conexao.cursor()
                    
                    if DATABASE_URL:
                        cursor.execute("""
                            INSERT INTO configuracoes (usuario, chave, valor) VALUES (%s, 'cartoes', %s)
                            ON CONFLICT (usuario, chave) DO UPDATE SET valor = EXCLUDED.valor
                        """, (usuario_ativo, str_cartoes))
                    else:
                        cursor.execute("INSERT OR REPLACE INTO configuracoes (usuario, chave, valor) VALUES (?, 'cartoes', ?)", (usuario_ativo, str_cartoes))
                    
                    conexao.commit()
                    cursor.close()
                    conexao.close()
                    st.success("Conta adicionada!")
                    st.rerun()
        
        if cartoes:
            st.write("**Contas cadastradas:**")
            for c in cartoes:
                st.text(f"• {c}")

    # Filtro de Mês
    mes_atual_str = datetime.now().strftime("%m/%Y")
    mes_filtro = st.selectbox("Visualizar Mês:", [mes_atual_str] + [f"{m:02d}/{a}" for a in range(2026, 2030) for m in range(1, 13) if f"{m:02d}/{a}" != mes_atual_str])

    # Resumo Financeiro
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT tipo, SUM(valor) FROM lancamentos WHERE usuario = %s AND mes_ano = %s GROUP BY tipo" if DATABASE_URL else "SELECT tipo, SUM(valor) FROM lancamentos WHERE usuario = ? AND mes_ano = ? GROUP BY tipo", (usuario_ativo, mes_filtro))
    totais = {t: v for t, v in cursor.fetchall()}
    cursor.close()
    conexao.close()

    receita = totais.get("Receita", 0.0)
    despesa = totais.get("Despesa", 0.0)
    saldo = receita - despesa

    c1, c2, c3 = st.columns(3)
    c1.metric("Receitas", f"R$ {receita:.2f}")
    c2.metric("Despesas", f"R$ {despesa:.2f}")
    c3.metric("Saldo", f"R$ {saldo:.2f}", delta_color="normal" if saldo >= 0 else "inverse")

    st.divider()

    # Formulário de Lançamento
    st.subheader("➕ Novo Lançamento")
    with st.form("form_lancamento", clear_on_submit=True):
        desc = st.text_input("Descrição")
        val = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
        dt = st.date_input("Data do Gasto", datetime.now())
        cartao_sel = st.selectbox("Conta/Cartão", cartoes if cartoes else ["Sem conta cadastrada"])
        tipo_cob = st.radio("Tipo de Cobrança", ["Única", "Parcelado"], horizontal=True)
        
        num_p = st.number_input("Número de Parcelas", min_value=1, value=2) if tipo_cob == "Parcelado" else 1
        tipo_mov = st.radio("Tipo de Lançamento", ["Despesa", "Receita"], horizontal=True)
        submit = st.form_submit_button("Salvar Lançamento", type="primary")

        if submit:
            if not desc or val <= 0:
                st.error("Preencha a descrição e o valor corretamente.")
            else:
                conexao = get_conexao()
                cursor = conexao.cursor()
                sql_insert = "INSERT INTO lancamentos (usuario, data, mes_ano, tipo, cartao, descricao, valor, status, observacao) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)" if DATABASE_URL else "INSERT INTO lancamentos (usuario, data, mes_ano, tipo, cartao, descricao, valor, status, observacao) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                
                if tipo_cob == "Parcelado":
                    data_curr = dt
                    for i in range(1, int(num_p) + 1):
                        m_fmt = data_curr.strftime("%m/%Y")
                        d_fmt = data_curr.strftime("%d/%m/%Y")
                        desc_p = f"{desc} ({i:02d}/{int(num_p):02d})"
                        cursor.execute(sql_insert, (usuario_ativo, d_fmt, m_fmt, tipo_mov, cartao_sel, desc_p, val, "Pago", ""))
                        data_curr += relativedelta(months=1)
                else:
                    m_fmt = dt.strftime("%m/%Y")
                    d_fmt = dt.strftime("%d/%m/%Y")
                    cursor.execute(sql_insert, (usuario_ativo, d_fmt, m_fmt, tipo_mov, cartao_sel, desc, val, "Pago", ""))
                
                conexao.commit()
                cursor.close()
                conexao.close()
                st.success("Lançamento salvo com sucesso!")
                st.rerun()

    # Lista e Edição de Lançamentos
    st.subheader(f"📋 Lançamentos de {mes_filtro}")
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, descricao, valor, tipo, cartao, data FROM lancamentos WHERE usuario = %s AND mes_ano = %s ORDER BY id DESC" if DATABASE_URL else "SELECT id, descricao, valor, tipo, cartao, data FROM lancamentos WHERE usuario = ? AND mes_ano = ? ORDER BY id DESC", (usuario_ativo, mes_filtro))
    itens = cursor.fetchall()
    cursor.close()
    conexao.close()

    if itens:
        for id_l, d, v, t, c, dt_s in itens:
            cor = "🔴" if t == "Despesa" else "🟢"
            
            with st.expander(f"{cor} {d} — R$ {v:.2f} ({c} em {dt_s})"):
                with st.form(key=f"edit_form_{id_l}"):
                    edit_desc = st.text_input("Descrição", value=d)
                    edit_val = st.number_input("Valor (R$)", min_value=0.0, step=0.01, value=float(v))
                    
                    try:
                        data_obj = datetime.strptime(dt_s, "%d/%m/%Y")
                    except ValueError:
                        data_obj = datetime.now()
                        
                    edit_dt = st.date_input("Data", value=data_obj)
                    idx_cartao = cartoes.index(c) if c in cartoes else 0
                    edit_cartao = st.selectbox("Conta/Cartão", cartoes if cartoes else ["Sem conta cadastrada"], index=idx_cartao)
                    
                    idx_tipo = 0 if t == "Despesa" else 1
                    edit_tipo = st.radio("Tipo", ["Despesa", "Receita"], index=idx_tipo, horizontal=True)
                    
                    salvar = st.form_submit_button("💾 Salvar Alterações", type="primary")
                    
                    if salvar:
                        if not edit_desc or edit_val <= 0:
                            st.error("Descrição e Valor devem ser preenchidos corretamente.")
                        else:
                            nova_m_fmt = edit_dt.strftime("%m/%Y")
                            nova_d_fmt = edit_dt.strftime("%d/%m/%Y")
                            
                            conexao = get_conexao()
                            cursor = conexao.cursor()
                            sql_update = """
                                UPDATE lancamentos 
                                SET descricao = %s, valor = %s, data = %s, mes_ano = %s, cartao = %s, tipo = %s
                                WHERE id = %s AND usuario = %s
                            """ if DATABASE_URL else """
                                UPDATE lancamentos 
                                SET descricao = ?, valor = ?, data = ?, mes_ano = ?, cartao = ?, tipo = ?
                                WHERE id = ? AND usuario = ?
                            """
                            cursor.execute(sql_update, (edit_desc, edit_val, nova_d_fmt, nova_m_fmt, edit_cartao, edit_tipo, id_l, usuario_ativo))
                            conexao.commit()
                            cursor.close()
                            conexao.close()
                            st.success("Lançamento atualizado!")
                            st.rerun()

                if st.button("🗑️ Apagar Lançamento", key=f"del_{id_l}"):
                    conexao = get_conexao()
                    cursor = conexao.cursor()
                    cursor.execute("DELETE FROM lancamentos WHERE id = %s AND usuario = %s" if DATABASE_URL else "DELETE FROM lancamentos WHERE id = ? AND usuario = ?", (id_l, usuario_ativo))
                    conexao.commit()
                    cursor.close()
                    conexao.close()
                    st.success("Removido com sucesso!")
                    st.rerun()
    else:
        st.info("Nenhum lançamento encontrado para este mês.")
