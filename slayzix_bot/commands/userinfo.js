const { EmbedBuilder } = require("discord.js");
module.exports = {
  name: "userinfo",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    const target = message.mentions.members.first() || message.member;
    const roles  = [...target.roles.cache.values()].filter(r => r.name !== "@everyone").reverse().slice(0, 10).map(r => `${r}`);
    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle(`👤 ${target.displayName}`)
      .setThumbnail(target.displayAvatarURL())
      .addFields(
        { name: "ID",       value: `\`${target.id}\``, inline: true },
        { name: "Créé",     value: `<t:${Math.floor(target.user.createdTimestamp / 1000)}:D>`, inline: true },
        { name: "Rejoint",  value: `<t:${Math.floor(target.joinedTimestamp / 1000)}:D>`, inline: true },
        { name: `Rôles (${roles.length})`, value: roles.join(" ") || "Aucun", inline: false }
      );
    message.channel.send({ embeds: [e] });
  }
};
