import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime, timedelta
import re

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= CONFIG GLOBALE =================

config = {
    # Bienvenue
    "welcome_channel": None,
    "welcome_message": "Bienvenue {mention} sur **{server}** ! Tu es le membre n°{count} 🎉",
    "welcome_dm": False,
    "goodbye_channel": None,
    "goodbye_message": "**{name}** vient de quitter {server}. Il reste {count} membres.",

    # Tickets
    "ticket_channel": None,
    "ticket_category": None,
    "ticket_support_role": None,
    "ticket_log_channel": None,
    "ticket_message": "Clique sur le bouton ci-dessous pour ouvrir un ticket.",

    # Auto-rôle
    "autorole": [],

    # Logs
    "log_channel": None,

    # Anti-spam
    "antispam_enabled": False,
    "antispam_max": 5,
    "antispam_interval": 3,
    "antispam_action": "mute",
    "antispam_mute_duration": 10,

    # Anti-raid
    "antiraid_enabled": False,
    "antiraid_joins": 5,
    "antiraid_interval": 10,
    "antiraid_action": "kick",

    # Auto-modération
    "automod_enabled": False,
    "automod_badwords": [],
    "automod_links": False,
    "automod_caps": False,
    "automod_action": "delete",

    # Mute role
    "mute_role": None,
}

spam_tracker = {}
raid_tracker = []

# ================= UTILITAIRES =================

async def send_log(guild, description, color=0xED4245):
    if not config["log_channel"]:
        return
    channel = guild.get_channel(config["log_channel"])
    if not channel:
        return
    embed = discord.Embed(description=description, color=color, timestamp=discord.utils.utcnow())
    embed.set_footer(text="Logs • Bot")
    await channel.send(embed=embed)


async def mute_member(guild, member, duration_minutes=10, reason="Auto-modération"):
    mute_role = guild.get_role(config["mute_role"]) if config["mute_role"] else None
    if not mute_role:
        try:
            mute_role = await guild.create_role(name="Muted")
            config["mute_role"] = mute_role.id
            for channel in guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        except:
            return
    await member.add_roles(mute_role, reason=reason)
    await asyncio.sleep(duration_minutes * 60)
    await member.remove_roles(mute_role, reason="Fin du mute")

# ================= EVENTS =================

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return await bot.process_commands(message)

    member = message.author
    guild = message.guild

    # Anti-spam
    if config["antispam_enabled"]:
        uid = member.id
        now = datetime.utcnow()
        if uid not in spam_tracker:
            spam_tracker[uid] = []
        spam_tracker[uid] = [t for t in spam_tracker[uid] if (now - t).total_seconds() < config["antispam_interval"]]
        spam_tracker[uid].append(now)

        if len(spam_tracker[uid]) >= config["antispam_max"]:
            spam_tracker[uid] = []
            action = config["antispam_action"]
            await message.delete()
            if action == "warn":
                await message.channel.send(f"⚠️ {member.mention} Stop le spam !", delete_after=5)
            elif action == "mute":
                dur = config["antispam_mute_duration"]
                await message.channel.send(f"🔇 {member.mention} muté {dur} min pour spam.", delete_after=5)
                asyncio.create_task(mute_member(guild, member, dur, "Anti-spam"))
            elif action == "kick":
                await member.kick(reason="Anti-spam")
            elif action == "ban":
                await member.ban(reason="Anti-spam")
            await send_log(guild, f"🛡️ **Anti-spam** → {member.mention} ({action})\nSalon : {message.channel.mention}", 0xE67E22)
            return

    # Auto-modération
    if config["automod_enabled"]:
        content = message.content
        for word in config["automod_badwords"]:
            if word.lower() in content.lower():
                await message.delete()
                await _apply_automod(message, f"mot interdit : `{word}`")
                return
        if config["automod_links"] and re.search(r"https?://|discord\.gg/", content):
            await message.delete()
            await _apply_automod(message, "lien non autorisé")
            return
        if config["automod_caps"] and len(content) > 10:
            upper = sum(1 for c in content if c.isupper())
            if upper / len(content) > 0.7:
                await message.delete()
                await _apply_automod(message, "trop de majuscules")
                return

    await bot.process_commands(message)


async def _apply_automod(message, reason):
    member = message.author
    guild = message.guild
    action = config["automod_action"]
    if action == "warn":
        await message.channel.send(f"⚠️ {member.mention} Message supprimé : {reason}.", delete_after=5)
    elif action == "mute":
        await message.channel.send(f"🔇 {member.mention} muté pour {reason}.", delete_after=5)
        asyncio.create_task(mute_member(guild, member, 10, f"Auto-mod : {reason}"))
    await send_log(guild, f"🤖 **Auto-mod** → {member.mention}\nRaison : {reason}\nSalon : {message.channel.mention}", 0xE67E22)


@bot.event
async def on_member_join(member):
    guild = member.guild
    now = datetime.utcnow()

    # Anti-raid
    if config["antiraid_enabled"]:
        global raid_tracker
        raid_tracker = [t for t in raid_tracker if (now - t).total_seconds() < config["antiraid_interval"]]
        raid_tracker.append(now)
        if len(raid_tracker) >= config["antiraid_joins"]:
            raid_tracker = []
            action = config["antiraid_action"]
            await send_log(guild, f"🚨 **RAID DÉTECTÉ !** Action : **{action}**", 0xFF0000)
            if action == "kick":
                try: await member.kick(reason="Anti-raid")
                except: pass
            elif action == "ban":
                try: await member.ban(reason="Anti-raid")
                except: pass
            elif action == "lockdown":
                for ch in guild.text_channels:
                    try: await ch.set_permissions(guild.default_role, send_messages=False)
                    except: pass
                await send_log(guild, "🔒 **LOCKDOWN activé** — Tous les salons verrouillés.", 0xFF0000)
            return

    # Auto-rôle
    for role_id in config["autorole"]:
        role = guild.get_role(role_id)
        if role:
            try: await member.add_roles(role)
            except: pass

    # Bienvenue
    if config["welcome_channel"]:
        channel = guild.get_channel(config["welcome_channel"])
        if channel:
            msg = config["welcome_message"]\
                .replace("{mention}", member.mention)\
                .replace("{name}", member.name)\
                .replace("{server}", guild.name)\
                .replace("{count}", str(guild.member_count))
            embed = discord.Embed(description=msg, color=0x57F287)
            embed.set_author(name="Bienvenue !", icon_url=member.display_avatar.url)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"{guild.name} • Membre n°{guild.member_count}")
            embed.timestamp = discord.utils.utcnow()
            await channel.send(embed=embed)

    if config["welcome_dm"]:
        try:
            msg = config["welcome_message"]\
                .replace("{mention}", member.name)\
                .replace("{name}", member.name)\
                .replace("{server}", guild.name)\
                .replace("{count}", str(guild.member_count))
            await member.send(embed=discord.Embed(title=f"Bienvenue sur {guild.name} !", description=msg, color=0x57F287))
        except: pass

    await send_log(guild, f"📥 **Membre rejoint** → {member.mention} (`{member.id}`)\nCompte créé : <t:{int(member.created_at.timestamp())}:R>", 0x57F287)


@bot.event
async def on_member_remove(member):
    guild = member.guild
    if config["goodbye_channel"]:
        channel = guild.get_channel(config["goodbye_channel"])
        if channel:
            msg = config["goodbye_message"]\
                .replace("{mention}", member.mention)\
                .replace("{name}", member.name)\
                .replace("{server}", guild.name)\
                .replace("{count}", str(guild.member_count))
            embed = discord.Embed(description=msg, color=0xED4245)
            embed.set_author(name="Départ du serveur", icon_url=member.display_avatar.url)
            embed.timestamp = discord.utils.utcnow()
            await channel.send(embed=embed)
    await send_log(guild, f"📤 **Membre parti** → {member.mention} (`{member.id}`)", 0xED4245)


@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    await send_log(message.guild, f"🗑️ **Message supprimé** par {message.author.mention}\nSalon : {message.channel.mention}\n> {message.content[:300] or '*Aucun contenu*'}", 0xFEE75C)


@bot.event
async def on_member_ban(guild, user):
    await send_log(guild, f"🔨 **Banni** → {user.mention} (`{user.id}`)", 0xED4245)

# ================= TICKETS =================

class TicketOpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Ouvrir un ticket", style=discord.ButtonStyle.primary, custom_id="ticket_open_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.id}")
        if existing:
            return await interaction.response.send_message(f"❌ Tu as déjà un ticket → {existing.mention}", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if config["ticket_support_role"]:
            role = guild.get_role(config["ticket_support_role"])
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        category = guild.get_channel(config["ticket_category"]) if config["ticket_category"] else None
        if not category:
            category = discord.utils.get(guild.categories, name="TICKETS") or await guild.create_category("TICKETS")

        channel = await guild.create_text_channel(f"ticket-{user.id}", overwrites=overwrites, category=category)

        embed = discord.Embed(title="🎫 Ticket ouvert", description=f"Bonjour {user.mention} !\nL'équipe va te répondre rapidement.\n\nPour fermer ce ticket, clique ci-dessous.", color=0x5865F2)
        embed.set_footer(text="Support")
        embed.timestamp = discord.utils.utcnow()
        await channel.send(user.mention, embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"✅ Ticket créé → {channel.mention}", ephemeral=True)

        if config["ticket_log_channel"]:
            log_ch = guild.get_channel(config["ticket_log_channel"])
            if log_ch:
                await log_ch.send(embed=discord.Embed(description=f"📩 **Ticket ouvert** par {user.mention} → {channel.mention}", color=0x57F287, timestamp=discord.utils.utcnow()))


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Fermeture dans 5 secondes...")
        if config["ticket_log_channel"]:
            log_ch = interaction.guild.get_channel(config["ticket_log_channel"])
            if log_ch:
                await log_ch.send(embed=discord.Embed(description=f"🔒 **Ticket fermé** → `{interaction.channel.name}` par {interaction.user.mention}", color=0xED4245, timestamp=discord.utils.utcnow()))
        await asyncio.sleep(5)
        await interaction.channel.delete()

# ================= MODALS DU PANEL =================

class WelcomeModal(discord.ui.Modal, title="⚙️ Bienvenue / Au revoir"):
    ch_welcome = discord.ui.TextInput(label="ID salon bienvenue (vide = désactivé)", required=False)
    msg_welcome = discord.ui.TextInput(label="Message bienvenue ({mention} {name} {server} {count})", style=discord.TextStyle.paragraph, required=False)
    dm = discord.ui.TextInput(label="DM de bienvenue ? (oui/non)", required=False, default="non")
    ch_goodbye = discord.ui.TextInput(label="ID salon au revoir (vide = désactivé)", required=False)
    msg_goodbye = discord.ui.TextInput(label="Message au revoir", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if self.ch_welcome.value:
            ch = interaction.guild.get_channel(int(self.ch_welcome.value))
            config["welcome_channel"] = ch.id if ch else None
        else:
            config["welcome_channel"] = None
        if self.msg_welcome.value:
            config["welcome_message"] = self.msg_welcome.value
        config["welcome_dm"] = self.dm.value.lower() in ["oui", "yes", "o", "y"]
        if self.ch_goodbye.value:
            ch = interaction.guild.get_channel(int(self.ch_goodbye.value))
            config["goodbye_channel"] = ch.id if ch else None
        else:
            config["goodbye_channel"] = None
        if self.msg_goodbye.value:
            config["goodbye_message"] = self.msg_goodbye.value
        await interaction.response.send_message("✅ Bienvenue/Au revoir configuré !", ephemeral=True)


class TicketModal(discord.ui.Modal, title="⚙️ Tickets"):
    ch_ticket = discord.ui.TextInput(label="ID salon (où poser le bouton ticket)", required=False)
    cat_ticket = discord.ui.TextInput(label="ID catégorie pour les tickets", required=False)
    role_support = discord.ui.TextInput(label="ID rôle support", required=False)
    ch_log = discord.ui.TextInput(label="ID salon logs tickets", required=False)
    msg = discord.ui.TextInput(label="Message du panel ticket", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        if self.ch_ticket.value: config["ticket_channel"] = int(self.ch_ticket.value)
        if self.cat_ticket.value: config["ticket_category"] = int(self.cat_ticket.value)
        if self.role_support.value: config["ticket_support_role"] = int(self.role_support.value)
        if self.ch_log.value: config["ticket_log_channel"] = int(self.ch_log.value)
        if self.msg.value: config["ticket_message"] = self.msg.value
        await interaction.response.send_message("✅ Tickets configurés !", ephemeral=True)


class AutoroleModal(discord.ui.Modal, title="⚙️ Auto-rôle"):
    roles = discord.ui.TextInput(label="IDs des rôles séparés par des virgules", placeholder="Ex: 111111, 222222")

    async def on_submit(self, interaction: discord.Interaction):
        ids = [r.strip() for r in self.roles.value.split(",") if r.strip().isdigit()]
        config["autorole"] = [int(i) for i in ids]
        roles_txt = ", ".join(f"<@&{i}>" for i in config["autorole"]) or "Aucun"
        await interaction.response.send_message(f"✅ Auto-rôle : {roles_txt}", ephemeral=True)


class LogsModal(discord.ui.Modal, title="⚙️ Logs"):
    ch_log = discord.ui.TextInput(label="ID du salon de logs", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            ch = interaction.guild.get_channel(int(self.ch_log.value))
            if not ch:
                return await interaction.response.send_message("❌ Salon introuvable.", ephemeral=True)
            config["log_channel"] = ch.id
            await interaction.response.send_message(f"✅ Logs → {ch.mention}", ephemeral=True)
        except:
            await interaction.response.send_message("❌ ID invalide.", ephemeral=True)


class AntispamModal(discord.ui.Modal, title="⚙️ Anti-Spam"):
    max_msg = discord.ui.TextInput(label="Nb max de messages avant sanction", default="5")
    interval = discord.ui.TextInput(label="Intervalle en secondes", default="3")
    action = discord.ui.TextInput(label="Action : warn / mute / kick / ban", default="mute")
    mute_dur = discord.ui.TextInput(label="Durée du mute (minutes)", default="10")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["antispam_max"] = int(self.max_msg.value)
            config["antispam_interval"] = int(self.interval.value)
            config["antispam_mute_duration"] = int(self.mute_dur.value)
            if self.action.value in ["warn", "mute", "kick", "ban"]:
                config["antispam_action"] = self.action.value
            config["antispam_enabled"] = True
            await interaction.response.send_message(
                f"✅ Anti-spam activé !\n`{config['antispam_max']} msg / {config['antispam_interval']}s` → **{config['antispam_action']}**", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Valeurs invalides.", ephemeral=True)


class AntiRaidModal(discord.ui.Modal, title="⚙️ Anti-Raid"):
    joins = discord.ui.TextInput(label="Nb de joins pour déclencher l'alerte", default="5")
    interval = discord.ui.TextInput(label="Intervalle en secondes", default="10")
    action = discord.ui.TextInput(label="Action : kick / ban / lockdown", default="kick")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["antiraid_joins"] = int(self.joins.value)
            config["antiraid_interval"] = int(self.interval.value)
            if self.action.value in ["kick", "ban", "lockdown"]:
                config["antiraid_action"] = self.action.value
            config["antiraid_enabled"] = True
            await interaction.response.send_message(
                f"✅ Anti-raid activé !\n`{config['antiraid_joins']} joins / {config['antiraid_interval']}s` → **{config['antiraid_action']}**", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Valeurs invalides.", ephemeral=True)


class AutomodModal(discord.ui.Modal, title="⚙️ Auto-Modération"):
    badwords = discord.ui.TextInput(label="Mots interdits (séparés par virgules)", required=False, placeholder="mot1, mot2, mot3")
    links = discord.ui.TextInput(label="Bloquer les liens ? (oui/non)", default="non")
    caps = discord.ui.TextInput(label="Bloquer les MAJUSCULES ? (oui/non)", default="non")
    action = discord.ui.TextInput(label="Action : delete / warn / mute", default="delete")

    async def on_submit(self, interaction: discord.Interaction):
        if self.badwords.value:
            config["automod_badwords"] = [w.strip() for w in self.badwords.value.split(",") if w.strip()]
        config["automod_links"] = self.links.value.lower() in ["oui", "yes", "o", "y"]
        config["automod_caps"] = self.caps.value.lower() in ["oui", "yes", "o", "y"]
        if self.action.value in ["delete", "warn", "mute"]:
            config["automod_action"] = self.action.value
        config["automod_enabled"] = True
        await interaction.response.send_message(
            f"✅ Auto-mod activé !\n"
            f"🚫 Mots interdits : `{len(config['automod_badwords'])}`\n"
            f"🔗 Liens bloqués : `{config['automod_links']}`\n"
            f"🔠 Caps bloqués : `{config['automod_caps']}`\n"
            f"⚡ Action : `{config['automod_action']}`", ephemeral=True)

# ================= PANEL VIEW =================

def build_panel_embed(guild):
    def s(val): return "🟢 Actif" if val else "🔴 Inactif"
    embed = discord.Embed(title="⚙️ Panel de Configuration", description=f"Serveur : **{guild.name}**\nClique sur un bouton pour configurer.", color=0x5865F2)
    embed.add_field(name="👋 Bienvenue", value=s(config["welcome_channel"]), inline=True)
    embed.add_field(name="🎫 Tickets", value=s(config["ticket_channel"]), inline=True)
    embed.add_field(name="🎭 Auto-rôle", value=s(config["autorole"]), inline=True)
    embed.add_field(name="📋 Logs", value=s(config["log_channel"]), inline=True)
    embed.add_field(name="🛡️ Anti-Spam", value=s(config["antispam_enabled"]), inline=True)
    embed.add_field(name="🚨 Anti-Raid", value=s(config["antiraid_enabled"]), inline=True)
    embed.add_field(name="🤖 Auto-Mod", value=s(config["automod_enabled"]), inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.set_footer(text="Panel de configuration")
    embed.timestamp = discord.utils.utcnow()
    return embed


class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="👋 Bienvenue", style=discord.ButtonStyle.primary, custom_id="panel_welcome", row=0)
    async def welcome_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WelcomeModal())

    @discord.ui.button(label="🎫 Tickets", style=discord.ButtonStyle.primary, custom_id="panel_tickets", row=0)
    async def tickets_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

    @discord.ui.button(label="🎭 Auto-rôle", style=discord.ButtonStyle.primary, custom_id="panel_autorole", row=0)
    async def autorole_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AutoroleModal())

    @discord.ui.button(label="📋 Logs", style=discord.ButtonStyle.secondary, custom_id="panel_logs", row=1)
    async def logs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LogsModal())

    @discord.ui.button(label="🛡️ Anti-Spam", style=discord.ButtonStyle.secondary, custom_id="panel_antispam", row=1)
    async def antispam_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AntispamModal())

    @discord.ui.button(label="🚨 Anti-Raid", style=discord.ButtonStyle.secondary, custom_id="panel_antiraid", row=1)
    async def antiraid_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AntiRaidModal())

    @discord.ui.button(label="🤖 Auto-Mod", style=discord.ButtonStyle.secondary, custom_id="panel_automod", row=2)
    async def automod_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AutomodModal())

    @discord.ui.button(label="🚀 Déployer les Tickets", style=discord.ButtonStyle.success, custom_id="panel_deploy", row=2)
    async def deploy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not config["ticket_channel"]:
            return await interaction.response.send_message("❌ Configure d'abord un salon dans **🎫 Tickets**.", ephemeral=True)
        channel = interaction.guild.get_channel(config["ticket_channel"])
        if not channel:
            return await interaction.response.send_message("❌ Salon introuvable.", ephemeral=True)
        embed = discord.Embed(title="🎫 Support — Ouvrir un ticket", description=config["ticket_message"], color=0x5865F2)
        embed.set_footer(text=interaction.guild.name)
        await channel.send(embed=embed, view=TicketOpenView())
        await interaction.response.send_message(f"✅ Panel ticket déployé dans {channel.mention} !", ephemeral=True)

    @discord.ui.button(label="🔴 OFF Anti-Spam", style=discord.ButtonStyle.danger, custom_id="panel_off_spam", row=3)
    async def off_spam(self, interaction: discord.Interaction, button: discord.ui.Button):
        config["antispam_enabled"] = False
        await interaction.response.send_message("🔴 Anti-spam désactivé.", ephemeral=True)

    @discord.ui.button(label="🔴 OFF Anti-Raid", style=discord.ButtonStyle.danger, custom_id="panel_off_raid", row=3)
    async def off_raid(self, interaction: discord.Interaction, button: discord.ui.Button):
        config["antiraid_enabled"] = False
        await interaction.response.send_message("🔴 Anti-raid désactivé.", ephemeral=True)

    @discord.ui.button(label="🔴 OFF Auto-Mod", style=discord.ButtonStyle.danger, custom_id="panel_off_automod", row=3)
    async def off_automod(self, interaction: discord.Interaction, button: discord.ui.Button):
        config["automod_enabled"] = False
        await interaction.response.send_message("🔴 Auto-modération désactivée.", ephemeral=True)

# ================= SLASH COMMANDS =================

@bot.tree.command(name="panel", description="Ouvre le panel de configuration")
@app_commands.default_permissions(administrator=True)
async def panel_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(embed=build_panel_embed(interaction.guild), view=PanelView(), ephemeral=True)


@bot.tree.command(name="lockdown", description="[ADMIN] Verrouille ou déverrouille tous les salons")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(action="lock ou unlock")
async def lockdown(interaction: discord.Interaction, action: str):
    locked = action.lower() == "lock"
    count = 0
    for ch in interaction.guild.text_channels:
        try:
            await ch.set_permissions(interaction.guild.default_role, send_messages=not locked)
            count += 1
        except: pass
    label = "🔒 Lockdown activé" if locked else "🔓 Lockdown désactivé"
    await interaction.response.send_message(f"{label} — {count} salons modifiés.", ephemeral=True)
    await send_log(interaction.guild, f"{'🔒' if locked else '🔓'} **{label}** par {interaction.user.mention}", 0xFF0000 if locked else 0x57F287)


@bot.tree.command(name="warn", description="Avertir un membre")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="Le membre", raison="La raison")
async def warn(interaction: discord.Interaction, member: discord.Member, raison: str = "Aucune raison"):
    embed = discord.Embed(description=f"⚠️ {member.mention} a reçu un avertissement.\nRaison : **{raison}**", color=0xFEE75C)
    await interaction.response.send_message(embed=embed)
    await send_log(interaction.guild, f"⚠️ **Warn** → {member.mention}\nPar : {interaction.user.mention}\nRaison : {raison}", 0xFEE75C)
    try: await member.send(embed=discord.Embed(description=f"⚠️ Tu as reçu un avertissement sur **{interaction.guild.name}**.\nRaison : {raison}", color=0xFEE75C))
    except: pass


@bot.tree.command(name="mute", description="Muter un membre")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="Le membre", duree="Durée en minutes", raison="La raison")
async def mute_cmd(interaction: discord.Interaction, member: discord.Member, duree: int = 10, raison: str = "Aucune raison"):
    await interaction.response.send_message(f"🔇 {member.mention} muté pour **{duree} min**.")
    await send_log(interaction.guild, f"🔇 **Mute** → {member.mention}\nDurée : {duree} min | Par : {interaction.user.mention}\nRaison : {raison}", 0xE67E22)
    asyncio.create_task(mute_member(interaction.guild, member, duree, raison))


@bot.tree.command(name="unmute", description="Démuter un membre")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="Le membre")
async def unmute_cmd(interaction: discord.Interaction, member: discord.Member):
    mute_role = interaction.guild.get_role(config["mute_role"]) if config["mute_role"] else discord.utils.get(interaction.guild.roles, name="Muted")
    if mute_role and mute_role in member.roles:
        await member.remove_roles(mute_role)
        await interaction.response.send_message(f"🔊 {member.mention} démute.")
    else:
        await interaction.response.send_message(f"❌ {member.mention} n'est pas muté.", ephemeral=True)


@bot.tree.command(name="kick", description="Expulser un membre")
@app_commands.default_permissions(kick_members=True)
@app_commands.describe(member="Le membre", raison="La raison")
async def kick_cmd(interaction: discord.Interaction, member: discord.Member, raison: str = "Aucune raison"):
    await member.kick(reason=raison)
    await interaction.response.send_message(f"👢 {member.mention} expulsé.")
    await send_log(interaction.guild, f"👢 **Kick** → {member.mention}\nPar : {interaction.user.mention} | Raison : {raison}", 0xE67E22)


@bot.tree.command(name="ban", description="Bannir un membre")
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(member="Le membre", raison="La raison")
async def ban_cmd(interaction: discord.Interaction, member: discord.Member, raison: str = "Aucune raison"):
    await member.ban(reason=raison)
    await interaction.response.send_message(f"🔨 {member.mention} banni.")
    await send_log(interaction.guild, f"🔨 **Ban** → {member.mention}\nPar : {interaction.user.mention} | Raison : {raison}", 0xED4245)


@bot.tree.command(name="unban", description="Débannir un utilisateur")
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(user_id="L'ID de l'utilisateur")
async def unban_cmd(interaction: discord.Interaction, user_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ {user.mention} débanni.", ephemeral=True)
        await send_log(interaction.guild, f"✅ **Unban** → {user.mention} par {interaction.user.mention}", 0x57F287)
    except:
        await interaction.response.send_message("❌ Utilisateur introuvable ou non banni.", ephemeral=True)


@bot.tree.command(name="clear", description="Supprimer des messages en masse")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(nombre="Nombre de messages (max 100)")
async def clear_cmd(interaction: discord.Interaction, nombre: int):
    if not 1 <= nombre <= 100:
        return await interaction.response.send_message("❌ Entre 1 et 100.", ephemeral=True)
    await interaction.response.send_message(f"🗑️ Suppression...", ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await send_log(interaction.guild, f"🗑️ **Clear** — {len(deleted)} messages supprimés dans {interaction.channel.mention} par {interaction.user.mention}", 0xFEE75C)


@bot.tree.command(name="userinfo", description="Infos sur un membre")
@app_commands.describe(member="Le membre (optionnel)")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    roles = [r.mention for r in member.roles if r != interaction.guild.default_role]
    embed = discord.Embed(title=f"👤 {member}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=str(member.id), inline=True)
    embed.add_field(name="Pseudo", value=member.display_name, inline=True)
    embed.add_field(name="Compte créé", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="A rejoint", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    embed.add_field(name=f"Rôles ({len(roles)})", value=" ".join(roles[:10]) if roles else "Aucun", inline=False)
    embed.set_footer(text="userinfo")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="serverinfo", description="Infos sur le serveur")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"🏠 {guild.name}", color=0x5865F2)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="ID", value=str(guild.id), inline=True)
    embed.add_field(name="Propriétaire", value=guild.owner.mention if guild.owner else "?", inline=True)
    embed.add_field(name="Membres", value=str(guild.member_count), inline=True)
    embed.add_field(name="Salons", value=str(len(guild.channels)), inline=True)
    embed.add_field(name="Rôles", value=str(len(guild.roles)), inline=True)
    embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)
    embed.add_field(name="Créé le", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
    embed.set_footer(text="serverinfo")
    await interaction.response.send_message(embed=embed)


# ================= ON READY =================

@bot.event
async def on_ready():
    bot.add_view(PanelView())
    bot.add_view(TicketOpenView())
    bot.add_view(TicketCloseView())
    await bot.tree.sync()
    print(f"✅ {bot.user} connecté !")
    print(f"⚙️  /panel prêt")

# ================= LANCEMENT =================

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        raise ValueError("❌ TOKEN manquant !")
    bot.run(TOKEN)
