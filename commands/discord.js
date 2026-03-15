const { EmbedBuilder } = require("discord.js");

module.exports = {
  name: "discord",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("💬 Slayzix Shop — Discord")
      .setDescription(
        `👉 **https://discord.gg/8sUvMRJX3B**\n\n` +
        `📌 C'est sur ce serveur que tu dois laisser ton **vouch** après chaque achat.\n\n` +
        `⚠️ Tout vouch non effectué dans **1h** = **warn automatique**\n` +
        `🔨 **3 warns = ban permanent** de tous les serveurs.`
      )
      .setImage(ctx.BANNER_URL)
      .setTimestamp();
    message.channel.send({ embeds: [e] });
  }
};
