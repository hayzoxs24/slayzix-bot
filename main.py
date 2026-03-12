import discord, asyncio, json, os, time as time_module
from discord.ext import commands
from datetime import datetime
from collections import defaultdict

# ── Intents & Bot ──────────────────────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="*", intents=intents)

BANNER_URL = "https://i.ibb.co/fdJxKj7c/BANNIERE.png"
RED = discord.Color.from_rgb(255, 0, 0)

def red_embed(desc=None, title=None): return discord.Embed(title=title, description=desc, color=RED)

# ── JSON helpers ───────────────────────────────────────────────────────────────
def _load(path):
    try: return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    except Exception: return {}

def _save(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

ppl_data    = _load("ppl_data.json")
ltc_data    = _load("ltc_data.json")
vouch_counts= _load("vouch_data.json")

def _load_staff_ids():
    d = _load("ticket_staff.json")
    return set(d.get("ids", []))

def _save_staff_ids():
    _save("ticket_staff.json", {"ids": list(ticket_staff_ids)})

# ── Config ─────────────────────────────────────────────────────────────────────
ticket_config = {k: None for k in (
    "category","log_channel","support_role",
    "role_french","role_english",
    "role_nitro","role_boost","role_decoration","role_exchange","role_other"
)}
vouch_config = {"channel": None, "role": None}
vouch_milestone_roles = {}
open_tickets = {}        # user_id -> channel_id
ping_staff_cooldown = {} # channel_id -> timestamp
ticket_claimers = {}     # channel_id -> member_id
active_giveaways = {}

# ─── NEW: extra staff who can use ticket commands (persistent) ────────────────
ticket_staff_ids = _load_staff_ids()  # loaded from ticket_staff.json

# ── Ticket options ─────────────────────────────────────────────────────────────
TICKET_TYPES = [
    discord.SelectOption(label="Nitro",        emoji="<:Nitro:1480046132707987611>",    value="Nitro"),
    discord.SelectOption(label="Server Boost", emoji="<:Boost:1480046746146050149>",    value="Server Boost"),
    discord.SelectOption(label="Decoration",   emoji="<:Discord:1480047123188944906>",  value="Decoration"),
    discord.SelectOption(label="Exchange",     emoji="<:Exchange:1480047481491427492>", value="Exchange"),
    discord.SelectOption(label="Other",        emoji="<:Other:1480047561615085638>",    value="Other"),
]
PAYMENT_OPTIONS = [
    discord.SelectOption(label="PayPal", emoji="<:PPL:1480046672162852985>", value="PayPal"),
    discord.SelectOption(label="LTC",    emoji="<:LTC:1480634361555452176>", value="LTC"),
]
LANG_OPTIONS = [
    discord.SelectOption(label="Français", emoji="🇫🇷", value="fr"),
    discord.SelectOption(label="English",  emoji="🇬🇧", value="en"),
]
TYPE_ROLE_MAP = {"Nitro":"role_nitro","Server Boost":"role_boost","Decoration":"role_decoration","Exchange":"role_exchange","Other":"role_other"}

MESSAGES = {
    "fr": dict(ticket_title="<:Nitroo:1480046413441273968> Nouveau Ticket",
               ticket_desc="Le support sera avec vous rapidement.\n\nPour fermer ce ticket, appuyez sur le bouton Fermer.",
               ping_staff_tip="🔔 Utilisez **Ping Staff** si aucune réponse après 15 min (cooldown 15 min)",
               close="Fermer", claim="Prendre en charge", unclaim="Rendre",
               transcript="Transcript", ping_staff="Ping Staff", finish="Finish",
               closing="🔒 Fermeture du ticket dans 5 secondes...",
               already_open="❌ Tu as déjà un ticket ouvert →", created="✅ Ticket créé →"),
    "en": dict(ticket_title="<:Nitroo:1480046413441273968> New Ticket",
               ticket_desc="Support will be with you shortly.\n\nTo close this ticket, press the close button below.",
               ping_staff_tip="🔔 Use **Ping Staff** if no response after 15 min (15 min cooldown)",
               close="Close", claim="Claim", unclaim="Unclaim",
               transcript="Transcript", ping_staff="Ping Staff", finish="Finish",
               closing="🔒 Closing ticket in 5 seconds...",
               already_open="❌ You already have an open ticket →", created="✅ Ticket created →"),
}

# ── Vouch logic (shared) ───────────────────────────────────────────────────────
async def _submit_vouch(interaction, staff, rating, service, comment):
    if not 1 <= rating <= 5:
        return await interaction.response.send_message("❌ Rating must be 1-5.", ephemeral=True)
    stars  = "⭐"*rating + "🌑"*(5-rating)
    badges = {1:"😡 Very bad",2:"😕 Bad",3:"😐 Average",4:"😊 Good",5:"🤩 Excellent!"}
    sid = str(staff.id)
    vouch_counts[sid] = vouch_counts.get(sid, 0) + 1
    total = vouch_counts[sid]
    _save("vouch_data.json", vouch_counts)

    embed = discord.Embed(title="📝 New Review — Slayzix Shop", color=RED)
    embed.add_field(name="👤 Customer",   value=interaction.user.mention, inline=True)
    embed.add_field(name="🛠️ Staff",      value=staff.mention,            inline=True)
    embed.add_field(name="📦 Service",    value=f"**{service}**",          inline=True)
    embed.add_field(name="⭐ Rating",     value=f"{stars} `{rating}/5` — {badges[rating]}", inline=False)
    embed.add_field(name="💬 Comment",   value=f"*{comment}*",             inline=False)
    embed.add_field(name="🏆 Vouches",   value=f"`{total}` vouch(s) total",inline=False)
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="Slayzix Shop • Thank you for your review!")
    embed.timestamp = discord.utils.utcnow()

    role_name = f"+{total} vouch"
    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if not role:
        try:
            role = await interaction.guild.create_role(name=role_name, color=RED, reason="Vouch auto-role")
            admins = [r for r in interaction.guild.roles if r.permissions.administrator and r != interaction.guild.default_role]
            if admins:
                await role.edit(position=max(1, min(admins, key=lambda r: r.position).position - 1))
        except discord.Forbidden: role = None
    if total > 1:
        old = discord.utils.get(interaction.guild.roles, name=f"+{total-1} vouch")
        if old and old in staff.roles:
            try: await staff.remove_roles(old)
            except discord.Forbidden: pass
    if role and role not in staff.roles:
        try: await staff.add_roles(role)
        except discord.Forbidden: pass
    if vouch_config["role"]:
        br = interaction.guild.get_role(vouch_config["role"])
        if br and br not in interaction.user.roles:
            try: await interaction.user.add_roles(br)
            except discord.Forbidden: pass
    if vouch_config["channel"]:
        ch = interaction.guild.get_channel(vouch_config["channel"])
        if ch: await ch.send(embed=embed)
    return embed

class VouchModal(discord.ui.Modal, title="⭐ Leave a Review"):
    rating_input  = discord.ui.TextInput(label="Rating (1 to 5)",    placeholder="5", max_length=1)
    service_input = discord.ui.TextInput(label="Service purchased",   placeholder="e.g. Nitro Basic", max_length=100)
    comment_input = discord.ui.TextInput(label="Comment",             placeholder="Fast, legit…", style=discord.TextStyle.long, max_length=500)

    def __init__(self, claimer): super().__init__(); self.claimer = claimer

    async def on_submit(self, interaction):
        try: rating = int(self.rating_input.value.strip())
        except ValueError: return await interaction.response.send_message("❌ Rating must be a number.", ephemeral=True)
        if not self.claimer:
            return await interaction.response.send_message("❌ No staff found. Ask staff to click **Claim** first.", ephemeral=True)
        await _submit_vouch(interaction, self.claimer, rating, self.service_input.value.strip(), self.comment_input.value.strip())
        await interaction.response.send_message("✅ Review submitted! Thank you 🙏", ephemeral=True)

# ── Ticket channel creation ────────────────────────────────────────────────────
async def create_ticket_channel(interaction, ticket_type, payment, lang):
    guild, user, m = interaction.guild, interaction.user, MESSAGES[lang]
    if user.id in open_tickets:
        ex = guild.get_channel(open_tickets[user.id])
        if ex: return await interaction.followup.send(f"{m['already_open']} {ex.mention}", ephemeral=True)

    cat = guild.get_channel(ticket_config["category"]) if ticket_config["category"] else None
    if not cat: cat = discord.utils.get(guild.categories, name="TICKETS") or await guild.create_category("TICKETS")

    ow = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
    }
    if ticket_config["support_role"]:
        sr = guild.get_role(ticket_config["support_role"])
        if sr: ow[sr] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    # NEW: give access to extra ticket staff
    for sid in ticket_staff_ids:
        member = guild.get_member(sid)
        if member: ow[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    channel = await guild.create_text_channel(
        name=f"{ticket_type.lower().replace(' ','-')}-{user.name}", overwrites=ow, category=cat)
    open_tickets[user.id] = channel.id

    mentions = user.mention
    for key in ("support_role", f"role_{'french' if lang=='fr' else 'english'}", TYPE_ROLE_MAP.get(ticket_type,"")):
        if key and ticket_config.get(key): mentions += f" <@&{ticket_config[key]}>"

    embed = discord.Embed(title=m["ticket_title"], description=m["ticket_desc"], color=RED)
    embed.add_field(name="<:Nitroo:1480046413441273968> Type", value=ticket_type, inline=True)
    embed.add_field(name="<:Paiement:1480046846658351276> Payment", value=payment, inline=True)
    embed.add_field(name="🌍 Language", value="🇫🇷 Français" if lang=="fr" else "🇬🇧 English", inline=True)
    embed.set_footer(text=m["ping_staff_tip"]); embed.timestamp = discord.utils.utcnow()

    await channel.send(content=mentions, embed=embed,
                       view=TicketActionsView(lang, ticket_type),
                       allowed_mentions=discord.AllowedMentions(users=True, roles=True))

    # NEW: log to setlogs channel
    if ticket_config["log_channel"]:
        lc = guild.get_channel(ticket_config["log_channel"])
        if lc:
            le = discord.Embed(title="📋 Ticket ouvert", color=RED,
                               description=f"**User:** {user.mention}\n**Type:** {ticket_type}\n**Payment:** {payment}\n**Lang:** {lang}\n**Channel:** {channel.mention}")
            le.timestamp = discord.utils.utcnow(); await lc.send(embed=le)

    await interaction.followup.send(f"{m['created']} {channel.mention}", ephemeral=True)

# ── Ticket Views ───────────────────────────────────────────────────────────────
class TicketActionsView(discord.ui.View):
    def __init__(self, lang, ticket_type):
        super().__init__(timeout=None)
        self.lang, self.ticket_type = lang, ticket_type
        m = MESSAGES[lang]
        btns = [
            ("ticket_close",      m["close"],      "<:Other:1480047561615085638>",      0, self.close_cb),
            ("ticket_claim",      m["claim"],      "<:Boost:1480046746146050149>",      0, self.claim_cb),
            ("ticket_unclaim",    m["unclaim"],    "<:Exchange:1480047481491427492>",   0, self.unclaim_cb),
            ("ticket_transcript", m["transcript"], "<:Transcript:1480047021707759727>", 0, self.transcript_cb),
            ("ticket_finish",     m["finish"],     "<:oui:1480176155989508348>",         1, self.finish_cb),
            ("ticket_ping",       m["ping_staff"], "<:Discord:1480047123188944906>",    1, self.ping_cb),
        ]
        for cid, label, emoji, row, cb in btns:
            b = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary,
                                  custom_id=cid, emoji=emoji, row=row)
            b.callback = cb; self.add_item(b)

    async def close_cb(self, interaction):
        await interaction.response.send_message(MESSAGES[self.lang]["closing"])
        if ticket_config["log_channel"]:
            lc = interaction.guild.get_channel(ticket_config["log_channel"])
            if lc:
                e = red_embed(f"**Salon:** {interaction.channel.name}\n**Par:** {interaction.user.mention}", "📋 Ticket fermé")
                e.timestamp = discord.utils.utcnow(); await lc.send(embed=e)
        open_tickets.pop(next((u for u,c in open_tickets.items() if c==interaction.channel.id), None), None)
        await asyncio.sleep(5); await interaction.channel.delete()

    async def claim_cb(self, interaction):
        ticket_claimers[interaction.channel.id] = interaction.user.id
        txt = f"✅ Ticket pris en charge par {interaction.user.mention}" if self.lang=="fr" else f"✅ Ticket claimed by {interaction.user.mention}"
        await interaction.response.send_message(embed=red_embed(txt))

    async def unclaim_cb(self, interaction):
        ticket_claimers.pop(interaction.channel.id, None)
        txt = f"🔄 Ticket rendu par {interaction.user.mention}" if self.lang=="fr" else f"🔄 Ticket unclaimed by {interaction.user.mention}"
        await interaction.response.send_message(embed=red_embed(txt))

    async def transcript_cb(self, interaction):
        await interaction.response.defer(ephemeral=True)
        msgs = [f"[{m.created_at.strftime('%d/%m/%Y %H:%M')}] {m.author.name}: {m.content}"
                async for m in interaction.channel.history(limit=200, oldest_first=True) if not m.author.bot]
        if not msgs:
            return await interaction.followup.send("Aucun message." if self.lang=="fr" else "No messages.", ephemeral=True)
        import io
        await interaction.followup.send(
            "📄 Transcript généré !" if self.lang=="fr" else "📄 Transcript generated!",
            file=discord.File(io.BytesIO("\n".join(msgs).encode()), filename=f"transcript-{interaction.channel.name}.txt"),
            ephemeral=True)

    async def finish_cb(self, interaction):
        claimer_id = ticket_claimers.get(interaction.channel.id)
        claimer = interaction.guild.get_member(claimer_id) if claimer_id else None
        if not claimer:
            return await interaction.response.send_message("❌ No staff has claimed this ticket yet!", ephemeral=True)
        await interaction.response.send_modal(VouchModal(claimer))

    async def ping_cb(self, interaction):
        now = datetime.utcnow().timestamp()
        last = ping_staff_cooldown.get(interaction.channel.id, 0)
        if now - last < 900:
            rem = int(900 - (now - last))
            msg = f"⏳ Cooldown ! **{rem//60}m {rem%60}s**" if self.lang=="fr" else f"⏳ Cooldown! **{rem//60}m {rem%60}s**"
            return await interaction.response.send_message(msg, ephemeral=True)
        ping_staff_cooldown[interaction.channel.id] = now
        mentions = []
        if ticket_config["support_role"]:
            r = interaction.guild.get_role(ticket_config["support_role"])
            if r: mentions.append(r.mention)
        tr = TYPE_ROLE_MAP.get(self.ticket_type)
        if tr and ticket_config.get(tr):
            r2 = interaction.guild.get_role(ticket_config[tr])
            if r2 and r2.mention not in mentions: mentions.append(r2.mention)
        if mentions:
            suffix = "Un client attend !" if self.lang=="fr" else "A customer needs help!"
            await interaction.channel.send(" ".join(mentions)+" — "+suffix,
                                           allowed_mentions=discord.AllowedMentions(roles=True))
        await interaction.response.send_message("✅ Staff pingé !" if self.lang=="fr" else "✅ Staff pinged!", ephemeral=True)


class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Select a category...", options=TICKET_TYPES, custom_id="ticket_type_select")
    async def callback(self, interaction):
        if interaction.user.id in open_tickets:
            ex = interaction.guild.get_channel(open_tickets[interaction.user.id])
            if ex: return await interaction.response.send_message(f"❌ You already have an open ticket → {ex.mention}", ephemeral=True)
        e = discord.Embed(title="<:Paiement:1480046846658351276> Payment Method",
                          description="Select your payment method:", color=RED)
        e.set_footer(text="Your ticket will be created after selection")
        await interaction.response.send_message(embed=e, view=PaymentView(self.values[0], interaction.user.id), ephemeral=True)

class PaymentSelect(discord.ui.Select):
    def __init__(self, ticket_type, user_id):
        super().__init__(placeholder="Select your payment method...", options=PAYMENT_OPTIONS, custom_id="payment_select")
        self.ticket_type, self.user_id = ticket_type, user_id
    async def callback(self, interaction):
        e = discord.Embed(title="🌍 Language / Langue",
                          description="Please select your language.\nVeuillez sélectionner votre langue.", color=RED)
        await interaction.response.edit_message(embed=e, view=LangView(self.ticket_type, self.values[0], self.user_id))

class LangSelect(discord.ui.Select):
    def __init__(self, ticket_type, payment, user_id):
        super().__init__(placeholder="🌍 Select language...", options=LANG_OPTIONS, custom_id="lang_select")
        self.ticket_type, self.payment, self.user_id = ticket_type, payment, user_id
    async def callback(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await create_ticket_channel(interaction, self.ticket_type, self.payment, self.values[0])

class PaymentView(discord.ui.View):
    def __init__(self, tt, uid): super().__init__(timeout=120); self.add_item(PaymentSelect(tt, uid))
class LangView(discord.ui.View):
    def __init__(self, tt, pay, uid): super().__init__(timeout=120); self.add_item(LangSelect(tt, pay, uid))
class TicketPanelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(TicketTypeSelect())

# ── Setup ──────────────────────────────────────────────────────────────────────
class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        cat = discord.ui.ChannelSelect(placeholder="📁 Catégorie tickets", channel_types=[discord.ChannelType.category])
        log = discord.ui.ChannelSelect(placeholder="📋 Salon des logs", channel_types=[discord.ChannelType.text], row=1)
        rol = discord.ui.RoleSelect(placeholder="👮 Rôle support", row=2)
        async def cat_cb(i): ticket_config["category"]=i.data["values"][0]; await i.response.send_message(f"✅ Catégorie OK", ephemeral=True)
        async def log_cb(i): ticket_config["log_channel"]=int(i.data["values"][0]); await i.response.send_message(f"✅ Log OK", ephemeral=True)
        async def rol_cb(i): ticket_config["support_role"]=int(i.data["values"][0]); await i.response.send_message(f"✅ Rôle OK", ephemeral=True)
        cat.callback, log.callback, rol.callback = cat_cb, log_cb, rol_cb
        self.add_item(cat); self.add_item(log); self.add_item(rol)

    @discord.ui.button(label="📨 Envoyer le panel ici", style=discord.ButtonStyle.success, row=3)
    async def send_panel(self, interaction, button):
        e = discord.Embed(title="<:Nitroo:1480046413441273968> Support Ticket System",
                          description="Select a category below to create a support ticket.\n\nOur team will assist you as soon as possible.", color=RED)
        e.set_image(url=BANNER_URL); e.set_footer(text="Please provide detailed information in your ticket")
        await interaction.channel.send(embed=e, view=TicketPanelView())
        await interaction.response.send_message("✅ Panel envoyé !", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.message.delete()
    e = discord.Embed(title="⚙️ Configuration Ticket System",
                      description="**1️⃣** Catégorie **2️⃣** Logs **3️⃣** Rôle\nPuis **📨 Envoyer le panel**", color=RED)
    await ctx.send(embed=e, view=SetupView())

# ── Role commands (factory) ────────────────────────────────────────────────────
def make_role_cmd(name, key, label):
    @bot.command(name=name)
    @commands.has_permissions(administrator=True)
    async def _cmd(ctx, role: discord.Role):
        ticket_config[key] = role.id; await ctx.message.delete()
        await ctx.send(embed=red_embed(f"**{label}** → {role.mention}", "✅ Rôle configuré"), delete_after=8)
    _cmd.__name__ = name; return _cmd

for _n,_k,_l in [("setfrench","role_french","🇫🇷 Français"),("setenglish","role_english","🇬🇧 English"),
                  ("setnitro","role_nitro","Nitro"),("setboost","role_boost","Server Boost"),
                  ("setdeco","role_decoration","Decoration"),("setexchange","role_exchange","Exchange"),
                  ("setother","role_other","Other")]:
    make_role_cmd(_n,_k,_l)

# ── PPL / LTC generic helpers ──────────────────────────────────────────────────
def _make_crypto_cmds(name, file, data_dict, save_fn, fields_fn, modal_cls, emoji):
    @bot.command(name=f"{name}save")
    async def _save_cmd(ctx):
        await ctx.message.delete()
        class _View(discord.ui.View):
            def __init__(self): super().__init__(timeout=60)
            @discord.ui.button(label=f"Sauvegarder mon {name.upper()}", style=discord.ButtonStyle.secondary, emoji=emoji)
            async def _btn(self, interaction, button):
                if interaction.user.id != ctx.author.id: return await interaction.response.send_message("❌ Pas pour toi.", ephemeral=True)
                await interaction.response.send_modal(modal_cls())
        e = discord.Embed(title=f"{emoji} Sauvegarde {name.upper()}",
                          description=f"Clique pour enregistrer.\n📌 Affiché avec `*{name}`\n🔒 Seul toi peut modifier.", color=RED)
        e.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=e, view=_View())

    @bot.command(name=f"{name}delete")
    async def _del_cmd(ctx):
        uid = str(ctx.author.id); await ctx.message.delete()
        if uid not in data_dict: return await ctx.send(embed=red_embed(f"❌ Aucun {name.upper()} à supprimer."), delete_after=8)
        del data_dict[uid]; save_fn(data_dict)
        await ctx.send(embed=red_embed(f"Ton adresse {name.upper()} a été supprimée.", f"🗑️ {name.upper()} supprimé"), delete_after=8)

# ── PPL ────────────────────────────────────────────────────────────────────────
class PPLSaveModal(discord.ui.Modal, title="💳 Sauvegarder mon PPL PayPal"):
    email = discord.ui.TextInput(label="Email PayPal",       placeholder="exemple@email.com", max_length=100)
    nom   = discord.ui.TextInput(label="Nom du compte",      placeholder="Jean Dupont",       max_length=100)
    note  = discord.ui.TextInput(label="Note (optionnel)",   required=False, max_length=300, style=discord.TextStyle.long)
    async def on_submit(self, interaction):
        uid = str(interaction.user.id)
        ppl_data[uid] = {"email":self.email.value.strip(),"nom":self.nom.value.strip(),
                         "note":self.note.value.strip(),"updated_at":datetime.utcnow().strftime("%d/%m/%Y %H:%M")}
        _save("ppl_data.json", ppl_data)
        await interaction.response.send_message(embed=red_embed("Ton PayPal a été enregistré. Utilise `*ppl`.", "✅ PPL sauvegardé !"), ephemeral=True)

@bot.command(name="pplsave")
async def pplsave(ctx):
    await ctx.message.delete()
    class _View(discord.ui.View):
        def __init__(self): super().__init__(timeout=60)
        @discord.ui.button(label="Sauvegarder mon PayPal", style=discord.ButtonStyle.success, emoji="<:PPL:1480046672162852985>")
        async def _btn(self, interaction, button):
            if interaction.user.id != ctx.author.id: return await interaction.response.send_message("❌ Pas pour toi.", ephemeral=True)
            await interaction.response.send_modal(PPLSaveModal())
    e = discord.Embed(title="💳 Sauvegarde PPL PayPal",
                      description="Clique pour enregistrer ton adresse PayPal.\n📌 `*ppl` l'affichera.\n🔒 Seul toi peut modifier.", color=RED)
    e.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=e, view=_View())

@bot.command(name="ppl")
async def ppl(ctx):
    uid = str(ctx.author.id); await ctx.message.delete()
    if uid not in ppl_data or not ppl_data[uid].get("email"):
        return await ctx.send(embed=red_embed(f"{ctx.author.mention} utilise `*pplsave` pour enregistrer.", "❌ Aucun PPL"), delete_after=10)
    d = ppl_data[uid]; email = d["email"]
    class _View(discord.ui.View):
        def __init__(self): super().__init__(timeout=None)
        @discord.ui.button(label="Copier le PayPal", style=discord.ButtonStyle.secondary, emoji="<:PPL:1480046672162852985>")
        async def _btn(self, interaction, button):
            await interaction.response.send_message(f"📋 **PayPal de {ctx.author.display_name}:**\n```{email}```", ephemeral=True)
    e = discord.Embed(title="<:PPL:1480046672162852985> Informations PayPal", color=RED)
    e.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    e.add_field(name="📧 Email PayPal",   value=f"```{email}```", inline=False)
    e.add_field(name="👤 Nom du compte",  value=f"```{d['nom']}```", inline=True)
    e.add_field(name="🕐 Mis à jour",     value=f"`{d.get('updated_at','?')}`", inline=True)
    if d.get("note"): e.add_field(name="📝 Note", value=d["note"], inline=False)
    e.set_thumbnail(url="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_111x69.jpg")
    e.timestamp = discord.utils.utcnow(); await ctx.send(embed=e, view=_View())

@bot.command(name="ppldelete")
async def ppldelete(ctx):
    uid = str(ctx.author.id); await ctx.message.delete()
    if uid not in ppl_data: return await ctx.send(embed=red_embed("❌ Aucun PPL à supprimer."), delete_after=8)
    del ppl_data[uid]; _save("ppl_data.json", ppl_data)
    await ctx.send(embed=red_embed("Ton adresse PayPal a été supprimée.", "🗑️ PPL supprimé"), delete_after=8)

# ── LTC ────────────────────────────────────────────────────────────────────────
class LTCSaveModal(discord.ui.Modal, title="🪙 Sauvegarder mon adresse LTC"):
    address = discord.ui.TextInput(label="Adresse LTC", placeholder="LxxxxxxxxxX", max_length=100)
    note    = discord.ui.TextInput(label="Note (optionnel)", required=False, max_length=300, style=discord.TextStyle.long)
    async def on_submit(self, interaction):
        uid = str(interaction.user.id)
        ltc_data[uid] = {"address":self.address.value.strip(),"note":self.note.value.strip(),
                         "updated_at":datetime.utcnow().strftime("%d/%m/%Y %H:%M")}
        _save("ltc_data.json", ltc_data)
        await interaction.response.send_message(embed=red_embed("Ton LTC a été enregistré. Utilise `*ltc`.", "✅ LTC sauvegardé !"), ephemeral=True)

@bot.command(name="ltcsave")
async def ltcsave(ctx):
    await ctx.message.delete()
    class _View(discord.ui.View):
        def __init__(self): super().__init__(timeout=60)
        @discord.ui.button(label="Sauvegarder mon LTC", style=discord.ButtonStyle.secondary, emoji="<:LTC:1480634361555452176>")
        async def _btn(self, interaction, button):
            if interaction.user.id != ctx.author.id: return await interaction.response.send_message("❌ Pas pour toi.", ephemeral=True)
            await interaction.response.send_modal(LTCSaveModal())
    e = discord.Embed(title="<:LTC:1480634361555452176> Sauvegarde LTC",
                      description="Clique pour enregistrer ton adresse LTC.\n📌 `*ltc` l'affichera.\n🔒 Seul toi peut modifier.", color=RED)
    e.set_thumbnail(url=ctx.author.display_avatar.url); await ctx.send(embed=e, view=_View())

@bot.command(name="ltc")
async def ltc_cmd(ctx):
    uid = str(ctx.author.id); await ctx.message.delete()
    if uid not in ltc_data or not ltc_data[uid].get("address"):
        return await ctx.send(embed=red_embed(f"{ctx.author.mention} utilise `*ltcsave`.", "❌ Aucun LTC"), delete_after=10)
    d = ltc_data[uid]; addr = d["address"]
    class _View(discord.ui.View):
        def __init__(self): super().__init__(timeout=None)
        @discord.ui.button(label="Copier l'adresse LTC", style=discord.ButtonStyle.secondary, emoji="<:LTC:1480634361555452176>")
        async def _btn(self, interaction, button):
            await interaction.response.send_message(f"📋 **LTC de {ctx.author.display_name}:**\n```{addr}```", ephemeral=True)
    e = discord.Embed(title="<:LTC:1480634361555452176> Adresse LTC", color=RED)
    e.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    e.add_field(name="🪙 Adresse", value=f"```{addr}```", inline=False)
    e.add_field(name="🕐 Mis à jour", value=f"`{d.get('updated_at','?')}`", inline=True)
    if d.get("note"): e.add_field(name="📝 Note", value=d["note"], inline=False)
    e.timestamp = discord.utils.utcnow(); await ctx.send(embed=e, view=_View())

@bot.command(name="ltcdelete")
async def ltcdelete(ctx):
    uid = str(ctx.author.id); await ctx.message.delete()
    if uid not in ltc_data: return await ctx.send(embed=red_embed("❌ Aucun LTC à supprimer."), delete_after=8)
    del ltc_data[uid]; _save("ltc_data.json", ltc_data)
    await ctx.send(embed=red_embed("Ton adresse LTC a été supprimée.", "🗑️ LTC supprimé"), delete_after=8)

# ── Vouch commands ─────────────────────────────────────────────────────────────
class VouchSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        ch = discord.ui.ChannelSelect(placeholder="Select vouch channel", channel_types=[discord.ChannelType.text])
        rl = discord.ui.RoleSelect(placeholder="Select vouch role", row=1)
        async def ch_cb(i): vouch_config["channel"]=int(i.data["values"][0]); await i.response.send_message("✅ Channel OK", ephemeral=True)
        async def rl_cb(i): vouch_config["role"]=int(i.data["values"][0]); await i.response.send_message("✅ Role OK", ephemeral=True)
        ch.callback, rl.callback = ch_cb, rl_cb; self.add_item(ch); self.add_item(rl)

@bot.command(name="vouchsetup")
@commands.has_permissions(administrator=True)
async def vouchsetup(ctx):
    await ctx.message.delete()
    await ctx.send(embed=discord.Embed(title="⚙️ Vouch Setup", description="Select vouch channel and role.", color=RED), view=VouchSetupView())

@bot.command(name="vouch")
async def vouch(ctx, staff: discord.Member, rating: int, service: str, *, comment: str):
    await ctx.message.delete()
    if not 1 <= rating <= 5: return await ctx.send("❌ Rating 1-5.", delete_after=8)
    stars="⭐"*rating+"🌑"*(5-rating); badges={1:"😡 Very bad",2:"😕 Bad",3:"😐 Average",4:"😊 Good",5:"🤩 Excellent!"}
    sid=str(staff.id); vouch_counts[sid]=vouch_counts.get(sid,0)+1; total=vouch_counts[sid]; _save("vouch_data.json",vouch_counts)
    e=discord.Embed(title="📝 New Review — Slayzix Shop",color=RED)
    e.add_field(name="👤 Customer",value=ctx.author.mention,inline=True)
    e.add_field(name="🛠️ Staff",value=staff.mention,inline=True)
    e.add_field(name="📦 Service",value=f"**{service}**",inline=True)
    e.add_field(name="⭐ Rating",value=f"{stars} `{rating}/5` — {badges[rating]}",inline=False)
    e.add_field(name="💬 Comment",value=f"*{comment}*",inline=False)
    e.add_field(name="🏆 Vouches",value=f"`{total}` vouch(s) total",inline=False)
    e.set_thumbnail(url=ctx.author.display_avatar.url); e.timestamp=discord.utils.utcnow()
    rn=f"+{total} vouch"; role=discord.utils.get(ctx.guild.roles,name=rn)
    if not role:
        try:
            role=await ctx.guild.create_role(name=rn,color=RED)
            admins=[r for r in ctx.guild.roles if r.permissions.administrator and r!=ctx.guild.default_role]
            if admins: await role.edit(position=max(1,min(admins,key=lambda r:r.position).position-1))
        except discord.Forbidden: role=None
    if total>1:
        old=discord.utils.get(ctx.guild.roles,name=f"+{total-1} vouch")
        if old and old in staff.roles:
            try: await staff.remove_roles(old)
            except discord.Forbidden: pass
    if role and role not in staff.roles:
        try: await staff.add_roles(role)
        except discord.Forbidden: pass
    if vouch_config["role"]:
        br=ctx.guild.get_role(vouch_config["role"])
        if br and br not in ctx.author.roles:
            try: await ctx.author.add_roles(br)
            except discord.Forbidden: pass
    if vouch_config["channel"]:
        ch=ctx.guild.get_channel(vouch_config["channel"])
        if ch: await ch.send(embed=e); return await ctx.send(f"✅ Review posted in {ch.mention}! {staff.display_name} has **{total}** vouch(s)!", delete_after=8)
    await ctx.send(embed=e)

@bot.command(name="setvouchrole")
@commands.has_permissions(administrator=True)
async def setvouchrole(ctx, milestone:int, role:discord.Role):
    vouch_milestone_roles[milestone]=role.id; await ctx.message.delete()
    await ctx.send(embed=red_embed(f"À **{milestone}** vouch(s) → {role.mention}","✅ Milestone configuré"), delete_after=8)

@bot.command(name="vouchcount")
async def vouchcount(ctx, member: discord.Member=None):
    target=member or ctx.author; await ctx.message.delete()
    e=red_embed(f"{target.mention} has **{vouch_counts.get(str(target.id),0)}** vouch(s).","🏆 Vouch Count")
    e.set_thumbnail(url=target.display_avatar.url); await ctx.send(embed=e)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ── NEW: *analyse — Classement des vouchs (lit vouch_data.json au démarrage) ──
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.command(name="analyse")
@commands.has_permissions(manage_guild=True)
async def analyse_cmd(ctx):
    """Classement complet des vouchs de tous les staff (données chargées au démarrage)."""
    await ctx.message.delete()

    if not vouch_counts:
        return await ctx.send(embed=red_embed("Aucun vouch enregistré pour le moment.", "📊 Analyse Vouchs"), delete_after=10)

    sorted_vouches = sorted(vouch_counts.items(), key=lambda x: x[1], reverse=True)
    total_vouches  = sum(v for _, v in sorted_vouches)
    medals = ["🥇", "🥈", "🥉"]

    lines = []
    for i, (uid, count) in enumerate(sorted_vouches[:15]):
        member = ctx.guild.get_member(int(uid))
        name   = member.display_name if member else f"Inconnu (`{uid}`)"
        medal  = medals[i] if i < 3 else f"`#{i+1}`"
        filled = min(count, 20)
        bar    = "█" * filled + "░" * (20 - filled)
        lines.append(f"{medal} **{name}** — `{count}` vouch(s)\n`{bar}`")

    e = discord.Embed(
        title="📊 Analyse — Classement des Vouchs",
        description="\n\n".join(lines),
        color=RED
    )
    e.add_field(name="📦 Total vouchs",  value=f"`{total_vouches}`",       inline=True)
    e.add_field(name="👥 Staff actifs",  value=f"`{len(sorted_vouches)}`", inline=True)

    top_uid, top_count = sorted_vouches[0]
    top_member = ctx.guild.get_member(int(top_uid))
    top_name   = top_member.display_name if top_member else f"`{top_uid}`"
    e.add_field(name="🏆 Meilleur staff", value=f"**{top_name}** avec `{top_count}` vouch(s)", inline=False)

    if ctx.guild.icon: e.set_thumbnail(url=ctx.guild.icon.url)
    e.set_footer(text="Slayzix Shop • Données chargées depuis vouch_data.json")
    e.timestamp = discord.utils.utcnow()
    await ctx.send(embed=e)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ── NEW: *setlogs — Définir le salon de logs des tickets ─────────────────────
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.command(name="setlogs")
@commands.has_permissions(administrator=True)
async def setlogs_cmd(ctx, channel: discord.TextChannel):
    """Définit le salon de logs des tickets. Usage: *setlogs #salon"""
    await ctx.message.delete()
    ticket_config["log_channel"] = channel.id
    await ctx.send(embed=red_embed(
        f"✅ Les logs des tickets seront envoyés dans {channel.mention}",
        "📋 Logs configurés"
    ), delete_after=8)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ── NEW: *addaccessticket / *removeaccessticket / *listaccessticket ───────────
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.command(name="addaccessticket")
@commands.has_permissions(administrator=True)
async def addaccessticket_cmd(ctx, member: discord.Member):
    """Donne accès aux commandes ticket à un membre. Usage: *addaccessticket @membre"""
    await ctx.message.delete()
    ticket_staff_ids.add(member.id)
    _save_staff_ids()
    await ctx.send(embed=red_embed(
        f"✅ {member.mention} peut maintenant utiliser `*claim`, `*unclaim`, `*close`, `*finish`, `*add`, `*remove`, `*rename`, `*slowmode`.",
        "🎫 Accès ticket accordé"
    ), delete_after=10)

@bot.command(name="removeaccessticket")
@commands.has_permissions(administrator=True)
async def removeaccessticket_cmd(ctx, member: discord.Member):
    """Retire l'accès ticket d'un membre. Usage: *removeaccessticket @membre"""
    await ctx.message.delete()
    ticket_staff_ids.discard(member.id)
    _save_staff_ids()
    await ctx.send(embed=red_embed(
        f"❌ Accès ticket retiré à {member.mention}.",
        "🎫 Accès retiré"
    ), delete_after=8)

@bot.command(name="listaccessticket")
@commands.has_permissions(administrator=True)
async def listaccessticket_cmd(ctx):
    """Liste tous les membres avec accès ticket. Usage: *listaccessticket"""
    await ctx.message.delete()
    if not ticket_staff_ids:
        return await ctx.send(embed=red_embed("Aucun membre ajouté via `*addaccessticket`.", "🎫 Accès ticket"), delete_after=10)
    members_list = []
    for sid in ticket_staff_ids:
        m = ctx.guild.get_member(sid)
        members_list.append(m.mention if m else f"`{sid}`")
    await ctx.send(embed=red_embed(
        "\n".join(members_list),
        f"🎫 Staff ticket ({len(members_list)})"
    ), delete_after=15)

# ── Ticket utility commands ────────────────────────────────────────────────────
# Permission check helper: admin OR addaccessticket
def _has_ticket_access(ctx):
    return (ctx.author.guild_permissions.administrator
            or ctx.author.guild_permissions.manage_messages
            or ctx.author.id in ticket_staff_ids)

@bot.command(name="finish")
async def finish_cmd(ctx, staff: discord.Member=None):
    if not _has_ticket_access(ctx): return await ctx.send(embed=red_embed("❌ Permission refusée."), delete_after=5)
    await ctx.message.delete()
    if not staff:
        cid=ticket_claimers.get(ctx.channel.id)
        staff=ctx.guild.get_member(cid) if cid else None
    if not staff: return await ctx.send(embed=red_embed("❌ Mentionne un staff : `*finish @staff`"), delete_after=8)
    class _View(discord.ui.View):
        def __init__(self): super().__init__(timeout=None)
        @discord.ui.button(label="Finish",style=discord.ButtonStyle.secondary,emoji="<:oui:1480176155989508348>")
        async def _btn(self,interaction,button): await interaction.response.send_modal(VouchModal(staff))
    e=discord.Embed(title="✅ Transaction terminée !",
                    description=f"Merci d'avoir choisi **Slayzix Shop** !\n\n🛠️ Staff : {staff.mention}\n\nLaisse ton avis ⭐",color=RED)
    e.set_footer(text="Slayzix Shop"); e.timestamp=discord.utils.utcnow()
    await ctx.send(embed=e, view=_View())

@bot.command(name="claim")
async def claim_cmd(ctx):
    if not _has_ticket_access(ctx): return await ctx.send(embed=red_embed("❌ Permission refusée."), delete_after=5)
    await ctx.message.delete(); ticket_claimers[ctx.channel.id]=ctx.author.id
    await ctx.send(embed=red_embed(f"✅ Ticket pris en charge par {ctx.author.mention}"))

@bot.command(name="unclaim")
async def unclaim_cmd(ctx):
    if not _has_ticket_access(ctx): return await ctx.send(embed=red_embed("❌ Permission refusée."), delete_after=5)
    await ctx.message.delete(); ticket_claimers.pop(ctx.channel.id,None)
    await ctx.send(embed=red_embed(f"🔄 Ticket rendu par {ctx.author.mention}"))

@bot.command(name="close")
async def close_cmd(ctx):
    if not _has_ticket_access(ctx): return await ctx.send(embed=red_embed("❌ Permission refusée."), delete_after=5)
    await ctx.message.delete(); await ctx.send(embed=red_embed("🔒 Fermeture dans 5s..."))
    if ticket_config["log_channel"]:
        lc=ctx.guild.get_channel(ticket_config["log_channel"])
        if lc:
            e=red_embed(f"**Salon:** {ctx.channel.name}\n**Par:** {ctx.author.mention}","📋 Ticket fermé")
            e.timestamp=discord.utils.utcnow(); await lc.send(embed=e)
    open_tickets.pop(next((u for u,c in open_tickets.items() if c==ctx.channel.id),None),None)
    await asyncio.sleep(5); await ctx.channel.delete()

@bot.command(name="add")
async def add_cmd(ctx, member:discord.Member):
    if not _has_ticket_access(ctx): return await ctx.send(embed=red_embed("❌ Permission refusée."), delete_after=5)
    await ctx.message.delete(); await ctx.channel.set_permissions(member,read_messages=True,send_messages=True)
    await ctx.send(embed=red_embed(f"✅ {member.mention} ajouté."),delete_after=8)

@bot.command(name="remove")
async def remove_cmd(ctx, member:discord.Member):
    if not _has_ticket_access(ctx): return await ctx.send(embed=red_embed("❌ Permission refusée."), delete_after=5)
    await ctx.message.delete(); await ctx.channel.set_permissions(member,overwrite=None)
    await ctx.send(embed=red_embed(f"❌ {member.mention} retiré."),delete_after=8)

@bot.command(name="rename")
async def rename_cmd(ctx, *, name:str):
    if not _has_ticket_access(ctx): return await ctx.send(embed=red_embed("❌ Permission refusée."), delete_after=5)
    old=ctx.channel.name; await ctx.message.delete(); await ctx.channel.edit(name=name)
    await ctx.send(embed=red_embed(f"✏️ `{old}` → `{name}`"),delete_after=8)

@bot.command(name="slowmode")
async def slowmode_cmd(ctx, seconds:int=0):
    if not _has_ticket_access(ctx): return await ctx.send(embed=red_embed("❌ Permission refusée."), delete_after=5)
    await ctx.message.delete(); await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(embed=red_embed(f"⏱️ Slowmode {'désactivé' if seconds==0 else f'**{seconds}s**'}."),delete_after=8)

# ── Giveaway ───────────────────────────────────────────────────────────────────
class GiveawayView(discord.ui.View):
    def __init__(self, gid): super().__init__(timeout=None); self.gid=gid
    @discord.ui.button(label="🎉 Participate", style=discord.ButtonStyle.success, custom_id="giveaway_join")
    async def join(self, interaction, button):
        if self.gid not in active_giveaways: return await interaction.response.send_message("❌ Giveaway ended.", ephemeral=True)
        g=active_giveaways[self.gid]
        if interaction.user.id in g["participants"]:
            g["participants"].discard(interaction.user.id); msg="❌ You withdrew."
        else:
            g["participants"].add(interaction.user.id); msg="✅ You joined! 🍀"
        button.label=f"🎉 Participate — {len(g['participants'])}"; await interaction.message.edit(view=self)
        await interaction.response.send_message(msg, ephemeral=True)

async def end_giveaway(channel_id, message_id, guild):
    import random
    if message_id not in active_giveaways: return
    g=active_giveaways[message_id]; channel=guild.get_channel(channel_id)
    if not channel: return
    try: message=await channel.fetch_message(message_id)
    except Exception: return
    participants=list(g["participants"]); prize=g["prize"]; host=g["host"]
    if not participants:
        e=discord.Embed(title="🎉 GIVEAWAY ENDED",description=f"**Prize:** {prize}\n**Host:** <@{host}>\n\n😔 No participants!",color=RED)
        await message.edit(embed=e,view=None); await channel.send("😔 No participants, no winner!")
    else:
        winners=random.sample(participants,min(g["winners"],len(participants)))
        wm=" ".join(f"<@{w}>" for w in winners)
        e=discord.Embed(title="🎉 GIVEAWAY ENDED",
                        description=f"**Prize:** {prize}\n**Winner(s):** {wm}\n**Host:** <@{host}>\n**Participants:** {len(participants)}",color=RED)
        await message.edit(embed=e,view=None)
        await channel.send(f"🎊 Congrats {wm}! You won **{prize}**! Contact <@{host}> to claim.")
    del active_giveaways[message_id]

@bot.tree.command(name="giveaway",description="🎉 Start a giveaway!")
@discord.app_commands.describe(duration="e.g. 10s 5m 1h 2d",winners="Number of winners",prize="Prize")
@discord.app_commands.checks.has_permissions(manage_guild=True)
async def giveaway_cmd(interaction, duration:str, winners:int, prize:str):
    try:
        unit=duration[-1].lower(); val=int(duration[:-1])
        secs=val*{"s":1,"m":60,"h":3600,"d":86400}[unit]
    except Exception: return await interaction.response.send_message("❌ Format invalide. Ex: `30s` `5m` `1h`", ephemeral=True)
    if winners<1: return await interaction.response.send_message("❌ Min 1 winner.", ephemeral=True)
    import datetime as dt
    end_ts=int((dt.datetime.utcnow()+dt.timedelta(seconds=secs)).timestamp())
    e=discord.Embed(title="🎉 GIVEAWAY",
                    description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Host:** {interaction.user.mention}\n**Ends:** <t:{end_ts}:R>\n\nClick 🎉!",color=RED)
    await interaction.response.send_message("✅ Giveaway started!", ephemeral=True)
    msg=await interaction.channel.send(embed=e)
    active_giveaways[msg.id]={"prize":prize,"winners":winners,"host":interaction.user.id,"participants":set(),"channel_id":interaction.channel.id}
    await msg.edit(view=GiveawayView(msg.id))
    await asyncio.sleep(secs); await end_giveaway(interaction.channel.id,msg.id,interaction.guild)

@bot.tree.command(name="giveawayend",description="⏹️ End a giveaway manually")
@discord.app_commands.checks.has_permissions(manage_guild=True)
async def giveawayend(interaction, message_id:str):
    mid=int(message_id)
    if mid not in active_giveaways: return await interaction.response.send_message("❌ Not found.", ephemeral=True)
    await interaction.response.send_message("✅ Ended manually!", ephemeral=True)
    await end_giveaway(interaction.channel.id,mid,interaction.guild)

# ── Say ────────────────────────────────────────────────────────────────────────
class SayModal(discord.ui.Modal, title="📢 Send a message as the bot"):
    msg=discord.ui.TextInput(label="Message",style=discord.TextStyle.long,max_length=2000)
    def __init__(self,ch): super().__init__(); self.ch=ch
    async def on_submit(self,interaction): await self.ch.send(self.msg.value); await interaction.response.send_message(f"✅ Sent in {self.ch.mention}!",ephemeral=True)

class SayView(discord.ui.View):
    def __init__(self): super().__init__(timeout=120); self._add()
    def _add(self):
        s=discord.ui.ChannelSelect(placeholder="Select channel...",channel_types=[discord.ChannelType.text])
        async def cb(i): await i.response.send_modal(SayModal(i.guild.get_channel(i.data["values"][0])))
        s.callback=cb; self.add_item(s)

@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx):
    await ctx.message.delete()
    await ctx.send(embed=red_embed("Select the target channel, then type your message.","📢 Send as bot"),view=SayView(),delete_after=120)

# ── TOS ────────────────────────────────────────────────────────────────────────
TOS = {
"fr": """📋 **Slayzix Shop — CGV**

**1. Remboursement** — Aucun remboursement après paiement.
**2. Anti-Spam** — Spam = commande annulée sans remboursement.
**3. Respect** — Comportement toxique = bannissement.
**4. Délai** — Variable selon le produit. Soyez patient.
**5. Responsabilité** — Informations incorrectes = votre responsabilité.
**6. Stock** — Produits temporairement indisponibles possibles.
**7. Vouchs** — Laissez un vouch après réception.
**8. Modifications** — CGV modifiables à tout moment.

Merci de faire confiance à **Slayzix Shop** 🤝""",
"en": """📋 **Slayzix Shop — TOS**

**1. No Refund** — All payments are final.
**2. Spam Policy** — Spamming = order cancelled without refund.
**3. Respect Staff** — Toxic behavior = ban or cancellation.
**4. Delivery** — Varies by product. Please be patient.
**5. Responsibility** — Incorrect info = customer's fault.
**6. Stock** — Some items may be temporarily unavailable.
**7. Vouches** — Please leave a vouch after receiving your order.
**8. TOS Changes** — We reserve the right to modify at any time.

Thank you for trusting **Slayzix Shop** 🤝"""
}

class TOSView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🇫🇷 Français", style=discord.ButtonStyle.secondary, custom_id="tos_fr")
    async def fr(self,i,b):
        e=discord.Embed(title="📋 Slayzix Shop — CGV",description=TOS["fr"],color=RED)
        e.set_image(url=BANNER_URL); await i.response.send_message(embed=e,ephemeral=True)
    @discord.ui.button(label="🇬🇧 English", style=discord.ButtonStyle.secondary, custom_id="tos_en")
    async def en(self,i,b):
        e=discord.Embed(title="📋 Slayzix Shop — TOS",description=TOS["en"],color=RED)
        e.set_image(url=BANNER_URL); await i.response.send_message(embed=e,ephemeral=True)

@bot.command(name="tos")
@commands.has_permissions(administrator=True)
async def tos_cmd(ctx):
    await ctx.message.delete()
    e=discord.Embed(title="📋 TOS / CGV",description="Choisissez votre langue / Choose your language.",color=RED)
    e.set_image(url=BANNER_URL); await ctx.send(embed=e,view=TOSView())

# ── We Are Legit ───────────────────────────────────────────────────────────────
@bot.command(name="wearelegit")
@commands.has_permissions(administrator=True)
async def wearelegit(ctx):
    await ctx.message.delete()
    e=discord.Embed(title="Slayzix Shop Legit?",description="<:oui:1480176155989508348> = Yes\n<:non:1480176175589621821> No = **Ban**",color=RED)
    e.set_image(url=BANNER_URL); await ctx.send(embed=e)

# ── Moderation ─────────────────────────────────────────────────────────────────
async def _mod_send(ctx, desc, title=None, after=10):
    await ctx.send(embed=red_embed(desc, title), delete_after=after)

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_cmd(ctx, n:int=10):
    await ctx.message.delete(); d=await ctx.channel.purge(limit=n)
    await ctx.send(embed=red_embed(f"🗑️ **{len(d)}** messages supprimés."), delete_after=5)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, m:discord.Member, *, r:str="Aucune raison"):
    await ctx.message.delete(); await m.ban(reason=r)
    await _mod_send(ctx, f"**{m}** banni.\n**Raison:** {r}", "🔨 Membre banni")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, m:discord.Member, *, r:str="Aucune raison"):
    await ctx.message.delete(); await m.kick(reason=r)
    await _mod_send(ctx, f"**{m}** kick.\n**Raison:** {r}", "👢 Membre kick")

@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute_cmd(ctx, m:discord.Member, d:int=10, *, r:str="Aucune raison"):
    await ctx.message.delete(); await m.timeout(discord.utils.utcnow()+discord.timedelta(minutes=d),reason=r)
    await _mod_send(ctx, f"{m.mention} muté **{d} min**.\n**Raison:** {r}", "🔇 Muté")

@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute_cmd(ctx, m:discord.Member):
    await ctx.message.delete(); await m.timeout(None)
    await _mod_send(ctx, f"🔊 {m.mention} unmute.")

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban_cmd(ctx, user_id:int):
    await ctx.message.delete(); u=await bot.fetch_user(user_id); await ctx.guild.unban(u)
    await _mod_send(ctx, f"✅ **{u}** unban.")

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock_cmd(ctx):
    await ctx.message.delete(); await ctx.channel.set_permissions(ctx.guild.default_role,send_messages=False)
    await _mod_send(ctx,"🔒 Salon **verrouillé**.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock_cmd(ctx):
    await ctx.message.delete(); await ctx.channel.set_permissions(ctx.guild.default_role,send_messages=True)
    await _mod_send(ctx,"🔓 Salon **déverrouillé**.")

@bot.command(name="announce")
@commands.has_permissions(administrator=True)
async def announce_cmd(ctx, channel:discord.TextChannel, *, msg:str):
    await ctx.message.delete()
    e=discord.Embed(title="📢 Annonce — Slayzix Shop",description=msg,color=RED)
    e.set_image(url=BANNER_URL); e.timestamp=discord.utils.utcnow(); await channel.send(embed=e)
    await _mod_send(ctx,f"✅ Annonce → {channel.mention}",after=5)

# ── Stats / Info ───────────────────────────────────────────────────────────────
@bot.command(name="stats")
@commands.has_permissions(manage_guild=True)
async def stats(ctx, member:discord.Member=None):
    await ctx.message.delete(); t=member or ctx.author
    roles=[r.mention for r in reversed(t.roles) if r.name!="@everyone"]
    e=discord.Embed(title=f"📊 Stats — {t.display_name}",color=RED)
    e.set_thumbnail(url=t.display_avatar.url)
    e.add_field(name="👤 Compte",value=f"**Nom:** {t.name}\n**ID:** `{t.id}`",inline=True)
    e.add_field(name="📅 Dates",value=f"**Créé:** <t:{int(t.created_at.timestamp())}:D>\n**Rejoint:** <t:{int(t.joined_at.timestamp())}:D>",inline=True)
    e.add_field(name="🏆 Vouchs",value=f"`{vouch_counts.get(str(t.id),0)}`",inline=True)
    e.add_field(name=f"🎭 Rôles ({len(roles)})",value=" ".join(roles)[:1024] or "Aucun",inline=False)
    e.timestamp=discord.utils.utcnow(); await ctx.send(embed=e)

@bot.command(name="userinfo")
async def userinfo_cmd(ctx, member:discord.Member=None):
    await ctx.message.delete(); t=member or ctx.author
    roles=[r.mention for r in reversed(t.roles) if r.name!="@everyone"]
    e=discord.Embed(title=f"👤 {t.display_name}",color=RED)
    e.set_thumbnail(url=t.display_avatar.url)
    e.add_field(name="ID",value=f"`{t.id}`",inline=True)
    e.add_field(name="Créé",value=f"<t:{int(t.created_at.timestamp())}:D>",inline=True)
    e.add_field(name="Rejoint",value=f"<t:{int(t.joined_at.timestamp())}:D>",inline=True)
    e.add_field(name=f"Rôles ({len(roles)})",value=" ".join(roles[:10]) or "Aucun",inline=False)
    await ctx.send(embed=e)

@bot.command(name="serverinfo")
async def serverinfo_cmd(ctx):
    await ctx.message.delete(); g=ctx.guild
    e=discord.Embed(title=f"🏠 {g.name}",color=RED)
    if g.icon: e.set_thumbnail(url=g.icon.url)
    e.add_field(name="👑 Owner",value=g.owner.mention,inline=True)
    e.add_field(name="👥 Membres",value=f"`{g.member_count}`",inline=True)
    e.add_field(name="📅 Créé",value=f"<t:{int(g.created_at.timestamp())}:D>",inline=True)
    e.add_field(name="💬 Salons",value=f"`{len(g.channels)}`",inline=True)
    e.add_field(name="🎭 Rôles",value=f"`{len(g.roles)}`",inline=True)
    e.add_field(name="🚀 Boosts",value=f"`{g.premium_subscription_count}`",inline=True)
    e.set_footer(text=f"ID: {g.id}"); await ctx.send(embed=e)

# ── Prefix ─────────────────────────────────────────────────────────────────────
@bot.command(name="prefix")
@commands.has_permissions(administrator=True)
async def prefix_cmd(ctx, new:str):
    await ctx.message.delete(); bot.command_prefix=new
    await ctx.send(embed=red_embed(f"Nouveau préfixe : `{new}`","⚙️ Préfixe mis à jour"),delete_after=8)

# ── DM All ─────────────────────────────────────────────────────────────────────
@bot.command(name="dmall")
@commands.has_permissions(administrator=True)
async def dmall_cmd(ctx, *, message:str):
    await ctx.message.delete()
    members=[m for m in ctx.guild.members if not m.bot]
    confirm=await ctx.send(embed=red_embed(f"Envoyer à **{len(members)}** membres :\n*{message}*\nRéponds `oui`","📨 DM All"))
    try: await bot.wait_for("message",check=lambda m:m.author==ctx.author and m.content.lower()=="oui",timeout=30)
    except asyncio.TimeoutError: await confirm.delete(); return await ctx.send(embed=red_embed("❌ Annulé."),delete_after=5)
    await confirm.delete(); prog=await ctx.send(embed=red_embed("📨 Envoi en cours..."))
    ok=fail=0; dm_e=discord.Embed(title="📨 Message de Slayzix Shop",description=message,color=RED)
    dm_e.set_footer(text="Slayzix Shop"); dm_e.timestamp=discord.utils.utcnow()
    for m in members:
        try: await m.send(embed=dm_e); ok+=1
        except Exception: fail+=1
        await asyncio.sleep(0.5)
    await prog.edit(embed=red_embed(f"✅ Envoyé: **{ok}**\n❌ Échec: **{fail}**","✅ DM All terminé"))

# ── Anti-spam / protection ─────────────────────────────────────────────────────
spam_tracker=defaultdict(list); warned_users=set()
SPAM_LIMIT=5; SPAM_WINDOW=4; MUTE_DURATION=300
protection_enabled=True
protection_config={"anti_spam":True,"anti_invite":True,"anti_mention_mass":True,"mention_limit":5,"log_channel":None}

async def _plog(guild, action, member, reason):
    if protection_config["log_channel"]:
        ch=guild.get_channel(protection_config["log_channel"])
        if ch:
            e=red_embed(f"**Membre:** {member.mention}\n**Raison:** {reason}",f"🛡️ {action}")
            e.timestamp=discord.utils.utcnow(); await ch.send(embed=e)

@bot.listen("on_message")
async def protection_listener(message):
    if not protection_enabled or not message.guild or message.author.bot: return
    member=message.guild.get_member(message.author.id)
    if not member or member.guild_permissions.administrator: return
    now=time_module.time(); uid=message.author.id

    if protection_config["anti_spam"]:
        spam_tracker[uid]=[t for t in spam_tracker[uid] if now-t<SPAM_WINDOW]
        spam_tracker[uid].append(now)
        if len(spam_tracker[uid])>=SPAM_LIMIT:
            spam_tracker[uid]=[]
            try:
                await member.timeout(discord.utils.utcnow()+discord.timedelta(seconds=MUTE_DURATION),reason="Anti-spam")
                if uid not in warned_users:
                    warned_users.add(uid)
                    await message.channel.send(embed=red_embed(f"⏱️ {member.mention} timeout 5 min pour spam."),delete_after=10)
                await _plog(message.guild,"Anti-Spam",member,f"{SPAM_LIMIT} msg/{SPAM_WINDOW}s")
            except discord.Forbidden: pass
            return

    if protection_config["anti_invite"] and ("discord.gg/" in message.content or "discord.com/invite/" in message.content):
        try:
            await message.delete()
            await message.channel.send(embed=red_embed(f"🚫 {member.mention} Les invitations sont interdites !"),delete_after=8)
            await _plog(message.guild,"Anti-Invite",member,"Lien d'invitation posté")
        except discord.Forbidden: pass
        return

    if protection_config["anti_mention_mass"]:
        mc=len(message.mentions)+len(message.role_mentions)
        if mc>=protection_config["mention_limit"]:
            try:
                await message.delete()
                await member.timeout(discord.utils.utcnow()+discord.timedelta(seconds=MUTE_DURATION),reason="Anti-mention")
                await message.channel.send(embed=red_embed(f"🚫 {member.mention} Mention de masse — timeout 5 min."),delete_after=10)
                await _plog(message.guild,"Anti-Mention",member,f"{mc} mentions")
            except discord.Forbidden: pass

@bot.command(name="protect")
@commands.has_permissions(administrator=True)
async def protect_cmd(ctx, action:str="status"):
    await ctx.message.delete(); global protection_enabled
    if action=="on": protection_enabled=True; desc="✅ Protection **activée**."
    elif action=="off": protection_enabled=False; desc="⛔ Protection **désactivée**."
    else:
        desc=(f"🛡️ {'✅ ON' if protection_enabled else '⛔ OFF'}\n"
              f"• Anti-Spam: {'✅' if protection_config['anti_spam'] else '❌'}\n"
              f"• Anti-Invite: {'✅' if protection_config['anti_invite'] else '❌'}\n"
              f"• Anti-Mention: {'✅' if protection_config['anti_mention_mass'] else '❌'}\n"
              f"• Log: {'<#'+str(protection_config['log_channel'])+'>' if protection_config['log_channel'] else '❌'}")
    await ctx.send(embed=red_embed(desc,"🛡️ Protection Slayzix"),delete_after=15)

@bot.command(name="protectlog")
@commands.has_permissions(administrator=True)
async def protectlog_cmd(ctx, channel:discord.TextChannel):
    await ctx.message.delete(); protection_config["log_channel"]=channel.id
    await ctx.send(embed=red_embed(f"✅ Logs → {channel.mention}"),delete_after=8)

# ── /help ──────────────────────────────────────────────────────────────────────
@bot.tree.command(name="help",description="📋 Affiche toutes les commandes")
async def help_cmd(interaction):
    e=discord.Embed(title="📋 Commandes — Slayzix Shop",description="Préfixe: **`*`**",color=RED)
    e.add_field(name="🎫 Tickets",value="`*setup` `*setlogs #salon` `*setfrench/english/nitro/boost/deco/exchange/other @role`",inline=False)
    e.add_field(name="🔑 Accès Ticket",value="`*addaccessticket @m` `*removeaccessticket @m` `*listaccessticket`",inline=False)
    e.add_field(name="💳 PayPal",value="`*pplsave` `*ppl` `*ppldelete`",inline=False)
    e.add_field(name="🪙 LTC",value="`*ltcsave` `*ltc` `*ltcdelete`",inline=False)
    e.add_field(name="⭐ Vouch",value="`*vouch @staff note service comment` `*vouchsetup` `*vouchcount` `*setvouchrole` `*analyse`",inline=False)
    e.add_field(name="🎉 Giveaway",value="`/giveaway` `/giveawayend`",inline=False)
    e.add_field(name="🛡️ Protection",value="`*protect on/off/status` `*protectlog #salon`",inline=False)
    e.add_field(name="🔨 Modération",value="`*ban` `*kick` `*mute` `*unmute` `*unban` `*clear` `*lock` `*unlock`",inline=False)
    e.add_field(name="🎫 Ticket Utils",value="`*claim` `*unclaim` `*close` `*add` `*remove` `*rename` `*slowmode` `*finish`",inline=False)
    e.add_field(name="📢 Divers",value="`*say` `*announce` `*dmall` `*tos` `*wearelegit` `*stats` `*userinfo` `*serverinfo` `*prefix`",inline=False)
    if interaction.guild and interaction.guild.icon: e.set_thumbnail(url=interaction.guild.icon.url)
    e.set_footer(text="Préfixe: * • Slash: /help"); e.timestamp=discord.utils.utcnow()
    await interaction.response.send_message(embed=e,ephemeral=True)

# ── On ready ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} connecté — {len(bot.commands)} commandes chargées")
    print(f"📊 Vouchs chargés: {len(vouch_counts)} entrées depuis vouch_data.json")
    print(f"🔑 Staff ticket chargés: {len(ticket_staff_ids)} membres depuis ticket_staff.json")

# ── Start ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN: raise ValueError("❌ DISCORD_TOKEN manquant dans les variables d'environnement.")
    bot.run(TOKEN)
