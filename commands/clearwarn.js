const { PermissionFlagsBits } = require("discord.js");

module.exports = {
  name: "clearwarn",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});

    const member = message.mentions.members.first();
    if (!member) return message.channel.send({ embeds: [ctx.redEmbed("❌ Usage: `*clearwarn @membre`")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));

    const uid = member.id;
    if (!ctx.warnData[uid])
      return message.channel.send({ embeds: [ctx.redEmbed(`✅ ${member} n'a aucun warn.`)] })
        .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));

    delete ctx.warnData[uid];
    ctx.saveJSON("./data/warns.json", ctx.warnData);

    message.channel.send({ embeds: [ctx.redEmbed(`✅ Warns de ${member} réinitialisés.`, "🗑️ Warns effacés")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
