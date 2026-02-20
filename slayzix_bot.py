import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import asyncio

# ============================================================
#   ⚙️  CONFIG — Remplace ces valeurs par les tiennes
# ============================================================
TOKEN          = "MTQ2NTA1NzE3OTg0ODY3MTM4Mw.GHe67x.Z5hJz4YeYS03AMsC8qc7yX-Z2HNvh5s9DryqrM"
CHANNEL_ID     = 1474164824660377772  # ID du channel où envoyer l'embed
CATEGORY_ID    = 1457482620249309390  # ID de la catégorie pour les tickets
STAFF_ROLE_ID  = 1256671391575703623  # ID du rôle staff/admin qui voit les tickets
# ============================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ─────────────────────────────────────────────
#   VUE : Bouton "Fermer le ticket"
# ─────────────────────────────────────────────
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("⏳ Fermeture du ticket dans 5 secondes...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket fermé par {interaction.user}")


# ─────────────────────────────────────────────
#   VUE : Menu de sélection du service
# ─────────────────────────────────────────────
class ServiceSelect(View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    @discord.ui.select(
        placeholder="🛒 Choisis ton service...",
        custom_id="service_select",
        options=[
            discord.SelectOption(label="1 000 Followers TikTok",    description="2,50€ — PayPal", emoji="🎵"),
            discord.SelectOption(label="10 000 Followers TikTok",   description="25,00€ — PayPal", emoji="🎵"),
            discord.SelectOption(label="1 000 Followers Instagram",  description="5,00€ — PayPal", emoji="📸"),
            discord.SelectOption(label="10 000 Followers Instagram", description="50,00€ — PayPal", emoji="📸"),
            discord.SelectOption(label="1 000 Views TikTok",        description="0,15€ — PayPal", emoji="👁️"),
            discord.SelectOption(label="10 000 Views TikTok",       description="1,50€ — PayPal", emoji="👁️"),
            discord.SelectOption(label="1 000 Likes TikTok",        description="1,00€ — PayPal", emoji="❤️"),
            discord.SelectOption(label="10 000 Likes TikTok",       description="10,00€ — PayPal", emoji="❤️"),
        ]
    )
    async def select_service(self, interaction: discord.Interaction, select: Select):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Ce menu ne t'appartient pas.", ephemeral=True)
            return

        service = select.values[0]
        guild   = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        staff_role = guild.get_role(STAFF_ROLE_ID)

        # Création du channel ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user:   discord.PermissionOverwrite(read_messages=True, send_messages=True),
            staff_role:         discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me:           discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket de {interaction.user} | Service : {service}"
        )

        # Embed dans le ticket
        embed = discord.Embed(
            title="🎟️ Nouveau Ticket",
            description=(
                f"Bienvenue {interaction.user.mention} !\n\n"
                f"**Service commandé :**\n> {service}\n\n"
                f"Un membre du staff va te répondre très bientôt.\n"
                f"Donne ton **lien de profil** et on s'occupe du reste !"
            ),
            color=0x00f5ff
        )
        embed.set_footer(text="Slayzix's Shop • Powered by ⚡")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await ticket_channel.send(
            content=f"{interaction.user.mention} | {staff_role.mention}",
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ton ticket a été créé : {ticket_channel.mention}",
            ephemeral=True
        )
        self.stop()


# ─────────────────────────────────────────────
#   VUE : Bouton principal "Commander"
# ─────────────────────────────────────────────
class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟️ Commander", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        # Vérifie si l'user a déjà un ticket ouvert
        guild = interaction.guild
        for channel in guild.text_channels:
            if channel.name == f"ticket-{interaction.user.name}":
                await interaction.response.send_message(
                    f"❌ Tu as déjà un ticket ouvert : {channel.mention}",
                    ephemeral=True
                )
                return

        embed = discord.Embed(
            title="🛒 Slayzix's Shop — Choix du service",
            description="Sélectionne le service que tu veux commander dans le menu ci-dessous.",
            color=0x00f5ff
        )

        await interaction.response.send_message(
            embed=embed,
            view=ServiceSelect(interaction.user),
            ephemeral=True
        )


# ─────────────────────────────────────────────
#   COMMANDE : !shop  →  envoie l'embed
# ─────────────────────────────────────────────
@bot.command()
@commands.has_permissions(administrator=True)
async def shop(ctx):
    """Envoie l'embed de la boutique dans le channel configuré."""
    channel = bot.get_channel(CHANNEL_ID)

    embed = discord.Embed(
        title="⚡ Slayzix's Shop",
        description=(
            "**Services TikTok & Instagram**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "👥 **FOLLOWERS**\n"
            "> 🎵 1 000 Followers TikTok — **2,50€**\n"
            "> 🎵 10 000 Followers TikTok — **25,00€**\n"
            "> 📸 1 000 Followers Instagram — **5,00€**\n"
            "> 📸 10 000 Followers Instagram — **50,00€**\n\n"
            "👁️ **VIEWS** *(TikTok only)*\n"
            "> 1 000 Views — **0,15€**\n"
            "> 10 000 Views — **1,50€**\n\n"
            "❤️ **LIKES** *(TikTok only)*\n"
            "> 1 000 Likes — **1,00€**\n"
            "> 10 000 Likes — **10,00€**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💳 Paiement : **PayPal** uniquement\n"
            "*Prix susceptibles d'évoluer selon la demande.*"
        ),
        color=0x00f5ff
    )
    embed.set_footer(text="Slayzix's Shop • Clique sur Commander pour ouvrir un ticket ⚡")

    await channel.send(embed=embed, view=ShopView())
    await ctx.message.delete()
    await ctx.send("✅ Embed envoyé !", delete_after=3)


# ─────────────────────────────────────────────
#   EVENTS
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    # Réenregistre les vues persistantes au redémarrage
    bot.add_view(ShopView())
    bot.add_view(CloseTicketView())
    print(f"✅ Bot connecté en tant que {bot.user}")
    print(f"   Serveurs : {len(bot.guilds)}")


bot.run(TOKEN)
