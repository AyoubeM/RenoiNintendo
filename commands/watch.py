import logging
import discord
from discord import app_commands
from discord.ext import commands
from services.analyzer import PriceAnalyzer
from services.psprices import PSPricesService, extract_game_id_from_url, is_valid_psprices_url
from utils.embeds import create_game_embed
from utils.json_manager import add_game, get_current_paris_iso, get_game_by_id, get_game_by_url

logger = logging.getLogger("checkprice.commands.watch")


class WatchCommand(commands.Cog):
    """Commande pour ajouter un jeu à la surveillance."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.psprices = PSPricesService()

    @app_commands.command(
        name="watch",
        description="Ajouter un jeu PSPrices à la liste de surveillance des prix"
    )
    @app_commands.describe(
        url="Lien de la page du jeu sur PSPrices (ex: https://psprices.com/region-fr/game/...)"
    )
    async def watch(self, interaction: discord.Interaction, url: str):
        # Différer la réponse car le scraping web peut prendre 1 à 2 secondes
        await interaction.response.defer(thinking=True)

        clean_url = url.strip()
        if not is_valid_psprices_url(clean_url):
            await interaction.followup.send(
                "❌ **Lien invalide.** Merci de fournir une URL de jeu valide issue de PSPrices.\n"
                "*Exemple : https://psprices.com/region-fr/game/4247730/unchartedtm-the-nathan-drake-collection*",
                ephemeral=True
            )
            return

        game_id = extract_game_id_from_url(clean_url)
        if not game_id:
            await interaction.followup.send(
                "❌ Impossible d'extraire l'identifiant du jeu depuis cette URL.",
                ephemeral=True
            )
            return

        # Vérifier si déjà surveillé
        if get_game_by_id(game_id) or get_game_by_url(clean_url):
            await interaction.followup.send("⚠️ Ce jeu est déjà surveillé.")
            return

        try:
            game_data = await self.psprices.fetch_game_data(clean_url)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de {clean_url}: {e}")
            await interaction.followup.send(
                f"❌ Impossible de récupérer les données du jeu sur PSPrices : {e}",
                ephemeral=True
            )
            return

        # Compléter avec date et prix précédent initial
        game_data["previous_price"] = game_data["current_price"]
        game_data["last_checked"] = get_current_paris_iso()

        success = add_game(game_data)
        if not success:
            await interaction.followup.send("⚠️ Ce jeu est déjà surveillé.")
            return

        # Générer l'embed de confirmation
        analysis = PriceAnalyzer.analyze_game(game_data)
        embed = create_game_embed(game_data, analysis)

        await interaction.followup.send(
            content=f"✅ Le jeu **{game_data.get('name')}** a été ajouté avec succès à la surveillance !",
            embed=embed
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(WatchCommand(bot))
