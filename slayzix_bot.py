import discord
from discord.ext import commands
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= PRIX =================

TIKTOK_PRICES = {
    "Followers": 2.0,
    "Likes": 0.50,
    "Views": 0.20
}

DISCORD_PRICES = {
    "Membres en ligne": 4.5,
    "Membres hors-ligne": 4,
    "Boost x14": 3,
    "Nitro 1 mois": 3.5
}

# ================= BOUTON FERMETURE =================

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# ================= TICKET =================

async def create_ticket(interaction, title, description):
    guild = interaction.guild
    user = interaction.user

    existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.id}")
    if existing:
        return await interaction.response.send_message(
            "❌ Tu as déjà un ticket ouvert.",
            ephemeral=True
        )

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    category = discord.utils.get(guild.categories, name="TICKETS")
    if not category:
        category = await guild.create_category("TICKETS")

    channel = await guild.create_text_channel(
        name=f"ticket-{user.id}",
        overwrites=overwrites,
        category=category
    )

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Slayzix Shop")

    await channel.send(user.mention, embed=embed, view=CloseTicketView())
    await interaction.response.send_message("✅ Ticket créé !", ephemeral=True)

# ================= MODAL =================

class QuantityModal(discord.ui.Modal):

    def __init__(self, service, platform):
        super().__init__(title="Commande")
        self.service = service
        self.platform = platform

        self.quantity = discord.ui.TextInput(
            label="Quantité (multiple de 1000 si membres)",
            required=True
        )
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.quantity.value)

            # ===== TIKTOK =====
            if self.platform == "tiktok":
                if value < 1000 or value % 1000 != 0:
                    return await interaction.response.send_message(
                        "❌ Minimum 1000 et multiple de 1000.",
                        ephemeral=True
                    )
                price = (value / 1000) * TIKTOK_PRICES[self.service]

            # ===== DISCORD =====
            else:
                # 👥 Membres (multiple de 1000 obligatoire)
                if "Membres" in self.service:
                    if value < 1000 or value % 1000 != 0:
                        return await interaction.response.send_message(
                            "❌ Minimum 1000 et multiple de 1000.",
                            ephemeral=True
                        )
                    price = (value / 1000) * DISCORD_PRICES[self.service]

                # 🚀 Boost x14 & 🎁 Nitro (quantité libre)
                elif self.service in ["Boost x14", "Nitro 1 mois"]:
                    if value < 1:
                        return await interaction.response.send_message(
                            "❌ Quantité invalide.",
                            ephemeral=True
                        )
                    price = value * DISCORD_PRICES[self.service]

                else:
                    return await interaction.response.send_message(
                        "❌ Service inconnu.",
                        ephemeral=True
                    )

        except ValueError:
            return await interaction.response.send_message(
                "❌ Valeur invalide. Entre un nombre entier.",
                ephemeral=True
            )

        await create_ticket(
            interaction,
            "🎫 Facture",
            f"📦 Service : **{self.service}**\n"
            f"🔢 Quantité : **{value}**\n"
            f"💰 Prix : **{price:.2f}€**\n\n"
            f"💳 Paiement PayPal\n"
            f"⚡ Livraison rapide\n"
            f"💬 Merci de patienter"
        )

# ================= SELECT =================

class ServiceSelect(discord.ui.Select):

    def __init__(self, platform):

        if platform == "tiktok":
            options = [
                discord.SelectOption(label="Followers", emoji="🚀"),
                discord.SelectOption(label="Likes", emoji="❤️"),
                discord.SelectOption(label="Views", emoji="👀"),
            ]
        else:
            options = [
                discord.SelectOption(label="Membres en ligne", emoji="👥"),
                discord.SelectOption(label="Membres hors-ligne", emoji="👤"),
                discord.SelectOption(label="Boost x14", emoji="🚀"),
                discord.SelectOption(label="Nitro 1 mois", emoji="🎁"),
            ]

        super().__init__(
            placeholder="Choisis ton service",
            options=options
        )

        self.platform = platform

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            QuantityModal(self.values[0], self.platform)
        )

class ServiceView(discord.ui.View):
    def __init__(self, platform):
        super().__init__(timeout=None)
        self.add_item(ServiceSelect(platform))

# ================= COMMANDES =================

@bot.command()
async def tiktok(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — TikTok Boost",
        description=(
            "🚀 Followers haute qualité\n"
            "❤️ Likes instantanés\n"
            "👀 Views rapides\n\n"
            "⚡ Livraison en moins de 24h\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton service"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=ServiceView("tiktok"))

@bot.command()
async def discordpanel(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Discord Services",
        description=(
            "👥 Membres haute qualité\n"
            "🚀 Boosts rapides\n"
            "🎁 Nitro instantané\n\n"
            "⚡ Livraison rapide\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton service"
        ),
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=ServiceView("discord"))

# ================= START =================

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    bot.run(TOKEN)
