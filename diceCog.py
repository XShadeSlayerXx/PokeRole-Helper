from discord.ext import commands

import random
import re
import math

maxDice = 20
maxPips = 100

diceSplit = re.compile(r'\d*d\d+')

class Dice(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name = 'roll',
        aliases = ['r'],
        help = 'Roll a d6. You can type \'!roll 3d6\' for example to change # of dice and/or # of faces',
        brief = '\'!roll\' or \'!roll 3d6\' for example'
    )
    async def rollDice(self, ctx, *, mc = ''):
        mc = mc.lower()
        if '+' in mc:
            place = mc.find('+')
            add = int(mc[1 + place:])
        else:
            add = None
        if mc != '':
            # are we rolling random dice?
            if re.search(diceSplit, mc) is not None:
                dice = mc.split('d')
                if dice[0] == '':
                    dice[0] = 1
                if add is not None:
                    place = dice[1].find('+')
                    dice[1] = dice[1][:place]
                dice[0] = sorted((1, int(dice[0]), maxDice))[1]
                dice[1] = sorted((2, int(dice[1]), maxPips))[1]
                total = [random.randrange(int(dice[1])) + 1 for _ in range(int(dice[0]))]
                rolled = f'{dice[0]}d{dice[1]}'
                numSuccesses = None
                if dice[1] == 6 and add is None:
                    msg = f'{rolled} -- '
                    numSuccesses = 0
                    for x in total:
                        if x < 4: #don't bold failed rolls
                            msg += str(x)
                        else: #bold successes
                            msg += f'**{str(x)}**'
                            numSuccesses += 1
                        msg += ', '
                    msg = msg[:-2]
                else:
                    msg = f'{rolled} -- {", ".join([str(x) for x in total])}'
                if add is not None:
                    msg += f' + {add} = {sum(total) + add}'
                if numSuccesses is not None:
                    msg += (f'\n{numSuccesses} Successes' if numSuccesses != 1 else f'\n{numSuccesses} Success')
                await ctx.send(msg)
        else:
            ran = random.randrange(6) + 1
            await ctx.send(f'{ran}')

def setup(bot):
    bot.add_cog(Dice(bot))