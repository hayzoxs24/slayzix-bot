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
# PRICES
# =============================

PRICES = {
    "Followers": 0.0025,
    "Views": 0.00015,
    "Likes": 0.001
}

# =============================
# MAIN SHOP VIEW (SERVICE MENU BEFORE TICKET)
# =============================

class MainServiceSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Followers", emoji="👥"),
            discord.SelectOption(label="Views", emoji="👀"),
            discord.SelectOption(label="Likes", emoji="❤️"),
        ]

        super().__init__(
            placeholder="Choisis ton service...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        service = self.values[0]

        data = load_data()
        data["counter"] += 1
        save_data(data)

        ticket_number = data["counter"]

        # Création catégorie auto
        category = discord.utils.get(interaction.guild.categories, name="🎫 Tickets")
        if not category:
            category = await interaction.guild.create_category("🎫 Tickets")

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{ticket_number}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Nouveau Ticket",
            description=(
                f"👤 Client : {interaction.user.mention}\n"
                f"📦 Service : **{service}**\n\n"
                "Choisis maintenant la quantité 👇"
            ),
            color=discord.Color.blurple()
        )

        embed.set_footer(text=f"Ticket #{ticket_number} • SLAYZIX SHOP")

        await channel.send(
            embed=embed,
            view=QuantitySelectView(interaction.user, service)
        )

        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )

class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MainServiceSelect())

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
                f"📦 Service : {self.service}\n"
                f"🔢 Quantité : {quantity}\n"
                f"💰 Total : **{total}€**"
            ),
            color=discord.Color.green()
        )

        embed.set_footer(text="Procède au paiement via PayPal")

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

        # Boutons PayPal
        self.add_item(discord.ui.Button(
            label="💳 PayPal HayZoXs",
            style=discord.ButtonStyle.link,
            url="https://www.paypal.me/HayZoXs"
        ))

        self.add_item(discord.ui.Button(
            label="💳 PayPal Slayzix",
            style=discord.ButtonStyle.link,
            url="https://www.paypal.me/SlayzixxBetter"
        ))

    @discord.ui.button(label="✅ J'ai payé", style=discord.ButtonStyle.success)
    async def paid_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.creator:
            await interaction.response.send_message("❌ Seul le client peut cliquer.", ephemeral=True)
            return

        self.paid = True
        await interaction.channel.send("⏳ Paiement signalé. En attente validation staff.")
        await interaction.response.defer()

    @discord.ui.button(label="🔒 Confirmer paiement (Staff)", style=discord.ButtonStyle.primary)
    async def confirm_staff(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role.name in ["Manager", "Founders"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Staff uniquement.", ephemeral=True)
            return

        if not self.paid:
            await interaction.response.send_message("❌ Le client n'a pas encore payé.", ephemeral=True)
            return

        await interaction.channel.send("✅ Paiement confirmé. Commande lancée 🚀")
        await interaction.response.defer()

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role.name in ["Manager", "Founders"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Staff uniquement.", ephemeral=True)
            return

        await interaction.channel.send("🔒 Ticket fermé.")
        await interaction.channel.delete()

# =============================
# SHOP COMMAND
# =============================

@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="💎 SLAYZIX PREMIUM SHOP",
        description=(
            "Bienvenue dans la boutique officielle.\n\n"
            "📦 Sélectionne un service ci-dessous pour ouvrir un ticket."
        ),
        color=discord.Color.purple()
    )

    embed.set_footer(text="Paiement sécurisé • Livraison rapide • Support 24/7")

    await ctx.send(embed=embed, view=MainView())

# =============================

bot.run(TOKEN)
