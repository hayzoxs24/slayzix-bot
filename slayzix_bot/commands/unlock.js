const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "unlock",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.ManageChannels)) return;
    await message.delete().catch(() => {});
    await message.channel.permissionOverwrites.edit(message.guild.roles.everyone, { SendMessages: true });
    message.channel.send({ embeds: [ctx.redEmbed("🔓 Salon **déverrouillé**.")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
