import discord
from discord.ext import commands
import os

# ===============================
# CONFIG
# ===============================

TOKEN = os.getenv("TOKEN")
CATEGORY_ID = 123456789  # ID catégorie tickets

BANNER_URL = "https://cdn.discordapp.com/attachments/1462275672503357705/1474577936265904198/IMG_4255.png?ex=699a5b38&is=699909b8&hm=c7fe4cbce99d75b832edb22ba31db9a0d86711dc1f9bd32c14e6c1010307a302&"

if not TOKEN:
    raise ValueError("TOKEN manquant dans les variables d'environnement.")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ===============================
# MODAL QUANTITE
# ===============================

class QuantityModal(discord.ui.Modal, title="Entrer la quantité (multiple de 1000)"):

    quantity = discord.ui.TextInput(
        label="Quantité",
        placeholder="1000 / 2000 / 5000",
        required=True
    )

    def __init__(self, service):
        super().__init__()
        self.service = service

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.quantity.value)

            if amount < 1000 or amount % 1000 != 0:
                await interaction.response.send_message(
                    "❌ Doit être multiple de 1000.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="💳 Détails de la commande",
                description=(
                    f"📦 Service : **{self.service}**\n"
                    f"🔢 Quantité : **{amount}**\n\n"
                    "📩 Envoie ton lien.\n"
                    "💰 Le staff donnera le prix.\n"
                    "⚡ Livraison rapide."
                ),
                color=discord.Color.green()
            )

            embed.set_image(url=BANNER_URL)

            await interaction.response.send_message(embed=embed)

        except ValueError:
            await interaction.response.send_message(
                "❌ Nombre invalide.",
                ephemeral=True
            )


# ===============================
# BOUTONS TICKET
# ===============================

class QuantityButton(discord.ui.Button):
    def __init__(self, service):
        super().__init__(
            label="✏️ Entrer la quantité",
            style=discord.ButtonStyle.primary
        )
        self.service = service

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(QuantityModal(self.service))


class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="🔒 Fermer",
            style=discord.ButtonStyle.danger
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.channel.delete()


class TicketView(discord.ui.View):
    def __init__(self, service):
        super().__init__(timeout=None)
        self.add_item(QuantityButton(service))
        self.add_item(CloseButton())


# ===============================
# MENU SERVICE
# ===============================

class MainServiceSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Instagram Followers", emoji="📈"),
            discord.SelectOption(label="Instagram Likes", emoji="❤️"),
            discord.SelectOption(label="TikTok Views", emoji="🎬"),
        ]

        super().__init__(
            placeholder="Choisis ton service...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        service = self.values[0]
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)

        if not category:
            await interaction.response.send_message(
                "❌ CATEGORY_ID invalide.",
                ephemeral=True
            )
            return

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category
        )

        embed = discord.Embed(
            title="🛒 Nouvelle Commande",
            description=(
                f"👤 {interaction.user.mention}\n"
                f"📦 Service : **{service}**\n\n"
                "💎 Premium\n"
                "⚡ Rapide\n"
                "🔒 Sécurisé\n\n"
                "Clique pour entrer la quantité."
            ),
            color=discord.Color.dark_gray()
        )

        embed.set_image(url=BANNER_URL)

        await channel.send(embed=embed, view=TicketView(service))

        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )


class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MainServiceSelect())


# ===============================
# COMMANDE SHOP
# ===============================

@bot.command()
@commands.has_permissions(administrator=True)
async def shop(ctx):
    embed = discord.Embed(
        title="🚀 Elite Social Boost",
        description=(
            "📈 Instagram Followers\n"
            "❤️ Instagram Likes\n"
            "🎬 TikTok Views\n\n"
            "💎 Haute qualité\n"
            "⚡ Livraison rapide\n"
            "🔒 Paiement sécurisé\n\n"
            "Sélectionne un service ci-dessous."
        ),
        color=discord.Color.dark_gray()
    )

    embed.set_image(url=BANNER_URL)

    await ctx.send(embed=embed, view=MainView())


@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")


bot.run(TOKEN)
