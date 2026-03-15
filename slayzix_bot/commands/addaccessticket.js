const { PermissionFlagsBits } = require("discord.js");

module.exports = {
  name: "addaccessticket",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const member = message.mentions.members.first();
    if (!member) return message.channel.send({ embeds: [ctx.redEmbed("❌ Mentionne un membre.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));

    if (!ctx.config.ticket_staff_ids.includes(member.id)) ctx.config.ticket_staff_ids.push(member.id);
    ctx.saveJSON("./config.json", ctx.config);

    let updated = 0;
    for (const [, channelId] of Object.entries(ctx.openTickets)) {
      const ch = message.guild.channels.cache.get(channelId);
      if (ch) { await ch.permissionOverwrites.edit(member.id, { ViewChannel: true, SendMessages: true }).catch(() => {}); updated++; }
    }

    const desc = `✅ ${member} peut maintenant utiliser \`*claim\`, \`*unclaim\`, \`*close\`, \`*finish\`, \`*add\`, \`*remove\`, \`*rename\`, \`*slowmode\`.\n📂 Accès ajouté à **${updated}** ticket(s) existant(s).`;
    message.channel.send({ embeds: [ctx.redEmbed(desc, "🎫 Accès ticket accordé")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 12000));
  }
};
