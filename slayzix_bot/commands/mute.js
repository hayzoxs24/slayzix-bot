const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "mute",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.ModerateMembers)) return;
    await message.delete().catch(() => {});
    const member  = message.mentions.members.first();
    if (!member) return;
    const minutes = parseInt(args[1]) || 10;
    const reason  = args.slice(2).join(" ") || "Aucune raison";
    await member.timeout(minutes * 60 * 1000, reason);
    message.channel.send({ embeds: [ctx.redEmbed(`${member} muté **${minutes} min**.\n**Raison:** ${reason}`, "🔇 Muté")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 10000));
  }
};
