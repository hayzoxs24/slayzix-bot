import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime
import re
import random
import time
import io

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.start_time = time.time()

# ================= CONFIG GLOBALE =================

config = {
    "welcome_channel": None,
    "welcome_message": "Bienvenue {mention} sur **{server}** ! Tu es le membre n°{count} 🎉",
    "welcome_dm": False,
    "goodbye_channel": None,
    "goodbye_message": "**{name}** vient de quitter {server}. Il reste {count} membres.",
    "ticket_channel": None,
    "ticket_category": None,
    "ticket_support_role": None,
    "ticket_log_channel": None,
    "ticket_message": "Clique sur le bouton ci-dessous pour ouvrir un ticket.",
    "ticket_topics": [],
    "autorole": [],
    "log_channel": None,
    "antispam_enabled": False,
    "antispam_max": 5,
    "antispam_interval": 3,
    "antispam_action": "mute",
    "antispam_mute_duration": 10,
    "antiraid_enabled": False,
    "antiraid_joins": 5,
    "antiraid_interval": 10,
    "antiraid_action": "kick",
    "automod_enabled": False,
    "automod_badwords": [],
    "automod_links": False,
    "automod_caps": False,
    "automod_action": "delete",
    "mute_role": None,
    "member_counter_channel": None,
    "reaction_roles": {},
}

warns_db = {}
tickets_db = {}
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
    embed.set_footer(text="Logs")
    await channel.send(embed=embed)


async def mute_member(guild, member, duration_minutes=10, reason="Auto-modération"):
    mute_role = guild.get_role(config["mute_role"]) if config["mute_role"] else discord.utils.get(guild.roles, name="Muted")
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


def get_warns(guild_id, user_id):
    return warns_db.get(guild_id, {}).get(user_id, [])


def add_warn(guild_id, user_id, raison, by):
    if guild_id not in warns_db:
        warns_db[guild_id] = {}
    if user_id not in warns_db[guild_id]:
        warns_db[guild_id][user_id] = []
    warns_db[guild_id][user_id].append({
        "raison": raison, "by": by,
        "at": datetime.utcnow().strftime("%d/%m/%Y %H:%M")
    })
    return len(warns_db[guild_id][user_id])


async def update_member_counter(guild):
    if not config["member_counter_channel"]:
        return
    ch = guild.get_channel(config["member_counter_channel"])
    if ch:
        try:
            await ch.edit(name=f"👥 Membres : {guild.member_count}")
        except:
            pass

# ================= EVENTS =================

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return await bot.process_commands(message)
    member = message.author
    guild = message.guild

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
            return

    for role_id in config["autorole"]:
        role = guild.get_role(role_id)
        if role:
            try: await member.add_roles(role)
            except: pass

    if config["welcome_channel"]:
        channel = guild.get_channel(config["welcome_channel"])
        if channel:
            msg = config["welcome_message"]\
                .replace("{mention}", member.mention).replace("{name}", member.name)\
                .replace("{server}", guild.name).replace("{count}", str(guild.member_count))
            embed = discord.Embed(description=msg, color=0x57F287)
            embed.set_author(name="Bienvenue !", icon_url=member.display_avatar.url)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"{guild.name} • Membre n°{guild.member_count}")
            embed.timestamp = discord.utils.utcnow()
            await channel.send(embed=embed)

    if config["welcome_dm"]:
        try:
            msg = config["welcome_message"]\
                .replace("{mention}", member.name).replace("{name}", member.name)\
                .replace("{server}", guild.name).replace("{count}", str(guild.member_count))
            await member.send(embed=discord.Embed(title=f"Bienvenue sur {guild.name} !", description=msg, color=0x57F287))
        except: pass

    await update_member_counter(guild)
    await send_log(guild, f"📥 **Membre rejoint** → {member.mention} (`{member.id}`)\nCompte créé : <t:{int(member.created_at.timestamp())}:R>", 0x57F287)


@bot.event
async def on_member_remove(member):
    guild = member.guild
    if config["goodbye_channel"]:
        channel = guild.get_channel(config["goodbye_channel"])
        if channel:
            msg = config["goodbye_message"]\
                .replace("{mention}", member.mention).replace("{name}", member.name)\
                .replace("{server}", guild.name).replace("{count}", str(guild.member_count))
            embed = discord.Embed(description=msg, color=0xED4245)
            embed.set_author(name="Départ du serveur", icon_url=member.display_avatar.url)
            embed.timestamp = discord.utils.utcnow()
            await channel.send(embed=embed)
    await update_member_counter(guild)
    await send_log(guild, f"📤 **Membre parti** → {member.mention} (`{member.id}`)", 0xED4245)


@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    await send_log(message.guild, f"🗑️ **Message supprimé** par {message.author.mention}\nSalon : {message.channel.mention}\n> {message.content[:300] or '*Aucun contenu*'}", 0xFEE75C)


@bot.event
async def on_member_ban(guild, user):
    await send_log(guild, f"🔨 **Banni** → {user.mention} (`{user.id}`)", 0xED4245)


@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id: return
    msg_id = str(payload.message_id)
    if msg_id not in config["reaction_roles"]: return
    role_id = config["reaction_roles"][msg_id].get(str(payload.emoji))
    if not role_id: return
    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    member = guild.get_member(payload.user_id)
    role = guild.get_role(role_id)
    if member and role:
        await member.add_roles(role)


@bot.event
async def on_raw_reaction_remove(payload):
    msg_id = str(payload.message_id)
    if msg_id not in config["reaction_roles"]: return
    role_id = config["reaction_roles"][msg_id].get(str(payload.emoji))
    if not role_id: return
    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    member = guild.get_member(payload.user_id)
    role = guild.get_role(role_id)
    if member and role:
        await member.remove_roles(role)

# =====================================================================
# ====================== SYSTÈME DE TICKETS ==========================
# =====================================================================

class AddUserModal(discord.ui.Modal, title="➕ Ajouter un utilisateur"):
    user_id = discord.ui.TextInput(label="ID de l'utilisateur")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(int(self.user_id.value))
            if not member:
                return await interaction.response.send_message("❌ Membre introuvable.", ephemeral=True)
            await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
            await interaction.response.send_message(f"✅ {member.mention} ajouté au ticket.")
        except:
            await interaction.response.send_message("❌ ID invalide.", ephemeral=True)


class RemoveUserModal(discord.ui.Modal, title="➖ Retirer un utilisateur"):
    user_id = discord.ui.TextInput(label="ID de l'utilisateur")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = interaction.guild.get_member(int(self.user_id.value))
            if not member:
                return await interaction.response.send_message("❌ Membre introuvable.", ephemeral=True)
            await interaction.channel.set_permissions(member, read_messages=False, send_messages=False)
            await interaction.response.send_message(f"✅ {member.mention} retiré du ticket.")
        except:
            await interaction.response.send_message("❌ ID invalide.", ephemeral=True)


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger, custom_id="tkt_close", row=0)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=30)
        confirm = discord.ui.Button(label="✅ Confirmer", style=discord.ButtonStyle.danger)
        cancel = discord.ui.Button(label="❌ Annuler", style=discord.ButtonStyle.secondary)

        async def confirm_cb(i: discord.Interaction):
            ch_id = i.channel.id
            ticket_info = tickets_db.get(ch_id, {})
            if config["ticket_log_channel"]:
                log_ch = i.guild.get_channel(config["ticket_log_channel"])
                if log_ch:
                    log_embed = discord.Embed(title="🔒 Ticket fermé", color=0xED4245, timestamp=discord.utils.utcnow())
                    log_embed.add_field(name="Salon", value=i.channel.name, inline=True)
                    log_embed.add_field(name="Fermé par", value=i.user.mention, inline=True)
                    log_embed.add_field(name="Sujet", value=ticket_info.get("topic", "?"), inline=True)
                    await log_ch.send(embed=log_embed)
            tickets_db.pop(ch_id, None)
            await i.response.send_message("🔒 Fermeture dans 5 secondes...")
            await asyncio.sleep(5)
            await i.channel.delete()

        async def cancel_cb(i: discord.Interaction):
            await i.response.edit_message(content="❌ Annulé.", view=None)

        confirm.callback = confirm_cb
        cancel.callback = cancel_cb
        view.add_item(confirm)
        view.add_item(cancel)
        await interaction.response.send_message("❓ Confirmer la fermeture ?", view=view, ephemeral=True)

    @discord.ui.button(label="✋ Prendre en charge", style=discord.ButtonStyle.success, custom_id="tkt_claim", row=0)
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch_id = interaction.channel.id
        if ch_id not in tickets_db:
            return await interaction.response.send_message("❌ Ticket introuvable.", ephemeral=True)
        if tickets_db[ch_id].get("claimed_by"):
            return await interaction.response.send_message("❌ Ce ticket est déjà pris en charge.", ephemeral=True)
        tickets_db[ch_id]["claimed_by"] = interaction.user.id
        button.label = f"✋ Pris par {interaction.user.display_name}"
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=discord.Embed(description=f"✋ **{interaction.user.mention}** a pris en charge ce ticket.", color=0x57F287))
        await send_log(interaction.guild, f"✋ **Ticket pris en charge** → `{interaction.channel.name}`\nPar : {interaction.user.mention}", 0x57F287)

    @discord.ui.button(label="📄 Transcript", style=discord.ButtonStyle.secondary, custom_id="tkt_transcript", row=0)
    async def transcript_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        messages = []
        async for msg in interaction.channel.history(limit=500, oldest_first=True):
            if not msg.author.bot:
                messages.append(f"[{msg.created_at.strftime('%d/%m/%Y %H:%M')}] {msg.author}: {msg.content}")
        if not messages:
            return await interaction.followup.send("❌ Aucun message.", ephemeral=True)
        content = "\n".join(messages).encode("utf-8")
        file = discord.File(fp=io.BytesIO(content), filename=f"transcript-{interaction.channel.name}.txt")
        await interaction.followup.send("📄 Transcript :", file=file, ephemeral=True)
        if config["ticket_log_channel"]:
            log_ch = interaction.guild.get_channel(config["ticket_log_channel"])
            if log_ch:
                file2 = discord.File(fp=io.BytesIO(content), filename=f"transcript-{interaction.channel.name}.txt")
                await log_ch.send(embed=discord.Embed(description=f"📄 **Transcript** → `{interaction.channel.name}`\nPar {interaction.user.mention}", color=0x5865F2), file=file2)

    @discord.ui.button(label="➕ Ajouter", style=discord.ButtonStyle.secondary, custom_id="tkt_add", row=1)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddUserModal())

    @discord.ui.button(label="➖ Retirer", style=discord.ButtonStyle.secondary, custom_id="tkt_remove", row=1)
    async def remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveUserModal())


class TicketTopicSelect(discord.ui.Select):
    def __init__(self, topics):
        options = [
            discord.SelectOption(label=t["label"], description=t.get("desc", ""), emoji=t.get("emoji", "🎫"))
            for t in topics
        ]
        super().__init__(placeholder="📋 Choisis le sujet...", options=options, custom_id="tkt_topic_select")

    async def callback(self, interaction: discord.Interaction):
        await open_ticket(interaction, self.values[0])


class TicketOpenView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Ouvrir un ticket", style=discord.ButtonStyle.primary, custom_id="tkt_open_btn")
    async def open_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        topics = config["ticket_topics"]
        if topics:
            view = discord.ui.View(timeout=60)
            view.add_item(TicketTopicSelect(topics))
            await interaction.response.send_message("📋 Choisis le sujet de ton ticket :", view=view, ephemeral=True)
        else:
            await open_ticket(interaction, "Support général")


async def open_ticket(interaction: discord.Interaction, topic: str):
    guild = interaction.guild
    user = interaction.user

    existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.id}")
    if existing:
        msg = f"❌ Tu as déjà un ticket → {existing.mention}"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
    }
    if config["ticket_support_role"]:
        role = guild.get_role(config["ticket_support_role"])
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    category = guild.get_channel(config["ticket_category"]) if config["ticket_category"] else None
    if not category:
        category = discord.utils.get(guild.categories, name="🎫 TICKETS") or await guild.create_category("🎫 TICKETS")

    ticket_num = len([c for c in guild.channels if c.name.startswith("ticket-")]) + 1
    channel = await guild.create_text_channel(
        f"ticket-{user.id}", overwrites=overwrites, category=category,
        topic=f"Ticket de {user} | Sujet : {topic}"
    )

    tickets_db[channel.id] = {
        "user_id": user.id, "topic": topic,
        "opened_at": datetime.utcnow(), "claimed_by": None, "ticket_num": ticket_num,
    }

    embed = discord.Embed(title=f"🎫 Ticket #{ticket_num:04d}", color=0x5865F2, timestamp=discord.utils.utcnow())
    embed.set_author(name=str(user), icon_url=user.display_avatar.url)
    embed.add_field(name="👤 Ouvert par", value=user.mention, inline=True)
    embed.add_field(name="📋 Sujet", value=f"**{topic}**", inline=True)
    embed.add_field(name="📅 Ouvert le", value=f"<t:{int(datetime.utcnow().timestamp())}:F>", inline=False)
    embed.add_field(name="ℹ️ Info", value="L'équipe va te répondre rapidement.\nUtilise les boutons ci-dessous pour gérer ton ticket.", inline=False)
    embed.set_footer(text="Système de tickets")

    ping_msg = user.mention
    if config["ticket_support_role"]:
        ping_msg += f" <@&{config['ticket_support_role']}>"

    await channel.send(ping_msg, embed=embed, view=TicketControlView())

    if config["ticket_log_channel"]:
        log_ch = guild.get_channel(config["ticket_log_channel"])
        if log_ch:
            log_embed = discord.Embed(title="📩 Ticket ouvert", color=0x57F287, timestamp=discord.utils.utcnow())
            log_embed.add_field(name="Créateur", value=user.mention, inline=True)
            log_embed.add_field(name="Sujet", value=topic, inline=True)
            log_embed.add_field(name="Salon", value=channel.mention, inline=True)
            await log_ch.send(embed=log_embed)

    resp = f"✅ Ton ticket a été créé → {channel.mention}"
    if interaction.response.is_done():
        await interaction.followup.send(resp, ephemeral=True)
    else:
        await interaction.response.send_message(resp, ephemeral=True)

# =====================================================================
# ========================= MODALS PANEL =============================
# =====================================================================

class WelcomeModal(discord.ui.Modal, title="⚙️ Bienvenue / Au revoir"):
    ch_welcome = discord.ui.TextInput(label="ID salon bienvenue (vide = désactivé)", required=False)
    msg_welcome = discord.ui.TextInput(label="Message ({mention} {name} {server} {count})", style=discord.TextStyle.paragraph, required=False)
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


class TicketConfigModal(discord.ui.Modal, title="⚙️ Configuration Tickets"):
    ch_ticket = discord.ui.TextInput(label="ID salon (bouton ticket)", required=False)
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


class TicketTopicsModal(discord.ui.Modal, title="⚙️ Sujets de tickets"):
    topics_raw = discord.ui.TextInput(
        label="Sujets (emoji|label|description, 1 par ligne)",
        style=discord.TextStyle.paragraph,
        placeholder="🛒|Commande|Problème avec une commande\n🐛|Bug|Signaler un bug\n💬|Question|Poser une question"
    )

    async def on_submit(self, interaction: discord.Interaction):
        topics = []
        for line in self.topics_raw.value.strip().split("\n"):
            parts = line.split("|")
            if len(parts) >= 2:
                topics.append({"emoji": parts[0].strip(), "label": parts[1].strip(), "desc": parts[2].strip() if len(parts) > 2 else ""})
        config["ticket_topics"] = topics[:25]
        await interaction.response.send_message(f"✅ **{len(topics)} sujets** configurés !", ephemeral=True)


class AutoroleModal(discord.ui.Modal, title="⚙️ Auto-rôle"):
    roles = discord.ui.TextInput(label="IDs des rôles séparés par des virgules", placeholder="111111, 222222")

    async def on_submit(self, interaction: discord.Interaction):
        ids = [r.strip() for r in self.roles.value.split(",") if r.strip().isdigit()]
        config["autorole"] = [int(i) for i in ids]
        roles_txt = ", ".join(f"<@&{i}>" for i in config["autorole"]) or "Aucun"
        await interaction.response.send_message(f"✅ Auto-rôle : {roles_txt}", ephemeral=True)


class LogsModal(discord.ui.Modal, title="⚙️ Logs"):
    ch_log = discord.ui.TextInput(label="ID du salon de logs")

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
            await interaction.response.send_message(f"✅ Anti-spam activé ! `{config['antispam_max']} msg/{config['antispam_interval']}s` → **{config['antispam_action']}**", ephemeral=True)
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
            await interaction.response.send_message(f"✅ Anti-raid activé ! `{config['antiraid_joins']} joins/{config['antiraid_interval']}s` → **{config['antiraid_action']}**", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Valeurs invalides.", ephemeral=True)


class AutomodModal(discord.ui.Modal, title="⚙️ Auto-Modération"):
    badwords = discord.ui.TextInput(label="Mots interdits (séparés par virgules)", required=False)
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
            f"✅ Auto-mod activé !\n🚫 Mots : `{len(config['automod_badwords'])}` | 🔗 Liens : `{config['automod_links']}` | 🔠 Caps : `{config['automod_caps']}` | ⚡ `{config['automod_action']}`",
            ephemeral=True)


class CounterModal(discord.ui.Modal, title="⚙️ Compteur de membres"):
    ch_id = discord.ui.TextInput(label="ID du salon vocal (compteur)", placeholder="Crée un salon vocal et colle son ID")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            ch = interaction.guild.get_channel(int(self.ch_id.value))
            if not ch:
                return await interaction.response.send_message("❌ Salon introuvable.", ephemeral=True)
            config["member_counter_channel"] = ch.id
            await update_member_counter(interaction.guild)
            await interaction.response.send_message(f"✅ Compteur activé sur {ch.mention} !", ephemeral=True)
        except:
            await interaction.response.send_message("❌ ID invalide.", ephemeral=True)


class ReactionRoleModal(discord.ui.Modal, title="⚙️ Rôles par réaction"):
    msg_id = discord.ui.TextInput(label="ID du message cible")
    pairs = discord.ui.TextInput(
        label="Paires emoji|roleID (1 par ligne)",
        style=discord.TextStyle.paragraph,
        placeholder="✅|123456789\n🔵|987654321"
    )

    async def on_submit(self, interaction: discord.Interaction):
        msg_id = self.msg_id.value.strip()
        rr = {}
        for line in self.pairs.value.strip().split("\n"):
            parts = line.split("|")
            if len(parts) == 2:
                emoji, role_id = parts[0].strip(), parts[1].strip()
                if role_id.isdigit():
                    rr[emoji] = int(role_id)
        config["reaction_roles"][msg_id] = rr
        await interaction.response.send_message(f"✅ **{len(rr)} rôles par réaction** configurés !", ephemeral=True)

# =====================================================================
# =========================== PANEL VIEW =============================
# =====================================================================

def build_panel_embed(guild):
    def s(val): return "🟢 Actif" if val else "🔴 Inactif"
    embed = discord.Embed(title="⚙️ Panel de Configuration", description=f"**{guild.name}** — Clique pour configurer.", color=0x5865F2)
    embed.add_field(name="👋 Bienvenue", value=s(config["welcome_channel"]), inline=True)
    embed.add_field(name="🎫 Tickets", value=s(config["ticket_channel"]), inline=True)
    embed.add_field(name="🎭 Auto-rôle", value=s(config["autorole"]), inline=True)
    embed.add_field(name="📋 Logs", value=s(config["log_channel"]), inline=True)
    embed.add_field(name="🛡️ Anti-Spam", value=s(config["antispam_enabled"]), inline=True)
    embed.add_field(name="🚨 Anti-Raid", value=s(config["antiraid_enabled"]), inline=True)
    embed.add_field(name="🤖 Auto-Mod", value=s(config["automod_enabled"]), inline=True)
    embed.add_field(name="👥 Compteur", value=s(config["member_counter_channel"]), inline=True)
    embed.add_field(name="🎭 Reaction Roles", value=s(config["reaction_roles"]), inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.set_footer(text="Panel de configuration")
    embed.timestamp = discord.utils.utcnow()
    return embed


class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="👋 Bienvenue", style=discord.ButtonStyle.primary, custom_id="panel_welcome", row=0)
    async def welcome_btn(self, interaction, button):
        await interaction.response.send_modal(WelcomeModal())

    @discord.ui.button(label="🎫 Tickets", style=discord.ButtonStyle.primary, custom_id="panel_tickets", row=0)
    async def tickets_btn(self, interaction, button):
        await interaction.response.send_modal(TicketConfigModal())

    @discord.ui.button(label="📋 Sujets Tickets", style=discord.ButtonStyle.primary, custom_id="panel_ticket_topics", row=0)
    async def ticket_topics_btn(self, interaction, button):
        await interaction.response.send_modal(TicketTopicsModal())

    @discord.ui.button(label="🚀 Déployer Tickets", style=discord.ButtonStyle.success, custom_id="panel_deploy", row=0)
    async def deploy_btn(self, interaction, button):
        if not config["ticket_channel"]:
            return await interaction.response.send_message("❌ Configure d'abord un salon dans **🎫 Tickets**.", ephemeral=True)
        channel = interaction.guild.get_channel(config["ticket_channel"])
        if not channel:
            return await interaction.response.send_message("❌ Salon introuvable.", ephemeral=True)
        embed = discord.Embed(title="🎫 Support — Ouvrir un ticket", description=config["ticket_message"], color=0x5865F2)
        embed.set_footer(text=interaction.guild.name)
        await channel.send(embed=embed, view=TicketOpenView())
        await interaction.response.send_message(f"✅ Panel ticket déployé dans {channel.mention} !", ephemeral=True)

    @discord.ui.button(label="🎭 Auto-rôle", style=discord.ButtonStyle.secondary, custom_id="panel_autorole", row=1)
    async def autorole_btn(self, interaction, button):
        await interaction.response.send_modal(AutoroleModal())

    @discord.ui.button(label="📋 Logs", style=discord.ButtonStyle.secondary, custom_id="panel_logs", row=1)
    async def logs_btn(self, interaction, button):
        await interaction.response.send_modal(LogsModal())

    @discord.ui.button(label="👥 Compteur", style=discord.ButtonStyle.secondary, custom_id="panel_counter", row=1)
    async def counter_btn(self, interaction, button):
        await interaction.response.send_modal(CounterModal())

    @discord.ui.button(label="🎭 Reaction Roles", style=discord.ButtonStyle.secondary, custom_id="panel_rr", row=1)
    async def rr_btn(self, interaction, button):
        await interaction.response.send_modal(ReactionRoleModal())

    @discord.ui.button(label="🛡️ Anti-Spam", style=discord.ButtonStyle.danger, custom_id="panel_antispam", row=2)
    async def antispam_btn(self, interaction, button):
        await interaction.response.send_modal(AntispamModal())

    @discord.ui.button(label="🚨 Anti-Raid", style=discord.ButtonStyle.danger, custom_id="panel_antiraid", row=2)
    async def antiraid_btn(self, interaction, button):
        await interaction.response.send_modal(AntiRaidModal())

    @discord.ui.button(label="🤖 Auto-Mod", style=discord.ButtonStyle.danger, custom_id="panel_automod", row=2)
    async def automod_btn(self, interaction, button):
        await interaction.response.send_modal(AutomodModal())

    @discord.ui.button(label="🔴 OFF Spam", style=discord.ButtonStyle.secondary, custom_id="panel_off_spam", row=3)
    async def off_spam(self, interaction, button):
        config["antispam_enabled"] = False
        await interaction.response.send_message("🔴 Anti-spam désactivé.", ephemeral=True)

    @discord.ui.button(label="🔴 OFF Raid", style=discord.ButtonStyle.secondary, custom_id="panel_off_raid", row=3)
    async def off_raid(self, interaction, button):
        config["antiraid_enabled"] = False
        await interaction.response.send_message("🔴 Anti-raid désactivé.", ephemeral=True)

    @discord.ui.button(label="🔴 OFF AutoMod", style=discord.ButtonStyle.secondary, custom_id="panel_off_automod", row=3)
    async def off_automod(self, interaction, button):
        config["automod_enabled"] = False
        await interaction.response.send_message("🔴 Auto-modération désactivée.", ephemeral=True)

# =====================================================================
# ========================= SLASH COMMANDS ===========================
# =====================================================================

@bot.tree.command(name="panel", description="Ouvre le panel de configuration")
@app_commands.default_permissions(administrator=True)
async def panel_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(embed=build_panel_embed(interaction.guild), view=PanelView(), ephemeral=True)


@bot.tree.command(name="ping", description="Latence du bot")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    color = 0x57F287 if latency < 100 else 0xFEE75C if latency < 200 else 0xED4245
    await interaction.response.send_message(embed=discord.Embed(title="🏓 Pong !", description=f"Latence : **{latency}ms**", color=color))


@bot.tree.command(name="botinfo", description="Informations sur le bot")
async def botinfo(interaction: discord.Interaction):
    uptime = int(time.time() - bot.start_time)
    h, r = divmod(uptime, 3600)
    m, s = divmod(r, 60)
    embed = discord.Embed(title="🤖 Bot Info", color=0x5865F2)
    embed.add_field(name="Nom", value=str(bot.user), inline=True)
    embed.add_field(name="Serveurs", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="Latence", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="Uptime", value=f"{h}h {m}m {s}s", inline=True)
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="avatar", description="Affiche l'avatar d'un membre")
@app_commands.describe(member="Le membre")
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"🖼️ Avatar de {member.display_name}", color=member.color)
    embed.set_image(url=member.display_avatar.url)
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Voir en plein écran", url=str(member.display_avatar.url), style=discord.ButtonStyle.link))
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="userinfo", description="Infos sur un membre")
@app_commands.describe(member="Le membre")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    roles = [r.mention for r in member.roles if r != interaction.guild.default_role]
    embed = discord.Embed(title=f"👤 {member}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=str(member.id), inline=True)
    embed.add_field(name="Pseudo", value=member.display_name, inline=True)
    embed.add_field(name="Warns", value=str(len(get_warns(interaction.guild.id, member.id))), inline=True)
    embed.add_field(name="Compte créé", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="A rejoint", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    embed.add_field(name=f"Rôles ({len(roles)})", value=" ".join(roles[:10]) if roles else "Aucun", inline=False)
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
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="warn", description="Avertir un membre")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="Le membre", raison="La raison")
async def warn(interaction: discord.Interaction, member: discord.Member, raison: str = "Aucune raison"):
    count = add_warn(interaction.guild.id, member.id, raison, str(interaction.user))
    embed = discord.Embed(description=f"⚠️ {member.mention} averti. (`{count}` warn(s))\nRaison : **{raison}**", color=0xFEE75C)
    await interaction.response.send_message(embed=embed)
    await send_log(interaction.guild, f"⚠️ **Warn** → {member.mention} ({count} total)\nPar : {interaction.user.mention} | Raison : {raison}", 0xFEE75C)
    try:
        await member.send(embed=discord.Embed(description=f"⚠️ Avertissement sur **{interaction.guild.name}**.\nRaison : {raison} | Total : {count}", color=0xFEE75C))
    except: pass


@bot.tree.command(name="warns", description="Voir les avertissements d'un membre")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="Le membre")
async def warns_cmd(interaction: discord.Interaction, member: discord.Member):
    warns_list = get_warns(interaction.guild.id, member.id)
    embed = discord.Embed(title=f"⚠️ Avertissements de {member}", color=0xFEE75C)
    embed.set_thumbnail(url=member.display_avatar.url)
    if not warns_list:
        embed.description = "✅ Aucun avertissement."
    else:
        for i, w in enumerate(warns_list, 1):
            embed.add_field(name=f"Warn #{i}", value=f"Raison : {w['raison']}\nPar : {w['by']} | Le : {w['at']}", inline=False)
    embed.set_footer(text=f"Total : {len(warns_list)} warn(s)")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="clearwarns", description="Supprimer tous les warns d'un membre")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(member="Le membre")
async def clearwarns(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild.id in warns_db:
        warns_db[interaction.guild.id][member.id] = []
    await interaction.response.send_message(f"✅ Warns de {member.mention} supprimés.", ephemeral=True)


@bot.tree.command(name="mute", description="Muter un membre")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="Le membre", duree="Durée en minutes", raison="La raison")
async def mute_cmd(interaction: discord.Interaction, member: discord.Member, duree: int = 10, raison: str = "Aucune raison"):
    await interaction.response.send_message(f"🔇 {member.mention} muté **{duree} min**.")
    await send_log(interaction.guild, f"🔇 **Mute** → {member.mention} | {duree} min | Par : {interaction.user.mention} | Raison : {raison}", 0xE67E22)
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
    await send_log(interaction.guild, f"👢 **Kick** → {member.mention} | Par : {interaction.user.mention} | Raison : {raison}", 0xE67E22)


@bot.tree.command(name="ban", description="Bannir un membre")
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(member="Le membre", raison="La raison")
async def ban_cmd(interaction: discord.Interaction, member: discord.Member, raison: str = "Aucune raison"):
    await member.ban(reason=raison)
    await interaction.response.send_message(f"🔨 {member.mention} banni.")
    await send_log(interaction.guild, f"🔨 **Ban** → {member.mention} | Par : {interaction.user.mention} | Raison : {raison}", 0xED4245)


@bot.tree.command(name="unban", description="Débannir un utilisateur")
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(user_id="L'ID de l'utilisateur")
async def unban_cmd(interaction: discord.Interaction, user_id: str):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ {user.mention} débanni.", ephemeral=True)
    except:
        await interaction.response.send_message("❌ Utilisateur introuvable.", ephemeral=True)


@bot.tree.command(name="clear", description="Supprimer des messages en masse")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(nombre="Nombre de messages (max 100)")
async def clear_cmd(interaction: discord.Interaction, nombre: int):
    if not 1 <= nombre <= 100:
        return await interaction.response.send_message("❌ Entre 1 et 100.", ephemeral=True)
    await interaction.response.send_message("🗑️ Suppression...", ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await send_log(interaction.guild, f"🗑️ **Clear** — {len(deleted)} messages dans {interaction.channel.mention} par {interaction.user.mention}", 0xFEE75C)


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
    await interaction.response.send_message(f"{label} — {count} salons.", ephemeral=True)
    await send_log(interaction.guild, f"{'🔒' if locked else '🔓'} **{label}** par {interaction.user.mention}", 0xFF0000 if locked else 0x57F287)


@bot.tree.command(name="tickets", description="Voir les tickets ouverts")
@app_commands.default_permissions(manage_messages=True)
async def tickets_list(interaction: discord.Interaction):
    if not tickets_db:
        return await interaction.response.send_message("📭 Aucun ticket ouvert.", ephemeral=True)
    embed = discord.Embed(title="🎫 Tickets ouverts", color=0x5865F2, timestamp=discord.utils.utcnow())
    for ch_id, info in tickets_db.items():
        ch = interaction.guild.get_channel(ch_id)
        user = interaction.guild.get_member(info["user_id"])
        claimed_member = interaction.guild.get_member(info["claimed_by"]) if info.get("claimed_by") else None
        claimed_txt = claimed_member.mention if claimed_member else "Non pris en charge"
        if ch:
            embed.add_field(name=f"#{ch.name}", value=f"👤 {user.mention if user else '?'} | 📋 {info['topic']}\n✋ {claimed_txt}", inline=False)
    embed.set_footer(text=f"{len(tickets_db)} ticket(s) ouvert(s)")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="poll", description="Créer un sondage")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(question="La question", choix="Choix séparés par | (vide = oui/non)")
async def poll(interaction: discord.Interaction, question: str, choix: str = None):
    if choix:
        options = [c.strip() for c in choix.split("|") if c.strip()][:10]
        emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        description = "\n".join(f"{emojis[i]} {opt}" for i, opt in enumerate(options))
        embed = discord.Embed(title=f"📊 {question}", description=description, color=0x5865F2, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Sondage par {interaction.user}")
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        for i in range(len(options)):
            await msg.add_reaction(emojis[i])
    else:
        embed = discord.Embed(title=f"📊 {question}", description="✅ Pour\n❌ Contre", color=0x5865F2, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Sondage par {interaction.user}")
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")


@bot.tree.command(name="announce", description="Envoyer une annonce formatée")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(salon="Le salon cible", titre="Titre", message="Le message", mention="@everyone / @here")
async def announce(interaction: discord.Interaction, salon: discord.TextChannel, titre: str, message: str, mention: str = None):
    embed = discord.Embed(title=f"📢 {titre}", description=message, color=0xFFD700, timestamp=discord.utils.utcnow())
    embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_footer(text=f"Annonce par {interaction.user}")
    await salon.send(content=mention or "", embed=embed)
    await interaction.response.send_message(f"✅ Annonce envoyée dans {salon.mention} !", ephemeral=True)


@bot.tree.command(name="giveaway", description="Lancer un giveaway")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(salon="Le salon", duree="Durée en minutes", gagnants="Nb de gagnants", prix="Le prix")
async def giveaway(interaction: discord.Interaction, salon: discord.TextChannel, duree: int, gagnants: int, prix: str):
    end_time = int(time.time()) + duree * 60
    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=f"**Prix :** {prix}\n\nRéagis avec 🎉 pour participer !\n\n**Fin :** <t:{end_time}:R>\n**Gagnants :** {gagnants}",
        color=0xFFD700, timestamp=discord.utils.utcnow()
    )
    embed.set_footer(text=f"Lancé par {interaction.user}")
    await interaction.response.send_message(f"✅ Giveaway lancé dans {salon.mention} !", ephemeral=True)
    msg = await salon.send(embed=embed)
    await msg.add_reaction("🎉")

    await asyncio.sleep(duree * 60)

    msg = await salon.fetch_message(msg.id)
    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    users = [u async for u in reaction.users() if not u.bot]

    if not users:
        end_embed = discord.Embed(title="🎉 GIVEAWAY TERMINÉ", description="Aucun participant 😢", color=0xED4245)
        await msg.edit(embed=end_embed)
        return

    winners = random.sample(users, min(gagnants, len(users)))
    winners_mention = ", ".join(w.mention for w in winners)
    end_embed = discord.Embed(
        title="🎉 GIVEAWAY TERMINÉ !",
        description=f"**Prix :** {prix}\n\n🏆 **Gagnant(s) :** {winners_mention}",
        color=0x57F287, timestamp=discord.utils.utcnow()
    )
    end_embed.set_footer(text=f"Lancé par {interaction.user}")
    await msg.edit(embed=end_embed)
    await salon.send(f"🎊 Félicitations {winners_mention} ! Vous gagnez **{prix}** !")

# =====================================================================
# ============================= ON READY =============================
# =====================================================================

@bot.event
async def on_ready():
    bot.add_view(PanelView())
    bot.add_view(TicketOpenView())
    bot.add_view(TicketControlView())
    await bot.tree.sync()
    print(f"✅ {bot.user} connecté !")
    print(f"⚙️  /panel | Tickets avancés | Warns | Giveaway | Poll | Announce | Reaction Roles | Compteur")

if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        raise ValueError("❌ TOKEN manquant !")
    bot.run(TOKEN)
