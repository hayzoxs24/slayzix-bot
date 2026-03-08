import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime

# ================= INTENTS & BOT =================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= CONFIG =================

ticket_config = {
    "category": None,
    "log_channel": None,
    "support_role": None,
    "nitro_ping_role": None,  # Rôle à ping pour les tickets Nitro
}

open_tickets = {}  # user_id -> channel_id

# ================= PPL STORAGE =================

PPL_FILE = "ppl_data.json"

def load_ppl() -> dict:
    if os.path.exists(PPL_FILE):
        try:
            with open(PPL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_ppl(data: dict):
    with open(PPL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

ppl_data: dict = load_ppl()  # { "user_id": { "email": str, "nom": str, "note": str } }

# ================= PPL STORAGE =================

PPL_FILE = "ppl_data.json"

def load_ppl() -> dict:
    """Charge les données PPL depuis le fichier JSON."""
    if os.path.exists(PPL_FILE):
        try:
            with open(PPL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_ppl(data: dict):
    """Sauvegarde les données PPL dans le fichier JSON."""
    with open(PPL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

ppl_data: dict = load_ppl()  # { "user_id": { "email": str, "nom": str, "note": str } }

# ================= TICKET TYPES =================

TICKET_TYPES = [
    discord.SelectOption(label="Nitro",        emoji="<:nitro:1234567890>", description="Discord Nitro",      value="Nitro"),
    discord.SelectOption(label="Server Boost", emoji="🚀",                  description="Server Boost",        value="Server Boost"),
    discord.SelectOption(label="Decoration",   emoji="🎨",                  description="Profile Decoration",  value="Decoration"),
    discord.SelectOption(label="Exchange",     emoji="🔄",                  description="Trade / Exchange",    value="Exchange"),
    discord.SelectOption(label="Other",        emoji="📌",                  description="Other request",       value="Other"),
]

PAYMENT_OPTIONS = [
    discord.SelectOption(label="PayPal",       emoji="💳",  description="Pay via PayPal",  value="PayPal"),
]

LANG_OPTIONS = [
    discord.SelectOption(label="Français",     emoji="🇫🇷",  description="Continuer en français", value="fr"),
    discord.SelectOption(label="English",      emoji="🇬🇧",  description="Continue in English",   value="en"),
]

# ================= MESSAGES PAR LANGUE =================

MESSAGES = {
    "fr": {
        "ticket_title":   "🎫 Nouveau Ticket",
        "ticket_desc":    "Le support sera avec vous rapidement.\n\nPour fermer ce ticket, appuyez sur le bouton Fermer.",
        "ping_staff_tip": "🔔 Utilisez **Ping Staff** si aucune réponse après 15 min (cooldown 15 min)",
        "close":          "🔴 Fermer",
        "claim":          "🟢 Prendre en charge",
        "unclaim":        "🔴 Rendre",
        "transcript":     "📄 Transcript",
        "ping_staff":     "🔔 Ping Staff",
        "closing":        "🔒 Fermeture du ticket dans 5 secondes...",
        "closed_by":      "Ticket fermé par",
        "already_open":   "❌ Tu as déjà un ticket ouvert →",
        "created":        "✅ Ticket créé →",
    },
    "en": {
        "ticket_title":   "🎫 New Ticket",
        "ticket_desc":    "Support will be with you shortly.\n\nTo close this ticket, press the close button below.",
        "ping_staff_tip": "🔔 Use **Ping Staff** if no response after 15 min (15 min cooldown)",
        "close":          "🔴 Close",
        "claim":          "🟢 Claim",
        "unclaim":        "🔴 Unclaim",
        "transcript":     "📄 Transcript",
        "ping_staff":     "🔔 Ping Staff",
        "closing":        "🔒 Closing ticket in 5 seconds...",
        "closed_by":      "Ticket closed by",
        "already_open":   "❌ You already have an open ticket →",
        "created":        "✅ Ticket created →",
    }
}

# ================= PING STAFF COOLDOWN =================

ping_staff_cooldown = {}  # channel_id -> last_ping timestamp


# ================= VIEWS =================

class TicketActionsView(discord.ui.View):
    """Boutons dans le salon du ticket."""

    def __init__(self, lang: str, ticket_type: str, payment: str):
        super().__init__(timeout=None)
        self.lang = lang
        m = MESSAGES[lang]
        # On crée les boutons dynamiquement pour avoir les bons labels
        close_btn = discord.ui.Button(label=m["close"], style=discord.ButtonStyle.danger, custom_id="ticket_close", row=0)
        claim_btn = discord.ui.Button(label=m["claim"], style=discord.ButtonStyle.success, custom_id="ticket_claim", row=0)
        unclaim_btn = discord.ui.Button(label=m["unclaim"], style=discord.ButtonStyle.secondary, custom_id="ticket_unclaim", row=0)
        transcript_btn = discord.ui.Button(label=m["transcript"], style=discord.ButtonStyle.primary, custom_id="ticket_transcript", row=0)
        ping_btn = discord.ui.Button(label=m["ping_staff"], style=discord.ButtonStyle.secondary, emoji="🔔", custom_id="ticket_ping_staff", row=1)

        close_btn.callback = self.close_callback
        claim_btn.callback = self.claim_callback
        unclaim_btn.callback = self.unclaim_callback
        transcript_btn.callback = self.transcript_callback
        ping_btn.callback = self.ping_staff_callback

        self.add_item(close_btn)
        self.add_item(claim_btn)
        self.add_item(unclaim_btn)
        self.add_item(transcript_btn)
        self.add_item(ping_btn)

    async def close_callback(self, interaction: discord.Interaction):
        m = MESSAGES[self.lang]
        await interaction.response.send_message(m["closing"], ephemeral=False)
        # Log
        if ticket_config["log_channel"]:
            lc = interaction.guild.get_channel(ticket_config["log_channel"])
            if lc:
                e = discord.Embed(
                    title="📋 Ticket fermé",
                    description=f"**Salon :** {interaction.channel.name}\n**Par :** {interaction.user.mention}",
                    color=discord.Color.red()
                )
                e.timestamp = discord.utils.utcnow()
                await lc.send(embed=e)
        # Retire de open_tickets
        for uid, cid in list(open_tickets.items()):
            if cid == interaction.channel.id:
                del open_tickets[uid]
                break
        await asyncio.sleep(5)
        await interaction.channel.delete()

    async def claim_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            description=f"✅ Ticket pris en charge par {interaction.user.mention}" if self.lang == "fr" else f"✅ Ticket claimed by {interaction.user.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    async def unclaim_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            description=f"🔄 Ticket rendu par {interaction.user.mention}" if self.lang == "fr" else f"🔄 Ticket unclaimed by {interaction.user.mention}",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

    async def transcript_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        messages = []
        async for msg in interaction.channel.history(limit=200, oldest_first=True):
            if not msg.author.bot:
                messages.append(f"[{msg.created_at.strftime('%d/%m/%Y %H:%M')}] {msg.author.name}: {msg.content}")
        if not messages:
            content = "Aucun message." if self.lang == "fr" else "No messages."
            return await interaction.followup.send(content, ephemeral=True)
        transcript_text = "\n".join(messages)
        file = discord.File(
            fp=__import__("io").BytesIO(transcript_text.encode()),
            filename=f"transcript-{interaction.channel.name}.txt"
        )
        await interaction.followup.send(
            "📄 Transcript généré !" if self.lang == "fr" else "📄 Transcript generated!",
            file=file,
            ephemeral=True
        )

    async def ping_staff_callback(self, interaction: discord.Interaction):
        now = datetime.utcnow().timestamp()
        last_ping = ping_staff_cooldown.get(interaction.channel.id, 0)
        if now - last_ping < 900:  # 15 minutes
            remaining = int(900 - (now - last_ping))
            msg = f"⏳ Cooldown actif ! Réessaie dans **{remaining // 60}m {remaining % 60}s**." if self.lang == "fr" else f"⏳ Cooldown active! Try again in **{remaining // 60}m {remaining % 60}s**."
            return await interaction.response.send_message(msg, ephemeral=True)
        ping_staff_cooldown[interaction.channel.id] = now
        role = interaction.guild.get_role(ticket_config["support_role"]) if ticket_config["support_role"] else None
        if role:
            await interaction.channel.send(
                f"🔔 {role.mention} — " + ("Un client attend de l'aide !" if self.lang == "fr" else "A customer needs help!"),
                allowed_mentions=discord.AllowedMentions(roles=True)
            )
        await interaction.response.send_message("✅ Staff pingé !" if self.lang == "fr" else "✅ Staff pinged!", ephemeral=True)


class LangSelect(discord.ui.Select):
    """Étape 3 : choix de la langue."""

    def __init__(self, ticket_type: str, payment: str, user_id: int):
        super().__init__(
            placeholder="🌍 Select your language / Choisissez votre langue...",
            min_values=1, max_values=1,
            options=LANG_OPTIONS,
            custom_id="lang_select"
        )
        self.ticket_type = ticket_type
        self.payment = payment
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        lang = self.values[0]
        await interaction.response.defer(ephemeral=True)
        await create_ticket_channel(interaction, self.ticket_type, self.payment, lang)


class LangView(discord.ui.View):
    def __init__(self, ticket_type: str, payment: str, user_id: int):
        super().__init__(timeout=120)
        self.add_item(LangSelect(ticket_type, payment, user_id))


class PaymentSelect(discord.ui.Select):
    """Étape 2 : choix du moyen de paiement."""

    def __init__(self, ticket_type: str, user_id: int):
        super().__init__(
            placeholder="💳 Select your payment method...",
            min_values=1, max_values=1,
            options=PAYMENT_OPTIONS,
            custom_id="payment_select"
        )
        self.ticket_type = ticket_type
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        payment = self.values[0]
        lang_embed = discord.Embed(
            title="🌍 Language / Langue",
            description="Please select your language to continue.\nVeuillez sélectionner votre langue pour continuer.",
            color=discord.Color.blurple()
        )
        lang_embed.set_footer(text="Your ticket will be created after selection • Le ticket sera créé après la sélection")
        await interaction.response.edit_message(
            embed=lang_embed,
            view=LangView(self.ticket_type, payment, self.user_id)
        )


class PaymentView(discord.ui.View):
    def __init__(self, ticket_type: str, user_id: int):
        super().__init__(timeout=120)
        self.add_item(PaymentSelect(ticket_type, user_id))


class TicketTypeSelect(discord.ui.Select):
    """Étape 1 : choix du type de ticket."""

    def __init__(self):
        super().__init__(
            placeholder="🎫 Select a category...",
            min_values=1, max_values=1,
            options=TICKET_TYPES,
            custom_id="ticket_type_select"
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id in open_tickets:
            existing = interaction.guild.get_channel(open_tickets[interaction.user.id])
            if existing:
                return await interaction.response.send_message(
                    f"❌ You already have an open ticket → {existing.mention}",
                    ephemeral=True
                )

        ticket_type = self.values[0]
        payment_embed = discord.Embed(
            title="💳 Payment Method",
            description="Please select your preferred payment method to create your ticket:",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        payment_embed.set_footer(text="Your ticket will be created after selection")
        await interaction.response.send_message(
            embed=payment_embed,
            view=PaymentView(ticket_type, interaction.user.id),
            ephemeral=True
        )


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())


# ================= CRÉATION DU SALON TICKET =================

async def create_ticket_channel(interaction: discord.Interaction, ticket_type: str, payment: str, lang: str):
    guild = interaction.guild
    user = interaction.user
    m = MESSAGES[lang]

    if user.id in open_tickets:
        existing = guild.get_channel(open_tickets[user.id])
        if existing:
            await interaction.followup.send(f"{m['already_open']} {existing.mention}", ephemeral=True)
            return

    # Catégorie
    category = guild.get_channel(ticket_config["category"]) if ticket_config["category"] else None
    if not category:
        category = discord.utils.get(guild.categories, name="TICKETS") or await guild.create_category("TICKETS")

    # Permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
    }
    if ticket_config["support_role"]:
        role = guild.get_role(ticket_config["support_role"])
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    # Nom du salon
    channel_name = f"{ticket_type.lower().replace(' ', '-')}-{user.name}"
    channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites, category=category)
    open_tickets[user.id] = channel.id

    # Mentions pour le ping
    mention_str = user.mention
    if ticket_config["support_role"]:
        mention_str += f" <@&{ticket_config['support_role']}>"

    # Embed dans le ticket
    flag = "🇫🇷" if lang == "fr" else "🇬🇧"
    embed = discord.Embed(
        title=m["ticket_title"],
        description=m["ticket_desc"],
        color=discord.Color.red()
    )
    embed.add_field(name="📦 Type", value=ticket_type, inline=True)
    embed.add_field(name="💳 Payment", value=payment, inline=True)
    embed.add_field(name=f"{flag} Language", value="Français" if lang == "fr" else "English", inline=True)
    embed.set_footer(text=m["ping_staff_tip"])
    embed.timestamp = discord.utils.utcnow()

    await channel.send(
        content=mention_str,
        embed=embed,
        view=TicketActionsView(lang, ticket_type, payment),
        allowed_mentions=discord.AllowedMentions(users=True, roles=True)
    )

    # Log
    if ticket_config["log_channel"]:
        lc = guild.get_channel(ticket_config["log_channel"])
        if lc:
            log_embed = discord.Embed(
                title="📋 Ticket ouvert" if lang == "fr" else "📋 Ticket opened",
                description=f"**Utilisateur :** {user.mention}\n**Type :** {ticket_type}\n**Paiement :** {payment}\n**Langue :** {'Français' if lang == 'fr' else 'English'}\n**Salon :** {channel.mention}",
                color=discord.Color.green()
            )
            log_embed.timestamp = discord.utils.utcnow()
            await lc.send(embed=log_embed)

    await interaction.followup.send(f"{m['created']} {channel.mention}", ephemeral=True)


# ================= COMMANDES DE CONFIGURATION =================

class SetupCategorySelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="📁 Catégorie des tickets", channel_types=[discord.ChannelType.category])
    async def callback(self, interaction: discord.Interaction):
        ticket_config["category"] = self.values[0].id
        await interaction.response.send_message(f"✅ Catégorie : **{self.values[0].name}**", ephemeral=True)

class SetupLogSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="📋 Salon des logs", channel_types=[discord.ChannelType.text])
    async def callback(self, interaction: discord.Interaction):
        ticket_config["log_channel"] = self.values[0].id
        await interaction.response.send_message(f"✅ Logs : {self.values[0].mention}", ephemeral=True)

class SetupRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="👮 Rôle support (staff)")
    async def callback(self, interaction: discord.Interaction):
        ticket_config["support_role"] = self.values[0].id
        await interaction.response.send_message(f"✅ Rôle support : {self.values[0].mention}", ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SetupCategorySelect())
        self.add_item(SetupLogSelect())
        self.add_item(SetupRoleSelect())

    @discord.ui.button(label="📨 Envoyer le panel ici", style=discord.ButtonStyle.success, row=2)
    async def send_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        panel_embed = discord.Embed(
            title="🎫 Support Ticket System",
            description=(
                "Select a category below to create a support ticket.\n\n"
                "Our team will assist you as soon as possible."
            ),
            color=discord.Color.from_rgb(180, 0, 0)
        )
        panel_embed.set_footer(text="Please provide detailed information in your ticket")
        await interaction.channel.send(embed=panel_embed, view=TicketPanelView())
        await interaction.response.send_message("✅ Panel envoyé !", ephemeral=True)


@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Configure et déploie le panel de tickets."""
    embed = discord.Embed(
        title="⚙️ Configuration du Ticket System",
        description=(
            "**1️⃣** Sélectionne la catégorie des tickets\n"
            "**2️⃣** Sélectionne le salon des logs\n"
            "**3️⃣** Sélectionne le rôle support\n\n"
            "Puis clique sur **📨 Envoyer le panel ici** pour déployer !"
        ),
        color=discord.Color.blurple()
    )
    await ctx.message.delete()
    await ctx.send(embed=embed, view=SetupView())



# ================= PPL COMMANDS =================

class PPLSaveModal(discord.ui.Modal, title="💳 Sauvegarder mon PPL PayPal"):
    email = discord.ui.TextInput(
        label="Email PayPal",
        placeholder="exemple@email.com",
        required=True,
        max_length=100
    )
    nom = discord.ui.TextInput(
        label="Nom affiché sur le compte PayPal",
        placeholder="Jean Dupont",
        required=True,
        max_length=100
    )
    note = discord.ui.TextInput(
        label="Note / Info supplémentaire (optionnel)",
        placeholder="Ex: Compte pro, paiements en EUR...",
        required=False,
        max_length=300,
        style=discord.TextStyle.long
    )

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        ppl_data[uid] = {
            "email": self.email.value.strip(),
            "nom": self.nom.value.strip(),
            "note": self.note.value.strip() if self.note.value else "",
            "updated_at": datetime.utcnow().strftime("%d/%m/%Y %H:%M"),
        }
        save_ppl(ppl_data)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ PPL sauvegardé !",
                description="Ton PayPal a bien été enregistré.\nUtilise `*ppl` pour l'afficher.",
                color=discord.Color.green()
            ),
            ephemeral=True
        )


@bot.command(name="pplsave")
async def pplsave(ctx):
    """Ouvre le formulaire pour sauvegarder son PPL PayPal."""

    class PPLSaveView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)

        @discord.ui.button(label="💳 Sauvegarder mon PayPal", style=discord.ButtonStyle.success, emoji="💾")
        async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("❌ Ce bouton n'est pas pour toi.", ephemeral=True)
            await interaction.response.send_modal(PPLSaveModal())

    embed = discord.Embed(
        title="💳 Sauvegarde PPL PayPal",
        description=(
            "Clique sur le bouton ci-dessous pour enregistrer ton adresse PayPal.\n\n"
            "📌 Ces informations seront affichées quand tu utiliseras `*ppl`.\n"
            "🔒 Seul toi peut modifier tes données."
        ),
        color=discord.Color.from_rgb(0, 48, 135)
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text="Tes données sont stockées localement sur le bot.")
    await ctx.message.delete()
    await ctx.send(embed=embed, view=PPLSaveView())


@bot.command(name="ppl")
async def ppl(ctx):
    """Affiche le PPL PayPal de la personne qui exécute la commande — visible par tous, jamais supprimé."""
    uid = str(ctx.author.id)
    await ctx.message.delete()

    if uid not in ppl_data or not ppl_data[uid].get("email"):
        embed = discord.Embed(
            title="❌ Aucun PPL enregistré",
            description=(
                f"{ctx.author.mention}, tu n'as pas encore sauvegardé ton PayPal.\n\n"
                "Utilise `*pplsave` pour enregistrer ton adresse PayPal."
            ),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        return await ctx.send(embed=embed, delete_after=10)

    data = ppl_data[uid]
    email = data["email"]

    class CopyPPLView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="📋 Copier le PayPal", style=discord.ButtonStyle.secondary, emoji="💳")
        async def copy_ppl(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                f"📋 **PayPal de {ctx.author.display_name} :**\n```{email}```\n*Clique sur l'email ci-dessus pour le copier !*",
                ephemeral=True
            )

    embed = discord.Embed(
        title="💳 Informations PayPal",
        color=discord.Color.from_rgb(0, 48, 135)
    )
    embed.set_author(
        name=ctx.author.display_name,
        icon_url=ctx.author.display_avatar.url
    )
    embed.add_field(
        name="📧 Email PayPal",
        value=f"```{email}```",
        inline=False
    )
    embed.add_field(
        name="👤 Nom du compte",
        value=f"```{data['nom']}```",
        inline=True
    )
    embed.add_field(
        name="🕐 Dernière mise à jour",
        value=f"`{data.get('updated_at', 'Inconnu')}`",
        inline=True
    )
    if data.get("note"):
        embed.add_field(
            name="📝 Note",
            value=data["note"],
            inline=False
        )
    embed.set_thumbnail(url="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_111x69.jpg")
    embed.set_footer(text=f"PPL de {ctx.author.name} • Utilise *pplsave pour modifier")
    embed.timestamp = discord.utils.utcnow()

    await ctx.send(embed=embed, view=CopyPPLView())


@bot.command(name="ppldelete")
async def ppldelete(ctx):
    """Supprime le PPL sauvegardé de la personne."""
    uid = str(ctx.author.id)
    await ctx.message.delete()
    if uid not in ppl_data:
        return await ctx.send(
            embed=discord.Embed(description="❌ Aucun PPL à supprimer.", color=discord.Color.red()),
            delete_after=8
        )
    del ppl_data[uid]
    save_ppl(ppl_data)
    await ctx.send(
        embed=discord.Embed(
            title="🗑️ PPL supprimé",
            description="Ton adresse PayPal a été supprimée avec succès.",
            color=discord.Color.orange()
        ),
        delete_after=8
    )


# ================= /HELP =================

@bot.tree.command(name="help", description="📋 Affiche toutes les commandes disponibles")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Liste des commandes",
        description="Toutes les commandes utilisent le préfixe **`*`**",
        color=discord.Color.from_rgb(0, 48, 135)
    )

    embed.add_field(
        name="🎫 __Tickets__",
        value=(
            "`*setup` — *(Admin)* Configure et déploie le panel de tickets\n"
        ),
        inline=False
    )

    embed.add_field(
        name="💳 __PayPal (PPL)__",
        value=(
            "`*pplsave` — Enregistre ton adresse PayPal\n"
            "`*ppl` — Affiche ton PayPal avec un bouton Copier\n"
            "`*ppldelete` — Supprime ton PayPal enregistré\n"
        ),
        inline=False
    )

    embed.add_field(
        name="ℹ️ __Infos__",
        value=(
            "• Les commandes `*` suppriment ton message automatiquement\n"
            "• `*ppl` est visible par tout le monde et ne disparaît jamais\n"
            "• `*pplsave` — seul toi peux modifier tes données\n"
            "• `/help` — cette commande"
        ),
        inline=False
    )

    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else discord.Embed.Empty)
    embed.set_footer(text="Préfixe : * • Slash : /help uniquement")
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= ON READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} connecté — Slash commands synchronisées !")
    print("🎫 Ticket System : OK")
    print("💳 PayPal Only  : OK")
    print("🌍 FR / EN Lang : OK")
    print("💳 PPL System   : OK")
    print("📋 /help        : OK")


# ================= START =================

if __name__ == "__main__":
    import os
    TOKEN = os.environ.get("TOKEN")
    if not TOKEN:
        raise ValueError("❌ TOKEN introuvable ! Ajoute la variable d'environnement TOKEN sur Railway.")
    bot.run(TOKEN)
