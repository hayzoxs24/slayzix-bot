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
# CLOSE CONFIRM
# =============================

class CloseConfirmSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Confirmer la fermeture", emoji="✅"),
            discord.SelectOption(label="Annuler", emoji="❌")
        ]
        super().__init__(placeholder="Confirmer la fermeture ?", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Confirmer la fermeture":
            await interaction.channel.send("🔒 Ticket fermé.")
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Fermeture annulée.", ephemeral=True)

class CloseConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)
        self.add_item(CloseConfirmSelect())

# =============================
# QUANTITY MODAL
# =============================

class QuantityModal(discord.ui.Modal, title="Entrer la quantité"):

    quantity = discord.ui.TextInput(
        label="Quantité (multiple de 1000 uniquement)",
        placeholder="1000, 2000, 3000...",
        required=True
    )

    def __init__(self, creator, service):
        super().__init__()
        self.creator = creator
        self.service = service

    async def on_submit(self, interaction: discord.Interaction):

        if interaction.user != self.creator:
            await interaction.response.send_message("❌ Ce n'est pas ton ticket.", ephemeral=True)
            return

        try:
            quantity = int(self.quantity.value)
        except:
            await interaction.response.send_message("❌ Nombre invalide.", ephemeral=True)
            return

        if quantity < 1000 or quantity % 1000 != 0:
            await interaction.response.send_message(
                "❌ La quantité doit être 1000, 2000, 3000 etc.",
                ephemeral=True
            )
            return

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

        await interaction.channel.send(embed=embed, view=PaymentView(self.creator))
        await interaction.response.send_message("✅ Quantité validée.", ephemeral=True)

# =============================
# QUANTITY BUTTON VIEW
# =============================

class QuantityButtonView(discord.ui.View):
    def __init__(self, creator, service):
        super().__init__(timeout=None)
        self.creator = creator
        self.service = service

    @discord.ui.button(label="✏️ Entrer la quantité", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.creator:
            await interaction.response.send_message("❌ Ce n'est pas ton ticket.", ephemeral=True)
            return

        await interaction.response.send_modal(
            QuantityModal(self.creator, self.service)
        )

# =============================
# PAYMENT VIEW
# =============================

class PaymentView(discord.ui.View):
    def __init__(self, creator):
        super().__init__(timeout=None)
        self.creator = creator
        self.paid = False

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

        await interaction.response.send_message(
            "⚠️ Confirmation requise :",
            view=CloseConfirmView(),
            ephemeral=True
        )

# =============================
# SERVICE SELECT
# =============================

class MainServiceSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Followers", emoji="👥"),
            discord.SelectOption(label="Views", emoji="👀"),
            discord.SelectOption(label="Likes", emoji="❤️"),
        ]
        super().__init__(placeholder="Choisis ton service...", options=options)

    async def callback(self, interaction: discord.Interaction):

        service = self.values[0]

        data = load_data()
        data["counter"] += 1
        save_data(data)
        ticket_number = data["counter"]

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
            description=f"Service sélectionné : **{service}**\n\nClique pour entrer la quantité.",
            color=discord.Color.blurple()
        )

        await channel.send(
            embed=embed,
            view=QuantityButtonView(interaction.user, service)
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
# SHOP COMMAND
# =============================

@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX PREMIUM SHOP",
        description="Sélectionne un service ci-dessous.",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed, view=MainView())

bot.run(TOKEN)
