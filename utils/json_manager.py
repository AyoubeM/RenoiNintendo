import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

PARIS_TZ = ZoneInfo("Europe/Paris")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
GAMES_FILE = DATA_DIR / "games.json"
HISTORY_FILE = DATA_DIR / "price_history.json"


def get_current_paris_iso() -> str:
    """Retourne la date et heure courante au fuseau Europe/Paris au format ISO."""
    return datetime.now(PARIS_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def ensure_data_files() -> None:
    """S'assure que le dossier data et les fichiers JSON existent."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not GAMES_FILE.exists():
        _atomic_write_json(GAMES_FILE, {"games": []})

    if not HISTORY_FILE.exists():
        _atomic_write_json(HISTORY_FILE, {})


def _atomic_write_json(file_path: Path, data: Any) -> None:
    """Écrit des données dans un fichier JSON de manière atomique pour éviter toute corruption."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(dir=file_path.parent, prefix="tmp_", suffix=".json")
    try:
        with open(temp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        shutil.move(temp_path, file_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def load_games() -> List[Dict[str, Any]]:
    """Charge la liste des jeux surveillés."""
    ensure_data_files()
    try:
        with open(GAMES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("games", [])
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_games(games: List[Dict[str, Any]]) -> None:
    """Sauvegarde la liste des jeux surveillés."""
    ensure_data_files()
    _atomic_write_json(GAMES_FILE, {"games": games})


def get_game_by_id(game_id: str) -> Optional[Dict[str, Any]]:
    """Trouve un jeu surveillé par son identifiant PSPrices."""
    games = load_games()
    for g in games:
        if str(g.get("id")) == str(game_id):
            return g
    return None


def get_game_by_url(url: str) -> Optional[Dict[str, Any]]:
    """Trouve un jeu surveillé par son URL."""
    games = load_games()
    clean_target = url.strip().rstrip("/").lower()
    for g in games:
        if g.get("url", "").strip().rstrip("/").lower() == clean_target:
            return g
    return None


def add_game(game_data: Dict[str, Any]) -> bool:
    """
    Ajoute un jeu à games.json s'il n'existe pas déjà.
    Retourne True si ajouté, False si déjà présent.
    """
    games = load_games()
    game_id = str(game_data.get("id"))

    for g in games:
        if str(g.get("id")) == game_id:
            return False

    # Structure attendue
    new_game = {
        "id": game_id,
        "name": game_data.get("name", "Jeu Inconnu"),
        "url": game_data.get("url", ""),
        "current_price": float(game_data.get("current_price", 0.0)),
        "previous_price": float(game_data.get("previous_price", game_data.get("current_price", 0.0))),
        "lowest_price": float(game_data.get("lowest_price", game_data.get("current_price", 0.0))),
        "currency": game_data.get("currency", "EUR"),
        "discount": int(game_data.get("discount", 0)),
        "last_checked": game_data.get("last_checked", get_current_paris_iso()),
        "image": game_data.get("image", None)
    }

    games.append(new_game)
    save_games(games)

    # Initialiser également l'historique
    add_price_history_entry(
        game_id=game_id,
        price=new_game["current_price"],
        discount=new_game["discount"],
        date_iso=new_game["last_checked"]
    )
    return True


def update_game(game_id: str, updated_fields: Dict[str, Any]) -> bool:
    """Met à jour les informations d'un jeu surveillé."""
    games = load_games()
    game_id_str = str(game_id)
    updated = False

    for i, g in enumerate(games):
        if str(g.get("id")) == game_id_str:
            games[i].update(updated_fields)
            updated = True
            break

    if updated:
        save_games(games)
    return updated


def remove_game(game_id: str) -> bool:
    """Supprime un jeu surveillé par son identifiant."""
    games = load_games()
    game_id_str = str(game_id)
    initial_len = len(games)

    games = [g for g in games if str(g.get("id")) != game_id_str]
    if len(games) < initial_len:
        save_games(games)
        return True
    return False


def load_history() -> Dict[str, List[Dict[str, Any]]]:
    """Charge l'ensemble de l'historique des prix."""
    ensure_data_files()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_history(history: Dict[str, List[Dict[str, Any]]]) -> None:
    """Sauvegarde l'ensemble de l'historique des prix."""
    ensure_data_files()
    _atomic_write_json(HISTORY_FILE, history)


def get_game_history(game_id: str) -> List[Dict[str, Any]]:
    """Retourne l'historique des prix pour un jeu donné."""
    history = load_history()
    return history.get(str(game_id), [])


def add_price_history_entry(
    game_id: str,
    price: float,
    discount: int = 0,
    date_iso: Optional[str] = None
) -> bool:
    """
    Ajoute une entrée dans price_history.json UNIQUEMENT si le prix a changé
    ou si l'historique était vide pour ce jeu.
    Retourne True si une nouvelle entrée a été enregistrée, False sinon.
    """
    history = load_history()
    game_id_str = str(game_id)

    if game_id_str not in history:
        history[game_id_str] = []

    game_entries = history[game_id_str]
    price_val = round(float(price), 2)

    # Règle d'or : ne pas enregistrer si le prix est identique au dernier prix connu
    if game_entries:
        last_price = round(float(game_entries[-1].get("price", 0.0)), 2)
        if last_price == price_val:
            return False

    new_entry = {
        "date": date_iso or get_current_paris_iso(),
        "price": price_val,
        "discount": int(discount)
    }

    game_entries.append(new_entry)
    history[game_id_str] = game_entries
    save_history(history)
    return True
