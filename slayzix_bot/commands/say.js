const { PermissionFlagsBits, ActionRowBuilder, ChannelSelectMenuBuilder, ChannelType, ModalBuilder, TextInputBuilder, TextInputStyle } = require("discord.js");
module.exports = {
  name: "say",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.ManageMessages)) return;
    await message.delete().catch(() => {});

    const row = new ActionRowBuilder().addComponents(
      new ChannelSelectMenuBuilder().setCustomId("say_channel_select").setPlaceholder("Sélectionne le salon cible...").setChannelTypes(ChannelType.GuildText)
    );
    const msg = await message.channel.send({ embeds: [ctx.redEmbed("Sélectionne le salon cible, puis tape ton message.", "📢 Envoyer en tant que bot")], components: [row] });

    const col = msg.createMessageComponentCollector({ filter: i => i.user.id === message.author.id, time: 120000 });
    col.on("collect", async i => {
      if (i.customId !== "say_channel_select") return;
      const targetChannel = message.guild.channels.cache.get(i.values[0]);
      const modal = new ModalBuilder().setCustomId("say_modal").setTitle("📢 Message du bot")
        .addComponents(new ActionRowBuilder().addComponents(
          new TextInputBuilder().setCustomId("content").setLabel("Message").setStyle(TextInputStyle.Paragraph).setMaxLength(2000).setRequired(true)
        ));
      await i.showModal(modal);

      const submitted = await i.awaitModalSubmit({ time: 120000 }).catch(() => null);
      if (!submitted) return;
      const content = submitted.fields.getTextInputValue("content");
      await targetChannel.send(content);
      await submitted.reply({ content: `✅ Envoyé dans ${targetChannel} !`, ephemeral: true });
      msg.delete().catch(() => {});
    });

    setTimeout(() => msg.delete().catch(() => {}), 120000);
  }
};
