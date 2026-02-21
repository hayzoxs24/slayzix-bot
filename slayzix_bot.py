import discord
from discord.ext import commands
import os

# ===============================
# CONFIGURATION
# ===============================

TOKEN = os.getenv("TOKEN")  # Token via variable d'environnement
CATEGORY_ID = 123456789  # ID de la catégorie où les tickets seront créés

BANNER_URL = "https://cdn.discordapp.com/attachments/1462275672503357705/1474577936265904198/IMG_4255.png?ex=699a5b38&is=699909b8&hm=c7fe4cbce99d75b832edb22ba31db9a0d86711dc1f9bd32c14e6c1010307a302&"

if not TOKEN:
    raise ValueError("Le TOKEN n'est pas défini dans les variables d'environnement.")

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ===============================
# MODAL QUANTITÉ (MULTIPLE DE 1000)
# ===============================

class QuantityModal(discord.ui.Modal, title="Entrer la quantité (multiple de 1000)"):

    quantity = discord.ui.TextInput(
        label="Quantité souhaitée",
        placeholder="Exemple: 1000 / 2000 / 5000",
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
                    "❌ La quantité doit être un multiple de 1000 (1000, 2000, 3000...)",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="💳 Détails de la commande",
                description=(
                    f"📦 **Service :** {self.service}\n"
                    f"🔢 **Quantité :** {amount}\n\n"
                    "📩 Envoie ton lien dans ce salon.\n"
                    "💰 Le prix sera communiqué par le staff.\n"
                    "⚡ Livraison rapide.\n"
                    "💎 Haute qualité garantie."
                ),
                color=discord.Color.green()
            )

            embed.set_image(url=BANNER_URL)
            embed.set_footer(text="Elite Social Boost • Premium Services")

            await interaction.response.send_message(embed=embed)

        except ValueError:
            await interaction.response.send_message(
                "❌ Merci d'entrer un nombre valide.",
                ephemeral=True
            )


# ===============================
# BOUTONS DU TICKET
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
# MENU PRINCIPAL
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
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        service = self.values[0]

        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)

        if category is None:
            await interaction.response.send_message(
                "❌ Catégorie invalide. Vérifie le CATEGORY_ID.",
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
                f"👤 **Client :** {interaction.user.mention}\n"
                f"📦 **Service choisi :** {service}\n\n"
                "💎 **Nos avantages :**\n"
                "• Engagement premium\n"
                "• Livraison rapide\n"
                "• Support actif\n"
                "• Service sécurisé\n"
                "• Résultats garantis\n\n"
                "Clique sur **Entrer la quantité** pour continuer."
            ),
            color=discord.Color.from_rgb(25, 25, 25)
        )

        embed.set_image(url=BANNER_URL)
        embed.set_footer(text="Elite Social Boost • Premium Services")

        await channel.send(embed=embed, view=TicketView(service))

        await interaction.response.send_message(
            f"✅ Ton ticket a été créé : {channel.mention}",
            ephemeral=True
        )


class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MainServiceSelect())


# ===============================
# COMMANDE PANEL
# ===============================

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="🚀 Elite Social Boost",
        description=(
            "🎯 **Nos Services Premium :**\n\n"
            "📈 Instagram Followers\n"
            "❤️ Instagram Likes\n"
            "🎬 TikTok Views\n\n"
            "💎 Haute qualité\n"
            "⚡ Livraison rapide\n"
            "🔒 Paiement sécurisé\n"
            "📊 Résultats garantis\n\n"
            "Sélectionne un service ci-dessous pour ouvrir un ticket."
        ),
        color=discord.Color.from_rgb(30, 30, 30)
    )

    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="Elite Social Boost • Premium Services")

    await ctx.send(embed=embed, view=MainView())


# ===============================
# READY
# ===============================

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    bot.add_view(MainView())


bot.run(TOKEN)
