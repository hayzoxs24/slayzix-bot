import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import os

TOKEN = os.getenv("TOKEN")

PAYPAL_HAYZOXS = "https://paypal.me/HAYZOXS"
PAYPAL_SLAYZIX = "https://paypal.me/SLAYZIXxbetter"

PRICES = {
    "Followers": 2,
    "Likes": 1.5,
    "Views": 1
}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= SELECT =================

class ServiceSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Followers", emoji="🚀"),
            discord.SelectOption(label="Likes", emoji="❤️"),
            discord.SelectOption(label="Views", emoji="👀"),
        ]

        super().__init__(
            placeholder="Choisis ton service...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            QuantityModal(self.values[0])
        )

# ================= MODAL =================

class QuantityModal(discord.ui.Modal, title="Commande TikTok"):

    def __init__(self, service):
        super().__init__()
        self.service = service

        self.quantity = discord.ui.TextInput(
            label="Quantité (multiple de 1000)",
            placeholder="1000, 2000, 3000...",
            required=True
        )

        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):

        if not interaction.guild:
            return await interaction.response.send_message(
                "❌ Commande uniquement dans un serveur.",
                ephemeral=True
            )

        try:
            qty = int(self.quantity.value)
            if qty % 1000 != 0:
                raise ValueError
        except:
            return await interaction.response.send_message(
                "❌ Entre un multiple de 1000 valide.",
                ephemeral=True
            )

        price = (qty / 1000) * PRICES[self.service]
        price_formatted = f"{price:.2f}"

        guild = interaction.guild

        channel_name = f"commande-{interaction.user.name}".replace(" ", "-").lower()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🧾 Facture Automatique",
            description=(
                f"🎯 **Service :** {self.service}\n"
                f"📦 **Quantité :** {qty}\n"
                f"💰 **Total :** {price_formatted}€\n\n"
                f"Paiement sécurisé via PayPal ci-dessous 👇"
            ),
            color=discord.Color.purple()
        )

        embed.set_footer(text="Slayzix Premium Shop")

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=TicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )

# ================= TICKET VIEW =================

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

    @discord.ui.button(label="🔒 Fermer la commande", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# ================= MAIN =================

class MainView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ServiceSelect())

@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="💎 SLAYZIX PREMIUM SHOP",
        description=(
            "🚀 Followers\n"
            "❤️ Likes\n"
            "👀 Views\n\n"
            "Sélectionne ton service 👇"
        ),
        color=discord.Color.purple()
    )

    await ctx.send(embed=embed, view=MainView())

@bot.event
async def on_ready():
    bot.add_view(MainView())
    bot.add_view(TicketView())
    print(f"✅ Connecté en tant que {bot.user}")

bot.run(TOKEN)
