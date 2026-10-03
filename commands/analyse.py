import os
import discord
from discord import app_commands
from discord.ext import commands
from services.price_checker import PriceCheckerService
from utils.embeds import create_daily_report_embed
from utils.json_manager import load_games


class AnalyseCommand(commands.Cog):
    """Commande pour lancer l'analyse manuelle de tous les jeux surveillés."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.checker = PriceCheckerService()

    @app_commands.command(
        name="analyse",
        description="Lancer immédiatement l'analyse des prix de tous les jeux surveillés"
    )
    async def analyse(self, interaction: discord.Interaction):
        games = load_games()
        if not games:
            await interaction.response.send_message(
                "ℹ️ Aucun jeu n'est actuellement surveillé. Utilise `/watch <url>` pour en ajouter un.",
                ephemeral=True
            )
            return

        # Différer la réponse car l'analyse peut durer quelques secondes selon le nombre de jeux
        await interaction.response.defer(thinking=True)

        # Salon où envoyer les éventuelles alertes promo avec ping
        # Si un DISCORD_CHANNEL_ID est configuré dans le .env, on peut l'utiliser ou utiliser le salon courant
        configured_channel_id = os.getenv("DISCORD_CHANNEL_ID")
        channel = None
        if configured_channel_id:
            try:
                channel = self.bot.get_channel(int(configured_channel_id))
            except Exception:
                pass
        if not channel:
            channel = interaction.channel

        # Exécuter la vérification complète
        # target_channel=None pour ne pas doubler le rapport global (car followup va l'envoyer ci-dessous)
        # Mais on passe target_channel pour les alertes promo individuelles si de nouvelles baisses sont trouvées !
        results = await self.checker.check_all_games(
            bot=self.bot,
            target_channel=channel,
            delay_between_requests=1.5
        )

        report_embed = create_daily_report_embed(results)
        await interaction.followup.send(embed=report_embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AnalyseCommand(bot))
