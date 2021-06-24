from discord.ext import commands
from dbhelper import Database
import typing, random
import pmd_quest_text as pmd

import random

# TODO: wanted final output:
#  Requested by: Pokemon
#  Objective: Recover their lost item
#  Reward: Money¥ + ??? (item, etc)
#  Difficulty: Starter - Master

# good sources: view-source:https://syphist.com/pmd/rt/wondermail.html
# view-source:https://web.archive.org/web/20080912161910/http://www.upokecenter.com/games/dungeon2/guides/wondermail.php
# prices: https://mysterydungeon.fandom.com/wiki/Explorers/Items

ranks = ['Starter', 'Beginner', 'Amateur', 'Ace', 'Pro', 'Master', 'Champion']
prices = [0, 50, 100, 1000, 2500, 4000, 4500]

quests = [
    [pmd.RescueTitle, pmd.Rescue, pmd.RescueP2],
    [pmd.FindSomeoneTitle, pmd.FindSomeone, pmd.FindSomeoneP2],
    [pmd.EscortTitle, pmd.Escort, pmd.EscortP2],
    [['I\'ve lost my {item}, please retrieve it!'], pmd.FindItem, pmd.FindItemP2],
    [[pmd.DeliverTitle, pmd.DeliverTitle2], pmd.FindItem, pmd.FindItemP2],
    [['{target} stole my {item}!'],['{target} is a thief!'], ['Help me get my {item} back!']],
    [['Arrest {target}!'],['{target} is a wanted criminal!'], ['Please bring {target} to justice!']]
]

def ensure_rank(arg : str) -> str:
    if arg.title() not in ranks:
        raise commands.errors.ConversionError(f'{arg} is not a valid rank.')
    return arg

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
        query = (self.db.custom_query(query))[0]

        avg_price = (price+upper_price)//2

        if not query:
            query = ('???', avg_price)
        else:
            query = (query[0], avg_price-int(query[1]))

        return query

    # in: quest parameters
    # out: estimated rank (Starter - Champion), item reward and/or money
    def estimate_reward(self, rank, price_lower, price_upper) -> str:
        item, price = self.get_item(price_lower, price_upper)
        output = item
        rand = random.random()
        if price > price_lower:
            if rand > .5:
                output += ' + ???'
            else:
                tmp = self.get_item(0, price)
                if tmp[0] == '???':
                    output += f' + {price//10}'
                else:
                    output += f' + {tmp[0]}'
        elif rand > .5:
            output += f' + {price//5}'
        return item

    def quest_output(self, client, difficulty, price_range) -> str:
        # get a random poke to deliver to/help/rescue/arrest/etc
        target_poke = self.get_poke(difficulty)
        item = (self.get_item(price_range[0], price_range[1]))[0]

        # determine objective based on difficulty,
        # and reward based on the type of quest + suggested item
        # objective = get_quest(target_poke, difficulty)
        objective = random.choice(quests)
        reward = self.estimate_reward(difficulty, price_range[0], price_range[1])

        # aggregate output
        output = f'__{random.choice(objective[0]).format(target = target_poke, item = item)}__\n' \
                 f'\t{random.choice(objective[1]).format(target = target_poke, item = item)}\n' \
                 f'\t{random.choice(objective[2]).format(target = target_poke, item = item)}\n'
        output += f'**Difficulty:** {difficulty}\n'
        output += f'**Client:** {client.title()}\n'
        output += f'**Reward:** {reward}'

        return output

    def quest_recursor(self, ctx, numQuests, rank, price,
                                      price_upper, mc):
        rank = rank.title()
        # get a random pokemon if none provided
        if mc == '':
            poke = self.get_poke(rank)
        #... otherwise select a random poke from the list
        else:
            poke = random.choice(mc)

        query = f'SELECT name FROM pkmnStats WHERE name="{poke.title()}"'
        query = self.db.custom_query(query)

        try:
            if not query:
                poke = random.choice(self.bot.expand_list(poke))
        except:
            query = f'SELECT name FROM pkmnStats WHERE name="{self.bot.dictionary(poke.title())}"'
            poke = (self.db.custom_query(query))[0][0]


        rank_as_num = ranks.index(rank)
        if price < 0:
            price = prices[rank_as_num]
        if price_upper < price:
            price_upper = price

        if numQuests > 5:
            numQuests = 5

        if numQuests == 0:
            return ''
        else:
            numQuests-=1

        tmp = self.quest_output(poke, rank, (price, price_upper))
        return tmp + '\n\n' + self.quest_recursor(ctx = ctx, numQuests = numQuests, rank = rank, price = price,
                                      price_upper = price_upper, mc = mc)

    @commands.command(
        name = 'quest',
        aliases = ['q'],
        help = 'Generate a Mystery Dungeon quest.\n'
               'Format: `%quest (numQuests) rank (price_lower_bound) (price_higher bound) (pokemon list)`\n'
               'Example: Generate 2 quests at beginner rank, with pmd items priced between 30 and 100 as rewards,\n'
               'where the client is possibly a Pikachu, Dwebble, or in the custom list called myPokemon.\n'
               '`%quest 2 beginner 30 100 Pikachu, Dwebble, myPokemon`\n'
               'Please note that any part left blank will be randomized within reason. This is a work in progress,\n'
               'so rewards are currently limited to a small pool.',
        brief = 'Generate a Mystery Dungeon quest.'
    )
    # example: %quest (numQuests) rank (price) (price2) (pkmnList)
    async def generate_quest(self, ctx,
                             numQuests : typing.Optional[int] = 1,
                             rank : ensure_rank = '',
                             price : typing.Optional[int] = -1,
                             price_upper : typing.Optional[int] = -1,
                             *, mc : (lambda x : x.split(', ')) = ''):
        msg = self.quest_recursor(ctx = ctx, numQuests = numQuests, rank = rank, price = price,
                                  price_upper = price_upper, mc = mc)
        await self.bot.big_msg(ctx, msg)


def setup(bot):
    bot.add_cog(Quests(bot))