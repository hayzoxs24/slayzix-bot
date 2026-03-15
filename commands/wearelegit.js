const { EmbedBuilder, PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "wearelegit",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("Slayzix Shop Legit?")
      .setDescription("✅ = Yes\n❌ No = **Ban**")
      .setImage(ctx.BANNER_URL);
    message.channel.send({ embeds: [e] });
  }
};
