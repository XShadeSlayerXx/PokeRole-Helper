from discord.ext import commands

import random

# TODO: wanted final output:
#  Requested by: Pokemon
#  Objective: Recover their lost item
#  Reward: Money¥ + ??? (item, etc)
#  Difficulty: Starter - Master

quests = {
    'Rescue' : 'Rescue me!',
    'Deliver' : 'Bring me a {item}!',
    'Arrest' : 'Arrest the outlaw {pokemon}',
    'Find' : 'I\'ve lost my {item}, please retrieve it!'
}

class Quests(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(Quests(bot))