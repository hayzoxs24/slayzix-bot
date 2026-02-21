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

PRICES = {
    "Followers TikTok": 2.50,
    "Views TikTok": 0.15,
    "Likes TikTok": 1.00,
}

bot.active_tickets = {}

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

        # Bloque écriture autres staff
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
        bot.active_tickets.pop(interaction.channel.id, None)
        await interaction.channel.delete()

# ===============================
# SELECT MENU
# ===============================

class ServiceSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Followers TikTok", emoji="👥"),
            discord.SelectOption(label="Views TikTok", emoji="👀"),
            discord.SelectOption(label="Likes TikTok", emoji="❤️"),
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

        bot.active_tickets[channel.id] = {
            "service": service,
            "user_id": user.id
        }

        embed = discord.Embed(
            title=f"🎫 TICKET #{ticket_number:03}",
            description=f"""
━━━━━━━━━━━━━━━━━━━━━━
👤 Client : {user.mention}
🛒 Service : **{service}**

✍️ Écris la quantité souhaitée.
(ex: 5000)
━━━━━━━━━━━━━━━━━━━━━━
""",
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Slayzix Premium System")

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
# AUTO INVOICE SYSTEM
# ===============================

@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id in bot.active_tickets:

        ticket_data = bot.active_tickets[message.channel.id]
        service = ticket_data["service"]

        if message.content.isdigit():

            quantity = int(message.content)

            if quantity < 100:
                await message.channel.send("❌ Minimum 100.")
                return

            price_per_1000 = PRICES[service]
            total_price = round((quantity / 1000) * price_per_1000, 2)

            # 🎨 Dégradé dynamique
            r = (quantity * 3) % 255
            g = (quantity * 7) % 255
            b = (quantity * 11) % 255

            invoice = discord.Embed(
                title="🧾 FACTURE AUTOMATIQUE",
                description=f"""
━━━━━━━━━━━━━━━━━━━━━━
🛒 Service : **{service}**
📦 Quantité : **{quantity}**
💰 Total : **{total_price}€**
━━━━━━━━━━━━━━━━━━━━━━
""",
                color=discord.Color.from_rgb(r, g, b)
            )

            invoice.set_footer(text="Slayzix Premium Billing")

            await message.channel.send(embed=invoice)

    await bot.process_commands(message)

# ===============================
# SHOP COMMAND
# ===============================

@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="💎 SLAYZIX PREMIUM SHOP",
        description="""
━━━━━━━━━━━━━━━━━━━━━━
👥 Followers TikTok  
👀 Views TikTok  
❤️ Likes TikTok  

💳 Paiement : Paypal

Sélectionne ton service ci-dessous.
━━━━━━━━━━━━━━━━━━━━━━
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
