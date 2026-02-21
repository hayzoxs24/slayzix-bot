import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===============================
# CONFIG
# ===============================

CATEGORY_NAME = "🎫 TICKETS"
STAFF_ROLE_NAME = "Staff"  # crée un rôle Staff si pas déjà fait

# ===============================
# VIEW FERMER TICKET
# ===============================

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fermeture du ticket...", ephemeral=True)
        await interaction.channel.delete()

# ===============================
# VIEW SHOP
# ===============================

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📱 Réseaux Sociaux", style=discord.ButtonStyle.primary)
    async def social_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        user = interaction.user

        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        if not category:
            await interaction.response.send_message(
                "❌ Catégorie TICKETS introuvable.",
                ephemeral=True
            )
            return

        existing = discord.utils.get(guild.channels, name=f"ticket-{user.id}")
        if existing:
            await interaction.response.send_message(
                "❌ Tu as déjà un ticket ouvert.",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{user.id}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="📱 TIKTOK / INSTAGRAM SERVICES",
            description="Bienvenue dans ton ticket.\nUn membre du staff va te répondre rapidement.",
            color=discord.Color.green()
        )

        embed.add_field(
            name="👥 Followers",
            value=(
                "➤ 1 000 TikTok — **2.50€**\n"
                "➤ 1 000 Instagram — **5€**\n"
                "➤ 10 000 TikTok — **25€**\n"
                "➤ 10 000 Instagram — **50€**"
            ),
            inline=False
        )

        embed.add_field(
            name="👀 Views (TikTok)",
            value=(
                "➤ 1 000 Views — **0.15€**\n"
                "➤ 10 000 Views — **1.50€**"
            ),
            inline=False
        )

        embed.add_field(
            name="❤️ Likes (TikTok)",
            value=(
                "➤ 1 000 Likes — **1€**\n"
                "➤ 10 000 Likes — **10€**"
            ),
            inline=False
        )

        embed.set_footer(text="💳 Paiement : Paypal • Powered by Slayzix's Shop")

        await channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )

# ===============================
# READY
# ===============================

@bot.event
async def on_ready():
    bot.add_view(ShopView())
    bot.add_view(CloseTicketView())
    print(f"✅ Connecté en tant que {bot.user}")

# ===============================
# COMMANDE SHOP
# ===============================

@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="🛒 Slayzix's Shop",
        description="Clique sur le bouton ci-dessous pour commander nos services.",
        color=discord.Color.blurple()
    )

    embed.set_footer(text="Services rapides • Paiement sécurisé")

    await ctx.send(embed=embed, view=ShopView())

# ===============================

bot.run(TOKEN)
