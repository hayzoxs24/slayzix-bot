module.exports = {
  name: "ltcdelete",
  async execute(message, args, client, ctx) {
    await message.delete().catch(() => {});
    if (!ctx.ltcData[message.author.id])
      return message.channel.send({ embeds: [ctx.redEmbed("❌ Aucun LTC à supprimer.")] }).then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
    delete ctx.ltcData[message.author.id];
    ctx.saveJSON("./data/ltc.json", ctx.ltcData);
    message.channel.send({ embeds: [ctx.redEmbed("Ton adresse LTC a été supprimée.", "🗑️ LTC supprimé")] })
      .then(m => setTimeout(() => m.delete().catch(() => {}), 8000));
  }
};
