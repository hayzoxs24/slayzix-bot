const { EmbedBuilder, ActionRowBuilder, StringSelectMenuBuilder, ButtonBuilder, ButtonStyle, PermissionFlagsBits, ModalBuilder, TextInputBuilder, TextInputStyle } = require("discord.js");

module.exports = {
  name: "shopembed",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});

    let embed = new EmbedBuilder().setColor(ctx.RED).setTitle("Titre ici").setDescription("Description ici").setFooter({ text: "Footer ici" });
    const history = [embed.toJSON()];
    let histIdx = 0;

    const selectRow = new ActionRowBuilder().addComponents(
      new StringSelectMenuBuilder().setCustomId("shopembed_select").setPlaceholder("Choisir un champ à modifier...")
        .addOptions([
          { label: "Titre",              value: "title" },
          { label: "Description",        value: "description" },
          { label: "Auteur",             value: "author" },
          { label: "Footer",             value: "footer" },
          { label: "Image",              value: "image" },
          { label: "Thumbnail",          value: "thumbnail" },
          { label: "Couleur",            value: "color" },
          { label: "Ajouter un Field",   value: "add_field" },
          { label: "Supprimer un Field", value: "remove_field" },
          { label: "Timestamp",          value: "timestamp" }
        ])
    );
    const btnRow = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId("shopembed_undo")     .setLabel("↩️ Défaire")    .setStyle(ButtonStyle.Secondary),
      new ButtonBuilder().setCustomId("shopembed_redo")     .setLabel("↪️ Refaire")    .setStyle(ButtonStyle.Secondary),
      new ButtonBuilder().setCustomId("shopembed_validate") .setLabel("✅ Valider")    .setStyle(ButtonStyle.Success),
      new ButtonBuilder().setCustomId("shopembed_delete")   .setLabel("🗑️ Supprimer") .setStyle(ButtonStyle.Danger)
    );

    const msg = await message.channel.send({ embeds: [embed], components: [selectRow, btnRow] });

    const col = msg.createMessageComponentCollector({ filter: i => i.user.id === message.author.id, time: 600000 });

    col.on("collect", async i => {
      // Undo
      if (i.customId === "shopembed_undo") {
        await i.deferUpdate();
        if (histIdx > 0) { histIdx--; embed = EmbedBuilder.from(history[histIdx]); await msg.edit({ embeds: [embed] }); }
        return;
      }
      // Redo
      if (i.customId === "shopembed_redo") {
        await i.deferUpdate();
        if (histIdx < history.length - 1) { histIdx++; embed = EmbedBuilder.from(history[histIdx]); await msg.edit({ embeds: [embed] }); }
        return;
      }
      // Delete
      if (i.customId === "shopembed_delete") {
        await i.deferUpdate();
        return msg.delete().catch(() => {});
      }
      // Validate → send to channel
      if (i.customId === "shopembed_validate") {
        const modal = new ModalBuilder().setCustomId("shopembed_send_modal").setTitle("Envoyer l'embed")
          .addComponents(new ActionRowBuilder().addComponents(
            new TextInputBuilder().setCustomId("channel_id").setLabel("ID ou #salon").setStyle(TextInputStyle.Short).setRequired(true)
          ));
        await i.showModal(modal);
        const sub = await i.awaitModalSubmit({ time: 60000 }).catch(() => null);
        if (!sub) return;
        const raw = sub.fields.getTextInputValue("channel_id").replace(/[<#>]/g, "");
        const target = message.guild.channels.cache.get(raw);
        if (!target) return sub.reply({ content: "❌ Salon introuvable.", ephemeral: true });
        await target.send({ embeds: [embed] });
        return sub.reply({ content: `✅ Embed envoyé dans ${target} !`, ephemeral: true });
      }
      // Select field
      if (i.customId === "shopembed_select") {
        const field = i.values[0];
        if (field === "timestamp") {
          await i.deferUpdate();
          embed.setTimestamp();
          history.splice(histIdx + 1); history.push(embed.toJSON()); histIdx++;
          return msg.edit({ embeds: [embed] });
        }
        const labels = { title: "Titre", description: "Description", author: "Auteur", footer: "Footer", image: "URL image principale", thumbnail: "URL thumbnail", color: "Couleur hex (ex: #ff0000)", add_field: "Nom du field", remove_field: "Numéro du field (commence à 1)" };
        const modal = new ModalBuilder().setCustomId(`shopembed_field_${field}`).setTitle(`Modifier: ${labels[field] || field}`)
          .addComponents(new ActionRowBuilder().addComponents(
            new TextInputBuilder().setCustomId("value").setLabel(labels[field] || "Valeur").setStyle(field === "description" ? TextInputStyle.Paragraph : TextInputStyle.Short).setRequired(true)
          ));
        await i.showModal(modal);
        const sub = await i.awaitModalSubmit({ time: 120000 }).catch(() => null);
        if (!sub) return;
        const val = sub.fields.getTextInputValue("value").trim();
        try {
          if (field === "title")         embed.setTitle(val);
          else if (field === "description") embed.setDescription(val);
          else if (field === "author")   embed.setAuthor({ name: val });
          else if (field === "footer")   embed.setFooter({ text: val });
          else if (field === "image")    embed.setImage(val);
          else if (field === "thumbnail") embed.setThumbnail(val);
          else if (field === "color")    embed.setColor(parseInt(val.replace("#", ""), 16));
          else if (field === "add_field") embed.addFields({ name: val, value: "Valeur", inline: false });
          else if (field === "remove_field") embed.spliceFields(parseInt(val) - 1, 1);
        } catch { return sub.reply({ content: "❌ Valeur invalide.", ephemeral: true }); }
        history.splice(histIdx + 1); history.push(embed.toJSON()); histIdx++;
        await msg.edit({ embeds: [embed] });
        return sub.reply({ content: "✅ Mis à jour !", ephemeral: true });
      }
    });

    col.on("end", () => msg.edit({ components: [] }).catch(() => {}));
  }
};
