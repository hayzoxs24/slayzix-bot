const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require("discord.js");

module.exports = {
  name: "ltc",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    const d = ctx.ltcData[message.author.id];
    if (!d?.address)
      return message.channel.send({ embeds: [ctx.redEmbed(`${message.author} utilise \`${ctx.config.prefix}ltcsave\`.`, "❌ Aucun LTC")] })
        .then(m => setTimeout(() => m.delete().catch(() => {}), 10000));

    const btn = new ButtonBuilder().setCustomId("ltc_copy").setLabel("Copier l'adresse LTC").setStyle(ButtonStyle.Secondary).setEmoji("🪙");
    const embed = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("🪙 Adresse LTC")
      .setAuthor({ name: message.author.displayName, iconURL: message.author.displayAvatarURL() })
      .addFields(
        { name: "🪙 Adresse",    value: `\`\`\`${d.address}\`\`\``, inline: false },
        { name: "🕐 Mis à jour", value: `\`${d.updated_at || "?"}\``, inline: true }
      ).setTimestamp();
    if (d.note) embed.addFields({ name: "📝 Note", value: d.note, inline: false });

    const msg = await message.channel.send({ embeds: [embed], components: [new ActionRowBuilder().addComponents(btn)] });
    const col = msg.createMessageComponentCollector({ time: 60000 });
    col.on("collect", async i => {
      if (i.customId === "ltc_copy")
        await i.reply({ content: `📋 **LTC de ${message.author.displayName}:**\n\`\`\`${d.address}\`\`\``, ephemeral: true });
    });
  }
};
