import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime

# ================= INTENTS & BOT =================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="*", intents=intents)

# ================= CONFIG =================

ticket_config = {
    "category": None,
    "log_channel": None,
    "support_role": None,
    # Rôles ping par langue
    "role_french": None,
    "role_english": None,
    # Rôles ping par type de ticket
    "role_nitro": None,
    "role_boost": None,
    "role_decoration": None,
    "role_exchange": None,
    "role_other": None,
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
    discord.SelectOption(label="Nitro",        emoji="<:Nitro:1480046132707987611>", description="Discord Nitro",      value="Nitro"),
    discord.SelectOption(label="Server Boost", emoji="<:Boost:1480046746146050149>", description="Server Boost",        value="Server Boost"),
    discord.SelectOption(label="Decoration",   emoji="<:Discord:1480047123188944906>", description="Profile Decoration",  value="Decoration"),
    discord.SelectOption(label="Exchange",     emoji="<:Exchange:1480047481491427492>", description="Trade / Exchange",    value="Exchange"),
    discord.SelectOption(label="Other",        emoji="<:Other:1480047561615085638>", description="Other request",       value="Other"),
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
        "ticket_title":   "<:Nitroo:1480046413441273968> Nouveau Ticket",
        "ticket_desc":    "Le support sera avec vous rapidement.\n\nPour fermer ce ticket, appuyez sur le bouton Fermer.",
        "ping_staff_tip": "🔔 Utilisez **Ping Staff** si aucune réponse après 15 min (cooldown 15 min)",
        "close":          "Fermer",
        "claim":          "Prendre en charge",
        "unclaim":        "Rendre",
        "transcript":     "Transcript",
        "ping_staff":     "Ping Staff",
        "closing":        "🔒 Fermeture du ticket dans 5 secondes...",
        "closed_by":      "Ticket fermé par",
        "already_open":   "❌ Tu as déjà un ticket ouvert →",
        "created":        "✅ Ticket créé →",
        "finish":         "✅ Finish",
    },
    "en": {
        "ticket_title":   "<:Nitroo:1480046413441273968> New Ticket",
        "ticket_desc":    "Support will be with you shortly.\n\nTo close this ticket, press the close button below.",
        "ping_staff_tip": "🔔 Use **Ping Staff** if no response after 15 min (15 min cooldown)",
        "close":          "Close",
        "claim":          "Claim",
        "unclaim":        "Unclaim",
        "transcript":     "Transcript",
        "ping_staff":     "Ping Staff",
        "closing":        "🔒 Closing ticket in 5 seconds...",
        "closed_by":      "Ticket closed by",
        "already_open":   "❌ You already have an open ticket →",
        "created":        "✅ Ticket created →",
        "finish":         "✅ Finish",
    }
}

# ================= PING STAFF COOLDOWN =================

ping_staff_cooldown = {}  # channel_id -> last_ping timestamp
ticket_claimers = {}  # channel_id -> claimer member id


# ================= VIEWS =================

class TicketActionsView(discord.ui.View):
    """Boutons dans le salon du ticket."""

    def __init__(self, lang: str, ticket_type: str, payment: str):
        super().__init__(timeout=None)
        self.lang = lang
        self.ticket_type = ticket_type
        m = MESSAGES[lang]
        # On crée les boutons dynamiquement pour avoir les bons labels
        close_btn      = discord.ui.Button(label=m["close"],       style=discord.ButtonStyle.secondary, custom_id="ticket_close",      emoji="<:Other:1480047561615085638>",    row=0)
        claim_btn      = discord.ui.Button(label=m["claim"],       style=discord.ButtonStyle.secondary, custom_id="ticket_claim",      emoji="<:Boost:1480046746146050149>",    row=0)
        unclaim_btn    = discord.ui.Button(label=m["unclaim"],     style=discord.ButtonStyle.secondary, custom_id="ticket_unclaim",    emoji="<:Exchange:1480047481491427492>", row=0)
        transcript_btn = discord.ui.Button(label=m["transcript"],  style=discord.ButtonStyle.secondary, custom_id="ticket_transcript", emoji="<:Transcript:1480047021707759727>", row=0)
        finish_btn     = discord.ui.Button(label=m["finish"],      style=discord.ButtonStyle.secondary, custom_id="ticket_finish",     emoji="<:oui:1480176155989508348>",      row=1)
        ping_btn       = discord.ui.Button(label=m["ping_staff"],  style=discord.ButtonStyle.secondary, emoji="<:Discord:1480047123188944906>", custom_id="ticket_ping_staff",   row=1)

        close_btn.callback      = self.close_callback
        claim_btn.callback      = self.claim_callback
        unclaim_btn.callback    = self.unclaim_callback
        transcript_btn.callback = self.transcript_callback
        finish_btn.callback     = self.finish_callback
        ping_btn.callback       = self.ping_staff_callback

        self.add_item(close_btn)
        self.add_item(claim_btn)
        self.add_item(unclaim_btn)
        self.add_item(transcript_btn)
        self.add_item(finish_btn)
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
        ticket_claimers[interaction.channel.id] = interaction.user.id
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

    async def finish_callback(self, interaction: discord.Interaction):
        """Envoie un modal vouch pré-rempli au client."""
        # Trouve le staff qui a claim le ticket
        claimer_id = ticket_claimers.get(interaction.channel.id)
        claimer = interaction.guild.get_member(claimer_id) if claimer_id else None

        class VouchModal(discord.ui.Modal, title="⭐ Leave a Review"):
            rating_input = discord.ui.TextInput(
                label="Rating (1 to 5)",
                placeholder="5",
                max_length=1,
                required=True
            )
            service_input = discord.ui.TextInput(
                label="Service purchased",
                placeholder="e.g. Nitro Basic",
                required=True,
                max_length=100
            )
            comment_input = discord.ui.TextInput(
                label="Comment",
                placeholder="Fast, legit, great service...",
                style=discord.TextStyle.long,
                required=True,
                max_length=500
            )

            def __init__(self_, claimer_member):
                super().__init__()
                self_.claimer_member = claimer_member

            async def on_submit(self_, modal_interaction: discord.Interaction):
                try:
                    rating = int(self_.rating_input.value.strip())
                    if rating < 1 or rating > 5:
                        return await modal_interaction.response.send_message("❌ Rating must be between 1 and 5.", ephemeral=True)
                except ValueError:
                    return await modal_interaction.response.send_message("❌ Rating must be a number.", ephemeral=True)

                staff = self_.claimer_member
                service = self_.service_input.value.strip()
                comment = self_.comment_input.value.strip()

                if not staff:
                    return await modal_interaction.response.send_message("❌ No staff found for this ticket. Ask staff to click **Claim** first.", ephemeral=True)

                stars = "⭐" * rating + "🌑" * (5 - rating)
                badges = {1: "😡 Very bad", 2: "😕 Bad", 3: "😐 Average", 4: "😊 Good", 5: "🤩 Excellent!"}

                staff_id = str(staff.id)
                vouch_counts[staff_id] = vouch_counts.get(staff_id, 0) + 1
                staff_total = vouch_counts[staff_id]
                save_vouches(vouch_counts)

                embed = discord.Embed(title="📝 New Review — Slayzix Shop", color=discord.Color.from_rgb(255, 0, 0))
                embed.add_field(name="👤 Customer", value=modal_interaction.user.mention, inline=True)
                embed.add_field(name="🛠️ Staff", value=staff.mention, inline=True)
                embed.add_field(name="📦 Service", value=f"**{service}**", inline=True)
                embed.add_field(name="⭐ Rating", value=f"{stars}  `{rating}/5` — {badges[rating]}", inline=False)
                embed.add_field(name="💬 Comment", value=f"*{comment}*", inline=False)
                embed.add_field(name="🏆 Staff Vouches", value=f"`{staff_total}` vouch(s) total", inline=False)
                embed.set_thumbnail(url=modal_interaction.user.display_avatar.url)
                embed.set_footer(text="Slayzix Shop • Thank you for your review!")
                embed.timestamp = discord.utils.utcnow()

                # Rôle auto +X vouch
                new_role_name = f"+{staff_total} vouch"
                existing_role = discord.utils.get(modal_interaction.guild.roles, name=new_role_name)
                if not existing_role:
                    try:
                        existing_role = await modal_interaction.guild.create_role(
                            name=new_role_name,
                            color=discord.Color.from_rgb(255, 0, 0),
                            reason=f"Vouch auto-role: {staff_total} vouches"
                        )
                        admin_roles = [r for r in modal_interaction.guild.roles if r.permissions.administrator and r != modal_interaction.guild.default_role]
                        if admin_roles:
                            lowest_admin = min(admin_roles, key=lambda r: r.position)
                            try:
                                await existing_role.edit(position=max(1, lowest_admin.position - 1))
                            except Exception:
                                pass
                    except discord.Forbidden:
                        existing_role = None

                if staff_total > 1:
                    old_role = discord.utils.get(modal_interaction.guild.roles, name=f"+{staff_total - 1} vouch")
                    if old_role and old_role in staff.roles:
                        try:
                            await staff.remove_roles(old_role)
                        except discord.Forbidden:
                            pass

                if existing_role and existing_role not in staff.roles:
                    try:
                        await staff.add_roles(existing_role)
                    except discord.Forbidden:
                        pass

                # Rôle de base au customer
                if vouch_config["role"]:
                    base_role = modal_interaction.guild.get_role(vouch_config["role"])
                    if base_role and base_role not in modal_interaction.user.roles:
                        try:
                            await modal_interaction.user.add_roles(base_role)
                        except discord.Forbidden:
                            pass

                if vouch_config["channel"]:
                    ch = modal_interaction.guild.get_channel(vouch_config["channel"])
                    if ch:
                        await ch.send(embed=embed)

                await modal_interaction.response.send_message(
                    f"✅ Review submitted! Thank you 🙏",
                    ephemeral=True
                )

        if not claimer:
            return await interaction.response.send_message(
                "❌ No staff has claimed this ticket yet. Ask your staff to click **Claim** first!",
                ephemeral=True
            )

        await interaction.response.send_modal(VouchModal(claimer))

    async def ping_staff_callback(self, interaction: discord.Interaction):
        now = datetime.utcnow().timestamp()
        last_ping = ping_staff_cooldown.get(interaction.channel.id, 0)
        if now - last_ping < 900:  # 15 minutes
            remaining = int(900 - (now - last_ping))
            msg = f"⏳ Cooldown actif ! Réessaie dans **{remaining // 60}m {remaining % 60}s**." if self.lang == "fr" else f"⏳ Cooldown active! Try again in **{remaining // 60}m {remaining % 60}s**."
            return await interaction.response.send_message(msg, ephemeral=True)
        ping_staff_cooldown[interaction.channel.id] = now

        # Détermine le rôle à pinger selon le type de ticket
        type_role_map = {
            "Nitro": "role_nitro",
            "Server Boost": "role_boost",
            "Decoration": "role_decoration",
            "Exchange": "role_exchange",
            "Other": "role_other",
        }
        mentions = []
        # Rôle support général
        if ticket_config["support_role"]:
            role = interaction.guild.get_role(ticket_config["support_role"])
            if role:
                mentions.append(role.mention)
        # Rôle spécifique au type
        type_key = type_role_map.get(self.ticket_type)
        if type_key and ticket_config.get(type_key):
            type_role = interaction.guild.get_role(ticket_config[type_key])
            if type_role and type_role.mention not in mentions:
                mentions.append(type_role.mention)

        if mentions:
            await interaction.channel.send(
                " ".join(mentions) + " — " + ("Un client attend de l'aide !" if self.lang == "fr" else "A customer needs help!"),
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
            placeholder="Select your payment method...",
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
            placeholder="Select a category...",
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
            title="<:Paiement:1480046846658351276> Payment Method",
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
    # Ping rôle langue
    lang_role_key = "role_french" if lang == "fr" else "role_english"
    if ticket_config.get(lang_role_key):
        mention_str += f" <@&{ticket_config[lang_role_key]}>"
    # Ping rôle type
    type_role_map = {
        "Nitro": "role_nitro",
        "Server Boost": "role_boost",
        "Decoration": "role_decoration",
        "Exchange": "role_exchange",
        "Other": "role_other",
    }
    type_role_key = type_role_map.get(ticket_type)
    if type_role_key and ticket_config.get(type_role_key):
        mention_str += f" <@&{ticket_config[type_role_key]}>"

    # Embed dans le ticket
    flag = "🇫🇷" if lang == "fr" else "🇬🇧"
    embed = discord.Embed(
        title=m["ticket_title"],
        description=m["ticket_desc"],
        color=discord.Color.red()
    )
    embed.add_field(name="<:Nitroo:1480046413441273968> Type", value=ticket_type, inline=True)
    embed.add_field(name="<:Paiement:1480046846658351276> Payment", value=payment, inline=True)
    embed.add_field(name="🌍 Language", value="🇫🇷 Français" if lang == "fr" else "🇬🇧 English", inline=True)
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
            title="<:Nitroo:1480046413441273968> Support Ticket System",
            description=(
                "Select a category below to create a support ticket.\n\n"
                "Our team will assist you as soon as possible."
            ),
            color=discord.Color.from_rgb(180, 0, 0)
        )
        panel_embed.set_image(url="https://i.ibb.co/fdJxKj7c/BANNIERE.png")
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

        @discord.ui.button(label="Sauvegarder mon PayPal", style=discord.ButtonStyle.success, emoji="<:PPL:1480046672162852985>")
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

        @discord.ui.button(label="Copier le PayPal", style=discord.ButtonStyle.secondary, emoji="<:PPL:1480046672162852985>")
        async def copy_ppl(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                f"📋 **PayPal de {ctx.author.display_name} :**\n```{email}```\n*Clique sur l'email ci-dessus pour le copier !*",
                ephemeral=True
            )

    embed = discord.Embed(
        title="<:PPL:1480046672162852985> Informations PayPal",
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
            "`*setfrench @role` — *(Admin)* Rôle pingé pour les tickets FR\n"
            "`*setenglish @role` — *(Admin)* Rôle pingé pour les tickets EN\n"
            "`*setnitro @role` — *(Admin)* Rôle pingé pour Nitro\n"
            "`*setboost @role` — *(Admin)* Rôle pingé pour Server Boost\n"
            "`*setdeco @role` — *(Admin)* Rôle pingé pour Decoration\n"
            "`*setexchange @role` — *(Admin)* Rôle pingé pour Exchange\n"
            "`*setother @role` — *(Admin)* Rôle pingé pour Other\n"
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
        name="🎉 __Giveaway__",
        value=(
            "`/giveaway` — Start a giveaway\n"
            "`/giveawayend` — End a giveaway manually\n"
        ),
        inline=False
    )

    embed.add_field(
        name="⭐ __Vouch__",
        value=(
            "`/vouch` — Leave a review\n"
            "`*vouchsetup` — *(Admin)* Configure vouch channel & role\n"
        ),
        inline=False
    )

    embed.add_field(
        name="📢 __Divers__",
        value=(
            "`*say` — Send a message as the bot\n"
            "`*wearelegit` — *(Admin)* Post the legit vote panel\n"
            "`*stats @user` — *(Manage)* Affiche les stats d'un membre\n"
            "`*setvouchrole <nb> @role` — *(Admin)* Rôle milestone vouchs\n"
            "`*vouchcount @user` — Voir le nb de vouchs d'un membre\n"
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


# ================= SET ROLE COMMANDS =================

def make_set_role_command(name, config_key, label):
    @bot.command(name=name)
    @commands.has_permissions(administrator=True)
    async def _cmd(ctx, role: discord.Role):
        ticket_config[config_key] = role.id
        await ctx.message.delete()
        embed = discord.Embed(
            title="✅ Rôle configuré",
            description=f"**{label}** → {role.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, delete_after=8)
    _cmd.__name__ = name
    return _cmd

# Langue
setfrench   = make_set_role_command("setfrench",     "role_french",     "🇫🇷 Rôle Français")
setenglish  = make_set_role_command("setenglish",    "role_english",    "🇬🇧 Rôle English")
# Types
setnitro    = make_set_role_command("setnitro",      "role_nitro",      "<:Nitro:1480046132707987611> Rôle Nitro")
setboost    = make_set_role_command("setboost",      "role_boost",      "<:Boost:1480046746146050149> Rôle Server Boost")
setdeco     = make_set_role_command("setdeco",       "role_decoration", "<:Discord:1480047123188944906> Rôle Decoration")
setexchange = make_set_role_command("setexchange",   "role_exchange",   "<:Exchange:1480047481491427492> Rôle Exchange")
setother    = make_set_role_command("setother",      "role_other",      "<:Other:1480047561615085638> Rôle Other")


# ================= VOUCH =================

vouch_config = {
    "channel": None,
    "role": None,
}
# Stocke le nombre de vouchs par user: { "staff_id": count }
VOUCH_FILE = "vouch_data.json"

def load_vouches() -> dict:
    if os.path.exists(VOUCH_FILE):
        try:
            with open(VOUCH_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_vouches(data: dict):
    with open(VOUCH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

vouch_counts: dict = load_vouches()
# Stocke les rôles milestone: { 1: role_id, 5: role_id, 10: role_id, ... }
vouch_milestone_roles: dict = {}

class SetVouchChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Select vouch channel", channel_types=[discord.ChannelType.text])
    async def callback(self, interaction: discord.Interaction):
        vouch_config["channel"] = self.values[0].id
        await interaction.response.send_message(f"✅ Vouch channel: {self.values[0].mention}", ephemeral=True)

class SetVouchRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Select vouch role (given after vouch)")
    async def callback(self, interaction: discord.Interaction):
        vouch_config["role"] = self.values[0].id
        await interaction.response.send_message(f"✅ Vouch role: {self.values[0].mention}", ephemeral=True)

class VouchSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SetVouchChannelSelect())
        self.add_item(SetVouchRoleSelect())

@bot.command(name="vouchsetup")
@commands.has_permissions(administrator=True)
async def vouchsetup(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="⚙️ Vouch Setup",
        description="Select the vouch channel and the role to give after a vouch.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=VouchSetupView())

@bot.command(name="vouch")
async def vouch(ctx, staff: discord.Member, rating: int, service: str, *, comment: str):
    """Usage: *vouch @staff <note 1-5> <service> <commentaire>"""
    await ctx.message.delete()

    if rating < 1 or rating > 5:
        return await ctx.send("❌ Rating must be between 1 and 5.", delete_after=8)

    stars = "⭐" * rating + "🌑" * (5 - rating)
    badges = {1: "😡 Very bad", 2: "😕 Bad", 3: "😐 Average", 4: "😊 Good", 5: "🤩 Excellent!"}

    # Incrément du compteur de vouchs du staff
    staff_id = str(staff.id)
    vouch_counts[staff_id] = vouch_counts.get(staff_id, 0) + 1
    staff_total = vouch_counts[staff_id]
    save_vouches(vouch_counts)

    embed = discord.Embed(title="📝 New Review — Slayzix Shop", color=discord.Color.from_rgb(255, 0, 0))
    embed.add_field(name="👤 Customer", value=ctx.author.mention, inline=True)
    embed.add_field(name="🛠️ Staff", value=staff.mention, inline=True)
    embed.add_field(name="📦 Service", value=f"**{service}**", inline=True)
    embed.add_field(name="⭐ Rating", value=f"{stars}  `{rating}/5` — {badges[rating]}", inline=False)
    embed.add_field(name="💬 Comment", value=f"*{comment}*", inline=False)
    embed.add_field(name="🏆 Staff Vouches", value=f"`{staff_total}` vouch(s) total", inline=False)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text="Slayzix Shop • Thank you for your review!")
    embed.timestamp = discord.utils.utcnow()

    # Attribution automatique du rôle "+X vouch" au staff
    new_role_name = f"+{staff_total} vouch"
    existing_role = discord.utils.get(ctx.guild.roles, name=new_role_name)
    if not existing_role:
        try:
            existing_role = await ctx.guild.create_role(
                name=new_role_name,
                color=discord.Color.from_rgb(255, 0, 0),
                reason=f"Vouch auto-role: {staff_total} vouches"
            )
            admin_roles = [
                r for r in ctx.guild.roles
                if r.permissions.administrator and r != ctx.guild.default_role
            ]
            if admin_roles:
                lowest_admin = min(admin_roles, key=lambda r: r.position)
                try:
                    await existing_role.edit(position=max(1, lowest_admin.position - 1))
                except Exception:
                    pass
        except discord.Forbidden:
            existing_role = None

    # Retire l'ancien rôle vouch du staff
    if staff_total > 1:
        old_role_name = f"+{staff_total - 1} vouch"
        old_role = discord.utils.get(ctx.guild.roles, name=old_role_name)
        if old_role and old_role in staff.roles:
            try:
                await staff.remove_roles(old_role, reason="Vouch role upgrade")
            except discord.Forbidden:
                pass

    # Donne le nouveau rôle
    if existing_role and existing_role not in staff.roles:
        try:
            await staff.add_roles(existing_role, reason=f"Vouch auto-role: {staff_total} vouches")
        except discord.Forbidden:
            pass

    # Rôle de base au customer
    if vouch_config["role"]:
        base_role = ctx.guild.get_role(vouch_config["role"])
        if base_role and base_role not in ctx.author.roles:
            try:
                await ctx.author.add_roles(base_role, reason="Vouch submitted")
            except discord.Forbidden:
                pass

    if vouch_config["channel"]:
        ch = ctx.guild.get_channel(vouch_config["channel"])
        if ch:
            await ch.send(embed=embed)
            return await ctx.send(
                f"✅ Review posted in {ch.mention}! 🙏 {staff.display_name} now has **{staff_total}** vouch(s)!",
                delete_after=8
            )
    await ctx.send(embed=embed)


@bot.command(name="setvouchrole")
@commands.has_permissions(administrator=True)
async def setvouchrole(ctx, milestone: int, role: discord.Role):
    """Configure un rôle milestone pour les vouchs. Ex: *setvouchrole 5 @role"""
    vouch_milestone_roles[milestone] = role.id
    await ctx.message.delete()
    await ctx.send(
        embed=discord.Embed(
            title="✅ Vouch Milestone configuré",
            description=f"À **{milestone}** vouch(s) → {role.mention}",
            color=discord.Color.from_rgb(255, 0, 0)
        ),
        delete_after=8
    )


@bot.command(name="vouchcount")
async def vouchcount(ctx, member: discord.Member = None):
    """Affiche le nombre de vouchs d'un membre."""
    target = member or ctx.author
    await ctx.message.delete()
    count = vouch_counts.get(str(target.id), 0)
    embed = discord.Embed(
        title="🏆 Vouch Count",
        description=f"{target.mention} has **{count}** vouch(s).",
        color=discord.Color.from_rgb(255, 0, 0)
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)


# ================= GIVEAWAY =================

active_giveaways = {}

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="🎉 Participate", style=discord.ButtonStyle.success, custom_id="giveaway_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.giveaway_id not in active_giveaways:
            return await interaction.response.send_message("❌ This giveaway has ended.", ephemeral=True)
        giveaway = active_giveaways[self.giveaway_id]
        if interaction.user.id in giveaway["participants"]:
            giveaway["participants"].discard(interaction.user.id)
            button.label = f"🎉 Participate — {len(giveaway['participants'])}"
            await interaction.message.edit(view=self)
            return await interaction.response.send_message("❌ You withdrew from the giveaway.", ephemeral=True)
        giveaway["participants"].add(interaction.user.id)
        button.label = f"🎉 Participate — {len(giveaway['participants'])}"
        await interaction.message.edit(view=self)
        await interaction.response.send_message("✅ You joined! Good luck 🍀", ephemeral=True)


async def end_giveaway(channel_id: int, message_id: int, guild: discord.Guild):
    import random
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
        embed = discord.Embed(title="🎉 GIVEAWAY ENDED", description=f"**Prize:** {prize}\n**Host:** <@{host}>\n\n😔 No participants!", color=discord.Color.red())
        embed.set_footer(text="Slayzix Shop • Giveaway ended")
        embed.timestamp = discord.utils.utcnow()
        await message.edit(embed=embed, view=None)
        await channel.send("😔 No participants, no winner!")
        del active_giveaways[message_id]
        return
    winners = random.sample(participants, min(giveaway["winners"], len(participants)))
    winners_mentions = " ".join([f"<@{w}>" for w in winners])
    embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED",
        description=f"**Prize:** {prize}\n**Winner(s):** {winners_mentions}\n**Host:** <@{host}>\n**Participants:** {len(participants)}",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Slayzix Shop • Giveaway ended")
    embed.timestamp = discord.utils.utcnow()
    await message.edit(embed=embed, view=None)
    await channel.send(f"🎊 Congratulations {winners_mentions}! You won **{prize}**!\nContact <@{host}> to claim your prize.")
    del active_giveaways[message_id]


@bot.tree.command(name="giveaway", description="🎉 Start a giveaway!")
@discord.app_commands.describe(duration="Duration (e.g. 10s, 5m, 1h, 2d)", winners="Number of winners", prize="What you are giving away")
@discord.app_commands.checks.has_permissions(manage_guild=True)
async def giveaway_cmd(interaction: discord.Interaction, duration: str, winners: int, prize: str):
    try:
        unit = duration[-1].lower()
        value = int(duration[:-1])
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        if unit not in multipliers:
            raise ValueError
        seconds = value * multipliers[unit]
    except Exception:
        return await interaction.response.send_message("❌ Invalid format. Ex: `30s`, `5m`, `1h`, `2d`", ephemeral=True)
    if winners < 1:
        return await interaction.response.send_message("❌ Minimum 1 winner.", ephemeral=True)
    end_timestamp = int((datetime.utcnow() + __import__("datetime").timedelta(seconds=seconds)).timestamp())
    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=f"**Prize:** {prize}\n**Winner(s):** {winners}\n**Host:** {interaction.user.mention}\n**Ends:** <t:{end_timestamp}:R> (<t:{end_timestamp}:f>)\n\nClick 🎉 to participate!",
        color=discord.Color.red()
    )
    embed.set_footer(text="Slayzix Shop • Giveaway")
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message("✅ Giveaway started!", ephemeral=True)
    msg = await interaction.channel.send(embed=embed)
    active_giveaways[msg.id] = {"prize": prize, "winners": winners, "host": interaction.user.id, "participants": set(), "channel_id": interaction.channel.id}
    await msg.edit(view=GiveawayView(msg.id))
    await asyncio.sleep(seconds)
    await end_giveaway(interaction.channel.id, msg.id, interaction.guild)


@bot.tree.command(name="giveawayend", description="⏹️ End a giveaway manually")
@discord.app_commands.describe(message_id="The giveaway message ID")
@discord.app_commands.checks.has_permissions(manage_guild=True)
async def giveawayend(interaction: discord.Interaction, message_id: str):
    msg_id = int(message_id)
    if msg_id not in active_giveaways:
        return await interaction.response.send_message("❌ Giveaway not found or already ended.", ephemeral=True)
    await interaction.response.send_message("✅ Giveaway ended manually!", ephemeral=True)
    await end_giveaway(interaction.channel.id, msg_id, interaction.guild)


# ================= SAY =================

class SayModal(discord.ui.Modal, title="📢 Send a message as the bot"):
    message_content = discord.ui.TextInput(
        label="Message",
        placeholder="Type your message here...",
        style=discord.TextStyle.long,
        max_length=2000,
        required=True
    )

    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        await self.target_channel.send(self.message_content.value)
        await interaction.response.send_message(f"✅ Message sent in {self.target_channel.mention}!", ephemeral=True)


class SayChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Select the target channel...", channel_types=[discord.ChannelType.text], row=0)

    async def callback(self, interaction: discord.Interaction):
        target = self.values[0]
        channel = interaction.guild.get_channel(target.id)
        await interaction.response.send_modal(SayModal(channel))


class SayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(SayChannelSelect())


@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx):
    """Ouvre un panel pour envoyer un message avec le bot."""
    await ctx.message.delete()
    embed = discord.Embed(
        title="📢 Send a message as the bot",
        description="Select the target channel, then type your message.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=SayView(), delete_after=120)


# ================= WE ARE LEGIT =================

class LegitView(discord.ui.View):
    def __init__(self, msg_id: int):
        super().__init__(timeout=None)
        self.msg_id = msg_id
        self.yes_count = 0
        self.no_count = 0
        self.voters = set()

        yes_btn = discord.ui.Button(label=str(self.yes_count), style=discord.ButtonStyle.secondary, emoji="<:oui:1480176155989508348>", custom_id=f"legit_yes_{msg_id}", row=0)
        no_btn  = discord.ui.Button(label=str(self.no_count),  style=discord.ButtonStyle.secondary, emoji="<:non:1480176175589621821>", custom_id=f"legit_no_{msg_id}",  row=0)

        yes_btn.callback = self.yes_callback
        no_btn.callback  = self.no_callback

        self.add_item(yes_btn)
        self.add_item(no_btn)

    async def yes_callback(self, interaction: discord.Interaction):
        if interaction.user.id in self.voters:
            return await interaction.response.send_message("❌ You already voted!", ephemeral=True)
        self.voters.add(interaction.user.id)
        self.yes_count += 1
        self.children[0].label = str(self.yes_count)
        await interaction.message.edit(view=self)
        await interaction.response.send_message("✅ You voted **Yes**!", ephemeral=True)

    async def no_callback(self, interaction: discord.Interaction):
        if interaction.user.id in self.voters:
            return await interaction.response.send_message("❌ You already voted!", ephemeral=True)
        self.voters.add(interaction.user.id)
        if interaction.guild.me.guild_permissions.ban_members:
            try:
                await interaction.response.send_message("🔨 You voted **No** — you have been banned.", ephemeral=True)
                await interaction.user.ban(reason="Voted No on Legit check")
                # Vote retiré du compteur car banni
                self.voters.discard(interaction.user.id)
            except Exception:
                self.no_count += 1
                self.children[1].label = str(self.no_count)
                await interaction.message.edit(view=self)
                await interaction.response.send_message("✅ You voted **No**!", ephemeral=True)
        else:
            self.no_count += 1
            self.children[1].label = str(self.no_count)
            await interaction.message.edit(view=self)
            await interaction.response.send_message("✅ You voted **No**!", ephemeral=True)


@bot.command(name="wearelegit")
@commands.has_permissions(administrator=True)
async def wearelegit(ctx):
    """Envoie le panel We Are Legit avec vote oui/non."""
    await ctx.message.delete()
    embed = discord.Embed(
        title="Slayzix Shop Legit?",
        description="<:oui:1480176155989508348> = Yes\n<:non:1480176175589621821> No = **Ban**",
        color=discord.Color.from_rgb(255, 0, 0)
    )
    embed.set_image(url="https://i.ibb.co/fdJxKj7c/BANNIERE.png")
    embed.set_footer(text="Slayzix Legit ?")
    msg = await ctx.send(embed=embed)
    pass  # No buttons, reactions added manually


# ================= STATS =================

@bot.command(name="stats")
@commands.has_permissions(manage_guild=True)
async def stats(ctx, member: discord.Member = None):
    """Affiche les stats d'un membre depuis son arrivée sur le serveur."""
    await ctx.message.delete()
    target = member or ctx.author

    # Dates
    joined_at = target.joined_at
    created_at = target.created_at
    now = discord.utils.utcnow()

    joined_days = (now - joined_at).days if joined_at else 0
    account_days = (now - created_at).days

    # Rôles (sans @everyone)
    roles = [r.mention for r in reversed(target.roles) if r.name != "@everyone"]
    roles_str = " ".join(roles) if roles else "Aucun rôle"

    # Vouch count du membre
    vouch_total = vouch_counts.get(str(target.id), 0)

    # Badges / statut
    status_map = {
        discord.Status.online: "🟢 Online",
        discord.Status.idle: "🟡 Idle",
        discord.Status.dnd: "🔴 Do Not Disturb",
        discord.Status.offline: "⚫ Offline",
    }
    status_str = status_map.get(target.status, "⚫ Offline")

    embed = discord.Embed(
        title=f"📊 Stats — {target.display_name}",
        color=discord.Color.from_rgb(255, 0, 0)
    )
    embed.set_thumbnail(url=target.display_avatar.url)

    embed.add_field(
        name="👤 Compte",
        value=(
            f"**Nom :** {target.name}\n"
            f"**ID :** `{target.id}`\n"
            f"**Statut :** {status_str}"
        ),
        inline=True
    )
    embed.add_field(
        name="📅 Dates",
        value=(
            f"**Compte créé :** <t:{int(created_at.timestamp())}:D>\n"
            f"**(`{account_days}` jours)** \n"
            f"**Rejoint le :** <t:{int(joined_at.timestamp())}:D>\n"
            f"**(`{joined_days}` jours sur le serv)**"
        ),
        inline=True
    )
    embed.add_field(
        name="🏆 Vouchs reçus",
        value=f"`{vouch_total}` vouch(s)",
        inline=True
    )
    embed.add_field(
        name=f"🎭 Rôles ({len(roles)})",
        value=roles_str[:1024] if roles_str else "Aucun",
        inline=False
    )

    # Invité par (bot Discord ne peut pas savoir qui a invité nativement sans audit log)
    try:
        async for entry in ctx.guild.audit_logs(action=discord.AuditLogAction.invite, limit=50):
            pass  # placeholder
    except Exception:
        pass

    embed.set_footer(text=f"Slayzix Shop • Stats de {target.name}")
    embed.timestamp = discord.utils.utcnow()

    await ctx.send(embed=embed)

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
    print("⭐ Vouch         : OK")
    print("🎉 Giveaway      : OK")
    print("📢 Say           : OK")
    print("🙏 WeAreLegit    : OK")
    print("📊 Stats         : OK")


# ================= START =================

if __name__ == "__main__":
    import os
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        raise ValueError("❌ TOKEN introuvable ! Ajoute la variable d'environnement DISCORD_TOKEN sur Railway.")
    bot.run(TOKEN)
