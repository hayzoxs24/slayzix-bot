const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "lock",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.ManageChannels)) return;
    await message.delete().catch(() => {});
    await message.channel.permissionOverwrites.edit(message.guild.roles.everyone, { SendMessages: false });
    message.channel.send({ embeds: [ctx.redEmbed("🔒 Salon **verrouillé**.")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
