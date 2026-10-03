"""
Script autonome d'exécution Cron (peut être exécuté directement en ligne de commande,
via crontab, GitHub Actions ou un scheduler sans nécessiter le Gateway Discord).
Utilisation : python cron_check.py
"""

import asyncio
import logging
import os
from pathlib import Path
import aiohttp
from dotenv import load_dotenv

from services.price_checker import PriceCheckerService
from utils.embeds import create_daily_report_embed, create_promo_embed
from utils.json_manager import ensure_data_files, load_games

# Chargement de l'environnement
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("checkprice.cron_check")


async def send_discord_rest_message(session: aiohttp.ClientSession, channel_id: str, token: str, embed_dict: dict):
    """Envoie un embed directement via l'API REST de Discord sans Gateway WebSocket."""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "embeds": [embed_dict]
    }
    async with session.post(url, headers=headers, json=payload) as resp:
        if resp.status not in (200, 201):
            body = await resp.text()
            logger.error(f"Erreur API Discord ({resp.status}): {body}")
        else:
            logger.info("Message envoyé avec succès sur Discord.")


async def run_cron_analysis() -> dict:
    """Exécute l'analyse complète de tous les jeux et publie les messages sur Discord."""
    ensure_data_files()
    games = load_games()
    if not games:
        logger.info("Aucun jeu surveillé trouvé dans data/games.json.")
        return {"status": "ok", "message": "Aucun jeu surveillé", "total_games": 0}

    token = os.getenv("DISCORD_TOKEN")
    channel_id = os.getenv("DISCORD_CHANNEL_ID")

    if not token or not channel_id:
        msg = "DISCORD_TOKEN ou DISCORD_CHANNEL_ID manquant dans les variables d'environnement."
        logger.error(msg)
        return {"status": "error", "message": msg}

    logger.info(f"Lancement de l'actualisation Cron pour {len(games)} jeu(x)...")
    checker = PriceCheckerService()

    # Exécuter l'analyse complète
    results = await checker.check_all_games(
        bot=None,
        target_channel=None,
        delay_between_requests=1.5
    )

    # Envoi direct des alertes et du rapport via API REST Discord
    async with aiohttp.ClientSession() as session:
        # 1. Alertes promos détectées
        for promo in results.get("promotions", []):
            embed = create_promo_embed(
                game=promo["game"],
                old_price=promo["old_price"],
                new_price=promo["new_price"],
                discount=promo["discount"]
            )
            await send_discord_rest_message(session, channel_id, token, embed.to_dict())

        # 2. Rapport global
        report_embed = create_daily_report_embed(results)
        await send_discord_rest_message(session, channel_id, token, report_embed.to_dict())

    logger.info("Actualisation Cron terminée avec succès.")
    return {
        "status": "success",
        "total_games": results.get("total_games", 0),
        "promotions_detected": len(results.get("promotions", [])),
        "price_hikes": len(results.get("hikes", [])),
        "unchanged": len(results.get("unchanged", []))
    }


async def main():
    await run_cron_analysis()


if __name__ == "__main__":
    asyncio.run(main())
