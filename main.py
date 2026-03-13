# ── Shop Embed ─────────────────────────────────────────────────────────────────
@bot.command(name="shopembed")
@commands.has_permissions(administrator=True)
async def shopembed(ctx):
    await ctx.message.delete()
    embed = discord.Embed(title="Titre ici", description="Description ici", color=RED)
    embed.set_footer(text="Footer ici")
    message = await ctx.send(embed=embed)

    class ShopView(discord.ui.View):
        def __init__(self, embed, ctx, message):
            super().__init__(timeout=120)
            self.embed = embed
            self.ctx = ctx
            self.message = message
            self.history = [embed.to_dict()]
            self.history_index = 0

            options = [
                discord.SelectOption(label="Titre",           value="title"),
                discord.SelectOption(label="Description",     value="description"),
                discord.SelectOption(label="Auteur",          value="author"),
                discord.SelectOption(label="Footer",          value="footer"),
                discord.SelectOption(label="Thumbnail",       value="thumbnail"),
                discord.SelectOption(label="Image",           value="image"),
                discord.SelectOption(label="URL",             value="url"),
                discord.SelectOption(label="Couleur",         value="color"),
                discord.SelectOption(label="Ajouter un Field",   value="add_field"),
                discord.SelectOption(label="Supprimer un Field", value="remove_field"),
                discord.SelectOption(label="Timestamp",       value="timestamp"),
            ]
            select = discord.ui.Select(placeholder="Choisir un champ à modifier", options=options)
            select.callback = self.select_callback
            self.add_item(select)

            for label, style, cb_name in [
                ("↩️ Défaire",   discord.ButtonStyle.secondary, "undo_callback"),
                ("↪️ Refaire",   discord.ButtonStyle.secondary, "redo_callback"),
                ("✅ Valider",   discord.ButtonStyle.success,   "validate_callback"),
                ("🗑️ Supprimer", discord.ButtonStyle.danger,    "delete_callback"),
            ]:
                btn = discord.ui.Button(label=label, style=style)
                btn.callback = getattr(self, cb_name)
                self.add_item(btn)

        async def select_callback(self, interaction):
            field = interaction.data["values"][0]
            instructions = {
                "title":        "Envoie le **titre** de l'embed.",
                "description":  "Envoie la **description** de l'embed.",
                "author":       "Envoie le **nom de l'auteur**.",
                "footer":       "Envoie le **texte du footer**.",
                "thumbnail":    "Envoie une **URL ou image** pour la thumbnail.",
                "image":        "Envoie une **URL ou image** principale.",
                "url":          "Envoie l'**URL** de l'embed.",
                "color":        "Envoie une **couleur hex** (ex: `#ff0000`).",
                "add_field":    "Envoie le **nom** du field à ajouter.",
                "remove_field": "Envoie le **numéro** du field à supprimer (commence à 1).",
                "timestamp":    "✅ Timestamp ajouté automatiquement.",
            }
            await interaction.response.send_message(instructions[field], ephemeral=True)

            if field == "timestamp":
                self.embed.timestamp = discord.utils.utcnow()
                self.history = self.history[:self.history_index + 1]
                self.history.append(self.embed.to_dict())
                self.history_index += 1
                await self.message.edit(embed=self.embed, view=self)
                return

            def check(m): return m.author == self.ctx.author and m.channel == self.ctx.channel
            try:
                msg = await bot.wait_for("message", check=check, timeout=120)
            except asyncio.TimeoutError:
                await interaction.followup.send("⏱️ Temps écoulé.", ephemeral=True)
                return

            val = msg.content
            try:
                if field == "title":        self.embed.title = val
                elif field == "description":self.embed.description = val
                elif field == "author":     self.embed.set_author(name=val)
                elif field == "footer":     self.embed.set_footer(text=val)
                elif field == "thumbnail":  self.embed.set_thumbnail(url=msg.attachments[0].url if msg.attachments else val)
                elif field == "image":      self.embed.set_image(url=msg.attachments[0].url if msg.attachments else val)
                elif field == "url":        self.embed.url = val
                elif field == "color":      self.embed.color = discord.Color(int(val.replace("#", ""), 16))
                elif field == "add_field":  self.embed.add_field(name=val, value="Valeur", inline=False)
                elif field == "remove_field":
                    idx = int(val) - 1
                    self.embed.remove_field(idx)
            except Exception:
                await interaction.followup.send("❌ Valeur invalide.", ephemeral=True)
                return

            self.history = self.history[:self.history_index + 1]
            self.history.append(self.embed.to_dict())
            self.history_index += 1
            try: await msg.delete()
            except Exception: pass
            await self.message.edit(embed=self.embed, view=self)

        async def undo_callback(self, interaction):
            await interaction.response.defer()
            if self.history_index > 0:
                self.history_index -= 1
                self.embed = discord.Embed.from_dict(self.history[self.history_index])
                await self.message.edit(embed=self.embed, view=self)

        async def redo_callback(self, interaction):
            await interaction.response.defer()
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self.embed = discord.Embed.from_dict(self.history[self.history_index])
                await self.message.edit(embed=self.embed, view=self)

        async def validate_callback(self, interaction):
            await interaction.response.send_message("Envoie l'**ID** ou le **#salon** où envoyer l'embed :", ephemeral=True)
            def check(m): return m.author == self.ctx.author and m.channel == self.ctx.channel
            try:
                msg = await bot.wait_for("message", check=check, timeout=120)
            except asyncio.TimeoutError:
                await interaction.followup.send("⏱️ Temps écoulé.", ephemeral=True)
                return
            try:
                cid = int(msg.content[2:-1]) if msg.content.startswith("<#") else int(msg.content)
                channel = bot.get_channel(cid)
                if not channel:
                    return await interaction.followup.send("❌ Salon introuvable.", ephemeral=True)
                await channel.send(embed=self.embed)
                try: await msg.delete()
                except Exception: pass
                await interaction.followup.send(f"✅ Embed envoyé dans {channel.mention} !", ephemeral=True)
            except Exception:
                await interaction.followup.send("❌ ID invalide.", ephemeral=True)

        async def delete_callback(self, interaction):
            await interaction.response.defer()
            await self.message.delete()

        async def on_timeout(self):
            try: await self.message.delete()
            except Exception: pass

    await message.edit(view=ShopView(embed, ctx, message))
