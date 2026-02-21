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

# ================= SERVICE SELECT =================

class ServiceSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Followers", description="Boost abonnés TikTok 🚀"),
            discord.SelectOption(label="Likes", description="Augmente les likes ❤️"),
            discord.SelectOption(label="Views", description="Augmente les vues 👀"),
        ]

        super().__init__(
            placeholder="Choisis ton service TikTok...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            QuantityModal(self.values[0])
        )

# ================= MODAL =================

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

        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"commande-{interaction.user.name}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🧾 Facture Automatique",
            description=(
                f"🎯 Service : **{self.service}**\n"
                f"📦 Quantité : **{qty}**\n"
                f"💰 Prix : **{price}€**"
            ),
            color=discord.Color.purple()
        )

        embed.set_footer(text="Slayzix Shop")

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

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# ================= MAIN VIEW =================

class MainView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ServiceSelect())

@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — TikTok Boost",
        description="Sélectionne ton service ci-dessous 👇",
        color=discord.Color.purple()
    )

    await ctx.send(embed=embed, view=MainView())

@bot.event
async def on_ready():
    bot.add_view(MainView())
    bot.add_view(TicketView())
    print(f"✅ Connecté en tant que {bot.user}")

bot.run(TOKEN)
