import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================
# VIEW DU SHOP
# ==============================

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📱 Réseaux sociaux", style=discord.ButtonStyle.primary)
    async def social_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        user = interaction.user

        # Vérifie si ticket existe déjà
        existing = discord.utils.get(guild.channels, name=f"ticket-{user.name}")
        if existing:
            await interaction.response.send_message(
                "❌ Tu as déjà un ticket ouvert.",
                ephemeral=True
            )
            return

        # Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="📱 TIKTOK / INSTAGRAM SERVICES",
            description="""
👥 **Followers**
➤ 1 000 Followers TikTok — 2.50€
➤ 1 000 Followers Instagram — 5€
➤ 10 000 Followers TikTok — 25€
➤ 10 000 Followers Instagram — 50€

━━━━━━━━━━━━━━━━━━━━

👀 **Views (TikTok uniquement)**
➤ 1 000 Views — 0.15€
➤ 10 000 Views — 1.50€

━━━━━━━━━━━━━━━━━━━━

❤️ **Likes (TikTok uniquement)**
➤ 1 000 Likes — 1€
➤ 10 000 Likes — 10€

━━━━━━━━━━━━━━━━━━━━

💳 Paiement : Paypal  
⏳ Prix susceptibles d’évoluer  
⚡ Powered by Slayzix's Shop
""",
            color=discord.Color.green()
        )

        await channel.send(f"{user.mention}", embed=embed)
        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )

# ==============================
# EVENT READY
# ==============================

@bot.event
async def on_ready():
    bot.add_view(ShopView())
    print(f"✅ Connecté en tant que {bot.user}")

# ==============================
# COMMANDE SHOP
# ==============================

@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="🛒 Boutique Slayzix",
        description="Clique sur le bouton ci-dessous pour ouvrir un ticket.",
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=ShopView())

# ==============================

bot.run(TOKEN)
