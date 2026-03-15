const { EmbedBuilder, PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "dmall",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const text = args.join(" ");
    if (!text) return message.channel.send({ embeds: [ctx.redEmbed("❌ Usage: `*dmall <message>`")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));

    const members = [...message.guild.members.cache.values()].filter(m => !m.user.bot);
    const confirm = await message.channel.send({ embeds: [ctx.redEmbed(`Envoyer à **${members.length}** membres :\n*${text}*\nRéponds \`oui\` pour confirmer.`, "📨 DM All")] });

    const filter = m => m.author.id === message.author.id && m.content.toLowerCase() === "oui";
    const collected = await message.channel.awaitMessages({ filter, max: 1, time: 30000 }).catch(() => null);
    await confirm.delete().catch(() => {});
    if (!collected || !collected.size) return message.channel.send({ embeds: [ctx.redEmbed("❌ Annulé.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 5000));

    const prog = await message.channel.send({ embeds: [ctx.redEmbed("📨 Envoi en cours...")] });
    let ok = 0, fail = 0;
    const dmEmbed = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("📨 Message de Slayzix Shop")
      .setDescription(text)
      .setFooter({ text: "Slayzix Shop" }).setTimestamp();

    for (const m of members) {
      try { await m.send({ embeds: [dmEmbed] }); ok++; }
      catch { fail++; }
      await new Promise(r => setTimeout(r, 500));
    }
    prog.edit({ embeds: [ctx.redEmbed(`✅ Envoyé: **${ok}**\n❌ Échec: **${fail}**`, "✅ DM All terminé")] });
  }
};
