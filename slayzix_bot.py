import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3, time, re, random, json, os

TOKEN = os.environ.get("TOKEN")

COLOR = 0x5865F2

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ============================================================
# BASE DE DONNÉES
# ============================================================

db = sqlite3.connect("bot.db", check_same_thread=False)
cursor = db.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS sanctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    mod_id INTEGER,
    type TEXT,
    reason TEXT,
    date INTEGER
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    mod_id INTEGER,
    note TEXT,
    date INTEGER
);
CREATE TABLE IF NOT EXISTS whitelist (
    user_id INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS open_tickets (
    user_id INTEGER PRIMARY KEY,
    channel_id INTEGER
);
""")
db.commit()

def now(): return int(time.time())

def parse_duration(txt: str):
    m = re.match(r"(\d+)([smhd])", txt)
    if not m: return None
    return int(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]

# ============================================================
# ANTIRAID
# ============================================================

ANTIRAID = {
    "antibot": False,
    "antitoken": False,
    "antieveryone": False,
    "antiban": False,
    "secur": "off",
    "raidlog": None,
    "join_limit": 5,
    "join_time": 10
}

JOIN_CACHE = []
ENDED_GIVEAWAYS = {}
GIVEAWAYS = {}

# ============================================================
# HELPERS
# ============================================================

def is_whitelisted(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM whitelist WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def get_ticket_owner(channel_id: int):
    cursor.execute("SELECT user_id FROM open_tickets WHERE channel_id=?", (channel_id,))
    row = cursor.fetchone()
    return row[0] if row else None

async def raid_log(guild: discord.Guild, content: str):
    if ANTIRAID["raidlog"]:
        channel = guild.get_channel(ANTIRAID["raidlog"])
        if channel:
            await channel.send(embed=discord.Embed(
                title="🛡️ Antiraid", description=content, color=0xff0000))

async def send_log(guild: discord.Guild, log_type: str, embed: discord.Embed):
    channel_id = LOGS.get(log_type)
    if channel_id:
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed)

LOGS = {
    "modlog": None,
    "messagelog": None,
    "voicelog": None,
    "rolelog": None,
    "boostlog": None
}

# ============================================================
# ON READY
# ============================================================

@bot.event
async def on_ready():
    print(f"✅ Connecté : {bot.user}")
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())
    if not giveaway_loop.is_running():
        giveaway_loop.start()
    try:
        synced = await tree.sync()
        print(f"✅ {len(synced)} slash commande(s) synchronisée(s)")
    except Exception as e:
        print(f"❌ Erreur sync : {e}")

# ============================================================
# GESTION D'ERREURS GLOBALE
# ============================================================

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    msg = "❌ Une erreur est survenue."
    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ Tu n'as pas les permissions nécessaires."
    elif isinstance(error, app_commands.BotMissingPermissions):
        msg = "❌ Je n'ai pas les permissions nécessaires."
    elif isinstance(error, app_commands.CommandOnCooldown):
        msg = f"⏳ Réessaie dans **{error.retry_after:.1f}s**."
    else:
        print(f"[ERREUR SLASH] {error}")

    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)

# ============================================================
# MODÉRATION
# ============================================================

@tree.command(name="kick", description="Expulser un membre du serveur")
@app_commands.describe(membre="Le membre à expulser", raison="Raison de l'expulsion")
@app_commands.default_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    if membre.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("❌ Tu ne peux pas expulser ce membre (rôle supérieur ou égal).", ephemeral=True)
    await membre.kick(reason=raison)
    cursor.execute("INSERT INTO sanctions VALUES (NULL,?,?,?,?,?)",
                   (membre.id, interaction.user.id, "kick", raison, now()))
    db.commit()
    embed = discord.Embed(title="👢 Membre expulsé", color=COLOR)
    embed.add_field(name="Membre", value=str(membre))
    embed.add_field(name="Raison", value=raison)
    embed.add_field(name="Modérateur", value=interaction.user.mention)
    await interaction.response.send_message(embed=embed)

@tree.command(name="ban", description="Bannir un membre du serveur")
@app_commands.describe(membre="Le membre à bannir", raison="Raison du ban")
@app_commands.default_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    if membre.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("❌ Tu ne peux pas bannir ce membre (rôle supérieur ou égal).", ephemeral=True)
    await membre.ban(reason=raison)
    cursor.execute("INSERT INTO sanctions VALUES (NULL,?,?,?,?,?)",
                   (membre.id, interaction.user.id, "ban", raison, now()))
    db.commit()
    embed = discord.Embed(title="🔨 Membre banni", color=0xff0000)
    embed.add_field(name="Membre", value=str(membre))
    embed.add_field(name="Raison", value=raison)
    embed.add_field(name="Modérateur", value=interaction.user.mention)
    await interaction.response.send_message(embed=embed)

@tree.command(name="unban", description="Débannir un utilisateur")
@app_commands.describe(user_id="L'ID de l'utilisateur à débannir", raison="Raison du déban")
@app_commands.default_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str, raison: str = "Aucune raison"):
    await interaction.response.defer()
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=raison)
        await interaction.followup.send(embed=discord.Embed(
            title="✅ Membre débanni",
            description=f"{user} a été débanni.\n**Raison :** {raison}",
            color=0x00ff00))
    except discord.NotFound:
        await interaction.followup.send("❌ Utilisateur introuvable ou non banni.", ephemeral=True)
    except ValueError:
        await interaction.followup.send("❌ ID invalide.", ephemeral=True)

@tree.command(name="mute", description="Mettre un membre en timeout")
@app_commands.describe(membre="Le membre à mute", duree="Durée (ex: 10m, 2h, 7d)", raison="Raison du mute")
@app_commands.default_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, membre: discord.Member, duree: str = "1h", raison: str = "Aucune raison"):
    seconds = parse_duration(duree)
    if not seconds:
        return await interaction.response.send_message("❌ Durée invalide. Exemples : `10m`, `2h`, `7d`", ephemeral=True)
    until = discord.utils.utcnow() + discord.timedelta(seconds=seconds)
    await membre.timeout(until, reason=raison)
    cursor.execute("INSERT INTO sanctions VALUES (NULL,?,?,?,?,?)",
                   (membre.id, interaction.user.id, "mute", raison, now()))
    db.commit()
    embed = discord.Embed(title="🔇 Membre mute", color=COLOR)
    embed.add_field(name="Membre", value=str(membre))
    embed.add_field(name="Durée", value=duree)
    embed.add_field(name="Raison", value=raison)
    embed.add_field(name="Modérateur", value=interaction.user.mention)
    await interaction.response.send_message(embed=embed)

@tree.command(name="unmute", description="Retirer le timeout d'un membre")
@app_commands.describe(membre="Le membre à unmute")
@app_commands.default_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, membre: discord.Member):
    await membre.timeout(None)
    await interaction.response.send_message(embed=discord.Embed(
        title="🔊 Membre unmute",
        description=f"{membre.mention} n'est plus en timeout.",
        color=0x00ff00))

@tree.command(name="warn", description="Avertir un membre")
@app_commands.describe(membre="Le membre à avertir", raison="Raison de l'avertissement")
@app_commands.default_permissions(kick_members=True)
async def warn(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    cursor.execute("INSERT INTO sanctions VALUES (NULL,?,?,?,?,?)",
                   (membre.id, interaction.user.id, "warn", raison, now()))
    db.commit()
    embed = discord.Embed(title="⚠️ Avertissement", color=0xffaa00)
    embed.add_field(name="Membre", value=str(membre))
    embed.add_field(name="Raison", value=raison)
    embed.add_field(name="Modérateur", value=interaction.user.mention)
    await interaction.response.send_message(embed=embed)
    try:
        await membre.send(embed=discord.Embed(
            title=f"⚠️ Avertissement sur {interaction.guild.name}",
            description=f"**Raison :** {raison}",
            color=0xffaa00))
    except Exception:
        pass

@tree.command(name="clear", description="Supprimer des messages en masse")
@app_commands.describe(nombre="Nombre de messages à supprimer (max 100)")
@app_commands.default_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, nombre: app_commands.Range[int, 1, 100] = 10):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(f"✅ **{len(deleted)}** message(s) supprimé(s).", ephemeral=True)

@tree.command(name="sanctions", description="Voir les sanctions d'un membre")
@app_commands.describe(membre="Le membre à consulter")
@app_commands.default_permissions(kick_members=True)
async def sanctions(interaction: discord.Interaction, membre: discord.Member):
    cursor.execute("SELECT type, reason, date FROM sanctions WHERE user_id=?", (membre.id,))
    rows = cursor.fetchall()
    if not rows:
        return await interaction.response.send_message(f"✅ Aucune sanction pour {membre}.", ephemeral=True)
    txt = "\n".join(f"• **{r[0]}** — {r[1]} (<t:{r[2]}:R>)" for r in rows)
    await interaction.response.send_message(embed=discord.Embed(
        title=f"📋 Sanctions de {membre}",
        description=txt,
        color=COLOR))

@tree.command(name="note", description="Ajouter une note sur un membre")
@app_commands.describe(membre="Le membre", note="Contenu de la note")
@app_commands.default_permissions(kick_members=True)
async def note(interaction: discord.Interaction, membre: discord.Member, note: str):
    cursor.execute("INSERT INTO notes VALUES (NULL,?,?,?,?)",
                   (membre.id, interaction.user.id, note, now()))
    db.commit()
    await interaction.response.send_message(f"✅ Note ajoutée pour {membre}.", ephemeral=True)

@tree.command(name="notes", description="Voir les notes d'un membre")
@app_commands.describe(membre="Le membre à consulter")
@app_commands.default_permissions(kick_members=True)
async def notes(interaction: discord.Interaction, membre: discord.Member):
    cursor.execute("SELECT note, date FROM notes WHERE user_id=?", (membre.id,))
    rows = cursor.fetchall()
    if not rows:
        return await interaction.response.send_message(f"Aucune note pour {membre}.", ephemeral=True)
    txt = "\n".join(f"• {r[0]} (<t:{r[1]}:R>)" for r in rows)
    await interaction.response.send_message(embed=discord.Embed(
        title=f"📝 Notes de {membre}", description=txt, color=COLOR), ephemeral=True)

# ============================================================
# ANTIRAID COMMANDES
# ============================================================

@tree.command(name="antibot", description="Activer/désactiver l'antibot")
@app_commands.describe(etat="on ou off")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activer", value="on"),
    app_commands.Choice(name="Désactiver", value="off")
])
@app_commands.default_permissions(administrator=True)
async def antibot(interaction: discord.Interaction, etat: str):
    ANTIRAID["antibot"] = etat == "on"
    await interaction.response.send_message(
        f"🤖 Antibot **{'activé' if ANTIRAID['antibot'] else 'désactivé'}**.")

@tree.command(name="antitoken", description="Activer/désactiver l'antitoken (anti-raid joins)")
@app_commands.describe(etat="on ou off")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activer", value="on"),
    app_commands.Choice(name="Désactiver", value="off")
])
@app_commands.default_permissions(administrator=True)
async def antitoken(interaction: discord.Interaction, etat: str):
    ANTIRAID["antitoken"] = etat == "on"
    await interaction.response.send_message(
        f"🛡️ Antitoken **{'activé' if ANTIRAID['antitoken'] else 'désactivé'}**.")

@tree.command(name="antieveryone", description="Activer/désactiver l'antieveryone")
@app_commands.describe(etat="on ou off")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activer", value="on"),
    app_commands.Choice(name="Désactiver", value="off")
])
@app_commands.default_permissions(administrator=True)
async def antieveryone(interaction: discord.Interaction, etat: str):
    ANTIRAID["antieveryone"] = etat == "on"
    await interaction.response.send_message(
        f"📢 Antieveryone **{'activé' if ANTIRAID['antieveryone'] else 'désactivé'}**.")

@tree.command(name="antiban", description="Activer/désactiver l'antiban")
@app_commands.describe(etat="on ou off")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activer", value="on"),
    app_commands.Choice(name="Désactiver", value="off")
])
@app_commands.default_permissions(administrator=True)
async def antiban(interaction: discord.Interaction, etat: str):
    ANTIRAID["antiban"] = etat == "on"
    await interaction.response.send_message(
        f"🔨 Antiban **{'activé' if ANTIRAID['antiban'] else 'désactivé'}**.")

@tree.command(name="secur", description="Définir le niveau de sécurité antiraid")
@app_commands.describe(niveau="Niveau de sécurité")
@app_commands.choices(niveau=[
    app_commands.Choice(name="Désactivé", value="off"),
    app_commands.Choice(name="Normal", value="on"),
    app_commands.Choice(name="Maximum", value="max")
])
@app_commands.default_permissions(administrator=True)
async def secur(interaction: discord.Interaction, niveau: str):
    ANTIRAID["secur"] = niveau
    await interaction.response.send_message(f"🔒 Mode sécurité : **{niveau.upper()}**")

@tree.command(name="raidlog", description="Configurer le salon de log antiraid")
@app_commands.describe(etat="on ou off", salon="Salon de log")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activer", value="on"),
    app_commands.Choice(name="Désactiver", value="off")
])
@app_commands.default_permissions(administrator=True)
async def raidlog(interaction: discord.Interaction, etat: str, salon: discord.TextChannel = None):
    if etat == "on" and salon:
        ANTIRAID["raidlog"] = salon.id
        await interaction.response.send_message(f"✅ Raidlog activé dans {salon.mention}")
    else:
        ANTIRAID["raidlog"] = None
        await interaction.response.send_message("✅ Raidlog désactivé.")

@tree.command(name="wl", description="Ajouter un membre à la whitelist antiraid")
@app_commands.describe(membre="Le membre à whitelister")
@app_commands.default_permissions(administrator=True)
async def wl(interaction: discord.Interaction, membre: discord.Member):
    cursor.execute("INSERT OR IGNORE INTO whitelist VALUES (?)", (membre.id,))
    db.commit()
    await interaction.response.send_message(f"✅ {membre} ajouté à la whitelist.")

@tree.command(name="unwl", description="Retirer un membre de la whitelist antiraid")
@app_commands.describe(membre="Le membre à retirer")
@app_commands.default_permissions(administrator=True)
async def unwl(interaction: discord.Interaction, membre: discord.Member):
    cursor.execute("DELETE FROM whitelist WHERE user_id=?", (membre.id,))
    db.commit()
    await interaction.response.send_message(f"✅ {membre} retiré de la whitelist.")

# ============================================================
# EVENTS ANTIRAID
# ============================================================

@bot.event
async def on_member_join(member: discord.Member):
    if is_whitelisted(member.id):
        return
    now_time = time.time()
    JOIN_CACHE.append(now_time)
    JOIN_CACHE[:] = [t for t in JOIN_CACHE if now_time - t <= ANTIRAID["join_time"]]

    if ANTIRAID["antibot"] and member.bot:
        await member.ban(reason="Antibot")
        await raid_log(member.guild, f"🤖 Bot banni : {member}")
        return

    if ANTIRAID["antitoken"] and len(JOIN_CACHE) >= ANTIRAID["join_limit"]:
        await member.ban(reason="Antitoken (join massif)")
        await raid_log(member.guild, f"🚨 Ban token raid : {member}")
        return

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if ANTIRAID["antieveryone"] and "@everyone" in message.content:
        if not is_whitelisted(message.author.id):
            await message.delete()
            await message.author.timeout(
                discord.utils.utcnow() + discord.timedelta(minutes=10),
                reason="Antieveryone")
            await raid_log(message.guild, f"📢 @everyone bloqué : {message.author}")
    await bot.process_commands(message)

# ============================================================
# TICKETS
# ============================================================

TICKET_CATEGORY_NAME = "🎫 Tickets"

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Ouvrir un ticket", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        cursor.execute("SELECT 1 FROM open_tickets WHERE user_id=?", (user.id,))
        if cursor.fetchone():
            return await interaction.response.send_message(
                "❌ Tu as déjà un ticket ouvert.", ephemeral=True)

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}", category=category)

        await channel.set_permissions(guild.default_role, view_channel=False)
        await channel.set_permissions(user, view_channel=True, send_messages=True)
        await channel.set_permissions(guild.me, view_channel=True, send_messages=True)

        cursor.execute("INSERT INTO open_tickets VALUES (?, ?)", (user.id, channel.id))
        db.commit()

        close_view = CloseTicketView()
        embed = discord.Embed(
            title="🎫 Ticket ouvert",
            description="Un membre du staff va te répondre.\nClique sur le bouton pour fermer le ticket.",
            color=COLOR)
        embed.add_field(name="Utilisateur", value=user.mention)
        await channel.send(embed=embed, view=close_view)
        await interaction.response.send_message(
            f"✅ Ticket créé : {channel.mention}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (interaction.channel.category and
                interaction.channel.category.name == TICKET_CATEGORY_NAME):
            return await interaction.response.send_message("❌ Pas un ticket.", ephemeral=True)

        owner_id = get_ticket_owner(interaction.channel.id)
        if owner_id:
            cursor.execute("DELETE FROM open_tickets WHERE channel_id=?", (interaction.channel.id,))
            db.commit()

        await interaction.response.send_message("🔒 Fermeture dans 5 secondes…")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
        await interaction.channel.delete()

@tree.command(name="ticket", description="Envoyer le panel de création de ticket")
@app_commands.default_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Support",
        description="Clique sur le bouton ci-dessous pour ouvrir un ticket.",
        color=COLOR)
    await interaction.response.send_message(embed=embed, view=TicketView())

@tree.command(name="claim", description="Claim le ticket actuel")
@app_commands.default_permissions(manage_channels=True)
async def claim(interaction: discord.Interaction):
    if not (interaction.channel.category and
            interaction.channel.category.name == TICKET_CATEGORY_NAME):
        return await interaction.response.send_message("❌ Pas un ticket.", ephemeral=True)
    await interaction.response.send_message(f"✅ Ticket claim par {interaction.user.mention}")

@tree.command(name="rename", description="Renommer le ticket actuel")
@app_commands.describe(nom="Nouveau nom du ticket")
@app_commands.default_permissions(manage_channels=True)
async def rename(interaction: discord.Interaction, nom: str):
    if not (interaction.channel.category and
            interaction.channel.category.name == TICKET_CATEGORY_NAME):
        return await interaction.response.send_message("❌ Pas un ticket.", ephemeral=True)
    await interaction.channel.edit(name=nom)
    await interaction.response.send_message(f"✅ Ticket renommé en **{nom}**")

@tree.command(name="add", description="Ajouter un membre au ticket")
@app_commands.describe(membre="Le membre à ajouter")
@app_commands.default_permissions(manage_channels=True)
async def add(interaction: discord.Interaction, membre: discord.Member):
    if not (interaction.channel.category and
            interaction.channel.category.name == TICKET_CATEGORY_NAME):
        return await interaction.response.send_message("❌ Pas un ticket.", ephemeral=True)
    await interaction.channel.set_permissions(membre, view_channel=True, send_messages=True)
    await interaction.response.send_message(f"➕ {membre.mention} ajouté au ticket.")

@tree.command(name="remove", description="Retirer un membre du ticket")
@app_commands.describe(membre="Le membre à retirer")
@app_commands.default_permissions(manage_channels=True)
async def remove(interaction: discord.Interaction, membre: discord.Member):
    if not (interaction.channel.category and
            interaction.channel.category.name == TICKET_CATEGORY_NAME):
        return await interaction.response.send_message("❌ Pas un ticket.", ephemeral=True)
    await interaction.channel.set_permissions(membre, overwrite=None)
    await interaction.response.send_message(f"➖ {membre.mention} retiré du ticket.")

@tree.command(name="close", description="Fermer le ticket actuel")
@app_commands.describe(raison="Raison de la fermeture")
@app_commands.default_permissions(manage_channels=True)
async def close(interaction: discord.Interaction, raison: str = "Aucune raison"):
    if not (interaction.channel.category and
            interaction.channel.category.name == TICKET_CATEGORY_NAME):
        return await interaction.response.send_message("❌ Pas un ticket.", ephemeral=True)

    owner_id = get_ticket_owner(interaction.channel.id)
    if owner_id:
        cursor.execute("DELETE FROM open_tickets WHERE channel_id=?", (interaction.channel.id,))
        db.commit()

    await interaction.response.send_message(f"🔒 Fermeture dans 5 secondes… | Raison : {raison}")
    await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
    await interaction.channel.delete()

# ============================================================
# GIVEAWAYS
# ============================================================

@tree.command(name="giveaway", description="Lancer un giveaway")
@app_commands.describe(
    duree="Durée du giveaway (ex: 10m, 2h, 1d)",
    gagnants="Nombre de gagnants",
    prix="Le prix à gagner"
)
@app_commands.default_permissions(manage_guild=True)
async def giveaway(interaction: discord.Interaction, duree: str, gagnants: int, prix: str):
    seconds = parse_duration(duree)
    if not seconds:
        return await interaction.response.send_message(
            "❌ Durée invalide. Exemples : `10m`, `2h`, `1d`", ephemeral=True)

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"🏆 **Prix** : {prix}\n👥 **Gagnants** : {gagnants}\n⏱️ **Durée** : {duree}",
        color=COLOR)
    embed.set_footer(text=f"Finit dans {duree} • Réagis avec 🎉 pour participer")

    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("🎉")

    GIVEAWAYS[msg.id] = {
        "channel": interaction.channel.id,
        "winners": gagnants,
        "end": time.time() + seconds
    }

@tree.command(name="reroll", description="Reroll le dernier giveaway terminé dans ce salon")
@app_commands.default_permissions(manage_guild=True)
async def reroll(interaction: discord.Interaction):
    for msg_id, data in reversed(list(ENDED_GIVEAWAYS.items())):
        if data["channel"] == interaction.channel.id:
            channel = bot.get_channel(data["channel"])
            try:
                msg = await channel.fetch_message(msg_id)
                reaction = discord.utils.get(msg.reactions, emoji="🎉")
                users = [u async for u in reaction.users() if not u.bot]
                if users:
                    winner = random.choice(users)
                    return await interaction.response.send_message(
                        f"🎉 Nouveau gagnant : {winner.mention}")
            except Exception:
                pass
    await interaction.response.send_message("❌ Aucun giveaway terminé trouvé dans ce salon.")

@tasks.loop(seconds=5)
async def giveaway_loop():
    for msg_id, data in list(GIVEAWAYS.items()):
        if time.time() >= data["end"]:
            channel = bot.get_channel(data["channel"])
            if not channel:
                del GIVEAWAYS[msg_id]
                continue
            try:
                msg = await channel.fetch_message(msg_id)
                reaction = discord.utils.get(msg.reactions, emoji="🎉")
                users = [u async for u in reaction.users() if not u.bot]

                if not users:
                    await channel.send("❌ Aucun participant pour ce giveaway.")
                else:
                    winners = random.sample(users, min(len(users), data["winners"]))
                    await channel.send(
                        "🎉 **Gagnant(s)** : " + ", ".join(u.mention for u in winners))
                    ENDED_GIVEAWAYS[msg_id] = {"channel": data["channel"], "msg_id": msg_id}
            except Exception as e:
                print(f"[Giveaway] Erreur : {e}")
            finally:
                if msg_id in GIVEAWAYS:
                    del GIVEAWAYS[msg_id]

@giveaway_loop.before_loop
async def before_giveaway():
    await bot.wait_until_ready()

# ============================================================
# LOGS COMMANDES
# ============================================================

@tree.command(name="modlog", description="Configurer le salon de log de modération")
@app_commands.describe(etat="on ou off", salon="Salon de log")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activer", value="on"),
    app_commands.Choice(name="Désactiver", value="off")
])
@app_commands.default_permissions(administrator=True)
async def modlog(interaction: discord.Interaction, etat: str, salon: discord.TextChannel = None):
    if etat == "on" and salon:
        LOGS["modlog"] = salon.id
        await interaction.response.send_message(f"✅ Modlog activé dans {salon.mention}")
    else:
        LOGS["modlog"] = None
        await interaction.response.send_message("✅ Modlog désactivé.")

@tree.command(name="messagelog", description="Configurer le salon de log des messages")
@app_commands.describe(etat="on ou off", salon="Salon de log")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activer", value="on"),
    app_commands.Choice(name="Désactiver", value="off")
])
@app_commands.default_permissions(administrator=True)
async def messagelog(interaction: discord.Interaction, etat: str, salon: discord.TextChannel = None):
    if etat == "on" and salon:
        LOGS["messagelog"] = salon.id
        await interaction.response.send_message(f"✅ Messagelog activé dans {salon.mention}")
    else:
        LOGS["messagelog"] = None
        await interaction.response.send_message("✅ Messagelog désactivé.")

@tree.command(name="voicelog", description="Configurer le salon de log vocal")
@app_commands.describe(etat="on ou off", salon="Salon de log")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activer", value="on"),
    app_commands.Choice(name="Désactiver", value="off")
])
@app_commands.default_permissions(administrator=True)
async def voicelog(interaction: discord.Interaction, etat: str, salon: discord.TextChannel = None):
    if etat == "on" and salon:
        LOGS["voicelog"] = salon.id
        await interaction.response.send_message(f"✅ Voicelog activé dans {salon.mention}")
    else:
        LOGS["voicelog"] = None
        await interaction.response.send_message("✅ Voicelog désactivé.")

@tree.command(name="rolelog", description="Configurer le salon de log des rôles")
@app_commands.describe(etat="on ou off", salon="Salon de log")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activer", value="on"),
    app_commands.Choice(name="Désactiver", value="off")
])
@app_commands.default_permissions(administrator=True)
async def rolelog(interaction: discord.Interaction, etat: str, salon: discord.TextChannel = None):
    if etat == "on" and salon:
        LOGS["rolelog"] = salon.id
        await interaction.response.send_message(f"✅ Rolelog activé dans {salon.mention}")
    else:
        LOGS["rolelog"] = None
        await interaction.response.send_message("✅ Rolelog désactivé.")

@tree.command(name="boostlog", description="Configurer le salon de log des boosts")
@app_commands.describe(etat="on ou off", salon="Salon de log")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activer", value="on"),
    app_commands.Choice(name="Désactiver", value="off")
])
@app_commands.default_permissions(administrator=True)
async def boostlog(interaction: discord.Interaction, etat: str, salon: discord.TextChannel = None):
    if etat == "on" and salon:
        LOGS["boostlog"] = salon.id
        await interaction.response.send_message(f"✅ Boostlog activé dans {salon.mention}")
    else:
        LOGS["boostlog"] = None
        await interaction.response.send_message("✅ Boostlog désactivé.")

# ============================================================
# EVENTS LOGS
# ============================================================

@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    await send_log(guild, "modlog", discord.Embed(
        title="🔨 Membre banni", description=str(user), color=0xff0000))

@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User):
    await send_log(guild, "modlog", discord.Embed(
        title="✅ Membre débanni", description=str(user), color=0x00ff00))

@bot.event
async def on_message_delete(message: discord.Message):
    if not message.guild or message.author.bot:
        return
    embed = discord.Embed(title="🗑️ Message supprimé", color=0xffaa00)
    embed.add_field(name="Auteur", value=str(message.author), inline=True)
    embed.add_field(name="Salon", value=message.channel.mention, inline=True)
    embed.add_field(name="Contenu", value=message.content[:1000] or "*(vide)*", inline=False)
    await send_log(message.guild, "messagelog", embed)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.content == after.content or before.author.bot:
        return
    embed = discord.Embed(title="✏️ Message modifié", color=0x3498db)
    embed.add_field(name="Auteur", value=str(before.author), inline=True)
    embed.add_field(name="Salon", value=before.channel.mention, inline=True)
    embed.add_field(name="Avant", value=before.content[:1000] or "—", inline=False)
    embed.add_field(name="Après", value=after.content[:1000] or "—", inline=False)
    await send_log(before.guild, "messagelog", embed)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if before.channel == after.channel:
        return
    embed = discord.Embed(title="🎙️ Activité vocale", description=str(member), color=0x9b59b6)
    embed.add_field(name="Avant", value=str(before.channel) if before.channel else "Aucun", inline=True)
    embed.add_field(name="Après", value=str(after.channel) if after.channel else "Aucun", inline=True)
    await send_log(member.guild, "voicelog", embed)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.premium_since is None and after.premium_since is not None:
        await send_log(after.guild, "boostlog", discord.Embed(
            title="💜 Boost", description=f"{after} a boosté le serveur !", color=0xf47fff))
    elif before.premium_since is not None and after.premium_since is None:
        await send_log(after.guild, "boostlog", discord.Embed(
            title="🩶 Unboost", description=f"{after} a retiré son boost.", color=0xaaaaaa))

    if before.roles != after.roles:
        added = set(after.roles) - set(before.roles)
        removed = set(before.roles) - set(after.roles)
        txt = ""
        if added:   txt += "➕ " + ", ".join(r.name for r in added) + "\n"
        if removed: txt += "➖ " + ", ".join(r.name for r in removed)
        embed = discord.Embed(title="🎭 Rôles modifiés", description=f"{after}\n\n{txt}", color=0x2ecc71)
        await send_log(after.guild, "rolelog", embed)

# ============================================================
# BACKUP
# ============================================================

BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

@tree.command(name="backup", description="Gérer les backups du serveur")
@app_commands.describe(action="Action à effectuer", nom="Nom de la backup")
@app_commands.choices(action=[
    app_commands.Choice(name="Créer", value="server"),
    app_commands.Choice(name="Lister", value="list"),
    app_commands.Choice(name="Charger", value="load")
])
@app_commands.default_permissions(administrator=True)
async def backup(interaction: discord.Interaction, action: str, nom: str = None):
    await interaction.response.defer()

    if action == "server":
        if not nom:
            return await interaction.followup.send("❌ Fournis un nom pour la backup.", ephemeral=True)
        data = {"roles": [], "categories": []}
        for role in interaction.guild.roles:
            if role.is_default(): continue
            data["roles"].append({
                "name": role.name, "color": role.color.value,
                "hoist": role.hoist, "mentionable": role.mentionable
            })
        for cat in interaction.guild.categories:
            channels = []
            for ch in cat.channels:
                if isinstance(ch, discord.TextChannel):
                    channels.append(("text", ch.name))
                elif isinstance(ch, discord.VoiceChannel):
                    channels.append(("voice", ch.name))
            data["categories"].append({"name": cat.name, "channels": channels})
        with open(f"{BACKUP_DIR}/{nom}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        await interaction.followup.send(f"✅ Backup **{nom}** créée.")

    elif action == "list":
        files = os.listdir(BACKUP_DIR)
        await interaction.followup.send(
            "📂 **Backups disponibles :**\n" + "\n".join(f"• `{f}`" for f in files)
            if files else "Aucune backup disponible.")

    elif action == "load":
        if not nom:
            return await interaction.followup.send("❌ Fournis un nom de backup.", ephemeral=True)
        path = f"{BACKUP_DIR}/{nom}.json"
        if not os.path.exists(path):
            return await interaction.followup.send("❌ Backup introuvable.", ephemeral=True)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for role in data["roles"]:
            await interaction.guild.create_role(
                name=role["name"], color=discord.Color(role["color"]),
                hoist=role["hoist"], mentionable=role["mentionable"])
        for cat in data["categories"]:
            category = await interaction.guild.create_category(cat["name"])
            for ch_type, ch_name in cat["channels"]:
                if ch_type == "text":
                    await interaction.guild.create_text_channel(ch_name, category=category)
                else:
                    await interaction.guild.create_voice_channel(ch_name, category=category)
        await interaction.followup.send(f"✅ Backup **{nom}** chargée.")

# ============================================================
# UTILITAIRE
# ============================================================

@tree.command(name="userinfo", description="Afficher les infos d'un membre")
@app_commands.describe(membre="Le membre à inspecter")
async def userinfo(interaction: discord.Interaction, membre: discord.Member = None):
    membre = membre or interaction.user
    embed = discord.Embed(title=str(membre), color=membre.color)
    embed.set_thumbnail(url=membre.display_avatar.url)
    embed.add_field(name="ID", value=membre.id)
    embed.add_field(name="Surnom", value=membre.nick or "Aucun")
    embed.add_field(name="Compte créé", value=f"<t:{int(membre.created_at.timestamp())}:R>")
    embed.add_field(name="A rejoint", value=f"<t:{int(membre.joined_at.timestamp())}:R>")
    embed.add_field(name="Rôles", value=", ".join(r.mention for r in reversed(membre.roles[1:])) or "Aucun", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="serverinfo", description="Afficher les infos du serveur")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=g.name, color=COLOR)
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="Propriétaire", value=str(g.owner))
    embed.add_field(name="Membres", value=g.member_count)
    embed.add_field(name="Salons", value=len(g.channels))
    embed.add_field(name="Rôles", value=len(g.roles))
    embed.add_field(name="Boosts", value=g.premium_subscription_count)
    embed.add_field(name="Créé", value=f"<t:{int(g.created_at.timestamp())}:R>")
    await interaction.response.send_message(embed=embed)

@tree.command(name="avatar", description="Afficher l'avatar d'un membre")
@app_commands.describe(membre="Le membre")
async def avatar(interaction: discord.Interaction, membre: discord.Member = None):
    membre = membre or interaction.user
    embed = discord.Embed(title=f"Avatar de {membre}", color=COLOR)
    embed.set_image(url=membre.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@tree.command(name="banner", description="Afficher la bannière d'un membre")
@app_commands.describe(membre="Le membre")
async def banner(interaction: discord.Interaction, membre: discord.Member = None):
    membre = membre or interaction.user
    user = await bot.fetch_user(membre.id)
    if not user.banner:
        return await interaction.response.send_message("❌ Ce membre n'a pas de bannière.", ephemeral=True)
    embed = discord.Embed(title=f"Bannière de {membre}", color=COLOR)
    embed.set_image(url=user.banner.url)
    await interaction.response.send_message(embed=embed)

@tree.command(name="help", description="Afficher la liste des commandes")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Commandes disponibles", color=COLOR)
    categories = {
        "🔨 Modération": ["/kick", "/ban", "/unban", "/mute", "/unmute", "/warn", "/clear", "/sanctions", "/note", "/notes"],
        "🛡️ Antiraid": ["/antibot", "/antitoken", "/antiban", "/antieveryone", "/secur", "/raidlog", "/wl", "/unwl"],
        "🎫 Tickets": ["/ticket", "/claim", "/rename", "/add", "/remove", "/close"],
        "🎉 Giveaways": ["/giveaway", "/reroll"],
        "📋 Logs": ["/modlog", "/messagelog", "/voicelog", "/rolelog", "/boostlog"],
        "🔧 Utilitaire": ["/userinfo", "/serverinfo", "/avatar", "/banner"],
        "💾 Backup": ["/backup"]
    }
    for cat, cmds in categories.items():
        embed.add_field(name=cat, value=" • ".join(cmds), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================================
# LANCEMENT
# ============================================================

if not TOKEN:
    raise ValueError("❌ La variable d'environnement TOKEN est manquante !")

bot.run(TOKEN)
