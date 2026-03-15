const { EmbedBuilder } = require("discord.js");

module.exports = {
  name: "discord",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("💬 Slayzix Shop — Discord")
      .setDescription("👉 **https://discord.gg/8sUvMRJX3B**")
      .setImage(ctx.BANNER_URL)
      .setTimestamp();
    message.channel.send({ embeds: [e] });
  }
};
