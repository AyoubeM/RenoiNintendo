import json
import logging
import re
from typing import Any, Dict, Optional
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger("checkprice.psprices")

# Headers standards imitant un navigateur moderne pour respecter les règles de requête de PSPrices
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Not-A.Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}


def extract_game_id_from_url(url: str) -> Optional[str]:
    """Extrait l'identifiant numérique du jeu depuis une URL PSPrices."""
    match = re.search(r"/game/(?:buy/)?(\d+)", url)
    return match.group(1) if match else None


def is_valid_psprices_url(url: str) -> bool:
    """Vérifie si l'URL est une URL valide de jeu PSPrices."""
    if not url or not isinstance(url, str):
        return False
    clean_url = url.strip()
    return "psprices.com" in clean_url and bool(extract_game_id_from_url(clean_url))


def clean_price_value(val: Any) -> float:
    """Convertit une chaîne ou un nombre en valeur float propre."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    val_str = str(val).replace("\xa0", "").replace(" ", "").replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)", val_str)
    return round(float(match.group(1)), 2) if match else 0.0


def clean_game_name(raw_name: Optional[str]) -> str:
    """Nettoie le nom du jeu des symboles spéciaux superflus (marques déposées, etc.)."""
    if not raw_name:
        return "Jeu sans nom"
    cleaned = raw_name.replace("™", "").replace("®", "").replace("©", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class PSPricesService:
    """Service d'interaction avec le site PSPrices."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._external_session = session

    async def fetch_game_data(self, url: str) -> Dict[str, Any]:
        """
        Récupère et analyse les informations d'un jeu à partir de son URL PSPrices.
        Retourne un dictionnaire standardisé ou lève une exception en cas d'erreur.
        """
        if not is_valid_psprices_url(url):
            raise ValueError("L'URL fournie n'est pas une URL de jeu PSPrices valide.")

        game_id = extract_game_id_from_url(url)
        timeout = aiohttp.ClientTimeout(total=15)

        async def _do_request(sess: aiohttp.ClientSession):
            async with sess.get(url, headers=DEFAULT_HEADERS, timeout=timeout) as resp:
                if resp.status == 404:
                    raise ValueError("Page PSPrices introuvable (404). Vérifie le lien.")
                if resp.status == 403:
                    raise PermissionError("Accès refusé par PSPrices (403).")
                if resp.status != 200:
                    raise RuntimeError(f"Erreur HTTP PSPrices : {resp.status}")
                return await resp.text()

        if self._external_session and not self._external_session.closed:
            html = await _do_request(self._external_session)
        else:
            async with aiohttp.ClientSession() as session:
                html = await _do_request(session)

        return self._parse_game_page(html, url, game_id)

    def _parse_game_page(self, html: str, url: str, game_id: Optional[str]) -> Dict[str, Any]:
        """Extrait les métadonnées officielles JSON-LD et OpenGraph de la page PSPrices."""
        soup = BeautifulSoup(html, "html.parser")

        product_data: Optional[Dict[str, Any]] = None
        videogame_data: Optional[Dict[str, Any]] = None

        # Recherche des balises schema.org JSON-LD (données publiques officielles)
        for s in soup.find_all("script", type="application/ld+json"):
            if not s.string:
                continue
            try:
                parsed = json.loads(s.string)
                if isinstance(parsed, dict):
                    t = parsed.get("@type")
                    if t == "Product":
                        product_data = parsed
                    elif t == "VideoGame":
                        videogame_data = parsed
            except Exception:
                continue

        name = None
        image = None
        current_price = 0.0
        lowest_price = 0.0
        high_price = 0.0
        currency = "EUR"

        # 1. Extraction depuis VideoGame (prix actuel et devise)
        if videogame_data:
            name = videogame_data.get("name")
            offers = videogame_data.get("offers", {})
            if isinstance(offers, dict):
                current_price = clean_price_value(offers.get("price"))
                currency = offers.get("priceCurrency", currency) or currency

        # 2. Extraction depuis Product (prix plus bas, prix fort/normal, image)
        if product_data:
            if not name:
                name = product_data.get("name")
            image = product_data.get("image")
            offers = product_data.get("offers", {})
            if isinstance(offers, dict):
                lowest_price = clean_price_value(offers.get("lowPrice"))
                high_price = clean_price_value(offers.get("highPrice"))
                if not currency:
                    currency = offers.get("priceCurrency", currency) or currency

        # 3. Fallbacks OpenGraph et balises HTML
        if not name:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                name = og_title.get("content")
            elif soup.title and soup.title.string:
                name = soup.title.string.split("|")[0].split("·")[0].strip()

        if not image:
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                image = og_img.get("content")

        name = clean_game_name(name)

        # Si current_price n'a pas pu être récupéré via JSON-LD VideoGame, on cherche dans Product ou HTML
        if current_price == 0.0 and high_price > 0.0:
            # Vérifier si un prix en gras est présent dans la page
            current_price = high_price

        if lowest_price == 0.0 and current_price > 0.0:
            lowest_price = current_price

        # Calcul de la réduction actuelle
        discount = 0
        reference_price = high_price if high_price > 0 else current_price
        if reference_price > current_price > 0:
            discount = int(round((1 - (current_price / reference_price)) * 100))

        # Recherche de badge explicite de réduction dans le HTML si discount est 0
        if discount == 0:
            discount_badge = soup.find(string=re.compile(r"-\s*(\d{1,2})\s*%"))
            if discount_badge:
                m_disc = re.search(r"-\s*(\d{1,2})\s*%", discount_badge)
                if m_disc:
                    discount = int(m_disc.group(1))

        return {
            "id": game_id,
            "name": name,
            "url": url,
            "current_price": round(current_price, 2),
            "lowest_price": round(lowest_price, 2),
            "high_price": round(high_price, 2),
            "currency": currency,
            "discount": discount,
            "image": image
        }
