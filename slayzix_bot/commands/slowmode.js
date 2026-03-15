const { PermissionFlagsBits } = require("discord.js");
function hasAccess(member, config) {
  return member.permissions.has(PermissionFlagsBits.Administrator)
    || member.permissions.has(PermissionFlagsBits.ManageMessages)
    || (config.ticket_staff_ids || []).includes(member.id);
}
module.exports = {
  name: "slowmode",
  async execute(message, args, client, ctx) {
    if (!hasAccess(message.member, ctx.config)) return message.channel.send({ embeds: [ctx.redEmbed("❌ Permission refusée.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 5000));
    await message.delete().catch(() => {});
    const seconds = parseInt(args[0]) || 0;
    await message.channel.setRateLimitPerUser(seconds);
    message.channel.send({ embeds: [ctx.redEmbed(`⏱️ Slowmode ${seconds === 0 ? "désactivé" : `**${seconds}s**`}.`)] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
