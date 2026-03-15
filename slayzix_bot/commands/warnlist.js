const { EmbedBuilder, PermissionFlagsBits } = require("discord.js");

module.exports = {
  name: "warnlist",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.ManageGuild)) return;
    await message.delete().catch(() => {});

    const warns = ctx.warnData;
    const entries = Object.entries(warns);

    if (!entries.length)
      return message.channel.send({ embeds: [ctx.redEmbed("✅ Aucun warn enregistré.", "⚠️ Warn List")] })
        .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));

    const lines = entries.map(([uid, data]) => {
      const m = message.guild.members.cache.get(uid);
      const name = m ? `${m.user.tag}` : `\`${uid}\``;
      return `**${name}** — \`${data.count}\` warn(s)`;
    });

    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle(`⚠️ Warn List (${entries.length} membres)`)
      .setDescription(lines.join("\n"))
      .setFooter({ text: `${ctx.config.vouch_server?.warn_limit || 3} warns = ban des 2 serveurs` })
      .setTimestamp();

    message.channel.send({ embeds: [e] }).then(m => setTimeout(() => m.delete().catch(() => {}), 15000));
  }
};
