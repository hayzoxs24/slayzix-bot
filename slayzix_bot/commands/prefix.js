const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "prefix",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const newPrefix = args[0];
    if (!newPrefix) return message.channel.send({ embeds: [ctx.redEmbed("❌ Usage: `*prefix <nouveau_préfixe>`")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    ctx.config.prefix = newPrefix;
    ctx.saveJSON("./config.json", ctx.config);
    message.channel.send({ embeds: [ctx.redEmbed(`Nouveau préfixe : \`${newPrefix}\``, "⚙️ Préfixe mis à jour")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
