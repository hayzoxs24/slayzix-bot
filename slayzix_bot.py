import discord
from discord.ext import commands
import os

# ===============================
# CONFIG
# ===============================

TOKEN = os.getenv("TOKEN")

BANNER_URL = "https://cdn.discordapp.com/attachments/1462275672503357705/1474580179153326332/IMG_6798.png?ex=699a5d4f&is=69990bcf&hm=b52804eedcfcc25698865a8b59a9d7ade23366dc0ad6cd90dda04679a38ebd53&"

if not TOKEN:
    raise ValueError("TOKEN manquant dans les variables d'environnement.")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ===============================
# MODAL QUANTITÉ (MULTIPLE 1000)
# ===============================

class QuantityModal(discord.ui.Modal, title="Entrer la quantité (multiple de 1000)"):

    quantity = discord.ui.TextInput(
        label="Quantité",
        placeholder="1000 / 2000 / 5000",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.quantity.value)

            if amount < 1000 or amount % 1000 != 0:
                await interaction.response.send_message(
                    "❌ La quantité doit être un multiple de 1000.",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="💳 Détails de la commande TikTok",
                description=(
                    f"🎬 Service : **TikTok Boost**\n"
                    f"🔢 Quantité : **{amount}**\n\n"
                    "📩 Envoie ton lien TikTok.\n"
                    "💰 Le staff donnera le prix.\n"
                    "⚡ Livraison rapide.\n"
                    "💎 Haute qualité garantie."
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
    def __init__(self):
        super().__init__(
            label="✏️ Entrer la quantité",
            style=discord.ButtonStyle.primary
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(QuantityModal())


class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="🔒 Fermer",
            style=discord.ButtonStyle.danger
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.channel.delete()


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(QuantityButton())
        self.add_item(CloseButton())


# ===============================
# COMMANDE SHOP (TikTok uniquement)
# ===============================

@bot.command()
@commands.has_permissions(administrator=True)
async def shop(ctx):

    embed = discord.Embed(
        title="🚀 TikTok Boost Premium",
        description=(
            "🎬 **Services TikTok disponibles :**\n\n"
            "• TikTok Followers\n"
            "• TikTok Likes\n"
            "• TikTok Views\n\n"
            "💎 Engagement premium\n"
            "⚡ Livraison rapide\n"
            "🔒 Paiement sécurisé\n"
            "📊 Résultats garantis\n\n"
            "Clique sur le bouton ci-dessous pour ouvrir un ticket."
        ),
        color=discord.Color.dark_gray()
    )

    embed.set_image(url=BANNER_URL)

    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="🎬 Ouvrir un ticket TikTok",
            style=discord.ButtonStyle.success,
            custom_id="open_ticket"
        )
    )

    async def open_ticket_callback(interaction: discord.Interaction):
        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}"
        )

        ticket_embed = discord.Embed(
            title="🛒 Nouvelle Commande TikTok",
            description=(
                f"👤 {interaction.user.mention}\n\n"
                "💎 Premium\n"
                "⚡ Rapide\n"
                "🔒 Sécurisé\n\n"
                "Clique sur **Entrer la quantité** pour continuer."
            ),
            color=discord.Color.dark_gray()
        )

        ticket_embed.set_image(url=BANNER_URL)

        await channel.send(embed=ticket_embed, view=TicketView())

        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )

    view.children[0].callback = open_ticket_callback

    await ctx.send(embed=embed, view=view)


@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")


bot.run(TOKEN)
