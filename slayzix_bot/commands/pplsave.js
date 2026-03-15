const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, ModalBuilder, TextInputBuilder, TextInputStyle } = require("discord.js");

module.exports = {
  name: "pplsave",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    const btn = new ButtonBuilder().setCustomId("open_ppl_modal").setLabel("Sauvegarder mon PayPal").setStyle(ButtonStyle.Success).setEmoji("💳");
    const embed = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("💳 Sauvegarde PayPal")
      .setDescription("Clique pour enregistrer ton adresse PayPal.\n📌 `*ppl` l'affichera.\n🔒 Seul toi peut modifier.")
      .setThumbnail(message.author.displayAvatarURL());

    const msg = await message.channel.send({ embeds: [embed], components: [new ActionRowBuilder().addComponents(btn)] });
    const col = msg.createMessageComponentCollector({ filter: i => i.user.id === message.author.id, time: 60000 });
    col.on("collect", async i => {
      if (i.customId !== "open_ppl_modal") return;
      const modal = new ModalBuilder().setCustomId("ppl_save_modal").setTitle("💳 Sauvegarder mon PayPal")
        .addComponents(
          new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("email").setLabel("Email PayPal").setStyle(TextInputStyle.Short).setPlaceholder("exemple@email.com").setMaxLength(100).setRequired(true)),
          new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("nom").setLabel("Nom du compte").setStyle(TextInputStyle.Short).setPlaceholder("Jean Dupont").setMaxLength(100).setRequired(true)),
          new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId("note").setLabel("Note (optionnel)").setStyle(TextInputStyle.Paragraph).setMaxLength(300).setRequired(false))
        );
      await i.showModal(modal);
    });
  }
};
