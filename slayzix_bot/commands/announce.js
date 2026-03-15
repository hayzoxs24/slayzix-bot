const { EmbedBuilder, PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "announce",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const channel = message.mentions.channels.first();
    if (!channel) return message.channel.send({ embeds: [ctx.redEmbed("❌ Usage: `*announce #salon <message>`")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    const text = args.slice(1).join(" ");
    if (!text) return;
    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("📢 Annonce — Slayzix Shop")
      .setDescription(text)
      .setImage(ctx.BANNER_URL)
      .setTimestamp();
    await channel.send({ embeds: [e] });
    message.channel.send({ embeds: [ctx.redEmbed(`✅ Annonce → ${channel}`)] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 5000));
  }
};
