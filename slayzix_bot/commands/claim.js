const { PermissionFlagsBits } = require("discord.js");

function hasAccess(member, config) {
  return member.permissions.has(PermissionFlagsBits.Administrator)
    || member.permissions.has(PermissionFlagsBits.ManageMessages)
    || (config.ticket_staff_ids || []).includes(member.id);
}

module.exports = {
  name: "claim",
  async execute(message, args, client, ctx) {
    if (!hasAccess(message.member, ctx.config)) return message.channel.send({ embeds: [ctx.redEmbed("❌ Permission refusée.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 5000));
    await message.delete().catch(() => {});

    const ownerUid = Object.keys(ctx.openTickets).find(u => ctx.openTickets[u] === message.channel.id);
    const owner    = ownerUid ? message.guild.members.cache.get(ownerUid) : null;

    for (const [id, ow] of message.channel.permissionOverwrites.cache) {
      const t = message.guild.members.cache.get(id) || message.guild.roles.cache.get(id);
      if (!t) continue;
      if (t.id === message.member.id || t.id === message.guild.members.me.id) continue;
      if (t.permissions?.has?.(PermissionFlagsBits.Administrator)) continue;
      if (owner && t.id === owner.id) continue;
      await message.channel.permissionOverwrites.edit(id, { SendMessages: false }).catch(() => {});
    }
    await message.channel.permissionOverwrites.edit(message.member.id, { ViewChannel: true, SendMessages: true, AttachFiles: true });
    if (owner) await message.channel.permissionOverwrites.edit(owner.id, { ViewChannel: true, SendMessages: true, AttachFiles: true });

    ctx.ticketClaimers[message.channel.id] = message.member.id;
    message.channel.send({ embeds: [ctx.redEmbed(`✅ Ticket pris en charge par ${message.author}\n🔒 Seul le staff et le créateur peuvent écrire.`)] });
  }
};
