const { PermissionFlagsBits } = require("discord.js");

function hasAccess(member, config) {
  return member.permissions.has(PermissionFlagsBits.Administrator)
    || member.permissions.has(PermissionFlagsBits.ManageMessages)
    || (config.ticket_staff_ids || []).includes(member.id);
}

module.exports = {
  name: "unclaim",
  async execute(message, args, client, ctx) {
    if (!hasAccess(message.member, ctx.config)) return message.channel.send({ embeds: [ctx.redEmbed("❌ Permission refusée.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 5000));
    await message.delete().catch(() => {});

    const ownerUid = Object.keys(ctx.openTickets).find(u => ctx.openTickets[u] === message.channel.id);
    const owner    = ownerUid ? message.guild.members.cache.get(ownerUid) : null;

    if (owner) await message.channel.permissionOverwrites.edit(owner.id, { ViewChannel: true, SendMessages: true, AttachFiles: true }).catch(() => {});

    for (const sid of (ctx.config.ticket_staff_ids || [])) {
      const m = message.guild.members.cache.get(sid);
      if (m) await message.channel.permissionOverwrites.edit(m.id, { ViewChannel: true, SendMessages: true }).catch(() => {});
    }
    if (ctx.config.ticket_config?.support_role)
      await message.channel.permissionOverwrites.edit(ctx.config.ticket_config.support_role, { ViewChannel: true, SendMessages: true }).catch(() => {});

    delete ctx.ticketClaimers[message.channel.id];
    message.channel.send({ embeds: [ctx.redEmbed(`🔄 Ticket rendu par ${message.author}\n🔓 Accès restauré.`)] });
  }
};
