import discord
from discord.ext import commands
import os
import asyncio
import random
from datetime import datetime, timedelta
import aiohttp
import re

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= CONFIG =================

vouch_channel_id = None
vouch_role_id = None
welcome_channel_id = None
goodbye_channel_id = None
autoping_channel_id = None
autodiscret_channel_id = None

ticket_config = {
    "category": None,
    "log_channel": None,
    "support_role": None,
    "welcome_message": "Bienvenue ! Un membre du staff va vous répondre rapidement.",
}

open_tickets = {}
active_giveaways = {}
embed_sessions = {}

# ================= WELCOME / GOODBYE =================

@bot.event
async def on_member_join(member):
    if autoping_channel_id:
        ch = member.guild.get_channel(autoping_channel_id)
        if ch:
            await ch.send(
                f"👋 Bienvenue {member.mention} sur **{member.guild.name}** !",
                allowed_mentions=discord.AllowedMentions(users=True)
            )

    if autodiscret_channel_id:
        ch = member.guild.get_channel(autodiscret_channel_id)
        if ch:
            msg = await ch.send(
                f"👋 Bienvenue {member.mention} sur **{member.guild.name}** !",
                allowed_mentions=discord.AllowedMentions(users=True)
            )
            await asyncio.sleep(1)
            await msg.delete()

    if welcome_channel_id:
        ch = member.guild.get_channel(welcome_channel_id)
        if ch:
            embed = discord.Embed(
                title="🎉 Bienvenue sur le serveur !",
                description=(
                    f"Salut {member.mention}, on est ravis de t'accueillir sur **{member.guild.name}** ! 🙌\n\n"
                    f"Tu es le **{member.guild.member_count}ème** membre à nous rejoindre.\n\n"
                    "──────────────────────\n"
                    "🛒 Consulte nos services et passe ta commande !\n"
                    "💬 Notre équipe est là pour t'aider."
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Slayzix Shop • Bienvenue parmi nous ! • {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}")
            await ch.send(content=member.mention, embed=embed, allowed_mentions=discord.AllowedMentions(users=True))


@bot.event
async def on_member_remove(member):
    if not goodbye_channel_id:
        return
    ch = member.guild.get_channel(goodbye_channel_id)
    if not ch:
        return
    embed = discord.Embed(
        title="👋 Départ du serveur",
        description=(
            f"**{member.name}** vient de quitter **{member.guild.name}**...\n\n"
            f"Il reste désormais **{member.guild.member_count} membres** sur le serveur.\n\n"
            "──────────────────────\n"
            "😊 On espère te revoir bientôt !"
        ),
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"Slayzix Shop • À bientôt ! • {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}")
    await ch.send(embed=embed)


# ================= !welcome / !goodbye =================

class WelcomeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon de bienvenue", channel_types=[discord.ChannelType.text])
    async def callback(self, interaction: discord.Interaction):
        global welcome_channel_id
        welcome_channel_id = self.values[0].id
        await interaction.response.send_message(f"✅ Salon de bienvenue : {self.values[0].mention}", ephemeral=True)

class WelcomeSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(WelcomeChannelSelect())

@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    await ctx.send(embed=discord.Embed(title="⚙️ Salon de bienvenue", color=discord.Color.green()), view=WelcomeSetupView())


class GoodbyeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon d'au revoir", channel_types=[discord.ChannelType.text])
    async def callback(self, interaction: discord.Interaction):
        global goodbye_channel_id
        goodbye_channel_id = self.values[0].id
        await interaction.response.send_message(f"✅ Salon d'au revoir : {self.values[0].mention}", ephemeral=True)

class GoodbyeSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GoodbyeChannelSelect())

@bot.command()
@commands.has_permissions(administrator=True)
async def goodbye(ctx):
    await ctx.send(embed=discord.Embed(title="⚙️ Salon d'au revoir", color=discord.Color.red()), view=GoodbyeSetupView())


# ================= TICKETS =================

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(embed=discord.Embed(
            title="🔒 Fermeture du ticket",
            description=f"Ticket fermé par {interaction.user.mention}",
            color=discord.Color.red()
        ))
        if ticket_config["log_channel"]:
            lc = interaction.guild.get_channel(ticket_config["log_channel"])
            if lc:
                e = discord.Embed(title="📋 Ticket fermé", description=f"**Salon :** {interaction.channel.name}\n**Par :** {interaction.user.mention}", color=discord.Color.red())
                e.timestamp = discord.utils.utcnow()
                await lc.send(embed=e)
        for uid, cid in list(open_tickets.items()):
            if cid == interaction.channel.id:
                del open_tickets[uid]
                break
        await interaction.response.send_message("Fermeture dans 3 secondes...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()


async def open_ticket_for(interaction: discord.Interaction, ticket_type: str = "Général"):
    guild = interaction.guild
    user = interaction.user
    if user.id in open_tickets:
        existing = guild.get_channel(open_tickets[user.id])
        if existing:
            return await interaction.response.send_message(f"❌ Ticket déjà ouvert → {existing.mention}", ephemeral=True)

    category = guild.get_channel(ticket_config["category"]) if ticket_config["category"] else None
    if not category:
        category = discord.utils.get(guild.categories, name="TICKETS") or await guild.create_category("TICKETS")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    if ticket_config["support_role"]:
        role = guild.get_role(ticket_config["support_role"])
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel = await guild.create_text_channel(name=f"ticket-{user.name}", overwrites=overwrites, category=category)
    open_tickets[user.id] = channel.id

    embed = discord.Embed(
        title=f"🎫 Ticket — {ticket_type}",
        description=f"👤 **Utilisateur :** {user.mention}\n📋 **Type :** {ticket_type}\n\n💬 {ticket_config['welcome_message']}",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Slayzix Shop • Support")
    embed.timestamp = discord.utils.utcnow()

    mention_str = user.mention
    if ticket_config["support_role"]:
        mention_str += f" | <@&{ticket_config['support_role']}>"
    await channel.send(content=mention_str, embed=embed, view=CloseTicketView())

    if ticket_config["log_channel"]:
        lc = guild.get_channel(ticket_config["log_channel"])
        if lc:
            e = discord.Embed(title="📋 Ticket ouvert", description=f"**Utilisateur :** {user.mention}\n**Type :** {ticket_type}\n**Salon :** {channel.mention}", color=discord.Color.green())
            e.timestamp = discord.utils.utcnow()
            await lc.send(embed=e)

    await interaction.response.send_message(f"✅ Ticket créé → {channel.mention}", ephemeral=True)


TICKET_OPTIONS = [
    discord.SelectOption(label="Général",     emoji="🎫", description="Question générale",       value="Général"),
    discord.SelectOption(label="Support",     emoji="❓", description="Problème / aide",          value="Support"),
    discord.SelectOption(label="Commande",    emoji="💰", description="Passer une commande",      value="Commande"),
    discord.SelectOption(label="Signalement", emoji="⚠️", description="Signaler un problème",     value="Signalement"),
    discord.SelectOption(label="Partenariat", emoji="🤝", description="Proposer un partenariat",  value="Partenariat"),
    discord.SelectOption(label="Giveaway",    emoji="🎉", description="Organiser un giveaway",    value="Giveaway"),
    discord.SelectOption(label="Récompense",  emoji="🏆", description="Réclamer une récompense",  value="Récompense"),
]

class TicketSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="📂 Choisis le type de ticket...", min_values=1, max_values=1, options=TICKET_OPTIONS, custom_id="ticket_select")
    async def callback(self, interaction: discord.Interaction):
        await open_ticket_for(interaction, self.values[0])

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

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

class TicketConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())
        self.add_item(TicketLogSelect())
        self.add_item(TicketRoleSelect())

class SendPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="📨 Envoyer le panel ici", style=discord.ButtonStyle.success)
    async def send_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎫 SLAYZIX SHOP — Ouvre un ticket",
            description=(
                "Sélectionne le type de ta demande dans le menu ci-dessous !\n\n"
                "🎫 **Général** — Question générale\n"
                "❓ **Support** — Problème / aide\n"
                "💰 **Commande** — Passer une commande\n"
                "⚠️ **Signalement** — Signaler un problème\n"
                "🤝 **Partenariat** — Proposer un partenariat\n"
                "🎉 **Giveaway** — Organiser un giveaway\n"
                "🏆 **Récompense** — Réclamer une récompense\n\n"
                "⚡ Réponse rapide garantie !"
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Slayzix Shop • Un seul ticket à la fois par utilisateur")
        await interaction.channel.send(embed=embed, view=TicketPanel())
        await interaction.response.send_message("✅ Panel envoyé !", ephemeral=True)

@bot.tree.command(name="createticket", description="Configure et envoie le panel de tickets")
@discord.app_commands.checks.has_permissions(administrator=True)
async def createticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Panel Tickets — Configuration",
        description="**1️⃣** Catégorie\n**2️⃣** Salon des logs\n**3️⃣** Rôle support\n\nPuis envoie le panel 👇",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=TicketConfigView(), ephemeral=True)
    await interaction.followup.send("📨 Envoyer le panel :", view=SendPanelView(), ephemeral=True)


# ================= MODÉRATION =================

@bot.tree.command(name="clear", description="Supprime des messages dans ce salon")
@discord.app_commands.describe(nombre="Nombre de messages à supprimer (1-100)")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, nombre: int = 10):
    if not 1 <= nombre <= 100:
        return await interaction.response.send_message("❌ Entre 1 et 100.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(f"🗑️ **{len(deleted)}** message(s) supprimé(s).", ephemeral=True)


@bot.tree.command(name="ban", description="Bannir un membre du serveur")
@discord.app_commands.describe(membre="Le membre à bannir", raison="Raison du ban")
@discord.app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison fournie"):
    if membre.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("❌ Tu ne peux pas bannir ce membre.", ephemeral=True)
    try:
        await membre.send(embed=discord.Embed(title="🔨 Tu as été banni", description=f"**Serveur :** {interaction.guild.name}\n**Raison :** {raison}", color=discord.Color.red()))
    except Exception:
        pass
    await membre.ban(reason=raison)
    embed = discord.Embed(title="🔨 Membre banni", description=f"**Membre :** {membre.mention}\n**Raison :** {raison}\n**Par :** {interaction.user.mention}", color=discord.Color.red())
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="unban", description="Débannir un utilisateur par son ID")
@discord.app_commands.describe(user_id="L'ID de l'utilisateur à débannir")
@discord.app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        embed = discord.Embed(title="✅ Membre débanni", description=f"**Utilisateur :** {user.mention}\n**Par :** {interaction.user.mention}", color=discord.Color.green())
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)
    except discord.NotFound:
        await interaction.response.send_message("❌ Utilisateur introuvable ou pas banni.", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ ID invalide.", ephemeral=True)


@bot.tree.command(name="unbanall", description="Débannir TOUS les membres du serveur")
@discord.app_commands.checks.has_permissions(administrator=True)
async def unbanall(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    bans = [entry async for entry in interaction.guild.bans()]
    count = 0
    for entry in bans:
        try:
            await interaction.guild.unban(entry.user)
            count += 1
        except Exception:
            pass
    await interaction.followup.send(embed=discord.Embed(title="✅ Déban général", description=f"**{count}** membre(s) débanni(s).", color=discord.Color.green()), ephemeral=True)


# ================= /hide =================

@bot.tree.command(name="hide", description="Cache ce salon à @everyone (toggle)")
@discord.app_commands.describe(salon="Salon à cacher (optionnel, défaut : salon actuel)")
@discord.app_commands.checks.has_permissions(manage_channels=True)
async def hide(interaction: discord.Interaction, salon: discord.TextChannel = None):
    target = salon or interaction.channel
    everyone = interaction.guild.default_role
    overwrite = target.overwrites_for(everyone)

    if overwrite.view_channel is False:
        overwrite.view_channel = None
        await target.set_permissions(everyone, overwrite=overwrite)
        await interaction.response.send_message(f"👁️ {target.mention} est maintenant **visible** par @everyone.", ephemeral=True)
    else:
        overwrite.view_channel = False
        await target.set_permissions(everyone, overwrite=overwrite)
        await interaction.response.send_message(f"🔒 {target.mention} est maintenant **caché** à @everyone.", ephemeral=True)


# ================= /autoping =================

class AutopingChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon d'autoping", channel_types=[discord.ChannelType.text])
    async def callback(self, interaction: discord.Interaction):
        global autoping_channel_id
        autoping_channel_id = self.values[0].id
        await interaction.response.send_message(f"✅ Autoping activé dans {self.values[0].mention}", ephemeral=True)

class AutopingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AutopingChannelSelect())

@bot.tree.command(name="autoping", description="Ping automatiquement les nouveaux membres dans un salon")
@discord.app_commands.checks.has_permissions(administrator=True)
async def autoping(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=discord.Embed(title="⚙️ Autoping", description="Sélectionne le salon.", color=discord.Color.blurple()),
        view=AutopingView(), ephemeral=True
    )

@bot.tree.command(name="autopingdelete", description="Désactive l'autoping")
@discord.app_commands.checks.has_permissions(administrator=True)
async def autopingdelete(interaction: discord.Interaction):
    global autoping_channel_id
    if autoping_channel_id is None:
        return await interaction.response.send_message("❌ Aucun autoping configuré.", ephemeral=True)
    autoping_channel_id = None
    await interaction.response.send_message("✅ Autoping désactivé.", ephemeral=True)


# ================= /autodiscret =================

class AutodiscretChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon autodiscret", channel_types=[discord.ChannelType.text])
    async def callback(self, interaction: discord.Interaction):
        global autodiscret_channel_id
        autodiscret_channel_id = self.values[0].id
        await interaction.response.send_message(f"✅ Autodiscret activé dans {self.values[0].mention}", ephemeral=True)

class AutodiscretView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AutodiscretChannelSelect())

@bot.tree.command(name="autodiscret", description="Ping discret : ping puis supprime après 1s")
@discord.app_commands.checks.has_permissions(administrator=True)
async def autodiscret(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=discord.Embed(title="⚙️ Autodiscret", description="Sélectionne le salon.", color=discord.Color.blurple()),
        view=AutodiscretView(), ephemeral=True
    )


# ================= /say =================

@bot.tree.command(name="say", description="Faire parler le bot")
@discord.app_commands.describe(message="Le message à envoyer", salon="Salon cible (optionnel)")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def say(interaction: discord.Interaction, message: str, salon: discord.TextChannel = None):
    target = salon or interaction.channel
    await target.send(message)
    await interaction.response.send_message(f"✅ Message envoyé dans {target.mention}.", ephemeral=True)


# ================= /embed — MENU INTERACTIF COMPLET =================

COULEURS_PRESET = {
    "🔵 Blurple":       "5865f2",
    "🟢 Vert":          "57f287",
    "🔴 Rouge":         "ed4245",
    "🟡 Jaune":         "fee75c",
    "🟠 Orange":        "e67e22",
    "🩷 Rose":          "ff73fa",
    "⚫ Noir":          "23272a",
    "⚪ Blanc":         "ffffff",
    "🩵 Cyan":          "1abc9c",
    "🟣 Violet":        "9b59b6",
    "🎲 Aléatoire":     "random",
    "✏️ Personnalisée": "custom",
}


def new_session():
    return {
        "titre": "",
        "description": "",
        "couleur": "5865f2",
        "footer": "",
        "image": "",
        "thumbnail": "",
        "auteur_nom": "",
        "auteur_icon": "",
        "fields": [],
        "target_channel": None,
    }


def build_embed(session: dict, username: str) -> discord.Embed:
    hex_val = session.get("couleur", "5865f2")
    if hex_val == "random":
        color = discord.Color(random.randint(0, 0xFFFFFF))
    else:
        try:
            color = discord.Color(int(hex_val, 16))
        except Exception:
            color = discord.Color.blurple()

    embed = discord.Embed(
        title=session.get("titre") or None,
        description=session.get("description") or None,
        color=color
    )
    embed.timestamp = discord.utils.utcnow()

    auteur_nom = session.get("auteur_nom", "")
    auteur_icon = session.get("auteur_icon", "")
    if auteur_nom:
        if auteur_icon.startswith("http"):
            embed.set_author(name=auteur_nom, icon_url=auteur_icon)
        else:
            embed.set_author(name=auteur_nom)

    thumb = session.get("thumbnail", "")
    if thumb.startswith("http"):
        embed.set_thumbnail(url=thumb)

    img = session.get("image", "")
    if img.startswith("http"):
        embed.set_image(url=img)

    for field in session.get("fields", []):
        embed.add_field(name=field["name"], value=field["value"], inline=field.get("inline", False))

    footer = session.get("footer", "")
    embed.set_footer(text=footer if footer else f"Slayzix Shop • Par {username}")

    return embed


class EmbedColorSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=nom, value=val) for nom, val in COULEURS_PRESET.items()]
        super().__init__(placeholder="🎨 Couleur...", options=options, custom_id="embed_color_select", row=0)

    async def callback(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if self.values[0] == "custom":
            await interaction.response.send_modal(EmbedCustomColorModal(uid))
        elif self.values[0] == "random":
            embed_sessions[uid]["couleur"] = "random"
            await interaction.response.send_message("✅ Couleur aléatoire sélectionnée !", ephemeral=True)
        else:
            embed_sessions[uid]["couleur"] = self.values[0]
            await interaction.response.send_message("✅ Couleur enregistrée !", ephemeral=True)


class EmbedChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, uid):
        super().__init__(placeholder="📢 Salon d'envoi...", channel_types=[discord.ChannelType.text], row=1)
        self.uid = uid

    async def callback(self, interaction: discord.Interaction):
        embed_sessions[self.uid]["target_channel"] = self.values[0].id
        await interaction.response.send_message(f"✅ Salon cible : {self.values[0].mention}", ephemeral=True)


class EmbedCustomColorModal(discord.ui.Modal, title="🎨 Couleur personnalisée"):
    couleur = discord.ui.TextInput(label="Code hex (sans #)", placeholder="ex: ff0000", min_length=6, max_length=6)

    def __init__(self, uid):
        super().__init__()
        self.uid = uid

    async def on_submit(self, interaction: discord.Interaction):
        try:
            int(self.couleur.value, 16)
            embed_sessions[self.uid]["couleur"] = self.couleur.value
            await interaction.response.send_message(f"✅ Couleur `#{self.couleur.value}` enregistrée !", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Code hex invalide.", ephemeral=True)


class EmbedContenuModal(discord.ui.Modal, title="✏️ Contenu principal"):
    titre = discord.ui.TextInput(label="Titre", placeholder="Titre de l'embed", max_length=256, required=False)
    description = discord.ui.TextInput(
        label="Description  (\\n = saut de ligne)",
        placeholder="Ta description ici...",
        style=discord.TextStyle.long,
        max_length=4000,
        required=False
    )
    footer = discord.ui.TextInput(label="Footer (optionnel)", placeholder="Texte en bas de l'embed", required=False, max_length=2048)

    def __init__(self, uid):
        super().__init__()
        self.uid = uid

    async def on_submit(self, interaction: discord.Interaction):
        s = embed_sessions.get(self.uid, new_session())
        s["titre"] = self.titre.value or ""
        s["description"] = self.description.value.replace("\\n", "\n") if self.description.value else ""
        s["footer"] = self.footer.value or ""
        embed_sessions[self.uid] = s
        await interaction.response.send_message("✅ Contenu enregistré !", ephemeral=True)


class EmbedMediaModal(discord.ui.Modal, title="🖼️ Images & Auteur"):
    image = discord.ui.TextInput(label="URL Image principale", placeholder="https://...", required=False)
    thumbnail = discord.ui.TextInput(label="URL Thumbnail (petite image droite)", placeholder="https://...", required=False)
    auteur_nom = discord.ui.TextInput(label="Nom de l'auteur (optionnel)", placeholder="ex: Slayzix Shop", required=False, max_length=256)
    auteur_icon = discord.ui.TextInput(label="URL icône auteur (optionnel)", placeholder="https://...", required=False)

    def __init__(self, uid):
        super().__init__()
        self.uid = uid

    async def on_submit(self, interaction: discord.Interaction):
        s = embed_sessions.get(self.uid, new_session())
        s["image"] = self.image.value or ""
        s["thumbnail"] = self.thumbnail.value or ""
        s["auteur_nom"] = self.auteur_nom.value or ""
        s["auteur_icon"] = self.auteur_icon.value or ""
        embed_sessions[self.uid] = s
        await interaction.response.send_message("✅ Médias & auteur enregistrés !", ephemeral=True)


class EmbedFieldModal(discord.ui.Modal, title="➕ Ajouter un champ (field)"):
    field_name = discord.ui.TextInput(label="Nom du champ", placeholder="ex: Prix", max_length=256)
    field_value = discord.ui.TextInput(label="Valeur du champ", placeholder="ex: 10€", style=discord.TextStyle.long, max_length=1024)
    inline = discord.ui.TextInput(label="Inline ? (oui / non)", placeholder="oui", max_length=3, required=False)

    def __init__(self, uid):
        super().__init__()
        self.uid = uid

    async def on_submit(self, interaction: discord.Interaction):
        s = embed_sessions.get(self.uid, new_session())
        if len(s["fields"]) >= 25:
            return await interaction.response.send_message("❌ Maximum 25 champs.", ephemeral=True)
        inline_val = self.inline.value.strip().lower() in ("oui", "o", "yes", "y", "true")
        s["fields"].append({"name": self.field_name.value, "value": self.field_value.value, "inline": inline_val})
        embed_sessions[self.uid] = s
        await interaction.response.send_message(f"✅ Champ **{self.field_name.value}** ajouté ! ({len(s['fields'])}/25)", ephemeral=True)


class EmbedBuilderView(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=300)
        self.uid = uid
        self.add_item(EmbedColorSelect())
        self.add_item(EmbedChannelSelect(uid))

    @discord.ui.button(label="✏️ Contenu", style=discord.ButtonStyle.primary, row=2)
    async def write_content(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmbedContenuModal(self.uid))

    @discord.ui.button(label="🖼️ Images & Auteur", style=discord.ButtonStyle.secondary, row=2)
    async def write_media(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmbedMediaModal(self.uid))

    @discord.ui.button(label="➕ Ajouter un champ", style=discord.ButtonStyle.secondary, row=2)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmbedFieldModal(self.uid))

    @discord.ui.button(label="🗑️ Vider les champs", style=discord.ButtonStyle.danger, row=3)
    async def clear_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_sessions[self.uid]["fields"] = []
        await interaction.response.send_message("✅ Champs supprimés.", ephemeral=True)

    @discord.ui.button(label="👁️ Prévisualiser", style=discord.ButtonStyle.secondary, row=3)
    async def preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = embed_sessions.get(self.uid, new_session())
        e = build_embed(session, interaction.user.name)
        await interaction.response.send_message("**Aperçu :**", embed=e, ephemeral=True)

    @discord.ui.button(label="🚀 Envoyer", style=discord.ButtonStyle.success, row=3)
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        session = embed_sessions.get(self.uid, new_session())
        if not session.get("titre") and not session.get("description") and not session.get("fields"):
            return await interaction.response.send_message("❌ Ajoute au moins un titre, une description ou un champ.", ephemeral=True)
        target_id = session.get("target_channel")
        target = interaction.guild.get_channel(target_id) if target_id else interaction.channel
        e = build_embed(session, interaction.user.name)
        await target.send(embed=e)
        embed_sessions.pop(self.uid, None)
        await interaction.response.send_message(f"✅ Embed envoyé dans {target.mention} !", ephemeral=True)

    @discord.ui.button(label="❌ Annuler", style=discord.ButtonStyle.danger, row=3)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed_sessions.pop(self.uid, None)
        await interaction.response.send_message("❌ Création annulée.", ephemeral=True)


@bot.tree.command(name="embed", description="Créer un embed personnalisé avec un menu interactif")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def embed_cmd(interaction: discord.Interaction):
    uid = interaction.user.id
    embed_sessions[uid] = new_session()

    info = discord.Embed(
        title="🛠️ Créateur d'embed",
        description=(
            "**1.** 🎨 Choisis une couleur\n"
            "**2.** 📢 Choisis le salon d'envoi\n"
            "**3.** ✏️ **Contenu** — Titre, description (`\\n` = saut de ligne), footer\n"
            "**4.** 🖼️ **Images & Auteur** — Image principale, thumbnail, auteur\n"
            "**5.** ➕ **Ajouter un champ** — Jusqu'à 25 fields\n"
            "**6.** 👁️ Prévisualise puis 🚀 Envoie !"
        ),
        color=discord.Color.blurple()
    )
    info.set_footer(text="Menu valable 5 minutes")
    await interaction.response.send_message(embed=info, view=EmbedBuilderView(uid), ephemeral=True)


# ================= GIVEAWAY =================

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Participer", style=discord.ButtonStyle.success, custom_id="giveaway_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.giveaway_id not in active_giveaways:
            return await interaction.response.send_message("❌ Ce giveaway est terminé.", ephemeral=True)
        giveaway = active_giveaways[self.giveaway_id]
        if interaction.user.id in giveaway["participants"]:
            giveaway["participants"].discard(interaction.user.id)
            button.label = f"🎉 Participer — {len(giveaway['participants'])}"
            await interaction.message.edit(view=self)
            return await interaction.response.send_message("❌ Tu t'es retiré du giveaway.", ephemeral=True)
        giveaway["participants"].add(interaction.user.id)
        button.label = f"🎉 Participer — {len(giveaway['participants'])}"
        await interaction.message.edit(view=self)
        await interaction.response.send_message("✅ Tu participes ! Bonne chance 🍀", ephemeral=True)


async def end_giveaway(channel_id: int, message_id: int, guild: discord.Guild):
    await asyncio.sleep(0.1)
    if message_id not in active_giveaways:
        return
    giveaway = active_giveaways[message_id]
    channel = guild.get_channel(channel_id)
    if not channel:
        return
    try:
        message = await channel.fetch_message(message_id)
    except Exception:
        return

    participants = list(giveaway["participants"])
    prize = giveaway["prize"]
    host = giveaway["host"]

    if not participants:
        embed = discord.Embed(title="🎉 GIVEAWAY TERMINÉ", description=f"**Prix :** {prize}\n**Organisateur :** <@{host}>\n\n😔 Aucun participant !", color=discord.Color.red())
        embed.set_footer(text="Slayzix Shop • Giveaway terminé")
        embed.timestamp = discord.utils.utcnow()
        await message.edit(embed=embed, view=None)
        await channel.send("😔 Aucun participant, pas de gagnant !")
        del active_giveaways[message_id]
        return

    winners = random.sample(participants, min(giveaway["winners"], len(participants)))
    winners_mentions = " ".join([f"<@{w}>" for w in winners])
    embed = discord.Embed(
        title="🎉 GIVEAWAY TERMINÉ",
        description=f"**Prix :** {prize}\n**Gagnant(s) :** {winners_mentions}\n**Organisateur :** <@{host}>\n**Participants :** {len(participants)}",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Slayzix Shop • Giveaway terminé")
    embed.timestamp = discord.utils.utcnow()
    await message.edit(embed=embed, view=None)
    await channel.send(f"🎊 Félicitations {winners_mentions} ! Tu as gagné **{prize}** !\nContacte <@{host}> pour récupérer ton prix.")
    del active_giveaways[message_id]


@bot.tree.command(name="giveaway", description="Lance un giveaway !")
@discord.app_commands.describe(duree="Durée (ex: 10s, 5m, 1h, 2d)", gagnants="Nombre de gagnants", prix="Ce que tu fais gagner")
@discord.app_commands.checks.has_permissions(manage_guild=True)
async def giveaway(interaction: discord.Interaction, duree: str, gagnants: int, prix: str):
    try:
        unit = duree[-1].lower()
        value = int(duree[:-1])
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        if unit not in multipliers:
            raise ValueError
        seconds = value * multipliers[unit]
    except Exception:
        return await interaction.response.send_message("❌ Format invalide. Ex : `30s`, `5m`, `1h`, `2d`", ephemeral=True)

    if gagnants < 1:
        return await interaction.response.send_message("❌ Minimum 1 gagnant.", ephemeral=True)

    end_timestamp = int((datetime.utcnow() + timedelta(seconds=seconds)).timestamp())
    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=f"**Prix :** {prix}\n**Gagnant(s) :** {gagnants}\n**Organisateur :** {interaction.user.mention}\n**Fin :** <t:{end_timestamp}:R> (<t:{end_timestamp}:f>)\n\nClique sur 🎉 pour participer !",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Slayzix Shop • Giveaway")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message("✅ Giveaway lancé !", ephemeral=True)
    msg = await interaction.channel.send(embed=embed)
    active_giveaways[msg.id] = {"prize": prix, "winners": gagnants, "host": interaction.user.id, "participants": set(), "channel_id": interaction.channel.id}
    await msg.edit(view=GiveawayView(msg.id))
    await asyncio.sleep(seconds)
    await end_giveaway(interaction.channel.id, msg.id, interaction.guild)


@bot.tree.command(name="reroll", description="Nouveau tirage pour un giveaway terminé")
@discord.app_commands.describe(message_id="L'ID du message du giveaway")
@discord.app_commands.checks.has_permissions(manage_guild=True)
async def reroll(interaction: discord.Interaction, message_id: str):
    try:
        await interaction.channel.fetch_message(int(message_id))
    except Exception:
        return await interaction.response.send_message("❌ Message introuvable.", ephemeral=True)
    await interaction.response.send_message("🎲 Les participants ne sont plus dispo après la fin. Utilise `/giveaway` pour relancer !", ephemeral=True)


@bot.tree.command(name="giveawayend", description="Terminer un giveaway manuellement")
@discord.app_commands.describe(message_id="L'ID du message du giveaway")
@discord.app_commands.checks.has_permissions(manage_guild=True)
async def giveawayend(interaction: discord.Interaction, message_id: str):
    msg_id = int(message_id)
    if msg_id not in active_giveaways:
        return await interaction.response.send_message("❌ Giveaway introuvable ou déjà terminé.", ephemeral=True)
    await interaction.response.send_message("✅ Giveaway terminé manuellement !", ephemeral=True)
    await end_giveaway(interaction.channel.id, msg_id, interaction.guild)


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
    await ctx.send(embed=discord.Embed(title="⚙️ Salon des avis", color=discord.Color.blurple()), view=VouchSetupView())


class VouchRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le rôle attribué après un vouch")
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
    await ctx.send(embed=discord.Embed(title="⚙️ Rôle Vouch", color=discord.Color.blurple()), view=VouchRoleSetupView())


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
        ch = interaction.guild.get_channel(vouch_channel_id)
        if ch:
            await ch.send(embed=embed)
            msg = f"✅ Avis posté dans {ch.mention}, merci ! 🙏"
            if role_added:
                msg += f"\n🎖️ Rôle **{role.name}** attribué !"
            return await interaction.response.send_message(msg, ephemeral=True)

    await interaction.response.send_message(embed=embed)
    if role_added:
        await interaction.followup.send(f"🎖️ Rôle **{role.name}** attribué !", ephemeral=True)


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


# ================= /osint =================

# Liste des plateformes à vérifier (pseudo)
OSINT_PLATFORMS = [
    {"name": "TikTok",      "url": "https://www.tiktok.com/@{}", "emoji": "🎵"},
    {"name": "Instagram",   "url": "https://www.instagram.com/{}/", "emoji": "📸"},
    {"name": "Twitter/X",   "url": "https://twitter.com/{}", "emoji": "🐦"},
    {"name": "YouTube",     "url": "https://www.youtube.com/@{}", "emoji": "▶️"},
    {"name": "GitHub",      "url": "https://github.com/{}", "emoji": "💻"},
    {"name": "Reddit",      "url": "https://www.reddit.com/user/{}", "emoji": "🟠"},
    {"name": "Twitch",      "url": "https://www.twitch.tv/{}", "emoji": "🟣"},
    {"name": "Pinterest",   "url": "https://www.pinterest.com/{}/", "emoji": "📌"},
    {"name": "Snapchat",    "url": "https://www.snapchat.com/add/{}", "emoji": "👻"},
    {"name": "Steam",       "url": "https://steamcommunity.com/id/{}", "emoji": "🎮"},
    {"name": "Spotify",     "url": "https://open.spotify.com/user/{}", "emoji": "🎧"},
    {"name": "Roblox",      "url": "https://www.roblox.com/user.aspx?username={}", "emoji": "🧱"},
]

async def check_platform(session: aiohttp.ClientSession, platform: dict, username: str) -> dict:
    """Vérifie si un pseudo existe sur une plateforme via une requête HTTP."""
    url = platform["url"].format(username)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5), allow_redirects=True) as resp:
            # On considère le profil comme trouvé si le status est 200
            found = resp.status == 200
            return {"name": platform["name"], "emoji": platform["emoji"], "url": url, "found": found}
    except Exception:
        return {"name": platform["name"], "emoji": platform["emoji"], "url": url, "found": False}


@bot.tree.command(name="osint", description="🔍 Recherche OSINT sur un pseudo (réseaux sociaux, email, téléphone, adresse)")
@discord.app_commands.describe(
    pseudo="Pseudo à rechercher sur les réseaux sociaux",
    email="Adresse email à rechercher (optionnel)",
    telephone="Numéro de téléphone à rechercher (optionnel)",
    adresse="Adresse / ville à rechercher (optionnel)"
)
async def osint(
    interaction: discord.Interaction,
    pseudo: str,
    email: str = None,
    telephone: str = None,
    adresse: str = None
):
    # Defer car la recherche peut prendre du temps
    await interaction.response.defer(ephemeral=True)

    # ── Vérification des plateformes ──
    found_platforms = []
    not_found_platforms = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [check_platform(session, p, pseudo) for p in OSINT_PLATFORMS]
        results = await asyncio.gather(*tasks)

    for r in results:
        if r["found"]:
            found_platforms.append(r)
        else:
            not_found_platforms.append(r)

    # ── Construction de l'embed principal ──
    embed = discord.Embed(
        title=f"🕵️ Rapport OSINT — `{pseudo}`",
        color=discord.Color.dark_red()
    )
    embed.set_footer(text=f"Slayzix Shop • OSINT • Demandé par {interaction.user.name}")
    embed.timestamp = discord.utils.utcnow()

    # Résultats réseaux sociaux
    if found_platforms:
        found_text = "\n".join(
            [f"{p['emoji']} **[{p['name']}]({p['url']})**  ✅" for p in found_platforms]
        )
        embed.add_field(
            name=f"✅ Profils trouvés ({len(found_platforms)}/{len(OSINT_PLATFORMS)})",
            value=found_text,
            inline=False
        )
    else:
        embed.add_field(
            name="✅ Profils trouvés",
            value="❌ Aucun profil trouvé pour ce pseudo.",
            inline=False
        )

    if not_found_platforms:
        not_found_text = "  ".join([f"{p['emoji']} ~~{p['name']}~~" for p in not_found_platforms])
        embed.add_field(
            name=f"❌ Non trouvé ({len(not_found_platforms)}/{len(OSINT_PLATFORMS)})",
            value=not_found_text,
            inline=False
        )

    embed.add_field(name="​", value="──────────────────────", inline=False)

    # ── Email ──
    if email:
        # Validation basique du format
        email_valid = bool(re.match(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$", email))
        email_domain = email.split("@")[-1] if "@" in email else "?"
        email_info = (
            f"📧 **Adresse :** `{email}`\n"
            f"🌐 **Domaine :** `{email_domain}`\n"
            f"✅ **Format valide :** {'Oui' if email_valid else 'Non'}\n"
            f"🔗 **Recherche :** [Google](https://www.google.com/search?q=%22{email}%22) | "
            f"[HaveIBeenPwned](https://haveibeenpwned.com/account/{email})"
        )
        embed.add_field(name="📧 Email", value=email_info, inline=False)

    # ── Téléphone ──
    if telephone:
        # Nettoyage du numéro
        phone_clean = re.sub(r"[\s\-\.\(\)]", "", telephone)
        phone_info = (
            f"📞 **Numéro :** `{telephone}`\n"
            f"🔗 **Recherche :** [Google](https://www.google.com/search?q=%22{phone_clean}%22) | "
            f"[NumLookup](https://www.numlookup.com/?number={phone_clean})"
        )
        embed.add_field(name="📞 Téléphone", value=phone_info, inline=False)

    # ── Adresse ──
    if adresse:
        adresse_encoded = adresse.replace(" ", "+")
        adresse_info = (
            f"🏠 **Adresse :** `{adresse}`\n"
            f"🔗 **Recherche :** [Google Maps](https://www.google.com/maps/search/{adresse_encoded}) | "
            f"[Google](https://www.google.com/search?q=%22{adresse_encoded}%22)"
        )
        embed.add_field(name="🏠 Adresse", value=adresse_info, inline=False)

    # ── Liens de recherche globaux ──
    pseudo_encoded = pseudo.replace(" ", "+")
    global_links = (
        f"[Google](https://www.google.com/search?q=%22{pseudo_encoded}%22) | "
        f"[Sherlock](https://sherlock-project.github.io/) | "
        f"[WhatsMyName](https://whatsmyname.app/?q={pseudo})"
    )
    embed.add_field(name="🌐 Recherches globales", value=global_links, inline=False)

    embed.add_field(
        name="⚠️ Avertissement",
        value="*Ces données proviennent de sources **publiques** uniquement. Utilisation éthique et légale uniquement.*",
        inline=False
    )

    await interaction.followup.send(embed=embed, ephemeral=True)


# ================= ON READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} connecté et slash commands synchronisées !")


# ================= START =================

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    bot.run(TOKEN)
