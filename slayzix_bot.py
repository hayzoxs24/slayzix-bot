import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

STAFF_ROLE_NAME = "Staff"  # facultatif

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
# VIEW SHOP (BOUTON)
# ===============================

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🌐 Réseaux Sociaux", style=discord.ButtonStyle.danger)
    async def social_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        user = interaction.user
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

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
            overwrites=overwrites
        )

        await channel.send(
            f"{user.mention} 🎫 Merci d’indiquer ce que tu souhaites commander.",
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )

# ===============================
# COMMANDE SHOP
# ===============================

@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="📱 TIKTOK / INSTAGRAM SERVICES",
        color=discord.Color.dark_theme()
    )

    embed.description = """
👥 **Followers**

➤ 1 000 Followers TikTok  
Prix : **2.50€**  
Paiement : Paypal  

➤ 1 000 Followers Instagram  
Prix : **5€**  
Paiement : Paypal  

➤ 10 000 Followers TikTok  
Prix : **25€**  
Paiement : Paypal  

➤ 10 000 Followers Instagram  
Prix : **50€**  
Paiement : Paypal  

━━━━━━━━━━━━━━━━━━━━  

👀 **Views (TikTok uniquement)**  

➤ 1 000 Views  
Prix : **0.15€**  

➤ 10 000 Views  
Prix : **1.50€**  

━━━━━━━━━━━━━━━━━━━━  

❤️ **Likes (TikTok uniquement)**  

➤ 1 000 Likes  
Prix : **1€**  

➤ 10 000 Likes  
Prix : **10€**  

━━━━━━━━━━━━━━━━━━━━  

Commande rapide en ticket.  
Prix susceptibles d’évoluer selon la demande. ⏳  

Powered by Slayzix's Shop
"""

    await ctx.send(embed=embed, view=ShopView())

# ===============================
# READY
# ===============================

@bot.event
async def on_ready():
    bot.add_view(ShopView())
    bot.add_view(CloseTicketView())
    print(f"✅ Connecté en tant que {bot.user}")

# ===============================

bot.run(TOKEN)
