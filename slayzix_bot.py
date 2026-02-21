import discord
from discord.ext import commands
import json
import os

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("TOKEN manquant.")
    exit()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TICKET_FILE = "tickets.json"

# =============================
# SAVE SYSTEM
# =============================

def load_data():
    if not os.path.exists(TICKET_FILE):
        with open(TICKET_FILE, "w") as f:
            json.dump({"counter": 0}, f)
    with open(TICKET_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(TICKET_FILE, "w") as f:
        json.dump(data, f, indent=4)

# =============================
# PRIX
# =============================

PRICES = {
    "Followers": 0.0025,
    "Views": 0.00015,
    "Likes": 0.001
}

# =============================
# SHOP VIEW
# =============================

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟 Créer un Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        data = load_data()
        data["counter"] += 1
        save_data(data)

        ticket_number = data["counter"]

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{ticket_number}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"🎫 Ticket #{ticket_number}",
            description="Sélectionne ton service 👇",
            color=discord.Color.blurple()
        )

        await channel.send(
            content=f"{interaction.user.mention} | @Manager @Founders",
            embed=embed,
            view=ServiceSelectView(interaction.user)
        )

        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )

# =============================
# SERVICE SELECT
# =============================

class ServiceSelect(discord.ui.Select):
    def __init__(self, creator):
        self.creator = creator

        options = [
            discord.SelectOption(label="Followers"),
            discord.SelectOption(label="Views"),
            discord.SelectOption(label="Likes"),
        ]

        super().__init__(placeholder="Choisis le service...", options=options)

    async def callback(self, interaction: discord.Interaction):

        if interaction.user != self.creator:
            await interaction.response.send_message("❌ Ce n'est pas ton ticket.", ephemeral=True)
            return

        service = self.values[0]
        await interaction.channel.send(
            f"📦 Service sélectionné : **{service}**\nChoisis maintenant la quantité 👇",
            view=QuantitySelectView(self.creator, service)
        )

        await interaction.response.defer()

class ServiceSelectView(discord.ui.View):
    def __init__(self, creator):
        super().__init__(timeout=None)
        self.add_item(ServiceSelect(creator))

# =============================
# QUANTITY SELECT
# =============================

class QuantitySelect(discord.ui.Select):
    def __init__(self, creator, service):
        self.creator = creator
        self.service = service

        options = [
            discord.SelectOption(label="1000"),
            discord.SelectOption(label="5000"),
            discord.SelectOption(label="10000"),
        ]

        super().__init__(placeholder="Choisis la quantité...", options=options)

    async def callback(self, interaction: discord.Interaction):

        if interaction.user != self.creator:
            await interaction.response.send_message("❌ Ce n'est pas ton ticket.", ephemeral=True)
            return

        quantity = int(self.values[0])
        total = round(quantity * PRICES[self.service], 2)

        embed = discord.Embed(
            title="🧾 Facture",
            description=(
                f"🎯 Service : {self.service}\n"
                f"📦 Quantité : {quantity}\n"
                f"💰 Total : {total}€"
            ),
            color=discord.Color.green()
        )

        await interaction.channel.send(
            embed=embed,
            view=PaymentView(self.creator)
        )

        await interaction.response.defer()

class QuantitySelectView(discord.ui.View):
    def __init__(self, creator, service):
        super().__init__(timeout=None)
        self.add_item(QuantitySelect(creator, service))

# =============================
# PAYMENT VIEW
# =============================

class PaymentView(discord.ui.View):
    def __init__(self, creator):
        super().__init__(timeout=None)
        self.creator = creator
        self.paid = False

    @discord.ui.button(label="💳 PayPal HayZoXs", style=discord.ButtonStyle.link,
                       url="https://www.paypal.me/HayZoXs")
    async def paypal1(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="💳 PayPal Slayzix's", style=discord.ButtonStyle.link,
                       url="https://www.paypal.me/SlayzixxBetter")
    async def paypal2(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="✅ J'ai payé", style=discord.ButtonStyle.success)
    async def paid_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.creator:
            await interaction.response.send_message("❌ Seul le client peut cliquer.", ephemeral=True)
            return

        self.paid = True
        await interaction.channel.send("💬 Le client indique avoir payé. En attente confirmation staff.")
        await interaction.response.defer()

    @discord.ui.button(label="🔒 Confirmer paiement (Staff)", style=discord.ButtonStyle.danger)
    async def confirm_staff(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role.name in ["Manager", "Founders"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Staff uniquement.", ephemeral=True)
            return

        if not self.paid:
            await interaction.response.send_message("❌ Le client n'a pas encore cliqué sur 'J'ai payé'.", ephemeral=True)
            return

        await interaction.channel.send("✅ Paiement confirmé par le staff. Commande en cours 🚀")
        await interaction.response.defer()

# =============================
# COMMAND SHOP
# =============================

@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="💎 SLAYZIX SHOP",
        description="Clique pour créer un ticket.",
        color=discord.Color.purple()
    )

    await ctx.send(embed=embed, view=ShopView())

# =============================

bot.run(TOKEN)
