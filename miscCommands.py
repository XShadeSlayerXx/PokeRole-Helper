from discord.ext import commands
import csv

class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.weather = dict()
        self.status = dict()

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

    @commands.command(name = 'weather',
                 aliases = ['w'],
                 help = 'Quick reference for the weather.\n'
                        'Type `%weather` for a list of all weather types, or'
                        'type `%weather sunny day` for example for an in-depth explanation.')
    async def weather(self, ctx, *, weather = ''):
        if len(self.weather) == 0:
            await self.instantiateWeather()
        output = ''
        weatherrepl = '\n\t- '
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
        await ctx.send(output)

    @commands.command(name = 'status',
                      help = 'Quick reference for statuses.\n'
                             'Type `%status` for a list of all statuses, or'
                             'type `%status burn` for example for an in-depth explanation.')
    async def status(self, ctx, *, status = ''):
        if len(self.status) == 0:
            await self.instantiateStatus()
        output = ''
        statusrepl = '\n\t- '
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
        await ctx.send(output)

def setup(bot):
    bot.add_cog(Misc(bot))