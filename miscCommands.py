import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
import csv

statuses = [
    'Burn 1',
    'Burn 2',
    'Burn 3',
    'Paralysis',
    'Frozen Solid',
    'Poison',
    'Badly Poisoned',
    'Sleep',
    'Flinched',
    'Confused',
    'Disabled',
    'In Love',
    'Blocked'
]
weathers = [
    'Sunny Weather',
    'Harsh Sunlight Weather',
    'Rain Weather',
    'Typhoon Weather',
    'Sandstorm Weather',
    'Strong Winds Weather',
    'Hail Weather',
    'Fog/Darkness',
    'Muddy',
    'On Fire!',
    'Electric Poles'
]

natures = [
    'Adamant',
    'Bashful',
    'Bold',
    'Brave',
    'Calm',
    'Careful',
    'Docile',
    'Gentle',
    'Hardy',
    'Hasty',
    'Impish',
    'Jolly',
    'Lax',
    'Lonely',
    'Mild',
    'Modest',
    'Naive',
    'Naughty',
    'Quiet',
    'Quirky',
    'Rash',
    'Relaxed',
    'Sassy',
    'Serious',
    'Timid'
]

async def send_msg(context, msg):
    if isinstance(context, discord.Interaction):
        await context.response.send_message(msg)
    else:
        await context.send(msg)

class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.weather = dict()
        self.status = dict()
        self.nature = dict()

    async def instantiateWeather(self):
        # 0 is name, 1 is description, 2 is effect
        with open('weather.csv', 'r', encoding = "UTF-8") as file:
            reader = csv.reader(file)
            for row in reader:
                self.weather[row[0]] = row[1:]

    async def instantiateStatus(self):
        with open('status.csv', 'r', encoding = "UTF-8") as file:
            reader = csv.reader(file)
            for row in reader:
                self.status[row[0]] = row[1:]

    async def instantiateNature(self):
        with open('nature.csv', 'r', encoding = "UTF-8") as file:
            reader = csv.reader(file)
            for row in reader:
                self.nature[row[0]] = row[1:]

    # @commands.command(name = 'weather',
    #              aliases = ['w'],
    #              help = 'Quick reference for the weather.\n'
    #                     'Type `%weather` for a list of all weather types, or'
    #                     'type `%weather sunny day` for example for an in-depth explanation.')
    async def weather_func(self, ctx, *, weather = ''):
        if len(self.weather) == 0:
            await self.instantiateWeather()
        output = ''
        weatherrepl = '\n- '
        if weather == '':
            #list all weather
            for k, v in list(self.weather.items()):
                output += f'**{k}**{weatherrepl}*{v[0]}*\n'
        else:
            #list a single weather description
            weather = weather.title()
            if f'{weather} Weather' in self.weather:
                weather += ' Weather'
            if weather in self.weather:
                effect = self.weather[weather][1].replace('. ', '.'+weatherrepl)
                output = f'**{weather}**:\n*{self.weather[weather][0]}*{weatherrepl}{effect}'
            else:
                output = f'`{weather}` wasn\'t found in the weather list:{weatherrepl}'\
                         + weatherrepl.join([str(k) for k in self.weather.keys()])
        await send_msg(ctx, output)

    # @commands.command(name = 'status',
    #                   help = 'Quick reference for statuses.\n'
    #                          'Type `%status` for a list of all statuses, or'
    #                          'type `%status burn` for example for an in-depth explanation.')
    async def status_func(self, ctx, *, status = ''):
        if len(self.status) == 0:
            await self.instantiateStatus()
        output = ''
        statusrepl = '\n- '
        if status == '':
            #list all status
            for k, v in list(self.status.items()):
                output += f'**{k}**{statusrepl}*{v[0]}*\n'
        else:
            #list a single status description
            status = status.title()
            if status == 'Burn':
                status += ' 1'
            if status in self.status:
                effect = ''
                for stat in self.status[status][1:]:
                    effect += f'{statusrepl}__{stat.replace(":","__:", 1)}'
                # effect = statusrepl.join(self.status[status][1:])
                output = f'**{status}**\n*{self.status[status][0]}*{effect}'
            else:
                output = f'`{status}` wasn\'t found in the status list:{statusrepl}' \
                         + statusrepl.join([str(k) for k in self.status.keys()])
        await send_msg(ctx, output)


    # @commands.command(name = 'nature',
    #              aliases = ['n'],
    #              help = 'Quick reference for natures.\n'
    #                     'Type `%nature` for a list of all natures, or'
    #                     'type `%nature bold` for example for an in-depth explanation.')
    async def nature_func(self, ctx, *, nature = ''):
        if len(self.nature) == 0:
            await self.instantiateNature()
        output = ''
        naturerepl = '\n'
        if nature == '':
            #list all nature
            for k, v in list(self.nature.items()):
                output += f'**{k}**{naturerepl}\t-*{v[0]}*\n'
        else:
            #list a single nature description
            nature = nature.title()
            if nature in self.nature:
                effect = self.nature[nature][1]
                output = f'**{nature}**\n*{self.nature[nature][0]}*{naturerepl}\n{effect}'
            else:
                output = f'`{nature}` wasn\'t found in the nature list:{naturerepl}'\
                         + naturerepl.join([str(k) for k in self.nature.keys()])
        await send_msg(ctx, output)


    @commands.hybrid_command(
        name = 'status',
        description = "A nice long nap...",
        help = 'Quick reference for statuses.\n'
             'Type `%status` for a list of all statuses, or'
             'type `%status burn` for example for an in-depth explanation.'
    )
    @app_commands.describe(
        status = "Which status?"
    )
    @app_commands.choices(
        status = [
            Choice(name = x, value = x) for x in list(statuses)
        ]
    )
    async def slash_status(self, inter : discord.Interaction, *, status : str):
        await self.status_func(ctx = inter, status = status)


    @commands.hybrid_command(
        name = 'weather',
        description = "Are those clouds?",
        help = 'Quick reference for the weather.\n'
            'Type `%weather` for a list of all weather types, or'
            'type `%weather sunny day` for example for an in-depth explanation.'
    )
    @app_commands.describe(
        weather = "Which weather?"
    )
    @app_commands.choices(
        weather = [
            Choice(name = x, value = x) for x in list(weathers)
        ]
    )
    async def slash_weather(self, inter, *, weather : str):
        await self.weather_func(ctx = inter, weather = weather)


    @commands.hybrid_command(
        name = 'nature',
        description = "Who am I?",
        help = 'Quick reference for natures.\n'
            'Type `%nature` for a list of all natures, or'
            'type `%nature bold` for example for an in-depth explanation.'
    )
    @app_commands.describe(
        nature = "Which nature?"
    )
    @app_commands.choices(
        nature = [
            Choice(name = x, value = x) for x in list(natures)
        ]
    )
    async def slash_nature(self, inter, *, nature : str):
        await self.nature_func(ctx = inter, nature = nature)

async def setup(bot):
    await bot.add_cog(Misc(bot))