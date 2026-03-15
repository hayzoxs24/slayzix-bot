const { PermissionFlagsBits } = require("discord.js");
module.exports = {
  name: "protect",
  async execute(message, args, client, ctx) {
    if (!message.member.permissions.has(PermissionFlagsBits.Administrator)) return;
    await message.delete().catch(() => {});
    const action = (args[0] || "status").toLowerCase();
    const p = ctx.config.protection;
    let desc;
    if (action === "on") {
      p.enabled = true;
      ctx.saveJSON("./config.json", ctx.config);
      desc = "✅ Protection **activée**.";
    } else if (action === "off") {
      p.enabled = false;
      ctx.saveJSON("./config.json", ctx.config);
      desc = "⛔ Protection **désactivée**.";
    } else {
      const lc = p.log_channel ? `<#${p.log_channel}>` : "❌";
      desc = `🛡️ ${p.enabled ? "✅ ON" : "⛔ OFF"}\n`
           + `• Anti-Spam: ${p.anti_spam ? "✅" : "❌"}\n`
           + `• Anti-Invite: ${p.anti_invite ? "✅" : "❌"}\n`
           + `• Anti-Mention: ${p.anti_mention ? "✅" : "❌"}\n`
           + `• Log: ${lc}`;
    }
    message.channel.send({ embeds: [ctx.redEmbed(desc, "🛡️ Protection Slayzix")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 15000));
  }
};
