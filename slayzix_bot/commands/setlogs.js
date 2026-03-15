const { PermissionFlagsBits } = require("discord.js");

module.exports = {
  name: "setlogs",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const channel = message.mentions.channels.first();
    if (!channel) return message.channel.send({ embeds: [ctx.redEmbed("❌ Mentionne un salon : `*setlogs #salon`")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    ctx.config.ticket_config.log_channel = channel.id;
    ctx.saveJSON("./config.json", ctx.config);
    message.channel.send({ embeds: [ctx.redEmbed(`✅ Les logs des tickets seront envoyés dans ${channel}`, "📋 Logs configurés")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
