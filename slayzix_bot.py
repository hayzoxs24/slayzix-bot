import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import os

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")

BANNER_URL = "https://cdn.discordapp.com/attachments/1462275672503357705/1474580179153326332/IMG_6798.png"

PAYPAL_HAYZOXS = "https://paypal.me/HAYZOXS"
PAYPAL_SLAYZIX = "https://paypal.me/SLAYZIXbetter"

PRICES_TIKTOK = {
    "Followers": 2,
    "Likes": 1.5,
    "Views": 1
}

DISCORD_PRICES = {
    "1000 Membres en ligne": 4.5,
    "1000 Membres hors-ligne": 4,
    "Boost Serveur x14": 3,
    "Nitro (1 mois)": 3.5,
    "Nitro Basique (1 mois)": 2,
}

# ================= INTENTS =================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =====================================================
# ================= TIKTOK SYSTEM =====================
# =====================================================

class TikTokSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Followers"),
            discord.SelectOption(label="Likes"),
            discord.SelectOption(label="Views"),
        ]

        super().__init__(
            placeholder="Choisis ton service TikTok...",
            options=options,
            custom_id="tiktok_select"
        )

    async def callback(self, interaction: discord.Interaction):
        service = self.values[0]
        await interaction.response.send_modal(TikTokQuantityModal(service))


class TikTokQuantityModal(discord.ui.Modal, title="Quantité (multiple de 1000)"):
    def __init__(self, service):
        super().__init__()
        self.service = service

        self.quantity = discord.ui.TextInput(
            label="Ex: 1000, 2000, 3000...",
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
                "❌ Nombre invalide.",
                ephemeral=True
            )

        price = (qty / 1000) * PRICES_TIKTOK[self.service]

        await create_ticket(
            interaction,
            f"TikTok • {self.service}",
            f"🎯 Service : {self.service}\n📦 Quantité : {qty}\n💰 Prix : {price}€"
        )


class TikTokView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TikTokSelect())


@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="💎 SLAYZIX SHOP — TikTok Boost",
        description=(
            "• Followers\n"
            "• Likes\n"
            "• Views\n\n"
            "Quantité libre (multiple de 1000)"
        ),
        color=discord.Color.purple()
    )
    embed.set_image(url=BANNER_URL)

    await ctx.send(embed=embed, view=TikTokView())

# =====================================================
# ================= DISCORD SYSTEM ====================
# =====================================================

class DiscordSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="1000 Membres en ligne"),
            discord.SelectOption(label="1000 Membres hors-ligne"),
            discord.SelectOption(label="Boost Serveur x14"),
            discord.SelectOption(label="Nitro (1 mois)"),
            discord.SelectOption(label="Nitro Basique (1 mois)"),
        ]

        super().__init__(
            placeholder="Choisis ton service Discord...",
            options=options,
            custom_id="discord_select"
        )

    async def callback(self, interaction: discord.Interaction):
        service = self.values[0]
        price = DISCORD_PRICES[service]

        await create_ticket(
            interaction,
            f"Discord • {service}",
            f"💬 Service : {service}\n💰 Prix : {price}€"
        )


class DiscordView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DiscordSelect())


@bot.command()
async def discord(ctx):
    embed = discord.Embed(
        title="💬 DISCORD SERVICES",
        description=(
            "👥 Membres Discord\n"
            "➤ 1 000 Membres en ligne — 4.50€\n"
            "➤ 1 000 Membres hors-ligne — 4€\n\n"
            "🚀 Boost Serveur x14 — 3€\n\n"
            "🎁 Nitro\n"
            "➤ Nitro (1 mois) — 3.50€\n"
            "➤ Nitro Basique (1 mois) — 2€"
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed, view=DiscordView())

# =====================================================
# ================= TICKET SYSTEM =====================
# =====================================================

async def create_ticket(interaction, title, description):
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
        title="🧾 Facture",
        description=description,
        color=discord.Color.green()
    )

    embed.set_footer(text="Paiement via PayPal")

    view = View(timeout=None)

    view.add_item(Button(label="💳 PayPal HayZoXs", style=discord.ButtonStyle.link, url=PAYPAL_HAYZOXS))
    view.add_item(Button(label="💳 PayPal Slayzix's", style=discord.ButtonStyle.link, url=PAYPAL_SLAYZIXbetter))

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close(inter, button):
        await inter.channel.delete()

    view.add_item(Button(label="🔒 Fermer", style=discord.ButtonStyle.danger, custom_id="close_ticket"))

    await channel.send(content=interaction.user.mention, embed=embed, view=view)

    await interaction.response.send_message(
        f"✅ Ticket créé : {channel.mention}",
        ephemeral=True
    )

# =====================================================

@bot.event
async def on_ready():
    bot.add_view(TikTokView())
    bot.add_view(DiscordView())
    print(f"✅ Connecté en tant que {bot.user}")

bot.run(TOKEN)
