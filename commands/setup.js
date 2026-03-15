const {
  EmbedBuilder, ActionRowBuilder, ChannelSelectMenuBuilder,
  RoleSelectMenuBuilder, ButtonBuilder, ButtonStyle,
  StringSelectMenuBuilder, ChannelType, PermissionFlagsBits
} = require("discord.js");

const TICKET_TYPES_OPTIONS = [
  { label: "Nitro",        value: "Nitro",        emoji: "<:Nitro:1480046132707987611>" },
  { label: "Server Boost", value: "Server Boost", emoji: "<:Boost:1480046746146050149>" },
  { label: "Decoration",   value: "Decoration",   emoji: "<:Discord:1480047123188944906>" },
  { label: "Exchange",     value: "Exchange",     emoji: "<:Exchange:1480047481491427492>" },
  { label: "Other",        value: "Other",        emoji: "<:Other:1480047561615085638>" },
];

module.exports = {
  name: "setup",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});

    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("⚙️ Configuration Ticket System")
      .setDescription("**1️⃣** Catégorie tickets\n**2️⃣** Salon des logs\n**3️⃣** Rôle support\nPuis clique sur **📨 Envoyer le panel**");

    const row1 = new ActionRowBuilder().addComponents(
      new ChannelSelectMenuBuilder().setCustomId("setup_category").setPlaceholder("📁 Catégorie tickets").setChannelTypes(ChannelType.GuildCategory)
    );
    const row2 = new ActionRowBuilder().addComponents(
      new ChannelSelectMenuBuilder().setCustomId("setup_logs").setPlaceholder("📋 Salon des logs").setChannelTypes(ChannelType.GuildText)
    );
    const row3 = new ActionRowBuilder().addComponents(
      new RoleSelectMenuBuilder().setCustomId("setup_role").setPlaceholder("👮 Rôle support")
    );
    const row4 = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId("setup_send_panel").setLabel("📨 Envoyer le panel ici").setStyle(ButtonStyle.Success)
    );

    const msg = await message.channel.send({ embeds: [e], components: [row1, row2, row3, row4] });

    const col = msg.createMessageComponentCollector({
      filter: i => i.user.id === message.author.id,
      time: 300000
    });

    col.on("collect", async i => {
      if (i.customId === "setup_category") {
        ctx.config.ticket_config.category = i.values[0];
        ctx.saveJSON("./config.json", ctx.config);
        return i.reply({ content: "✅ Catégorie OK", ephemeral: true });
      }
      if (i.customId === "setup_logs") {
        ctx.config.ticket_config.log_channel = i.values[0];
        ctx.saveJSON("./config.json", ctx.config);
        return i.reply({ content: "✅ Logs OK", ephemeral: true });
      }
      if (i.customId === "setup_role") {
        ctx.config.ticket_config.support_role = i.values[0];
        ctx.saveJSON("./config.json", ctx.config);
        return i.reply({ content: "✅ Rôle support OK", ephemeral: true });
      }
      if (i.customId === "setup_send_panel") {
        const panelEmbed = new EmbedBuilder().setColor(ctx.RED)
          .setTitle("<:Nitroo:1480046413441273968> Support Ticket System")
          .setDescription("Select a category below to create a support ticket.\n\nOur team will assist you as soon as possible.")
          .setImage(ctx.BANNER_URL)
          .setFooter({ text: "Please provide detailed information in your ticket" });

        const select = new StringSelectMenuBuilder()
          .setCustomId("ticket_type_select")
          .setPlaceholder("Select a category...")
          .addOptions(TICKET_TYPES_OPTIONS);

        await i.channel.send({
          embeds: [panelEmbed],
          components: [new ActionRowBuilder().addComponents(select)]
        });
        return i.reply({ content: "✅ Panel envoyé !", ephemeral: true });
      }
    });

    col.on("end", () => msg.edit({ components: [] }).catch(() => {}));
  }
};
