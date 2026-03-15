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

// ── Vouch : fixe, ne pas modifier ─────────────────────────────────────────────
const VOUCH_CHANNEL_ID = "1482763336364851263"; // salon #vouchs fixe
const VOUCH_DELAY_MS   = 3600000;               // 1 heure fixe
const WARN_LIMIT       = 3;                     // 3 warns = ban

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
//  SYSTÈME VOUCH PENDING + WARN + BAN
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
    const remaining = data.deadline - now;
    setTimeout(() => checkVouch(uid), Math.max(remaining, 5000));
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

  const count    = warnData[userId].count;
  const maxWarns = WARN_LIMIT;

  delete pendingVouches[userId];
  saveJSON("./data/pending_vouches.json", pendingVouches);

  try {
    const user = await client.users.fetch(userId);

    if (count >= maxWarns) {
      // DM ban
      const e = new EmbedBuilder().setColor(RED)
        .setTitle("🔨 Tu as été banni — Slayzix Shop")
        .setDescription(
          `Tu as accumulé **${count}/${maxWarns} warns** pour ne pas avoir laissé de vouch.\n\n` +
          `Tu as été **banni de tous les serveurs** où le bot est présent.\n\n` +
          `Si tu penses que c'est une erreur, contacte un administrateur.`
        )
        .setImage(BANNER_URL)
        .setFooter({ text: "Slayzix Shop" }).setTimestamp();
      await user.send({ embeds: [e] }).catch(() => {});
    } else {
      // DM warn
      const e = new EmbedBuilder().setColor(RED)
        .setTitle(`⚠️ Avertissement ${count}/${maxWarns} — Slayzix Shop`)
        .setDescription(
          `Tu n'as **pas laissé de vouch** après ton achat !\n\n` +
          `**📦 Produit :** ${pendingData?.product || "?"}\n` +
          `**💰 Prix :** ${pendingData?.price || "?"}\n` +
          `**💳 Paiement :** ${pendingData?.payment || "?"}\n\n` +
          `━━━━━━━━━━━━━━━━━━━━\n` +
          `👉 Rejoins le serveur : **${VOUCH_SERVER_INVITE}**\n\n` +
          `Et envoie dans **#vouchs** :\n\`\`\`${pendingData?.vouchMsg || "+vouch ..."}\`\`\`\n` +
          `━━━━━━━━━━━━━━━━━━━━\n` +
          `⚠️ Encore **${maxWarns - count} warn(s)** avant le **ban automatique** de tous les serveurs.`
        )
        .setImage(BANNER_URL)
        .setFooter({ text: `Slayzix Shop • Warn ${count}/${maxWarns}` }).setTimestamp();
      await user.send({ embeds: [e] }).catch(() => {});
    }
  } catch (err) {
    console.error(`DM warn impossible pour ${userId}:`, err.message);
  }

  if (count >= maxWarns) {
    await banFromAllServers(userId);
  }
}

async function banFromAllServers(userId) {
  const reason = `[Slayzix Bot] ${WARN_LIMIT} warns — Vouch(s) non effectué(s)`;
  let banned = 0;
  for (const guild of client.guilds.cache.values()) {
    try {
      await guild.members.ban(userId, { reason, deleteMessageSeconds: 0 });
      banned++;
      console.log(chalk.red(`🔨 ${userId} banni de "${guild.name}"`));
    } catch (_) {}
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
//  MESSAGE
// ─────────────────────────────────────────────────────────────────────────────
client.on("messageCreate", async (message) => {
  if (message.author.bot || !message.guild) return;

  // ── Détection vouch dans le salon dédié ────────────────────────────────────
  
  if (message.channel.id === VOUCH_CHANNEL_ID) {
    if (message.content.trim().toLowerCase().startsWith("+vouch")) {
      const uid = message.author.id;
      pendingVouches = loadJSON("./data/pending_vouches.json");
      if (pendingVouches[uid] && !pendingVouches[uid].vouched) {
        pendingVouches[uid].vouched = true;
        saveJSON("./data/pending_vouches.json", pendingVouches);
        console.log(chalk.green(`✅ Vouch détecté et validé pour ${uid}`));
      }
    }
    return; // ne pas traiter les commandes dans le salon vouch
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
    // ── Select type ticket ─────────────────────────────────────────────────
    if (interaction.isStringSelectMenu() && interaction.customId === "ticket_type_select") {
      const type = interaction.values[0];
      if (openTickets[interaction.user.id]) {
        const ex = interaction.guild.channels.cache.get(openTickets[interaction.user.id]);
        if (ex) return interaction.reply({ content: `❌ Tu as déjà un ticket ouvert → ${ex}`, ephemeral: true });
      }
      const row = new ActionRowBuilder().addComponents(
        new StringSelectMenuBuilder().setCustomId("ticket_payment_select").setPlaceholder("Choisis ton moyen de paiement...")
          .addOptions([
            { label: "PayPal", value: `${type}|PayPal`, emoji: "💳" },
            { label: "LTC",    value: `${type}|LTC`,    emoji: "🪙" }
          ])
      );
      return interaction.reply({ embeds: [new EmbedBuilder().setColor(RED).setTitle("💳 Moyen de paiement").setDescription("Sélectionne ton moyen de paiement :")], components: [row], ephemeral: true });
    }

    // ── Select payment ─────────────────────────────────────────────────────
    if (interaction.isStringSelectMenu() && interaction.customId === "ticket_payment_select") {
      const [type, payment] = interaction.values[0].split("|");
      const row = new ActionRowBuilder().addComponents(
        new StringSelectMenuBuilder().setCustomId("ticket_lang_select").setPlaceholder("🌍 Sélectionne ta langue...")
          .addOptions([
            { label: "Français", value: `${type}|${payment}|fr`, emoji: "🇫🇷" },
            { label: "English",  value: `${type}|${payment}|en`, emoji: "🇬🇧" }
          ])
      );
      return interaction.update({ embeds: [new EmbedBuilder().setColor(RED).setTitle("🌍 Langue / Language").setDescription("Sélectionne ta langue / Please select your language.")], components: [row] });
    }

    // ── Select lang → créer ticket ─────────────────────────────────────────
    if (interaction.isStringSelectMenu() && interaction.customId === "ticket_lang_select") {
      await interaction.deferReply({ ephemeral: true });
      const [type, payment, l] = interaction.values[0].split("|");
      await createTicketChannel(interaction, type, payment, l);
      return;
    }

    // ── Boutons ticket ─────────────────────────────────────────────────────
    if (interaction.isButton()) {
      const id = interaction.customId;

      if (id === "ticket_close") {
        await interaction.reply({ content: getLang(interaction.channelId) === "fr" ? "🔒 Fermeture du ticket dans 5 secondes..." : "🔒 Closing ticket in 5 seconds..." });
        logTicket(interaction.guild, "📋 Ticket fermé", `**Salon:** ${interaction.channel.name}\n**Par:** ${interaction.user}`);
        const uid = Object.keys(openTickets).find(u => openTickets[u] === interaction.channel.id);
        if (uid) delete openTickets[uid];
        setTimeout(() => interaction.channel.delete().catch(() => {}), 5000);
        return;
      }

      if (id === "ticket_claim") {
        if (!hasTicketAccess(interaction.member))
          return interaction.reply({ content: "❌ Tu n'as pas la permission de prendre en charge ce ticket.", ephemeral: true });
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
        return interaction.reply({ embeds: [redEmbed(getLang(interaction.channelId) === "fr" ? `✅ Ticket pris en charge par ${interaction.user}\n🔒 Seul le staff et le créateur peuvent écrire.` : `✅ Ticket claimed by ${interaction.user}\n🔒 Only staff and the ticket owner can write.`)] });
      }

      if (id === "ticket_unclaim") {
        if (!hasTicketAccess(interaction.member))
          return interaction.reply({ content: "❌ Tu n'as pas la permission de rendre ce ticket.", ephemeral: true });
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
        return interaction.reply({ embeds: [redEmbed(getLang(interaction.channelId) === "fr" ? `🔄 Ticket rendu par ${interaction.user}\n🔓 Accès restauré.` : `🔄 Ticket unclaimed by ${interaction.user}\n🔓 Access restored.`)] });
      }

      if (id === "ticket_transcript") {
        await interaction.deferReply({ ephemeral: true });
        const msgs = await interaction.channel.messages.fetch({ limit: 200 });
        const lines = [...msgs.values()].filter(m => !m.author.bot)
          .sort((a, b) => a.createdTimestamp - b.createdTimestamp)
          .map(m => `[${new Date(m.createdTimestamp).toLocaleString("fr-FR")}] ${m.author.tag}: ${m.content}`).join("\n");
        if (!lines) return interaction.followUp({ content: "Aucun message.", ephemeral: true });
        return interaction.followUp({ content: "📄 Transcript généré !", files: [new AttachmentBuilder(Buffer.from(lines, "utf8"), { name: `transcript-${interaction.channel.name}.txt` })], ephemeral: true });
      }

      if (id === "ticket_finish") {
        if (!hasTicketAccess(interaction.member))
          return interaction.reply({ content: "❌ Permission refusée.", ephemeral: true });
        const claimerId = ticketClaimers[interaction.channel.id];
        const claimer   = claimerId ? interaction.guild.members.cache.get(claimerId) : null;
        if (!claimer) return interaction.reply({ content: "❌ Aucun staff n'a claim ce ticket !", ephemeral: true });
        return interaction.showModal(buildFinishModal(claimer.id, interaction.channel.id));
      }

      if (id === "ticket_ping") {
        const now = Date.now(), last = pingCooldowns[interaction.channel.id] || 0;
        if (now - last < 900000) {
          const rem = Math.floor((900000 - (now - last)) / 1000);
          return interaction.reply({ content: `⏳ Cooldown ! **${Math.floor(rem/60)}m ${rem%60}s**`, ephemeral: true });
        }
        pingCooldowns[interaction.channel.id] = now;
        const mentions = [];
        const tInfo = ticketData[`chan_${interaction.channel.id}`];
        if (tInfo?.type) { const k = typeRoleKey(tInfo.type); if (k && config.ticket_config?.[k]) mentions.push(`<@&${config.ticket_config[k]}>`); }
        if (config.ticket_config?.support_role) { const sr = `<@&${config.ticket_config.support_role}>`; if (!mentions.includes(sr)) mentions.push(sr); }
        if (mentions.length) await interaction.channel.send({ content: mentions.join(" ") + " — A customer needs help!", allowedMentions: { roles: mentions.map(m => m.slice(3,-1)) } });
        return interaction.reply({ content: "✅ Staff pingé !", ephemeral: true });
      }

      if (id.startsWith("giveaway_")) {
        const gid = id.split("_")[1];
        giveawayData = loadJSON("./data/giveaways.json");
        const g = giveawayData[gid];
        if (!g || g.ended) return interaction.reply({ content: "❌ Ce giveaway est terminé.", ephemeral: true });
        if (!g.participants) g.participants = [];
        const idx = g.participants.indexOf(interaction.user.id);
        if (idx >= 0) { g.participants.splice(idx, 1); } else { g.participants.push(interaction.user.id); }
        saveJSON("./data/giveaways.json", giveawayData);
        return interaction.reply({ content: idx >= 0 ? "❌ Tu t'es retiré du giveaway." : "✅ Tu participes ! 🍀", ephemeral: true });
      }
    }

    // ── Modals ─────────────────────────────────────────────────────────────
    if (interaction.isModalSubmit()) {

      // ── Finish modal ───────────────────────────────────────────────────
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

        // Recap ticket
        const recap = new EmbedBuilder().setColor(RED)
          .setTitle("✅ Transaction terminée — Slayzix Shop")
          .addFields(
            { name: "🛠️ Staff",        value: staffMember ? `${staffMember}` : `<@${staffId}>`, inline: true },
            { name: "📦 Produit",       value: product,  inline: true },
            { name: "💰 Prix",          value: price,    inline: true },
            { name: "💳 Paiement",      value: payment,  inline: true },
            { name: "📋 Message vouch", value: `\`\`\`${vouchMsg}\`\`\``, inline: false }
          )
          .setFooter({ text: "Slayzix Shop • Merci pour votre achat !" }).setTimestamp();
        await interaction.reply({ embeds: [recap] });

        // DM client
        if (owner) {
          try {
            const dm = new EmbedBuilder().setColor(RED)
              .setTitle("✅ Merci pour votre achat — Slayzix Shop !")
              .setDescription(
                `Votre commande a été traitée par ${staffMember ? staffMember.toString() : `<@${staffId}>`} !\n\n` +
                `**📦 Produit :** ${product}\n**💰 Prix :** ${price}\n**💳 Paiement :** ${payment}\n\n` +
                `━━━━━━━━━━━━━━━━━━━━\n` +
                `⭐ **Tu as 1 heure pour laisser ton vouch !**\n\n` +
                `👉 Rejoins le serveur : **${VOUCH_SERVER_INVITE}**\n\n` +
                `Et envoie dans **#vouchs** :\n\`\`\`${vouchMsg}\`\`\`\n` +
                `━━━━━━━━━━━━━━━━━━━━\n` +
                `⚠️ Si tu ne vouchs pas dans **1 heure**, tu recevras un **warn**.\n` +
                `À **3 warns** tu seras **banni automatiquement** de tous les serveurs.`
              )
              .setImage(BANNER_URL)
              .setFooter({ text: "Slayzix Shop • Merci de votre confiance 🤝" }).setTimestamp();
            await owner.send({ embeds: [dm] });
            const chan = interaction.guild.channels.cache.get(chanId);
            if (chan) chan.send({ embeds: [redEmbed(`✅ DM envoyé à ${owner} — Timer vouch 1h démarré ⏱️`)] })
              .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
          } catch {
            const chan = interaction.guild.channels.cache.get(chanId);
            if (chan) chan.send({ embeds: [redEmbed(`⚠️ DMs fermés pour ${owner}.\nMessage vouch : \`${vouchMsg}\``)] })
              .then(m => setTimeout(() => m.delete().catch(() => {}), 15000));
          }
          // Démarrer le timer vouch
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
function typeRoleKey(type) {
  return { "Nitro": "role_nitro", "Server Boost": "role_boost", "Decoration": "role_decoration", "Exchange": "role_exchange", "Other": "role_other" }[type] || null;
}
function getLang(channelId) {
  return ticketData[`chan_${channelId}`]?.lang || "en";
}
function buildFinishModal(staffId, chanId) {
  return new ModalBuilder().setCustomId(`finish_modal_${staffId}_${chanId}`).setTitle("✅ Terminer la transaction")
    .addComponents(
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("product").setLabel("Produit (ex: ×1 Nitro Boost)").setStyle(TextInputStyle.Short).setPlaceholder("×1 Nitro Boost").setMaxLength(100).setRequired(true)),
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("price").setLabel("Prix (ex: 3.20€)").setStyle(TextInputStyle.Short).setPlaceholder("3.20€").setMaxLength(30).setRequired(true)),
      new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("payment").setLabel("Moyen de paiement (ex: PayPal, LTC)").setStyle(TextInputStyle.Short).setPlaceholder("PayPal").setMaxLength(30).setRequired(true))
    );
}
function logTicket(guild, title, desc) {
  const lc = config.ticket_config?.log_channel ? guild.channels.cache.get(String(config.ticket_config.log_channel)) : null;
  if (lc) lc.send({ embeds: [redEmbed(desc, title).setTimestamp()] }).catch(() => {});
}

async function createTicketChannel(interaction, type, payment, l) {
  const guild = interaction.guild, user = interaction.user;
  if (openTickets[user.id]) {
    const ex = guild.channels.cache.get(openTickets[user.id]);
    if (ex) return interaction.followUp({ content: `❌ Tu as déjà un ticket ouvert → ${ex}`, ephemeral: true });
  }
  const tc = config.ticket_config || {};
  let category = tc.category ? guild.channels.cache.get(String(tc.category)) : null;
  if (!category) category = guild.channels.cache.find(c => c.type === 4 && c.name === "TICKETS") || await guild.channels.create({ name: "TICKETS", type: 4 });

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
  const channel = await guild.channels.create({ name: `${type.toLowerCase().replace(/ /g,"-")}-${user.username}`, type: 0, parent: category, permissionOverwrites: overwrites });
  openTickets[user.id] = channel.id;
  ticketData[`chan_${channel.id}`] = { lang: l, type, payment, userId: user.id };
  saveJSON("./data/tickets.json", ticketData);

  const M = { fr: { title:"🎫 Nouveau Ticket", desc:"Le support sera avec vous rapidement.\n\nPour fermer ce ticket, appuyez sur le bouton Fermer.", tip:"🔔 Utilisez Ping Staff si aucune réponse après 15 min", close:"Fermer", claim:"Prendre en charge", unclaim:"Rendre", finish:"Finish", ping:"Ping Staff" }, en: { title:"🎫 New Ticket", desc:"Support will be with you shortly.\n\nTo close this ticket, press the close button below.", tip:"🔔 Use Ping Staff if no response after 15 min", close:"Close", claim:"Claim", unclaim:"Unclaim", finish:"Finish", ping:"Ping Staff" } };
  const m = M[l] || M.en;
  const embed = new EmbedBuilder().setColor(RED).setTitle(m.title).setDescription(m.desc)
    .addFields({ name:"🎫 Type", value:type, inline:true }, { name:"💳 Payment", value:payment, inline:true }, { name:"🌍 Language", value: l==="fr"?"🇫🇷 Français":"🇬🇧 English", inline:true })
    .setFooter({ text: m.tip }).setTimestamp();
  const row1 = new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId("ticket_close").setLabel(m.close).setStyle(ButtonStyle.Secondary).setEmoji("🔒"),
    new ButtonBuilder().setCustomId("ticket_claim").setLabel(m.claim).setStyle(ButtonStyle.Primary),
    new ButtonBuilder().setCustomId("ticket_unclaim").setLabel(m.unclaim).setStyle(ButtonStyle.Secondary),
    new ButtonBuilder().setCustomId("ticket_transcript").setLabel("Transcript").setStyle(ButtonStyle.Secondary).setEmoji("📄")
  );
  const row2 = new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId("ticket_finish").setLabel(m.finish).setStyle(ButtonStyle.Success).setEmoji("✅"),
    new ButtonBuilder().setCustomId("ticket_ping").setLabel(m.ping).setStyle(ButtonStyle.Secondary).setEmoji("🔔")
  );
  let mentions = `${user}`;
  if (tc.support_role) mentions += ` <@&${tc.support_role}>`;
  if (l==="fr" && tc.role_french) mentions += ` <@&${tc.role_french}>`;
  if (l==="en" && tc.role_english) mentions += ` <@&${tc.role_english}>`;
  const tk = typeRoleKey(type); if (tk && tc[tk]) mentions += ` <@&${tc[tk]}>`;
  await channel.send({ content: mentions, embeds: [embed], components: [row1, row2], allowedMentions: { parse: ["users","roles"] } });
  logTicket(guild, "📋 Ticket ouvert", `**User:** ${user}\n**Type:** ${type}\n**Payment:** ${payment}\n**Lang:** ${l}\n**Channel:** ${channel}`);
  await interaction.followUp({ content: `✅ Ticket créé → ${channel}`, ephemeral: true });
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
  g.ended = true; saveJSON("./data/giveaways.json", giveawayData);
  try {
    const channel = await client.channels.fetch(g.channelId);
    const message = await channel.messages.fetch(g.messageId);
    const participants = g.participants || [];
    if (!participants.length) {
      await message.edit({ embeds: [new EmbedBuilder().setColor(RED).setTitle("🎉 GIVEAWAY TERMINÉ").setDescription(`**Prix:** ${g.prize}\n**Organisateur:** <@${g.host}>\n\n😔 Aucun participant !`).setTimestamp()], components: [] });
      await channel.send("😔 Aucun participant, pas de gagnant !");
    } else {
      const winners = participants.sort(() => Math.random() - 0.5).slice(0, Math.min(g.winners, participants.length));
      const wm = winners.map(w => `<@${w}>`).join(" ");
      await message.edit({ embeds: [new EmbedBuilder().setColor(RED).setTitle("🎉 GIVEAWAY TERMINÉ").setDescription(`**Prix:** ${g.prize}\n**Gagnant(s):** ${wm}\n**Organisateur:** <@${g.host}>\n**Participants:** ${participants.length}`).setTimestamp()], components: [] });
      await channel.send(`🎊 Félicitations ${wm} ! Vous avez gagné **${g.prize}** ! Contactez <@${g.host}> pour réclamer.`);
    }
  } catch (err) { console.error("Erreur fin giveaway:", err); }
}
client.endGiveaway = endGiveaway;

client.login(process.env.DISCORD_TOKEN || config.token).catch(err => {
  console.log(chalk.red(`\n❌ Erreur de connexion: ${err.message}`));
  console.log(chalk.yellow("💡 Renseignez votre token dans config.json"));
});
