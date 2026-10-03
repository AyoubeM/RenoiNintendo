import logging
from typing import List
import discord
from discord import app_commands
from discord.ext import commands
from services.analyzer import PriceAnalyzer
from services.psprices import PSPricesService, extract_game_id_from_url, is_valid_psprices_url
from utils.embeds import create_game_embed
from utils.json_manager import get_game_by_id, load_games, update_game, get_current_paris_iso

logger = logging.getLogger("checkprice.commands.prix")


class PrixCommand(commands.Cog):
    """Commande pour consulter immédiatement le prix et l'analyse d'un jeu."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.psprices = PSPricesService()

    async def game_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplétion des jeux surveillés."""
        games = load_games()
        choices = []
        current_lower = current.lower()

        for g in games:
            name = g.get("name", "Inconnu")
            game_id = str(g.get("id"))
            display = f"{name} ({game_id})"
            display_short = (display[:97] + "...") if len(display) > 100 else display

            if not current or current_lower in name.lower() or current_lower in game_id:
                choices.append(app_commands.Choice(name=display_short, value=game_id))

            if len(choices) >= 25:
                break

        return choices

    @app_commands.command(
        name="prix",
        description="Vérifier immédiatement le prix et l'analyse d'un jeu"
    )
    @app_commands.describe(
        jeu="Sélectionne un jeu surveillé ou colle directement une URL PSPrices"
    )
    @app_commands.autocomplete(jeu=game_autocomplete)
    async def prix(self, interaction: discord.Interaction, jeu: str):
        await interaction.response.defer(thinking=True)

        target_game = None
        clean_input = jeu.strip()

        # 1. Vérifier si l'entrée est une URL directe
        if is_valid_psprices_url(clean_input):
            try:
                scraped = await self.psprices.fetch_game_data(clean_input)
                target_game = {
                    "id": scraped.get("id"),
                    "name": scraped.get("name"),
                    "url": clean_input,
                    "current_price": scraped.get("current_price"),
                    "previous_price": scraped.get("high_price"),
                    "lowest_price": scraped.get("lowest_price"),
                    "currency": scraped.get("currency", "EUR"),
                    "discount": scraped.get("discount", 0),
                    "last_checked": get_current_paris_iso(),
                    "image": scraped.get("image")
                }
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Erreur lors de la récupération des données PSPrices : {e}",
                    ephemeral=True
                )
                return

        # 2. Sinon chercher par ID dans les jeux surveillés
        if not target_game:
            target_game = get_game_by_id(clean_input)

        # 3. Sinon chercher par nom dans les jeux surveillés
        if not target_game:
            games = load_games()
            for g in games:
                if clean_input.lower() in g.get("name", "").lower():
                    target_game = g
                    break

        if not target_game:
            await interaction.followup.send(
                f"❌ Aucun jeu trouvé pour **{jeu}**.\n"
                "Choisis un jeu de la watchlist ou colle une URL PSPrices valide.",
                ephemeral=True
            )
            return

        # Analyse des données
        analysis = PriceAnalyzer.analyze_game(target_game)
        embed = create_game_embed(target_game, analysis)

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PrixCommand(bot))
