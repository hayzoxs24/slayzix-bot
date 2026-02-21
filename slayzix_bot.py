import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

STAFF_ROLES = ["Manager", "Founders"]

ticket_counter = 0

# ===============================
# VIEW TICKET
# ===============================

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.claimed_by = None

    @discord.ui.button(label="🔔 Réclamer", style=discord.ButtonStyle.success)
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role.name in STAFF_ROLES for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Seuls les Managers ou Founders peuvent réclamer.",
                ephemeral=True
            )
            return

        if self.claimed_by:
            await interaction.response.send_message(
                f"❌ Ticket déjà réclamé par {self.claimed_by.mention}.",
                ephemeral=True
            )
            return

        self.claimed_by = interaction.user
        button.disabled = True
        button.label = f"✅ Réclamé par {interaction.user.name}"

        await interaction.message.edit(view=self)

        await interaction.response.send_message(
            f"🔔 {interaction.user.mention} a pris en charge le ticket."
        )

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role.name in STAFF_ROLES for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Seuls les Managers ou Founders peuvent fermer.",
                ephemeral=True
            )
            return

        await interaction.response.send_message("🔒 Fermeture du ticket...")
        await interaction.channel.delete()

# ===============================
# VIEW SHOP
# ===============================

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🌐 Réseaux Sociaux", style=discord.ButtonStyle.danger)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        global ticket_counter
        ticket_counter += 1

        guild = interaction.guild
        user = interaction.user

        # Vérifie si l'utilisateur a déjà un ticket
        for channel in guild.text_channels:
            if channel.name.startswith("ticket-") and user in channel.members:
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

        # Ajoute permissions Manager & Founders
        for role_name in STAFF_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )

        channel = await guild.create_text_channel(
            name=f"ticket-{ticket_counter:03}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"🎫 Ticket #{ticket_counter:03}",
            description="Merci d’indiquer ce que tu souhaites commander.",
            color=discord.Color.green()
        )

        await channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=TicketView()
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

➤ 1 000 Followers TikTok — **2.50€**
➤ 1 000 Followers Instagram — **5€**
➤ 10 000 Followers TikTok — **25€**
➤ 10 000 Followers Instagram — **50€**

━━━━━━━━━━━━━━━━━━━━

👀 **Views (TikTok uniquement)**

➤ 1 000 Views — **0.15€**
➤ 10 000 Views — **1.50€**

━━━━━━━━━━━━━━━━━━━━

❤️ **Likes (TikTok uniquement)**

➤ 1 000 Likes — **1€**
➤ 10 000 Likes — **10€**

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
    bot.add_view(TicketView())
    print(f"✅ Connecté en tant que {bot.user}")

# ===============================

bot.run(TOKEN)
