const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "kick",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.KickMembers)) return;
    await message.delete().catch(() => {});
    const member = message.mentions.members.first();
    if (!member) return;
    const reason = args.slice(1).join(" ") || "Aucune raison";
    await member.kick(reason);
    message.channel.send({ embeds: [ctx.redEmbed(`**${member.user.tag}** kick.\n**Raison:** ${reason}`, "👢 Membre kick")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 10000));
  }
};
