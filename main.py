import os
import json
import re
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
import streamlit as st
from PIL import Image

# Importação com tratamento de compatibilidade
try:
    from google import genai
    NOVO_SDK = True
except ImportError:
    NOVO_SDK = False

try:
    import google.generativeai as legacy_genai
    SDK_ANTIGO = True
except ImportError:
    SDK_ANTIGO = False

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
            senha VARCHAR(255),
            pergunta_sec TEXT,
            resposta_sec TEXT
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

def ajustar_schema():
    if not DATABASE_URL:
        conexao = get_conexao()
        cursor = conexao.cursor()
        try:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN pergunta_sec TEXT")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN resposta_sec TEXT")
            conexao.commit()
        except sqlite3.OperationalError:
            pass
        finally:
            cursor.close()
            conexao.close()

inicializar_banco()
ajustar_schema()

# --- SISTEMA DE MANTER LOGADO VIA QUERY PARAMS ---
query_params = st.query_params

if "usuario_logado" not in st.session_state or not st.session_state["usuario_logado"]:
    if "user" in query_params and query_params["user"]:
        st.session_state["usuario_logado"] = str(query_params["user"]).strip().lower()
    else:
        st.session_state["usuario_logado"] = None

# --- TELA DE LOGIN / CADASTRO / RECUPERAÇÃO ---
if not st.session_state["usuario_logado"]:
    st.title("💰 Controle de Custos")
    
    aba1, aba2, aba3 = st.tabs(["🔑 Entrar", "📝 Cadastrar", "❓ Esqueci a Senha"])
    
    with aba1:
        u = st.text_input("Usuário", key="login_user")
        s = st.text_input("Senha", type="password", key="login_pass")
        manter_logado = st.checkbox("Manter-me conectado neste aparelho", value=True)
        
        if st.button("Entrar", type="primary", use_container_width=True):
            usuario_limpo = u.strip().lower()
            senha_limpa = s.strip()
            
            if not usuario_limpo or not senha_limpa:
                st.warning("Preencha usuário e senha.")
            else:
                conexao = get_conexao()
                cursor = conexao.cursor()
                cursor.execute(
                    "SELECT usuario FROM usuarios WHERE LOWER(usuario) = %s AND senha = %s" if DATABASE_URL 
                    else "SELECT usuario FROM usuarios WHERE LOWER(usuario) = ? AND senha = ?", 
                    (usuario_limpo, senha_limpa)
                )
                valido = cursor.fetchone()
                cursor.close()
                conexao.close()
                
                if valido:
                    usr_banco = valido[0]
                    st.session_state["usuario_logado"] = usr_banco
                    if manter_logado:
                        st.query_params["user"] = usr_banco
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos. Verifique se digitou corretamente.")

    with aba2:
        u_cad = st.text_input("Novo Usuário", key="cad_user")
        s_cad = st.text_input("Nova Senha", type="password", key="cad_pass")
        p_cad = st.selectbox("Pergunta de Segurança", [
            "Qual o nome do seu primeiro animal de estimação?",
            "Qual a sua cidade natal?",
            "Qual o seu livro ou filme favorito?",
            "Qual o nome da sua primeira escola?"
        ], key="cad_perg")
        r_cad = st.text_input("Resposta de Segurança", key="cad_resp")
        
        if st.button("Cadastrar Conta", use_container_width=True):
            usuario_cad_limpo = u_cad.strip().lower()
            senha_cad_limpa = s_cad.strip()
            resp_cad_limpa = r_cad.strip().lower()
            
            if usuario_cad_limpo and senha_cad_limpa and resp_cad_limpa:
                try:
                    conexao = get_conexao()
                    cursor = conexao.cursor()
                    sql_cad = "INSERT INTO usuarios (usuario, senha, pergunta_sec, resposta_sec) VALUES (%s, %s, %s, %s)" if DATABASE_URL else "INSERT INTO usuarios (usuario, senha, pergunta_sec, resposta_sec) VALUES (?, ?, ?, ?)"
                    cursor.execute(sql_cad, (usuario_cad_limpo, senha_cad_limpa, p_cad, resp_cad_limpa))
                    conexao.commit()
                    cursor.close()
                    conexao.close()
                    st.success("Conta criada com sucesso! Você já pode entrar na aba 'Entrar'.")
                except Exception:
                    st.error("Este nome de usuário já existe.")
            else:
                st.warning("Preencha todos os campos do cadastro.")

    with aba3:
        u_rec = st.text_input("Digite o seu Usuário", key="rec_user")
        if u_rec:
            usuario_rec_limpo = u_rec.strip().lower()
            conexao = get_conexao()
            cursor = conexao.cursor()
            cursor.execute("SELECT pergunta_sec FROM usuarios WHERE LOWER(usuario) = %s" if DATABASE_URL else "SELECT pergunta_sec FROM usuarios WHERE LOWER(usuario) = ?", (usuario_rec_limpo,))
            dados_user = cursor.fetchone()
            cursor.close()
            conexao.close()

            if dados_user and dados_user[0]:
                st.info(f"**Pergunta de Segurança:** {dados_user[0]}")
                r_rec = st.text_input("Sua Resposta", key="rec_resp")
                nova_senha = st.text_input("Nova Senha", type="password", key="rec_new_pass")

                if st.button("Redefinir Senha", use_container_width=True):
                    resp_rec_limpa = r_rec.strip().lower()
                    nova_senha_limpa = nova_senha.strip()

                    if resp_rec_limpa and nova_senha_limpa:
                        conexao = get_conexao()
                        cursor = conexao.cursor()
                        cursor.execute("SELECT id FROM usuarios WHERE LOWER(usuario) = %s AND LOWER(resposta_sec) = %s" if DATABASE_URL else "SELECT id FROM usuarios WHERE LOWER(usuario) = ? AND LOWER(resposta_sec) = ?", (usuario_rec_limpo, resp_rec_limpa))
                        valido = cursor.fetchone()

                        if valido:
                            sql_up = "UPDATE usuarios SET senha = %s WHERE LOWER(usuario) = %s" if DATABASE_URL else "UPDATE usuarios SET senha = ? WHERE LOWER(usuario) = ?"
                            cursor.execute(sql_up, (nova_senha_limpa, usuario_rec_limpo))
                            conexao.commit()
                            cursor.close()
                            conexao.close()
                            st.success("Senha alterada com sucesso!")
                        else:
                            cursor.close()
                            conexao.close()
                            st.error("Resposta incorreta.")
                    else:
                        st.warning("Preencha a resposta e a nova senha.")
            elif dados_user:
                st.warning("Usuário cadastrado sem pergunta de segurança.")
            else:
                st.error("Usuário não encontrado.")

# --- PAINEL PRINCIPAL DO APP ---
else:
    usuario_ativo = st.session_state["usuario_logado"]
    
    col_t, col_l = st.columns([3, 1])
    col_t.title(f"Finanças de {usuario_ativo}")
    
    if col_l.button("Sair"):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

    def obter_cartoes():
        conexao = get_conexao()
        cursor = conexao.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE LOWER(usuario) = %s AND chave = 'cartoes'" if DATABASE_URL else "SELECT valor FROM configuracoes WHERE LOWER(usuario) = ? AND chave = 'cartoes'", (usuario_ativo,))
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
    cursor.execute("SELECT tipo, SUM(valor) FROM lancamentos WHERE LOWER(usuario) = %s AND mes_ano = %s GROUP BY tipo" if DATABASE_URL else "SELECT tipo, SUM(valor) FROM lancamentos WHERE LOWER(usuario) = ? AND mes_ano = ? GROUP BY tipo", (usuario_ativo, mes_filtro))
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

    # --- NOVO LANÇAMENTO (MANUAL OU SCANNER DE COMPROVANTE/IMAGENS) ---
    aba_manual, aba_ocr = st.tabs(["✍️ Manual", "📷 Escanear Imagem/Comprovante"])

    with aba_manual:
        st.subheader("➕ Novo Lançamento Manual")
        with st.form("form_lancamento", clear_on_submit=True):
            desc = st.text_input("Descrição")
            val = st.number_input("Valor (R$)", min_value=0.0, step=0.01)
            dt = st.date_input("Data do Gasto", datetime.now())
            cartao_sel = st.selectbox("Conta/Cartão", cartoes if cartoes else ["Sem conta cadastrada"], key="c_manual")
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

    # --- OPÇÃO 2: ESCANEAR LINHA A LINHA COM VALORES NUMÉRICOS ---
    with aba_ocr:
        st.subheader("📷 Extrair Linhas com Valores Numéricos")
        st.caption("Envie uma foto de um recibo, fatura ou nota. A IA extrairá apenas os itens que possuem valor numérico.")

        arquivo_imagem = st.file_uploader(
            "Selecione uma imagem do comprovante ou produto", 
            type=["jpg", "jpeg", "png", "webp"]
        )
        
        if arquivo_imagem:
            st.image(arquivo_imagem, caption="Imagem carregada", use_container_width=True)
            
            if st.button("🔍 Processar Imagem e Extrair Itens", type="primary"):
                api_key = os.getenv("GEMINI_API_KEY")
                
                if not (NOVO_SDK or SDK_ANTIGO):
                    st.error("Nenhuma biblioteca 'google-genai' ou 'google-generativeai' está instalada.")
                elif not api_key:
                    st.error("Variável GEMINI_API_KEY não configurada no Render/Ambiente.")
                else:
                    with st.spinner("Analisando imagem e extraindo linhas com valores..."):
                        try:
                            img = Image.open(arquivo_imagem)
                            prompt = """
                            Analise a imagem fornecida (comprovante, nota, recibo ou extrato).
                            Identifique TODAS as linhas ou itens que possuem um VALOR NUMÉRICO associado (preço, custo, taxa, etc.).
                            Ignore linhas que sejam apenas textos, cabeçalhos ou sem valores.

                            Retorne EXATAMENTE um JSON com o seguinte formato:
                            {
                              "data_geral": "YYYY-MM-DD",
                              "itens": [
                                {
                                  "descricao": "nome do item ou descrição da linha",
                                  "valor": 12.50,
                                  "tipo": "Despesa"
                                }
                              ]
                            }

                            Se não encontrar a data, use a data de hoje.
                            Responda estritamente o JSON válido.
                            """

                            texto_resposta = None

                            # Tativa 1: Usando a biblioteca nova (google-genai)
                            if NOVO_SDK:
                                client = genai.Client(api_key=api_key)
                                modelos_tentativa = ['gemini-2.5-flash', 'gemini-1.5-flash']
                                
                                for mod in modelos_tentativa:
                                    try:
                                        res = client.models.generate_content(model=mod, contents=[img, prompt])
                                        texto_resposta = res.text
                                        if texto_resposta:
                                            break
                                    except Exception:
                                        continue

                            # Tentativa 2: Usando a biblioteca legada se a nova falhar ou não estiver disponível
                            if not texto_resposta and SDK_ANTIGO:
                                legacy_genai.configure(api_key=api_key)
                                modelos_legacy = ['gemini-1.5-flash', 'gemini-pro-vision']
                                
                                for mod in modelos_legacy:
                                    try:
                                        model_inst = legacy_genai.GenerativeModel(mod)
                                        res = model_inst.generate_content([prompt, img])
                                        texto_resposta = res.text
                                        if texto_resposta:
                                            break
                                    except Exception:
                                        continue

                            if not texto_resposta:
                                raise Exception("Não foi possível conectar a nenhum modelo da Google API.")

                            # Extração Segura do JSON via Regex
                            json_match = re.search(r'\{.*\}', texto_resposta, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(0)
                            else:
                                json_str = texto_resposta.strip()

                            dados = json.loads(json_str)
                            
                            st.session_state["ocr_dados_itens"] = dados
                            st.success(f"{len(dados.get('itens', []))} item(ns) encontrado(s)! Revise antes de lançar.")

                        except Exception as e:
                            st.error(f"Erro ao analisar comprovante: {e}")

        # Se itens foram extraídos, mostra para confirmação em lote
        if "ocr_dados_itens" in st.session_state and st.session_state["ocr_dados_itens"]:
            dados_extraidos = st.session_state["ocr_dados_itens"]
            lista_itens = dados_extraidos.get("itens", [])
            data_geral_str = dados_extraidos.get("data_geral", datetime.now().strftime("%Y-%m-%d"))

            try:
                dt_padrao = datetime.strptime(data_geral_str, "%Y-%m-%d")
            except ValueError:
                dt_padrao = datetime.now()

            st.divider()
            st.write("### 📝 Itens Detectados para Lançamento")
            
            with st.form("form_ocr_multiplos"):
                dt_lanc = st.date_input("Data dos Lançamentos", value=dt_padrao)
                cartao_ocr = st.selectbox("Conta/Cartão", cartoes if cartoes else ["Sem conta cadastrada"], key="c_ocr_multi")
                
                itens_confirmados = []
                for idx, item in enumerate(lista_itens):
                    c_desc, c_val, c_tipo = st.columns([3, 2, 2])
                    desc_i = c_desc.text_input(f"Descrição #{idx+1}", value=item.get("descricao", "Item"), key=f"desc_ocr_{idx}")
                    val_i = c_val.number_input(f"Valor #{idx+1} (R$)", value=float(item.get("valor", 0.0)), step=0.01, key=f"val_ocr_{idx}")
                    tipo_i = c_tipo.selectbox(f"Tipo #{idx+1}", ["Despesa", "Receita"], index=0 if item.get("tipo") == "Despesa" else 1, key=f"tipo_ocr_{idx}")
                    
                    itens_confirmados.append({"descricao": desc_i, "valor": val_i, "tipo": tipo_i})

                if st.form_submit_button("💾 Salvar Todos os Itens Extraídos", type="primary"):
                    m_fmt = dt_lanc.strftime("%m/%Y")
                    d_fmt = dt_lanc.strftime("%d/%m/%Y")
                    
                    conexao = get_conexao()
                    cursor = conexao.cursor()
                    sql_insert = "INSERT INTO lancamentos (usuario, data, mes_ano, tipo, cartao, descricao, valor, status, observacao) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)" if DATABASE_URL else "INSERT INTO lancamentos (usuario, data, mes_ano, tipo, cartao, descricao, valor, status, observacao) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    
                    qtd_salva = 0
                    for item in itens_confirmados:
                        if item["valor"] > 0 and item["descricao"].strip():
                            cursor.execute(sql_insert, (usuario_ativo, d_fmt, m_fmt, item["tipo"], cartao_ocr, item["descricao"].strip(), item["valor"], "Pago", "Via Scanner de Imagem"))
                            qtd_salva += 1

                    conexao.commit()
                    cursor.close()
                    conexao.close()
                    
                    del st.session_state["ocr_dados_itens"]
                    st.success(f"{qtd_salva} lançamento(s) salvos com sucesso!")
                    st.rerun()

    # --- LISTA E EDICÃO DOS LANÇAMENTOS ---
    st.subheader(f"📋 Lançamentos de {mes_filtro}")
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, descricao, valor, tipo, cartao, data FROM lancamentos WHERE LOWER(usuario) = %s AND mes_ano = %s ORDER BY id DESC" if DATABASE_URL else "SELECT id, descricao, valor, tipo, cartao, data FROM lancamentos WHERE LOWER(usuario) = ? AND mes_ano = ? ORDER BY id DESC", (usuario_ativo, mes_filtro))
    itens = cursor.fetchall()
    cursor.close()
    conexao.close()

    if itens:
        for idx, (id_l, d, v, t, c, dt_s) in enumerate(itens):
            cor = "🔴" if t == "Despesa" else "🟢"
            
            with st.expander(f"{cor} {d} — R$ {v:.2f} ({c} em {dt_s})"):
                with st.form(key=f"edit_form_{id_l}_{idx}"):
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
                            
                            if id_l is not None:
                                sql_update = "UPDATE lancamentos SET descricao = %s, valor = %s, data = %s, mes_ano = %s, cartao = %s, tipo = %s WHERE id = %s AND LOWER(usuario) = %s" if DATABASE_URL else "UPDATE lancamentos SET descricao = ?, valor = ?, data = ?, mes_ano = ?, cartao = ?, tipo = ? WHERE id = ? AND LOWER(usuario) = ?"
                                cursor.execute(sql_update, (edit_desc, edit_val, nova_d_fmt, nova_m_fmt, edit_cartao, edit_tipo, id_l, usuario_ativo))
                            else:
                                sql_update = "UPDATE lancamentos SET descricao = %s, valor = %s, data = %s, mes_ano = %s, cartao = %s, tipo = %s WHERE LOWER(usuario) = %s AND descricao = %s AND valor = %s" if DATABASE_URL else "UPDATE lancamentos SET descricao = ?, valor = ?, data = ?, mes_ano = ?, cartao = ?, tipo = ? WHERE LOWER(usuario) = ? AND descricao = ? AND valor = ?"
                                cursor.execute(sql_update, (edit_desc, edit_val, nova_d_fmt, nova_m_fmt, edit_cartao, edit_tipo, usuario_ativo, d, v))
                                
                            conexao.commit()
                            cursor.close()
                            conexao.close()
                            st.success("Lançamento atualizado!")
                            st.rerun()

                if st.button("🗑️ Apagar Lançamento", key=f"del_{id_l}_{idx}"):
                    conexao = get_conexao()
                    cursor = conexao.cursor()
                    if id_l is not None:
                        cursor.execute("DELETE FROM lancamentos WHERE id = %s AND LOWER(usuario) = %s" if DATABASE_URL else "DELETE FROM lancamentos WHERE id = ? AND LOWER(usuario) = ?", (id_l, usuario_ativo))
                    else:
                        cursor.execute("DELETE FROM lancamentos WHERE LOWER(usuario) = %s AND descricao = %s AND valor = %s" if DATABASE_URL else "DELETE FROM lancamentos WHERE LOWER(usuario) = ? AND descricao = ? AND valor = ?", (usuario_ativo, d, v))
                    conexao.commit()
                    cursor.close()
                    conexao.close()
                    st.success("Removido com sucesso!")
                    st.rerun()
    else:
        st.info("Nenhum lançamento encontrado para este mês.")
