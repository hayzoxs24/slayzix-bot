import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import asyncio

# ================= CONFIG =================
CHANNEL_ID = 1474164824660377772
CATEGORY_ID = 1457482620249309390
STAFF_ROLE_ID = 1256671391575703623
# ==========================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ─────────────────────────────────────────
#   BOUTON FERMER TICKET
# ─────────────────────────────────────────
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("⏳ Fermeture dans 5 secondes...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()


# ─────────────────────────────────────────
#   MENU SELECTION SERVICE
# ─────────────────────────────────────────
class ServiceSelect(View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    @discord.ui.select(
        placeholder="🛒 Choisis ton service...",
        custom_id="service_select",
        options=[
            discord.SelectOption(label="1 000 Followers TikTok", description="2,50€ — PayPal", emoji="🎵"),
            discord.SelectOption(label="10 000 Followers TikTok", description="25,00€ — PayPal", emoji="🎵"),
            discord.SelectOption(label="1 000 Followers Instagram", description="5,00€ — PayPal", emoji="📸"),
            discord.SelectOption(label="10 000 Followers Instagram", description="50,00€ — PayPal", emoji="📸"),
        ]
    )
    async def select_service(self, interaction: discord.Interaction, select: Select):

        if interaction.user != self.user:
            await interaction.response.send_message("❌ Ce menu ne t'appartient pas.", ephemeral=True)
            return

        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        staff_role = guild.get_role(STAFF_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎟️ Nouveau Ticket",
            description=f"Service choisi : **{select.values[0]}**\nUn membre du staff va te répondre.",
            color=0x00f5ff
        )

        await channel.send(
            content=f"{interaction.user.mention} | {staff_role.mention}",
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )

        self.stop()


# ─────────────────────────────────────────
#   BOUTON OUVRIR TICKET
# ─────────────────────────────────────────
class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟️ Commander", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):

        for channel in interaction.guild.text_channels:
            if channel.name == f"ticket-{interaction.user.name}":
                await interaction.response.send_message(
                    f"❌ Tu as déjà un ticket : {channel.mention}",
                    ephemeral=True
                )
                return

        embed = discord.Embed(
            title="🛒 Slayzix Shop",
            description="Choisis ton service dans le menu ci-dessous.",
            color=0x00f5ff
        )

        await interaction.response.send_message(
            embed=embed,
            view=ServiceSelect(interaction.user),
            ephemeral=True
        )


# ─────────────────────────────────────────
#   COMMANDE !shop
# ─────────────────────────────────────────
@bot.command()
@commands.has_permissions(administrator=True)
async def shop(ctx):

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        await ctx.send("❌ CHANNEL_ID incorrect.")
        return

    embed = discord.Embed(
        title="⚡ Slayzix Shop",
        description="Clique sur le bouton pour commander.",
        color=0x00f5ff
    )

    await channel.send(embed=embed, view=ShopView())
    await ctx.message.delete()


# ─────────────────────────────────────────
#   READY EVENT
# ─────────────────────────────────────────
@bot.event
async def on_ready():
    bot.add_view(ShopView())
    bot.add_view(CloseTicketView())
    print(f"✅ Connecté en tant que {bot.user}")


# ─────────────────────────────────────────
#   TOKEN (NE JAMAIS METTRE EN DUR)
# ─────────────────────────────────────────
TOKEN = os.environ.get("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN manquant dans Railway Variables")

bot.run(TOKEN)
