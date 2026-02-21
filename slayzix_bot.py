import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import os

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")

PAYPAL_HAYZOXS = "https://paypal.me/HAYZOXS"
PAYPAL_SLAYZIX = "https://paypal.me/SLAYZIXxbetter"

PRICES = {
    "Followers": 2,
    "Likes": 1.5,
    "Views": 1
}

# ================= INTENTS =================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =====================================================
# ================= TIKTOK SYSTEM =====================
# =====================================================

class ServiceSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Followers", description="Abonnés TikTok 🚀"),
            discord.SelectOption(label="Likes", description="Likes TikTok ❤️"),
            discord.SelectOption(label="Views", description="Vues TikTok 👀"),
        ]

        super().__init__(
            placeholder="Choisis ton service",
            options=options,
            custom_id="service_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            QuantityModal(self.values[0])
        )


class QuantityModal(discord.ui.Modal, title="Quantité (multiple de 1000)"):

    def __init__(self, service):
        super().__init__()
        self.service = service

        self.quantity = discord.ui.TextInput(
            label="Ex: 1000, 2000, 3000...",
            required=True
        )
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):

        try:
            qty = int(self.quantity.value)
            if qty % 1000 != 0:
                return await interaction.response.send_message(
                    "❌ La quantité doit être un multiple de 1000.",
                    ephemeral=True
                )
        except:
            return await interaction.response.send_message(
                "❌ Nombre invalide.",
                ephemeral=True
            )

        price = (qty / 1000) * PRICES[self.service]
        price_formatted = f"{price:.2f}"

        await create_ticket(
            interaction,
            title="🧾 Facture Automatique",
            description=(
                f"🎯 Service : **{self.service}**\n"
                f"📦 Quantité : **{qty}**\n"
                f"💰 Prix : **{price_formatted}€**\n\n"
                f"⚡ Livraison garantie en moins de 24h\n"
                f"🔒 Paiement sécurisé via PayPal\n"
                f"💬 Support actif si besoin"
            ),
            color=discord.Color.purple(),
            footer="Slayzix Shop • Livraison rapide -24H"
        )


class MainView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ServiceSelect())


# =====================================================
# ================= DISCORD SYSTEM ====================
# =====================================================

class DiscordServiceSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Membres en ligne x1000", emoji="👥"),
            discord.SelectOption(label="Membres hors-ligne x1000", emoji="👤"),
            discord.SelectOption(label="Boost serveur x14", emoji="🚀"),
            discord.SelectOption(label="Nitro 1 mois", emoji="🎁"),
        ]

        super().__init__(
            placeholder="Choisis ton service Discord",
            options=options,
            custom_id="discord_service_select"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            DiscordQuantityModal(self.values[0])
        )


class DiscordQuantityModal(discord.ui.Modal, title="Quantité"):

    def __init__(self, service):
        super().__init__()
        self.service = service

        self.quantity = discord.ui.TextInput(
            label="Quantité (ex: 1000 , 2000 , 3000...)",
            required=True
        )
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):

        try:
            qty = int(self.quantity.value)
        except:
            return await interaction.response.send_message(
                "❌ Nombre invalide.",
                ephemeral=True
            )

        await create_ticket(
            interaction,
            title="🎫 Ticket Discord",
            description=(
                f"📦 Service : **{self.service}**\n"
                f"🔢 Quantité : **{qty}**\n\n"
                f"💳 Paiement via PayPal\n"
                f"⚡ Livraison rapide\n"
                f"💬 Merci de patienter"
            ),
            color=discord.Color.blurple(),
            footer="Slayzix Shop • Discord Services"
        )


class DiscordPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DiscordServiceSelect())


# =====================================================
# ================= TICKET SYSTEM =====================
# =====================================================

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(Button(
            label="💳 PayPal HayZoXs",
            style=discord.ButtonStyle.link,
            url=PAYPAL_HAYZOXS
        ))

        self.add_item(Button(
            label="💳 PayPal Slayzix's",
            style=discord.ButtonStyle.link,
            url=PAYPAL_SLAYZIX
        ))

    @discord.ui.button(
        label="🔒 Fermer",
        style=discord.ButtonStyle.danger,
        custom_id="close_ticket"
    )
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()


async def create_ticket(interaction, title, description, color, footer):

    guild = interaction.guild

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True),
        guild.me: discord.PermissionOverwrite(view_channel=True)
    }

    category = discord.utils.get(guild.categories, name="🎫 COMMANDES")
    if not category:
        category = await guild.create_category("🎫 COMMANDES")

    channel = await guild.create_text_channel(
        name=f"ticket-{interaction.user.name}".replace(" ", "-").lower(),
        overwrites=overwrites,
        category=category
    )

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    embed.set_footer(text=footer)

    await channel.send(
        content=interaction.user.mention,
        embed=embed,
        view=TicketView()
    )

    await interaction.response.send_message(
        f"✅ Ticket créé : {channel.mention}",
        ephemeral=True
    )


# =====================================================
# ================= COMMANDES =========================
# =====================================================

@bot.command()
async def shop(ctx):

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
        color=discord.Color.purple()
    )

    await ctx.send(embed=embed, view=MainView())


@bot.command()
async def discordpanel(ctx):

    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Discord Boost",
        description=(
            "👥 Membres Discord\n"
            "🚀 Boost Serveur\n"
            "🎁 Nitro\n\n"
            "⚡ Livraison rapide\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton service"
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed, view=DiscordPanelView())


@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")


bot.run(TOKEN)
