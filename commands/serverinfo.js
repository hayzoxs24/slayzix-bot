const { EmbedBuilder } = require("discord.js");
module.exports = {
  name: "serverinfo",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    const g = message.guild;
    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle(`🏠 ${g.name}`)
      .addFields(
        { name: "👑 Owner",    value: `<@${g.ownerId}>`,              inline: true },
        { name: "👥 Membres",  value: `\`${g.memberCount}\``,          inline: true },
        { name: "📅 Créé",     value: `<t:${Math.floor(g.createdTimestamp / 1000)}:D>`, inline: true },
        { name: "💬 Salons",   value: `\`${g.channels.cache.size}\``,  inline: true },
        { name: "🎭 Rôles",    value: `\`${g.roles.cache.size}\``,     inline: true },
        { name: "🚀 Boosts",   value: `\`${g.premiumSubscriptionCount}\``, inline: true }
      )
      .setFooter({ text: `ID: ${g.id}` });
    if (g.iconURL()) e.setThumbnail(g.iconURL());
    message.channel.send({ embeds: [e] });
  }
};
