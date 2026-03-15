const { EmbedBuilder, PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "stats",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.ManageGuild)) return;
    await message.delete().catch(() => {});
    const target = message.mentions.members.first() || message.member;
    const roles  = [...target.roles.cache.values()].filter(r => r.name !== "@everyone").reverse().map(r => `${r}`);
    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle(`📊 Stats — ${target.displayName}`)
      .setThumbnail(target.displayAvatarURL())
      .addFields(
        { name: "👤 Compte",  value: `**Nom:** ${target.user.tag}\n**ID:** \`${target.id}\``, inline: true },
        { name: "📅 Dates",   value: `**Créé:** <t:${Math.floor(target.user.createdTimestamp / 1000)}:D>\n**Rejoint:** <t:${Math.floor(target.joinedTimestamp / 1000)}:D>`, inline: true },
        { name: "🏆 Vouchs", value: `\`${ctx.vouchCounts[target.id] || 0}\``, inline: true },
        { name: `🎭 Rôles (${roles.length})`, value: roles.join(" ").slice(0, 1024) || "Aucun", inline: false }
      ).setTimestamp();
    message.channel.send({ embeds: [e] });
  }
};
