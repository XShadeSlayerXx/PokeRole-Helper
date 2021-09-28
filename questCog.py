from discord.ext import commands
from dislash import slash_command, Option, OptionChoice, OptionType
from dbhelper import Database
import typing, math
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
        self.socials = [x[0] for x in self.bot.socials[:]]
        self.skills = [x[0] for x in self.bot.skills[:]]
        self.attributes = ['Strength', 'Dexterity', 'Vitality', 'Special', 'Insight']
        self.special_attributes = ['Lucky', 'Magic']
        self.fabric_types = ['Mouth Piece', 'Band', 'Scarf', 'Ribbon', 'Belt', 'Necklace', 'Hat']

    def cog_unload(self):
        self.db.connection.close()

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

    def get_prefix(self, lst):
        output = {}
        for name in lst:
            if name in output:
                output[name]+=1
            else:
                output[name]=1
        outstr = ''
        for item, value in list(output.items()):
            outstr += f'{item}{("+" + str(value)) if value > 1 else ""}, '
        return outstr[:-2] #truncate the trailing ', '

    def get_stat_equipment(self, price_lower, price_higher):
        # price for 1 social: 50, 1 skill: 100, 2 random skills: 600, 1 attribute: 1000, 2 socials: 1200,
        # 3 random skills: 2000, 2 attributes: 2400, 4 random skills: 3000

        #Note: removing everything above 2 socials for potential balance reasons.
        item = random.choice(self.fabric_types) + ' of '
        new_price = (price_lower + price_higher) // 2
        rand = random.random()
        if new_price < 60 or rand < .1:
            item += random.choice(self.socials)
            new_price -= 50
        elif new_price < 110 or rand < .2:
            item += random.choice(self.skills)
            new_price -= 100
        elif new_price < 510 or rand < .3:
            item += self.get_prefix([random.choice(self.skills) for _ in range(2)])
            new_price -= 500
        elif new_price < 1010 or rand < .4:
            item += random.choice(self.attributes)
            new_price -= 1000
        elif new_price < 1210 or rand < .5:
            item += self.get_prefix([random.choice(self.socials) for _ in range(2)])
            new_price -= 1200
        else:
            item = random.choice(self.special_attributes) + ' ' + random.choice(self.fabric_types)
            new_price -= 2000
        # elif new_price < 2010 or rand < .35:
        #     item += self.get_prefix([random.choice(self.skills) for _ in range(3)])
        #     new_price -= 2000
        # elif new_price < 2410 or rand < .4:
        #     item += self.get_prefix([random.choice(self.attributes) for _ in range(2)])
        #     new_price -= 2400
        # elif new_price < 3010:
        #     item += self.get_prefix([random.choice(self.skills) for _ in range(4)])
        #     new_price -= 3000
        return item, new_price

    # in: quest parameters
    # out: estimated rank (Starter - Champion), item reward and/or money
    def estimate_reward(self, include_garmets, price_lower, price_upper) -> str:
        if include_garmets and random.random() < .2:
            item, price = self.get_stat_equipment(price_lower, price_upper)
        else:
            item, price = self.get_item(price_lower, price_upper)
        output = item
        rand = random.random()
        vary = random.random() + .5
        if price > price_lower:
            if rand > .5 or price == 0:
                output += ' + ???'
            else:
                tmp, tmp_price = self.get_item(0, price)
                if tmp == '???':
                    output += f' + {math.ceil(price/10) * vary} PoKé'
                else:
                    output += f' + {tmp}'
        elif rand > .5:
            tmp = math.ceil(price/2 * vary)
            if tmp > 0:
                output += f' + {tmp} PoKé'
            else:
                output += f' + ???'
        return output

    def quest_output(self, garmets, client, difficulty, price_range) -> str:
        # get a random poke to deliver to/help/rescue/arrest/etc
        target_poke = self.get_poke(difficulty)
        item = (self.get_item(price_range[0]//4, int(price_range[1])))[0]

        # determine objective based on difficulty,
        # and reward based on the type of quest + suggested item
        # objective = get_quest(target_poke, difficulty)
        objective = random.choice(quests)
        reward = self.estimate_reward(garmets, price_range[0], price_range[1])

        # aggregate output
        output = f'__{random.choice(objective[0]).format(target = target_poke, item = item)}__\n' \
                 f'\t{random.choice(objective[1]).format(target = target_poke, item = item)}\n' \
                 f'\t{random.choice(objective[2]).format(target = target_poke, item = item)}\n'
        output += f'**Difficulty:** {difficulty}\n'
        output += f'**Client:** {client.title()}\n'
        output += f'**Reward:** {reward}'

        return output

    def quest_recursor(self, ctx, numQuests, include_garmets, rank, price,
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

        tmp = self.quest_output(include_garmets, poke, rank, (price, price_upper))
        return tmp + '\n\n' + self.quest_recursor(ctx = ctx, numQuests = numQuests, include_garmets = include_garmets,
                                                  rank = rank, price = price, price_upper = price_upper, mc = mc)

    @commands.command(
        name = 'quest',
        aliases = ['q', 'quests'],
        help = 'Generate a Mystery Dungeon quest.\n'
               'Format: `%quest (numQuests) (include_garmets) rank (price_lower_bound) (price_higher bound) (pokemon list)`\n'
               'Example: Generate 2 quests at beginner rank, with pmd items priced between 30 and 100 as rewards,\n'
               'where the client is possibly a Pikachu, Dwebble, or in the custom list called myPokemon. Do not include garmets.\n'
               '`%quest 2 False beginner 30 100 Pikachu, Dwebble, myPokemon`\n'
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
        include_garmets = False
        msg = self.quest_recursor(ctx = ctx, numQuests = numQuests, include_garmets = include_garmets, rank = rank,
                                  price = price, price_upper = price_upper, mc = mc)
        await self.bot.big_msg(ctx, msg)

    @slash_command(
        name = 'quest',
        description = 'Generate some quests at a rank, from [pokemon]!',
        options = [
            Option('number', 'How many? (up to 5)', OptionType.INTEGER, choices = [
                OptionChoice(str(x), x) for x in range(1, 6)
            ]),
            Option('rank', 'What rank?', OptionType.STRING, choices = [
                OptionChoice(x, x) for x in ranks
            ]),
            Option('pokemon', "Which pokemon?", OptionType.STRING)
        ]
    )
    async def generate_quest_slash(self, inter, number : int = 1, rank : str = '', pokemon : str = ''):
        if rank == '':
            rank = self.bot.rank_dist()
        pokemon = pokemon.split(', ')
        price = prices[ranks.index(rank)]
        msg = ''
        for _ in range(number):
            # get a random pokemon if none provided
            if pokemon == ['']:
                poke = self.get_poke(rank)
            #... otherwise select a random poke from the list
            else:
                poke = random.choice(pokemon)

            query = f'SELECT name FROM pkmnStats WHERE name="{poke.title()}"'
            query = self.db.custom_query(query)

            try:
                if not query:
                    poke = random.choice(self.bot.expand_list(poke))
            except:
                query = f'SELECT name FROM pkmnStats WHERE name="{self.bot.dictionary(poke.title())}"'
                poke = (self.db.custom_query(query))[0][0]


            msg += '\n' + self.quest_output(False, poke, rank, (price, price)) + '\n'
        await self.bot.big_msg(inter, msg)

    @generate_quest.error
    async def q_error(self, ctx, error):
        await ctx.send('Don\'t forget to state the quest rank! (Starter, Beginner, Amateur, Ace, Pro)')


def setup(bot):
    bot.add_cog(Quests(bot))