const {
  PermissionFlagsBits, EmbedBuilder, ActionRowBuilder,
  ChannelSelectMenuBuilder, RoleSelectMenuBuilder, ButtonBuilder,
  ButtonStyle, StringSelectMenuBuilder, ChannelType,
  ButtonBuilder: BB
} = require("discord.js");

// ── Constantes ticket (reprises du code Python original) ──────────────────────
const TICKET_TYPES = [
  { label: "Nitro",        emoji: "<:Nitro:1480046132707987611>",    value: "Nitro" },
  { label: "Server Boost", emoji: "<:Boost:1480046746146050149>",    value: "Server Boost" },
  { label: "Decoration",   emoji: "<:Discord:1480047123188944906>",  value: "Decoration" },
  { label: "Exchange",     emoji: "<:Exchange:1480047481491427492>", value: "Exchange" },
  { label: "Other",        emoji: "<:Other:1480047561615085638>",    value: "Other" },
];
const PAYMENT_OPTIONS = [
  { label: "PayPal", emoji: "<:PPL:1480046672162852985>",  value: "PayPal" },
  { label: "LTC",    emoji: "<:LTC:1480634361555452176>",  value: "LTC" },
];
const TYPE_ROLE_MAP = {
  "Nitro":        "role_nitro",
  "Server Boost": "role_boost",
  "Decoration":   "role_decoration",
  "Exchange":     "role_exchange",
  "Other":        "role_other"
};

// Langue par défaut : anglais
const MSG = {
  ticket_title:   "<:Nitroo:1480046413441273968> New Ticket",
  ticket_desc:    "Support will be with you shortly.\n\nTo close this ticket, press the close button below.",
  ping_staff_tip: "🔔 Use **Ping Staff** if no response after 15 min (15 min cooldown)",
  close:          "Close",
  claim:          "Claim",
  unclaim:        "Unclaim",
  transcript:     "Transcript",
  finish:         "Finish",
  ping_staff:     "Ping Staff",
  closing:        "🔒 Closing ticket in 5 seconds...",
  already_open:   "❌ You already have an open ticket →",
  created:        "✅ Ticket created →",
};

module.exports = {
  name: "setup",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});

    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("⚙️ Configuration Ticket System")
      .setDescription("**1️⃣** Catégorie **2️⃣** Logs **3️⃣** Rôle support\nPuis clique sur **📨 Envoyer le panel**");

    const row1 = new ActionRowBuilder().addComponents(
      new ChannelSelectMenuBuilder()
        .setCustomId("setup_category")
        .setPlaceholder("📁 Catégorie tickets")
        .setChannelTypes(ChannelType.GuildCategory)
    );
    const row2 = new ActionRowBuilder().addComponents(
      new ChannelSelectMenuBuilder()
        .setCustomId("setup_logs")
        .setPlaceholder("📋 Salon des logs")
        .setChannelTypes(ChannelType.GuildText)
    );
    const row3 = new ActionRowBuilder().addComponents(
      new RoleSelectMenuBuilder()
        .setCustomId("setup_role")
        .setPlaceholder("👮 Rôle support")
    );
    const row4 = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId("setup_send_panel")
        .setLabel("📨 Envoyer le panel ici")
        .setStyle(ButtonStyle.Success)
    );

    const msg = await message.channel.send({ embeds: [e], components: [row1, row2, row3, row4] });

    const col = msg.createMessageComponentCollector({
      filter: i => i.user.id === message.author.id,
      time: 300000
    });

    col.on("collect", async i => {
      // ── Catégorie ──────────────────────────────────────────────────────────
      if (i.customId === "setup_category") {
        ctx.config.ticket_config.category = i.values[0];
        ctx.saveJSON("./config.json", ctx.config);
        return i.reply({ content: "✅ Catégorie OK", ephemeral: true });
      }

      // ── Logs ───────────────────────────────────────────────────────────────
      if (i.customId === "setup_logs") {
        ctx.config.ticket_config.log_channel = i.values[0];
        ctx.saveJSON("./config.json", ctx.config);
        return i.reply({ content: "✅ Log OK", ephemeral: true });
      }

      // ── Rôle support ───────────────────────────────────────────────────────
      if (i.customId === "setup_role") {
        ctx.config.ticket_config.support_role = i.values[0];
        ctx.saveJSON("./config.json", ctx.config);
        return i.reply({ content: "✅ Rôle OK", ephemeral: true });
      }

      // ── Envoyer le panel ───────────────────────────────────────────────────
      if (i.customId === "setup_send_panel") {
        const panelEmbed = new EmbedBuilder().setColor(ctx.RED)
          .setTitle("<:Nitroo:1480046413441273968> Support Ticket System")
          .setDescription("Select a category below to create a support ticket.\n\nOur team will assist you as soon as possible.")
          .setImage(ctx.BANNER_URL)
          .setFooter({ text: "Please provide detailed information in your ticket" });

        const typeSelect = new StringSelectMenuBuilder()
          .setCustomId("ticket_type_select")
          .setPlaceholder("Select a category...")
          .addOptions(TICKET_TYPES.map(t => ({ label: t.label, value: t.value, emoji: t.emoji })));

        await i.channel.send({
          embeds: [panelEmbed],
          components: [new ActionRowBuilder().addComponents(typeSelect)]
        });
        return i.reply({ content: "✅ Panel envoyé !", ephemeral: true });
      }
    });

    col.on("end", () => msg.edit({ components: [] }).catch(() => {}));
  },

  // ── Exporté pour être utilisé dans index.js lors des interactions ──────────
  TICKET_TYPES,
  PAYMENT_OPTIONS,
  TYPE_ROLE_MAP,
  MSG,

  // Crée le salon ticket (appelé depuis index.js)
  async createTicketChannel(interaction, type, payment, openTickets, ticketData, config, saveJSON, redEmbed, BANNER_URL, RED) {
    const guild = interaction.guild;
    const user  = interaction.user;

    if (openTickets[user.id]) {
      const ex = guild.channels.cache.get(openTickets[user.id]);
      if (ex) return interaction.followUp({ content: `${MSG.already_open} ${ex}`, ephemeral: true });
    }

    const tc = config.ticket_config || {};

    // Catégorie
    let category = tc.category ? guild.channels.cache.get(String(tc.category)) : null;
    if (!category) {
      category = guild.channels.cache.find(c => c.type === 4 && c.name === "TICKETS")
        || await guild.channels.create({ name: "TICKETS", type: 4 });
    }

    // Permissions
    const overwrites = [
      { id: guild.roles.everyone.id, deny: [PermissionFlagsBits.ViewChannel] },
      { id: user.id,                 allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.AttachFiles] },
      { id: guild.members.me.id,     allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages, PermissionFlagsBits.ManageChannels] }
    ];
    if (tc.support_role)
      overwrites.push({ id: String(tc.support_role), allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] });
    for (const sid of (config.ticket_staff_ids || [])) {
      const m = guild.members.cache.get(String(sid));
      if (m) overwrites.push({ id: m.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] });
    }

    const channel = await guild.channels.create({
      name: `${type.toLowerCase().replace(/ /g, "-")}-${user.username}`,
      type: 0,
      parent: category,
      permissionOverwrites: overwrites
    });

    openTickets[user.id] = channel.id;
    ticketData[`chan_${channel.id}`] = { type, payment, userId: user.id };
    saveJSON("./data/tickets.json", ticketData);

    // Embed dans le ticket
    const embed = new EmbedBuilder().setColor(RED)
      .setTitle(MSG.ticket_title)
      .setDescription(MSG.ticket_desc)
      .addFields(
        { name: "<:Nitroo:1480046413441273968> Type",        value: type,    inline: true },
        { name: "<:Paiement:1480046846658351276> Payment",   value: payment, inline: true },
        { name: "🌍 Language",                               value: "🇬🇧 English", inline: true }
      )
      .setFooter({ text: MSG.ping_staff_tip })
      .setTimestamp();

    // Boutons (repris exactement du Python original)
    const row1 = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId("ticket_close")     .setLabel(MSG.close)      .setStyle(ButtonStyle.Secondary).setEmoji("<:Other:1480047561615085638>"),
      new ButtonBuilder().setCustomId("ticket_claim")     .setLabel(MSG.claim)      .setStyle(ButtonStyle.Secondary).setEmoji("<:Boost:1480046746146050149>"),
      new ButtonBuilder().setCustomId("ticket_unclaim")   .setLabel(MSG.unclaim)    .setStyle(ButtonStyle.Secondary).setEmoji("<:Exchange:1480047481491427492>"),
      new ButtonBuilder().setCustomId("ticket_transcript").setLabel(MSG.transcript) .setStyle(ButtonStyle.Secondary).setEmoji("<:Transcript:1480047021707759727>")
    );
    const row2 = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId("ticket_finish")    .setLabel(MSG.finish)     .setStyle(ButtonStyle.Secondary).setEmoji("<:oui:1480176155989508348>"),
      new ButtonBuilder().setCustomId("ticket_ping")      .setLabel(MSG.ping_staff) .setStyle(ButtonStyle.Secondary).setEmoji("<:Discord:1480047123188944906>")
    );

    // Mentions
    let mentions = `${user}`;
    if (tc.support_role) mentions += ` <@&${tc.support_role}>`;
    if (tc.role_english) mentions += ` <@&${tc.role_english}>`;
    const typeKey = TYPE_ROLE_MAP[type];
    if (typeKey && tc[typeKey]) mentions += ` <@&${tc[typeKey]}>`;

    await channel.send({
      content: mentions,
      embeds: [embed],
      components: [row1, row2],
      allowedMentions: { parse: ["users", "roles"] }
    });

    // Log
    if (tc.log_channel) {
      const lc = guild.channels.cache.get(String(tc.log_channel));
      if (lc) {
        const le = new EmbedBuilder().setColor(RED)
          .setTitle("📋 Ticket ouvert")
          .setDescription(`**User:** ${user}\n**Type:** ${type}\n**Payment:** ${payment}\n**Channel:** ${channel}`)
          .setTimestamp();
        lc.send({ embeds: [le] }).catch(() => {});
      }
    }

    await interaction.followUp({ content: `${MSG.created} ${channel}`, ephemeral: true });
  }
};
