import discord
from discord.ext import commands
from discord import app_commands
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= PRIX =================

TIKTOK_PRICES = {
    "Followers": 2.0,
    "Likes": 0.50,
    "Views": 0.20
}

DISCORD_PRICES = {
    "Membres en ligne": 4.5,
    "Membres hors-ligne": 4.0,
    "Boost x14": 3.0,
    "Nitro 1 mois": 3.5
}

FORTNITE_PRICES = {
    "V-Bucks": 7.50,
}

ROBLOX_PRICES = {
    "Robux": 7.50,
}

APPS_PRICES = {
    "ChatGPT Plus": 13.0,
    "YouTube Premium": 8.0,
    "Spotify Premium": 13.0,
    "Prime Video": 10.50
}

FOURNISSEUR_PRICES = {
    "Réseaux Sociaux": 10.0,
    "Discord": 10.0,
    "Fortnite": 10.0,
    "Roblox": 10.0,
    "Valorant": 10.0,
    "Rocket League": 10.0,
    "Applications": 10.0,
    "Tous les fournisseurs": 50.0
}

ALLSHOP_PRICE = 75.0

# ================= CONFIG GLOBALE =================

welcome_channel_id = None
goodbye_channel_id = None
vouch_channel_id = None

# ================= UTILITAIRES =================

async def create_ticket(interaction: discord.Interaction, title: str, description: str):
    guild = interaction.guild
    user = interaction.user

    existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.id}")
    if existing:
        return await interaction.response.send_message(
            f"❌ Tu as déjà un ticket ouvert → {existing.mention}",
            ephemeral=True
        )

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    # Donner accès aux admins
    for role in guild.roles:
        if role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    category = discord.utils.get(guild.categories, name="TICKETS")
    if not category:
        category = await guild.create_category("TICKETS")

    channel = await guild.create_text_channel(
        name=f"ticket-{user.id}",
        overwrites=overwrites,
        category=category
    )

    embed = discord.Embed(title=title, description=description, color=0x5865F2)
    embed.set_footer(text="Slayzix Shop • Ticket")
    embed.timestamp = discord.utils.utcnow()

    await channel.send(user.mention, embed=embed, view=CloseTicketView())
    await interaction.response.send_message(
        f"✅ Ticket créé ! → {channel.mention}", ephemeral=True
    )


# ================= FERMETURE TICKET =================

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fermeture dans 5 secondes...")
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()


# ================= MODALS =================

class QuantityModal(discord.ui.Modal):
    def __init__(self, service: str, platform: str):
        super().__init__(title=f"Commande — {service}")
        self.service = service
        self.platform = platform

        label = "Quantité" if service in ["Boost x14", "Nitro 1 mois"] else "Quantité (multiple de 1000)"
        self.quantity = discord.ui.TextInput(label=label, required=True, placeholder="Ex: 1000")
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.quantity.value)
        except ValueError:
            return await interaction.response.send_message("❌ Entre un nombre entier valide.", ephemeral=True)

        if self.platform == "tiktok":
            if value < 1000 or value % 1000 != 0:
                return await interaction.response.send_message("❌ Minimum 1000 et multiple de 1000.", ephemeral=True)
            price = (value / 1000) * TIKTOK_PRICES[self.service]

        elif self.platform == "discord":
            if self.service in ["Membres en ligne", "Membres hors-ligne"]:
                if value < 1000 or value % 1000 != 0:
                    return await interaction.response.send_message("❌ Minimum 1000 et multiple de 1000.", ephemeral=True)
                price = (value / 1000) * DISCORD_PRICES[self.service]
            elif self.service in ["Boost x14", "Nitro 1 mois"]:
                if value < 1:
                    return await interaction.response.send_message("❌ Quantité invalide.", ephemeral=True)
                price = value * DISCORD_PRICES[self.service]
            else:
                return await interaction.response.send_message("❌ Service inconnu.", ephemeral=True)
        else:
            return

        await create_ticket(
            interaction, "🎫 Facture",
            f"📦 **Service :** {self.service}\n"
            f"🔢 **Quantité :** {value:,}\n"
            f"💰 **Prix :** {price:.2f}€\n\n"
            f"💳 Paiement PayPal\n"
            f"⚡ Livraison rapide\n"
            f"💬 Merci de patienter, un vendeur arrive !"
        )


class FortniteModal(discord.ui.Modal):
    def __init__(self, service: str):
        super().__init__(title=f"Commande Fortnite — {service}")
        self.service = service

        if service == "V-Bucks":
            self.field = discord.ui.TextInput(label="Quantité de V-Bucks (multiple de 1000)", required=True, placeholder="Ex: 1000")
        else:
            self.field = discord.ui.TextInput(label="Décris ta demande", style=discord.TextStyle.paragraph, required=True, placeholder="Ex: skin souhaité, budget, compte recherché...")
        self.add_item(self.field)

    async def on_submit(self, interaction: discord.Interaction):
        if self.service == "V-Bucks":
            try:
                value = int(self.field.value)
                if value < 1000 or value % 1000 != 0:
                    return await interaction.response.send_message("❌ Minimum 1000 et multiple de 1000.", ephemeral=True)
                price = (value / 1000) * FORTNITE_PRICES["V-Bucks"]
                desc = f"📦 **Service :** V-Bucks\n🔢 **Quantité :** {value:,}\n💰 **Prix :** {price:.2f}€\n\n💳 Paiement PayPal\n⚡ Livraison rapide\n💬 Merci de patienter !"
            except ValueError:
                return await interaction.response.send_message("❌ Valeur invalide.", ephemeral=True)
        else:
            desc = f"📦 **Service :** {self.service}\n📝 **Détails :** {self.field.value}\n\n💳 Paiement PayPal\n💬 Un vendeur reviendra vers toi rapidement."

        await create_ticket(interaction, "🎫 Ticket Fortnite", desc)


class RobloxModal(discord.ui.Modal):
    def __init__(self, service: str):
        super().__init__(title=f"Commande Roblox — {service}")
        self.service = service

        if service == "Robux":
            self.field = discord.ui.TextInput(label="Quantité de Robux (multiple de 1000)", required=True, placeholder="Ex: 1000")
        else:
            self.field = discord.ui.TextInput(label="Décris ta demande", style=discord.TextStyle.paragraph, required=True, placeholder="Ex: nom du jeu, type de game pass, budget...")
        self.add_item(self.field)

    async def on_submit(self, interaction: discord.Interaction):
        if self.service == "Robux":
            try:
                value = int(self.field.value)
                if value < 1000 or value % 1000 != 0:
                    return await interaction.response.send_message("❌ Minimum 1000 et multiple de 1000.", ephemeral=True)
                price = (value / 1000) * ROBLOX_PRICES["Robux"]
                desc = f"📦 **Service :** Robux\n🔢 **Quantité :** {value:,}\n💰 **Prix :** {price:.2f}€\n\n💳 Paiement PayPal\n⚡ Livraison rapide\n💬 Merci de patienter !"
            except ValueError:
                return await interaction.response.send_message("❌ Valeur invalide.", ephemeral=True)
        else:
            desc = f"📦 **Service :** {self.service}\n📝 **Détails :** {self.field.value}\n\n💳 Paiement PayPal\n💬 Un vendeur reviendra vers toi rapidement."

        await create_ticket(interaction, "🎫 Ticket Roblox", desc)


class ValorantModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Commande Valorant — Riot Points")
        self.details = discord.ui.TextInput(label="Décris ta demande", style=discord.TextStyle.paragraph, required=True, placeholder="Ex: quantité de RP souhaitée, budget...")
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(interaction, "🎫 Ticket Valorant",
            f"📦 **Service :** Riot Points\n📝 **Détails :** {self.details.value}\n\n💳 Paiement PayPal\n💬 Un vendeur reviendra vers toi rapidement.")


class RocketLeagueModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Commande Rocket League")
        self.details = discord.ui.TextInput(label="Décris ta demande", style=discord.TextStyle.paragraph, required=True, placeholder="Ex: rang du compte, skins, inventaire...")
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(interaction, "🎫 Ticket Rocket League",
            f"📦 **Service :** Comptes Rocket League\n📝 **Détails :** {self.details.value}\n\n💳 Paiement PayPal\n💬 Un vendeur reviendra vers toi rapidement.")


class AppsModal(discord.ui.Modal):
    def __init__(self, service: str):
        super().__init__(title=f"Commande — {service}")
        self.service = service
        self.quantity = discord.ui.TextInput(label="Quantité", required=True, placeholder="Ex: 1")
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.quantity.value)
            if value < 1:
                return await interaction.response.send_message("❌ Quantité invalide.", ephemeral=True)
            price = value * APPS_PRICES[self.service]
        except ValueError:
            return await interaction.response.send_message("❌ Valeur invalide.", ephemeral=True)

        await create_ticket(interaction, "🎫 Ticket Applications",
            f"📦 **Service :** {self.service} (Lifetime)\n"
            f"🔢 **Quantité :** {value}\n"
            f"💰 **Prix :** {price:.2f}€\n\n"
            f"💳 Paiement PayPal\n⚡ Livraison rapide\n💬 Merci de patienter !")


# ================= SELECTS DU PANEL =================

class TikTokSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="🎵 Choisis ton service TikTok...",
            custom_id="panel_tiktok_select",
            options=[
                discord.SelectOption(label="Followers", emoji="🚀", description="1000 Followers = 2.00€"),
                discord.SelectOption(label="Likes", emoji="❤️", description="1000 Likes = 0.50€"),
                discord.SelectOption(label="Views", emoji="👀", description="1000 Views = 0.20€"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(QuantityModal(self.values[0], "tiktok"))


class DiscordServiceSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="💬 Choisis ton service Discord...",
            custom_id="panel_discord_select",
            options=[
                discord.SelectOption(label="Membres en ligne", emoji="👥", description="1000 membres = 4.50€"),
                discord.SelectOption(label="Membres hors-ligne", emoji="👤", description="1000 membres = 4.00€"),
                discord.SelectOption(label="Boost x14", emoji="🚀", description="1 boost = 3.00€"),
                discord.SelectOption(label="Nitro 1 mois", emoji="🎁", description="1 Nitro = 3.50€"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(QuantityModal(self.values[0], "discord"))


class FortniteSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="🎮 Choisis ton service Fortnite...",
            custom_id="panel_fortnite_select",
            options=[
                discord.SelectOption(label="V-Bucks", emoji="💎", description="1000 V-Bucks = 7.50€"),
                discord.SelectOption(label="Packs de skins / bundles", emoji="🎁", description="Prix en ticket"),
                discord.SelectOption(label="Comptes Fortnite", emoji="🕹️", description="Prix en ticket"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FortniteModal(self.values[0]))


class RobloxSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="🧱 Choisis ton service Roblox...",
            custom_id="panel_roblox_select",
            options=[
                discord.SelectOption(label="Robux", emoji="💰", description="1000 Robux = 7.50€"),
                discord.SelectOption(label="Game Pass", emoji="🎮", description="Prix en ticket"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RobloxModal(self.values[0]))


class ValorantSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="💠 Choisis ton service Valorant...",
            custom_id="panel_valorant_select",
            options=[
                discord.SelectOption(label="Riot Points", emoji="💠", description="Prix en ticket"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ValorantModal())


class RocketLeagueSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="🚗 Choisis ton service Rocket League...",
            custom_id="panel_rl_select",
            options=[
                discord.SelectOption(label="Comptes Rocket League", emoji="🏆", description="Rang / skins / inventaire"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RocketLeagueModal())


class AppsSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="📲 Choisis ton application...",
            custom_id="panel_apps_select",
            options=[
                discord.SelectOption(label="ChatGPT Plus", emoji="🤖", description="Lifetime — 13€"),
                discord.SelectOption(label="YouTube Premium", emoji="▶️", description="Lifetime — 8€"),
                discord.SelectOption(label="Spotify Premium", emoji="🎵", description="Lifetime — 13€"),
                discord.SelectOption(label="Prime Video", emoji="📺", description="Lifetime — 10.50€"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AppsModal(self.values[0]))


class FournisseurSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(
            placeholder="🔑 Choisis ton accès fournisseur...",
            custom_id="panel_fourni_select",
            options=[
                discord.SelectOption(label="Réseaux Sociaux", emoji="📱", description="10€"),
                discord.SelectOption(label="Discord", emoji="💬", description="10€"),
                discord.SelectOption(label="Fortnite", emoji="🎮", description="10€"),
                discord.SelectOption(label="Roblox", emoji="🧱", description="10€"),
                discord.SelectOption(label="Valorant", emoji="💠", description="10€"),
                discord.SelectOption(label="Rocket League", emoji="🚗", description="10€"),
                discord.SelectOption(label="Applications", emoji="📲", description="10€"),
                discord.SelectOption(label="Tous les fournisseurs", emoji="🌟", description="Accès complet — 50€"),
            ]
        )

    async def callback(self, interaction: discord.Interaction):
        service = self.values[0]
        price = FOURNISSEUR_PRICES[service]
        await create_ticket(interaction, "🎫 Ticket Fournisseur",
            f"📦 **Service :** Accès Fournisseur — {service}\n"
            f"💰 **Prix :** {price:.2f}€\n\n"
            f"💳 Paiement PayPal\n"
            f"💬 Un vendeur reviendra vers toi rapidement.")


# ================= VIEWS DU PANEL =================

class PanelMainView(discord.ui.View):
    """Panel principal — boutons de navigation par catégorie"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎵 TikTok", style=discord.ButtonStyle.primary, custom_id="panel_btn_tiktok", row=0)
    async def btn_tiktok(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = _category_embed(
            "🎵 TikTok Boost",
            "Choisis le service que tu veux booster :",
            [("🚀 Followers", "1 000 = **2.00€**"), ("❤️ Likes", "1 000 = **0.50€**"), ("👀 Views", "1 000 = **0.20€**")],
            0xFF0050
        )
        await interaction.response.send_message(embed=embed, view=CategoryView(TikTokSelect()), ephemeral=True)

    @discord.ui.button(label="💬 Discord", style=discord.ButtonStyle.primary, custom_id="panel_btn_discord", row=0)
    async def btn_discord(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = _category_embed(
            "💬 Discord Services",
            "Choisis le service Discord :",
            [("👥 Membres en ligne", "1 000 = **4.50€**"), ("👤 Membres hors-ligne", "1 000 = **4.00€**"), ("🚀 Boost x14", "1 boost = **3.00€**"), ("🎁 Nitro 1 mois", "1 Nitro = **3.50€**")],
            0x5865F2
        )
        await interaction.response.send_message(embed=embed, view=CategoryView(DiscordServiceSelect()), ephemeral=True)

    @discord.ui.button(label="🎮 Fortnite", style=discord.ButtonStyle.primary, custom_id="panel_btn_fortnite", row=0)
    async def btn_fortnite(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = _category_embed(
            "🎮 Fortnite Services",
            "Choisis le service Fortnite :",
            [("💎 V-Bucks", "1 000 = **7.50€**"), ("🎁 Packs de skins / bundles", "Prix en ticket"), ("🕹️ Comptes Fortnite", "Prix en ticket")],
            0x00C3FF
        )
        await interaction.response.send_message(embed=embed, view=CategoryView(FortniteSelect()), ephemeral=True)

    @discord.ui.button(label="🧱 Roblox", style=discord.ButtonStyle.primary, custom_id="panel_btn_roblox", row=1)
    async def btn_roblox(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = _category_embed(
            "🧱 Roblox Services",
            "Choisis le service Roblox :",
            [("💰 Robux", "1 000 = **7.50€**"), ("🎮 Game Pass", "Prix en ticket")],
            0xE52207
        )
        await interaction.response.send_message(embed=embed, view=CategoryView(RobloxSelect()), ephemeral=True)

    @discord.ui.button(label="💠 Valorant", style=discord.ButtonStyle.primary, custom_id="panel_btn_valorant", row=1)
    async def btn_valorant(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = _category_embed(
            "💠 Valorant Services",
            "Choisis le service Valorant :",
            [("💠 Riot Points", "Prix en ticket")],
            0xFF4655
        )
        await interaction.response.send_message(embed=embed, view=CategoryView(ValorantSelect()), ephemeral=True)

    @discord.ui.button(label="🚗 Rocket League", style=discord.ButtonStyle.primary, custom_id="panel_btn_rl", row=1)
    async def btn_rl(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = _category_embed(
            "🚗 Rocket League Services",
            "Choisis le service Rocket League :",
            [("🏆 Comptes RL", "Rang / skins / inventaire")],
            0x0077FF
        )
        await interaction.response.send_message(embed=embed, view=CategoryView(RocketLeagueSelect()), ephemeral=True)

    @discord.ui.button(label="📲 Applications", style=discord.ButtonStyle.success, custom_id="panel_btn_apps", row=2)
    async def btn_apps(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = _category_embed(
            "📲 Applications (Lifetime)",
            "Choisis ton application :",
            [("🤖 ChatGPT Plus", "**13.00€**"), ("▶️ YouTube Premium", "**8.00€**"), ("🎵 Spotify Premium", "**13.00€**"), ("📺 Prime Video", "**10.50€**")],
            0x1DB954
        )
        await interaction.response.send_message(embed=embed, view=CategoryView(AppsSelect()), ephemeral=True)

    @discord.ui.button(label="🔑 Accès Fournisseur", style=discord.ButtonStyle.success, custom_id="panel_btn_fourni", row=2)
    async def btn_fourni(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = _category_embed(
            "🔑 Accès Fournisseur",
            "Accède aux fournisseurs pour revendre :",
            [("📱 Réseaux Sociaux", "**10€**"), ("💬 Discord", "**10€**"), ("🎮 Fortnite", "**10€**"),
             ("🧱 Roblox", "**10€**"), ("💠 Valorant", "**10€**"), ("🚗 Rocket League", "**10€**"),
             ("📲 Applications", "**10€**"), ("🌟 Tous les fournisseurs", "**50€**")],
            0xF1C40F
        )
        await interaction.response.send_message(embed=embed, view=CategoryView(FournisseurSelect()), ephemeral=True)

    @discord.ui.button(label="🏆 Pack Shop Complet — 75€", style=discord.ButtonStyle.danger, custom_id="panel_btn_allshop", row=3)
    async def btn_allshop(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🏆 Pack Shop Complet — Offre Premium",
            description=(
                "Tout ce qu'il faut pour lancer ton business immédiatement.\n\n"
                "✅ Accès Fournisseurs inclus\n"
                "✅ Serveur Discord prêt à vendre\n"
                "✅ Gestion complète (Management)\n"
                "✅ Organisation & mise en place\n"
                "✅ Conseils & optimisation\n\n"
                f"💰 **Prix total : {ALLSHOP_PRICE:.2f}€**\n"
                "💳 Paiement PayPal\n"
                "🔒 Paiement sécurisé"
            ),
            color=0xFFD700
        )
        embed.set_footer(text="Slayzix Shop • Offre Premium")
        await interaction.response.send_message(embed=embed, view=AllShopConfirmView(), ephemeral=True)


class AllShopConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="🛒 Commander maintenant", style=discord.ButtonStyle.success, custom_id="allshop_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "🎫 Ticket Pack Shop Complet",
            f"📦 **Service :** Pack Shop Complet — Offre Premium\n"
            f"💰 **Prix :** {ALLSHOP_PRICE:.2f}€\n\n"
            f"✅ Accès Fournisseurs inclus\n"
            f"✅ Serveur Discord prêt à vendre\n"
            f"✅ Gestion complète (Management)\n"
            f"✅ Organisation & mise en place\n"
            f"✅ Conseils & optimisation\n\n"
            f"💳 Paiement PayPal\n"
            f"💬 Un vendeur reviendra vers toi rapidement.")


class CategoryView(discord.ui.View):
    """View avec un select menu pour une catégorie"""
    def __init__(self, select: discord.ui.Select):
        super().__init__(timeout=120)
        self.add_item(select)


# ================= HELPER EMBED CATÉGORIE =================

def _category_embed(title: str, desc: str, items: list, color: int) -> discord.Embed:
    embed = discord.Embed(title=f"💎 SLAYZIX SHOP — {title}", description=desc, color=color)
    for name, value in items:
        embed.add_field(name=name, value=value, inline=True)
    embed.add_field(name="\u200b", value="💳 Paiement PayPal • 🔒 Sécurisé • ⚡ Rapide", inline=False)
    embed.set_footer(text="Slayzix Shop • Sélectionne ton service ci-dessous")
    return embed


# ================= COMMANDE /panel =================

@bot.tree.command(name="panel", description="Affiche le panel de commande Slayzix Shop")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Panel de Commande",
        description=(
            "Bienvenue sur **Slayzix Shop** !\n"
            "Clique sur la catégorie de ton choix pour passer ta commande.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎵 **TikTok** • 💬 **Discord** • 🎮 **Fortnite**\n"
            "🧱 **Roblox** • 💠 **Valorant** • 🚗 **Rocket League**\n"
            "📲 **Applications** • 🔑 **Accès Fournisseur**\n"
            "🏆 **Pack Shop Complet**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💳 Paiement **PayPal** uniquement\n"
            "🔒 Transactions **100% sécurisées**\n"
            "⚡ Livraison **rapide & garantie**\n"
            "💬 Support **actif 24/7**"
        ),
        color=0x5865F2
    )
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text="Slayzix Shop • Votre satisfaction est notre priorité")
    embed.timestamp = discord.utils.utcnow()

    await interaction.response.send_message(embed=embed, view=PanelMainView(), ephemeral=True)


# ================= COMMANDE /deploy =================

@bot.tree.command(name="deploy", description="[ADMIN] Déploie le panel dans ce salon de façon permanente")
@app_commands.default_permissions(administrator=True)
async def deploy(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Panel de Commande",
        description=(
            "Bienvenue sur **Slayzix Shop** !\n"
            "Clique sur la catégorie de ton choix pour passer ta commande.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎵 **TikTok** • 💬 **Discord** • 🎮 **Fortnite**\n"
            "🧱 **Roblox** • 💠 **Valorant** • 🚗 **Rocket League**\n"
            "📲 **Applications** • 🔑 **Accès Fournisseur**\n"
            "🏆 **Pack Shop Complet**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "💳 Paiement **PayPal** uniquement\n"
            "🔒 Transactions **100% sécurisées**\n"
            "⚡ Livraison **rapide & garantie**\n"
            "💬 Support **actif 24/7**"
        ),
        color=0x5865F2
    )
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text="Slayzix Shop • Votre satisfaction est notre priorité")
    embed.timestamp = discord.utils.utcnow()

    await interaction.channel.send(embed=embed, view=PanelMainView())
    await interaction.response.send_message("✅ Panel déployé dans ce salon !", ephemeral=True)


# ================= VOUCH =================

@bot.tree.command(name="vouch", description="Laisse un avis sur le shop !")
@app_commands.describe(note="Ta note sur 5", service="Le service acheté", commentaire="Ton commentaire")
@app_commands.choices(note=[
    app_commands.Choice(name="⭐ 1/5", value=1),
    app_commands.Choice(name="⭐⭐ 2/5", value=2),
    app_commands.Choice(name="⭐⭐⭐ 3/5", value=3),
    app_commands.Choice(name="⭐⭐⭐⭐ 4/5", value=4),
    app_commands.Choice(name="⭐⭐⭐⭐⭐ 5/5", value=5),
])
async def vouch(interaction: discord.Interaction, note: int, service: str, commentaire: str):
    stars = "⭐" * note + "🌑" * (5 - note)
    colors = {1: 0xED4245, 2: 0xE67E22, 3: 0xFEE75C, 4: 0x57F287, 5: 0xFFD700}
    badges = {1: "😡 Très mauvais", 2: "😕 Mauvais", 3: "😐 Correct", 4: "😊 Bien", 5: "🤩 Excellent !"}

    embed = discord.Embed(title="📝 Nouvel Avis — Slayzix Shop", color=colors[note])
    embed.add_field(name="👤 Client", value=interaction.user.mention, inline=True)
    embed.add_field(name="📦 Service", value=f"**{service}**", inline=True)
    embed.add_field(name="⭐ Note", value=f"{stars}  `{note}/5` — {badges[note]}", inline=False)
    embed.add_field(name="💬 Commentaire", value=f"*{commentaire}*", inline=False)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Slayzix Shop • Merci pour ton avis !")
    embed.timestamp = discord.utils.utcnow()

    if vouch_channel_id:
        channel = interaction.guild.get_channel(vouch_channel_id)
        if channel:
            await channel.send(embed=embed)
            return await interaction.response.send_message(f"✅ Avis posté dans {channel.mention}, merci ! 🙏", ephemeral=True)

    await interaction.response.send_message(embed=embed)


# ================= WELCOME / GOODBYE =================

class WelcomeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon de bienvenue", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        global welcome_channel_id
        welcome_channel_id = self.values[0].id
        await interaction.response.send_message(f"✅ Salon de bienvenue → {self.values[0].mention}", ephemeral=True)


class GoodbyeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon d'au revoir", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        global goodbye_channel_id
        goodbye_channel_id = self.values[0].id
        await interaction.response.send_message(f"✅ Salon d'au revoir → {self.values[0].mention}", ephemeral=True)


class VouchChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon des avis", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        global vouch_channel_id
        vouch_channel_id = self.values[0].id
        await interaction.response.send_message(f"✅ Salon des avis → {self.values[0].mention}", ephemeral=True)


class SetupView(discord.ui.View):
    def __init__(self, select):
        super().__init__(timeout=None)
        self.add_item(select)


@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    embed = discord.Embed(title="⚙️ Configuration — Bienvenue", description="Sélectionne le salon de bienvenue.", color=0x5865F2)
    await ctx.send(embed=embed, view=SetupView(WelcomeChannelSelect()))

@bot.command()
@commands.has_permissions(administrator=True)
async def goodbye(ctx):
    embed = discord.Embed(title="⚙️ Configuration — Au revoir", description="Sélectionne le salon d'au revoir.", color=0x5865F2)
    await ctx.send(embed=embed, view=SetupView(GoodbyeChannelSelect()))

@bot.command()
@commands.has_permissions(administrator=True)
async def setvouchchannel(ctx):
    embed = discord.Embed(title="⚙️ Configuration — Avis", description="Sélectionne le salon des avis.", color=0x5865F2)
    await ctx.send(embed=embed, view=SetupView(VouchChannelSelect()))


@bot.event
async def on_member_join(member):
    if not welcome_channel_id:
        return
    channel = member.guild.get_channel(welcome_channel_id)
    if not channel:
        return
    embed = discord.Embed(
        title="🎉 Bienvenue sur le serveur !",
        description=(
            f"Salut {member.mention}, on est ravis de t'accueillir sur **{member.guild.name}** ! 🙌\n\n"
            f"Tu es le **{member.guild.member_count}ème** membre à nous rejoindre.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛒 Consulte nos services avec `/panel` !\n"
            f"💬 Notre équipe est là pour t'aider.\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0xFFD700
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Slayzix Shop • Bienvenue parmi nous !")
    embed.timestamp = discord.utils.utcnow()
    await channel.send(embed=embed)


@bot.event
async def on_member_remove(member):
    if not goodbye_channel_id:
        return
    channel = member.guild.get_channel(goodbye_channel_id)
    if not channel:
        return
    embed = discord.Embed(
        title="👋 Départ du serveur",
        description=(
            f"**{member.name}** vient de quitter **{member.guild.name}**...\n\n"
            f"Il reste désormais **{member.guild.member_count} membres**.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"😔 On espère te revoir bientôt !\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0xED4245
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Slayzix Shop • À bientôt !")
    embed.timestamp = discord.utils.utcnow()
    await channel.send(embed=embed)


# ================= ON READY =================

@bot.event
async def on_ready():
    # Ré-enregistrer les views persistantes pour que les boutons restent actifs après redémarrage
    bot.add_view(PanelMainView())
    bot.add_view(CloseTicketView())

    await bot.tree.sync()
    print(f"✅ {bot.user} connecté !")
    print(f"📋 Slash commands synchronisées")
    print(f"🛒 Panel Slayzix Shop prêt !")


# ================= LANCEMENT =================

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        raise ValueError("❌ TOKEN manquant dans les variables d'environnement !")
    bot.run(TOKEN)
