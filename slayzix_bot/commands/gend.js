const { PermissionFlagsBits } = require("discord.js");

module.exports = {
  name: "gend",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.ManageGuild)) return;
    await message.delete().catch(() => {});
    const gid = args[0];
    if (!gid) return message.channel.send({ embeds: [ctx.redEmbed("❌ Usage: `*gend <message_id>`")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    if (!ctx.giveawayData[gid]) return message.channel.send({ embeds: [ctx.redEmbed("❌ Giveaway introuvable.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    await client.endGiveaway(gid);
    message.channel.send({ embeds: [ctx.redEmbed("✅ Giveaway terminé manuellement !")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 5000));
  }
};
