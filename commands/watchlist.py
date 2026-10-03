import discord
from discord import app_commands
from discord.ext import commands
from utils.embeds import create_watchlist_embeds
from utils.json_manager import load_games


class WatchlistCommand(commands.Cog):
    """Commande pour afficher la liste des jeux surveillés."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="watchlist",
        description="Afficher tous les jeux actuellement surveillés et leurs prix"
    )
    async def watchlist(self, interaction: discord.Interaction):
        games = load_games()
        embeds = create_watchlist_embeds(games)

        # Si un seul embed, on l'envoie directement
        if len(embeds) == 1:
            await interaction.response.send_message(embed=embeds[0])
        else:
            # Plusieurs pages si la liste est longue
            await interaction.response.send_message(embed=embeds[0])
            for extra_embed in embeds[1:]:
                await interaction.followup.send(embed=extra_embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(WatchlistCommand(bot))
