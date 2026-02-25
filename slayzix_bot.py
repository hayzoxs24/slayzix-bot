import discord
from discord.ext import commands
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= CONFIG =================

vouch_channel_id = None
vouch_role_id = None

ticket_config = {
    "category": None,
    "log_channel": None,
    "support_role": None,
    "welcome_message": "Bienvenue ! Un membre du staff va vous répondre rapidement.",
}

open_tickets = {}  # {user_id: channel_id}

# ================= CLOSE TICKET =================

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔒 Fermeture du ticket",
            description=f"Ticket fermé par {interaction.user.mention}",
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed)

        if ticket_config["log_channel"]:
            log_channel = interaction.guild.get_channel(ticket_config["log_channel"])
            if log_channel:
                log_embed = discord.Embed(
                    title="📋 Ticket fermé",
                    description=f"**Salon :** {interaction.channel.name}\n**Fermé par :** {interaction.user.mention}",
                    color=discord.Color.red()
                )
                log_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=log_embed)

        for uid, cid in list(open_tickets.items()):
            if cid == interaction.channel.id:
                del open_tickets[uid]
                break

        await interaction.response.send_message("Fermeture dans 3 secondes...", ephemeral=True)
        import asyncio
        await asyncio.sleep(3)
        await interaction.channel.delete()

# ================= OPEN TICKET =================

async def open_ticket_for(interaction: discord.Interaction, ticket_type: str = "Général"):
    guild = interaction.guild
    user = interaction.user

    if user.id in open_tickets:
        existing = guild.get_channel(open_tickets[user.id])
        if existing:
            return await interaction.response.send_message(
                f"❌ Tu as déjà un ticket ouvert → {existing.mention}", ephemeral=True
            )

    category = None
    if ticket_config["category"]:
        category = guild.get_channel(ticket_config["category"])
    if not category:
        category = discord.utils.get(guild.categories, name="TICKETS")
        if not category:
            category = await guild.create_category("TICKETS")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    if ticket_config["support_role"]:
        role = guild.get_role(ticket_config["support_role"])
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel = await guild.create_text_channel(
        name=f"ticket-{user.name}",
        overwrites=overwrites,
        category=category
    )

    open_tickets[user.id] = channel.id

    embed = discord.Embed(
        title=f"🎫 Ticket — {ticket_type}",
        description=(
            f"👤 **Utilisateur :** {user.mention}\n"
            f"📋 **Type :** {ticket_type}\n\n"
            f"💬 {ticket_config['welcome_message']}"
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Slayzix Shop • Support")
    embed.timestamp = discord.utils.utcnow()

    mention_str = user.mention
    if ticket_config["support_role"]:
        mention_str += f" | <@&{ticket_config['support_role']}>"

    await channel.send(content=mention_str, embed=embed, view=CloseTicketView())

    if ticket_config["log_channel"]:
        log_channel = guild.get_channel(ticket_config["log_channel"])
        if log_channel:
            log_embed = discord.Embed(
                title="📋 Ticket ouvert",
                description=f"**Utilisateur :** {user.mention}\n**Type :** {ticket_type}\n**Salon :** {channel.mention}",
                color=discord.Color.green()
            )
            log_embed.timestamp = discord.utils.utcnow()
            await log_channel.send(embed=log_embed)

    await interaction.response.send_message(
        f"✅ Ton ticket a été créé → {channel.mention}", ephemeral=True
    )

# ================= TICKET PANEL BUTTONS =================

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Général", style=discord.ButtonStyle.primary, custom_id="ticket_general")
    async def general(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket_for(interaction, "Général")

    @discord.ui.button(label="❓ Support", style=discord.ButtonStyle.secondary, custom_id="ticket_support")
    async def support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket_for(interaction, "Support")

    @discord.ui.button(label="💰 Commande", style=discord.ButtonStyle.success, custom_id="ticket_commande")
    async def commande(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket_for(interaction, "Commande")

    @discord.ui.button(label="⚠️ Signalement", style=discord.ButtonStyle.danger, custom_id="ticket_signalement")
    async def signalement(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket_for(interaction, "Signalement")

# ================= CONFIG SELECTS =================

class TicketCategorySelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="📁 Catégorie des tickets", channel_types=[discord.ChannelType.category])

    async def callback(self, interaction: discord.Interaction):
        ticket_config["category"] = self.values[0].id
        await interaction.response.send_message(f"✅ Catégorie : **{self.values[0].name}**", ephemeral=True)

class TicketLogSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="📋 Salon des logs", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        ticket_config["log_channel"] = self.values[0].id
        await interaction.response.send_message(f"✅ Logs : {self.values[0].mention}", ephemeral=True)

class TicketRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="👮 Rôle support")

    async def callback(self, interaction: discord.Interaction):
        ticket_config["support_role"] = self.values[0].id
        await interaction.response.send_message(f"✅ Rôle support : {self.values[0].mention}", ephemeral=True)

class SendPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📨 Envoyer le panel ici", style=discord.ButtonStyle.success)
    async def send_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎫 SLAYZIX SHOP — Ouvre un ticket",
            description=(
                "Tu as besoin d'aide ou tu veux passer une commande ?\n"
                "Clique sur le bouton correspondant à ta demande !\n\n"
                "🎫 **Général** — Question générale\n"
                "❓ **Support** — Problème / aide\n"
                "💰 **Commande** — Passer une commande\n"
                "⚠️ **Signalement** — Signaler un problème\n\n"
                "⚡ Réponse rapide garantie !"
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Slayzix Shop • Un seul ticket à la fois par utilisateur")
        await interaction.channel.send(embed=embed, view=TicketPanel())
        await interaction.response.send_message("✅ Panel envoyé !", ephemeral=True)

class TicketConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())
        self.add_item(TicketLogSelect())
        self.add_item(TicketRoleSelect())

# ================= /createticket =================

@bot.tree.command(name="createticket", description="Configure et envoie le panel de tickets")
@discord.app_commands.checks.has_permissions(administrator=True)
async def createticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Panel Tickets — Configuration",
        description=(
            "Configure ton système de tickets ci-dessous :\n\n"
            "**1️⃣** Sélectionne la **catégorie** où seront créés les tickets\n"
            "**2️⃣** Sélectionne le **salon des logs**\n"
            "**3️⃣** Sélectionne le **rôle support** qui accède aux tickets\n\n"
            "Puis envoie le panel dans le salon de ton choix 👇"
        ),
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=TicketConfigView(), ephemeral=True)
    await interaction.followup.send("📨 Envoyer le panel :", view=SendPanelView(), ephemeral=True)

# ================= VOUCH =================

class VouchChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon des avis", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        global vouch_channel_id
        vouch_channel_id = self.values[0].id
        await interaction.response.send_message(f"✅ Salon des avis : {self.values[0].mention} !", ephemeral=True)

class VouchSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VouchChannelSelect())

@bot.command()
@commands.has_permissions(administrator=True)
async def setvouchchannel(ctx):
    embed = discord.Embed(title="⚙️ Configuration — Salon des avis", color=discord.Color.blurple())
    await ctx.send(embed=embed, view=VouchSetupView())

class VouchRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le rôle à attribuer après un vouch")

    async def callback(self, interaction: discord.Interaction):
        global vouch_role_id
        vouch_role_id = self.values[0].id
        await interaction.response.send_message(f"✅ Rôle vouch : {self.values[0].mention} !", ephemeral=True)

class VouchRoleSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VouchRoleSelect())

@bot.command()
@commands.has_permissions(administrator=True)
async def setvouchrole(ctx):
    embed = discord.Embed(title="⚙️ Configuration — Rôle Vouch", color=discord.Color.blurple())
    await ctx.send(embed=embed, view=VouchRoleSetupView())

@bot.tree.command(name="vouch", description="Laisse un avis sur le shop !")
@discord.app_commands.describe(note="Ta note sur 5", service="Le service acheté", commentaire="Ton commentaire")
@discord.app_commands.choices(note=[
    discord.app_commands.Choice(name="⭐ 1/5", value=1),
    discord.app_commands.Choice(name="⭐⭐ 2/5", value=2),
    discord.app_commands.Choice(name="⭐⭐⭐ 3/5", value=3),
    discord.app_commands.Choice(name="⭐⭐⭐⭐ 4/5", value=4),
    discord.app_commands.Choice(name="⭐⭐⭐⭐⭐ 5/5", value=5),
])
async def vouch(interaction: discord.Interaction, note: int, service: str, commentaire: str):
    stars = "⭐" * note + "🌑" * (5 - note)
    colors = {1: discord.Color.red(), 2: discord.Color.orange(), 3: discord.Color.yellow(), 4: discord.Color.green(), 5: discord.Color.gold()}
    badges = {1: "😡 Très mauvais", 2: "😕 Mauvais", 3: "😐 Correct", 4: "😊 Bien", 5: "🤩 Excellent !"}

    embed = discord.Embed(title="📝 Nouvel Avis — Slayzix Shop", color=colors[note])
    embed.add_field(name="👤 Client", value=interaction.user.mention, inline=True)
    embed.add_field(name="📦 Service", value=f"**{service}**", inline=True)
    embed.add_field(name="⭐ Note", value=f"{stars}  `{note}/5` — {badges[note]}", inline=False)
    embed.add_field(name="💬 Commentaire", value=f"*{commentaire}*", inline=False)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Slayzix Shop • Merci pour ton avis !")
    embed.timestamp = discord.utils.utcnow()

    role_added = False
    role = None
    if vouch_role_id:
        role = interaction.guild.get_role(vouch_role_id)
        if role and role not in interaction.user.roles:
            try:
                await interaction.user.add_roles(role, reason="Vouch effectué")
                role_added = True
            except discord.Forbidden:
                pass

    if vouch_channel_id:
        channel = interaction.guild.get_channel(vouch_channel_id)
        if channel:
            await channel.send(embed=embed)
            msg = f"✅ Ton avis a été posté dans {channel.mention}, merci ! 🙏"
            if role_added:
                msg += f"\n🎖️ Le rôle **{role.name}** t'a été attribué !"
            return await interaction.response.send_message(msg, ephemeral=True)

    await interaction.response.send_message(embed=embed)
    if role_added:
        await interaction.followup.send(f"🎖️ Le rôle **{role.name}** t'a été attribué !", ephemeral=True)

# ================= ON MESSAGE =================

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if vouch_channel_id and vouch_role_id and message.channel.id == vouch_channel_id:
        role = message.guild.get_role(vouch_role_id)
        if role and role not in message.author.roles:
            try:
                await message.author.add_roles(role, reason="Message dans le salon vouch")
            except discord.Forbidden:
                pass
    await bot.process_commands(message)

# ================= ON READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} connecté et slash commands synchronisées !")

# ================= START =================

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    bot.run(TOKEN)
