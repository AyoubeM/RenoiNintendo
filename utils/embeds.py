from datetime import datetime
from typing import Any, Dict, List, Optional
import discord
from services.analyzer import format_iso_date, format_price
from utils.json_manager import PARIS_TZ

# Palette de couleurs modernes pour Discord
COLOR_PRIMARY = 0x5865F2    # Blurple Discord
COLOR_PROMO = 0xFF5722      # Orange / Rouge feu pour les promotions
COLOR_RECORD = 0xFEE75C     # Or pour les records historiques
COLOR_NORMAL = 0x2ECC71     # Vert doux / neutre
COLOR_HIKE = 0xE67E22       # Ambre pour fin de promo / hausses
COLOR_MUTED = 0x95A5A6      # Gris


def create_game_embed(game: Dict[str, Any], analysis: Optional[Dict[str, Any]] = None) -> discord.Embed:
    """Crée un embed complet pour afficher les informations de prix d'un jeu."""
    current_price = game.get("current_price", 0.0)
    lowest_price = game.get("lowest_price", current_price)
    currency = game.get("currency", "EUR")
    discount = game.get("discount", 0)

    is_lowest = (analysis.get("is_lowest_reached") if analysis else (current_price <= lowest_price and lowest_price > 0))
    if is_lowest:
        color = COLOR_RECORD
    elif discount > 0:
        color = COLOR_PROMO
    else:
        color = COLOR_PRIMARY

    embed = discord.Embed(
        title=f"🎮 {game.get('name', 'Jeu Inconnu')}",
        url=game.get("url"),
        color=color
    )

    if game.get("image"):
        embed.set_thumbnail(url=game["image"])

    disc_str = f"**-{discount} %**" if discount > 0 else "aucune"
    embed.add_field(
        name="💰 Prix actuel",
        value=format_price(current_price, currency),
        inline=True
    )
    embed.add_field(
        name="📉 Réduction",
        value=disc_str,
        inline=True
    )
    embed.add_field(
        name="🏆 Prix minimum",
        value=format_price(lowest_price, currency),
        inline=True
    )

    last_check_str = format_iso_date(game.get("last_checked"))
    embed.add_field(
        name="🕐 Dernière vérification",
        value=last_check_str,
        inline=True
    )

    embed.add_field(
        name="🔗 PSPrices",
        value=f"[Consulter la page PSPrices]({game.get('url')})",
        inline=False
    )

    embed.set_footer(text="CheckPrice • Données issues de PSPrices", icon_url="https://psprices.com/staticfiles/i/favicon/512.png")
    embed.timestamp = datetime.now(PARIS_TZ)
    return embed


def create_promo_embed(game: Dict[str, Any], old_price: float, new_price: float, discount: int) -> discord.Embed:
    """Crée l'embed d'alerte lors de la détection d'une NOUVELLE promotion."""
    currency = game.get("currency", "EUR")
    lowest = game.get("lowest_price", new_price)

    embed = discord.Embed(
        title="🚨 NOUVELLE PROMO",
        url=game.get("url"),
        color=COLOR_PROMO
    )

    if game.get("image"):
        embed.set_thumbnail(url=game["image"])

    desc_lines = [
        f"🎮 **{game.get('name', 'Jeu Inconnu')}**\n",
        f"💰 **{format_price(old_price, currency)}** ➔ **{format_price(new_price, currency)}**",
        f"🔥 **-{discount} %**",
        f"🏆 Plus bas historique : **{format_price(lowest, currency)}**\n",
        f"🔗 [Voir sur PSPrices]({game.get('url')})"
    ]
    embed.description = "\n".join(desc_lines)
    embed.set_footer(text="CheckPrice • Alerte automatique", icon_url="https://psprices.com/staticfiles/i/favicon/512.png")
    embed.timestamp = datetime.now(PARIS_TZ)
    return embed


def create_watchlist_embeds(games: List[Dict[str, Any]]) -> List[discord.Embed]:
    """Crée un ou plusieurs embeds pour afficher la liste des jeux surveillés."""
    if not games:
        empty_embed = discord.Embed(
            title="🎮 JEUX SURVEILLÉS (0)",
            description="Aucun jeu n'est actuellement surveillé.\nUtilise `/watch <url>` pour en ajouter un !",
            color=COLOR_MUTED
        )
        return [empty_embed]

    embeds = []
    chunk_size = 10  # Maximum 10 jeux par embed pour rester lisible et sous les limites Discord
    chunks = [games[i:i + chunk_size] for i in range(0, len(games), chunk_size)]

    for page_idx, chunk in enumerate(chunks):
        title = f"🎮 JEUX SURVEILLÉS ({len(games)})"
        if len(chunks) > 1:
            title += f" — Page {page_idx + 1}/{len(chunks)}"

        embed = discord.Embed(
            title=title,
            color=COLOR_PRIMARY
        )

        lines = []
        for g in chunk:
            name = g.get("name", "Inconnu")
            url = g.get("url", "")
            curr = format_price(g.get("current_price", 0.0), g.get("currency", "EUR"))
            lowest = format_price(g.get("lowest_price", 0.0), g.get("currency", "EUR"))
            disc = g.get("discount", 0)

            disc_badge = f" 🔥 **-{disc}%**" if disc > 0 else ""
            lines.append(f"**[{name}]({url})**{disc_badge}")
            lines.append(f"💰 {curr}")
            lines.append(f"🏆 Plus bas : {lowest}")
            lines.append("─────────────────────")

        # Retirer le dernier séparateur
        if lines and lines[-1] == "─────────────────────":
            lines.pop()

        embed.description = "\n".join(lines)
        embed.set_footer(text="CheckPrice • Données PSPrices", icon_url="https://psprices.com/staticfiles/i/favicon/512.png")
        embed.timestamp = datetime.now(PARIS_TZ)
        embeds.append(embed)

    return embeds


def create_daily_report_embed(results: Dict[str, Any]) -> discord.Embed:
    """
    Crée l'embed du rapport complet (analyse quotidienne ou manuelle).
    results contient :
      - 'total_games': int
      - 'promotions': list
      - 'hikes': list
      - 'unchanged': list
      - 'errors': list
      - 'timestamp': datetime
    """
    dt = results.get("timestamp") or datetime.now(PARIS_TZ)
    date_str = dt.strftime("%d/%m/%Y")
    hour_str = dt.strftime("%H:%M")

    total = results.get("total_games", 0)
    promotions = results.get("promotions", [])
    hikes = results.get("hikes", [])
    unchanged = results.get("unchanged", [])

    embed = discord.Embed(
        title=f"📊 ANALYSE PS STORE — {date_str}",
        color=COLOR_PROMO if promotions else COLOR_PRIMARY
    )

    body_lines = [
        f"🎮 **{total} jeux surveillés**\n",
        "━━━━━━━━━━━━━━"
    ]

    # Section des promotions détectées en priorité
    for item in promotions:
        game = item["game"]
        old_p = format_price(item["old_price"], game.get("currency", "EUR"))
        new_p = format_price(item["new_price"], game.get("currency", "EUR"))
        lowest_p = format_price(game.get("lowest_price", item["new_price"]), game.get("currency", "EUR"))
        disc = item.get("discount", 0)

        body_lines.append(f"**{game.get('name')}**")
        body_lines.append(f"{old_p} ➔ {new_p}")
        body_lines.append(f"🔥 PROMO -{disc} %")
        body_lines.append(f"💰 Nouveau prix : {new_p}")
        body_lines.append(f"🏆 Plus bas : {lowest_p}")
        body_lines.append("━━━━━━━━━━━━━━")

    # Section des hausses / fins de promo
    for item in hikes:
        game = item["game"]
        old_p = format_price(item["old_price"], game.get("currency", "EUR"))
        new_p = format_price(item["new_price"], game.get("currency", "EUR"))
        lowest_p = format_price(game.get("lowest_price", 0.0), game.get("currency", "EUR"))

        body_lines.append(f"**{game.get('name')}**")
        body_lines.append("🔺 Fin de promotion")
        body_lines.append(f"{old_p} ➔ {new_p}")
        body_lines.append(f"🏆 Plus bas : {lowest_p}")
        body_lines.append("━━━━━━━━━━━━━━")

    # Section des jeux inchangés
    for item in unchanged:
        game = item["game"]
        curr_p = format_price(game.get("current_price", 0.0), game.get("currency", "EUR"))
        lowest_p = format_price(game.get("lowest_price", 0.0), game.get("currency", "EUR"))

        body_lines.append(f"**{game.get('name')}**")
        body_lines.append(f"💰 {curr_p}")
        body_lines.append(f"🏆 Plus bas historique : {lowest_p}")
        body_lines.append("➡️ Aucun changement")
        body_lines.append("━━━━━━━━━━━━━━")

    # Synthèse en bas
    promo_count = len(promotions)
    unchanged_count = len(unchanged)
    hike_count = len(hikes)

    promo_text = f"📉 **{promo_count} nouvelle{'s' if promo_count > 1 else ''} promotion{'s' if promo_count > 1 else ''}**" if promo_count > 0 else "📉 **0 nouvelle promotion**"
    unchanged_text = f"➡️ **{unchanged_count} prix inchangé{'s' if unchanged_count > 1 else ''}**"
    
    summary_lines = [
        promo_text,
        unchanged_text
    ]
    if hike_count > 0:
        summary_lines.append(f"🔺 **{hike_count} fin{'s' if hike_count > 1 else ''} de promotion**")

    summary_lines.append(f"🕐 Analyse effectuée à {hour_str}")

    body_lines.extend(summary_lines)

    # Discord impose 4096 caractères max pour la description d'un embed
    full_text = "\n".join(body_lines)
    if len(full_text) > 4000:
        embed.description = full_text[:3900] + "\n\n... *(liste tronquée pour taille Discord)*"
    else:
        embed.description = full_text

    embed.set_footer(text="CheckPrice • Rapport automatique PSPrices", icon_url="https://psprices.com/staticfiles/i/favicon/512.png")
    embed.timestamp = dt
    return embed
