const { PermissionFlagsBits } = require("discord.js");
function hasAccess(member, config) {
  return member.permissions.has(PermissionFlagsBits.Administrator)
    || member.permissions.has(PermissionFlagsBits.ManageMessages)
    || (config.ticket_staff_ids || []).includes(member.id);
}
module.exports = {
  name: "rename",
  async execute(message, args, client, ctx) {
    if (!hasAccess(message.member, ctx.config)) return message.channel.send({ embeds: [ctx.redEmbed("❌ Permission refusée.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 5000));
    await message.delete().catch(() => {});
    const name = args.join(" ");
    if (!name) return;
    const old = message.channel.name;
    await message.channel.setName(name);
    message.channel.send({ embeds: [ctx.redEmbed(`✏️ \`${old}\` → \`${name}\``)] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
