import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import asyncio

TOKEN = "TON_TOKEN_ICI"
BANNER_URL = "https://cdn.discordapp.com/attachments/1462275672503357705/1474580179153326332/IMG_6798.png?ex=699a5d4f&is=69990bcf&hm=b52804eedcfcc25698865a8b59a9d7ade23366dc0ad6cd90dda04679a38ebd53&"

PRICES = {
    "Followers": 2,
    "Likes": 1.5,
    "Views": 1
}

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


# =========================
# MENU SERVICE PRINCIPAL
# =========================

class ServiceSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Followers", description="Boost tes abonnés TikTok 🚀"),
            discord.SelectOption(label="Likes", description="Augmente les likes ❤️"),
            discord.SelectOption(label="Views", description="Augmente les vues 👀"),
        ]

        super().__init__(
            placeholder="Choisis ton service TikTok...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="service_select"
        )

    async def callback(self, interaction: discord.Interaction):
        service = self.values[0]
        await interaction.response.send_modal(QuantityModal(service))


# =========================
# MODAL QUANTITÉ
# =========================

class QuantityModal(discord.ui.Modal, title="Choisis la quantité (multiple de 1000)"):
    def __init__(self, service):
        super().__init__()
        self.service = service

        self.quantity = discord.ui.TextInput(
            label="Quantité (1000, 2000, 3000...)",
            placeholder="Ex: 3000",
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
                "❌ Entre un nombre valide.",
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
                f"🎯 **Service :** {self.service}\n"
                f"📦 **Quantité :** {qty}\n"
                f"💰 **Prix :** {price}€\n\n"
                f"⚡ Livraison rapide\n"
                f"🔒 Service sécurisé\n"
                f"📈 Boost TikTok Premium"
            ),
            color=discord.Color.purple()
        )

        embed.set_image(url=BANNER_URL)
        embed.set_footer(text="Slayzix Shop • TikTok Services")

        await channel.send(content=interaction.user.mention, embed=embed, view=CloseView())
        await interaction.response.send_message(f"✅ Ticket créé : {channel.mention}", ephemeral=True)


# =========================
# BOUTON FERMER DIRECT
# =========================

class CloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(Button(
            label="🔒 Fermer la commande",
            style=discord.ButtonStyle.danger,
            custom_id="close_ticket"
        ))

    @discord.ui.button(label="🔒 Fermer la commande", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()


# =========================
# VIEW PRINCIPALE
# =========================

class MainView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ServiceSelect())


# =========================
# COMMANDE SHOP
# =========================

@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — TikTok Services",
        description=(
            "🚀 **Boost Premium TikTok**\n\n"
            "• Followers réels & rapides\n"
            "• Likes instantanés\n"
            "• Views haute qualité\n\n"
            "📦 Quantité libre (multiple de 1000)\n"
            "⚡ Livraison rapide\n"
            "🔒 100% sécurisé\n\n"
            "👇 Sélectionne ton service ci-dessous"
        ),
        color=discord.Color.purple()
    )

    embed.set_image(url=BANNER_URL)

    await ctx.send(embed=embed, view=MainView())


# =========================

@bot.event
async def on_ready():
    bot.add_view(MainView())
    bot.add_view(CloseView())
    print(f"✅ Connecté en tant que {bot.user}")

bot.run(TOKEN)
