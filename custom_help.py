from discord.ext import commands

cmd_list = {}
spacing = 12

# todo: allow %help to recognize command aliases

class Help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        global cmd_list
        for cmd in self.bot.walk_commands():
            cmd_list[cmd.name] = cmd

    def get_cmd_signature(self, cmd):
        result = []
        prefix = '/'
        if len(cmd.aliases) > 0:
            aliases = '|'.join(cmd.aliases)
            fmt = '{0}[{1.name}|{2}]'
            result.append(fmt.format(prefix, cmd, aliases))
        else:
            name = prefix + cmd.name
            result.append(name)

        params = cmd.params.copy()
        if len(params) > 0:
            for name, param in params.items():
                if name in ['ctx', 'self']:
                    continue
                if param.default is not param.empty:
                    # We don't want None or '' to trigger the [name=value] case and instead it should
                    # do [name] since [name=None] or [name=] are not exactly useful for the user.
                    should_print = param.default if isinstance(param.default, str) else param.default is not None
                    if should_print:
                        result.append('[{}={}]'.format(name, param.default))
                    else:
                        result.append('[{}]'.format(name))
                elif param.kind == param.VAR_POSITIONAL:
                    result.append('[{}...]'.format(name))
                else:
                    result.append('<{}>'.format(name))

        return ' '.join(result)

    def brief_help_msg(self, cmd):
        end = 40
        add = ''
        if cmd.help is None:
            return
        if len(cmd.help) > end:
            tmp = cmd.help.find(' ', int(end * 1 / 2))
            tmp2 = cmd.help.find('\n')
            if tmp2 < tmp:
                tmp = tmp2
            if tmp < end and tmp != -1:
                end = tmp
            add = '...'
        return cmd.help[:end] + add

    def big_help_msg(self, cmd):
        output = self.get_cmd_signature(cmd)
        output += '\n\n'
        output += cmd.help
        return output

    @commands.hybrid_command(
        name = 'help'
    )
    async def help(self, ctx, *,which : str = None):
        global cmd_list
        global spacing
        if not which:

            custom_categories = {
                'Reference' : sorted(['ability', 'move', 'pokelearns',
                                      'stats', 'shop', 'item', 'weather', 'status', 'rank']),
                'Lists' : sorted(['filter', 'list', 'lists', 'listsub']),
                'Encounters' : sorted(['encounter', 'wEncounter', 'random', 'hEncounter']),
                'Misc': sorted([
                    'docs', 'donate', 'feedback', 'settings', 'tracker', 'roll',
                    'dungeon', 'habitat', 'quest', 'metronome', 'viewhabitat',
                    'forms'
                ])
            }
            output = '```\n'

            for category, cmds in custom_categories.items():
                output += f'{category}:\n'
                for cmd in cmds:
                    output += f'  {cmd:{spacing}}{self.brief_help_msg(cmd_list[cmd])}\n'
            output += f'\nType /help command for more info on a command.\n'
        else:
            output = f'```\n{self.big_help_msg(cmd_list[which])}\n'
        output += '```\n'

        await ctx.send(output[:1998])

async def setup(bot):
    bot.remove_command('help')
    await bot.add_cog(Help(bot))