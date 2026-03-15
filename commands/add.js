const { PermissionFlagsBits } = require("discord.js");
function hasAccess(member, config) {
  return member.permissions.has(PermissionFlagsBits.Administrator)
    || member.permissions.has(PermissionFlagsBits.ManageMessages)
    || (config.ticket_staff_ids || []).includes(member.id);
}
module.exports = {
  name: "add",
  async execute(message, args, client, ctx) {
    if (!hasAccess(message.member, ctx.config)) return message.channel.send({ embeds: [ctx.redEmbed("❌ Permission refusée.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 5000));
    await message.delete().catch(() => {});
    const member = message.mentions.members.first();
    if (!member) return;
    await message.channel.permissionOverwrites.edit(member.id, { ViewChannel: true, SendMessages: true });
    message.channel.send({ embeds: [ctx.redEmbed(`✅ ${member} ajouté.`)] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
