from discord.ext import commands
from dbhelper import Database
import typing, random

import random

#TODO: the actual command needs to go in the .py file, if only because of List expansion...

# TODO: wanted final output:
#  Requested by: Pokemon
#  Objective: Recover their lost item
#  Reward: Money¥ + ??? (item, etc)
#  Difficulty: Starter - Master

# Therefore...
# TODO:
#  add items to the database so we can reference them here
#  and query their prices and rarities and whatnot

# good sources: view-source:https://syphist.com/pmd/rt/wondermail.html
# view-source:https://web.archive.org/web/20080912161910/http://www.upokecenter.com/games/dungeon2/guides/wondermail.php
# prices: https://mysterydungeon.fandom.com/wiki/Explorers/Items

ranks = ['Starter', 'Beginner', 'Amateur', 'Ace', 'Pro', 'Master', 'Champion']
# TODO: fix prices, these are arbitrary :(
prices = [50, 100, 150, 200, 300, 600, 1000]

quests = {
    'Rescue' : 'Rescue me!',
    'Deliver' : 'Bring me a {item}!',
    'Arrest' : 'Arrest the outlaw {pokemon}',
    'Find' : 'I\'ve lost my {item}, please retrieve it!'
}

def ensure_rank(arg : str) -> str:
    if arg.title() not in ranks:
        raise commands.errors.ConversionError(f'{arg} is not a valid rank.')
    return arg

def choose_mission_text(obj):
    output = 'tmp_mission'
    return output

# input: difficulty
# output: list( objective, optional objective 1, etc )
def get_quest(difficulty):
    output = 'tmp_quest'
    return output

def expand_objective(obj):
    pass

class Quests(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    # get random poke from the given rank
    # TODO: should this include gen 8+?
    def get_poke(self, rank):
        query = f'SELECT name FROM pkmnStats WHERE rank="{rank}"' \
                f' AND generation BETWEEN 1 AND 8 ORDER BY RANDOM() LIMIT 1'

        return (self.db.custom_query(query))[0][0]

    # in: price range
    # out: random item (if no item in range choose random from lower bracket)
    def get_item(self, price, upper_price = -1):
        query = "SELECT name, pmd_price FROM pkmnItems WHERE CAST(pmd_price as integer)"
        if upper_price < 1:
            upper_price = 1
        if abs(upper_price - price) < 50:
            price -= 50
            upper_price += 50
        if price < 1:
            price = 1
        query += f' BETWEEN {price} AND {upper_price} ORDER BY RANDOM() LIMIT 1'
        query = self.db.custom_query(query)

        if not query:
            query = ('???', None)
        else:
            query = query[0]

        return query

    # in: quest parameters
    # out: estimated rank (Starter - Champion), item reward and/or money
    def estimate_reward(self, quest_type, client_rank, item, target_poke = None) -> str:
        #TODO: this
        return item[0]

    def quest_output(self, client, difficulty, price_range) -> str:
        # get a random poke to deliver to/help/rescue/arrest/etc
        target_poke = self.get_poke(difficulty)
        item = self.get_item(price_range[0], price_range[1])

        # determine objective based on difficulty,
        # and reward based on the type of quest + suggested item
        objective = get_quest(target_poke, difficulty)
        reward = self.estimate_reward(objective, difficulty, item, target_poke)

        # aggregate output
        output = f'{choose_mission_text(objective)}\n'
        output += f'**Client:** {client}\n'
        output += f'**Objective:** {expand_objective(objective)}\n'
        output += f'**Difficulty:** {difficulty}\n'
        output += f'**Reward:** {reward}'

        return output

    @commands.command(
        name = 'quest',
        aliases = ['q'],
        help = 'Generate a Mystery Dungeon quest.\n'
               '...',
        brief = 'Generate a Mystery Dungeon quest.'
    )
    # example: %quest (numQuests) rank (price) (price2) (pkmnList)
    async def generate_quest(self, ctx,
                             numQuests : typing.Optional[int] = 1,
                             rank : ensure_rank = '',
                             price : typing.Optional[int] = -1,
                             price_upper : typing.Optional[int] = -1,
                             *, mc : (lambda x : x.split(', ')) = ''):
        rank = rank.title()
        # get a random pokemon if none provided
        if mc == '':
            poke = self.get_poke(rank)
        #... otherwise select a random poke from the list
        else:
            poke = random.choice(mc)

        query = f'SELECT name FROM pkmnStats WHERE name="{poke.title()}"'
        query = self.db.custom_query(query)

        if not query:
            poke = random.choice(self.bot.expand_list(poke))

        rank_as_num = ranks.index(rank)
        if price < 0:
            price = prices[rank_as_num]
        if price_upper < price:
            price_upper = price

        if numQuests > 5:
            numQuests = 5

        numQuests -= 1
        if numQuests > -1:
            await ctx.send(self.quest_output(poke, rank, (price, price_upper)))
            await self.generate_quest(ctx = ctx, numQuests = numQuests, rank = rank, price = price,
                                      price_upper = price_upper, mc = mc)


def setup(bot):
    bot.add_cog(Quests(bot))