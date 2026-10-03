import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.json_manager import ensure_data_files, load_games

# 1. Chargement de l'environnement
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# 2. Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("checkprice")

# 3. Fuseau horaire Paris
PARIS_TZ = ZoneInfo("Europe/Paris")


class CheckPriceBot(commands.Bot):
    """Bot Discord CheckPrice pour la surveillance des prix PS Store via PSPrices."""

    def __init__(self):
        # Slash commands ne nécessitent pas de Message Content Intent
        intents = discord.Intents.default()
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        """Chargement des extensions et synchronisation des slash commands."""
        ensure_data_files()

        # Liste des extensions à charger
        extensions = [
            "commands.watch",
            "commands.unwatch",
            "commands.watchlist",
            "commands.prix",
            "commands.analyse",
            "tasks.daily_analysis"
        ]

        for ext in extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Extension chargée : {ext}")
            except Exception as e:
                logger.error(f"Échec du chargement de l'extension {ext}: {e}", exc_info=True)

        # Synchronisation des slash commands
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            try:
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(f"Slash commands synchronisées instantanément pour le serveur ({len(synced)} commandes).")
            except Exception as e:
                logger.warning(f"Impossible de synchroniser avec le serveur {guild_id}: {e}. Synchronisation globale en cours...")
                synced = await self.tree.sync()
                logger.info(f"Slash commands synchronisées globalement ({len(synced)} commandes).")
        else:
            synced = await self.tree.sync()
            logger.info(f"Slash commands synchronisées globalement ({len(synced)} commandes).")

    async def on_ready(self):
        """Événement déclenché lorsque le bot est connecté et prêt."""
        now_str = datetime.now(PARIS_TZ).strftime("%d/%m/%Y %H:%M:%S")
        games = load_games()
        logger.info(f"==================================================")
        logger.info(f" Connecté en tant que : {self.user.name}#{self.user.discriminator} (ID: {self.user.id})")
        logger.info(f" Heure Paris : {now_str}")
        logger.info(f" Jeux surveillés actuellement : {len(games)}")
        logger.info(f"==================================================")

        # Statut riche Discord
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(games)} jeux • /watchlist"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)


def main():
    """Point d'entrée principal de l'application."""
    token = os.getenv("DISCORD_TOKEN")
    if not token or token.strip() in ["", "your_discord_bot_token", "YOUR_BOT_TOKEN_HERE"]:
        logger.error(
            "ERREUR : DISCORD_TOKEN manquant ou non renseigné dans le fichier .env.\n"
            "Veuillez ouvrir le fichier .env et renseigner votre token Discord."
        )
        sys.exit(1)

    bot = CheckPriceBot()
    try:
        bot.run(token.strip())
    except discord.LoginFailure:
        logger.error("ERREUR : Token Discord invalide. Vérifiez la valeur de DISCORD_TOKEN dans le fichier .env.")
    except Exception as e:
        logger.error(f"Une erreur est survenue lors de l'exécution du bot : {e}", exc_info=True)


if __name__ == "__main__":
    main()
