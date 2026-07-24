import streamlit as st
import pandas as pd
import json
import re
import os
from datetime import datetime
from PIL import Image

# Importação condicional para suporte aos SDKs do Gemini
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


# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTADO
# ==========================================
st.set_page_config(page_title="Finanças de Luna", page_icon="💰", layout="wide")

if "transacoes" not in st.session_state:
    st.session_state["transacoes"] = []

if "ocr_dados_itens" not in st.session_state:
    st.session_state["ocr_dados_itens"] = None


# ==========================================
# 2. BARRA LATERAL (CONFIGURAÇÕES E FILTROS)
# ==========================================
with st.sidebar:
    st.header("⚙️ Configurações")
    st.subheader("Contas e Cartões")
    st.button("Adicionar Conta/Cartão")
    
    st.divider()
    st.header("Finanças de Luna")
    mes_selecionado = st.text_input("Visualizar Mês:", value="07/2026")


# ==========================================
# 3. PAINEL RESUMO (MÉTRICAS)
# ==========================================
df_transacoes = pd.DataFrame(st.session_state["transacoes"])

if not df_transacoes.empty:
    total_receitas = df_transacoes[df_transacoes["tipo"] == "Receita"]["valor"].sum()
    total_despesas = df_transacoes[df_transacoes["tipo"] == "Despesa"]["valor"].sum()
else:
    total_receitas = 0.0
    total_despesas = 0.0

saldo = total_receitas - total_despesas

col_rec, col_desp, col_sal = st.columns(3)
col_rec.metric("Receitas", f"R$ {total_receitas:,.2f}")
col_desp.metric("Despesas", f"R$ {total_despesas:,.2f}")
col_sal.metric("Saldo", f"R$ {saldo:,.2f}")

st.divider()


# ==========================================
# 4. ABAS DE ENTRADA DE DADOS
# ==========================================
aba_manual, aba_ocr = st.tabs(["✍️ Manual", "📷 Escanear Imagem/Comprovante"])

# --- ABA 1: ENTRADA MANUAL ---
with aba_manual:
    st.subheader("Adicionar Lançamento Manual")
    with st.form("form_manual", clear_on_submit=True):
        col_desc, col_val, col_tipo, col_data = st.columns([3, 2, 2, 2])
        desc = col_desc.text_input("Descrição")
        val = col_val.number_input("Valor (R$)", min_value=0.0, step=0.01)
        tipo = col_tipo.selectbox("Tipo", ["Despesa", "Receita"])
        dt = col_data.date_input("Data", value=datetime.today())
        
        btn_salvar_manual = st.form_submit_button("➕ Adicionar Lançamento")
        if btn_salvar_manual and desc and val > 0:
            st.session_state["transacoes"].append({
                "descricao": desc,
                "valor": val,
                "tipo": tipo,
                "data": dt.strftime("%Y-%m-%d")
            })
            st.success("Lançamento adicionado com sucesso!")
            st.rerun()

# --- ABA 2: OCR COM GEMINI ---
with aba_ocr:
    st.subheader("📷 Extrair Linhas com Valores Numéricos")
    st.caption("Envie uma foto de um recibo, fatura ou nota. A IA extrairá apenas os itens com valores.")

    arquivo_imagem = st.file_uploader(
        "Selecione uma imagem do comprovante ou produto", 
        type=["jpg", "jpeg", "png", "webp"]
    )
    
    if arquivo_imagem:
        st.image(arquivo_imagem, caption="Imagem carregada", use_container_width=True)
        
        if st.button("🔍 Processar Imagem e Extrair Itens", type="primary"):
            api_key = os.getenv("GEMINI_API_KEY")
            
            if not api_key:
                st.error("A variável 'GEMINI_API_KEY' não está configurada nas variáveis de ambiente.")
            elif not (NOVO_SDK or SDK_ANTIGO):
                st.error("Instale 'google-genai' no seu ambiente/requirements.txt.")
            else:
                with st.spinner("Analisando imagem com o Gemini..."):
                    texto_resposta = None
                    erros_encontrados = []
                    img = Image.open(arquivo_imagem)
                    
                    prompt = """
                    Analise a imagem fornecida (comprovante, nota, recibo ou extrato).
                    Identifique TODAS as linhas ou itens que possuem um VALOR NUMÉRICO associado (preço, custo, taxa, etc.).
                    Ignore linhas que sejam apenas textos, cabeçalhos ou sem valores.

                    Retorne EXATAMENTE um JSON no seguinte formato sem texto extra ao redor:
                    {
                      "data_geral": "YYYY-MM-DD",
                      "itens": [
                        {
                          "descricao": "nome do item ou linha",
                          "valor": 12.50,
                          "tipo": "Despesa"
                        }
                      ]
                    }
                    Se não encontrar a data no recibo, utilize a data de hoje.
                    """

                    # TENTATIVA 1: SDK Novo (google-genai)
                    if NOVO_SDK:
                        try:
                            client = genai.Client(api_key=api_key)
                            # Modelos atualizados e com nomenclatura correta v1beta
                            modelos_validos = [
                                'models/gemini-1.5-flash',
                                'models/gemini-2.0-flash',
                                'gemini-1.5-flash-latest'
                            ]
                            
                            for m in modelos_validos:
                                try:
                                    res = client.models.generate_content(model=m, contents=[img, prompt])
                                    if res and res.text:
                                        texto_resposta = res.text
                                        break
                                except Exception as ex:
                                    erros_encontrados.append(f"Modelo '{m}': {ex}")
                        except Exception as ex:
                            erros_encontrados.append(f"Erro no cliente genai: {ex}")

                    # TENTATIVA 2: SDK Legado (google-generativeai) caso o novo não responda
                    if not texto_resposta and SDK_ANTIGO:
                        try:
                            legacy_genai.configure(api_key=api_key)
                            for m in ['gemini-1.5-flash', 'gemini-1.5-pro']:
                                try:
                                    model_inst = legacy_genai.GenerativeModel(m)
                                    res = model_inst.generate_content([prompt, img])
                                    if res and res.text:
                                        texto_resposta = res.text
                                        break
                                except Exception as ex:
                                    erros_encontrados.append(f"Legacy '{m}': {ex}")
                        except Exception as ex:
                            erros_encontrados.append(f"Erro no SDK legado: {ex}")

                    # PARSE E TRATAMENTO DOS DADOS RETORNADOS
                    if texto_resposta:
                        try:
                            json_match = re.search(r'\{.*\}', texto_resposta, re.DOTALL)
                            json_str = json_match.group(0) if json_match else texto_resposta.strip()
                            dados = json.loads(json_str)
                            
                            st.session_state["ocr_dados_itens"] = dados
                            st.success(f"{len(dados.get('itens', []))} item(ns) encontrado(s)! Revise abaixo.")
                        except Exception as parse_error:
                            st.error(f"Erro ao interpretar o JSON retornado: {parse_error}")
                    else:
                        st.error("Não foi possível conectar à API do Gemini. Detalhes dos erros:")
                        for err in erros_encontrados:
                            st.warning(err)

    # REVISÃO E CONFIRMAÇÃO DOS ITENS EXTRAÍDOS
    if st.session_state["ocr_dados_itens"]:
        dados_ocr = st.session_state["ocr_dados_itens"]
        st.subheader("📋 Confirmar Lançamentos Extraídos")
        
        itens = dados_ocr.get("itens", [])
        data_padrao = dados_ocr.get("data_geral", datetime.today().strftime("%Y-%m-%d"))
        
        df_ocr = pd.DataFrame(itens)
        if not df_ocr.empty:
            df_editavel = st.data_editor(
                df_ocr, 
                num_rows="dynamic", 
                use_container_width=True,
                key="editor_ocr"
            )
            
            if st.button("✅ Salvar Itens Selecionados nas Finanças", type="primary"):
                novos_itens = df_editavel.to_dict("records")
                for item in novos_itens:
                    item["data"] = data_padrao
                    st.session_state["transacoes"].append(item)
                
                st.session_state["ocr_dados_itens"] = None
                st.success("Lançamentos importados com sucesso!")
                st.rerun()


# ==========================================
# 5. TABELA DE TRANSAÇÕES
# ==========================================
st.subheader("📊 Histórico de Transações")
if not df_transacoes.empty:
    st.dataframe(df_transacoes, use_container_width=True)
else:
    st.info("Nenhuma transação cadastrada até o momento.")
