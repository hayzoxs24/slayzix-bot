const { EmbedBuilder, ActionRowBuilder, ChannelSelectMenuBuilder, RoleSelectMenuBuilder, ButtonBuilder, ButtonStyle, ChannelType } = require("discord.js");

module.exports = {
  name: "setup",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(0x8n)) return;
    await message.delete().catch(() => {});

    const e = new EmbedBuilder().setColor(0xFF0000)
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

    const collector = msg.createMessageComponentCollector({ time: 300000 });
    collector.on("collect", async i => {
      if (i.user.id !== message.author.id) return i.reply({ content: "❌ Pas pour toi.", ephemeral: true });

      if (i.customId === "setup_category") {
        ctx.config.ticket_config.category = i.values[0];
        const { saveJSON } = ctx; saveJSON("./config.json", ctx.config);
        return i.reply({ content: "✅ Catégorie OK", ephemeral: true });
      }
      if (i.customId === "setup_logs") {
        ctx.config.ticket_config.log_channel = i.values[0];
        const { saveJSON } = ctx; saveJSON("./config.json", ctx.config);
        return i.reply({ content: "✅ Logs OK", ephemeral: true });
      }
      if (i.customId === "setup_role") {
        ctx.config.ticket_config.support_role = i.values[0];
        const { saveJSON } = ctx; saveJSON("./config.json", ctx.config);
        return i.reply({ content: "✅ Rôle support OK", ephemeral: true });
      }
      if (i.customId === "setup_send_panel") {
        const { EmbedBuilder: EB, ActionRowBuilder: AR, StringSelectMenuBuilder: SSM } = require("discord.js");
        const panelEmbed = new EB().setColor(0xFF0000)
          .setTitle("🎫 Support Ticket System")
          .setDescription("Sélectionne une catégorie ci-dessous pour créer un ticket.\n\nNotre équipe vous assistera dès que possible.")
          .setImage(ctx.BANNER_URL)
          .setFooter({ text: "Fournissez des informations détaillées dans votre ticket" });

        const select = new SSM().setCustomId("ticket_type_select").setPlaceholder("Sélectionne une catégorie...")
          .addOptions([
            { label: "Nitro",        value: "Nitro",        emoji: "💎" },
            { label: "Server Boost", value: "Server Boost", emoji: "🚀" },
            { label: "Decoration",   value: "Decoration",   emoji: "🎨" },
            { label: "Exchange",     value: "Exchange",     emoji: "🔄" },
            { label: "Other",        value: "Other",        emoji: "📦" }
          ]);

        await i.channel.send({ embeds: [panelEmbed], components: [new AR().addComponents(select)] });
        return i.reply({ content: "✅ Panel envoyé !", ephemeral: true });
      }
    });
  }
};
