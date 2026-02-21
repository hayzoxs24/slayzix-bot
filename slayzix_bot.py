import discord
from discord.ext import commands
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
    "Membres hors-ligne": 4,
    "Boost x14": 3,
    "Nitro 1 mois": 3.5
}

FORTNITE_PRICES = {
    "V-Bucks": 7.50,
    "Packs de skins / bundles": None,
    "Comptes Fortnite": None
}

ROBLOX_PRICES = {
    "Robux": 7.50,
    "Game Pass": None
}

VALORANT_PRICES = {
    "Riot Points": None
}

ROCKETLEAGUE_PRICES = {
    "Comptes Rocket League": None
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

# ================= BOUTON FERMETURE =================

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# ================= TICKET =================

async def create_ticket(interaction, title, description):
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
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    category = discord.utils.get(guild.categories, name="TICKETS")
    if not category:
        category = await guild.create_category("TICKETS")

    channel = await guild.create_text_channel(
        name=f"ticket-{user.id}",
        overwrites=overwrites,
        category=category
    )

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Slayzix Shop")

    await channel.send(user.mention, embed=embed, view=CloseTicketView())
    await interaction.response.send_message(
        f"✅ Ticket créé ! → {channel.mention}",
        ephemeral=True
    )

# ================= MODAL =================

class QuantityModal(discord.ui.Modal):

    def __init__(self, service, platform):
        super().__init__(title="Commande")
        self.service = service
        self.platform = platform

        if self.service in ["Boost x14", "Nitro 1 mois"]:
            label = "Quantité"
        else:
            label = "Quantité (multiple de 1000)"

        self.quantity = discord.ui.TextInput(
            label=label,
            required=True
        )
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.quantity.value)

            # ===== TIKTOK =====
            if self.platform == "tiktok":
                if value < 1000 or value % 1000 != 0:
                    return await interaction.response.send_message(
                        "❌ Minimum 1000 et multiple de 1000.",
                        ephemeral=True
                    )
                price = (value / 1000) * TIKTOK_PRICES[self.service]

            # ===== DISCORD =====
            else:
                # 👥 Membres (multiple de 1000 obligatoire)
                if "Membres" in self.service:
                    if value < 1000 or value % 1000 != 0:
                        return await interaction.response.send_message(
                            "❌ Minimum 1000 et multiple de 1000.",
                            ephemeral=True
                        )
                    price = (value / 1000) * DISCORD_PRICES[self.service]

                # 🚀 Boost x14 & 🎁 Nitro (quantité libre)
                elif self.service in ["Boost x14", "Nitro 1 mois"]:
                    if value < 1:
                        return await interaction.response.send_message(
                            "❌ Quantité invalide.",
                            ephemeral=True
                        )
                    price = value * DISCORD_PRICES[self.service]

                else:
                    return await interaction.response.send_message(
                        "❌ Service inconnu.",
                        ephemeral=True
                    )

        except ValueError:
            return await interaction.response.send_message(
                "❌ Valeur invalide. Entre un nombre entier.",
                ephemeral=True
            )

        await create_ticket(
            interaction,
            "🎫 Facture",
            f"📦 Service : **{self.service}**\n"
            f"🔢 Quantité : **{value}**\n"
            f"💰 Prix : **{price:.2f}€**\n\n"
            f"💳 Paiement PayPal\n"
            f"⚡ Livraison rapide\n"
            f"💬 Merci de patienter"
        )


class FortniteModal(discord.ui.Modal):

    def __init__(self, service):
        super().__init__(title="Commande Fortnite")
        self.service = service

        if service == "V-Bucks":
            self.quantity = discord.ui.TextInput(
                label="Quantité de V-Bucks (multiple de 1000)",
                required=True
            )
            self.add_item(self.quantity)
        else:
            self.details = discord.ui.TextInput(
                label="Décris ta demande",
                style=discord.TextStyle.paragraph,
                required=True,
                placeholder="Ex: skin souhaité, budget, compte recherché..."
            )
            self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        if self.service == "V-Bucks":
            try:
                value = int(self.quantity.value)
                if value < 1000 or value % 1000 != 0:
                    return await interaction.response.send_message(
                        "❌ Minimum 1000 et multiple de 1000.",
                        ephemeral=True
                    )
                price = (value / 1000) * FORTNITE_PRICES["V-Bucks"]
                description = (
                    f"📦 Service : **V-Bucks**\n"
                    f"🔢 Quantité : **{value}**\n"
                    f"💰 Prix : **{price:.2f}€**\n\n"
                    f"💳 Paiement PayPal\n"
                    f"⚡ Livraison rapide\n"
                    f"💬 Merci de patienter"
                )
            except ValueError:
                return await interaction.response.send_message(
                    "❌ Valeur invalide. Entre un nombre entier.",
                    ephemeral=True
                )
        else:
            description = (
                f"📦 Service : **{self.service}**\n"
                f"📝 Détails : **{self.details.value}**\n\n"
                f"💳 Paiement PayPal\n"
                f"💬 Un vendeur reviendra vers toi rapidement"
            )

        await create_ticket(
            interaction,
            "🎫 Ticket Fortnite",
            description
        )

# ================= SELECT =================

class ServiceSelect(discord.ui.Select):

    def __init__(self, platform):

        if platform == "tiktok":
            options = [
                discord.SelectOption(label="Followers", emoji="🚀"),
                discord.SelectOption(label="Likes", emoji="❤️"),
                discord.SelectOption(label="Views", emoji="👀"),
            ]
        else:
            options = [
                discord.SelectOption(label="Membres en ligne", emoji="👥"),
                discord.SelectOption(label="Membres hors-ligne", emoji="👤"),
                discord.SelectOption(label="Boost x14", emoji="🚀"),
                discord.SelectOption(label="Nitro 1 mois", emoji="🎁"),
            ]

        super().__init__(
            placeholder="Choisis ton service",
            options=options
        )

        self.platform = platform

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            QuantityModal(self.values[0], self.platform)
        )

class ServiceView(discord.ui.View):
    def __init__(self, platform):
        super().__init__(timeout=None)
        self.add_item(ServiceSelect(platform))


class FortniteSelect(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="V-Bucks", emoji="💎", description="1000 V-Bucks = 7.50€"),
            discord.SelectOption(label="Packs de skins / bundles", emoji="🎁", description="Prix en ticket"),
            discord.SelectOption(label="Comptes Fortnite", emoji="🎮", description="Prix en ticket"),
        ]
        super().__init__(placeholder="Choisis ton service", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FortniteModal(self.values[0]))

class FortniteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(FortniteSelect())


class RobloxModal(discord.ui.Modal):

    def __init__(self, service):
        super().__init__(title="Commande Roblox")
        self.service = service

        if service == "Robux":
            self.quantity = discord.ui.TextInput(
                label="Quantité de Robux (multiple de 1000)",
                required=True
            )
            self.add_item(self.quantity)
        else:
            self.details = discord.ui.TextInput(
                label="Décris ta demande",
                style=discord.TextStyle.paragraph,
                required=True,
                placeholder="Ex: nom du jeu, type de game pass, budget..."
            )
            self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        if self.service == "Robux":
            try:
                value = int(self.quantity.value)
                if value < 1000 or value % 1000 != 0:
                    return await interaction.response.send_message(
                        "❌ Minimum 1000 et multiple de 1000.",
                        ephemeral=True
                    )
                price = (value / 1000) * ROBLOX_PRICES["Robux"]
                description = (
                    f"📦 Service : **Robux**\n"
                    f"🔢 Quantité : **{value}**\n"
                    f"💰 Prix : **{price:.2f}€**\n\n"
                    f"💳 Paiement PayPal\n"
                    f"⚡ Livraison rapide\n"
                    f"💬 Merci de patienter"
                )
            except ValueError:
                return await interaction.response.send_message(
                    "❌ Valeur invalide. Entre un nombre entier.",
                    ephemeral=True
                )
        else:
            description = (
                f"📦 Service : **{self.service}**\n"
                f"📝 Détails : **{self.details.value}**\n\n"
                f"💳 Paiement PayPal\n"
                f"💬 Un vendeur reviendra vers toi rapidement"
            )

        await create_ticket(
            interaction,
            "🎫 Ticket Roblox",
            description
        )


class RobloxSelect(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="Robux", emoji="💰", description="1000 Robux = 7.50€"),
            discord.SelectOption(label="Game Pass", emoji="🎮", description="Prix en ticket"),
        ]
        super().__init__(placeholder="Choisis ton service", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RobloxModal(self.values[0]))


class RobloxView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RobloxSelect())


class ValorantModal(discord.ui.Modal):

    def __init__(self):
        super().__init__(title="Commande Valorant")

        self.details = discord.ui.TextInput(
            label="Décris ta demande",
            style=discord.TextStyle.paragraph,
            required=True,
            placeholder="Ex: quantité de RP souhaitée, budget..."
        )
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        description = (
            f"📦 Service : **Riot Points**\n"
            f"📝 Détails : **{self.details.value}**\n\n"
            f"💳 Paiement PayPal\n"
            f"💬 Un vendeur reviendra vers toi rapidement"
        )
        await create_ticket(
            interaction,
            "🎫 Ticket Valorant",
            description
        )


class ValorantSelect(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="Riot Points", emoji="💠", description="Prix en ticket"),
        ]
        super().__init__(placeholder="Choisis ton service", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ValorantModal())


class ValorantView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ValorantSelect())


class RocketLeagueModal(discord.ui.Modal):

    def __init__(self, service):
        super().__init__(title="Commande Rocket League")
        self.service = service

        self.details = discord.ui.TextInput(
            label="Décris ta demande",
            style=discord.TextStyle.paragraph,
            required=True,
            placeholder="Ex: quantité de crédits, item souhaité, rang du compte..."
        )
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        description = (
            f"📦 Service : **{self.service}**\n"
            f"📝 Détails : **{self.details.value}**\n\n"
            f"💳 Paiement PayPal\n"
            f"💬 Un vendeur reviendra vers toi rapidement"
        )
        await create_ticket(
            interaction,
            "🎫 Ticket Rocket League",
            description
        )


class RocketLeagueSelect(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="Comptes Rocket League", emoji="🏆", description="Rang / skins / inventaire"),
        ]
        super().__init__(placeholder="Choisis ton service", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RocketLeagueModal(self.values[0]))


class RocketLeagueView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RocketLeagueSelect())


class AppsModal(discord.ui.Modal):

    def __init__(self, service):
        super().__init__(title="Commande Application")
        self.service = service

        self.quantity = discord.ui.TextInput(
            label="Quantité",
            required=True,
            placeholder="Ex: 1"
        )
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.quantity.value)
            if value < 1:
                return await interaction.response.send_message(
                    "❌ Quantité invalide.",
                    ephemeral=True
                )
            price = value * APPS_PRICES[self.service]
        except ValueError:
            return await interaction.response.send_message(
                "❌ Valeur invalide. Entre un nombre entier.",
                ephemeral=True
            )

        await create_ticket(
            interaction,
            "🎫 Ticket Applications",
            f"📦 Service : **{self.service} (Lifetime)**\n"
            f"🔢 Quantité : **{value}**\n"
            f"💰 Prix : **{price:.2f}€**\n\n"
            f"💳 Paiement PayPal\n"
            f"⚡ Livraison rapide\n"
            f"💬 Merci de patienter"
        )


class AppsSelect(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="ChatGPT Plus", emoji="🤖", description="Lifetime — 13€"),
            discord.SelectOption(label="YouTube Premium", emoji="▶️", description="Lifetime — 8€"),
            discord.SelectOption(label="Spotify Premium", emoji="🎵", description="Lifetime — 13€"),
            discord.SelectOption(label="Prime Video", emoji="📺", description="Lifetime — 10.50€"),
        ]
        super().__init__(placeholder="Choisis ton application", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AppsModal(self.values[0]))


class AppsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AppsSelect())


class FournisseurSelect(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(label="Réseaux Sociaux", emoji="📱", description="Accès fournisseur — 10€"),
            discord.SelectOption(label="Discord", emoji="💬", description="Accès fournisseur — 10€"),
            discord.SelectOption(label="Fortnite", emoji="🎮", description="Accès fournisseur — 10€"),
            discord.SelectOption(label="Roblox", emoji="🧱", description="Accès fournisseur — 10€"),
            discord.SelectOption(label="Valorant", emoji="💠", description="Accès fournisseur — 10€"),
            discord.SelectOption(label="Rocket League", emoji="🚗", description="Accès fournisseur — 10€"),
            discord.SelectOption(label="Applications", emoji="📲", description="Accès fournisseur — 10€"),
            discord.SelectOption(label="Tous les fournisseurs", emoji="🌟", description="Accès complet — 50€"),
        ]
        super().__init__(placeholder="Choisis ton accès fournisseur", options=options)

    async def callback(self, interaction: discord.Interaction):
        service = self.values[0]
        price = FOURNISSEUR_PRICES[service]
        description = (
            f"📦 Service : **Accès Fournisseur — {service}**\n"
            f"💰 Prix : **{price:.2f}€**\n\n"
            f"💳 Paiement PayPal\n"
            f"💬 Un vendeur reviendra vers toi rapidement"
        )
        await create_ticket(interaction, "🎫 Ticket Fournisseur", description)


class FournisseurView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(FournisseurSelect())


class AllShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛒 Commander le Pack Complet", style=discord.ButtonStyle.success)
    async def order(self, interaction: discord.Interaction, button: discord.ui.Button):
        description = (
            f"📦 Service : **Pack Shop Complet — Offre Premium**\n"
            f"💰 Prix : **{ALLSHOP_PRICE:.2f}€**\n\n"
            f"✅ Accès Fournisseurs inclus\n"
            f"✅ Serveur Discord prêt à vendre\n"
            f"✅ Gestion complète (Management)\n"
            f"✅ Organisation & mise en place\n"
            f"✅ Conseils & optimisation\n\n"
            f"💳 Paiement PayPal\n"
            f"💬 Un vendeur reviendra vers toi rapidement"
        )
        await create_ticket(interaction, "🎫 Ticket Pack Shop Complet", description)

# ================= COMMANDES =================

@bot.command()
async def tiktok(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — TikTok Boost",
        description=(
            "🚀 Followers haute qualité\n"
            "❤️ Likes instantanés\n"
            "👀 Views rapides\n\n"
            "⚡ Livraison en moins de 24h\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton service"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=ServiceView("tiktok"))

@bot.command()
async def discordpanel(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Discord Services",
        description=(
            "👥 Membres haute qualité\n"
            "🚀 Boosts rapides\n"
            "🎁 Nitro instantané\n\n"
            "⚡ Livraison rapide\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton service"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=ServiceView("discord"))

@bot.command()
async def fortnite(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Fortnite Services",
        description=(
            "💎 V-Bucks — 1000 = 7.50€\n"
            "🎁 Packs de skins / bundles — Prix en ticket\n"
            "🎮 Comptes Fortnite — Prix en ticket\n\n"
            "💳 Paiement PayPal\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton service"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=FortniteView())

@bot.command()
async def roblox(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Roblox Services",
        description=(
            "💰 Robux — 1000 = 7.50€\n"
            "🎮 Game Pass personnalisé — Prix en ticket\n\n"
            "💳 Paiement PayPal\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton service"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=RobloxView())

@bot.command()
async def valorant(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Valorant Services",
        description=(
            "💠 Riot Points — Toutes quantités\n\n"
            "💳 Paiement PayPal\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton service"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=ValorantView())

@bot.command()
async def rocket(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Rocket League Services",
        description=(
            "🏆 Comptes — Rang / skins / inventaire\n\n"
            "💳 Paiement PayPal\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton service"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=RocketLeagueView())

@bot.command()
async def app(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Applications Services",
        description=(
            "🤖 ChatGPT Plus (Lifetime) — 13€\n"
            "▶️ YouTube Premium (Lifetime) — 8€\n"
            "🎵 Spotify Premium (Lifetime) — 13€\n"
            "📺 Prime Video (Lifetime) — 10.50€\n\n"
            "💳 Paiement PayPal\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton application"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=AppsView())

@bot.command()
async def fourni(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Accès Fournisseur",
        description=(
            "📱 Réseaux Sociaux — 10€\n"
            "💬 Discord — 10€\n"
            "🎮 Fortnite — 10€\n"
            "🧱 Roblox — 10€\n"
            "💠 Valorant — 10€\n"
            "🚗 Rocket League — 10€\n"
            "📲 Applications — 10€\n"
            "🌟 Tous les fournisseurs — 50€\n\n"
            "💳 Paiement PayPal\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton accès fournisseur"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=FournisseurView())

@bot.command()
async def allshop(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Pack Shop Complet",
        description=(
            "🏆 **Offre Premium – Shop clé en main**\n\n"
            "✅ Accès Fournisseurs inclus\n"
            "✅ Serveur Discord prêt à vendre\n"
            "✅ Gestion complète (Management)\n"
            "✅ Organisation & mise en place\n"
            "✅ Conseils & optimisation\n\n"
            "Tout est fourni pour lancer votre business immédiatement.\n\n"
            "💰 Prix total : **75€**\n"
            "💳 Paiement PayPal\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Clique pour commander"
        ),
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=AllShopView())

# ================= START =================

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    bot.run(TOKEN)
