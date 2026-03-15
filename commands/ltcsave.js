const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, ModalBuilder, TextInputBuilder, TextInputStyle } = require("discord.js");

module.exports = {
  name: "ltcsave",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    const btn = new ButtonBuilder().setCustomId("open_ltc_modal").setLabel("Sauvegarder mon LTC").setStyle(ButtonStyle.Secondary).setEmoji("🪙");
    const embed = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("🪙 Sauvegarde LTC")
      .setDescription("Clique pour enregistrer ton adresse LTC.\n📌 `*ltc` l'affichera.\n🔒 Seul toi peut modifier.")
      .setThumbnail(message.author.displayAvatarURL());

    const msg = await message.channel.send({ embeds: [embed], components: [new ActionRowBuilder().addComponents(btn)] });
    const col = msg.createMessageComponentCollector({ filter: i => i.user.id === message.author.id, time: 60000 });
    col.on("collect", async i => {
      if (i.customId !== "open_ltc_modal") return;
      const modal = new ModalBuilder().setCustomId("ltc_save_modal").setTitle("🪙 Sauvegarder mon adresse LTC")
        .addComponents(
          new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("address").setLabel("Adresse LTC").setStyle(TextInputStyle.Short).setPlaceholder("LxxxxxxxxxX").setMaxLength(100).setRequired(true)),
          new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("note").setLabel("Note (optionnel)").setStyle(TextInputStyle.Paragraph).setMaxLength(300).setRequired(false))
        );
      await i.showModal(modal);
    });
  }
};
