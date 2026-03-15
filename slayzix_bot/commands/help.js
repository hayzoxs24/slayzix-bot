const { EmbedBuilder } = require("discord.js");
module.exports = {
  name: "help",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    const p = ctx.config.prefix;
    const e = new EmbedBuilder().setColor(ctx.RED)
      .setTitle("📋 Commandes — Slayzix Shop")
      .setDescription(`Préfixe: **\`${p}\`**`)
      .addFields(
        { name: "🎫 Tickets",       value: `\`${p}setup\` \`${p}setlogs\` \`${p}setfrench\` \`${p}setenglish\` \`${p}setnitro\` \`${p}setboost\` \`${p}setdeco\` \`${p}setexchange\` \`${p}setother\``, inline: false },
        { name: "🔑 Accès Ticket",  value: `\`${p}addaccessticket @m\` \`${p}removeaccessticket @m\` \`${p}listaccessticket\``, inline: false },
        { name: "💳 PayPal",        value: `\`${p}pplsave\` \`${p}ppl\` \`${p}ppldelete\``, inline: false },
        { name: "🪙 LTC",           value: `\`${p}ltcsave\` \`${p}ltc\` \`${p}ltcdelete\``, inline: false },
        { name: "🎉 Giveaway",      value: `\`${p}gstart <durée> <gagnants> <prix>\` \`${p}gend <id>\``, inline: false },
        { name: "⚠️ Warn / Vouch",  value: `\`${p}warnlist\` \`${p}clearwarn @m\`\n⏱️ Délai fixe: **1h** — Salon vouch fixe: <#1482763336364851263>`, inline: false },
        { name: "🛡️ Protection",    value: `\`${p}protect on/off/status\` \`${p}protectlog #salon\``, inline: false },
        { name: "🔨 Modération",    value: `\`${p}ban\` \`${p}kick\` \`${p}mute\` \`${p}unmute\` \`${p}unban\` \`${p}clear\` \`${p}lock\` \`${p}unlock\``, inline: false },
        { name: "🎫 Ticket Utils",  value: `\`${p}claim\` \`${p}unclaim\` \`${p}close\` \`${p}add\` \`${p}remove\` \`${p}rename\` \`${p}slowmode\` \`${p}finish\``, inline: false },
        { name: "📢 Divers",        value: `\`${p}say\` \`${p}announce\` \`${p}dmall\` \`${p}tos\` \`${p}wearelegit\` \`${p}stats\` \`${p}userinfo\` \`${p}serverinfo\` \`${p}prefix\` \`${p}shopembed\``, inline: false }
      )
      .setFooter({ text: `Préfixe: ${p}` }).setTimestamp();
    if (message.guild.iconURL()) e.setThumbnail(message.guild.iconURL());
    message.channel.send({ embeds: [e] }).then(m => setTimeout(() => m.delete().catch(() => {}), 60000));
  }
};
