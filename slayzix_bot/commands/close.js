const { PermissionFlagsBits } = require("discord.js");

function hasAccess(member, config) {
  return member.permissions.has(PermissionFlagsBits.Administrator)
    || member.permissions.has(PermissionFlagsBits.ManageMessages)
    || (config.ticket_staff_ids || []).includes(member.id);
}

module.exports = {
  name: "close",
  async execute(message, args, client, ctx) {
    if (!hasAccess(message.member, ctx.config)) return message.channel.send({ embeds: [ctx.redEmbed("❌ Permission refusée.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 5000));
    await message.delete().catch(() => {});
    await message.channel.send({ embeds: [ctx.redEmbed("🔒 Fermeture dans 5 secondes...")] });

    if (ctx.config.ticket_config?.log_channel) {
      const lc = message.guild.channels.cache.get(String(ctx.config.ticket_config.log_channel));
      if (lc) lc.send({ embeds: [ctx.redEmbed(`**Salon:** ${message.channel.name}\n**Par:** ${message.author}`, "📋 Ticket fermé").setTimestamp()] }).catch(() => {});
    }

    const uid = Object.keys(ctx.openTickets).find(u => ctx.openTickets[u] === message.channel.id);
    if (uid) delete ctx.openTickets[uid];

    setTimeout(() => message.channel.delete().catch(() => {}), 5000);
  }
};
