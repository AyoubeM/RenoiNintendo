import asyncio
import logging
import os
from typing import Optional
import discord
from aiohttp import web
from services.price_checker import PriceCheckerService
from utils.json_manager import load_games

logger = logging.getLogger("checkprice.cron_server")


class CronWebServer:
    """
    Serveur HTTP léger (aiohttp.web) permettant de recevoir des requêtes externes
    (cron-job.org, EasyCron, Vercel Cron, Webhook, etc.) pour déclencher l'analyse.
    """

    def __init__(self, bot: discord.Client, checker: Optional[PriceCheckerService] = None):
        self.bot = bot
        self.checker = checker or PriceCheckerService()
        self.app = web.Application()
        self._setup_routes()
        self.runner: Optional[web.AppRunner] = None

    def _setup_routes(self):
        self.app.router.add_get("/", self.handle_health)
        self.app.router.add_get("/api/health", self.handle_health)
        self.app.router.add_get("/api/cron", self.handle_cron_trigger)
        self.app.router.add_post("/api/cron", self.handle_cron_trigger)

    def _verify_secret(self, request: web.Request) -> bool:
        """Vérifie le jeton de sécurité si CRON_SECRET est configuré."""
        expected_secret = os.getenv("CRON_SECRET")
        if not expected_secret:
            return True  # Pas de secret configuré, ouvert

        # Vérification via header Authorization: Bearer <secret>
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ", 1)[1].strip()
            if token == expected_secret:
                return True

        # Vérification via paramètre d'URL ?secret=<secret>
        query_secret = request.query.get("secret", "").strip()
        if query_secret == expected_secret:
            return True

        return False

    async def handle_health(self, request: web.Request) -> web.Response:
        """Endpoint de statut et santé du bot."""
        games = load_games()
        return web.json_response({
            "status": "online",
            "bot_user": str(self.bot.user) if self.bot.user else "connecting",
            "watched_games_count": len(games)
        })

    async def handle_cron_trigger(self, request: web.Request) -> web.Response:
        """Endpoint appelé par le cron externe pour déclencher l'analyse complète."""
        if not self._verify_secret(request):
            logger.warning("Tentative d'appel à /api/cron avec un secret invalide.")
            return web.json_response({"error": "Unauthorized: secret invalide"}, status=401)

        logger.info("Requête externe Cron reçue sur /api/cron. Lancement de l'analyse...")

        channel_id = os.getenv("DISCORD_CHANNEL_ID")
        channel = None
        if channel_id:
            try:
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    channel = await self.bot.fetch_channel(int(channel_id))
            except Exception as e:
                logger.error(f"Impossible d'obtenir le salon Discord {channel_id}: {e}")

        # Lancer la vérification en arrière-plan ou directement
        try:
            results = await self.checker.check_all_games(
                bot=self.bot,
                target_channel=channel,
                delay_between_requests=1.5
            )
            return web.json_response({
                "status": "success",
                "message": "Analyse effectuée avec succès.",
                "total_games": results.get("total_games", 0),
                "promotions_detected": len(results.get("promotions", [])),
                "price_hikes": len(results.get("hikes", [])),
                "unchanged": len(results.get("unchanged", []))
            })
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de /api/cron: {e}", exc_info=True)
            return web.json_response({
                "status": "error",
                "message": str(e)
            }, status=500)

    async def start(self, port: int = 8080):
        """Démarre le serveur web aiohttp."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Serveur Web Cron actif sur http://0.0.0.0:{port} (Endpoint: /api/cron)")

    async def stop(self):
        """Arrête le serveur web aiohttp."""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Serveur Web Cron arrêté.")
