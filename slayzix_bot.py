import discord
from discord.ext import commands
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= CONFIG =================

vouch_channel_id = None
vouch_role_id = None

# ================= SETUP VOUCH CHANNEL =================

class VouchChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Choisis le salon des avis",
            channel_types=[discord.ChannelType.text]
        )

    async def callback(self, interaction: discord.Interaction):
        global vouch_channel_id
        vouch_channel_id = self.values[0].id
        await interaction.response.send_message(
            f"✅ Salon des avis défini sur {self.values[0].mention} !",
            ephemeral=True
        )

class VouchSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VouchChannelSelect())

@bot.command()
@commands.has_permissions(administrator=True)
async def setvouchchannel(ctx):
    embed = discord.Embed(
        title="⚙️ Configuration — Salon des avis",
        description="Sélectionne le salon où les avis seront postés.",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=VouchSetupView())

# ================= SETUP VOUCH ROLE =================

class VouchRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="Choisis le rôle à attribuer après un vouch"
        )

    async def callback(self, interaction: discord.Interaction):
        global vouch_role_id
        vouch_role_id = self.values[0].id
        await interaction.response.send_message(
            f"✅ Rôle vouch défini sur {self.values[0].mention} !",
            ephemeral=True
        )

class VouchRoleSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VouchRoleSelect())

@bot.command()
@commands.has_permissions(administrator=True)
async def setvouchrole(ctx):
    embed = discord.Embed(
        title="⚙️ Configuration — Rôle Vouch",
        description="Sélectionne le rôle qui sera attribué automatiquement après un vouch.",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=VouchRoleSetupView())

# ================= VOUCH SLASH COMMAND =================

@bot.tree.command(name="vouch", description="Laisse un avis sur le shop !")
@discord.app_commands.describe(
    note="Ta note sur 5",
    service="Le service acheté",
    commentaire="Ton commentaire"
)
@discord.app_commands.choices(note=[
    discord.app_commands.Choice(name="⭐ 1/5", value=1),
    discord.app_commands.Choice(name="⭐⭐ 2/5", value=2),
    discord.app_commands.Choice(name="⭐⭐⭐ 3/5", value=3),
    discord.app_commands.Choice(name="⭐⭐⭐⭐ 4/5", value=4),
    discord.app_commands.Choice(name="⭐⭐⭐⭐⭐ 5/5", value=5),
])
async def vouch(interaction: discord.Interaction, note: int, service: str, commentaire: str):
    stars = "⭐" * note + "🌑" * (5 - note)

    colors = {
        1: discord.Color.red(),
        2: discord.Color.orange(),
        3: discord.Color.yellow(),
        4: discord.Color.green(),
        5: discord.Color.gold()
    }

    badges = {
        1: "😡 Très mauvais",
        2: "😕 Mauvais",
        3: "😐 Correct",
        4: "😊 Bien",
        5: "🤩 Excellent !"
    }

    embed = discord.Embed(
        title="📝 Nouvel Avis — Slayzix Shop",
        color=colors[note]
    )
    embed.add_field(name="👤 Client", value=interaction.user.mention, inline=True)
    embed.add_field(name="📦 Service", value=f"**{service}**", inline=True)
    embed.add_field(name="⭐ Note", value=f"{stars}  `{note}/5` — {badges[note]}", inline=False)
    embed.add_field(name="💬 Commentaire", value=f"*{commentaire}*", inline=False)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Slayzix Shop • Merci pour ton avis !")
    embed.timestamp = discord.utils.utcnow()

    role_added = False

    # Attribution du rôle vouch
    if vouch_role_id:
        role = interaction.guild.get_role(vouch_role_id)
        if role and role not in interaction.user.roles:
            try:
                await interaction.user.add_roles(role, reason="Vouch effectué")
                role_added = True
            except discord.Forbidden:
                pass

    # Post dans le salon vouch si défini
    if vouch_channel_id:
        channel = interaction.guild.get_channel(vouch_channel_id)
        if channel:
            await channel.send(embed=embed)

            response_msg = f"✅ Ton avis a été posté dans {channel.mention}, merci ! 🙏"
            if role_added:
                response_msg += f"\n🎖️ Le rôle **{role.name}** t'a été attribué !"

            await interaction.response.send_message(response_msg, ephemeral=True)
            return

    # Sinon on poste dans le salon courant
    await interaction.response.send_message(embed=embed)

    if role_added:
        await interaction.followup.send(
            f"🎖️ Le rôle **{role.name}** t'a été attribué pour ton vouch !",
            ephemeral=True
        )

# ================= EVENT ON_MESSAGE — Rôle si message dans salon vouch =================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Si le message est posté dans le salon vouch → donner le rôle
    if vouch_channel_id and vouch_role_id and message.channel.id == vouch_channel_id:
        role = message.guild.get_role(vouch_role_id)
        if role and role not in message.author.roles:
            try:
                await message.author.add_roles(role, reason="Message dans le salon vouch")
            except discord.Forbidden:
                pass

    await bot.process_commands(message)

# ================= ON READY =================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} connecté et slash commands synchronisées !")

# ================= START =================

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    bot.run(TOKEN)
