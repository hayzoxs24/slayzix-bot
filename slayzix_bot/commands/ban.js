const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "ban",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.BanMembers)) return;
    await message.delete().catch(() => {});
    const member = message.mentions.members.first();
    if (!member) return;
    const reason = args.slice(1).join(" ") || "Aucune raison";
    await member.ban({ reason });
    message.channel.send({ embeds: [ctx.redEmbed(`**${member.user.tag}** banni.\n**Raison:** ${reason}`, "🔨 Membre banni")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 10000));
  }
};
