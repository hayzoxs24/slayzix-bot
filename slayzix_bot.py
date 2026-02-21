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
# SAVE SYSTEM
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
# TICKET VIEW
# ===============================

class TicketView(discord.ui.View):
    def __init__(self, creator_id):
        super().__init__(timeout=None)
        self.creator_id = creator_id
        self.claimed_by = None

    @discord.ui.button(label="🔔 Réclamer", style=discord.ButtonStyle.success)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role.name in STAFF_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)

        if self.claimed_by:
            return await interaction.response.send_message(
                f"❌ Déjà réclamé par {self.claimed_by.mention}.",
                ephemeral=True
            )

        self.claimed_by = interaction.user
        button.label = f"✅ {interaction.user.name}"
        button.disabled = True

        # Bloque écriture aux autres staff
        for role_name in STAFF_ROLES:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                await interaction.channel.set_permissions(role, send_messages=False)

        # Autorise staff qui claim
        await interaction.channel.set_permissions(interaction.user, send_messages=True)

        # Autorise créateur
        creator = interaction.guild.get_member(self.creator_id)
        if creator:
            await interaction.channel.set_permissions(creator, send_messages=True)

        await interaction.message.edit(view=self)
        await interaction.response.send_message(
            f"🔔 Ticket pris en charge par {interaction.user.mention}"
        )

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role.name in STAFF_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)

        await interaction.response.send_message("🔒 Fermeture...")
        await interaction.channel.delete()

# ===============================
# SERVICE SELECT MENU
# ===============================

class ServiceSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Followers TikTok", emoji="👥", description="Augmente tes abonnés TikTok"),
            discord.SelectOption(label="Followers Instagram", emoji="📸", description="Boost Instagram"),
            discord.SelectOption(label="Views TikTok", emoji="👀", description="Augmente tes vues"),
            discord.SelectOption(label="Likes TikTok", emoji="❤️", description="Boost tes likes"),
        ]

        super().__init__(
            placeholder="💎 Choisis ton service...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        data["counter"] += 1
        save_data(data)
        ticket_number = data["counter"]

        guild = interaction.guild
        user = interaction.user
        service = self.values[0]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        for role_name in STAFF_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{ticket_number:03}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"🎫 𝗧𝗜𝗖𝗞𝗘𝗧 #{ticket_number:03}",
            description=f"""
━━━━━━━━━━━━━━━━━━━━━━
👤 Client : {user.mention}

🛒 Service choisi :
> **{service}**

💬 Indique la quantité souhaitée.

⏳ Temps moyen : 5-15 min
━━━━━━━━━━━━━━━━━━━━━━
""",
            color=0x00ff99
        )

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Slayzix Premium Support")

        await channel.send(
            content=user.mention,
            embed=embed,
            view=TicketView(user.id)
        )

        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}",
            ephemeral=True
        )

class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ServiceSelect())

# ===============================
# SHOP COMMAND
# ===============================

@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="💎 𝗦𝗟𝗔𝗬𝗭𝗜𝗫 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗦𝗛𝗢𝗣",
        description="""
━━━━━━━━━━━━━━━━━━━━━━
✨ Boost Réseaux Sociaux ✨
━━━━━━━━━━━━━━━━━━━━━━

👥 Followers  
👀 Views  
❤️ Likes  

💳 Paiement : Paypal

Clique ci-dessous pour commander.
""",
        color=0x2b2d31
    )

    embed.set_image(url="https://media.giphy.com/media/3o7TKz8G1pRz3yHqRa/giphy.gif")
    embed.set_footer(text="Powered by Slayzix")

    await ctx.send(embed=embed, view=ShopView())

# ===============================

@bot.event
async def on_ready():
    bot.add_view(ShopView())
    print(f"✅ Connecté en tant que {bot.user}")

bot.run(TOKEN)
