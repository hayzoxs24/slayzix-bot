const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "protectlog",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const channel = message.mentions.channels.first();
    if (!channel) return message.channel.send({ embeds: [ctx.redEmbed("❌ Mentionne un salon.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    ctx.config.protection.log_channel = channel.id;
    ctx.saveJSON("./config.json", ctx.config);
    message.channel.send({ embeds: [ctx.redEmbed(`✅ Logs protection → ${channel}`)] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
