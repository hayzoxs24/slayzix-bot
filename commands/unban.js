const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "unban",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.BanMembers)) return;
    await message.delete().catch(() => {});
    const userId = args[0];
    if (!userId) return message.channel.send({ embeds: [ctx.redEmbed("❌ Usage: `*unban <user_id>`")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    try {
      const user = await client.users.fetch(userId);
      await message.guild.members.unban(user);
      message.channel.send({ embeds: [ctx.redEmbed(`✅ **${user.tag}** unban.`)] })
        .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    } catch {
      message.channel.send({ embeds: [ctx.redEmbed("❌ Utilisateur introuvable ou non banni.")] })
        .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    }
  }
};
