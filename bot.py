import discord
from discord import app_commands
from discord.ui import View, Button

TOKEN = "SUA_TOKEN_AQUI"


# ================= CONFIGURAÇÕES =================
CARGO_STAFF = 1472261982873981011   # Cargo que pode confirmar pagamento
CARGO_ACESSO = 1472261680980430869 # Cargo que será dado ao comprador
CHAVE_PIX = "Espere o dono enviar a chave pix !"  
CARGOS_QUE_PODEM_VER = [CARGO_STAFF] # Quem pode ver o ticket
ID_DO_SERVIDOR = 1471676462942781470

# ==================================================

# =================== BOT ===================
class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=ID_DO_SERVIDOR)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        self.add_view(ComprarView())  # View persistente

bot = Bot()

@bot.event
async def on_ready():
    print(f"Bot online como {bot.user}")

# =================== BOTÃO DE CONFIRMAÇÃO ===================
class ConfirmarPagamentoButton(Button):
    def __init__(self, comprador_id):
        super().__init__(label="Confirmar Pagamento", style=discord.ButtonStyle.success)
        self.comprador_id = comprador_id

    async def callback(self, interaction: discord.Interaction):
        # Apenas staff pode confirmar
        if CARGO_STAFF not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ Apenas staff pode confirmar o pagamento.", ephemeral=True)
            return

        guild = interaction.guild
        comprador = guild.get_member(self.comprador_id)
        if not comprador:
            await interaction.response.send_message("❌ Usuário não encontrado.", ephemeral=True)
            return

        cargo_acesso = guild.get_role(CARGO_ACESSO)
        if not cargo_acesso:
            await interaction.response.send_message("❌ Cargo de acesso não encontrado.", ephemeral=True)
            return

        if cargo_acesso in comprador.roles:
            await interaction.response.send_message(f"⚠️ {comprador.mention} já possui o cargo de acesso.", ephemeral=True)
            return

        try:
            await comprador.add_roles(cargo_acesso, reason=f"Pagamento confirmado por {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não consigo dar o cargo, verifique a hierarquia do bot.", ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Ocorreu um erro: {e}", ephemeral=True)
            return

        await interaction.response.send_message(
            f"✅ Pagamento confirmado! {comprador.mention} recebeu o cargo de acesso.", ephemeral=False
        )

        # Fecha o ticket após 5 segundos
        await interaction.channel.delete(delay=5)

# =================== VIEW COM BOTÃO DE COMPRA ===================
class ComprarView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Comprar Acesso", style=discord.ButtonStyle.primary, custom_id="botao_comprar")
    async def comprar(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        categoria = discord.utils.get(guild.categories, name="Tickets Compras")
        if not categoria:
            categoria = await guild.create_category("Tickets Compras")

        # Checa se já existe ticket
        for canal in categoria.channels:
            if canal.topic == str(interaction.user.id):
                await interaction.response.send_message("❌ Você já possui um ticket aberto.", ephemeral=True)
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        for cargo_id in CARGOS_QUE_PODEM_VER:
            cargo = guild.get_role(cargo_id)
            if cargo:
                overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        canal = await guild.create_text_channel(
            name=f"compra-{interaction.user.name}".lower(),
            category=categoria,
            overwrites=overwrites,
            topic=str(interaction.user.id)
        )

        # Embed com chave PIX
        embed = discord.Embed(
            title="💰 Compra de Acesso",
            description=f"{interaction.user.mention}, faça o pagamento usando a chave PIX abaixo. "
                        f"Após o pagamento, um staff confirmará e você receberá o cargo de acesso.",
            color=0x5865F2
        )
        embed.add_field(name="Chave PIX", value=CHAVE_PIX, inline=False)

        # Botão Confirmar Pagamento
        view = View()
        view.add_item(ConfirmarPagamentoButton(interaction.user.id))

        await canal.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Seu ticket foi criado: {canal.mention}", ephemeral=True)

# =================== COMANDO PARA ENVIAR BOTÃO ===================
@bot.tree.command(name="painel_compra", description="Enviar botão de compra de acesso")
async def painel_compra(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛒 Comprar Acesso",
        description="Clique no botão abaixo para iniciar a compra e receber seu acesso, " \
        "aqui na lunar forn estamos forncendo produtos muito abaixo do preço , então para adquirir o acesso cobramos uma taixa de 1,30 centavos ! ",
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed, view=ComprarView())

# /trancar
@bot.tree.command(name="trancar", description="Tranca o canal atual para todos, exceto staff")
async def trancar(interaction: discord.Interaction):
    if CARGO_STAFF not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ Você não tem permissão para usar esse comando.", ephemeral=True)
        return
    
    canal = interaction.channel
    overwrites = canal.overwrites_for(interaction.guild.default_role)
    overwrites.send_messages = False
    await canal.set_permissions(interaction.guild.default_role, overwrite=overwrites)
    await interaction.response.send_message(f"🔒 {canal.mention} foi trancado com sucesso!")

# /destrancar
@bot.tree.command(name="destrancar", description="Destranca o canal atual para todos")
async def destrancar(interaction: discord.Interaction):
    if CARGO_STAFF not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ Você não tem permissão para usar esse comando.", ephemeral=True)
        return
    
    canal = interaction.channel
    overwrites = canal.overwrites_for(interaction.guild.default_role)
    overwrites.send_messages = True
    await canal.set_permissions(interaction.guild.default_role, overwrite=overwrites)
    await interaction.response.send_message(f"🔓 {canal.mention} foi destrancado com sucesso!")

# /limpar
@bot.tree.command(name="limpar", description="Apaga mensagens do canal")
@app_commands.describe(quantidade="Número de mensagens que deseja apagar (máx 100)")
async def limpar(interaction: discord.Interaction, quantidade: int):
    if CARGO_STAFF not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
        return

    if quantidade < 1 or quantidade > 100:
        await interaction.response.send_message("❌ Você pode apagar entre 1 e 100 mensagens por vez.", ephemeral=True)
        return

    await interaction.channel.purge(limit=quantidade)
    await interaction.response.send_message(f"✅ {quantidade} mensagens apagadas com sucesso!", ephemeral=True)

# =================== COMANDO PARA ENVIAR PAINEL ===================
@bot.tree.command(name="painel_tickets", description="Envia o painel de tickets")
async def painel_tickets(interaction: discord.Interaction):
    class TicketSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label="Denúncia", 
                    description="Crie um ticket para relatar uma denúncia", 
                    value="denuncia", 
                    emoji="⚠️"
                ),
                discord.SelectOption(
                    label="Suporte", 
                    description="Crie um ticket para receber suporte", 
                    value="suporte", 
                    emoji="🛠️"
                ),
                discord.SelectOption(
                    label="Resgatar Prêmio", 
                    description="Crie um ticket para resgatar seu prêmio", 
                    value="premio", 
                    emoji="🎁"
                ),
                discord.SelectOption(
                    label="Dúvidas", 
                    description="Crie um ticket para tirar dúvidas", 
                    value="duvida", 
                    emoji="❓"
                ),
                discord.SelectOption(
                    label="Outro motivo", 
                    description="Crie um ticket para outros assuntos", 
                    value="outro", 
                    emoji="📩"
                ),
            ]
            super().__init__(
                placeholder="Selecione um motivo para abrir o ticket...",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="menu_ticket"
            )

        async def callback(self, interaction: discord.Interaction):
            motivo = self.values[0]
            nomes_motivos = {
                "denuncia": "Denúncia",
                "suporte": "Suporte",
                "premio": "Resgatar Prêmio",
                "duvida": "Dúvida",
                "outro": "Outro Motivo"
            }

            # Categoria do ticket
            categoria = interaction.guild.get_channel(1472260986231718010)  # ID da categoria
            if not categoria:
                await interaction.response.send_message("❌ Categoria de tickets não encontrada.", ephemeral=True)
                return

            # Verifica se o usuário já tem ticket
            for canal in categoria.text_channels:
                if canal.topic == str(interaction.user.id):
                    await interaction.response.send_message("❌ Você já possui um ticket aberto.", ephemeral=True)
                    return

            # Permissões do canal
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            for cargo_id in CARGOS_QUE_PODEM_VER:
                cargo = interaction.guild.get_role(cargo_id)
                if cargo:
                    overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            # Cria canal
            canal = await interaction.guild.create_text_channel(
                name=f"{motivo}-{interaction.user.name}".lower(),
                category=categoria,
                overwrites=overwrites,
                topic=str(interaction.user.id)
            )

            # Embed de boas-vindas no ticket
            embed = discord.Embed(
                title=f"🎫 Ticket - {nomes_motivos[motivo]}",
                description=f"{interaction.user.mention} abriu um ticket para **{nomes_motivos[motivo]}**.\n"
                            f"Descreva detalhadamente o seu problema para nossa equipe ajudar.",
                color=0x5865F2
            )
            embed.set_footer(text="Sistema de Tickets")
            await canal.send(embed=embed)

            await interaction.response.send_message(f"✅ Seu ticket foi criado: {canal.mention}", ephemeral=True)

    class TicketView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(TicketSelect())

    # Embed do painel com explicação de cada ticket
    embed = discord.Embed(
        title="📩 Painel de Tickets",
        description="Selecione uma opção no menu abaixo para abrir um ticket.",
        color=0x5865F2
    )
    embed.add_field(name="⚠️ Denúncia", value="Crie um ticket para relatar uma denúncia de usuários ou problemas no servidor.", inline=False)
    embed.add_field(name="🛠️ Suporte", value="Crie um ticket para receber ajuda com comandos, dúvidas ou problemas técnicos.", inline=False)
    embed.add_field(name="🎁 Resgatar Prêmio", value="Crie um ticket para resgatar recompensas, brindes ou prêmios do servidor.", inline=False)
    embed.add_field(name="❓ Dúvidas", value="Crie um ticket para tirar dúvidas gerais sobre o servidor ou regras.", inline=False)
    embed.add_field(name="📩 Outro Motivo", value="Crie um ticket para outros assuntos que não se encaixem nas categorias acima.", inline=False)

    await interaction.response.send_message(embed=embed, view=TicketView())

# =================== COMANDO PARA PAINEL DE LOJINHA ===================
@bot.tree.command(name="painel_lojinha", description="Envia o painel de tickets da lojinha")
async def painel_lojinha(interaction: discord.Interaction):
    class LojinhaSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label="Lojinha Diária", 
                    description="Solicite acesso à lojinha diária", 
                    value="diaria", 
                    emoji="📅"
                ),
                discord.SelectOption(
                    label="Lojinha Semanal", 
                    description="Solicite acesso à lojinha semanal", 
                    value="semanal", 
                    emoji="🗓️"
                ),
                discord.SelectOption(
                    label="Lojinha Mensal", 
                    description="Solicite acesso à lojinha mensal", 
                    value="mensal", 
                    emoji="🛒"
                ),
                discord.SelectOption(
                    label="Lojinha Permanente", 
                    description="Solicite acesso à lojinha permanente", 
                    value="permanente", 
                    emoji="🏆"
                ),
            ]
            super().__init__(
                placeholder="Selecione o tipo de lojinha que deseja acessar...",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="menu_lojinha"
            )

        async def callback(self, interaction: discord.Interaction):
            tipo = self.values[0]
            nomes_tipos = {
                "diaria": "Lojinha Diária",
                "semanal": "Lojinha Semanal",
                "mensal": "Lojinha Mensal",
                "permanente": "Lojinha Permanente"
            }

            # Categoria onde os tickets da lojinha serão criados
            categoria = interaction.guild.get_channel(1472260986231718010)  # Substitua pelo ID correto da categoria
            if not categoria:
                await interaction.response.send_message("❌ Categoria de tickets não encontrada.", ephemeral=True)
                return

            # Evita que o usuário tenha múltiplos tickets abertos
            for canal in categoria.text_channels:
                if canal.topic == str(interaction.user.id):
                    await interaction.response.send_message("❌ Você já possui um ticket aberto.", ephemeral=True)
                    return

            # Permissões do canal
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            for cargo_id in CARGOS_QUE_PODEM_VER:
                cargo = interaction.guild.get_role(cargo_id)
                if cargo:
                    overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            # Cria canal do ticket
            canal = await interaction.guild.create_text_channel(
                name=f"{tipo}-{interaction.user.name}".lower(),
                category=categoria,
                overwrites=overwrites,
                topic=str(interaction.user.id)
            )

            # Embed de boas-vindas no ticket
            embed = discord.Embed(
                title=f"🛒 Ticket - {nomes_tipos[tipo]}",
                description=f"{interaction.user.mention} abriu um ticket para **{nomes_tipos[tipo]}**.\n"
                            f"Aguarde que nossa equipe liberará o acesso à lojinha.",
                color=0x5865F2
            )
            embed.set_footer(text="Sistema de Tickets - Lojinha")
            await canal.send(embed=embed)

            await interaction.response.send_message(f"✅ Seu ticket foi criado: {canal.mention}", ephemeral=True)

    class LojinhaView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(LojinhaSelect())

    # Embed explicativa do painel
    embed = discord.Embed(
        title="🛒 Painel da Lojinha",
        description="Selecione no menu abaixo qual lojinha deseja solicitar.",
        color=0x5865F2
    )
    embed.add_field(
        name="📅 Lojinha Diária", 
        value="Solicite acesso à lojinha diária, disponível todos os dias com itens especiais.", 
        inline=False
    )
    embed.add_field(
        name="🗓️ Lojinha Semanal", 
        value="Solicite acesso à lojinha semanal, com itens exclusivos que mudam toda semana.", 
        inline=False
    )
    embed.add_field(
        name="🛒 Lojinha Mensal", 
        value="Solicite acesso à lojinha mensal, onde são adicionados itens de destaque do mês.", 
        inline=False
    )
    embed.add_field(
        name="🏆 Lojinha Permanente", 
        value="Solicite acesso à lojinha permanente, com todos os itens fixos disponíveis sempre.", 
        inline=False
    )

    await interaction.response.send_message(embed=embed, view=LojinhaView())

# =================== COMANDO DE EMBED PERSONALIZADA ===================
from discord.ui import Modal, TextInput

class EmbedPersonalizadaModal(Modal, title="Criar Embed Personalizada"):
    titulo = TextInput(label="Título da Embed", required=False)
    descricao = TextInput(label="Descrição da Embed", style=discord.TextStyle.paragraph)
    cor = TextInput(label="Cor da Embed em HEX (ex: #5865F2)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        # Define a cor padrão se não for preenchida
        cor_final = 0x5865F2
        if self.cor.value:
            try:
                cor_final = int(self.cor.value.replace("#", ""), 16)
            except:
                pass  # se colocar valor inválido, usa a cor padrão

        # Cria embed
        embed = discord.Embed(
            title=self.titulo.value if self.titulo.value else None,
            description=self.descricao.value,
            color=cor_final
        )

        await interaction.response.send_message(embed=embed)

# Comando de barra para abrir o modal
@bot.tree.command(name="criar_embed", description="Crie uma embed personalizada")
async def criar_embed(interaction: discord.Interaction):
    await interaction.response.send_modal(EmbedPersonalizadaModal())

# =================== COMANDO PARA PAINEL DE LEILÕES ===================
@bot.tree.command(name="painel_leilao", description="Envia o painel de tickets de leilão")
async def painel_leilao(interaction: discord.Interaction):
    class LeilaoSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label="Leilão Único", 
                    description="Solicite um leilão único, disponível apenas uma vez", 
                    value="unico", 
                    emoji="🎯"
                ),
                discord.SelectOption(
                    label="Leilão Permanente", 
                    description="Solicite um leilão permanente, disponível sempre", 
                    value="permanente", 
                    emoji="🏆"
                ),
            ]
            super().__init__(
                placeholder="Selecione o tipo de leilão que deseja solicitar...",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="menu_leilao"
            )

        async def callback(self, interaction: discord.Interaction):
            tipo = self.values[0]
            nomes_tipos = {
                "unico": "Leilão Único",
                "permanente": "Leilão Permanente"
            }

            # Categoria onde os tickets de leilão serão criados
            categoria = interaction.guild.get_channel(1472260986231718010)  # Substitua pelo ID da categoria de leilões
            if not categoria:
                await interaction.response.send_message("❌ Categoria de tickets não encontrada.", ephemeral=True)
                return

            # Evita que o usuário abra múltiplos tickets
            for canal in categoria.text_channels:
                if canal.topic == str(interaction.user.id):
                    await interaction.response.send_message("❌ Você já possui um ticket aberto.", ephemeral=True)
                    return

            # Permissões do canal
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            for cargo_id in CARGOS_QUE_PODEM_VER:
                cargo = interaction.guild.get_role(cargo_id)
                if cargo:
                    overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            # Cria canal do ticket
            canal = await interaction.guild.create_text_channel(
                name=f"{tipo}-{interaction.user.name}".lower(),
                category=categoria,
                overwrites=overwrites,
                topic=str(interaction.user.id)
            )

            # Embed de boas-vindas no ticket
            embed = discord.Embed(
                title=f"🎯 Ticket - {nomes_tipos[tipo]}",
                description=f"{interaction.user.mention} abriu um ticket para **{nomes_tipos[tipo]}**.\n"
                            f"Aguarde nossa equipe analisar e liberar o leilão conforme solicitado.",
                color=0x5865F2
            )
            embed.set_footer(text="Sistema de Tickets - Leilões")
            await canal.send(embed=embed)

            await interaction.response.send_message(f"✅ Seu ticket foi criado: {canal.mention}", ephemeral=True)

    class LeilaoView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(LeilaoSelect())

    # Embed explicativa do painel
    embed = discord.Embed(
        title="🎯 Painel de Leilões",
        description="Selecione no menu abaixo qual tipo de leilão deseja solicitar.",
        color=0x5865F2
    )
    embed.add_field(
        name="🎯 Leilão Único", 
        value="Solicite um leilão único, que será realizado apenas uma vez e encerra após o término.", 
        inline=False
    )
    embed.add_field(
        name="🏆 Leilão Permanente", 
        value="Solicite um leilão permanente, que estará sempre disponível para participar.", 
        inline=False
    )

    await interaction.response.send_message(embed=embed, view=LeilaoView())

# =================== COMANDO PARA PAINEL DE MIDDLEMEN ===================
@bot.tree.command(name="painel_middlemen", description="Envia o painel de tickets de Middlemen")
async def painel_middlemen(interaction: discord.Interaction):
    class MiddlemenSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label="Middlemen Cross Trades",
                    description="Solicite um Middlemen para Cross Trades entre usuários",
                    value="cross_trades",
                    emoji="🔁"
                ),
                discord.SelectOption(
                    label="Middlemen PIX",
                    description="Solicite um Middlemen para pagamentos via PIX",
                    value="pix",
                    emoji="💰"
                ),
            ]
            super().__init__(
                placeholder="Selecione o tipo de Middlemen que deseja solicitar...",
                min_values=1,
                max_values=1,
                options=options,
                custom_id="menu_middlemen"
            )

        async def callback(self, interaction: discord.Interaction):
            tipo = self.values[0]
            nomes_tipos = {
                "cross_trades": "Middlemen Cross Trades",
                "pix": "Middlemen PIX"
            }

            # Categoria onde os tickets de middlemen serão criados
            categoria = interaction.guild.get_channel(1472260986231718010)  # Substitua pelo ID da categoria de middlemen
            if not categoria:
                await interaction.response.send_message("❌ Categoria de tickets não encontrada.", ephemeral=True)
                return

            # Evita que o usuário abra múltiplos tickets
            for canal in categoria.text_channels:
                if canal.topic == str(interaction.user.id):
                    await interaction.response.send_message("❌ Você já possui um ticket aberto.", ephemeral=True)
                    return

            # Permissões do canal
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            for cargo_id in CARGOS_QUE_PODEM_VER:
                cargo = interaction.guild.get_role(cargo_id)
                if cargo:
                    overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            # Cria canal do ticket
            canal = await interaction.guild.create_text_channel(
                name=f"{tipo}-{interaction.user.name}".lower(),
                category=categoria,
                overwrites=overwrites,
                topic=str(interaction.user.id)
            )

            # Embed de boas-vindas no ticket
            embed = discord.Embed(
                title=f"🤝 Ticket - {nomes_tipos[tipo]}",
                description=f"{interaction.user.mention} abriu um ticket para **{nomes_tipos[tipo]}**.\n"
                            f"Aguarde nossa equipe liberar o Middlemen conforme solicitado.",
                color=0x5865F2
            )
            embed.set_footer(text="Sistema de Tickets - Middlemen")
            await canal.send(embed=embed)

            await interaction.response.send_message(f"✅ Seu ticket foi criado: {canal.mention}", ephemeral=True)

    class MiddlemenView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(MiddlemenSelect())

    # Embed explicativa do painel
    embed = discord.Embed(
        title="🤝 Painel de Middlemen",
        description="Selecione no menu abaixo qual tipo de Middlemen deseja solicitar.",
        color=0x5865F2
    )
    embed.add_field(
        name="🔁 Middlemen Cross Trades",
        value="Solicite um Middlemen para intermediar trocas entre usuários de forma segura.", 
        inline=False
    )
    embed.add_field(
        name="💰 Middlemen PIX",
        value="Solicite um Middlemen para intermediar pagamentos via PIX de forma segura.", 
        inline=False
    )

    await interaction.response.send_message(embed=embed, view=MiddlemenView())



# =================== RODAR BOT ===================
import os
bot.run(os.getenv("DISCORD_TOKEN"))
