module.exports = {
  name: "ppldelete",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    if (!ctx.pplData[message.author.id])
      return message.channel.send({ embeds: [ctx.redEmbed("❌ Aucun PPL à supprimer.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    delete ctx.pplData[message.author.id];
    ctx.saveJSON("./data/ppl.json", ctx.pplData);
    message.channel.send({ embeds: [ctx.redEmbed("Ton adresse PayPal a été supprimée.", "🗑️ PPL supprimé")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
