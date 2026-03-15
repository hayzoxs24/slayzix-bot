const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "setdeco",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const role = message.mentions.roles.first();
    if (!role) return message.channel.send({ embeds: [ctx.redEmbed("❌ Mentionne un rôle : `*setdeco @role`")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    ctx.config.ticket_config.role_decoration = role.id;
    ctx.saveJSON("./config.json", ctx.config);
    message.channel.send({ embeds: [ctx.redEmbed(`**Decoration** → ${role}`, "✅ Rôle configuré")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
