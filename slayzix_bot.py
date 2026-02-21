import discord
from discord.ext import commands
import os
import json

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

STAFF_ROLES = ["Manager", "Founders"]
DATA_FILE = "ticket_data.json"

# ===============================
# SAUVEGARDE COMPTEUR
# ===============================

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"counter": 0}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ===============================
# VIEW TICKET
# ===============================

class TicketView(discord.ui.View):
    def __init__(self, creator_id):
        super().__init__(timeout=None)
        self.claimed_by = None
        self.creator_id = creator_id

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
                f"❌ Déjà réclamé par {self.claimed_by.mention}.",
                ephemeral=True
            )
            return

        self.claimed_by = interaction.user
        button.disabled = True
        button.label = f"✅ Réclamé par {interaction.user.name}"

        # 🔒 Retire l'écriture aux autres staff
        for role_name in STAFF_ROLES:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                await interaction.channel.set_permissions(
                    role,
                    send_messages=False
                )

        # ✅ Donne écriture uniquement au staff qui claim
        await interaction.channel.set_permissions(
            interaction.user,
            send_messages=True
        )

        # ✅ Créateur garde l'écriture
        creator = interaction.guild.get_member(self.creator_id)
        if creator:
            await interaction.channel.set_permissions(
                creator,
                send_messages=True
            )

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

        # 🔢 Incrémente compteur permanent
        data["counter"] += 1
        save_data(data)

        ticket_number = data["counter"]

        guild = interaction.guild
        user = interaction.user

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        # Ajoute accès staff
        for role_name in STAFF_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True
                )

        channel = await guild.create_text_channel(
            name=f"ticket-{ticket_number:03}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"🎫 Ticket #{ticket_number:03}",
            description="Merci d’indiquer ce que tu souhaites commander.",
            color=discord.Color.green()
        )

        await channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=TicketView(user.id)
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
    print(f"✅ Connecté en tant que {bot.user}")

# ===============================

bot.run(TOKEN)
