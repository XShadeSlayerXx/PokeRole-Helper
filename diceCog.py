from discord.ext import commands
from discord import app_commands, ButtonStyle, Member, Interaction
from discord.ui import button, Button, View
from discord.app_commands import Choice

import random
import re
import math

maxDice = 100
maxPips = 100

diceSplit = re.compile(r'\d*d\d+')

async def dice_backend(ctx, *, mc = ''):
    name = ctx.author.display_name
    msg = f'{name} rolled '
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
                msg += f'{rolled} -- '
                numSuccesses = 0
                for x in total:
                    if x < 4:  #don't bold failed rolls
                        msg += str(x)
                    else:  #bold successes
                        msg += f'**{str(x)}**'
                        numSuccesses += 1
                    msg += ', '
                msg = msg[:-2]
            else:
                msg += f'{rolled} -- {", ".join([str(x) for x in total])}'
            if add is not None:
                msg += f' + {add} = {sum(total) + add}'
            if numSuccesses is not None:
                msg += (f'\n{numSuccesses} Successes' if numSuccesses != 1 else f'\n{numSuccesses} Success')
            return msg
        else:
            try:
                int(mc)
                await dice_backend(ctx, mc = f'{mc}d6')
            except:
                pass
    else:
        ran = random.randrange(6) + 1
        return msg + f'a {ran}'

async def dice_backend_slash(sides, dice, addition):
    msg = ''
    if sides or dice or addition:
        # are we rolling random dice?
        total = [random.randrange(int(sides)) + 1 for _ in range(int(dice))]
        rolled = f'{dice}d{sides}'
        numSuccesses = None
        if sides == 6 and addition is None:
            msg += f'{rolled} -- '
            numSuccesses = 0
            for x in total:
                if x < 4: #don't bold failed rolls
                    msg += str(x)
                else: #bold successes
                    msg += f'**{str(x)}**'
                    numSuccesses += 1
                msg += ', '
            msg = msg[:-2] #remove trailing ', '
        else:
            msg += f'{rolled} -- {", ".join([str(x) for x in total])}'
        if addition is not None:
            msg += f' + {addition} = {sum(total) + addition}'
        if numSuccesses is not None:
            msg += (f'\n{numSuccesses} Successes' if numSuccesses != 1 else f'\n{numSuccesses} Success')
        return msg
    else:
        ran = random.randrange(6) + 1
        return msg + f'a {ran}'


class Dice(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.timeout = 60 * 2

    @commands.command(
        name = 'roll',
        aliases = ['r'],
        help = 'Roll a d6. You can type \'%roll 3d6\' for example to change # of dice and/or # of faces.\n'
               'You can also add notes for future reference like this: `%roll 3d6 # I am a note!`',
        brief = '\'!roll\' or \'!roll 3d6\' for example'
    )
    async def rollDice(self, ctx, *, mc = '', note = None):
        if not note:
            note = ''
        try:
            int(mc)
            mc = f'{mc}d6'
        except:
            if '#' in mc:
                try:
                    mc, note = mc.split('#', maxsplit = 2)
                except:
                    note = mc.replace('#', '')
                note = note.replace('\n', ' - ')[:500]
                note = note.strip()
                mc = mc.strip()
                note = f'*{note}*\n'
                await self.rollDice(ctx = ctx, mc = mc, note = note)
                return
        msg = await dice_backend(ctx = ctx, mc = mc)

        buttons = RerollButton(timeout = self.timeout,
                               note = note, mc = mc)
        await ctx.send(msg, view = buttons)


    @app_commands.command(
        name = 'roll',
        description = "Roll a single d6 by default. You can change the number of dice and/or the number of sides"
    )
    @app_commands.describe(
        dice = "Number of dice to roll (up to 100)",
        sides = "Number of sides each die has (up to 100)",
        flat_addition = "Add a flat number to the roll",
        note = "Add a note for future reference",
        private = "Send a private message to you in this chat? (default: False)"
    )
    @app_commands.choices(
        private = [
            Choice(name = 'Yes', value = 1),
            Choice(name = 'No', value = 0),
        ],
    )
    async def rollDice_slash(self, inter,
                             sides : app_commands.Range[int, 0, 100] = 6,
                             dice : app_commands.Range[int, 0, 100] = 1,
                             flat_addition : int = None,
                             note : str = '',
                             private : int = False):
        private = bool(private)
        dice = sorted((1, dice, maxDice))[1]
        sides = sorted((2, sides, maxPips))[1]

        msg = await dice_backend_slash(sides, dice, flat_addition)
        if note != '':
            note = f'*{note}*\n'
            msg = note + msg

        if not private:
            buttons = RerollButton(timeout = self.timeout,
                                   note = note, sides = sides, dice = dice, flat_addition = flat_addition)
        else:
            buttons = None
        await inter.response.send_message(msg, view = buttons, ephemeral = private)

class RerollButton(View):
    def __init__(self, *, timeout : int = 180,
                 note = None, sides = None, dice = None, flat_addition = None,
                 mc = None):
        super().__init__(timeout = timeout)
        self.note = note
        self.sides = sides
        self.dice = dice
        self.flat_addition = flat_addition
        self.mc = mc

    @button(label = "Roll Again", style = ButtonStyle.gray)
    async def reroll_button(self, interaction : Interaction, button : Button):
        if self.mc:
            extra = await dice_backend(self.mc)
            await interaction.send(extra)
        else:
            extra = await dice_backend_slash(self.sides, self.dice, self.flat_addition)
            await interaction.response.send_message(extra)


async def setup(bot):
    await bot.add_cog(Dice(bot))