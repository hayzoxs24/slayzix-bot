import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import os

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")

PAYPAL_HAYZOXS = "https://paypal.me/HAYZOXS"
PAYPAL_SLAYZIX = "https://paypal.me/SLAYZIXxbetter"

TIKTOK_PRICES = {
    "Followers": 2,
    "Likes": 1.5,
    "Views": 1
}

DISCORD_PRICES = {
    "Membres en ligne": 4.5,
    "Membres hors-ligne": 4,
    "Boost x14": 3,
    "Nitro 1 mois": 3.5
}

DECORATION_PRICES = {
    4.99: 1.75,
    5.99: 2.39,
    6.99: 2.55,
    7.99: 2.91,
    8.49: 3.25,
    9.99: 3.60,
    11.99: 3.95
}

# ================= INTENTS =================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =====================================================
# ================= TICKET SYSTEM =====================
# =====================================================

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(Button(label="💳 PayPal HayZoXs",
                             style=discord.ButtonStyle.link,
                             url=PAYPAL_HAYZOXS))

        self.add_item(Button(label="💳 PayPal Slayzix's",
                             style=discord.ButtonStyle.link,
                             url=PAYPAL_SLAYZIX))

    @discord.ui.button(label="🔒 Fermer",
                       style=discord.ButtonStyle.danger,
                       custom_id="close_ticket")
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

    embed = discord.Embed(title=title,
                          description=description,
                          color=color)

    embed.set_footer(text=footer)

    await channel.send(content=interaction.user.mention,
                       embed=embed,
                       view=TicketView())

    await interaction.response.send_message(
        f"✅ Ticket créé : {channel.mention}",
        ephemeral=True
    )

# =====================================================
# ================= TIKTOK PANEL ======================
# =====================================================

class TikTokSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Followers", emoji="🚀"),
            discord.SelectOption(label="Likes", emoji="❤️"),
            discord.SelectOption(label="Views", emoji="👀"),
        ]

        super().__init__(placeholder="Choisis ton service",
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            TikTokModal(self.values[0])
        )


class TikTokModal(discord.ui.Modal, title="Quantité (multiple de 1000)"):

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

            if qty < 1000 or qty % 1000 != 0:
                return await interaction.response.send_message(
                    "❌ Minimum 1000 et multiple de 1000 requis.",
                    ephemeral=True
                )

            price = (qty / 1000) * TIKTOK_PRICES[self.service]

        except:
            return await interaction.response.send_message(
                "❌ Nombre invalide.",
                ephemeral=True
            )

        await create_ticket(
            interaction,
            "🧾 Facture TikTok",
            f"📦 Service : **{self.service}**\n"
            f"🔢 Quantité : **{qty}**\n"
            f"💰 Prix : **{price:.2f}€**\n\n"
            "⚡ Livraison -24h\n💳 Paiement PayPal",
            discord.Color.purple(),
            "Slayzix Shop • TikTok"
        )


class TikTokView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TikTokSelect())

# =====================================================
# ================= DISCORD PANEL =====================
# =====================================================

class DiscordSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Membres en ligne", emoji="👥"),
            discord.SelectOption(label="Membres hors-ligne", emoji="👤"),
            discord.SelectOption(label="Boost x14", emoji="🚀"),
            discord.SelectOption(label="Nitro 1 mois", emoji="🎁"),
            discord.SelectOption(label="Profile Decoration", emoji="🎨"),
        ]

        super().__init__(placeholder="Choisis ton service Discord",
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            DiscordModal(self.values[0])
        )


class DiscordModal(discord.ui.Modal, title="Commande Discord"):

    def __init__(self, service):
        super().__init__()
        self.service = service

        self.quantity = discord.ui.TextInput(
            label="Quantité (ou prix original pour decoration)",
            required=True
        )
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):

        try:
            value = float(self.quantity.value)

            # MEMBRES
            if "Membres" in self.service:
                qty = int(value)

                if qty < 1000 or qty % 1000 != 0:
                    return await interaction.response.send_message(
                        "❌ Minimum 1000 et multiple de 1000 requis.",
                        ephemeral=True
                    )

                price = (qty / 1000) * DISCORD_PRICES[self.service]

            # BOOST / NITRO
            elif self.service in ["Boost x14", "Nitro 1 mois"]:
                qty = int(value)
                price = qty * DISCORD_PRICES[self.service]

            # DECORATION
            elif self.service == "Profile Decoration":

                if value not in DECORATION_PRICES:
                    return await interaction.response.send_message(
                        "❌ Prix invalide.\nExemple : 4.99, 5.99, 6.99...",
                        ephemeral=True
                    )

                qty = 1
                price = DECORATION_PRICES[value]

        except:
            return await interaction.response.send_message(
                "❌ Valeur invalide.",
                ephemeral=True
            )

        await create_ticket(
            interaction,
            "🎫 Facture Discord",
            f"📦 Service : **{self.service}**\n"
            f"🔢 Quantité : **{qty}**\n"
            f"💰 Prix : **{price:.2f}€**\n\n"
            "💳 Paiement PayPal\n⚡ Livraison rapide",
            discord.Color.blurple(),
            "Slayzix Shop • Discord"
        )


class DiscordView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DiscordSelect())

# =====================================================
# ================= COMMANDES =========================
# =====================================================

@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — TikTok Boost",
        description="Sélectionne ton service 👇",
        color=discord.Color.purple()
    )

    await ctx.send(embed=embed, view=TikTokView())


@bot.command(name="discord")
async def discordpanel(ctx):

    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Discord Boost",
        description="Sélectionne ton service 👇",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed, view=DiscordView())


@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")


bot.run(TOKEN)
