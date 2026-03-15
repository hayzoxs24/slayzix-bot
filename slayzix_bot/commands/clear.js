const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "clear",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.ManageMessages)) return;
    await message.delete().catch(() => {});
    const n = Math.min(parseInt(args[0]) || 10, 100);
    const deleted = await message.channel.bulkDelete(n, true);
    message.channel.send({ embeds: [ctx.redEmbed(`🗑️ **${deleted.size}** messages supprimés.`)] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 5000));
  }
};
