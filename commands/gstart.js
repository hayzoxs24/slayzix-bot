const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, PermissionFlagsBits } = require("discord.js");

module.exports = {
  name: "gstart",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.ManageGuild)) return;
    await message.delete().catch(() => {});
    // *gstart <duration> <winners> <prize>
    // e.g. *gstart 1h 2 Nitro Basic
    if (args.length < 3) return message.channel.send({ embeds: [ctx.redEmbed("❌ Usage: `*gstart <durée> <gagnants> <prix>`\nEx: `*gstart 1h 2 Nitro Basic`")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));

    const durationStr = args[0];
    const winners     = parseInt(args[1]);
    const prize       = args.slice(2).join(" ");

    const units = { s: 1000, m: 60000, h: 3600000, d: 86400000 };
    const unit  = durationStr.slice(-1).toLowerCase();
    const val   = parseInt(durationStr.slice(0, -1));
    if (!units[unit] || isNaN(val)) return message.channel.send({ embeds: [ctx.redEmbed("❌ Format invalide. Ex: `30s` `5m` `1h` `2d`")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    if (winners < 1) return message.channel.send({ embeds: [ctx.redEmbed("❌ Minimum 1 gagnant.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));

    const duration = val * units[unit];
    const endTime  = Date.now() + duration;
    const endTs    = Math.floor(endTime / 1000);

    const embed = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("🎉 GIVEAWAY !")
      .setDescription(`**Prix:** ${prize}\n**Gagnants:** ${winners}\n**Organisateur:** ${message.author}\n**Fin:** <t:${endTs}:R>\n\nClique sur 🎉 pour participer !`)
      .setTimestamp();

    const btn = new ButtonBuilder().setCustomId("giveaway_join").setLabel("🎉 Participer").setStyle(ButtonStyle.Success);
    const msg = await message.channel.send({ embeds: [embed], components: [new ActionRowBuilder().addComponents(btn)] });

    ctx.giveawayData[msg.id] = { prize, winners, host: message.author.id, participants: [], endTime, ended: false, channelId: message.channel.id, messageId: msg.id };
    ctx.saveJSON("./data/giveaways.json", ctx.giveawayData);

    setTimeout(() => client.endGiveaway(msg.id), duration);
  }
};
