const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "setboost",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const role = message.mentions.roles.first();
    if (!role) return message.channel.send({ embeds: [ctx.redEmbed("❌ Mentionne un rôle : `*setboost @role`")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    ctx.config.ticket_config.role_boost = role.id;
    ctx.saveJSON("./config.json", ctx.config);
    message.channel.send({ embeds: [ctx.redEmbed(`**Server Boost** → ${role}`, "✅ Rôle configuré")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
