import discord
from discord.ext import commands
import json
import os

# ==============================
# CONFIG
# ==============================

TOKEN = os.getenv("TOKEN")  # NE PAS mettre le token ici

if not TOKEN:
    print("❌ TOKEN manquant dans les variables d'environnement.")
    exit()

TICKET_FILE = "tickets.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================
# SAVE SYSTEM (COMPTEUR PERMANENT)
# ==============================

def load_data():
    if not os.path.exists(TICKET_FILE):
        with open(TICKET_FILE, "w") as f:
            json.dump({"counter": 0}, f)
    with open(TICKET_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(TICKET_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==============================
# PRIX UNITAIRES
# ==============================

PRICES = {
    "followers": 0.0025,
    "views": 0.00015,
    "likes": 0.001
}

# ==============================
# SHOP VIEW
# ==============================

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟 Ouvrir un Ticket", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

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
            description=(
                "📌 Écris ton service + quantité\n\n"
                "Exemple:\n"
                "`followers 5000`\n"
                "`views 10000`\n"
                "`likes 2000`"
            ),
            color=discord.Color.blurple()
        )

        await channel.send(
            content="@Manager @Founders",
            embed=embed,
            view=TicketView(interaction.user)
        )

        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )

# ==============================
# TICKET VIEW
# ==============================

class TicketView(discord.ui.View):
    def __init__(self, creator):
        super().__init__(timeout=None)
        self.creator = creator
        self.claimer = None

    @discord.ui.button(label="📌 Claim", style=discord.ButtonStyle.primary)
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.claimer:
            await interaction.response.send_message("❌ Déjà claim.", ephemeral=True)
            return

        self.claimer = interaction.user

        # Retire l'écriture des autres staff
        for member in interaction.guild.members:
            if any(role.name in ["Manager", "Founders"] for role in member.roles):
                if member != interaction.user:
                    await interaction.channel.set_permissions(member, send_messages=False)

        # PayPal automatique
        paypal = None
        username = interaction.user.name.lower()

        if username == "hayzoxs":
            paypal = "https://www.paypal.me/HayZoXs"
        elif username == "slayzixbetter":
            paypal = "https://www.paypal.me/SlayzixxBetter"

        await interaction.channel.send(
            f"📌 Ticket réclamé par {interaction.user.mention}\n"
            f"💳 PayPal : {paypal if paypal else 'Non défini'}"
        )

        await interaction.response.defer()

    @discord.ui.button(label="💳 Confirmer paiement", style=discord.ButtonStyle.success)
    async def confirm_payment(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.creator:
            await interaction.response.send_message(
                "❌ Seul le client peut confirmer.",
                ephemeral=True
            )
            return

        await interaction.channel.send("💳 Paiement confirmé par le client.")
        await interaction.response.defer()

    @discord.ui.button(label="🔒 Paiement validé (Staff)", style=discord.ButtonStyle.danger)
    async def validate_payment(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.claimer:
            await interaction.response.send_message(
                "❌ Seul le staff qui a claim peut valider.",
                ephemeral=True
            )
            return

        await interaction.channel.send("✅ Paiement validé. Commande en cours 🚀")
        await interaction.response.defer()

# ==============================
# CALCUL AUTOMATIQUE + FACTURE
# ==============================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.name.startswith("ticket-"):

        parts = message.content.lower().split()

        if len(parts) == 2:

            service = parts[0]

            try:
                quantity = int(parts[1])
            except:
                return

            if service in PRICES:

                total = round(quantity * PRICES[service], 2)

                embed = discord.Embed(
                    title="🧾 Facture automatique",
                    description=(
                        f"🎯 Service : {service.capitalize()}\n"
                        f"📦 Quantité : {quantity}\n"
                        f"💰 Total : {total}€"
                    ),
                    color=discord.Color.green()
                )

                await message.channel.send(embed=embed)

    await bot.process_commands(message)

# ==============================
# COMMAND SHOP
# ==============================

@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="💎 SLAYZIX SHOP",
        description=(
            "🔥 Services TikTok disponibles\n\n"
            "• followers\n"
            "• views\n"
            "• likes\n\n"
            "💬 Dans le ticket écris :\n"
            "`followers 5000`\n\n"
            "💳 Le prix sera calculé automatiquement."
        ),
        color=discord.Color.purple()
    )

    await ctx.send(embed=embed, view=ShopView())

# ==============================

bot.run(TOKEN)
