import csv
import os
import pickle
import random
import re
import typing
import sys
import traceback

import discord
from discord.ext import commands
from dotenv import load_dotenv
from symspellpy import SymSpell, Verbosity
# can be replaced when/if i ever convert to nosql
from collections import OrderedDict as ODict
import requests
from numpy.random import choice
from bisect import bisect

from dbhelper import Database

load_dotenv()
token = os.getenv('POKEROLE_TOKEN')

#for my testing environment
dev_env = (True if len(sys.argv) > 1 else False)

cmd_prefix = ('./' if dev_env else '%')

bot = commands.Bot(command_prefix = cmd_prefix)

#note that 'custom help' needs to load last
cogs = ['mapCog', 'diceCog', 'miscCommands', 'questCog', 'custom_help']

#TODO: compress more of the data in working memory
#   ++PokeLearns ranks complete
#   Need:
#   --PokeLearns moves (probably index the movelist and change all moves in pokelearns to an index?)

#settings {channel : [(shiny_chance, int), (ability, int), (secondary, int), (hidden, int),
# (show_encounter_move_desc, 0)]}
pokebotsettings = dict()

#status list
pokeStatus = dict()

#pokemon moves
pkmnMoves = dict()
pkmnHabitats = dict()
pkmnWeather = dict()
database = None
restartError = True

ranks = ['Starter', 'Beginner', 'Amateur', 'Ace', 'Pro', 'Master', 'Champion']
rankBias = [1, 3, 5, 7, 9, 10, 11]
natures = ['Hardy (9)','Lonely (5)','Brave (9)','Adamant (4)','Naughty (6)',
           'Bold (9)','Docile (7)','Relaxed (8)','Impish (7)',
           'Lax (8)', 'Timid (4)', 'Hasty (7)', 'Serious (4)', 'Jolly (10)',
           'Naive (7)', 'Modest (10)', 'Mild (8)', 'Quiet (5)', 'Bashful (6)',
           'Rash (6)', 'Calm (8)', 'Gentle (10)', 'Sassy (7)', 'Careful (5)', 'Quirky (9)']

bot.socials = [('Tough', 1), ('Cool', 1), ('Beauty', 1), ('Clever', 1), ('Cute', 1)]
bot.skills = [('Brawl', 0), ('Channel', 0), ('Clash', 0), ('Evasion', 0),
          ('Alert', 0), ('Athletic', 0), ('Nature', 0), ('Stealth', 0),
          ('Allure', 0), ('Etiquette', 0), ('Intimidate', 0), ('Perform', 0)]

#total attributes at a rank (base/social)
#attributes are limited by poke
attributeAmount = (0, 2, 4, 6, 8, 8, 14)
#total skill points at a rank
skillAmount = (5, 9, 12, 14, 15, 15, 16)
#highest any single skill can be
limit = (1, 2, 3, 4, 5, 5, 5)

#lists are global...
#   pokemon list:
#{listName : [list] }
#   item list:
#{listName : [ 'i', [chance, item1, item2], [chance2, item3, item4], ... ]
pkmnLists = dict()

pokecap = re.compile(r'(^|[-( ])\s*([a-zA-Z])')
pokeweight = re.compile(r'(\d+)%?,? ([\-\'\.():,\sA-z]+)(?= \d|$)')
alpha_str = re.compile(r'[^\w_, \-]+')

#...but need access privileges
#{user : [listName list] }
pkmnListsPriv = dict()

#add the dictionaries
poke_dict = SymSpell()
poke_dict.load_dictionary('PokeDictionary.txt', 0, 1, separator = '$')

#github stuff for updating the lists
github_base = 'https://raw.githubusercontent.com/XShadeSlayerXx/PokeRole-Discord.py-Base/master/'
github_files = [
    ('PokeRoleItems.csv', 'UTF-8'),
    ('PokeRoleAbilities.csv', 'UTF-8'),
    ('PokeRoleItems.csv', 'UTF-8'),
    ('pokeMoveSorted.csv', 'UTF-8'),
    ('PokeLearnMovesFull.csv', 'UTF-8'),
    ('PokeroleStats.csv', 'WINDOWS-1252'),
]

# save and load functions
def save_obj(obj: object, name: str):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

# list of dictionary files
files = [('pkmnLists', pkmnLists), ('pokebotsettings', pokebotsettings), ('pkmnListsPriv', pkmnListsPriv),
         ('pokeStatus', pokeStatus)]

@bot.event
async def on_ready():
    global pkmnLists
    global pokebotsettings
    global pkmnListsPriv
    global database
    global restartError

    database = Database()

    print(f'{bot.user} has connected to Discord! A part of {len(bot.guilds)} servers!')

    await bot.change_presence(activity = discord.Game(name = 'with wild pokemon!'))

    if not hasattr(bot, 'appinfo'):
       bot.appinfo = await bot.application_info()

    random.seed()

    # load the files
    for file in files:
        # check if saved data exists
        if os.path.isfile('{0}.pkl'.format(file[0])):
            # save the data if the file exists
            try:
                file[1].update(load_obj(file[0]))
            except:
                file[1] = load_obj(file[0])
            print(file[0] + ' info loaded!')
            # store the newly loaded data into a backup
            save_obj(file[1], file[0] + "_backup")
        else:
            print('file ' + file[0] + ' not found, creating file')
            tempf = open(file[0] + ".pkl", "w")
            tempf.close()
            save_obj(file[1], file[0])
    await instantiateHabitatsList()

    if not dev_env:
        await bot.appinfo.owner.send(f'Connected Successfully')
    restartError = False

#######
#converters

def sep_weights(arg) -> str:
    return re.findall(pokeweight, arg)

def sep_biomes(arg) -> list:
    arg = arg.title()
    biomes = set()
    last = 0
    marker = arg.find(', ')
    while marker != -1:
        for pkmn in pokesFromBiome(arg[last:marker]):
            biomes.add(pkmn)
        last = marker + 2 #ignore the comma and space
        marker = arg.find(', ', marker+1)
    #check from marker to end arg[marker:]
    for pkmn in pokesFromBiome(arg[last:]):
        biomes.add(pkmn)
    return list(biomes)

def ensure_rank(arg : str) -> str:
    arg = arg.title()
    if arg not in ranks and arg not in ['Base', 'Random']:
        raise commands.errors.ConversionError(f'{arg} is not a valid rank.')
    return arg

def pkmn_cap(arg : str) -> str:
    return re.sub(pokecap , lambda p: p.group(0).upper(), arg)

#######
#helper functions

def lookup_poke(arg : str) -> str:
    suggestion =  poke_dict.lookup(arg, Verbosity.CLOSEST, max_edit_distance = 2,
                     include_unknown = True)[0]
    return suggestion.term

async def send_big_msg(ctx, arg : str, codify : bool = False):
    if codify:
        arg = arg.replace('`','') #remove all backticks since they're irrelevant
        arg = arg.replace('*__','-')
        arg = arg.replace('__','')
        arg = arg.replace('*','')
    while arg != '' and arg != []:
        try:
            last_newline = arg.rindex('\n', 5, 1990)
        except:
            last_newline = 1990
        if codify:
            msg = f'```{arg[:last_newline]}```'
        else:
            msg = arg[:last_newline]
        await ctx.send(msg)
        #plus 1 to go over the '\n'
        arg = arg[last_newline+1:]

def returnWeights(pokestr : str) -> list:
    try:
        int(pokestr[0])
    except:
        pokestr = '100 '+pokestr
    temp = re.findall(pokeweight, pokestr)
    output = []
    for x in temp:
        toAdd = [int(x[0])]
        for y in x[1].strip(',').split(', '):
            toAdd.append(pkmn_cap(y))
        output.append(toAdd)
    return output

def modifyList(which : bool, pokeToAddDel : list, listname : str):
    #which True is 'add', False, is 'del'
    newOdds = [elem[0] for elem in pokeToAddDel]
    listOdds = [elem[0] for elem in pkmnLists[listname][1:]]
    bad = []
    for i, odds in enumerate(newOdds):
        try:
            index = listOdds.index(odds) + 1
        except:
            index = None
        if which: #add elements
            if index is not None and pokeToAddDel[i][1] != 'None':
                for elem in pokeToAddDel[i][1:]:
                    pkmnLists[listname][index].append(elem)
            else:
                #append everything, guarantee the percent first
                pkmnLists[listname].append(pokeToAddDel[i])
        else: #remove elements
            if pokeToAddDel[i][1] == 'None' and index is not None:
                del pkmnLists[listname][index]
            elif index is not None:
                for elem in pokeToAddDel[i][1:]:
                    try:
                        pkmnLists[listname][index].remove(elem)
                    except:
                        bad.append(elem)
            else:
                bad.append(str(odds)+'%')
    #remove duplicates and balance percentages
    percent_total = 0
    none_index = -1
    none_amt = 0
    for i in range(1,len(pkmnLists[listname])):
        percent_total += pkmnLists[listname][i][0]
        if pkmnLists[listname][i][0] == 'None':
            none_index = i
            none_amt = pkmnLists[listname][i][0]
        else:
            pkmnLists[listname][i][1:] = list(set(pkmnLists[listname][i][1:]))
    if percent_total > 100:
        #theres 'None' in the list
        if none_index != -1:
            none_sub = percent_total - 100
            none_amt -= none_sub
            #more percent added than none amount left
            if none_amt <= 0:
                percent_total = -none_amt + 100
                del pkmnLists[listname][none_index]
                #spread the cost above 100
                for i in range(1,len(pkmnLists[listname])):
                    pkmnLists[listname][i][0] = int(round(pkmnLists[listname][i][0]/percent_total*100))
            else:
                #theres enough 'None' to eat the cost
                pkmnLists[listname][none_index][0] -= none_sub
        else:
            for i in range(1,len(pkmnLists[listname])):
                pkmnLists[listname][i][0] = int(round(pkmnLists[listname][i][0]/percent_total*100))
    elif percent_total < 100:
        if none_index != -1:
            pkmnLists[listname][none_index][0] += 100-percent_total
        else:
            pkmnLists[listname].append([100-percent_total, 'None'])
    return bad

def displayList(listname : str) -> str:
    output = ''
    #remove the leading 'i' or 'p'
    for elemList in pkmnLists[listname][1:]:
        output += str(elemList[0]) + '% ' + ', '.join(map(str,elemList[1:])) + ' '
    return output[:-1] #remove the trailing space

async def getGuilds(ctx):
    try:
        guild = ctx.guild.id
    except:
        guild = ctx.author.id
    if guild not in pokebotsettings:
        await instantiateSettings(guild)
    return guild

def pokesFromList(listname : str) -> list:
    output = []
    #skip the 'i' or 'p'
    for lists in pkmnLists[listname][1:]:
        #skip the percentage
        for poke in lists[1:]:
            output.append(poke)
    return output

def getStatus(statustype : str) -> str:
    statustype = statustype.split()[0].lower()
    if statustype in ['burn','burned']:
        return '🔥'#'\N{FIRE}'
    elif statustype in ['badly','poison','poisoned']:
        return '🟢'#'\N{GREEN_CIRCLE}'
    elif statustype in ['love','infatuation']:
        return '❤️'#'\N{HEART}'
    elif statustype in ['paralyzed', 'paralysis']:
        return '⚡'#'\N{ZAP}'
    elif statustype == 'frozen':
        return '❄️'#'\N{SNOWFLAKE}'
    elif statustype == 'confused':
        return '💫'#'\N{SPARKLES}'
    elif statustype == 'leech':
        return '🌱'#'\N{SEEDLING}'
    return '🗡️'#'\N{DAGGER}'

def pokesFromBiome(name : str) -> list:
    biomes = set()
    if name.endswith('Biomes'):
        for biome in pkmnHabitats[name]:
            for pkmn in pkmnHabitats[biome]:
                biomes.add(pkmn)
    else:
        for pkmn in pkmnHabitats[name]:
            biomes.add(pkmn)
    return biomes

#######
#decorators

def dev():
    def predicate(ctx):
        return dev_env
    return commands.check(predicate)

#######

async def send_owner_msg(msg = '', fp = None):
    tmp = await bot.application_info()
    if fp:
        await tmp.owner.send(msg, file = discord.File(fp))
    else:
        await tmp.owner.send(msg)

@commands.is_owner()
@bot.command(name = 'restart', hidden = True)
async def restart(ctx):
    await ctx.message.add_reaction('\N{HIBISCUS}')
    await bot.close()

@commands.is_owner()
@bot.command(name = 'guilds', hidden = True)
async def guildcheck(ctx):
    # once the bot hits 75 servers I want to verify it
    # I'm curious of the growth
    await ctx.send(f'Currently in {len(bot.guilds)} guilds.')

# @commands.is_owner()
# @bot.command(name = 'checkdata', hidden = True)
# async def integrityChecks(ctx, which : typing.Optional[int] = 0):
#     #0 is all, 1 is stats, 2 is moves, 3 is learnables, 4 is habitats
#
#     #stats first
#     errors = []
#     if which in [0,1]:
#         if len(pkmnStats) == 0:
#             await instantiatePkmnStatList()
#         for pokemon, stats in list(pkmnStats.items()):
#             newName = pkmn_cap(pokemon)
#             if pokemon != newName:
#                 errors.append((pokemon, ' stats name mismatch'))
#             try:
#                 await pkmnlearnshelper(newName)
#             except:
#                 errors.append((newName, ' not found stats -> learnables'))
#             #check abilities
#             for x in range(15,18):
#                 if stats[x] != '':
#                     try:
#                         await pkmnabilitieshelper(stats[x])
#                     except:
#                         errors.append((pokemon, f' ability {stats[x]}'))
#
#     #moves next
#     if which in [0,2]:
#         if len(pkmnMoves) == 0:
#             await instantiatePkmnMoveList()
#         for move, info in list(pkmnMoves.items()):
#             if move.title() != move:
#                 errors.append((move, ' move name mismatch'))
#
#     #learnables now
#     if which in [0,3]:
#         if len(pkmnLearns) == 0:
#             await instantiatePkmnLearnsList()
#         for pokemon, stats in list(pkmnLearns.items()):
#             newName = pkmn_cap(pokemon)
#             if pokemon != newName:
#                 errors.append((pokemon, ' learn name mismatch'))
#             try:
#                 await pkmnstatshelper(newName)
#             except:
#                 errors.append((newName, ' not found learnables -> stats'))
#             for move in stats[::2]:
#                 try:
#                     await pkmnmovehelper(move)
#                 except:
#                     errors.append((pokemon, f' move {move} not found'))
#
#     msg = '\n'.join([f'{x} {y}' for x,y in errors if not x.startswith('Delta')])
#     #print(msg)
#     if ctx is not None:
#         await send_big_msg(ctx, msg)
#     else:
#         print(msg)

@commands.is_owner()
@bot.command(name = 'checkfuncs', hidden = True)
async def functionChecks(ctx, which : typing.Optional[int] = 0):
    funcs = [[pkmn_search_ability, {'abilityname':'Static'}, 'ability'],
             [pkmn_search_stats, {'pokemon':'Bulbasaur'}, 'stats'],
             [pkmn_search_move, {'movename':'Tackle'}, 'move'],
             [pkmn_search_learns, {'pokemon':'Bulbasaur'}, 'learns'],
             [pkmn_search_item, {'itemname':'Pokeball'}, 'items'],
             [pkmn_search_habitat, {'habitat':'Tide Pools'}, 'habitat'],
             [pkmn_search_encounter, {'pokelist':['Bulbasaur,', 'Charmander,', 'Squirtle']}, 'enc'],
             [weighted_pkmn_search, {'pokelist': [(100, 'Bulbasaur, Charmander, Squirtle')]}, 'w enc']]

    errors = []

    oldV1, oldV2 = pokebotsettings[ctx.author.id][4], pokebotsettings[ctx.author.id][5]
    pokebotsettings[ctx.author.id][4], pokebotsettings[ctx.author.id][5] = False, False

    for x in range(2):
        if which == 0:
            for y in funcs:
                try:
                    await y[0](ctx, **y[1])
                except:
                    errors.append(y[2])
        else:
            try:
                func = funcs[which-1]
                await func[0](ctx, **func[1])
            except:
                print(traceback.print_exc())
                errors.append(func[2])

    pokebotsettings[ctx.author.id][4], pokebotsettings[ctx.author.id][5] = oldV1, oldV2
    if errors:
        await ctx.send('Errors:\n'+'\n'.join([error for error in errors]))
    else:
        await ctx.send('**Passed!**')

@commands.is_owner()
@bot.command(name = 'reloadCog', hidden = True)
async def reloadCogs(ctx):
    for mycog in cogs:
        bot.reload_extension(mycog)

@commands.is_owner()
@bot.command(name = 'updateLists', hidden = True)
async def reloadLists(ctx):
    global database
    for cog in cogs:
        bot.unload_extension(cog)
    for file in github_files:
        r = requests.get(github_base+file[0])
        with open(file[0], 'w', encoding = file[1]) as f:
            r = r.text.replace('\r\n', '\n')
            f.write(r)
    database.reloadLists()
    for cog in cogs:
        bot.load_extension(cog)
    await ctx.message.add_reaction('\N{CYCLONE}')

@commands.is_owner()
@bot.command(name = 'updateSettings', hidden = True)
async def updateSettings(ctx):
    try:
        for place in pokebotsettings:
            await instantiateSettings(place)
    except:
        tmp = traceback.format_exc(limit = 3)
        await send_owner_msg(msg = tmp)

@commands.is_owner()
@bot.command(name = 'devQuery', hidden = True)
async def query(ctx, *, msg = ''):
    try:
        if len(msg.split()) == 1:
            returned = database.custom_query(f"PRAGMA table_info({msg})")
            await ctx.send(', '.join([x[1] for x in returned]))
            return
        elif msg == '':
            returned = database.custom_query('SELECT name FROM sqlite_master WHERE type="table" AND name NOT LIKE "SQLITE_%"')
            await ctx.send(', '.join([x[0] for x in returned]))
            return
        returned = database.custom_query(msg)
        if returned is None:
            await ctx.send('Error: no results')
            return
        if len(returned[0]) == 1:
            returned = ', '.join([x[0] for x in returned])
        else:
            returned = ', '.join([f'**{str(x[0])}**: {list(x[1:])}' for x in returned])
        await send_big_msg(ctx, returned)
    except:
        try:
            surplus = returned
        except:
            surplus = ''
        await ctx.send('Error: Bad or Empty Request\n'+str(surplus))

#######

@bot.command(name = 'docs',
             help = '--> A link to an easy to read file <--')
async def docs(ctx):
    await ctx.send('https://github.com/XShadeSlayerXx/PokeRole-Discord.py-Base/blob/master/PokeRoleBot-Docs.MD')

#######

#[ability1, ability2, ability3, shiny, show_move_desc, show ability desc, the item list used in encounter,
# display lists pokemon by rank or odds]
async def instantiateSettings(where : str):
    defaults = [50,49,1,.00012, True, True, False, True, False, 0, False]
    if where not in pokebotsettings:
        pokebotsettings[where] = defaults
        return
    size = len(pokebotsettings[where])
    pokebotsettings[where] += defaults[size:]
    save_obj(pokebotsettings, 'pokebotsettings')

@bot.command(name = 'settings', aliases = ['setting'],
             help = '%settings <setting_name> [value]\n'
                    'e.g. %settings ability_one_chance 50\n'
                    'List: (ability_one_chance value)\n'
                    '(ability_two_chance value)\n'
                    '(ability_hidden_chance value)\n'
                    '(shiny_chance value)\n'
                    '(pre_evo_moves Yes/No/Lower)\n'
                    '(code_block True/False)\n'
                    '(show_move_description True/False)\n'
                    '(encounter_item <listname>)\n'
                    '(display_list Rank/Odds)\n'
                    '(random_rolls True/False)')
async def settings(ctx, setting='', value=''):
    msg = ''
    try:
        guild = ctx.guild.id
    except:
        guild = ctx.author.id
    try:
        pokebotsettings[guild]
    except:
        await instantiateSettings(guild)
    try:
        if setting == 'ability_one_chance':
            pokebotsettings[guild][0] = float(value)
        elif setting == 'ability_two_chance':
            pokebotsettings[guild][1] = float(value)
        elif setting == 'ability_hidden_chance':
            pokebotsettings[guild][2] = float(value)
        elif setting == 'shiny_chance':
            pokebotsettings[guild][3] = float(value)
    except:
        await ctx.send('This setting may be any real number, set it to 0 to disable the chance (write it as 50, not 50%)')
    if setting == 'show_move_description' or setting[0:9] == 'show_move':
        if value[0].lower() == 't':
            pokebotsettings[guild][4] = True
        elif value[0].lower() == 'f':
            pokebotsettings[guild][4] = False
        else:
            await ctx.send('Setting "show_move_description" may only be True or False')
    elif setting == 'show_ability_description' or setting == 'show_ability':
        if value[0].lower() == 't':
            pokebotsettings[guild][5] = True
        elif value[0].lower() == 'f':
            pokebotsettings[guild][5] = False
        else:
            await ctx.send('Setting "show_ability_description" may only be True or False')
    elif setting == 'encounter_item' or setting == 'item':
        if value in pkmnLists and pkmnLists[value][0] == 'i':
            pokebotsettings[guild][6] = value
        else:
            pokebotsettings[guild][6] = False
            msg += f'{value} not found in the custom item list. Capitalization matters, is it misspelled?\n' \
                   f'Default set to False (no items).\n'
    elif setting == 'display_list':
        if not value[0].lower() == 'r': # set it to show odds
            pokebotsettings[guild][7] = False
        else: #set it to show rank
            pokebotsettings[guild][7] = True
    elif setting == 'random_rolls':
        if value[0].lower() == 't':
            pokebotsettings[guild][8] = True
        elif value[0].lower() == 'f':
            pokebotsettings[guild][8] = False
    elif setting in ['pre_evo_moves', 'pre_evo', 'evo_moves']:
        if value[0].lower() in ['y', 't', 's']:
            pokebotsettings[guild][9] = 0 # new behaviour
        elif value[0].lower() in ['n', 'f', 'd']:
            pokebotsettings[guild][9] = 1 # old behaviour
        elif value[0].lower() == 'l':
            pokebotsettings[guild][9] = 2 # lower rank pre-evo
        else:
            await ctx.send('Setting "pre_evo_moves" may be True, False, or Lower (Rank Pre-Evo Moves)')
    elif setting in ['code', 'block', 'code_block']:
        if value[0].lower() in ['y', 't']:
            pokebotsettings[guild][10] = True
        else:
            pokebotsettings[guild][10] = False
    temp = pokebotsettings[guild]
    if temp[9] == 0:
        pre_evo='Same Rank'
    elif temp[9] == 1:
        pre_evo='No'
    else:
        pre_evo='Lower Rank'
    await ctx.send(f'{msg}'
                   f'Current settings:\n(Ability1/Ability2/AbilityHidden)\n**{temp[0],temp[1],temp[2]}**\n'
                   f'Shiny chance: {temp[3]} out of 1, **{temp[3]*100}%**\n'
                   f'Allow previous evolution moves in `%encounter`? **{pre_evo}**\n'
                   f'Display `%encounter` text in a code block format: **{temp[10]}\n**'
                   f'Show move descriptions in %encounter: **{temp[4]}**\n'
                   f'Show ability description in %encounter: **{temp[5]}**\n'
                   f'Items in %encounter? **{temp[6]}**\n'
                   f'display_list by odds or rank? **{temp[7]}**\n'
                   f'arbitrary encounter random_rolls? **{temp[8]}**\n'
                   f'\n"%help settings" for help')
    save_obj(pokebotsettings, 'pokebotsettings')

#######

@commands.is_owner()
@bot.command(name = 'update_settings', hidden = True)
async def update_settings(ctx):
    for key, val in pokebotsettings.items():
        await instantiateSettings(key)
        for value in range(len(val)):
            pokebotsettings[key][value] = val[value]
    save_obj(pokebotsettings, 'pokebotsettings')
    await ctx.send('Good to go')

# def reformatList(listname):
#     if len(pkmnLists[listname]) == 0:
#         del pkmnLists[listname]
#         return
#     #the first element should be either 'i' or 'p'
#     if pkmnLists[listname][0] not in ['i', 'p']:
#         temp = pkmnLists[listname][:]
#         pkmnLists[listname] = [None, None] #two slots
#         pkmnLists[listname][0] = ('p' if lookup_poke(temp[0]) in pkmnStats else 'i')
#         pkmnLists[listname][1] = [100] + [x for x in temp]
#     #fix directly for item lists, such that
#     #['i', [40, (i1, i2, i3)], [60, (i4, i5, i6)]] --> ['i', [40, i1, i2, i3], ...]
#     if pkmnLists[listname][0] == 'i':
#         for i in range(1,len(pkmnLists[listname][1:])+1):
#             if isinstance(pkmnLists[listname][i][1], str):
#                 continue
#             pkmnLists[listname][i] = [pkmnLists[listname][i][0]] + [x for x in pkmnLists[listname][i][1]]


# @commands.is_owner()
# @bot.command(name = 'update_lists', hidden = True)
# async def update_lists(ctx):
#     if len(pkmnStats) == 0:
#         await instantiatePkmnStatList()
#     for key, val in list(pkmnLists.items()):
#         # print('before: ',key, val)
#         reformatList(key)
#         # if key in pkmnLists:
#         #     print('after: ',key, pkmnLists[key])
#     await ctx.send('Done')
#     save_obj(pkmnLists, 'pkmnLists')

@commands.is_owner()
@bot.command(name = 'listoverride', hidden = True)
async def pkmn_list_override(ctx, listname, who : discord.Member):
    who = who.id
    #if '@' in who:
    #    if who[0] == '<':
    #        who = int(who[3:-1])
    #    else:
    #        who = int(who)
    try:
        pkmnListsPriv[who].append(listname)
    except:
        pkmnListsPriv[who] = [listname]
    await ctx.message.add_reaction('\N{CYCLONE}')
    save_obj(pkmnListsPriv, 'pkmnListsPriv')

#######

@bot.command(name = 'lists', help = 'Displays all the lists people have made in the format:\n- list1 (#) / list2 (#)\n')
async def show_lists(ctx):
    msg = ''
    mymsg = ''
    up = True
    myUp = True
    permissibleLists = pkmnListsPriv[ctx.author.id]
    for x, y in pkmnLists.items():
        howMany = sum([len(z)-1 for z in y[1:]])
        if x in permissibleLists:
            mymsg += ('\n - ' if myUp else ' / ') + f'{x} ({str(howMany)}{" "+y[0] if y[0] == "i" else ""})'
            myUp = not myUp
        else:
            msg += ('\n - ' if up else ' / ') + f'{x} ({str(howMany)}{" "+y[0] if y[0] == "i" else ""})'
            up = not up
    if mymsg != '':
        msg = mymsg + '\n-----------\n' + msg
    await send_big_msg(ctx, msg)

@bot.command(name = 'list', aliases=['l'], help = '%list <listname> (add/show/del) poke1, poke2, etc\n'
                                   'or %list <listname> (add/show/del) 43% item1, item2, 10% item3, item4, etc\n'
                                   'In this case, the remaining 47% is no item, for %encounter and %random purposes.\n'
                                   'Lists are unique to people - don\'t forget everyone can see them!\n'
                                   'Use "%list <listname> access @mention" to give edit permissions to someone\n'
                                   'Their user id will also work (right click their profile --> copy id)')
async def pkmn_list(ctx, listname : str, which = 'show', *, pokelist = ''):
    #areListsBroken = [x for x in list(pkmnLists.keys())]
    try:
        #initialize pkmnstats and check if listname is a valid pokemon
        await pkmnstatshelper(listname)
        await ctx.send('Lists may not be named after pokemon')
        return
    except:
        pass
    try:
        await pkmnitemhelper(listname)
        await ctx.send('Lists may not be named after items')
        return
    except:
        pass
    isItem = False
    try:
        if listname in pkmnLists and pkmnLists[listname][0] == 'i':
            isItem = True
    except:
        pass
    #make sure the author is registered, regardless of what they do
    if ctx.author.id not in pkmnListsPriv:
        pkmnListsPriv[ctx.author.id] = set()
    #is this a task that looks at the pokelist parameter?
    if which not in ['access', 'show']:
        #split up the pokelist argument into separate bits... 'bulbasaur' --> [(100, 'bulbasaur')]
        try:
            pokelist = [[int(pokelist), 'None']]
        except:
            pokelist = returnWeights(pokelist)
            #pokelist = [pkmn_cap(x.strip()) for x in pokelist.replace(',','').split(' ')]
            bad = []
            correct = []
            tempmsg = ''
            #item or pokemon?
            isItem = True
            try:
                if database.query_table('pkmnStats', 'name', pokelist[0][1]):
                #if lookup_poke(pokelist[0][1]) not in pkmnStats:
                    isItem = False
            except:
                #hopefully empty bc 'del', 'show', etc
                pass

            if not isItem:
                #check for misspelled pokemon...
                whichList = True
            else:
                #...or misspelled items
                whichList = False

            #for pokelist in the passed in str
            for y in pokelist:
                #remove the percentage amount
                y = y[1:]
                #for pokemon in the list
                for x in y:
                    if x == '':
                        #sometimes an empty string gets through
                        pokelist.remove('')
                        continue
                    try:
                        database.query_table('pkmnItems', 'name', x)
                        tmp = True
                    except:
                        tmp = False
                    if not whichList and not tmp:
                        bad.append(x)
                        if x in pkmnLists:
                            tempmsg+=f'{x} : '+', '.join(pkmnLists[x])+'\n'
                        elif not isItem:
                            correct.append(lookup_poke(x))
                    if whichList:
                        try:
                            database.query_table('pkmnStats', 'name', x)
                        except:
                            bad.append(x)
                            if x in pkmnLists:
                                tempmsg+=f'{x} : '+', '.join(pkmnLists[x])+'\n'
                            elif not isItem:
                                correct.append(lookup_poke(x))
            if len(bad) > 0 and which in ['add', 'remove', 'del']:
                if tempmsg != '':
                    tempmsg ='Right now, you can\'t have a list inside of a list:\n'+tempmsg
                for name in range(len(bad)):
                    #this doesnt always work, especially if the word is too far from the real one
                    tempmsg += (f'{bad[name]}' if isItem else f'{bad[name]} --> {correct[name]}') + '  |  '
                await ctx.send(f'{tempmsg[:-4]}\n(Pokemon with multiple forms may not show correctly)\n'
                               f'The list "{listname}" was not changed.')
                return
    if listname not in pkmnLists and pokelist != '':
        pkmnLists[listname] = []
        if isItem:
            pkmnLists[listname].append('i')
        else:
            pkmnLists[listname].append('p')
        if ctx.author.id in pkmnListsPriv:
            pkmnListsPriv[ctx.author.id] = set(pkmnListsPriv[ctx.author.id])
            pkmnListsPriv[ctx.author.id].add(listname)
        else:
            pkmnListsPriv[ctx.author.id] = set([listname])
    if which == 'show':
        if listname in pkmnLists and len(pkmnLists[listname]) > 0:
            #is it an item?
            if pkmnLists[listname][0] == 'i':
                msg = displayList(listname)
                await ctx.send(msg)
            else:
                #...not an item
                guild = await getGuilds(ctx)
                if pokebotsettings[guild][7]:
                    await ctx.send(await pkmnRankListDisplay(f'__{listname}__',listname))
                else:
                    await ctx.send(f'__{listname}__\n'+displayList(listname))
        else:
            await ctx.send(f'List {listname} is empty')
    elif listname in pkmnListsPriv[ctx.author.id]:
        #need permissions for these commands
        if which == 'add':
            modifyList(True, pokelist, listname)
            await pkmn_list(ctx = ctx, listname = listname, which = 'show')
        elif which in ['del', 'delete', 'remove']:
            if not pokelist or pokelist == ['']:
                #if there are no pokemon delete the list
                msg = displayList(listname)
                del pkmnLists[listname]
                await send_big_msg(ctx, f'Everything ({msg}) was removed from list "{listname}"')
            else:
                msg = modifyList(False, pokelist, listname)
                if len(msg) > 0:
                    await ctx.send(f'There was a problem removing: {", ".join(msg)}.\nPokemon still in list:')
            await pkmn_list(ctx, listname, 'show')
        elif which == 'access':
            #i could probably use the User converter but ehh
            if pokelist[0] == '<':
                #remove the <@! at the start and the > at the end
                temp = int(pokelist.strip()[3:-1])
            else:
                temp = int(pokelist.strip())
            if temp in pkmnListsPriv and listname in pkmnListsPriv[temp]:
                pkmnListsPriv[temp].remove(listname)
                await ctx.send(f'Access removed from {bot.get_user(temp)}')
            else:
                try:
                    pkmnListsPriv[temp].add(listname)
                except:
                    pkmnListsPriv[temp] = set([listname])
                await ctx.send(f'Access given to {bot.get_user(temp)}')
        else:
            await ctx.send(f'The format for this command is `%list <listname> (add/del/show/access) poke1, poke2, etc`\n'
                           f'The part for (add/del/show/access) wasn\'t recognized.')
    elif listname not in pkmnListsPriv[ctx.author.id]:
        users = [str(bot.get_user(x)) for x in pkmnListsPriv if listname in pkmnListsPriv[x]]
        if len(users) > 0:
            await ctx.send(f'{", ".join(users)} {"have" if len(users)>1 else "has"} '
                           f'edit access to this. Please ask {"one of" if len(users)>1 else ""} '
                           f'them to "%list {listname} access @mention" if you want access')
        else:
            pkmnListsPriv[ctx.author.id].add(listname)
            await ctx.send(f'No users linked to this list. You now have permission, please try again.')
    # try:
    #     if isItem and pkmnLists[listname][0] != 'i':
    #         pkmnLists[listname].insert(0, 'i')
    # except:
    #     pass
    await ctx.message.add_reaction('\N{CYCLONE}')
    save_obj(pkmnListsPriv, 'pkmnListsPriv')
    save_obj(pkmnLists, 'pkmnLists')
    #if len(pkmnLists.keys()) < len(areListsBroken) - 1:
    #    await bot.appinfo.owner.send(f'{listname} {which} {pokelist}')

###

@bot.command(name = 'listsub', help = 'Subtract two lists.\n'
                                      'If list1 = "bulbasaur, treecko, chikorita"\n'
                                      'and list2 = "treecko"\n'
                                      'then "%listsub list1 list2" makes list1 = "bulbasaur, chikorita"')
async def pkmn_listsub(ctx, list1 : str, list2 : str):
    msg = ''
    bad = False
    for x in [list1, list2]:
        if x not in pkmnLists:
            msg += f'Is {x} a list?\n'
            bad = True
    if not bad and list1 not in pkmnListsPriv[ctx.author.id]:
        msg += f'You do not have permission to modify the list {list1}'
        bad = True
    if bad:
        await ctx.send(msg)
        return
    removed = []
    list1odds = [elem[0] for elem in pkmnLists[list1]]
    for index, elementlist in enumerate(pkmnLists[list2]):
        if elementlist[0] in list1odds:
            where = list1odds.index(elementlist[0])
            for x in elementlist[1:]:
                try:
                    pkmnLists[list1][where].remove(x)
                    removed.append(x)
                except:
                    pass
    await ctx.send(f'{", ".join(bad)}\n{"were" if len(removed) > 1 else "was"} removed from {list1}')

#######

def pkmn_full_list(listname : str) -> list:
    if listname not in pkmnLists:
        return ['There was not a list with this name.\n']
    full = []
    #strip out the 'p' or 'i'
    for lst in pkmnLists[listname][1:]:
        #strip out the percentage
        full += lst[1:]
    return full

#returns a random pokemon or item from given list
def pkmn_random_driver(listname : str, giveList = False) -> str:
    if listname not in pkmnLists:
        return 'There was not a list with this name.\n'
    #remove the leading 'i' or 'p'
    temp = pkmnLists[listname][1:]
    which = 0
    rand = random.randrange(1,101) - int(temp[0][0])
    while rand > 0 and which < len(temp):
        which += 1
        if which == len(temp):
            #if the list is 80% pokemon/items, 20% nothing
            return 'None'
        rand -= int(temp[which][0])
    if giveList:
        return temp[which][1:] #remove the percentage
    else:
        return random.choice(temp[which][1:])

@bot.command(name = 'random', aliases = ['rl'],
             help = 'Get a random item/poke from a list.\n'
                    '%random [howMany] <list>, <list2>, pokemon, etc')
async def pkmn_randomitem_driver(ctx, howMany : typing.Optional[int] = 1, *, listname : str):
    combined_list = []
    errors = []
    for name in listname.split(', '):
        #not using if/else because otherwise i would need the queries up front
        if name in pkmnLists:
            combined_list += pkmn_full_list(name)
            continue
        item_query = database.custom_query(f'SELECT name FROM pkmnItems WHERE category="{name.title()}"')
        if item_query:
            combined_list += [x[0] for x in item_query]
            continue
        poke_query = database.custom_query(f'SELECT name FROM pkmnStats WHERE name="{lookup_poke(name)}"')
        if poke_query:
            combined_list += [x[0] for x in poke_query]
            continue
        errors.append(name)

    rand = [f'{x+1}. {random.choice(combined_list)}' for x in range(howMany)]
    if errors:
        errors = ', '.join(errors)
        rand.append(f'*"{errors}" wasn\'t found as items, pokemon, or lists*')
    await ctx.send('\n'.join(rand))

#######

@bot.command(name = 'filter', aliases = ['f'],
             help = '%filter <listname> <rank> <type1> <type2> [includeLowerRanks T/F]'
                                     ' <generation>\n'
                                     'type1 & type2 - can be Any or None\n'
                                     'includeLowerRanks - if <rank> is ace, do you want starter/beginner/amateur/ace?\n'
                                     'generation - any number between 1 and 9 (kanto through galar + delta pkmn)\n'
                                     '%filter forest beginner grass None\n'
                                     '  --> Adds beginner rank pure grass types to the list forest\n'
                                     '%filter forest ace bug any True 4-6\n'
                                     '  --> Adds up to Ace rank bug/Any types from gen 4 to 6 to the list forest\n'
                                     'Note: generation 1-8 is default, and to change it you will need to include all parameters')
async def pkmn_filter_list(ctx, listname : str, rank : ensure_rank,
                           type1 : str, type2 : str = 'Any',
                           includeLowerRanks : bool = False, generation : str = ''):
    type1 = type1.title()
    type2 = type2.title()
    rank = rank.title()

    #which ranks to find
    if includeLowerRanks:
        rank = ranks[:ranks.index(rank)+1]
    else:
        rank = [rank]

    if type2 == 'None':
        type2 = ''

    if generation == '':
        generation = '1-8'

    generation = generation.replace(' ', '').split('-')
    if len(generation) == 1:
        gen = f' AND generation="{generation[0]}"'
    else:
        gen = f' AND generation BETWEEN {generation[0]} AND {generation[1]}'

    query = f'SELECT name FROM pkmnStats WHERE ' \
            f'( ( type1="{type1}" ' + \
            (f'AND type2="{type2}")'
             f' OR ( type1="{type2}" AND type2="{type1}") ) AND (' if type2 != 'Any' else ') ) AND (') + \
            ' OR '.join([f'rank="{x}"' for x in rank]) + ')' + gen + ' ORDER BY number ASC'
    returned = database.custom_query(query)
    returned = [x[0] for x in returned]

    #send the filtered list to %list, which will print it
    if len(returned) == 0:
        await ctx.send(f'I couldn\'t find any pokemon...')
        return
    await send_big_msg(ctx, f'Trying to add these pokemon to the list {listname}:\n'+', '.join(returned))
    await pkmn_list(ctx = ctx, listname = listname, which = 'add', pokelist = ', '.join(returned))

#######

async def pkmnitemhelper(item):
    global database
    try:
        return list(database.query_table('pkmnItems', 'name', item)[0])[1:]
    except:
        raise KeyError(f'{item} wasn\'t recognized as an item.')

@bot.command(name = 'item', aliases = ['items', 'i'], help = 'List an item\'s traits. "%item" for categories.')
async def pkmn_search_item(ctx, *, itemname : pkmn_cap = ''):
    global database
    if itemname != '':
        try:
            found = await pkmnitemhelper(itemname)
        except:
            await ctx.send(f'{itemname} wasn\'t found in the item list.')
            return
        try:
            output = f'__{itemname}__\n'

            if found[0] != '':
                order = [0,'Type Bonus', 'Value', 'Strength', 'Dexterity', 'Vitality', 'Special', 'Insight', 'Defense',
                         'Special Defense', 'Evasion', 'Accuracy', 0, 'Heal Amount']
                #this is an actual item
                output += f'**Price**: {found[-3] or "???"}\n'
                if found[12] != '':
                    output += f'**Pokemon**: {alpha_str.sub("", found[12])}\n'
                for name in range(1,len(order)):
                    if name == 12:
                        continue
                    if found[name] != '':
                        output += f'**{order[name]}**: {found[name]}\n'
                output += f'**Description**: {found[0].capitalize()}'
            else:
                #this is a category
                temp = database.custom_query(f'SELECT name FROM pkmnItems WHERE category="{itemname}"')
                temp = [x[0] for x in temp]
                for x in temp:
                    output += f' - {x}\n'
            await ctx.send(output)
        except:
            await ctx.send(f'{itemname} wasn\'t found in the item list.\n*Unknown Error Occurred?*')
    else:
        temp = database.custom_query('SELECT name FROM pkmnItems WHERE description=""')
        temp = [x[0] for x in temp]
        msg = ''
        wbool = False
        for x in temp:
            msg += ('\n - ' if not wbool else ' / ') + x
            wbool = not wbool
        await ctx.send(msg)

@bot.command(name='shop', help='Lists all recommended shop items grouped by price.\n'
                               '"%shop (price) (showHigherPriced)" to limit the output by price.\n'
                               'e.g. "%shop 750 True" to list all items priced higher than 750.')
async def shop_items(ctx, pricePoint : int = None, showHigherPriced : bool = False):
    global database
    low = 5
    high = 10000
    if showHigherPriced:
        low = pricePoint or low
    else:
        high = pricePoint or high
    if low < 5:
        low = 5
    full_list = "SELECT name, CAST(suggested_price as integer) FROM pkmnItems WHERE " \
                f"CAST(suggested_price as integer) BETWEEN {low} AND {high} " \
                "ORDER BY CAST(suggested_price as integer)"
    tmp = database.custom_query(full_list)
    output = ''
    tmpDict = ODict()
    for name, val in tmp:
        if val in tmpDict:
            tmpDict[val].append(name)
        else:
            tmpDict[val] = [name]
    for price, values in tmpDict.items():
        output += f'**{price}¥**\n' + ' -- '.join(values) + '\n'
    await send_big_msg(ctx, output)

#######

async def instantiateHabitatsList():
    with open('habitats.csv', 'r', encoding = 'UTF-8') as file:
        reader = csv.reader(file)
        for row in reader:
            pkmnHabitats[row[0]] = [x for x in row[1:]]

async def pkmnhabitatshelper(habitat):
    if len(pkmnHabitats.keys()) == 0:
        await instantiateHabitatsList()
    return pkmnHabitats[habitat]

async def pkmnDictRanks(pokemon : list) -> dict:
    level = dict()
    for poke in pokemon:
        try:
            rank = (await pkmnstatshelper(poke))[20]
        except:
            #its either nidoran or oricorio
            print(pkmnLists[poke.lower()])
            tmppoke = random.choice(random.choice(pkmnLists[poke.lower()][1:])[1:])
            rank = (await pkmnstatshelper(tmppoke))[20]
        if rank not in level:
            level[rank] = []
        level[rank].append(poke)
    return level

async def pkmnRankDisplay(title : str, pokemon : typing.Union[list, dict]) -> str:
    if isinstance(pokemon, list):
        pokemon = await pkmnDictRanks(pokemon)
    output = title + '\n'
    for rank in ranks:
        if rank in pokemon:
            output += f'**{rank}**\n{"  |  ".join(pokemon[rank])}\n'
    return output

async def pkmnRankListDisplay(title : str, listname : str) -> str:
    pokelist = []
    #for tuple in the list
    for x in pokesFromList(listname):
        pokelist.append(x)
    return await pkmnRankDisplay(title, pokelist)

@bot.command(name = 'habitat', aliases = ['biome', 'h', 'habitats'],
             help = 'List the pokemon for a biome that theworldofpokemon.com suggests.')
async def pkmn_search_habitat(ctx, *, habitat : str = ''):
    try:
        habitat = habitat.title()
        found = await pkmnhabitatshelper(habitat)
    except:
        pass
    if habitat != '':
        try:
            if not habitat.endswith('Biomes'):
                # this is a biome with pokebois
                output = await pkmnRankDisplay(f'__{habitat}__',found)
                await send_big_msg(ctx, output)
            else:
                output = f'__{habitat}__\n - '
                # this is an overarching theme
                wbool = False
                for x in found:
                    output += x + f' ({len(pkmnHabitats[x])})' + ('\n - ' if wbool else ' / ')
                    wbool = not wbool
                await ctx.send(output[:-3])
        except:
           await ctx.send(f'{habitat} wasn\'t recognized in the habitat list.')
    else:
        temp = []
        for key in list(pkmnHabitats.keys()):
            if key.endswith('Biomes'):
                temp.append(key)
        msg = '__Biome Supersets:__\n - '
        wbool = False
        for x in temp:
            msg += x + f' ({len(pkmnHabitats[x])})' + ('\n - ' if wbool else ' / ')
            wbool = not wbool
        await ctx.send(msg[:-3])

@bot.command(name = 'filterhabitat', aliases = ['fh'],
             help = '%filterhabitat <list> <rank=All> <includeLowerRanks=True> <habitat>\n'
                    'Transcribe pokemon from a habitat into a list (optionally by rank)',
             hidden = True)
async def pkmn_filter_habitat(ctx, listname : str, rank : typing.Optional[ensure_rank] = 'Champion',
                              includeLowerRanks : typing.Optional[bool] = True, *, habitat : str):
    habitat = habitat.title()
    if listname not in pkmnLists:
        await pkmn_list(ctx, listname, 'create')
    try:
        #get a list of pokemon in the habitat
        found = await pkmnhabitatshelper(habitat)
    except:
        await ctx.send(f'{habitat} wasn\'t recognized as a habitat.')
        return

    #get the pokemon's ranks
    ranklist = await pkmnDictRanks(found)
    #convert it into a list of tuples... for each, [0] is the rank, [1] is the poke list
    temp = []
    for ranking in ranks:
        if ranking in ranklist:
            temp.append((ranking, ranklist[ranking]))
    ranklist = temp
    #if rank is less than Champion...
    upperRank = ranks.index(rank)
    if upperRank < 6:
        for i, key in enumerate(ranklist):
            if not includeLowerRanks and upperRank == ranks.index(key[0]):
                ranklist = [ranklist[i]]
                break
            elif ranks.index(key[0]) > upperRank:
                ranklist = ranklist[:i]
                break
    pokes = []
    pokeCheck = pokesFromList(listname)
    for poketuples in ranklist:
        for x in poketuples[1]:
            #for wormadam, lycanroc, etc
            if x in pkmnLists:
                x = pkmn_random_driver(x)
            #check if pokemon or list
            if x not in pokeCheck:
                pokes.append(x)
    if pokes:
        await pkmn_list(ctx = ctx, listname = listname, which = 'add', pokelist = ', '.join(pokes))
    else:
        await ctx.send(f'All these pokemon are already in the list \'{listname}\'!')

@bot.command(name = 'viewhabitat', aliases = ['vh'],
             help = 'Expand a habitat into a viewable format.\n'
                    'e.g. %vh ocean biomes')
async def view_habitat(ctx, *, habitatlist : sep_biomes):
    await ctx.send((await pkmnRankDisplay(f'__{habitatlist}__', habitatlist)))

#######

async def pkmnabilitieshelper(ability):
    global database
    try:
        return list(database.query_table('pkmnAbilities', 'name', ability)[0])[1:]
    except:
        raise KeyError(f'{ability} wasn\'t recognized as an ability.')

@bot.command(name = 'ability', aliases = ['a'], help = 'List a pokemon ability\'s traits')
async def pkmn_search_ability(ctx, *, abilityname : pkmn_cap):
    try:
        found = await pkmnabilitieshelper(abilityname)

        output = f'**{abilityname}:** {found[0]}'
        if found[1] != '':
            output += f'\n-\n*{found[1]}*'

        await ctx.send(output)
    except:
        await ctx.send(f'{abilityname} wasn\'t found in the ability list.')

#######

async def pkmnmovehelper(move):
    global database
    try:
        return list(database.query_table('pkmnMoves', 'name', move)[0])[1:]
    except:
        move = move.replace(' ', '-')
        return list(database.query_table('pkmnMoves', 'name', move)[0])[1:]

@bot.command(name = 'move', aliases = ['m'], help = 'List a pokemon move traits')
async def pkmn_search_move(ctx, *, movename : pkmn_cap):
    try:
        found = await pkmnmovehelper(movename)

        output = f'__{movename}__\n'
        if found[9] != "":
            output += f'*{found[9]}*\n'
        output += f'**Type**: {found[0].capitalize()}'
        output += f' -- **{found[1].capitalize()}**\n'
        output += f'**Target**: {found[7]}'
        output += f' -- **Power**: {found[2]}\n'
        output += f'**Dmg Mods**: {(found[3] or "None")} + {(found[4] or "None")}\n'
        output += f'**Acc Mods**: {(found[5] or "None")} + {(found[6] or "None")}\n'
        output += f'**Effect**: {found[8]}'

        await ctx.send(output)
    except:
        await ctx.send(f'{movename} wasn\'t found in the move list.')

@bot.command(name = 'metronome',
             aliases = ['mtr'],
             help = """
             Simulates a random move. Comes with options to limit the scope.
             
             %metronome
                Randomly select any move.
             
             %metronome 1
                Select any move with power 1.
             
             %metronome 2<5
                Any move between power 2 and 5 (inclusive)
             
             %metronome dragon
                Any dragon type move. `support` instead of a type would give a random support move.""")
async def metronome(ctx, *, parameters : str = ''):
    parameters = parameters.replace(' ', '')
    custom_query = 'SELECT name FROM pkmnMoves'
    if parameters == '':
        pass
    elif '<' in parameters:
        tmp = parameters.split('<')
        lower = tmp[0]
        higher = tmp[1]
        custom_query += f' WHERE power BETWEEN {lower} and {higher}'
    elif parameters.isdigit():
        custom_query += f' WHERE power={parameters}'
    elif parameters.upper() == 'SUPPORT':
        custom_query += f' WHERE pwrtype="{parameters.upper()}"'
    else:
        custom_query += f' WHERE type="{parameters.lower()}"'

    custom_query += ' ORDER BY RANDOM() LIMIT 1'
    result = database.custom_query(custom_query)

    try:
        await pkmn_search_move(ctx = ctx, movename = result[0][0])
    except:
        await ctx.send(f'`{parameters}` was not recognized as a valid type (grass, water, etc) or power level (1, 2, 3 < 5, etc).\n'
                       f'*(This message self-destructs in 15 seconds)*',
                       delete_after = 15)

#####

async def pkmnstatshelper(poke : str):
    global database
    try:
        tmp = list(database.query_table('pkmnStats', 'name', poke)[0])
    except:
        raise KeyError(poke)
    tmp = [f'#{tmp[0]}'] + tmp[2:]
    return tmp

@bot.command(name = 'stats', aliases = ['s', 'info'], help = 'List a pokemon\'s stats. '
                                                             'Emote on the message to expand the abilities!')
async def pkmn_search_stats(ctx, *, pokemon : pkmn_cap):
    #try:
    #deep[:] copy of coroutine, otherwise it kindly creates a shallow copy which breaks everything
    try:
        found = (await pkmnstatshelper(pokemon))[:]
    except:
        pokemon = lookup_poke(pokemon)
        found = (await pkmnstatshelper(pokemon))[:]
    for x in range(4, 14, 2):
        found[x+1] = "⭘"*(int(found[x+1])-int(found[x]))
        found[x] = "⬤"*int(found[x])

    output = f'{found[0]} __{pokemon.title()}__\n'
    output += f'**Suggested Rank**: {found[20]}\n'
    output += f'**Type**: {found[1].capitalize()}'
    if found[2] == '':
        output += '\n'
    else:
        output += f' / {found[2].capitalize()}\n'
    exStats = [f'`({len(found[x])}/{len(found[x])+len(found[x+1])})`' for x in range(4,14,2)]
    output += f'**Base HP**: {found[3]}\n'
    output += f'**Strength**: {found[4]}{found[5]} {exStats[0]}\n'
    output += f'**Dexterity**: {found[6]}{found[7]} {exStats[1]}\n'
    output += f'**Vitality**: {found[8]}{found[9]} {exStats[2]}\n'
    output += f'**Special**: {found[10]}{found[11]} {exStats[3]}\n'
    output += f'**Insight**: {found[12]}{found[13]} {exStats[4]}\n'
    output += f'**Ability**: {found[14]}'
    if found[15] != '': #secondary
        output += f' / {found[15]}'
    if found[16] != '': #hidden
        output += f' ({found[16]})'
    if found[17] != '': #event
        output += f' <{found[17]}>'
    output += '\n'
    output += f'**Can Evolve**: {(found[18] or "No")}\n'
    output += f'**Other Forms**: {(found[19] or "No")}\n'

    await ctx.send(output)
    #except:
    #    msg = f'{pokemon} wasn\'t found in the pokemon list.'
    #    if pokemon in pkmnLists:
    #        msg += '\nDid you mean: '+', '.join(pkmnLists[pokemon])+'?'
    #    await ctx.send(msg)

#####

async def pkmnlearnshelper(poke : str, rank : ensure_rank = 'Master'):
    global database
    try:
        found = list(database.query_table('pkmnLearns', 'name', poke)[0][2:])
    except:
        raise KeyError(poke)
    #truncate the list to just the valid members
    try:
        found = found[:found.index(None)]
    except:
        pass
    #works if the ranks are 'starter', etc, or numbers
    try:
        found[1::2] = [ranks[x] for x in found[1::2]]
    except:
        pass
    done = False
    moves = dict()
    for x in range(0, len(found), 2):
        if done:
            break
        if found[x + 1] not in moves:
            if rank == 'Master' or ranks.index(found[x+1]) <= ranks.index(rank):
                moves[found[x + 1]] = [found[x]]
            else:
                done = True
        else:
            moves[found[x + 1]].append(found[x])
    return moves

@bot.command(name = 'pokelearns',
             aliases = ['canlearn', 'pl', 'moves', 'learnset'],
             help = 'Lists what moves a pokemon can learn\ne.g. %pokelearns vulpix')
async def pkmn_search_learns(ctx, *, pokemon : pkmn_cap):
    #known moves is insight + 2
    try:
        try:
            moves = await pkmnlearnshelper(pokemon)
        except:
            pokemon = lookup_poke(pokemon)
            moves = await pkmnlearnshelper(pokemon)
        output = f'__{pokemon.title()}__\n'

        for x in moves.keys():
            output += f'**{x}**\n' + '  |  '.join(moves[x]) + '\n'

        await ctx.send(output)
    except:
        msg = f'{pokemon} wasn\'t found in the pokeLearns list.'
        if pokemon in pkmnLists:
            msg += '\nDid you mean: '+', '.join(pkmnLists[pokemon])+'?'
        await ctx.send(msg)

#####

# returns the moves of a pokemon + all it's devolutions
async def move_aggregator(poke : str, rank : str) -> dict:
    movelist = {} # init final dict
    allPokes = [poke]
    result = False
    while result is not None:
        query = f'SELECT previous FROM pkmnEvo WHERE name="{allPokes[-1]}"'
        result = database.custom_query(query, multiple = False)
        if result:
            allPokes.append(result[0])
    for pkmn in allPokes:
        tmp = await pkmnlearnshelper(pkmn, rank)
        for x, y in list(tmp.items()):
            if x in movelist:
                for name in y:
                    movelist[x].add(name)
            else:
                movelist[x] = set(y)
    return movelist

async def calcStats(rank : str, attr : list, maxAttr : list,
                    movelist : dict = {}, additionalIns : int = 0,
                    additionalVit : int = 0) -> (list, list, list, int):
    #initialize base stats
    bhp = attr[0]
    attributes = attr[1:]
    maxattr = maxAttr[1:]
    #no limits on socials (except max of 5)
    socials = bot.socials[:]
    extraSocial = 6 if rank == 'Master' else 0
    #limited by rank
    skills = bot.skills[:]
    rankIndex = ranks.index(rank)
    pointsToAllocate = attributeAmount[rankIndex] - ( additionalIns + additionalVit )
    attributes[2] += additionalVit

    def normalize(array) -> list:
        tmp = sum(array)
        return [x/tmp for x in array]

    def weightedchoice(low, high, weights, number = 1, replace = True) -> int:
        try:
            final_list = choice(list(range(low, high)), number, p = weights, replace = replace)
        except:
            final_list = choice(list(range(low, high)), number, replace = replace)
        return final_list

    bias_amt = rankBias[rankIndex]

    attrWeight = [1] * len(attributes)
    socialWeight = [1] * len(socials)
    skillWeight = [bias_amt//2] * 5 + [1] * ( len(skills) - 5 ) # first 4 skills are combat + alert for initiative

    skill_names = [x[0].upper() for x in skills]
    if movelist:
        #if we have a movelist, then don't mess with insight
        insight = attributes[-1]
        attributes = attributes[:-1]
        attr_names = ['STRENGTH', 'DEXTERITY', 'VITALITY', 'SPECIAL']
        social_names = ['TOUGH', 'COOL', 'BEAUTY', 'CLEVER', 'CUTE']

        attrWeight[attr_names.index('VITALITY')] += bias_amt * 2

        #define all attributes and skills in separate lists (initially 0)
        # iterate over all moves, and add 1 to the equivalent attr/skill for each instance
        # this will be the weighted function
        for move, desc in list(movelist.items()):
            #index 3, 4 & 5 are attributes, 6 is skills
            #(5 could be a social stat)
            if desc[3] in attr_names: #check attributes...
                attrWeight[attr_names.index(desc[3])] += bias_amt
            if desc[4] in attr_names:
                attrWeight[attr_names.index(desc[4])] += bias_amt
            if desc[5] in attr_names:
                attrWeight[attr_names.index(desc[5])] += bias_amt
            elif desc[5] in social_names: #check social
                socialWeight[social_names.index(desc[5])] += bias_amt
            if desc[6] in skill_names: #check skills
                skillWeight[skill_names.index(desc[6])] += bias_amt
    attrWeight = attrWeight[:len(attributes)] #remove insight if needed, for normalization purposes

    # allocate attributes
    fullStats = [False]*(len(attributes)+1)
    x = 0 #count allocated stats
    #need "- attrMod" because insight may already be allocated
    if rank == 'Champion':
        maxattr = [x+2 for x in maxattr]
    while x < pointsToAllocate and len(attributes) > 0:
        attrWeight = normalize(attrWeight)
        temp = weightedchoice(0, len(attributes), attrWeight)[0]
        if attributes[temp] < maxattr[temp]:
            attributes[temp] = attributes[temp] + 1
            x = x + 1
        else:
            attrWeight.pop(temp)
            maxattr.pop(temp)
            tmpStat = attributes.pop(temp) #find the exact place
            temp = temp + sum([0 if not x else 1 for x in fullStats[:temp+1]])
            while fullStats[temp]: # is there a more elegant way to do this?
                temp += 1           # best i can see is to have an offset array otherwise
            fullStats[temp] = tmpStat
    if x < pointsToAllocate:
        leftover = attributeAmount[rankIndex] - x
    else:
        leftover = 0
    for index, val in enumerate(fullStats):
        if val:
            attributes.insert(index, val)
    attributes = [bhp] + attributes

    #distribute socials
    fullStats = [False]*len(socials)
    x = 0
    while x < attributeAmount[rankIndex] + extraSocial and len(socials) > 0:
        socialWeight = normalize(socialWeight)
        temp = weightedchoice(0, len(socials), socialWeight)[0]
        if socials[temp][1] < limit[rankIndex]:
            socials[temp] = (socials[temp][0], socials[temp][1] + 1)
            x = x + 1
        else:
            socialWeight.pop(temp)
            tmpStat = socials.pop(temp)
            temp = temp + sum([0 if not x else 1 for x in fullStats[:temp + 1]])
            while fullStats[temp]:  # is there a more elegant way to do this?
                temp += 1  # best i can see is to have an offset array otherwise
            fullStats[temp] = tmpStat

    for index, val in enumerate(fullStats):
        if val:
            socials.insert(index, val)

    #distribute skills
    lastAmt = 0
    skillWeight = normalize(skillWeight)
    for rankStep in range(rankIndex+1):
        currentAmt = skillAmount[rankStep] - lastAmt
        lastAmt = skillAmount[rankStep]
        points = weightedchoice(0, len(skills), skillWeight, number = currentAmt, replace = False)
        # champion only test
        if len(points) == 1:
            tmp = points[0]
            if skills[tmp][1] == 5: #champion skill trying to reach 6 points smh
                newWeight = skillWeight[:tmp] + [0] + skillWeight[tmp+1:]
                newWeight = normalize(newWeight)
                #retry but set the offending skill to 0 weight
                points = weightedchoice(0, len(skills), newWeight, number = currentAmt, replace = False)
        for temp in points:
            skills[temp] = (skills[temp][0], skills[temp][1] + 1)

    try:
        attributes.append(insight)
    except:
        pass
    return attributes, socials, skills, leftover

async def pkmn_encounter(ctx, number : int, rank : str, pokelist : list,
                         exact_rank : bool = False, boss : bool = False, guild = None) -> str:
    if guild is None:
        guild = await getGuilds(ctx)
    msg = ''
    rankrandom = False
    rankbase = False
    #rank = rank.title()
    if rank == 'Random':
        rank = random.choice(ranks[:-1])
        rankrandom = True
    if rank == 'Base':
        rankbase = True

    tempList = []
    for name in pokelist:
        name = name.strip()
        if name in pkmnLists:
            y = pkmn_random_driver(name, giveList = True)
            if y == 'None' or y == ['None']:
                return '...but nothing was there. *(Rolled an empty %)*\n'
            for poke in y:
                tempList.append(poke)
        else:
            tempList.append(name)
            #pokelist = [x.strip().title() for x in pokelist.split(',')]
            #if len(pokelist)==1:
            #    pokelist = [x.strip().title() for x in pokelist[0].split(' ')]
    pokelist = [pkmn_cap(item) for item in tempList]
    random.shuffle(pokelist)

    if number > 6:
        msg+='Can only create up to 6 pokes at once due to size\n'
        number = 6
    elif number < 1:
        number = 1

    if len(pokelist) == 0:
        return 'Need at least one pokemon in the list!'

    #exceptions for master rank: 6 extra social, HP + 2, DEF/S.DEF + 2

    for pokeamount in range(number):
        if not exact_rank:
            #get a poke from the list
            nextpoke = random.choice(pokelist)
            #get the attributes
            try:
                statlist = await pkmnstatshelper(nextpoke)
            except:
                # name is a typo
                nextpoke = lookup_poke(nextpoke)
                statlist = await pkmnstatshelper(nextpoke)
            if rankbase:
                #20 is suggested rank
                rank = statlist[20].title()
        else:
            foundrank = None
            nextpoke = None
            while len(pokelist) > 1 and foundrank != rank:
                if nextpoke:
                    pokelist.remove(nextpoke)
                #get a poke from the list
                nextpoke = random.choice(pokelist)
                #get the attributes
                try:
                    statlist = await pkmnstatshelper(nextpoke)
                except:
                    # name is a typo
                    nextpoke = lookup_poke(nextpoke)
                    statlist = await pkmnstatshelper(nextpoke)
                foundrank = statlist[20].title()

        # to differentiate between naturally learned moves at an evolution
        naturalMoves = await pkmnlearnshelper(nextpoke, rank)
        #get all potential moves, up to the rank
        try: #does the setting exist...
            setting = pokebotsettings[guild][9]
        except:
            await instantiateSettings(guild)
            setting = pokebotsettings[guild][9]
        if setting == 0: # all moves at rank from poke and pre evos
            movelist = await move_aggregator(nextpoke, rank)
        if setting == 1: # previous behaviour
            movelist = naturalMoves.copy()
        elif setting == 2: # previous evos at lower rank
            newrank = ranks.index(rank.title())
            if newrank != 0:
                newrank -= 1
            newrank = ranks[newrank]
            movelist = await move_aggregator(nextpoke, newrank)
        naturalMoves = [item for sublist in list(naturalMoves.values()) for item in sublist]

        #3/4/6/8/10/12 == b.hp/str/dex/vit/spe/ins
        attributes = [int(statlist[3])] + [int(statlist[x]) for x in range(4, 13, 2)]

        baseattr = [x for x in attributes]
        maxattr = [0] + [int(statlist[x]) for x in range(5, 14, 2)]

        # numVitality = 0
        if boss: #we need insight for # of moves
            attrNum = len(baseattr)
            numMoves = baseattr[5]
            for _ in range(attributeAmount[ranks.index(rank.title())]):
                randnum = random.random()
                # if randnum < 1/(attrNum*2) and baseattr[3] + numVitality < maxattr[3]: #chance for vitality
                #     numVitality += 1
                #     continue
                if randnum < 1/attrNum: #chance for insight
                    numMoves += 1
                if numMoves == maxattr[5]:
                    break
            numMoves += 2
        else: #generate stats randomly
            attributes, socials, skills, _ = await calcStats(rank, attributes, maxattr)
            numMoves = attributes[5] + 2 #insight + 2

#todo: guarantee a (attacking?) move from the pokemon's rank

        #cut the movelist down to this number
        newMoves = []
        #flatten, then convert to a set and back to remove duplicates
        movelist = list(set([item for sublist in list(movelist.values()) for item in set(sublist)]))
        for _ in range(numMoves):
            if len(movelist) == 0: #usually legendaries
                break
            temp = random.choice(movelist)
            newMoves.append(temp)
            movelist.remove(temp)

        move_descs = {}
        for move in newMoves:
            move_descs[move] = await pkmnmovehelper(move)

        if boss: #allocate stats since we didn't before (and adjust insight accordingly)
            insightAdded = numMoves - 2 - baseattr[5]
            attributes, socials, skills, leftover = await calcStats(rank, baseattr, maxattr,
                                                                    move_descs, insightAdded)#, numVitality)
            attributes[5] += insightAdded
            if rank == 'Champion':
                lowerBound = maxattr[5]-attributes[5]+2
            else:
                lowerBound = maxattr[5]-attributes[5]
            extraPoints = min(leftover, lowerBound)
            attributes[5] += extraPoints

            for _ in range(extraPoints): # repeated loop, yeah, yeah, i know
                if len(movelist) == 0:
                    break
                temp = random.choice(movelist)
                newMoves.append(temp)
                movelist.remove(temp)
                move_descs[temp] = await pkmnmovehelper(temp)
        movelist = newMoves

        #base 14, second 15, hidden 16, event 17
        totalchance = pokebotsettings[guild][0] + pokebotsettings[guild][1] + pokebotsettings[guild][2]
        randomnum = random.random()
        if pokebotsettings[guild][2]/totalchance >= randomnum and statlist[16] != '':
            #hidden, succeeded the low roll
            ability = statlist[16]
        elif pokebotsettings[guild][1]/totalchance >= randomnum and statlist[15] != '':
            #secondary, failed the hidden
            ability = statlist[15]
        else:
            #basic, failed the other checks
            ability = statlist[14]

        if pokebotsettings[guild][6] != False:
            item = pkmn_random_driver(pokebotsettings[guild][6])
        else:
            item = 'None'
        #calculate hp (base hp + vitality)
        attributes[0] = attributes[0] + attributes[3]

        #combine all the info into a dict()

        allAttr = {'STRENGTH': attributes[1],'DEXTERITY': attributes[2],'VITALITY': attributes[3],
                   'SPECIAL': attributes[4], 'INSIGHT': attributes[5], '': None, None: None, 'WILL': 0,
                   'MISSING HAPPINESS': 0, 'MISING BEAUTY': 0, 'HAPPINESS': 0}
        for skill in skills:
            allAttr.update({skill[0].upper():skill[1]})
        for social in socials:
            allAttr.update({social[0].upper():social[1]})

        abilitytext = ''
        if pokebotsettings[guild][5]:
            try:
                abilitytext = await pkmnabilitieshelper(ability)
            except:
                pass


        #then combine it into a msg

        gender = statlist[21]
        if gender == '':
            gender = 'M' if random.random() < .5 else 'F'

        #if there's only one pokemon generated then skip this
        if number != 1:
            msg += f'**{pokeamount+1}**.\n\n'
        msg += f'__{nextpoke}__' \
               f' ({gender})' \
               f'  |  **{rank}**'
        msg += f'  |  {random.choice(natures)}'
        msg += (f'  |  ***SHINY***' if pokebotsettings[guild][3] >= random.random() else f'')

        msg += f'\n**Type**: {statlist[1]}{"" if statlist[2] == "" else "/"+statlist[2]}\n'

        #ability
        msg += f'**Ability:** {ability}\n'

        #item
        if pokebotsettings[guild][6]:
            msg += f'**Item:** {item}\n'

        #⬤⦿⭘
        just = 0
        fullattr = [0]
        totalNums = [0]
        for attr in range(1,len(attributes)):
            a = int(baseattr[attr])
            b = int(attributes[attr])
            c = int(maxattr[attr])
            if c > just:
                just = c
            baseattr[attr] = '⬤'*a
            attributes[attr] = '⦿'*(b-a)
            maxattr[attr] = '⭘'*(c-b)
            totalNums.append(f' `({b}/{c})`')
            fullattr.append(baseattr[attr]+attributes[attr]+maxattr[attr])
            d = int(socials[attr-1][1])
            socials[attr-1] = (socials[attr-1][0],'⬤'*d + '⭘'*(5-d))
        just += 12
        msg += f'**Total HP:** {attributes[0]}\n'
        msg += ('**Str:** '+fullattr[1]+totalNums[1]).ljust(just)+f' -- **{socials[0][0]}:**  {socials[0][1]}\n'
        msg += ('**Dex:** '+fullattr[2]+totalNums[2]).ljust(just)+f' -- **{socials[1][0]}:**  {socials[1][1]}\n'
        msg += ('**Vit:** '+fullattr[3]+totalNums[3]).ljust(just)+f' -- **{socials[2][0]}:**  {socials[2][1]}\n'
        msg += ('**Spe:** '+fullattr[4]+totalNums[4]).ljust(just)+f' -- **{socials[3][0]}:**  {socials[3][1]}\n'
        msg += ('**Ins:** '+fullattr[5]+totalNums[5]).ljust(just)+f' -- **{socials[4][0]}:**  {socials[4][1]}\n'

        msg+= '\n'

        #add the socials (4 rows, 3 per line)
        for x in range(0,12,4):
            for y in range(4):
                msg += f'**{skills[x+y][0]}:**'.ljust(11) + ' '+str(skills[x+y][1]) + (' - ' if y!= 3 else '')
            msg+='\n'

        if pokebotsettings[guild][5] and abilitytext != '':
            msg += f'\n**{ability}**: {abilitytext[0]}\n'
            if abilitytext[1] != '':
                msg += f'*{abilitytext[1]}*\n'

        if item != 'None':
            try:
                temp = await pkmnitemhelper(item)
                msg += f'**{item}**: {temp[0]}\n'
            except:
                msg += f'**{item}**: ???\n'

        msg += '\n*Moves*:\n'

        if pokebotsettings[guild][4]:
            #add the moves + their desc
            for x in movelist:
                try:
                    # found = await pkmnmovehelper(x)
                    found = move_descs[x]
                    if found[8][-9:-1] == 'Accuracy':
                        try:
                            accMod = int(found[8][-11])
                        except:
                            accMod = 0
                    else:
                        accMod = 0
                    #todo: differentiate between damaging STAB, non-damaging STAB, and add + after the STAB dmg array
                    if x.title() not in naturalMoves:
                        msg += '*'
                    msg += f'__{x.title()}__\n'
                    if found[9] != "":
                        msg += f'*{found[9]}*\n'
                    msg += f'**Type**: {found[0].capitalize()}'
                    msg += f' -- **{found[1].capitalize()}**\n'
                    msg += f'**Target**: {found[7]}'
                    msg += f' -- **Power**: {found[2]}\n'
                    numRolls = 4
                    totalDmg = (allAttr[found[3]] or 0) + (allAttr[found[4]] or 0) + int(found[2])
                    dmgArray = [sum([random.randint(0,1) for _ in range(totalDmg)]) for _ in range(numRolls)]
                    totalAcc = (allAttr[found[5]] or 0) + (allAttr[found[6]] or 0)
                    accArray = [sum([random.randint(0,1) for _ in range(totalAcc)])-accMod for _ in range(numRolls)]
                    if found[1].capitalize() != 'Support':
                        msg += f'**Dmg Mods**: {(found[3] or "None")} + {(found[4] or "None")} ' \
                               f'+ {found[2]} = ({totalDmg}'
                        msg += f'{" STAB" if found[0].capitalize() in (statlist[1],statlist[2]) else ""})'
                        msg += f' {dmgArray}\n' if pokebotsettings[guild][8] else '\n'
                    else:
                        msg += f'**Dmg Mods**: None\n'
                    msg += f'**Acc Mods**: {(found[5] or "None")} + {(found[6] or "None")} = '
                    msg += f'({(allAttr[found[5]] or 0)+(allAttr[found[6]] or 0)}'
                    msg += f" - {accMod} Successes)" if accMod != 0 else ")"
                    msg += f' {accArray}\n' if pokebotsettings[guild][8] else '\n'
                    msg += f'**Effect**: {found[8]}\n\n'
                except:
                    msg += f'__{x.title()}__\n\n'
        else:
            for x in movelist:
                msg += f'{x.title()}\n'

    return msg

#####

@bot.command(name = 'encounter', aliases = ['e', 'pokemon'],
             brief = 'Gets # poke at listed rank from a given list',
             help = 'Simple: %e poke(, poke2, list)\n'
                    '%encounter [1-6] [1-6 upper bound] [rank/base] <list of pokemon>\n'
                    '"base" means pokemon generated are at suggested ranks\n'
                    'e.g. %encounter 2 amateur eevee, squirtle, pidgey, list1')
async def pkmn_search_encounter(ctx, number : typing.Optional[int] = 1,
                                numberMax : typing.Optional[int] = None,
                                rank : typing.Optional[ensure_rank] = 'Base',
                                *, pokelist : (lambda x : x.split(', ')),
                                boss = False):
    #pokelist = pokelist.split(', ')
    guild = await getGuilds(ctx)
    if numberMax is not None:
        number = random.randint(number, numberMax)
    msg = await pkmn_encounter(ctx, number, rank, pokelist, boss = boss, guild = guild)
    if pokebotsettings[guild][10]:
        codify = True
    else:
        codify = False
    await send_big_msg(ctx, msg, codify = codify)

@bot.command(name = 'wEncounter', aliases = ['we'],
             brief = 'Weighted encounter. %help wEncounter',
             help = 'Simple: %we 95% poke1 5% poke2, list\n'
                    '%wEncounter [1-6] [1-6] (rank/base/random) <True/False> [num]% list [num]% poke1, poke2, list2 [num]% etc\n'
                    'Same as %encounter, but the lists are weighted. Have a common and rare encounter in'
                    'the same area? This is the command you want.\n'
                    'separatePools: True sticks to the list you draw first. False does not.\n'
                    '(x% chance for the list vs x% chance per pokemon)\n'
                    'e.g. %wEncounter 2 base False 95% eevee, squirtle 5% list1, porygon\n')
async def weighted_pkmn_search(ctx, number : typing.Optional[int] = 1,
                                numberMax : typing.Optional[int] = None,
                                rank : typing.Optional[ensure_rank] = 'Base',
                               separatePools : typing.Optional[bool] = False, *, pokelist : sep_weights):
    #separate the pokelist string into a list of tuples (int(chance), str(pokemon, pokemon))
    #pokelist = re.findall(pokeweight, pokelist)
    #make the values useable
    guild = await getGuilds(ctx)
    if numberMax is not None:
        number = random.randint(number, numberMax)
    odds = [int(x) for x,y in pokelist]
    pokelist = [y.strip(',').split(', ') for x,y in pokelist]
    if separatePools:
        msg = ''
        which = 0
        rand = random.randrange(1,101) - odds[0]
        while rand > 0 and which < len(odds) - 1:
            which += 1
            rand -= odds[which]
        msg += await pkmn_encounter(ctx, number, rank, pokelist[which])
    else:
        msg = ''
        for x in range(number):
            msg += f'**{x+1}**\n\n'
            which = 0
            rand = random.randrange(1,101) - odds[0]
            while rand > 0 and which < len(odds) - 1:
                which += 1
                rand -= odds[which]
            msg += await pkmn_encounter(ctx, 1, rank, pokelist[which])
    if pokebotsettings[guild][10]:
        codify = True
    else:
        codify = False
    await send_big_msg(ctx, msg, codify)

@bot.command(name = 'hEncounter', aliases = ['he'],
             brief = 'Habitat encounter. %help hEncounter',
             help = 'Simple: %he habitat\n'
                    '%encounter [1-6] [1-6] (rank/base/random) habitat 1, habitat 2, etc\n'
                    'Same as %encounter, but draws from the %habitat pools\n'
                    'Note: specifying a rank will only pull from pokemon with that suggested rank.\n'
                    'e.g. %hEncounter 2 beginner tide pools, field biomes\n')
async def habitat_pkmn_search(ctx, number : typing.Optional[int] = 1,
                                numberMax : typing.Optional[int] = None,
                                rank : typing.Optional[ensure_rank] = 'Base',
                               *, pokelist : sep_biomes):
    guild = await getGuilds(ctx)
    if numberMax is not None:
        number = random.randint(number, numberMax)
    msg = []
    for x in range(number):
        msg.append(await pkmn_encounter(ctx, 1, rank, pokelist,
                                        exact_rank = (True if rank != 'Base' else False)))
    out = ''
    for x in range(len(msg)):
        out += f'\n**{x+1}**.\n{msg[x]}'
    # msg = '\n\n'.join(msg)
    if pokebotsettings[guild][10]:
        codify = True
    else:
        codify = False
    await send_big_msg(ctx, out, codify)

@bot.command(name = 'boss', aliases = ['sEncounter', 'se'],
             brief = 'Gets # poke at listed rank from a given list with smart stats',
             help = 'Simple: %se poke(, poke2, list)\n'
                    '%sEncounter [1-6] [1-6 upper bound] [rank/base] <list of pokemon>\n'
                    '"base" means pokemon generated are at suggested ranks\n'
                    'e.g. %sEncounter 2 amateur eevee, squirtle, pidgey, list1')
async def smart_pkmn_search(ctx, number : typing.Optional[int] = 1,
                                numberMax : typing.Optional[int] = None,
                                rank : typing.Optional[ensure_rank] = 'Base',
                                *, pokelist : (lambda x : x.split(', '))):
    await pkmn_search_encounter(ctx = ctx, number = number, numberMax =  numberMax,
                                rank = rank, pokelist =  pokelist, boss = True)

#####

@bot.command(name = 'forms',
             aliases = ['form'],
             help = 'A way to find pokemon with forms or similar names.\n'
                    '`%forms Lycanroc` (Capitalization should not matter)')
async def form_finder(ctx, *, name : str = ''):
    query = f'SELECT name FROM pkmnStats WHERE name LIKE "%{name}%" ' \
            f'AND generation BETWEEN 1 AND 8'
    result = database.custom_query(query)
    if len(result) > 20:
        msg = f'Too many results with `{name}`. Try a longer string?'
    elif len(result) == 0:
        msg = f'No pokemon with `{name}` were found. Try a shorter string?'
    else:
        msg = '- ' + '\n- '.join([x[0] for x in result])
    await ctx.send(msg)

#####

@bot.command(name = 'tracker',
             aliases = ['statuses'],
             help = 'A tracker for status effects in battle.\n'
                    '%tracker add burn 1\n'
                    '%tracker or %tracker round\n'
                    '%tracker remove/del burn 1\n'
                    '%tracker change {1} burn 2 --> change the status in slot 1 to "burn 2"\n'
                    '%tracker remove/del all')
async def tracker(ctx, cmd = '', *, mc = ''):
    cmd = cmd.lower()
    mc = mc.title()
    name_key = ctx.author.id
    if name_key not in pokeStatus or not pokeStatus[name_key]:
        pokeStatus[name_key] = []
    if cmd == 'add':
        pokeStatus[name_key].append(mc)
        await ctx.message.add_reaction(getStatus(mc))

    elif cmd in ['del', 'remove']:
        try:
            bad = []
            if mc == 'All':
                del pokeStatus[name_key]
                await ctx.message.add_reaction('👍')
            else:
                #remove by index(es)
                try:
                    mc = sorted(re.split(', | |,', mc), reverse = True)
                    for x in mc:
                        ind = int(x) - 1
                        if ind < len(pokeStatus[name_key]):
                            await ctx.message.add_reaction(getStatus(pokeStatus[name_key].pop(ind)))
                        else:
                            bad.append(x)
                #remove by name
                except:
                    for x in mc:
                        try:
                            pokeStatus[name_key].remove(x)
                            await ctx.message.add_reaction(getStatus(x))
                        except:
                            bad.append(x)
            if len(bad) > 0:
                statlist = '\n'.join([f'[{x+1}] {y}' for x,y in enumerate(pokeStatus[name_key])])
                await ctx.send(f'{", ".join(bad)} not recognized in the list\n{statlist}')
        except IndexError:
            await ctx.send(f'{x} is out of range, you currently have {len(pokeStatus[name_key])} status effects')
        except KeyError:
            await ctx.send(f"{ctx.author} doesn't have any status effects")
        except:
            await ctx.send(f'"{mc}" not recognized as an index or status in the list')

    elif cmd in ['change', 'c']:
        where = int(mc.split()[0])-1
        if where < len(pokeStatus[name_key]):
            what = ' '.join(mc.split()[1:])
            pokeStatus[name_key][where] = what
            await ctx.message.add_reaction(getStatus(what))
        else:
            await ctx.message.add_reaction('❌')

    elif cmd in ['round', '']:
        if len(pokeStatus[name_key]) > 0:
            msg = "Status Effects:\n"
            for x in range(len(pokeStatus[name_key])):
                msg += f"[{x + 1}] {pokeStatus[name_key][x]}\n"
        else:
            msg = 'No current status effects'
        await ctx.send(msg)
    else:
        await ctx.send(f'{cmd} isn\'t a recognized command')

    save_obj(pokeStatus, 'pokeStatus')

@bot.command(name = 'rank',
             aliases = ['ranks'],
             help = 'Displays all bot recognized ranks.')
async def rankDisplay(ctx):
    await ctx.send(' - ' + '\n- '.join(ranks))

#####

@bot.command(name = 'feedback',
             aliases = ['fb', 'report', 'typo', 'bug'],
             help = 'Send feedback/suggestions/bug reports straight to my creator!')
async def feedback(ctx, *, info):
    await bot.appinfo.owner.send(f'{ctx.author.name}: {info}')
    await ctx.message.add_reaction('\N{HIBISCUS}')

@bot.command(name = 'donate',
             help = 'Support me!')
async def donate(ctx):
    link = r'https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=VD9LEYX4TKGUW&currency_code=USD'
    await ctx.send(embed = discord.Embed(title = 'Click here to donate!', url = link))

@bot.command(name = 'invite',
             aliases = ['inv'],
             help = 'Get the invite code')
async def invite(ctx):
    link = r'https://discord.com/oauth2/authorize?client_id=747930418702974983&scope=bot&permissions=2048'
    await ctx.send(embed = discord.Embed(title = 'Invite me!', url = link))

#####

#error handling:

@weighted_pkmn_search.error
async def info_error(ctx, error):
    if 'IndexError' in str(error):
        await ctx.send('Don\'t forget the percentages.\nFor example "40% bulbasaur, charmander 60% squirtle"')

@view_habitat.error
async def vh_error(ctx, info):
    await ctx.send(f'Make sure you type the biome name exactly (e.g. Ocean Biomes)\n'
                   f'*(This message self-destructs in 15 seconds)*',
                   delete_after=15)

if not dev_env:
    @bot.event
    async def on_command_error(ctx, error):
        global restartError
        msg = f"Error:\n{str(error)}\n*(This message self-destructs in 15 seconds)*"
        if restartError:
            msg += f'\n*Restarting... please give me a minute*'
        await ctx.send(msg, delete_after=15)

if not dev_env:
    @bot.event
    async def on_raw_reaction_add(payload):
        user = payload.user_id
        if user == bot.user.id:
            return
        channel = await bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if len(message.reactions) != 1 or message.reactions[0].count != 1:
            return
        if message.author != bot.user or message.content[0] != '#':
            return
        msg = message.content
        try:
            pkmn = msg[7:msg.find('\n')-2]
            query = f'SELECT ability, ability2, abilityhidden, abilityevent FROM pkmnStats WHERE name="{pkmn}"'
            query = database.custom_query(query)[0]
            ability = list(query)
            while '' in ability:
                ability.remove('')
            ability_expanded = [(await pkmnabilitieshelper(x)) for x in ability]

            output = ''
            for name, (effect, desc) in zip(ability, ability_expanded):
                output += f'**{name}:** {effect}\n'
                if desc != "":
                    output += f'-\n*{desc}*\n'
                output += '\n'

            await channel.send(output[:-2]) #-2 to remove the trailing \n 's

        except:
            pass

#####

for cog in cogs:
    bot.load_extension(cog)

bot.expand_list = pokesFromList
bot.big_msg = send_big_msg
bot.dictionary = lookup_poke

bot.run(token)