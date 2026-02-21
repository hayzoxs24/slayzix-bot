class TicketView(discord.ui.View):
    def __init__(self, creator_id):
        super().__init__(timeout=None)
        self.creator_id = creator_id
        self.claimed_by = None
        self.paid = False

    @discord.ui.button(label="🔔 Réclamer", style=discord.ButtonStyle.success)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role.name in STAFF_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)

        if self.claimed_by:
            return await interaction.response.send_message(
                f"❌ Déjà réclamé par {self.claimed_by.mention}.",
                ephemeral=True
            )

        self.claimed_by = interaction.user
        button.label = f"✅ {interaction.user.name}"
        button.disabled = True

        for role_name in STAFF_ROLES:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                await interaction.channel.set_permissions(role, send_messages=False)

        await interaction.channel.set_permissions(interaction.user, send_messages=True)

        creator = interaction.guild.get_member(self.creator_id)
        if creator:
            await interaction.channel.set_permissions(creator, send_messages=True)

        await interaction.message.edit(view=self)
        await interaction.response.send_message(
            f"🔔 Ticket pris en charge par {interaction.user.mention}"
        )

    @discord.ui.button(label="💳 Confirmer paiement", style=discord.ButtonStyle.primary)
    async def confirm_payment(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id != self.creator_id:
            return await interaction.response.send_message(
                "❌ Seul le client peut confirmer.",
                ephemeral=True
            )

        if not self.claimed_by:
            return await interaction.response.send_message(
                "❌ Aucun staff n’a réclamé.",
                ephemeral=True
            )

        staff_name = self.claimed_by.name.lower()
        paypal_link = PAYPAL_LINKS.get(staff_name)

        if not paypal_link:
            return await interaction.response.send_message(
                "❌ Aucun PayPal configuré.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="💳 PAIEMENT PAYPAL",
            description=f"""
━━━━━━━━━━━━━━━━━━━━━━
👉 {paypal_link}

📌 Envoie la preuve après paiement.
━━━━━━━━━━━━━━━━━━━━━━
""",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="✅ Paiement validé", style=discord.ButtonStyle.secondary)
    async def validate_payment(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role.name in STAFF_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ Staff uniquement.", ephemeral=True)

        if not self.claimed_by:
            return await interaction.response.send_message("❌ Ticket non réclamé.", ephemeral=True)

        if self.paid:
            return await interaction.response.send_message("⚠️ Déjà validé.", ephemeral=True)

        self.paid = True
        button.disabled = True
        button.label = "🟢 Paiement confirmé"

        # 🔒 Retire écriture au client
        creator = interaction.guild.get_member(self.creator_id)
        if creator:
            await interaction.channel.set_permissions(creator, send_messages=False)

        embed = discord.Embed(
            title="🟢 PAIEMENT VALIDÉ",
            description=f"""
━━━━━━━━━━━━━━━━━━━━━━
💰 Paiement confirmé par {interaction.user.mention}

📦 Commande en cours de traitement.
Merci pour votre confiance 💎
━━━━━━━━━━━━━━━━━━━━━━
""",
            color=discord.Color.green()
        )

        await interaction.message.edit(view=self)
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(role.name in STAFF_ROLES for role in interaction.user.roles):
            return await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)

        await interaction.response.send_message("🔒 Fermeture...")
        bot.active_tickets.pop(interaction.channel.id, None)
        await interaction.channel.delete()
