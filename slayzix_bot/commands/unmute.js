const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "unmute",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.ModerateMembers)) return;
    await message.delete().catch(() => {});
    const member = message.mentions.members.first();
    if (!member) return;
    await member.timeout(null);
    message.channel.send({ embeds: [ctx.redEmbed(`🔊 ${member} unmute.`)] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
