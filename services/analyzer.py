from datetime import datetime
from typing import Any, Dict, List, Optional
from utils.json_manager import get_game_history


def format_iso_date(iso_str: Optional[str]) -> str:
    """Formate une date ISO en affichage français lisible."""
    if not iso_str:
        return "Inconnue"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d/%m/%Y à %H:%M")
    except Exception:
        return str(iso_str)


def format_price(amount: float, currency: str = "EUR") -> str:
    """Formate un prix avec le symbole de devise adapté."""
    symbol = "€" if currency.upper() in ["EUR", "EURO", "EUROS"] else currency
    val_str = f"{amount:.2f}".replace(".", ",")
    return f"{val_str} {symbol}"


class PriceAnalyzer:
    """Service d'analyse statistique et de tendance des prix."""

    @staticmethod
    def analyze_game(game: Dict[str, Any], history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Génère une analyse détaillée d'un jeu à partir de sa fiche et de son historique.
        """
        game_id = str(game.get("id"))
        if history is None:
            history = get_game_history(game_id)

        current_price = float(game.get("current_price", 0.0))
        previous_price = float(game.get("previous_price", current_price))
        lowest_price = float(game.get("lowest_price", current_price))
        currency = game.get("currency", "EUR")
        discount = int(game.get("discount", 0))

        # Analyser l'historique : nombre de baisses et dernière promo enregistrée
        drop_count = 0
        last_promo_price: Optional[float] = None
        last_change_date: Optional[str] = None

        if history and len(history) > 1:
            for i in range(1, len(history)):
                prev_p = float(history[i - 1].get("price", 0.0))
                curr_p = float(history[i].get("price", 0.0))
                if curr_p < prev_p:
                    drop_count += 1
                    last_promo_price = curr_p
            last_change_date = history[-1].get("date")
        elif history and len(history) == 1:
            last_change_date = history[0].get("date")

        # Déterminer la situation / tendance actuelle
        is_lowest_reached = (current_price <= lowest_price and lowest_price > 0)
        is_discounted = (discount > 0 or current_price < previous_price)
        is_price_hike = (current_price > previous_price)

        if is_lowest_reached:
            situation_title = "🏆 Prix minimum atteint"
            situation_desc = "Le prix minimum enregistré est actuellement atteint !"
            color_type = "record"
        elif is_discounted:
            situation_title = f"🔥 Promotion intéressante (-{discount} %)"
            situation_desc = f"Le jeu est en promotion à {format_price(current_price, currency)}."
            color_type = "promo"
        elif is_price_hike:
            situation_title = "🔺 Fin de promotion"
            situation_desc = f"Le prix est remonté de {format_price(previous_price, currency)} à {format_price(current_price, currency)}."
            color_type = "hike"
        else:
            situation_title = "➡️ Prix actuellement normal"
            situation_desc = "Aucune promotion active pour l'instant."
            color_type = "normal"

        return {
            "game_id": game_id,
            "name": game.get("name", "Jeu Inconnu"),
            "url": game.get("url", ""),
            "image": game.get("image"),
            "current_price": current_price,
            "previous_price": previous_price,
            "lowest_price": lowest_price,
            "currency": currency,
            "discount": discount,
            "last_checked": game.get("last_checked"),
            "last_change_date": format_iso_date(last_change_date),
            "drop_count": drop_count,
            "last_promo_price": last_promo_price,
            "situation_title": situation_title,
            "situation_desc": situation_desc,
            "color_type": color_type,
            "is_lowest_reached": is_lowest_reached,
            "is_discounted": is_discounted,
        }
