import discord
from discord.ext import commands
import os
import asyncio
import random
import anthropic
from datetime import datetime, timedelta

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= CONFIG =================

vouch_channel_id = None
vouch_role_id = None
welcome_channel_id = None
goodbye_channel_id = None
autoping_channel_id = None
invite_log_channel_id = None

ticket_config = {
    "category": None,
    "log_channel": None,
    "support_role": None,
    "welcome_message": "Bienvenue ! Un membre du staff va vous répondre rapidement.",
}

open_tickets = {}       # {user_id: channel_id}
active_giveaways = {}   # {message_id: giveaway_data}
guild_invites = {}      # {invite_code: uses}

# ================= WELCOME / GOODBYE =================

@bot.event
async def on_member_join(member):
    # ── Autoping ──
    if autoping_channel_id:
        ping_channel = member.guild.get_channel(autoping_channel_id)
        if ping_channel:
            await ping_channel.send(
                f"👋 Bienvenue {member.mention} sur **{member.guild.name}** !",
                allowed_mentions=discord.AllowedMentions(users=True)
            )

    # ── Welcome embed ──
    if welcome_channel_id:
        channel = member.guild.get_channel(welcome_channel_id)
        if channel:
            member_count = member.guild.member_count
            embed = discord.Embed(
                title="🎉 Bienvenue sur le serveur !",
                description=(
                    f"Salut {member.mention}, on est ravis de t'accueillir sur **{member.guild.name}** ! 🙌\n\n"
                    f"Tu es le **{member_count}ème** membre à nous rejoindre.\n\n"
                    "──────────────────────\n"
                    "🛒 Consulte nos services et passe ta commande !\n"
                    "💬 Notre équipe est là pour t'aider."
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(
                text=f"Slayzix Shop • Bienvenue parmi nous ! • {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}"
            )
            # content= permet le vrai ping en dehors de l'embed
            await channel.send(
                content=member.mention,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=True)
            )

    # ── Invite log ──
    if invite_log_channel_id:
        log_channel = member.guild.get_channel(invite_log_channel_id)
        if log_channel:
            try:
                new_invites = await member.guild.fetch_invites()
                inviter = None
                for inv in new_invites:
                    old_uses = guild_invites.get(inv.code, 0)
                    if inv.uses > old_uses:
                        inviter = inv.inviter
                        guild_invites[inv.code] = inv.uses
                        break
                for inv in new_invites:
                    guild_invites[inv.code] = inv.uses

                inv_embed = discord.Embed(
                    title="📨 Nouveau membre",
                    description=(
                        f"**Membre :** {member.mention} (`{member.name}`)\n"
                        f"**Invité par :** {inviter.mention if inviter else 'Inconnu'}\n"
                        f"**Compte créé :** <t:{int(member.created_at.timestamp())}:R>"
                    ),
                    color=discord.Color.green()
                )
                inv_embed.set_thumbnail(url=member.display_avatar.url)
                inv_embed.timestamp = discord.utils.utcnow()
                await log_channel.send(embed=inv_embed)
            except Exception:
                pass


@bot.event
async def on_member_remove(member):
    if not goodbye_channel_id:
        return
    channel = member.guild.get_channel(goodbye_channel_id)
    if not channel:
        return

    member_count = member.guild.member_count
    embed = discord.Embed(
        title="👋 Départ du serveur",
        description=(
            f"**{member.name}** vient de quitter **{member.guild.name}**...\n\n"
            f"Il reste désormais **{member_count} membres** sur le serveur.\n\n"
            "──────────────────────\n"
            "😊 On espère te revoir bientôt !"
        ),
        color=discord.Color.red()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(
        text=f"Slayzix Shop • À bientôt ! • {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}"
    )
    await channel.send(embed=embed)


# ================= !welcome =================

class WelcomeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon de bienvenue", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        global welcome_channel_id
        welcome_channel_id = self.values[0].id
        await interaction.response.send_message(
            f"✅ Salon de bienvenue défini : {self.values[0].mention}", ephemeral=True
        )

class WelcomeSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(WelcomeChannelSelect())

@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    embed = discord.Embed(
        title="⚙️ Configuration — Salon de bienvenue",
        description="Sélectionne le salon où les messages de bienvenue seront envoyés.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=WelcomeSetupView())


# ================= !goodbye =================

class GoodbyeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon d'au revoir", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        global goodbye_channel_id
        goodbye_channel_id = self.values[0].id
        await interaction.response.send_message(
            f"✅ Salon d'au revoir défini : {self.values[0].mention}", ephemeral=True
        )

class GoodbyeSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GoodbyeChannelSelect())

@bot.command()
@commands.has_permissions(administrator=True)
async def goodbye(ctx):
    embed = discord.Embed(
        title="⚙️ Configuration — Salon d'au revoir",
        description="Sélectionne le salon où les messages d'au revoir seront envoyés.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=GoodbyeSetupView())


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


# ================= TICKET PANEL — SELECT MENU =================

TICKET_OPTIONS = [
    discord.SelectOption(label="Général",     emoji="🎫", description="Question générale",        value="Général"),
    discord.SelectOption(label="Support",     emoji="❓", description="Problème / aide",           value="Support"),
    discord.SelectOption(label="Commande",    emoji="💰", description="Passer une commande",       value="Commande"),
    discord.SelectOption(label="Signalement", emoji="⚠️", description="Signaler un problème",      value="Signalement"),
    discord.SelectOption(label="Partenariat", emoji="🤝", description="Proposer un partenariat",   value="Partenariat"),
    discord.SelectOption(label="Giveaway",    emoji="🎉", description="Organiser un giveaway",     value="Giveaway"),
    discord.SelectOption(label="Récompense",  emoji="🏆", description="Réclamer une récompense",   value="Récompense"),
]

class TicketSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="📂 Choisis le type de ticket...",
            min_values=1,
            max_values=1,
            options=TICKET_OPTIONS,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await open_ticket_for(interaction, self.values[0])

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


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

class TicketConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())
        self.add_item(TicketLogSelect())
        self.add_item(TicketRoleSelect())

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


# ================= MODÉRATION =================

@bot.tree.command(name="clear", description="Supprime des messages dans ce salon")
@discord.app_commands.describe(nombre="Nombre de messages à supprimer (1-100)")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, nombre: int = 10):
    if nombre < 1 or nombre > 100:
        return await interaction.response.send_message("❌ Entre 1 et 100 messages.", ephemeral=True)
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
        await membre.send(
            embed=discord.Embed(
                title="🔨 Tu as été banni",
                description=f"**Serveur :** {interaction.guild.name}\n**Raison :** {raison}",
                color=discord.Color.red()
            )
        )
    except Exception:
        pass
    await membre.ban(reason=raison)
    embed = discord.Embed(
        title="🔨 Membre banni",
        description=(
            f"**Membre :** {membre.mention} (`{membre.name}`)\n"
            f"**Raison :** {raison}\n"
            f"**Par :** {interaction.user.mention}"
        ),
        color=discord.Color.red()
    )
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="unban", description="Débannir un utilisateur par son ID")
@discord.app_commands.describe(user_id="L'ID de l'utilisateur à débannir")
@discord.app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        embed = discord.Embed(
            title="✅ Membre débanni",
            description=f"**Utilisateur :** {user.mention} (`{user.name}`)\n**Par :** {interaction.user.mention}",
            color=discord.Color.green()
        )
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
    for ban_entry in bans:
        try:
            await interaction.guild.unban(ban_entry.user)
            count += 1
        except Exception:
            pass
    await interaction.followup.send(
        embed=discord.Embed(
            title="✅ Déban général",
            description=f"**{count}** membre(s) ont été débanni(s).",
            color=discord.Color.green()
        ),
        ephemeral=True
    )


# ================= /autoping =================

class AutopingChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon d'autoping", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        global autoping_channel_id
        autoping_channel_id = self.values[0].id
        await interaction.response.send_message(
            f"✅ Autoping activé dans {self.values[0].mention}", ephemeral=True
        )

class AutopingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AutopingChannelSelect())

@bot.tree.command(name="autoping", description="Ping automatiquement les nouveaux membres dans un salon")
@discord.app_commands.checks.has_permissions(administrator=True)
async def autoping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Configuration — Autoping",
        description="Sélectionne le salon où les nouveaux membres seront pingés à leur arrivée.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=AutopingView(), ephemeral=True)


# ================= /invitelog =================

class InviteLogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon des logs d'invite", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        global invite_log_channel_id
        invite_log_channel_id = self.values[0].id
        try:
            invites = await interaction.guild.fetch_invites()
            for inv in invites:
                guild_invites[inv.code] = inv.uses
        except Exception:
            pass
        await interaction.response.send_message(
            f"✅ Logs d'invitations définis : {self.values[0].mention}", ephemeral=True
        )

class InviteLogView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(InviteLogChannelSelect())

@bot.tree.command(name="invitelog", description="Définit le salon pour les logs d'invitation")
@discord.app_commands.checks.has_permissions(administrator=True)
async def invitelog(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Configuration — Logs d'invitations",
        description="Sélectionne le salon où seront enregistrés les logs d'invitations.",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed, view=InviteLogView(), ephemeral=True)


# ================= /say =================

@bot.tree.command(name="say", description="Faire parler le bot")
@discord.app_commands.describe(message="Le message à envoyer", salon="Salon cible (optionnel)")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def say(interaction: discord.Interaction, message: str, salon: discord.TextChannel = None):
    target = salon or interaction.channel
    await target.send(message)
    await interaction.response.send_message(f"✅ Message envoyé dans {target.mention}.", ephemeral=True)


# ================= /ia =================

@bot.tree.command(name="ia", description="Pose une question à l'IA Claude")
@discord.app_commands.describe(question="Ta question pour l'IA")
async def ia(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": question}]
        )
        answer = response.content[0].text

        embed = discord.Embed(title="🤖 Claude IA", color=discord.Color.blurple())
        embed.add_field(name="❓ Question", value=question[:1024], inline=False)
        if len(answer) > 1024:
            answer = answer[:1021] + "..."
        embed.add_field(name="💬 Réponse", value=answer, inline=False)
        embed.set_footer(text=f"Demandé par {interaction.user.name} • Slayzix Shop")
        embed.timestamp = discord.utils.utcnow()
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur IA : `{e}`", ephemeral=True)


# ================= /embed =================

@bot.tree.command(name="embed", description="Créer et envoyer un embed personnalisé")
@discord.app_commands.describe(
    titre="Titre de l'embed",
    description="Description de l'embed",
    couleur="Couleur hex sans # (ex: ff0000)",
    salon="Salon cible (optionnel)",
    image="URL d'une image (optionnel)",
    footer="Texte du footer (optionnel)"
)
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def embed_cmd(
    interaction: discord.Interaction,
    titre: str,
    description: str,
    couleur: str = "5865f2",
    salon: discord.TextChannel = None,
    image: str = None,
    footer: str = None
):
    try:
        color = discord.Color(int(couleur.strip("#"), 16))
    except ValueError:
        color = discord.Color.blurple()

    embed = discord.Embed(title=titre, description=description, color=color)
    embed.timestamp = discord.utils.utcnow()

    if image:
        embed.set_image(url=image)
    if footer:
        embed.set_footer(text=footer)
    else:
        embed.set_footer(text=f"Slayzix Shop • Par {interaction.user.name}")

    target = salon or interaction.channel
    await target.send(embed=embed)
    await interaction.response.send_message(f"✅ Embed envoyé dans {target.mention}.", ephemeral=True)


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
            count = len(giveaway["participants"])
            button.label = f"🎉 Participer — {count}"
            await interaction.message.edit(view=self)
            return await interaction.response.send_message("❌ Tu t'es retiré du giveaway.", ephemeral=True)

        giveaway["participants"].add(interaction.user.id)
        count = len(giveaway["participants"])
        button.label = f"🎉 Participer — {count}"
        await interaction.message.edit(view=self)
        await interaction.response.send_message("✅ Tu participes au giveaway ! Bonne chance 🍀", ephemeral=True)


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
    winners_count = giveaway["winners"]
    prize = giveaway["prize"]
    host = giveaway["host"]

    if not participants:
        embed = discord.Embed(
            title="🎉 GIVEAWAY TERMINÉ",
            description=(
                f"**Prix :** {prize}\n"
                f"**Organisateur :** <@{host}>\n\n"
                "😔 Personne n'a participé... Pas de gagnant !"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="Slayzix Shop • Giveaway terminé")
        embed.timestamp = discord.utils.utcnow()
        await message.edit(embed=embed, view=None)
        await channel.send("😔 Aucun participant, pas de gagnant pour ce giveaway !")
        del active_giveaways[message_id]
        return

    winners = random.sample(participants, min(winners_count, len(participants)))
    winners_mentions = " ".join([f"<@{w}>" for w in winners])

    embed = discord.Embed(
        title="🎉 GIVEAWAY TERMINÉ",
        description=(
            f"**Prix :** {prize}\n"
            f"**Gagnant(s) :** {winners_mentions}\n"
            f"**Organisateur :** <@{host}>\n"
            f"**Participants :** {len(participants)}"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Slayzix Shop • Giveaway terminé")
    embed.timestamp = discord.utils.utcnow()

    await message.edit(embed=embed, view=None)
    await channel.send(
        f"🎊 Félicitations {winners_mentions} ! Tu as gagné **{prize}** !\n"
        f"Contacte <@{host}> pour récupérer ton prix."
    )
    del active_giveaways[message_id]


@bot.tree.command(name="giveaway", description="Lance un giveaway !")
@discord.app_commands.describe(
    duree="Durée (ex: 10s, 5m, 1h, 2d)",
    gagnants="Nombre de gagnants",
    prix="Ce que tu fais gagner"
)
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
        return await interaction.response.send_message(
            "❌ Format invalide. Exemples : `30s`, `5m`, `1h`, `2d`", ephemeral=True
        )

    if gagnants < 1:
        return await interaction.response.send_message("❌ Minimum 1 gagnant.", ephemeral=True)

    end_time = datetime.utcnow() + timedelta(seconds=seconds)
    end_timestamp = int(end_time.timestamp())

    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=(
            f"**Prix :** {prix}\n"
            f"**Gagnant(s) :** {gagnants}\n"
            f"**Organisateur :** {interaction.user.mention}\n"
            f"**Fin :** <t:{end_timestamp}:R> (<t:{end_timestamp}:f>)\n\n"
            "Clique sur 🎉 pour participer !"
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Slayzix Shop • Giveaway")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message("✅ Giveaway lancé !", ephemeral=True)
    msg = await interaction.channel.send(embed=embed)

    active_giveaways[msg.id] = {
        "prize": prix,
        "winners": gagnants,
        "host": interaction.user.id,
        "participants": set(),
        "end_time": end_timestamp,
        "channel_id": interaction.channel.id
    }

    view = GiveawayView(msg.id)
    await msg.edit(view=view)

    await asyncio.sleep(seconds)
    await end_giveaway(interaction.channel.id, msg.id, interaction.guild)


@bot.tree.command(name="reroll", description="Nouveau tirage pour un giveaway terminé")
@discord.app_commands.describe(message_id="L'ID du message du giveaway terminé")
@discord.app_commands.checks.has_permissions(manage_guild=True)
async def reroll(interaction: discord.Interaction, message_id: str):
    try:
        await interaction.channel.fetch_message(int(message_id))
    except Exception:
        return await interaction.response.send_message("❌ Message introuvable.", ephemeral=True)
    await interaction.response.send_message(
        "🎲 Les participants ne sont plus dispo après la fin. Utilise `/giveaway` pour relancer !",
        ephemeral=True
    )


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
    colors = {
        1: discord.Color.red(), 2: discord.Color.orange(),
        3: discord.Color.yellow(), 4: discord.Color.green(), 5: discord.Color.gold()
    }
    badges = {
        1: "😡 Très mauvais", 2: "😕 Mauvais",
        3: "😐 Correct", 4: "😊 Bien", 5: "🤩 Excellent !"
    }

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
