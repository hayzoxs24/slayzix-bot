const { PermissionFlagsBits } = require("discord.js");

module.exports = {
  name: "listaccessticket",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const ids = ctx.config.ticket_staff_ids || [];
    if (!ids.length)
      return message.channel.send({ embeds: [ctx.redEmbed("Aucun membre ajouté via `*addaccessticket`.", "🎫 Accès ticket")] })
        .then(m => setTimeout(() => m.delete().catch(() => {}), 10000));

    const list = ids.map(id => {
      const m = message.guild.members.cache.get(id);
      return m ? `${m}` : `\`${id}\``;
    });
    message.channel.send({ embeds: [ctx.redEmbed(list.join("\n"), `🎫 Staff ticket (${list.length})`)] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 15000));
  }
};
