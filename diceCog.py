from discord.ext import commands
from dislash import slash_command, ActionRow, Button, ButtonStyle, ResponseType, Option, OptionType

import random
import re
import math

maxDice = 20
maxPips = 100

diceSplit = re.compile(r'\d*d\d+')

class Dice(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.timeout = 60 * 2

    async def dice_backend(self, ctx, *, mc = ''):
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
                        if x < 4: #don't bold failed rolls
                            msg += str(x)
                        else: #bold successes
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
                    await self.dice_backend(ctx, mc = f'{mc}d6')
                except:
                    pass
        else:
            ran = random.randrange(6) + 1
            return msg + f'a {ran}'


    @commands.command(
        name = 'roll',
        aliases = ['r'],
        help = 'Roll a d6. You can type \'!roll 3d6\' for example to change # of dice and/or # of faces',
        brief = '\'!roll\' or \'!roll 3d6\' for example'
    )
    async def rollDice(self, ctx, *, mc = ''):
        try:
            int(mc)
            mc = f'{mc}d6'
        except:
            pass
        msg = await self.dice_backend(ctx = ctx, mc = mc)

        button = [ActionRow(Button(
            style = ButtonStyle.gray,
            label = 'Roll Again',
            custom_id = 'reroll'
        ))]

        sent = await ctx.send(msg, components = button)

        on_click = sent.create_click_listener(timeout = self.timeout)
        button_owner = ctx.author.id

        @on_click.matching_id('reroll')
        async def on_matching_reroll(inter):
            if inter.author.id == button_owner:
                if inter.message.content.count('\n') > 6:
                    first = inter.message.content.index('\n')
                    final = inter.message.content[inter.message.content.index('\n', first+1)+1:]
                else:
                    final = inter.message.content
                extra = await self.dice_backend(ctx = ctx, mc = mc)
                final += '\n' + extra
                await sent.edit(content = final)
                await inter.reply(type = ResponseType.UpdateMessage)
            else:
                await inter.create_response(content = 'The Reroll button is reserved '
                                                      'for whoever ran the original message.',
                                            ephemeral = True)

        @on_click.timeout
        async def on_timeout():
            await sent.edit(components = [])

    async def dice_backend_slash(self, sides, dice, addition):
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

    @slash_command(
        name = 'roll',
        description = "Roll a single d6 by default. You can change the number of dice and/or the number of sides",
        options = [
            Option('dice', 'Number of dice to roll (up to 20)', OptionType.INTEGER),
            Option('sides', 'Number of sides each die has (up to 100)', OptionType.INTEGER),
            Option('flat_addition', 'Flat number to the roll', OptionType.INTEGER),
            Option('private', 'Send a private message to you in this chat? (default: False)', OptionType.BOOLEAN)
        ]
    )
    async def rollDice_slash(self, inter, sides : int = 6, dice : int = 1,
                             flat_addition : int = None, private : bool = False):
        dice = sorted((1, dice, maxDice))[1]
        sides = sorted((2, sides, maxPips))[1]

        msg = await self.dice_backend_slash(sides, dice, flat_addition)

        if private:
            sent = await inter.reply(msg, ephemeral = private)
        else:
            button = [ActionRow(Button(
                style = ButtonStyle.gray,
                label = 'Roll Again',
                custom_id = 'reroll'
            ))]

            # prefix = inter.author.display_name + ' rolled '
            sent = await inter.reply(msg, components = button)

            on_click = sent.create_click_listener(timeout = self.timeout)
            button_owner = inter.author.id

            @on_click.matching_id('reroll')
            async def on_matching_reroll(inter):
                if inter.author.id == button_owner:
                    if inter.message.content.count('\n') > 6:
                        first = inter.message.content.index('\n')
                        final = inter.message.content[inter.message.content.index('\n', first+1)+1:]
                    else:
                        final = inter.message.content
                    extra = await self.dice_backend_slash(sides, dice, flat_addition)
                    final += '\n' + extra
                    await sent.edit(content = final)
                    await inter.reply(type = ResponseType.UpdateMessage)
                else:
                    await inter.create_response(content = 'The Reroll button is reserved '
                                                          'for whoever ran the original message.',
                                                ephemeral = True)

            @on_click.timeout
            async def on_timeout():
                await sent.edit(components = [])

def setup(bot):
    bot.add_cog(Dice(bot))