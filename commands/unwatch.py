import discord
from discord import app_commands
from discord.ext import commands
from typing import List
from utils.json_manager import load_games, remove_game, get_game_by_id


class UnwatchCommand(commands.Cog):
    """Commande pour supprimer un jeu de la surveillance."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
            # Limite Discord : 100 caractères max pour name et value
            display_short = (display[:97] + "...") if len(display) > 100 else display

            if not current or current_lower in name.lower() or current_lower in game_id:
                choices.append(app_commands.Choice(name=display_short, value=game_id))

            if len(choices) >= 25:  # Limite Discord
                break

        return choices

    @app_commands.command(
        name="unwatch",
        description="Supprimer un jeu de la liste de surveillance"
    )
    @app_commands.describe(
        jeu="Le jeu à retirer (choisis dans la liste ou renseigne son ID)"
    )
    @app_commands.autocomplete(jeu=game_autocomplete)
    async def unwatch(self, interaction: discord.Interaction, jeu: str):
        # Tenter d'abord par ID direct
        target_game = get_game_by_id(jeu)

        # Si pas trouvé par ID, chercher par nom exact ou partiel
        if not target_game:
            games = load_games()
            for g in games:
                if jeu.lower() == g.get("name", "").lower() or jeu == str(g.get("id")):
                    target_game = g
                    break

        if not target_game:
            await interaction.response.send_message(
                f"❌ Aucun jeu correspondant à **{jeu}** n'a été trouvé dans la liste de surveillance.",
                ephemeral=True
            )
            return

        game_id = str(target_game.get("id"))
        game_name = target_game.get("name")

        removed = remove_game(game_id)
        if removed:
            await interaction.response.send_message(
                f"🗑️ Le jeu **{game_name}** a été retiré de la surveillance."
            )
        else:
            await interaction.response.send_message(
                f"❌ Une erreur est survenue lors de la suppression de **{game_name}**.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(UnwatchCommand(bot))
