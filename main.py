import os
os.environ["KIVY_NO_ARGS"] = "1" 

import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen, ScreenManager
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFillRoundFlatButton, MDIconButton, MDRaisedButton, MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, TwoLineAvatarListItem, IconLeftWidget, OneLineListItem
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivymd.uix.selectioncontrol import MDCheckbox

import tempfile
DB_NAME = os.path.join(tempfile.gettempdir(), "controle_gastos_v4.db")

def inicializar_banco():
    try:
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        
        # Tabela de usuários
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE,
                senha TEXT
            )
        """)
        
        # Tabela para lembrar o último login efetuado
        cursor.execute("CREATE TABLE IF NOT EXISTS sessao (chave TEXT PRIMARY KEY, valor TEXT)")
        
        # Tabelas modificadas para conter o dono do dado (usuario)
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
    except Exception as e:
        print(f"Erro banco: {e}")

# ============================================================
# TELA DE LOGIN
# ============================================================
class TelaLogin(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = MDBoxLayout(orientation="vertical", padding=dp(24), spacing=dp(16), justify_content="center")
        
        card = MDCard(
            orientation="vertical",
            padding=dp(24),
            spacing=dp(16),
            size_hint=(0.9, None),
            height=dp(400),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            elevation=3,
            radius=[dp(16)]
        )
        
        card.add_widget(MDLabel(
            text="Controle de Custos",
            font_style="H5",
            bold=True,
            halign="center",
            theme_text_color="Primary"
        ))
        
        self.txt_usuario = MDTextField(hint_text="Usuário", icon_left="account", mode="rectangle")
        self.txt_senha = MDTextField(hint_text="Senha", icon_left="lock", password=True, mode="rectangle")
        
        # Checkbox Lembrar-me
        box_lembrar = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40), spacing=dp(8))
        self.chk_lembrar = MDCheckbox(size_hint=(None, None), size=(dp(36), dp(36)), active=True)
        lbl_lembrar = MDLabel(text="Lembrar meus dados", theme_text_color="Secondary", font_style="Body2")
        box_lembrar.add_widget(self.chk_lembrar)
        box_lembrar.add_widget(lbl_lembrar)
        
        card.add_widget(self.txt_usuario)
        card.add_widget(self.txt_senha)
        card.add_widget(box_lembrar)
        
        box_botoes = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(45))
        btn_entrar = MDFillRoundFlatButton(text="Entrar", size_hint_x=0.5, on_release=self.autenticar)
        btn_cadastrar = MDFillRoundFlatButton(text="Cadastrar", size_hint_x=0.5, md_bg_color=(0.3, 0.3, 0.3, 1), on_release=self.cadastrar)
        box_botoes.add_widget(btn_entrar)
        box_botoes.add_widget(btn_cadastrar)
        
        card.add_widget(box_botoes)
        layout.add_widget(card)
        self.add_widget(layout)

    def on_enter(self):
        # Verifica se havia opção de login salvo
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute("SELECT valor FROM sessao WHERE chave = 'usuario_salvo'")
        usuario_salvo = cursor.fetchone()
        cursor.execute("SELECT valor FROM sessao WHERE chave = 'senha_salva'")
        senha_salva = cursor.fetchone()
        conexao.close()
        
        if usuario_salvo and senha_salva:
            self.txt_usuario.text = usuario_salvo[0]
            self.txt_senha.text = senha_salva[0]
            self.chk_lembrar.active = True

    def autenticar(self, instance):
        user = self.txt_usuario.text.strip()
        senha = self.txt_senha.text.strip()
        
        if not user or not senha:
            self.mostrar_mensagem("Erro", "Preencha todos os campos!")
            return
            
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", (user, senha))
        valido = cursor.fetchone()
        
        if valido:
            if self.chk_lembrar.active:
                cursor.execute("INSERT OR REPLACE INTO sessao (chave, valor) VALUES ('usuario_salvo', ?)", (user,))
                cursor.execute("INSERT OR REPLACE INTO sessao (chave, valor) VALUES ('senha_salva', ?)", (senha,))
            else:
                cursor.execute("DELETE FROM sessao WHERE chave = 'usuario_salvo'")
                cursor.execute("DELETE FROM sessao WHERE chave = 'senha_salva'")
            conexao.commit()
            conexao.close()
            
            # Define o usuário ativo globalmente no App
            MDApp.get_running_app().usuario_ativo = user
            self.manager.current = "principal"
        else:
            conexao.close()
            self.mostrar_mensagem("Erro", "Usuário ou senha incorretos.")

    def cadastrar(self, instance):
        user = self.txt_usuario.text.strip()
        senha = self.txt_senha.text.strip()
        
        if not user or not senha:
            self.mostrar_mensagem("Erro", "Preencha os campos para cadastrar!")
            return
            
        try:
            conexao = sqlite3.connect(DB_NAME)
            cursor = conexao.cursor()
            cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", (user, senha))
            conexao.commit()
            conexao.close()
            self.mostrar_mensagem("Sucesso", "Usuário cadastrado com sucesso! Clique em Entrar.")
        except sqlite3.IntegrityError:
            self.mostrar_mensagem("Erro", "Este nome de usuário já existe.")

    def mostrar_mensagem(self, titulo, texto):
        dialogo = MDDialog(title=titulo, text=texto, buttons=[MDFlatButton(text="OK", on_release=lambda x: dialogo.dismiss())])
        dialogo.open()


# ============================================================
# TELA PRINCIPAL (TELA DE INÍCIO)
# ============================================================
class TelaPrincipal(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cartao_selecionado = ""
        self.tipo_parcela_selecionado = "Única"
        self.mes_inicio_selecionado = datetime.now().strftime("%m/%Y")
        self.mes_filtro_atual = datetime.now().strftime("%m/%Y")
        self.id_lancamento_edicao = None
        
        scroll_principal = MDScrollView()
        layout_geral = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(16), size_hint_y=None)
        layout_geral.bind(minimum_height=layout_geral.setter('height'))
        
        # --- CABEÇALHO ---
        cabecalho = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(50), spacing=dp(10))
        self.lbl_boas_vindas = MDLabel(text="Minhas Finanças", font_style="H6", bold=True, theme_text_color="Primary")
        cabecalho.add_widget(self.lbl_boas_vindas)
        
        btn_config = MDIconButton(icon="cog", on_release=self.ir_para_configuracoes)
        btn_logout = MDIconButton(icon="logout", on_release=self.fazer_logout)
        cabecalho.add_widget(btn_config)
        cabecalho.add_widget(btn_logout)
        layout_geral.add_widget(cabecalho)
        
        # --- CARD DE RESUMO ---
        card_resumo = MDCard(
            orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None, height=dp(140),
            radius=[dp(16)], elevation=3, md_bg_color=(0.11, 0.15, 0.15, 1)
        )
        self.lbl_saldo = MDLabel(text="Saldo Atual: R$ 0,00", font_style="H6", bold=True, theme_text_color="Custom", text_color=(1, 1, 1, 1))
        self.lbl_receitas = MDLabel(text="Receitas: R$ 0,00", font_style="Subtitle2", theme_text_color="Custom", text_color=(0.15, 0.68, 0.37, 1))
        self.lbl_despesas = MDLabel(text="Despesas: R$ 0,00", font_style="Subtitle2", theme_text_color="Custom", text_color=(0.9, 0.29, 0.23, 1))
        card_resumo.add_widget(self.lbl_saldo)
        card_resumo.add_widget(self.lbl_receitas)
        card_resumo.add_widget(self.lbl_despesas)
        layout_geral.add_widget(card_resumo)
        
        # --- CARD DO FORMULÁRIO ---
        self.card_form = MDCard(orientation="vertical", padding=dp(16), spacing=dp(10), size_hint_y=None, height=dp(440), radius=[dp(16)], elevation=2)
        self.lbl_titulo_form = MDLabel(text="Novo Lançamento", font_style="Subtitle1", bold=True, theme_text_color="Primary")
        self.card_form.add_widget(self.lbl_titulo_form)
        
        self.txt_descricao = MDTextField(hint_text="Descrição", icon_left="lead-pencil", mode="rectangle")
        self.txt_valor = MDTextField(hint_text="Valor total ou da parcela (ex: 49.90)", icon_left="currency-usd", input_filter="float", mode="rectangle")
        self.txt_data = MDTextField(text=datetime.now().strftime("%d/%m/%Y"), hint_text="Data do Gasto (DD/MM/AAAA)", icon_left="calendar", mode="rectangle")
        
        self.btn_selecionar_cartao = MDFillRoundFlatButton(text="Selecionar Conta/Cartão ▾", pos_hint={"center_x": 0.5}, size_hint_x=1, on_release=self.toggle_lista_cartoes)
        self.container_dropdown = MDBoxLayout(orientation="vertical", size_hint_y=None, height=0)
        self.scroll_dropdown = MDScrollView(size_hint_y=None, height=0)
        self.lista_dropdown = MDList()
        self.scroll_dropdown.add_widget(self.lista_dropdown)
        self.container_dropdown.add_widget(self.scroll_dropdown)
        
        self.btn_tipo_parcela = MDFillRoundFlatButton(text="Tipo de Cobrança: Única ▾", pos_hint={"center_x": 0.5}, size_hint_x=1, on_release=self.toggle_lista_tipo_parcela)
        self.container_tipo_dropdown = MDBoxLayout(orientation="vertical", size_hint_y=None, height=0)
        self.scroll_tipo_dropdown = MDScrollView(size_hint_y=None, height=0)
        self.lista_tipo_dropdown = MDList()
        self.scroll_tipo_dropdown.add_widget(self.lista_tipo_dropdown)
        self.container_tipo_dropdown.add_widget(self.scroll_tipo_dropdown)
        
        self.box_parcelamento = MDBoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None, height=0)
        self.box_parcelamento.opacity = 0
        self.box_parcelamento.disabled = True
        self.txt_num_parcelas = MDTextField(hint_text="Número de Parcelas", icon_left="numeric", input_filter="int", mode="rectangle")
        self.btn_mes_inicio = MDFillRoundFlatButton(text=f"Mês de Início: {self.mes_inicio_selecionado} ▾", pos_hint={"center_x": 0.5}, size_hint_x=1, on_release=self.toggle_lista_mes_inicio)
        self.container_mes_dropdown = MDBoxLayout(orientation="vertical", size_hint_y=None, height=0)
        self.scroll_mes_dropdown = MDScrollView(size_hint_y=None, height=0)
        self.lista_mes_dropdown = MDList()
        self.scroll_mes_dropdown.add_widget(self.lista_mes_dropdown)
        self.container_mes_dropdown.add_widget(self.scroll_mes_dropdown)
        self.box_parcelamento.add_widget(self.txt_num_parcelas)
        self.box_parcelamento.add_widget(self.btn_mes_inicio)
        self.box_parcelamento.add_widget(self.container_mes_dropdown)

        self.card_form.add_widget(self.txt_descricao)
        self.card_form.add_widget(self.txt_valor)
        self.card_form.add_widget(self.txt_data)
        self.card_form.add_widget(self.btn_selecionar_cartao)
        self.card_form.add_widget(self.container_dropdown)
        self.card_form.add_widget(self.btn_tipo_parcela)
        self.card_form.add_widget(self.container_tipo_dropdown)
        self.card_form.add_widget(self.box_parcelamento)
        
        self.area_botoes = MDBoxLayout(spacing=dp(10), size_hint_y=None, height=dp(40))
        self.btn_despesa = MDFillRoundFlatButton(text="Gasto/Despesa", md_bg_color=(0.9, 0.29, 0.23, 1), on_release=lambda x: self.salvar(tipo="Despesa"))
        self.btn_receita = MDFillRoundFlatButton(text="Receita", md_bg_color=(0.15, 0.68, 0.37, 1), on_release=lambda x: self.salvar(tipo="Receita"))
        self.area_botoes.add_widget(self.btn_despesa)
        self.area_botoes.add_widget(self.btn_receita)
        self.card_form.add_widget(self.area_botoes)
        
        self.area_botoes_edicao = MDBoxLayout(spacing=dp(8), size_hint_y=None, height=0)
        self.area_botoes_edicao.opacity = 0
        self.area_botoes_edicao.disabled = True
        self.btn_atualizar = MDFillRoundFlatButton(text="Salvar Alteração", md_bg_color=(0.15, 0.68, 0.37, 1), size_hint_x=0.4, on_release=self.salvar_edicao)
        self.btn_apagar = MDFillRoundFlatButton(text="Apagar Gasto", md_bg_color=(0.9, 0.29, 0.23, 1), size_hint_x=0.3, on_release=self.confirmar_exclusao_lancamento)
        self.btn_cancelar = MDFillRoundFlatButton(text="Cancelar", md_bg_color=(0.5, 0.5, 0.5, 1), size_hint_x=0.3, on_release=self.cancelar_edicao)
        self.area_botoes_edicao.add_widget(self.btn_atualizar)
        self.area_botoes_edicao.add_widget(self.btn_apagar)
        self.area_botoes_edicao.add_widget(self.btn_cancelar)
        self.card_form.add_widget(self.area_botoes_edicao)
        
        layout_geral.add_widget(self.card_form)
        
        # --- SELETOR DE MÊS ATUAL ---
        self.card_filtro = MDCard(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None, height=dp(75), radius=[dp(12)], elevation=1, md_bg_color=(0.15, 0.18, 0.18, 1))
        self.btn_selecionar_mes_filtro = MDFillRoundFlatButton(text=f"Visualizando Mês: {self.mes_filtro_atual} ▾", pos_hint={"center_x": 0.5}, size_hint_x=1, on_release=self.toggle_filtro_meses)
        self.container_filtro_dropdown = MDBoxLayout(orientation="vertical", size_hint_y=None, height=0)
        self.scroll_filtro_dropdown = MDScrollView(size_hint_y=None, height=0)
        self.lista_filtro_dropdown = MDList()
        self.scroll_filtro_dropdown.add_widget(self.lista_filtro_dropdown)
        self.container_filtro_dropdown.add_widget(self.scroll_filtro_dropdown)
        self.card_filtro.add_widget(self.btn_selecionar_mes_filtro)
        self.card_filtro.add_widget(self.container_filtro_dropdown)
        layout_geral.add_widget(self.card_filtro)
        
        # --- HISTÓRICO ---
        layout_geral.add_widget(MDLabel(text="Lançamentos (Toque para Editar/Apagar)", font_style="Subtitle1", bold=True, theme_text_color="Secondary", size_hint_y=None, height=dp(30)))
        self.lista_historico = MDList()
        layout_geral.add_widget(self.lista_historico)
        
        # --- ASSINATURA ---
        box_rodape = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(50), padding=[0, dp(15), 0, 0])
        box_rodape.add_widget(MDLabel(text="Created by Eng. Evandro Santos", font_style="Caption", halign="center", theme_text_color="Secondary", size_hint_y=None, height=dp(20)))
        layout_geral.add_widget(box_rodape)
        
        scroll_principal.add_widget(layout_geral)
        self.add_widget(scroll_principal)

    def on_enter(self):
        self.usuario_ativo = MDApp.get_running_app().usuario_ativo
        self.lbl_boas_vindas.text = f"Finanças de {self.usuario_ativo}"
        self.fechar_dropdowns()
        self.cancelar_edicao(None)
        self.atualizar_resumo_e_lista()

    def fazer_logout(self, instance):
        MDApp.get_running_app().usuario_ativo = ""
        self.manager.current = "login"

    def ir_para_configuracoes(self, instance):
        self.manager.current = "gerenciar_cartoes"

    def fechar_dropdowns(self):
        self.fechar_dropdown()
        self.fechar_tipo_parcela_dropdown()
        self.fechar_mes_inicio_dropdown()
        self.fechar_filtro_dropdown()

    def obter_cartoes_cadastrados(self):
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE usuario = ? AND chave = 'cartoes'", (self.usuario_ativo,))
        resultado = cursor.fetchone()
        conexao.close()
        if resultado and resultado[0]:
            return [c.strip() for c in resultado[0].split(";") if c.strip()]
        return []

    def toggle_lista_cartoes(self, instance):
        if self.container_dropdown.height > 0:
            self.fechar_dropdown()
        else:
            self.fechar_dropdowns()
            self.abrir_dropdown()

    def abrir_dropdown(self):
        cartoes = self.obter_cartoes_cadastrados()
        self.lista_dropdown.clear_widgets()
        if not cartoes:
            item = OneLineListItem(text="Nenhuma conta cadastrada! Vá em configurações.")
            self.lista_dropdown.add_widget(item)
        else:
            for c in cartoes:
                item = OneLineListItem(text=c, on_release=self.selecionar_cartao_item)
                self.lista_dropdown.add_widget(item)
        altura_calculada = min(dp(120), len(cartoes) * dp(48) if cartoes else dp(48))
        self.container_dropdown.height = altura_calculada
        self.scroll_dropdown.height = altura_calculada
        self.ajustar_altura_card_formulario(mais_altura=altura_calculada)

    def fechar_dropdown(self):
        self.container_dropdown.height = 0
        self.scroll_dropdown.height = 0
        self.ajustar_altura_card_formulario()

    def selecionar_cartao_item(self, instance):
        self.cartao_selecionado = instance.text
        self.btn_selecionar_cartao.text = f"Selecionado: {self.cartao_selecionado} ▾"
        self.fechar_dropdown()

    def toggle_lista_tipo_parcela(self, instance):
        if self.container_tipo_dropdown.height > 0:
            self.fechar_tipo_parcela_dropdown()
        else:
            self.fechar_dropdowns()
            self.abrir_tipo_parcela_dropdown()

    def abrir_tipo_parcela_dropdown(self):
        self.lista_tipo_dropdown.clear_widgets()
        for opt in ["Única", "Parcelado"]:
            self.lista_tipo_dropdown.add_widget(OneLineListItem(text=opt, on_release=self.selecionar_tipo_parcela_item))
        self.container_tipo_dropdown.height = dp(96)
        self.scroll_tipo_dropdown.height = dp(96)
        self.ajustar_altura_card_formulario(mais_altura=dp(96))

    def fechar_tipo_parcela_dropdown(self):
        self.container_tipo_dropdown.height = 0
        self.scroll_tipo_dropdown.height = 0
        self.ajustar_altura_card_formulario()

    def selecionar_tipo_parcela_item(self, instance):
        self.tipo_parcela_selecionado = instance.text
        self.btn_tipo_parcela.text = f"Tipo de Cobrança: {self.tipo_parcela_selecionado} ▾"
        self.fechar_tipo_parcela_dropdown()
        if self.tipo_parcela_selecionado == "Parcelado":
            self.box_parcelamento.height = dp(110)
            self.box_parcelamento.opacity = 1
            self.box_parcelamento.disabled = False
        else:
            self.box_parcelamento.height = 0
            self.box_parcelamento.opacity = 0
            self.box_parcelamento.disabled = True
        self.ajustar_altura_card_formulario()

    def toggle_lista_mes_inicio(self, instance):
        if self.container_mes_dropdown.height > 0:
            self.fechar_mes_inicio_dropdown()
        else:
            self.fechar_dropdowns()
            self.abrir_mes_inicio_dropdown()

    def abrir_mes_inicio_dropdown(self):
        self.lista_mes_dropdown.clear_widgets()
        hoje = datetime.now()
        for i in range(12):
            mes = (hoje + relativedelta(months=i)).strftime("%m/%Y")
            self.lista_mes_dropdown.add_widget(OneLineListItem(text=mes, on_release=self.selecionar_mes_inicio_item))
        self.container_mes_dropdown.height = dp(140)
        self.scroll_mes_dropdown.height = dp(140)
        self.ajustar_altura_card_formulario(mais_altura=dp(140))

    def fechar_mes_inicio_dropdown(self):
        self.container_mes_dropdown.height = 0
        self.scroll_mes_dropdown.height = 0
        self.ajustar_altura_card_formulario()

    def selecionar_mes_inicio_item(self, instance):
        self.mes_inicio_selecionado = instance.text
        self.btn_mes_inicio.text = f"Mês de Início: {self.mes_inicio_selecionado} ▾"
        self.fechar_mes_inicio_dropdown()

    def ajustar_altura_card_formulario(self, mais_altura=0):
        altura_base = dp(440)
        if self.tipo_parcela_selecionado == "Parcelado":
            altura_base += dp(110)
        self.card_form.height = altura_base + mais_altura

    def toggle_filtro_meses(self, instance):
        if self.container_filtro_dropdown.height > 0:
            self.fechar_filtro_dropdown()
        else:
            self.fechar_dropdowns()
            self.abrir_filtro_dropdown()

    def abrir_filtro_dropdown(self):
        self.lista_filtro_dropdown.clear_widgets()
        meses_disponiveis = set()
        for ano in range(2026, 2031):
            for m in range(1, 13):
                meses_disponiveis.add(f"{m:02d}/{ano}")
        try:
            conexao = sqlite3.connect(DB_NAME)
            cursor = conexao.cursor()
            cursor.execute("SELECT DISTINCT mes_ano FROM lancamentos WHERE usuario = ?", (self.usuario_ativo,))
            for l in cursor.fetchall():
                if l[0]: meses_disponiveis.add(l[0])
            conexao.close()
        except Exception as e:
            print(e)
        meses_ordenados = sorted(list(meses_disponiveis), key=lambda x: datetime.strptime(x, "%m/%Y"), reverse=True)
        for mes in meses_ordenados:
            self.lista_filtro_dropdown.add_widget(OneLineListItem(text=mes, on_release=self.selecionar_mes_filtro_item))
        altura_calculada = min(dp(160), len(meses_ordenados) * dp(48))
        self.container_filtro_dropdown.height = altura_calculada
        self.scroll_filtro_dropdown.height = altura_calculada
        self.card_filtro.height = dp(75) + altura_calculada

    def fechar_filtro_dropdown(self):
        self.container_filtro_dropdown.height = 0
        self.scroll_filtro_dropdown.height = 0
        self.card_filtro.height = dp(75)

    def selecionar_mes_filtro_item(self, instance):
        self.mes_filtro_atual = instance.text
        self.btn_selecionar_mes_filtro.text = f"Visualizando Mês: {self.mes_filtro_atual} ▾"
        self.fechar_filtro_dropdown()
        self.atualizar_resumo_e_lista()

    def salvar(self, tipo):
        desc = self.txt_descricao.text.strip()
        valor_texto = self.txt_valor.text.strip()
        data_digitada = self.txt_data.text.strip()
        cartao = self.cartao_selecionado if tipo == "Despesa" else (self.cartao_selecionado if self.cartao_selecionado else "Recebimento")
        
        if not desc or not valor_texto or not data_digitada: return
        if tipo == "Despesa" and not self.cartao_selecionado:
            self.btn_selecionar_cartao.text = "Selecione uma conta antes! ⚠️"
            return
        try:
            valor = float(valor_texto.replace(",", "."))
        except ValueError: return
        try:
            data_objeto = datetime.strptime(data_digitada, "%d/%m/%Y")
            data_formatada = data_objeto.strftime("%d/%m/%Y")
            mes_ano = data_objeto.strftime("%m/%Y")
        except ValueError:
            self.txt_data.error = True
            return
            
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        
        if self.tipo_parcela_selecionado == "Parcelado":
            num_text = self.txt_num_parcelas.text.strip()
            if not num_text: return
            try:
                num_parcelas = int(num_text)
                if num_parcelas <= 0: return
            except ValueError: return
            
            data_corrente = datetime.strptime(self.mes_inicio_selecionado, "%m/%Y")
            for i in range(1, num_parcelas + 1):
                mes_formatado = data_corrente.strftime("%m/%Y")
                dia_calc = min(data_objeto.day, 28)
                data_calc_final = f"{dia_calc:02d}/{mes_formatado}"
                descricao_parcela = f"{desc} ({i:02d}/{num_parcelas:02d})"
                
                cursor.execute("""
                    INSERT INTO lancamentos (usuario, data, mes_ano, tipo, cartao, descricao, valor, status, observacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (self.usuario_ativo, data_calc_final, mes_formatado, tipo, cartao, descricao_parcela, valor, "Pago", ""))
                data_corrente += relativedelta(months=1)
            conexao.commit()
            conexao.close()
            self.mes_filtro_atual = self.mes_inicio_selecionado
        else:
            cursor.execute("""
                INSERT INTO lancamentos (usuario, data, mes_ano, tipo, cartao, descricao, valor, status, observacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.usuario_ativo, data_formatada, mes_ano, tipo, cartao, desc, valor, "Pago", ""))
            conexao.commit()
            conexao.close()
            self.mes_filtro_atual = mes_ano

        self.limpar_formulario()
        self.btn_selecionar_mes_filtro.text = f"Visualizando Mês: {self.mes_filtro_atual} ▾"
        self.atualizar_resumo_e_lista()

    def selecionar_para_edicao(self, id_lancamento):
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute("SELECT descricao, valor, data, cartao FROM lancamentos WHERE id = ? AND usuario = ?", (id_lancamento, self.usuario_ativo))
        item = cursor.fetchone()
        conexao.close()
        
        if item:
            desc, valor, data_salva, cartao = item
            self.id_lancamento_edicao = id_lancamento
            self.txt_descricao.text = desc
            self.txt_valor.text = str(valor)
            self.txt_data.text = data_salva
            self.cartao_selecionado = cartao
            self.btn_selecionar_cartao.text = f"Selecionado: {cartao} ▾"
            self.lbl_titulo_form.text = f"Editando Lançamento (ID: {id_lancamento})"
            self.area_botoes.opacity = 0; self.area_botoes.disabled = True; self.area_botoes.height = 0
            self.area_botoes_edicao.height = dp(40); self.area_botoes_edicao.opacity = 1; self.area_botoes_edicao.disabled = False
            self.ajustar_altura_card_formulario()

    def salvar_edicao(self, instance):
        if self.id_lancamento_edicao is None: return
        desc = self.txt_descricao.text.strip()
        valor_texto = self.txt_valor.text.strip()
        data_digitada = self.txt_data.text.strip()
        if not desc or not valor_texto or not data_digitada: return
        try: valor = float(valor_texto.replace(",", "."))
        except ValueError: return
        try:
            data_objeto = datetime.strptime(data_digitada, "%d/%m/%Y")
            data_formatada = data_objeto.strftime("%d/%m/%Y")
            mes_ano = data_objeto.strftime("%m/%Y")
        except ValueError: return
        
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute("""
            UPDATE lancamentos SET descricao = ?, valor = ?, data = ?, mes_ano = ?, cartao = ?
            WHERE id = ? AND usuario = ?
        """, (desc, valor, data_formatada, mes_ano, self.cartao_selecionado, self.id_lancamento_edicao, self.usuario_ativo))
        conexao.commit()
        conexao.close()
        self.cancelar_edicao(None)
        self.atualizar_resumo_e_lista()

    def confirmar_exclusao_lancamento(self, instance):
        if self.id_lancamento_edicao is None: return
        self.dialogo = MDDialog(
            title="Apagar Lançamento?", text="Tem certeza de que deseja apagar permanentemente?",
            buttons=[
                MDFlatButton(text="CANCELAR", on_release=lambda x: self.dialogo.dismiss()),
                MDRaisedButton(text="APAGAR", md_bg_color=(0.9, 0.29, 0.23, 1), on_release=self.apagar_lancamento)
            ]
        )
        self.dialogo.open()

    def apagar_lancamento(self, instance):
        self.dialogo.dismiss()
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM lancamentos WHERE id = ? AND usuario = ?", (self.id_lancamento_edicao, self.usuario_ativo))
        conexao.commit()
        conexao.close()
        self.cancelar_edicao(None)
        self.atualizar_resumo_e_lista()

    def cancelar_edicao(self, instance):
        self.id_lancamento_edicao = None
        self.lbl_titulo_form.text = "Novo Lançamento"
        self.limpar_formulario()
        self.area_botoes_edicao.opacity = 0; self.area_botoes_edicao.disabled = True; self.area_botoes_edicao.height = 0
        self.area_botoes.height = dp(40); self.area_botoes.opacity = 1; self.area_botoes.disabled = False
        self.ajustar_altura_card_formulario()

    def limpar_formulario(self):
        self.txt_descricao.text = ""
        self.txt_valor.text = ""
        self.txt_data.text = datetime.now().strftime("%d/%m/%Y")
        self.cartao_selecionado = ""
        self.btn_selecionar_cartao.text = "Selecionar Conta/Cartão ▾"
        self.tipo_parcela_selecionado = "Única"
        self.btn_tipo_parcela.text = "Tipo de Cobrança: Única ▾"
        self.txt_num_parcelas.text = ""
        self.box_parcelamento.height = 0; self.box_parcelamento.opacity = 0; self.box_parcelamento.disabled = True

    def atualizar_resumo_e_lista(self):
        self.lista_historico.clear_widgets()
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT id, descricao, valor, tipo, cartao, data FROM lancamentos WHERE usuario = ? AND mes_ano = ? ORDER BY id DESC", 
            (self.usuario_ativo, self.mes_filtro_atual)
        )
        linhas = cursor.fetchall()
        total_receita = 0.0; total_despesa = 0.0
        
        for linha in reversed(linhas):
            id_lan, desc, valor, tipo, cartao, data_salva = linha
            icone = "trending-down" if tipo == "Despesa" else "trending-up"
            cor = (0.9, 0.29, 0.23, 1) if tipo == "Despesa" else (0.15, 0.68, 0.37, 1)
            
            item = TwoLineAvatarListItem(
                text=desc, secondary_text=f"R$ {valor:.2f} — {cartao} ({data_salva})",
                on_release=lambda x, i=id_lan: self.selecionar_para_edicao(i)
            )
            item.add_widget(IconLeftWidget(icon=icone, theme_text_color="Custom", text_color=cor))
            self.lista_historico.add_widget(item)
            
        cursor.execute("SELECT tipo, SUM(valor) FROM lancamentos WHERE usuario = ? AND mes_ano = ? GROUP BY tipo", (self.usuario_ativo, self.mes_filtro_atual))
        for t, val in cursor.fetchall():
            if t == "Receita": total_receita = val
            elif t == "Despesa": total_despesa = val
        conexao.close()
        
        self.lbl_receitas.text = f"Receitas: R$ {total_receita:.2f}"
        self.lbl_despesas.text = f"Despesas: R$ {total_despesa:.2f}"
        saldo = total_receita - total_despesa
        self.lbl_saldo.text = f"Saldo: R$ {saldo:.2f}"
        self.lbl_saldo.text_color = (0.15, 0.68, 0.37, 1) if saldo >= 0 else (0.9, 0.29, 0.23, 1)


# ============================================================
# TELA DE GERENCIAMENTO DE CARTÕES (CONFIGURAÇÃO)
# ============================================================
class TelaGerenciarCartoes(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cartao_em_edicao = None
        layout = MDBoxLayout(orientation="vertical", padding=dp(20), spacing=dp(15))
        
        self.lbl_titulo = MDLabel(text="Gerenciar Contas e Cartões", font_style="H6", bold=True, size_hint_y=None, height=dp(40))
        layout.add_widget(self.lbl_titulo)
        
        self.txt_novo = MDTextField(hint_text="Nome do novo cartão/conta", icon_left="plus-circle-outline", mode="rectangle")
        layout.add_widget(self.txt_novo)
        
        self.box_botoes = MDBoxLayout(spacing=dp(10), size_hint_y=None, height=dp(45))
        self.btn_add = MDFillRoundFlatButton(text="Adicionar Novo", on_release=self.adicionar_ou_editar_cartao)
        self.btn_cancelar_edicao = MDFillRoundFlatButton(text="Cancelar", md_bg_color=(0.5, 0.5, 0.5, 1), opacity=0, disabled=True, on_release=self.cancelar_edicao_cartao)
        self.box_botoes.add_widget(self.btn_add)
        self.box_botoes.add_widget(self.btn_cancelar_edicao)
        layout.add_widget(self.box_botoes)
        
        layout.add_widget(MDLabel(text="Contas Ativas:", font_style="Subtitle1", theme_text_color="Secondary", size_hint_y=None, height=dp(25)))
        scroll = MDScrollView()
        self.lista_cartoes = MDList()
        scroll.add_widget(self.lista_cartoes)
        layout.add_widget(scroll)
        
        layout.add_widget(MDRaisedButton(text="Voltar ao Painel", pos_hint={"center_x": 0.5}, on_release=self.voltar))
        self.add_widget(layout)

    def on_enter(self):
        self.usuario_ativo = MDApp.get_running_app().usuario_ativo
        self.cancelar_edicao_cartao(None)
        self.atualizar_lista()

    def obter_cartoes(self):
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute("SELECT valor FROM configuracoes WHERE usuario = ? AND chave = 'cartoes'", (self.usuario_ativo,))
        resultado = cursor.fetchone()
        conexao.close()
        return resultado[0].split(";") if resultado and resultado[0] else []

    def atualizar_lista(self):
        self.lista_cartoes.clear_widgets()
        for c in self.obter_cartoes():
            item = TwoLineAvatarListItem(text=c, secondary_text="Toque para Opções", on_release=lambda x, nome=c: self.abrir_opcoes_cartao(nome))
            item.add_widget(IconLeftWidget(icon="credit-card-outline"))
            self.lista_cartoes.add_widget(item)

    def abrir_opcoes_cartao(self, nome):
        self.dialogo_cartao = MDDialog(
            title=f"Conta: {nome}",
            text="Escolha uma opção:",
            buttons=[
                MDFlatButton(text="APAGAR", text_color=(0.9, 0.29, 0.23, 1), on_release=lambda x: self.deletar_cartao(nome)),
                MDFlatButton(text="EDITAR", on_release=lambda x: self.preparar_edicao_cartao(nome)),
                MDFlatButton(text="FECHAR", on_release=lambda x: self.dialogo_cartao.dismiss())
            ]
        )
        self.dialogo_cartao.open()

    def preparar_edicao_cartao(self, nome):
        self.dialogo_cartao.dismiss()
        self.cartao_em_edicao = nome
        self.txt_novo.text = nome
        self.lbl_titulo.text = f"Editando: {nome}"
        self.btn_add.text = "Salvar Alteração"
        self.btn_cancelar_edicao.opacity = 1; self.btn_cancelar_edicao.disabled = False

    def adicionar_ou_editar_cartao(self, instance):
        novo = self.txt_novo.text.strip()
        if not novo: return
        cartoes = self.obter_cartoes()
        
        if self.cartao_em_edicao:
            if self.cartao_em_edicao in cartoes:
                cartoes[cartoes.index(self.cartao_em_edicao)] = novo
                conexao = sqlite3.connect(DB_NAME)
                cursor = conexao.cursor()
                cursor.execute("UPDATE lancamentos SET cartao = ? WHERE cartao = ? AND usuario = ?", (novo, self.cartao_em_edicao, self.usuario_ativo))
                conexao.commit(); conexao.close()
            self.cancelar_edicao_cartao(None)
        else:
            if novo not in cartoes: cartoes.append(novo)
                
        self.salvar_cartoes(cartoes)
        self.txt_novo.text = ""
        self.atualizar_lista()

    def deletar_cartao(self, nome):
        if hasattr(self, 'dialogo_cartao'): self.dialogo_cartao.dismiss()
        cartoes = self.obter_cartoes()
        if nome in cartoes:
            cartoes.remove(nome)
            self.salvar_cartoes(cartoes)
            self.atualizar_lista()

    def cancelar_edicao_cartao(self, instance):
        self.cartao_em_edicao = None
        self.txt_novo.text = ""
        self.lbl_titulo.text = "Gerenciar Contas e Cartões"
        self.btn_add.text = "Adicionar Novo"
        self.btn_cancelar_edicao.opacity = 0; self.btn_cancelar_edicao.disabled = True

    def salvar_cartoes(self, lista):
        cartoes_string = ";".join(lista)
        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute("INSERT OR REPLACE INTO configuracoes (usuario, chave, valor) VALUES (?, 'cartoes', ?)", (self.usuario_ativo, cartoes_string))
        conexao.commit(); conexao.close()

    def voltar(self, instance):
        self.manager.current = "principal"


# ============================================================
# CLASSE DO APP
# ============================================================
class ControleGastosApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Dark"
        
        inicializar_banco()
        
        # Variável para rastrear quem está logado globalmente
        self.usuario_ativo = ""
        
        sm = ScreenManager()
        sm.add_widget(TelaLogin(name="login"))
        sm.add_widget(TelaPrincipal(name="principal"))
        sm.add_widget(TelaGerenciarCartoes(name="gerenciar_cartoes"))
            
        return sm

if __name__ == "__main__":
    ControleGastosApp().run()
