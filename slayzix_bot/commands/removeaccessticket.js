const { PermissionFlagsBits } = require("discord.js");

module.exports = {
  name: "removeaccessticket",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const member = message.mentions.members.first();
    if (!member) return message.channel.send({ embeds: [ctx.redEmbed("❌ Mentionne un membre.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));

    ctx.config.ticket_staff_ids = ctx.config.ticket_staff_ids.filter(id => id !== member.id);
    ctx.saveJSON("./config.json", ctx.config);

    for (const [, channelId] of Object.entries(ctx.openTickets)) {
      const ch = message.guild.channels.cache.get(channelId);
      if (ch) await ch.permissionOverwrites.delete(member.id).catch(() => {});
    }

    message.channel.send({ embeds: [ctx.redEmbed(`❌ Accès ticket retiré à ${member} (tickets existants inclus).`, "🎫 Accès retiré")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
