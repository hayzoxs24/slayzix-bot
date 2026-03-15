const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, ModalBuilder, TextInputBuilder, TextInputStyle } = require("discord.js");

module.exports = {
  name: "ppl",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    const uid = message.author.id;
    const d = ctx.pplData[uid];
    if (!d?.email) {
      return message.channel.send({ embeds: [ctx.redEmbed(`${message.author} utilise \`${ctx.config.prefix}pplsave\` pour enregistrer ton PayPal.`, "❌ Aucun PPL")] })
        .then(m => setTimeout(() => m.delete().catch(() => {}), 10000));
    }
    const btn = new ButtonBuilder().setCustomId("ppl_copy").setLabel("Copier le PayPal").setStyle(ButtonStyle.Secondary).setEmoji("💳");
    const embed = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("💳 Informations PayPal")
      .setAuthor({ name: message.author.displayName, iconURL: message.author.displayAvatarURL() })
      .addFields(
        { name: "📧 Email PayPal",  value: `\`\`\`${d.email}\`\`\``, inline: false },
        { name: "👤 Nom du compte", value: `\`\`\`${d.nom}\`\`\``,   inline: true },
        { name: "🕐 Mis à jour",    value: `\`${d.updated_at || "?"}\``, inline: true }
      )
      .setThumbnail("https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_111x69.jpg")
      .setTimestamp();
    if (d.note) embed.addFields({ name: "📝 Note", value: d.note, inline: false });

    const msg = await message.channel.send({ embeds: [embed], components: [new ActionRowBuilder().addComponents(btn)] });
    const col = msg.createMessageComponentCollector({ time: 60000 });
    col.on("collect", async i => {
      if (i.customId === "ppl_copy") {
        await i.reply({ content: `📋 **PayPal de ${message.author.displayName}:**\n\`\`\`${d.email}\`\`\``, ephemeral: true });
      }
    });
  }
};
