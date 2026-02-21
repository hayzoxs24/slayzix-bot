import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= PRIX =================

TIKTOK_PRICES = {
    "Followers": 3.5,   # prix pour 1000
    "Likes": 2.5,       # prix pour 1000
    "Views": 1.5        # prix pour 1000
}

DISCORD_PRICES = {
    "Membres en ligne": 4.5,      # prix pour 1000
    "Membres hors-ligne": 4,      # prix pour 1000
    "Boost x14": 3,               # prix unité
    "Nitro 1 mois": 3.5           # prix unité
}

DECORATION_PRICES = {
    4.99: 1.75,
    5.99: 2.39,
    6.99: 2.55,
    7.99: 2.91,
    8.49: 3.25,
    9.99: 3.60,
    11.99: 3.95
}

# ================= TICKET =================

async def create_ticket(interaction, title, description):
    guild = interaction.guild
    user = interaction.user

    # Anti double ticket
    existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
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
        name=f"ticket-{user.name}",
        overwrites=overwrites,
        category=category
    )

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Slayzix Shop")

    await channel.send(f"{user.mention}", embed=embed)
    await interaction.response.send_message("✅ Ticket créé !", ephemeral=True)

# ================= MODAL =================

class QuantityModal(discord.ui.Modal):

    def __init__(self, service, platform):
        super().__init__(title="Commande")
        self.service = service
        self.platform = platform

        self.quantity = discord.ui.TextInput(
            label="Quantité (ou prix original decoration)",
            required=True
        )

        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):

        try:
            value = float(self.quantity.value)

            # ================= TIKTOK =================
            if self.platform == "tiktok":
                qty = int(value)

                if qty < 1000 or qty % 1000 != 0:
                    return await interaction.response.send_message(
                        "❌ Minimum 1000 et multiple de 1000.",
                        ephemeral=True
                    )

                price = (qty / 1000) * TIKTOK_PRICES[self.service]

            # ================= DISCORD =================
            else:

                # Membres
                if "Membres" in self.service:
                    qty = int(value)

                    if qty < 1000 or qty % 1000 != 0:
                        return await interaction.response.send_message(
                            "❌ Minimum 1000 et multiple de 1000.",
                            ephemeral=True
                        )

                    price = (qty / 1000) * DISCORD_PRICES[self.service]

                # Boost / Nitro
                elif self.service in ["Boost x14", "Nitro 1 mois"]:
                    qty = int(value)
                    price = qty * DISCORD_PRICES[self.service]

                # Decoration
                else:
                    original_price = float(value)

                    if original_price not in DECORATION_PRICES:
                        return await interaction.response.send_message(
                            "❌ Prix invalide (ex: 4.99, 5.99...).",
                            ephemeral=True
                        )

                    qty = 1
                    price = DECORATION_PRICES[original_price]

        except:
            return await interaction.response.send_message(
                "❌ Valeur invalide.",
                ephemeral=True
            )

        await create_ticket(
            interaction,
            "🎫 Facture",
            f"📦 Service : **{self.service}**\n"
            f"🔢 Quantité : **{qty}**\n"
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
                discord.SelectOption(label="Profile Decoration", emoji="🎨"),
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

    embed.set_footer(text="Slayzix Shop • TikTok Services")

    await ctx.send(embed=embed, view=ServiceView("tiktok"))

@bot.command()
async def discordpanel(ctx):

    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — Discord Services",
        description=(
            "👥 Membres haute qualité\n"
            "🚀 Boost rapides\n"
            "🎁 Nitro instantané\n"
            "🎨 Profile Decorations\n\n"
            "⚡ Livraison rapide\n"
            "🔒 Paiement sécurisé\n"
            "💬 Support actif\n\n"
            "👇 Sélectionne ton service"
        ),
        color=discord.Color.blurple()
    )

    embed.set_footer(text="Slayzix Shop • Discord Services")

    await ctx.send(embed=embed, view=ServiceView("discord"))

# ================= START =================

if __name__ == "__main__":
    import os
    TOKEN = os.getenv("TOKEN")
    
    if not TOKEN:
        print("❌ TOKEN manquant dans les variables d'environnement.")
    else:
        bot.run(TOKEN)
