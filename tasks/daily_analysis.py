import logging
import os
from datetime import time
from zoneinfo import ZoneInfo
import discord
from discord.ext import commands, tasks
from services.price_checker import PriceCheckerService

logger = logging.getLogger("checkprice.tasks.daily")

PARIS_TZ = ZoneInfo("Europe/Paris")
DAILY_TIME = time(hour=8, minute=0, second=0, tzinfo=PARIS_TZ)


class DailyAnalysisTask(commands.Cog):
    """Tâche automatisée exécutant l'analyse quotidienne des prix à 08h00 (Europe/Paris)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.checker = PriceCheckerService()
        self.daily_loop.start()

    def cog_unload(self):
        self.daily_loop.cancel()

    @tasks.loop(time=DAILY_TIME)
    async def daily_loop(self):
        """Boucle quotidienne exécutée à 08h00 précises heure de Paris."""
        logger.info("Exécution planifiée de 08:00 (Europe/Paris) démarrée...")
        channel_id = os.getenv("DISCORD_CHANNEL_ID")
        if not channel_id:
            logger.warning("DISCORD_CHANNEL_ID n'est pas configuré dans le fichier .env.")
            return

        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                channel = await self.bot.fetch_channel(int(channel_id))
        except Exception as e:
            logger.error(f"Impossible de récupérer le salon Discord {channel_id}: {e}")
            return

        if not channel:
            logger.error(f"Salon Discord {channel_id} introuvable.")
            return

        try:
            await self.checker.check_all_games(
                bot=self.bot,
                target_channel=channel,
                delay_between_requests=1.5
            )
            logger.info("Analyse quotidienne de 08:00 terminée avec succès.")
        except Exception as e:
            logger.error(f"Erreur durant l'analyse quotidienne de 08:00: {e}", exc_info=True)

    @daily_loop.before_loop
    async def before_daily_loop(self):
        """Attend que le bot soit pleinement connecté et prêt avant d'armer la boucle."""
        await self.bot.wait_until_ready()
        logger.info(f"Tâche quotidienne initialisée. Prochaine exécution à 08:00 (Europe/Paris).")


async def setup(bot: commands.Bot):
    await bot.add_cog(DailyAnalysisTask(bot))
