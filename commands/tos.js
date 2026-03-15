const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, PermissionFlagsBits } = require("discord.js");

const TOS = {
  fr: `📋 **Slayzix Shop — CGV**\n\n**1. Remboursement** — Aucun remboursement après paiement.\n**2. Anti-Spam** — Spam = commande annulée sans remboursement.\n**3. Respect** — Comportement toxique = bannissement.\n**4. Délai** — Variable selon le produit. Soyez patient.\n**5. Responsabilité** — Informations incorrectes = votre responsabilité.\n**6. Stock** — Produits temporairement indisponibles possibles.\n**7. Vouchs** — Laissez un vouch après réception.\n**8. Modifications** — CGV modifiables à tout moment.\n\nMerci de faire confiance à **Slayzix Shop** 🤝`,
  en: `📋 **Slayzix Shop — TOS**\n\n**1. No Refund** — All payments are final.\n**2. Spam Policy** — Spamming = order cancelled without refund.\n**3. Respect Staff** — Toxic behavior = ban or cancellation.\n**4. Delivery** — Varies by product. Please be patient.\n**5. Responsibility** — Incorrect info = customer's fault.\n**6. Stock** — Some items may be temporarily unavailable.\n**7. Vouches** — Please leave a vouch after receiving your order.\n**8. TOS Changes** — We reserve the right to modify at any time.\n\nThank you for trusting **Slayzix Shop** 🤝`
};

module.exports = {
  name: "tos",
  TOS, // exporté pour index.js
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId("tos_fr").setLabel("🇫🇷 Français").setStyle(ButtonStyle.Secondary),
      new ButtonBuilder().setCustomId("tos_en").setLabel("🇬🇧 English").setStyle(ButtonStyle.Secondary)
    );
    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("📋 TOS / CGV")
      .setDescription("Choisissez votre langue / Choose your language.")
      .setImage(ctx.BANNER_URL);

    await message.channel.send({ embeds: [e], components: [row] });
  }
};
