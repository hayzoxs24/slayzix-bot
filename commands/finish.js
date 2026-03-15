const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, ModalBuilder, TextInputBuilder, TextInputStyle, PermissionFlagsBits } = require("discord.js");

function hasAccess(member, config) {
  return member.permissions.has(PermissionFlagsBits.Administrator)
    || member.permissions.has(PermissionFlagsBits.ManageMessages)
    || (config.ticket_staff_ids || []).includes(member.id);
}

module.exports = {
  name: "finish",
  async execute(message, args, client, ctx) {
    if (!hasAccess(message.member, ctx.config)) return message.channel.send({ embeds: [ctx.redEmbed("❌ Permission refusée.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 5000));
    await message.delete().catch(() => {});

    const mentioned = message.mentions.members.first();
    const claimerId = ctx.ticketClaimers[message.channel.id];
    const staff = mentioned || (claimerId ? message.guild.members.cache.get(claimerId) : null);

    if (!staff) return message.channel.send({ embeds: [ctx.redEmbed("❌ Personne n'a claim ce ticket. Utilise `*claim` d'abord ou `*finish @staff`")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));

    // Modal pour renseigner le produit et le prix
    const modal = new ModalBuilder()
      .setCustomId(`finish_modal_${staff.id}_${message.channel.id}`)
      .setTitle("✅ Terminer la transaction")
      .addComponents(
        new ActionRowBuilder().addComponents(
          new TextInputBuilder()
            .setCustomId("product")
            .setLabel("Produit (ex: Nitro Boost, Nitro Basic...)")
            .setStyle(TextInputStyle.Short)
            .setPlaceholder("×1 Nitro Boost")
            .setMaxLength(100)
            .setRequired(true)
        ),
        new ActionRowBuilder().addComponents(
          new TextInputBuilder()
            .setCustomId("price")
            .setLabel("Prix (ex: 3.20€)")
            .setStyle(TextInputStyle.Short)
            .setPlaceholder("3.20€")
            .setMaxLength(30)
            .setRequired(true)
        ),
        new ActionRowBuilder().addComponents(
          new TextInputBuilder()
            .setCustomId("payment")
            .setLabel("Moyen de paiement (ex: PayPal, LTC...)")
            .setStyle(TextInputStyle.Short)
            .setPlaceholder("PayPal")
            .setMaxLength(30)
            .setRequired(true)
        )
      );

    // On a besoin d'une interaction pour showModal, donc on envoie un bouton d'abord
    const btn = new ButtonBuilder()
      .setCustomId(`finish_open_${staff.id}`)
      .setLabel("Terminer la transaction")
      .setStyle(ButtonStyle.Success)
      .setEmoji("✅");

    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("✅ Finaliser la transaction")
      .setDescription(`Staff : ${staff}\nClique sur le bouton pour renseigner les détails de la vente.`)
      .setFooter({ text: "Slayzix Shop" }).setTimestamp();

    const msg = await message.channel.send({ embeds: [e], components: [new ActionRowBuilder().addComponents(btn)] });

    const col = msg.createMessageComponentCollector({ filter: i => i.user.id === message.member.id || hasAccess(message.guild.members.cache.get(i.user.id), ctx.config), time: 300000 });

    col.on("collect", async i => {
      if (!i.customId.startsWith("finish_open_")) return;

      const staffId = i.customId.split("_")[2];
      const staffMember = message.guild.members.cache.get(staffId);

      const finishModal = new ModalBuilder()
        .setCustomId(`finish_modal_${staffId}_${message.channel.id}`)
        .setTitle("✅ Terminer la transaction")
        .addComponents(
          new ActionRowBuilder().addComponents(
            new TextInputBuilder()
              .setCustomId("product")
              .setLabel("Produit (ex: Nitro Boost, Nitro Basic...)")
              .setStyle(TextInputStyle.Short)
              .setPlaceholder("×1 Nitro Boost")
              .setMaxLength(100)
              .setRequired(true)
          ),
          new ActionRowBuilder().addComponents(
            new TextInputBuilder()
              .setCustomId("price")
              .setLabel("Prix (ex: 3.20€)")
              .setStyle(TextInputStyle.Short)
              .setPlaceholder("3.20€")
              .setMaxLength(30)
              .setRequired(true)
          ),
          new ActionRowBuilder().addComponents(
            new TextInputBuilder()
              .setCustomId("payment")
              .setLabel("Moyen de paiement (ex: PayPal, LTC...)")
              .setStyle(TextInputStyle.Short)
              .setPlaceholder("PayPal")
              .setMaxLength(30)
              .setRequired(true)
          )
        );

      await i.showModal(finishModal);

      const submitted = await i.awaitModalSubmit({ time: 120000 }).catch(() => null);
      if (!submitted) return;

      const product = submitted.fields.getTextInputValue("product").trim();
      const price   = submitted.fields.getTextInputValue("price").trim();
      const payment = submitted.fields.getTextInputValue("payment").trim();

      // Trouver l'owner du ticket (le client)
      const ownerUid = Object.keys(ctx.openTickets).find(u => ctx.openTickets[u] === message.channel.id);
      const owner = ownerUid ? message.guild.members.cache.get(ownerUid) : null;

      // Message vouch formaté
      const vouchMsg = `+vouch ${staffMember ? staffMember.toString() : `<@${staffId}>`} ${product} | ${price} | ${payment}`;

      // Embed récap dans le ticket
      const recap = new EmbedBuilder().setColor(ctx.RED)
        .setTitle("✅ Transaction terminée — Slayzix Shop")
        .addFields(
          { name: "🛠️ Staff",         value: staffMember ? `${staffMember}` : `<@${staffId}>`, inline: true },
          { name: "📦 Produit",        value: product,   inline: true },
          { name: "💰 Prix",           value: price,     inline: true },
          { name: "💳 Paiement",       value: payment,   inline: true },
          { name: "📋 Message vouch",  value: `\`\`\`${vouchMsg}\`\`\``, inline: false }
        )
        .setFooter({ text: "Slayzix Shop • Merci pour votre achat !" })
        .setTimestamp();

      await submitted.reply({ embeds: [recap] });

      // Supprimer le message avec le bouton
      msg.delete().catch(() => {});

      // Envoyer le DM au client avec le lien + le message vouch
      if (owner) {
        try {
          const dm = new EmbedBuilder().setColor(ctx.RED)
            .setTitle("✅ Merci pour votre achat — Slayzix Shop !")
            .setDescription(
              `Votre commande a bien été traitée par ${staffMember ? staffMember.toString() : `<@${staffId}>`} !\n\n` +
              `**📦 Produit :** ${product}\n` +
              `**💰 Prix :** ${price}\n` +
              `**💳 Paiement :** ${payment}\n\n` +
              `━━━━━━━━━━━━━━━━━━━━\n` +
              `⭐ **Laisse un vouch** sur notre serveur pour soutenir le shop !\n\n` +
              `👉 **Rejoins notre serveur :** https://discord.gg/eyXdtxUDC7\n\n` +
              `Une fois sur le serveur, envoie ce message dans le salon **#vouchs** :\n` +
              `\`\`\`${vouchMsg}\`\`\``
            )
            .setImage(ctx.BANNER_URL)
            .setFooter({ text: "Slayzix Shop • Merci de votre confiance 🤝" })
            .setTimestamp();

          await owner.send({ embeds: [dm] });
          await message.channel.send({ embeds: [ctx.redEmbed(`✅ DM envoyé à ${owner} avec le lien vouch !`)] })
            .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
        } catch {
          await message.channel.send({ embeds: [ctx.redEmbed(`⚠️ Impossible d'envoyer le DM à ${owner} (DMs fermés).\n\nMessage vouch : \`${vouchMsg}\``)] })
            .then(m => setTimeout(() => m.delete().catch(() => {}), 15000));
        }
      }
    });
  }
};
