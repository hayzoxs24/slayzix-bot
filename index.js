const fs = require("fs");
const chalk = require("chalk");
const figlet = require("figlet");
const {
  Client, GatewayIntentBits, Collection, EmbedBuilder, Partials,
  ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder,
  ModalBuilder, TextInputBuilder, TextInputStyle, AttachmentBuilder, PermissionFlagsBits
} = require("discord.js");

function loadJSON(path) {
  try { return JSON.parse(fs.readFileSync(path, "utf8") || "{}"); }
  catch (_) { return {}; }
}
function saveJSON(path, data) {
  fs.writeFileSync(path, JSON.stringify(data, null, 2));
}

let config         = loadJSON("./config.json");
let pplData        = loadJSON("./data/ppl.json");
let ltcData        = loadJSON("./data/ltc.json");
let ticketData     = loadJSON("./data/tickets.json");
let giveawayData   = loadJSON("./data/giveaways.json");
let warnData       = loadJSON("./data/warns.json");
let pendingVouches = loadJSON("./data/pending_vouches.json");

const BANNER_URL          = "https://i.ibb.co/fdJxKj7c/BANNIERE.png";
const VOUCH_SERVER_INVITE = "https://discord.gg/eyXdtxUDC7";
const RED = 0xFF0000;

// ── Vouch : fixe ───────────────────────────────────────────────────────────────
const VOUCH_CHANNEL_ID = "1482763336364851263";
const VOUCH_DELAY_MS   = 3600000; // 1h
const WARN_LIMIT       = 3;

// ── Ticket types / paiements (repris du code Python original) ─────────────────
const TICKET_TYPES = [
  { label: "Nitro",        emoji: "<:Nitro:1480046132707987611>",    value: "Nitro" },
  { label: "Server Boost", emoji: "<:Boost:1480046746146050149>",    value: "Server Boost" },
  { label: "Decoration",   emoji: "<:Discord:1480047123188944906>",  value: "Decoration" },
  { label: "Exchange",     emoji: "<:Exchange:1480047481491427492>", value: "Exchange" },
  { label: "Other",        emoji: "<:Other:1480047561615085638>",    value: "Other" },
];
const PAYMENT_OPTIONS = [
  { label: "PayPal", emoji: "<:PPL:1480046672162852985>", value: "PayPal" },
  { label: "LTC",    emoji: "<:LTC:1480634361555452176>", value: "LTC" },
];
const TYPE_ROLE_MAP = {
  "Nitro":        "role_nitro",
  "Server Boost": "role_boost",
  "Decoration":   "role_decoration",
  "Exchange":     "role_exchange",
  "Other":        "role_other"
};

const openTickets    = {};
const ticketClaimers = {};
const pingCooldowns  = {};
const spamTracker    = {};
const warnedUsers    = new Set();

process.stdout.write("\x1B[2J\x1B[0f");
console.log(chalk.hex("#FF0000")(figlet.textSync("Slayzix Bot", { font: "ANSI Shadow", horizontalLayout: "full" })));
console.log(chalk.hex("#FF0000")("═".repeat(80)));

function redEmbed(desc, title) {
  const e = new EmbedBuilder().setColor(RED);
  if (title) e.setTitle(title);
  if (desc)  e.setDescription(desc);
  return e;
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildPresences,
    GatewayIntentBits.GuildVoiceStates
  ],
  partials: [Partials.Message, Partials.Channel, Partials.GuildMember, Partials.User]
});

client.commands = new Collection();
const commandFiles = fs.readdirSync("./commands").filter(f => f.endsWith(".js"));
for (const file of commandFiles) {
  const cmd = require(`./commands/${file}`);
  if (cmd.name) client.commands.set(cmd.name, cmd);
}

// ─────────────────────────────────────────────────────────────────────────────
//  WARN / BAN SYSTEM
// ─────────────────────────────────────────────────────────────────────────────
function schedulePendingVouch(userId, staffId, product, price, payment, vouchMsg) {
  const deadline = Date.now() + VOUCH_DELAY_MS;
  pendingVouches[userId] = { userId, staffId, product, price, payment, vouchMsg, deadline, vouched: false };
  saveJSON("./data/pending_vouches.json", pendingVouches);
  setTimeout(() => checkVouch(userId), VOUCH_DELAY_MS);
  console.log(chalk.yellow(`⏱️  Vouch pending pour ${userId} — vérification dans 60 min`));
}

function restorePendingVouches() {
  pendingVouches = loadJSON("./data/pending_vouches.json");
  const now = Date.now();
  let n = 0;
  for (const [uid, data] of Object.entries(pendingVouches)) {
    if (data.vouched) continue;
    setTimeout(() => checkVouch(uid), Math.max(data.deadline - now, 5000));
    n++;
  }
  if (n) console.log(chalk.yellow(`⏱️  ${n} vouch(s) pending restauré(s)`));
}

async function checkVouch(userId) {
  pendingVouches = loadJSON("./data/pending_vouches.json");
  const data = pendingVouches[userId];
  if (!data || data.vouched) return;
  console.log(chalk.red(`⚠️  ${userId} n'a pas vouché → warn`));
  await warnUser(userId, data);
}

async function warnUser(userId, pendingData) {
  warnData = loadJSON("./data/warns.json");
  if (!warnData[userId]) warnData[userId] = { count: 0, history: [] };
  warnData[userId].count++;
  warnData[userId].history.push({
    date:   new Date().toLocaleString("fr-FR"),
    reason: `Vouch non effectué — ${pendingData?.product || "?"} | ${pendingData?.price || "?"}`
  });
  saveJSON("./data/warns.json", warnData);
  const count = warnData[userId].count;
  delete pendingVouches[userId];
  saveJSON("./data/pending_vouches.json", pendingVouches);

  try {
    const user = await client.users.fetch(userId);
    if (count >= WARN_LIMIT) {
      await user.send({ embeds: [new EmbedBuilder().setColor(RED)
        .setTitle("🔨 Tu as été banni — Slayzix Shop")
        .setDescription(`Tu as accumulé **${count}/${WARN_LIMIT} warns** pour ne pas avoir laissé de vouch.\n\nTu as été **banni de tous les serveurs** où le bot est présent.\n\nSi tu penses que c'est une erreur, contacte un administrateur.`)
        .setImage(BANNER_URL).setFooter({ text: "Slayzix Shop" }).setTimestamp()]
      }).catch(() => {});
    } else {
      await user.send({ embeds: [new EmbedBuilder().setColor(RED)
        .setTitle(`⚠️ Avertissement ${count}/${WARN_LIMIT} — Slayzix Shop`)
        .setDescription(
          `Tu n'as **pas laissé de vouch** après ton achat !\n\n` +
          `**📦 Produit :** ${pendingData?.product || "?"}\n` +
          `**💰 Prix :** ${pendingData?.price || "?"}\n` +
          `**💳 Paiement :** ${pendingData?.payment || "?"}\n\n` +
          `━━━━━━━━━━━━━━━━━━━━\n` +
          `👉 Rejoins le serveur : **${VOUCH_SERVER_INVITE}**\n\n` +
          `Et envoie dans **#vouchs** :\n\`\`\`${pendingData?.vouchMsg || "+vouch ..."}\`\`\`\n` +
          `━━━━━━━━━━━━━━━━━━━━\n` +
          `⚠️ Encore **${WARN_LIMIT - count} warn(s)** avant le **ban automatique** de tous les serveurs.`
        )
        .setImage(BANNER_URL).setFooter({ text: `Slayzix Shop • Warn ${count}/${WARN_LIMIT}` }).setTimestamp()]
      }).catch(() => {});
    }
  } catch (err) { console.error(`DM warn impossible pour ${userId}:`, err.message); }

  if (count >= WARN_LIMIT) await banFromAllServers(userId);
}

async function banFromAllServers(userId) {
  const reason = `[Slayzix Bot] ${WARN_LIMIT} warns — Vouch(s) non effectué(s)`;
  let banned = 0;
  for (const guild of client.guilds.cache.values()) {
    try { await guild.members.ban(userId, { reason, deleteMessageSeconds: 0 }); banned++; console.log(chalk.red(`🔨 ${userId} banni de "${guild.name}"`)); }
    catch (_) {}
  }
  console.log(chalk.red(`🔨 Ban terminé : ${banned} serveur(s) pour ${userId}`));
  warnData = loadJSON("./data/warns.json");
  delete warnData[userId];
  saveJSON("./data/warns.json", warnData);
}

// ─────────────────────────────────────────────────────────────────────────────
//  READY
// ─────────────────────────────────────────────────────────────────────────────
client.once("clientReady", () => {
  console.log(chalk.green(`✅ Connecté : ${client.user.tag}`));
  console.log(chalk.cyan(`💬 Préfixe : ${config.prefix}`));
  restoreGiveaways();
  restorePendingVouches();
});

// ─────────────────────────────────────────────────────────────────────────────
//  MESSAGES
// ─────────────────────────────────────────────────────────────────────────────
client.on("messageCreate", async (message) => {
  if (message.author.bot || !message.guild) return;

  // ── Détection vouch ────────────────────────────────────────────────────────
  if (message.channel.id === VOUCH_CHANNEL_ID) {
    if (message.content.trim().toLowerCase().startsWith("+vouch")) {
      const uid = message.author.id;
      pendingVouches = loadJSON("./data/pending_vouches.json");
      if (pendingVouches[uid] && !pendingVouches[uid].vouched) {
        pendingVouches[uid].vouched = true;
        saveJSON("./data/pending_vouches.json", pendingVouches);
        console.log(chalk.green(`✅ Vouch validé pour ${uid}`));
      }
    }
    return;
  }

  // ── Anti-spam ──────────────────────────────────────────────────────────────
  if (config.protection?.enabled && config.protection?.anti_spam) {
    const uid = message.author.id;
    const now = Date.now();
    if (!spamTracker[uid]) spamTracker[uid] = [];
    spamTracker[uid] = spamTracker[uid].filter(t => now - t < 4000);
    spamTracker[uid].push(now);
    if (spamTracker[uid].length >= 5) {
      spamTracker[uid] = [];
      try {
        const m = await message.guild.members.fetch(uid);
        await m.timeout(300000, "Anti-spam");
        if (!warnedUsers.has(uid)) {
          warnedUsers.add(uid);
          message.channel.send({ embeds: [redEmbed(`⏱️ ${message.author} timeout 5 min pour spam.`)] })
            .then(msg => setTimeout(() => msg.delete().catch(() => {}), 10000));
        }
      } catch (_) {}
      return;
    }
  }

  // ── Anti-invite ────────────────────────────────────────────────────────────
  if (config.protection?.enabled && config.protection?.anti_invite) {
    if (/discord\.gg\/|discord\.com\/invite\//.test(message.content)) {
      try {
        await message.delete();
        message.channel.send({ embeds: [redEmbed(`🚫 ${message.author} Les invitations sont interdites !`)] })
          .then(msg => setTimeout(() => msg.delete().catch(() => {}), 8000));
      } catch (_) {}
      return;
    }
  }

  // ── Anti-mention ───────────────────────────────────────────────────────────
  if (config.protection?.enabled && config.protection?.anti_mention) {
    const mc = message.mentions.users.size + message.mentions.roles.size;
    if (mc >= (config.protection.mention_limit || 5)) {
      try {
        await message.delete();
        const m = await message.guild.members.fetch(message.author.id);
        await m.timeout(300000, "Anti-mention");
        message.channel.send({ embeds: [redEmbed(`🚫 ${message.author} Mention de masse — timeout 5 min.`)] })
          .then(msg => setTimeout(() => msg.delete().catch(() => {}), 10000));
      } catch (_) {}
      return;
    }
  }

  // ── Commandes ──────────────────────────────────────────────────────────────
  if (!message.content.startsWith(config.prefix)) return;
  const args = message.content.slice(config.prefix.length).trim().split(/ +/);
  const commandName = args.shift().toLowerCase();
  const command = client.commands.get(commandName);
  if (!command) return;

  try {
    await command.execute(message, args, client, {
      config, pplData, ltcData, ticketData, giveawayData,
      warnData, pendingVouches,
      openTickets, ticketClaimers, pingCooldowns,
      saveJSON, redEmbed, BANNER_URL, RED,
      schedulePendingVouch, warnUser, banFromAllServers
    });
  } catch (err) {
    console.error(err);
    message.reply("⚠️ Erreur lors de l'exécution de la commande.").catch(() => {});
  }
});

// ─────────────────────────────────────────────────────────────────────────────
//  INTERACTIONS
// ─────────────────────────────────────────────────────────────────────────────
client.on("interactionCreate", async (interaction) => {
  try {

    // ── TICKET : sélection du type ─────────────────────────────────────────
    if (interaction.isStringSelectMenu() && interaction.customId === "ticket_type_select") {
      const type = interaction.values[0];
      if (openTickets[interaction.user.id]) {
        const ex = interaction.guild.channels.cache.get(openTickets[interaction.user.id]);
        if (ex) return interaction.reply({ content: `❌ You already have an open ticket → ${ex}`, ephemeral: true });
      }
      // Sélection du paiement avec emojis custom du code Python
      const payRow = new ActionRowBuilder().addComponents(
        new StringSelectMenuBuilder()
          .setCustomId("ticket_payment_select")
          .setPlaceholder("Select your payment method...")
          .addOptions(PAYMENT_OPTIONS.map(p => ({ label: p.label, value: `${type}|${p.value}`, emoji: p.emoji })))
      );
      const e = new EmbedBuilder().setColor(RED)
        .setTitle("<:Paiement:1480046846658351276> Payment Method")
        .setDescription("Select your payment method:")
        .setFooter({ text: "Your ticket will be created after selection" });
      return interaction.reply({ embeds: [e], components: [payRow], ephemeral: true });
    }

    // ── TICKET : sélection du paiement → sélection de langue ──────────────────
    if (interaction.isStringSelectMenu() && interaction.customId === "ticket_payment_select") {
      const [type, payment] = interaction.values[0].split("|");
      const langRow = new ActionRowBuilder().addComponents(
        new StringSelectMenuBuilder()
          .setCustomId("ticket_lang_select")
          .setPlaceholder("🌍 Select your language...")
          .addOptions([
            { label: "Français", value: `${type}|${payment}|fr`, emoji: "🇫🇷" },
            { label: "English",  value: `${type}|${payment}|en`, emoji: "🇬🇧" }
          ])
      );
      const e = new EmbedBuilder().setColor(RED)
        .setTitle("🌍 Language / Langue")
        .setDescription("Please select your language.\nVeuillez sélectionner votre langue.");
      return interaction.update({ embeds: [e], components: [langRow] });
    }

    // ── TICKET : sélection langue → créer ticket ────────────────────────────────
    if (interaction.isStringSelectMenu() && interaction.customId === "ticket_lang_select") {
      const [type, payment, lang] = interaction.values[0].split("|");
      await interaction.update({ components: [], embeds: [new EmbedBuilder().setColor(RED).setDescription("⏳ Creating your ticket...")] });
      await createTicketChannel(interaction, type, payment, lang);
      return;
    }

    // ── TICKET : boutons ───────────────────────────────────────────────────
    if (interaction.isButton()) {
      const id = interaction.customId;

      if (id === "ticket_close") {
        const isFr = ticketData[`chan_${interaction.channel.id}`]?.lang === "fr";
        await interaction.reply({ content: isFr ? "🔒 Fermeture du ticket dans 5 secondes..." : "🔒 Closing ticket in 5 seconds..." });
        logTicket(interaction.guild, "📋 Ticket fermé", `**Salon:** ${interaction.channel.name}\n**Par:** ${interaction.user}`);
        const uid = Object.keys(openTickets).find(u => openTickets[u] === interaction.channel.id);
        if (uid) delete openTickets[uid];
        setTimeout(() => interaction.channel.delete().catch(() => {}), 5000);
        return;
      }

      if (id === "ticket_claim") {
        if (!hasTicketAccess(interaction.member))
          return interaction.reply({ content: "❌ You don't have permission to claim this ticket.", ephemeral: true });
        const ownerUid = Object.keys(openTickets).find(u => openTickets[u] === interaction.channel.id);
        const owner = ownerUid ? interaction.guild.members.cache.get(ownerUid) : null;
        for (const [target] of interaction.channel.permissionOverwrites.cache) {
          const t = interaction.guild.members.cache.get(target) || interaction.guild.roles.cache.get(target);
          if (!t || t.id === interaction.user.id || t.id === interaction.guild.members.me.id) continue;
          if (t.permissions?.has(PermissionFlagsBits.Administrator)) continue;
          if (owner && t.id === owner.id) continue;
          await interaction.channel.permissionOverwrites.edit(t.id, { SendMessages: false }).catch(() => {});
        }
        await interaction.channel.permissionOverwrites.edit(interaction.user.id, { ViewChannel: true, SendMessages: true, AttachFiles: true });
        if (owner) await interaction.channel.permissionOverwrites.edit(owner.id, { ViewChannel: true, SendMessages: true, AttachFiles: true });
        ticketClaimers[interaction.channel.id] = interaction.user.id;
        const isFr = ticketData[`chan_${interaction.channel.id}`]?.lang === "fr";
        return interaction.reply({ embeds: [redEmbed(isFr
          ? `✅ Ticket pris en charge par ${interaction.user}\n🔒 Seul le staff et le créateur peuvent écrire.`
          : `✅ Ticket claimed by ${interaction.user}\n🔒 Only staff and the ticket owner can write.`)] });
      }

      if (id === "ticket_unclaim") {
        if (!hasTicketAccess(interaction.member))
          return interaction.reply({ content: "❌ You don't have permission to unclaim this ticket.", ephemeral: true });
        const ownerUid = Object.keys(openTickets).find(u => openTickets[u] === interaction.channel.id);
        const owner = ownerUid ? interaction.guild.members.cache.get(ownerUid) : null;
        if (owner) await interaction.channel.permissionOverwrites.edit(owner.id, { ViewChannel: true, SendMessages: true, AttachFiles: true }).catch(() => {});
        for (const sid of (config.ticket_staff_ids || [])) {
          const m = interaction.guild.members.cache.get(String(sid));
          if (m) await interaction.channel.permissionOverwrites.edit(m.id, { ViewChannel: true, SendMessages: true }).catch(() => {});
        }
        if (config.ticket_config?.support_role)
          await interaction.channel.permissionOverwrites.edit(config.ticket_config.support_role, { ViewChannel: true, SendMessages: true }).catch(() => {});
        delete ticketClaimers[interaction.channel.id];
        const isFr2 = ticketData[`chan_${interaction.channel.id}`]?.lang === "fr";
        return interaction.reply({ embeds: [redEmbed(isFr2
          ? `🔄 Ticket rendu par ${interaction.user}\n🔓 Accès restauré.`
          : `🔄 Ticket unclaimed by ${interaction.user}\n🔓 Access restored.`)] });
      }

      if (id === "ticket_transcript") {
        await interaction.deferReply({ ephemeral: true });
        const msgs = await interaction.channel.messages.fetch({ limit: 200 });
        const lines = [...msgs.values()].filter(m => !m.author.bot)
          .sort((a, b) => a.createdTimestamp - b.createdTimestamp)
          .map(m => `[${new Date(m.createdTimestamp).toLocaleString("fr-FR")}] ${m.author.tag}: ${m.content}`).join("\n");
        if (!lines) return interaction.followUp({ content: ticketData[`chan_${interaction.channel.id}`]?.lang === "fr" ? "Aucun message." : "No messages.", ephemeral: true });
        const isFrT = ticketData[`chan_${interaction.channel.id}`]?.lang === "fr";
        return interaction.followUp({
          content: isFrT ? "📄 Transcript généré !" : "📄 Transcript generated!",
          files: [new AttachmentBuilder(Buffer.from(lines, "utf8"), { name: `transcript-${interaction.channel.name}.txt` })],
          ephemeral: true
        });
      }

      if (id === "ticket_finish") {
        if (!hasTicketAccess(interaction.member))
          return interaction.reply({ content: "❌ Permission denied.", ephemeral: true });
        const claimerId = ticketClaimers[interaction.channel.id];
        const claimer   = claimerId ? interaction.guild.members.cache.get(claimerId) : null;
        if (!claimer) return interaction.reply({ content: "❌ No staff has claimed this ticket yet!", ephemeral: true });
        return interaction.showModal(buildFinishModal(claimer.id, interaction.channel.id));
      }

      if (id === "ticket_ping") {
        const now = Date.now(), last = pingCooldowns[interaction.channel.id] || 0;
        if (now - last < 900000) {
          const rem = Math.floor((900000 - (now - last)) / 1000);
          return interaction.reply({ content: `⏳ Cooldown! **${Math.floor(rem/60)}m ${rem%60}s**`, ephemeral: true });
        }
        pingCooldowns[interaction.channel.id] = now;
        const mentions = [];
        const tInfo = ticketData[`chan_${interaction.channel.id}`];
        if (tInfo?.type) { const k = TYPE_ROLE_MAP[tInfo.type]; if (k && config.ticket_config?.[k]) mentions.push(`<@&${config.ticket_config[k]}>`); }
        if (config.ticket_config?.support_role) { const sr = `<@&${config.ticket_config.support_role}>`; if (!mentions.includes(sr)) mentions.push(sr); }
        if (mentions.length) await interaction.channel.send({ content: mentions.join(" ") + (ticketData[`chan_${interaction.channel.id}`]?.lang === "fr" ? " — Un client attend !" : " — A customer needs help!"), allowedMentions: { roles: mentions.map(m => m.slice(3, -1)) } });
        return interaction.reply({ content: ticketData[`chan_${interaction.channel.id}`]?.lang === "fr" ? "✅ Staff pingé !" : "✅ Staff pinged!", ephemeral: true });
      }

      // ── Giveaway ───────────────────────────────────────────────────────────
      if (id.startsWith("giveaway_")) {
        const gid = id.split("_")[1];
        giveawayData = loadJSON("./data/giveaways.json");
        const g = giveawayData[gid];
        if (!g || g.ended) return interaction.reply({ content: "❌ This giveaway has ended.", ephemeral: true });
        if (!g.participants) g.participants = [];
        const idx = g.participants.indexOf(interaction.user.id);
        if (idx >= 0) { g.participants.splice(idx, 1); } else { g.participants.push(interaction.user.id); }
        saveJSON("./data/giveaways.json", giveawayData);
        return interaction.reply({ content: idx >= 0 ? "❌ You withdrew from the giveaway." : "✅ You joined the giveaway! 🍀", ephemeral: true });
      }
    }

    // ── MODALS ─────────────────────────────────────────────────────────────
    if (interaction.isModalSubmit()) {

      // Finish modal
      if (interaction.customId.startsWith("finish_modal_")) {
        const parts       = interaction.customId.split("_");
        const staffId     = parts[2];
        const chanId      = parts[3];
        const staffMember = interaction.guild.members.cache.get(staffId);
        const product     = interaction.fields.getTextInputValue("product").trim();
        const price       = interaction.fields.getTextInputValue("price").trim();
        const payment     = interaction.fields.getTextInputValue("payment").trim();
        const ownerUid    = Object.keys(openTickets).find(u => openTickets[u] === chanId);
        const owner       = ownerUid ? interaction.guild.members.cache.get(ownerUid) : null;
        const vouchMsg    = `+vouch ${staffMember ? staffMember.toString() : `<@${staffId}>`} ${product} | ${price} | ${payment}`;

        const recap = new EmbedBuilder().setColor(RED)
          .setTitle("✅ Transaction completed — Slayzix Shop")
          .addFields(
            { name: "🛠️ Staff",        value: staffMember ? `${staffMember}` : `<@${staffId}>`, inline: true },
            { name: "📦 Product",       value: product,  inline: true },
            { name: "💰 Price",         value: price,    inline: true },
            { name: "💳 Payment",       value: payment,  inline: true },
            { name: "📋 Vouch message", value: `\`\`\`${vouchMsg}\`\`\``, inline: false }
          )
          .setFooter({ text: "Slayzix Shop • Thank you for your purchase!" }).setTimestamp();
        await interaction.reply({ embeds: [recap] });

        if (owner) {
          try {
            const dm = new EmbedBuilder().setColor(RED)
              .setTitle("✅ Thank you for your purchase — Slayzix Shop!")
              .setDescription(
                `Your order has been processed by ${staffMember ? staffMember.toString() : `<@${staffId}>`}!\n\n` +
                `**📦 Product:** ${product}\n**💰 Price:** ${price}\n**💳 Payment:** ${payment}\n\n` +
                `━━━━━━━━━━━━━━━━━━━━\n` +
                `⭐ **You have 1 hour to leave your vouch!**\n\n` +
                `👉 Join our server: **${VOUCH_SERVER_INVITE}**\n\n` +
                `Then send this in **#vouchs**:\n\`\`\`${vouchMsg}\`\`\`\n` +
                `━━━━━━━━━━━━━━━━━━━━\n` +
                `⚠️ If you don't vouch within **1 hour**, you will receive a **warn**.\n` +
                `At **3 warns** you will be **automatically banned** from all servers.`
              )
              .setImage(BANNER_URL)
              .setFooter({ text: "Slayzix Shop • Thank you for your trust 🤝" }).setTimestamp();
            await owner.send({ embeds: [dm] });
            const chan = interaction.guild.channels.cache.get(chanId);
            if (chan) chan.send({ embeds: [redEmbed(`✅ DM sent to ${owner} — 1h vouch timer started ⏱️`)] })
              .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
          } catch {
            const chan = interaction.guild.channels.cache.get(chanId);
            if (chan) chan.send({ embeds: [redEmbed(`⚠️ DMs closed for ${owner}.\nVouch message: \`${vouchMsg}\``)] })
              .then(m => setTimeout(() => m.delete().catch(() => {}), 15000));
          }
          schedulePendingVouch(ownerUid, staffId, product, price, payment, vouchMsg);
        }
        return;
      }

      // PPL save
      if (interaction.customId === "ppl_save_modal") {
        const email = interaction.fields.getTextInputValue("email").trim();
        const nom   = interaction.fields.getTextInputValue("nom").trim();
        const note  = interaction.fields.getTextInputValue("note").trim();
        pplData[interaction.user.id] = { email, nom, note, updated_at: new Date().toLocaleString("fr-FR") };
        saveJSON("./data/ppl.json", pplData);
        return interaction.reply({ embeds: [redEmbed("Ton PayPal a été enregistré. Utilise `*ppl`.", "✅ PPL sauvegardé !")], ephemeral: true });
      }

      // LTC save
      if (interaction.customId === "ltc_save_modal") {
        const address = interaction.fields.getTextInputValue("address").trim();
        const note    = interaction.fields.getTextInputValue("note").trim();
        ltcData[interaction.user.id] = { address, note, updated_at: new Date().toLocaleString("fr-FR") };
        saveJSON("./data/ltc.json", ltcData);
        return interaction.reply({ embeds: [redEmbed("Ton LTC a été enregistré. Utilise `*ltc`.", "✅ LTC sauvegardé !")], ephemeral: true });
      }
    }
  } catch (err) {
    console.error("Interaction error:", err);
  }
});

// ─────────────────────────────────────────────────────────────────────────────
//  HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function hasTicketAccess(member) {
  return member.permissions.has(PermissionFlagsBits.Administrator)
    || member.permissions.has(PermissionFlagsBits.ManageMessages)
    || (config.ticket_staff_ids || []).includes(member.id);
}

function buildFinishModal(staffId, chanId) {
  return new ModalBuilder()
    .setCustomId(`finish_modal_${staffId}_${chanId}`)
    .setTitle("✅ Complete the transaction")
    .addComponents(
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("product").setLabel("Product").setStyle(TextInputStyle.Short).setMaxLength(100).setRequired(true)),
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("price").setLabel("Price").setStyle(TextInputStyle.Short).setMaxLength(30).setRequired(true)),
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("payment").setLabel("Payment method").setStyle(TextInputStyle.Short).setMaxLength(30).setRequired(true))
    );
}

function logTicket(guild, title, desc) {
  const lc = config.ticket_config?.log_channel ? guild.channels.cache.get(String(config.ticket_config.log_channel)) : null;
  if (lc) lc.send({ embeds: [redEmbed(desc, title).setTimestamp()] }).catch(() => {});
}

async function createTicketChannel(interaction, type, payment, lang = "en") {
  const guild = interaction.guild, user = interaction.user;

  if (openTickets[user.id]) {
    const ex = guild.channels.cache.get(openTickets[user.id]);
    if (ex) return interaction.followUp({ content: lang === "fr" ? `❌ Tu as déjà un ticket ouvert → ${ex}` : `❌ You already have an open ticket → ${ex}`, ephemeral: true });
  }

  const tc = config.ticket_config || {};
  let category = tc.category ? guild.channels.cache.get(String(tc.category)) : null;
  if (!category) category = guild.channels.cache.find(c => c.type === 4 && c.name === "TICKETS")
    || await guild.channels.create({ name: "TICKETS", type: 4 });

  const overwrites = [
    { id: guild.roles.everyone.id, deny: [PermissionFlagsBits.ViewChannel] },
    { id: user.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.AttachFiles] },
    { id: guild.members.me.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ManageChannels] }
  ];
  if (tc.support_role) overwrites.push({ id: String(tc.support_role), allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] });
  for (const sid of (config.ticket_staff_ids || [])) {
    const m = guild.members.cache.get(String(sid));
    if (m) overwrites.push({ id: m.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] });
  }

  const channel = await guild.channels.create({
    name: `${type.toLowerCase().replace(/ /g, "-")}-${user.username}`,
    type: 0, parent: category, permissionOverwrites: overwrites
  });

  openTickets[user.id] = channel.id;
  ticketData[`chan_${channel.id}`] = { type, payment, lang, userId: user.id };
  saveJSON("./data/tickets.json", ticketData);

  const isFr = lang === "fr";

  // Embed ticket avec titre et emojis du code Python original
  const embed = new EmbedBuilder().setColor(RED)
    .setTitle("<:Nitroo:1480046413441273968> " + (isFr ? "Nouveau Ticket" : "New Ticket"))
    .setDescription(isFr
      ? "Le support sera avec vous rapidement.\n\nPour fermer ce ticket, appuyez sur le bouton Fermer."
      : "Support will be with you shortly.\n\nTo close this ticket, press the close button below.")
    .addFields(
      { name: "<:Nitroo:1480046413441273968> Type",      value: type,    inline: true },
      { name: "<:Paiement:1480046846658351276> Payment", value: payment, inline: true },
      { name: "🌍 Language", value: isFr ? "🇫🇷 Français" : "🇬🇧 English", inline: true }
    )
    .setFooter({ text: isFr
      ? "🔔 Utilisez Ping Staff si aucune réponse après 15 min (cooldown 15 min)"
      : "🔔 Use Ping Staff if no response after 15 min (15 min cooldown)" })
    .setTimestamp();

  // Boutons repris exactement du code Python original
  const row1 = new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId("ticket_close")     .setLabel(isFr ? "Fermer"           : "Close")      .setStyle(ButtonStyle.Secondary).setEmoji("<:Other:1480047561615085638>"),
    new ButtonBuilder().setCustomId("ticket_claim")     .setLabel(isFr ? "Prendre en charge": "Claim")      .setStyle(ButtonStyle.Secondary).setEmoji("<:Boost:1480046746146050149>"),
    new ButtonBuilder().setCustomId("ticket_unclaim")   .setLabel(isFr ? "Rendre"           : "Unclaim")    .setStyle(ButtonStyle.Secondary).setEmoji("<:Exchange:1480047481491427492>"),
    new ButtonBuilder().setCustomId("ticket_transcript").setLabel("Transcript")                              .setStyle(ButtonStyle.Secondary).setEmoji("<:Transcript:1480047021707759727>")
  );
  const row2 = new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId("ticket_finish")    .setLabel("Finish")                                  .setStyle(ButtonStyle.Secondary).setEmoji("<:oui:1480176155989508348>"),
    new ButtonBuilder().setCustomId("ticket_ping")      .setLabel("Ping Staff")                              .setStyle(ButtonStyle.Secondary).setEmoji("<:Discord:1480047123188944906>")
  );

  // Mentions
  let mentions = `${user}`;
  if (tc.support_role) mentions += ` <@&${tc.support_role}>`;
  if (isFr && tc.role_french)   mentions += ` <@&${tc.role_french}>`;
  if (!isFr && tc.role_english) mentions += ` <@&${tc.role_english}>`;
  const tk = TYPE_ROLE_MAP[type]; if (tk && tc[tk]) mentions += ` <@&${tc[tk]}>`;

  await channel.send({ content: mentions, embeds: [embed], components: [row1, row2], allowedMentions: { parse: ["users", "roles"] } });
  logTicket(guild, "📋 Ticket ouvert", `**User:** ${user}\n**Type:** ${type}\n**Payment:** ${payment}\n**Lang:** ${lang}\n**Channel:** ${channel}`);
  await interaction.editReply({ embeds: [new EmbedBuilder().setColor(RED).setDescription(isFr ? `✅ Ticket créé → ${channel}` : `✅ Ticket created → ${channel}`)], components: [] }).catch(() => {});
}

// ─────────────────────────────────────────────────────────────────────────────
//  GIVEAWAY
// ─────────────────────────────────────────────────────────────────────────────
function restoreGiveaways() {
  giveawayData = loadJSON("./data/giveaways.json");
  let n = 0;
  for (const [id, g] of Object.entries(giveawayData)) {
    if (!g.ended && g.endTime > Date.now()) { setTimeout(() => endGiveaway(id), g.endTime - Date.now()); n++; }
  }
  if (n) console.log(chalk.green(`🎉 ${n} giveaway(s) restauré(s)`));
}

async function endGiveaway(gid) {
  giveawayData = loadJSON("./data/giveaways.json");
  const g = giveawayData[gid];
  if (!g || g.ended) return;
  g.ended = true;
  saveJSON("./data/giveaways.json", giveawayData);
  try {
    const channel = await client.channels.fetch(g.channelId);
    const message = await channel.messages.fetch(g.messageId);
    const participants = g.participants || [];
    if (!participants.length) {
      await message.edit({ embeds: [new EmbedBuilder().setColor(RED).setTitle("🎉 GIVEAWAY ENDED").setDescription(`**Prize:** ${g.prize}\n**Host:** <@${g.host}>\n\n😔 No participants!`).setTimestamp()], components: [] });
      await channel.send("😔 No participants, no winner!");
    } else {
      const winners = participants.sort(() => Math.random() - 0.5).slice(0, Math.min(g.winners, participants.length));
      const wm = winners.map(w => `<@${w}>`).join(" ");
      await message.edit({ embeds: [new EmbedBuilder().setColor(RED).setTitle("🎉 GIVEAWAY ENDED").setDescription(`**Prize:** ${g.prize}\n**Winner(s):** ${wm}\n**Host:** <@${g.host}>\n**Participants:** ${participants.length}`).setTimestamp()], components: [] });
      await channel.send(`🎊 Congratulations ${wm}! You won **${g.prize}**! Contact <@${g.host}> to claim your prize.`);
    }
  } catch (err) { console.error("Giveaway end error:", err); }
}

client.endGiveaway = endGiveaway;

client.login(process.env.DISCORD_TOKEN || config.token).catch(err => {
  console.log(chalk.red(`\n❌ Connection error: ${err.message}`));
  console.log(chalk.yellow("💡 Set your token in config.json"));
});
