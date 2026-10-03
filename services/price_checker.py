import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import discord
from services.psprices import PSPricesService
from utils.embeds import create_daily_report_embed, create_promo_embed
from utils.json_manager import (
    PARIS_TZ,
    add_price_history_entry,
    get_current_paris_iso,
    load_games,
    update_game,
)

logger = logging.getLogger("checkprice.checker")


class PriceCheckerService:
    """Service de vérification périodique et manuelle des prix."""

    def __init__(self, psprices_service: Optional[PSPricesService] = None):
        self.psprices = psprices_service or PSPricesService()

    async def check_all_games(
        self,
        bot: Optional[discord.Client] = None,
        target_channel: Optional[discord.abc.Messageable] = None,
        delay_between_requests: float = 1.5
    ) -> Dict[str, Any]:
        """
        Vérifie tous les jeux surveillés, met à jour les JSON et envoie
        les notifications Discord si demandé.
        """
        games = load_games()
        now_dt = datetime.now(PARIS_TZ)
        now_iso = get_current_paris_iso()

        results: Dict[str, Any] = {
            "total_games": len(games),
            "promotions": [],
            "hikes": [],
            "unchanged": [],
            "errors": [],
            "timestamp": now_dt
        }

        if not games:
            logger.info("Aucun jeu à vérifier.")
            return results

        logger.info(f"Début de l'analyse pour {len(games)} jeu(x)...")

        for idx, game in enumerate(games):
            game_id = str(game.get("id"))
            game_name = game.get("name", "Inconnu")
            game_url = game.get("url", "")
            old_price = round(float(game.get("current_price", 0.0)), 2)
            lowest_price = round(float(game.get("lowest_price", old_price)), 2)

            # Politesse envers PSPrices : petite pause entre chaque requête
            if idx > 0 and delay_between_requests > 0:
                await asyncio.sleep(delay_between_requests)

            try:
                scraped = await self.psprices.fetch_game_data(game_url)
                new_price = round(float(scraped.get("current_price", old_price)), 2)
                new_discount = int(scraped.get("discount", 0))
                scraped_lowest = round(float(scraped.get("lowest_price", lowest_price)), 2)

                # Mettre à jour lowest_price si un prix plus bas est détecté
                actual_lowest = min(scraped_lowest, new_price) if scraped_lowest > 0 else new_price

                # CAS 1 : Baisse de prix = PROMOTION !
                if new_price < old_price:
                    logger.info(f"PROMO détectée pour {game_name}: {old_price} -> {new_price} (-{new_discount}%)")
                    
                    update_data = {
                        "previous_price": old_price,
                        "current_price": new_price,
                        "lowest_price": actual_lowest,
                        "discount": new_discount,
                        "last_checked": now_iso,
                        "image": scraped.get("image") or game.get("image")
                    }
                    update_game(game_id, update_data)
                    # Enregistrer dans l'historique car le prix a changé
                    add_price_history_entry(game_id, new_price, new_discount, now_iso)

                    promo_item = {
                        "game": {**game, **update_data},
                        "old_price": old_price,
                        "new_price": new_price,
                        "discount": new_discount
                    }
                    results["promotions"].append(promo_item)

                    # Notification immédiate pour la promotion si salon disponible (sans ping de rôle)
                    if target_channel:
                        embed = create_promo_embed(
                            game={**game, **update_data},
                            old_price=old_price,
                            new_price=new_price,
                            discount=new_discount
                        )
                        try:
                            await target_channel.send(embed=embed)
                        except Exception as e:
                            logger.error(f"Erreur lors de l'envoi de l'alerte promo pour {game_name}: {e}")

                # CAS 2 : Hausse de prix = Fin de promotion
                elif new_price > old_price:
                    logger.info(f"Hausse de prix pour {game_name}: {old_price} -> {new_price}")
                    update_data = {
                        "previous_price": old_price,
                        "current_price": new_price,
                        "lowest_price": lowest_price,
                        "discount": new_discount,
                        "last_checked": now_iso,
                        "image": scraped.get("image") or game.get("image")
                    }
                    update_game(game_id, update_data)
                    # Enregistrer dans l'historique car le prix a changé
                    add_price_history_entry(game_id, new_price, new_discount, now_iso)

                    results["hikes"].append({
                        "game": {**game, **update_data},
                        "old_price": old_price,
                        "new_price": new_price
                    })

                # CAS 3 : Prix inchangé
                else:
                    # Règle d'or : NE PAS ajouter dans price_history.json
                    update_game(game_id, {
                        "last_checked": now_iso,
                        "image": scraped.get("image") or game.get("image"),
                        "lowest_price": actual_lowest,
                        "discount": new_discount
                    })
                    results["unchanged"].append({
                        "game": {**game, "last_checked": now_iso}
                    })

            except Exception as e:
                logger.error(f"Erreur lors de la vérification de {game_name} ({game_url}): {e}")
                results["errors"].append({
                    "game": game,
                    "error": str(e)
                })
                # Marquer au moins la date de tentative
                update_game(game_id, {"last_checked": now_iso})

        # Envoyer le rapport global dans le salon si spécifié
        if target_channel:
            report_embed = create_daily_report_embed(results)
            try:
                await target_channel.send(embed=report_embed)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi du rapport global: {e}")

        logger.info(
            f"Vérification terminée : {len(results['promotions'])} promo(s), "
            f"{len(results['hikes'])} hausse(s), {len(results['unchanged'])} inchangé(s), "
            f"{len(results['errors'])} erreur(s)."
        )

        return results
