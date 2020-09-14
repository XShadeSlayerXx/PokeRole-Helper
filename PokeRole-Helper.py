import csv
import os
import pickle
import random
import re
import typing

import discord
from discord.ext import commands
from dotenv import load_dotenv
from symspellpy import SymSpell, Verbosity

load_dotenv()
token = os.getenv('POKEROLE_TOKEN')

bot = commands.Bot(command_prefix = '%')



#TODO: find and implement the environment modifiers
#TODO: compress more of the data in working memory
#   ++PokeLearns ranks complete
#   Need:
#   --PokeLearns moves (probably index the movelist and change all moves in pokelearns to an index?)



#settings {channel : [(shiny_chance, int), (ability, int), (secondary, int), (hidden, int),
# (show_encounter_move_desc, 0)]}
pokebotsettings = dict()

#pokemon moves
pkmnMoves = dict()
pkmnStats = dict()
pkmnLearns = dict()
pkmnItems = dict()
pkmnAbilities = dict()
pkmnHabitats = dict()

ranks = ['Starter', 'Beginner', 'Amateur', 'Ace', 'Pro', 'Master', 'Champion']
natures = ['Hardy (9)','Lonely (5)','Brave (9)','Adamant (4)','Naughty (6)',
           'Bold (9)','Docile (7)','Relaxed (8)','Impish (7)',
           'Lax (8)', 'Timid (4)', 'Hasty (7)', 'Serious (4)', 'Jolly (10)',
           'Naive (7)', 'Modest (10)', 'Mild (8)', 'Quiet (5)', 'Bashful (6)',
           'Rash (6)', 'Calm (8)', 'Gentle (10)', 'Sassy (7)', 'Careful (5)', 'Quirky (9)']

#lists are global...
#   pokemon list:
#{listName : [list] }
#   item list:
#{listName : [ 'i', [chance, item1, item2], [chance2, item3, item4], ... ]
pkmnLists = dict()

pokecap = re.compile(r'(^|[-( ])\s*([a-zA-Z])')
pokeweight = re.compile(r'(\d+)%?,? ([\-\',\sA-z]+)(?= \d|$)')

#...but need access privileges
#{user : [listName list] }
pkmnListsPriv = dict()

#add the dictionaries
poke_dict = SymSpell()
poke_dict.load_dictionary('PokeDictionary.txt', 0, 1, separator = '$')

# save and load functions
def save_obj(obj: object, name: str):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

# list of dictionary files
files = [('pkmnLists', pkmnLists), ('pokebotsettings', pokebotsettings), ('pkmnListsPriv', pkmnListsPriv)]

@bot.event
async def on_ready():
    global pkmnLists
    global pokebotsettings
    global pkmnListsPriv

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

#######
#converters

def sep_weights(arg) -> str:
    return re.findall(pokeweight, arg)

def ensure_rank(arg : str) -> str:
    arg = arg.title()
    if arg not in ranks and arg not in ['Base', 'Random']:
        raise commands.errors.ConversionError(f'{arg} is not a valid rank.')
    return arg

def pkmn_cap(arg : str) -> str:
    return re.sub(pokecap , lambda p: p.group(0).upper(), arg)

#######
#helper functions.... yeah I know

def lookup_poke(arg : str) -> str:
    suggestion =  poke_dict.lookup(arg, Verbosity.CLOSEST, max_edit_distance = 2,
                     include_unknown = True)[0]
    return suggestion.term

#######

@commands.is_owner()
@bot.command(name = 'restart', hidden = True)
async def restart(ctx):
    await ctx.message.add_reaction('\N{HIBISCUS}')
    await bot.logout()

@commands.is_owner()
@bot.command(name = 'reload', hidden = True)
async def reload(ctx, what):
    global pkmnItems, pkmnStats, pkmnMoves, pkmnLearns
    try:
        #will this work correctly? maybe change to global()?
        await globals()['instantiate'+what]()
        await ctx.message.add_reaction('\N{CYCLONE}')
    except:
        await ctx.send('ItemList, PkmnStatList, PkmnMoveList, PkmnLearnsList')

#######

@bot.command(name = 'docs',
             help = '--> A link to an easy to read file <--')
async def docs(ctx):
    await ctx.send('https://github.com/XShadeSlayerXx/PokeRole-Discord.py-Base/blob/master/PokeRoleBot-Docs.MD')

#######

#[ability1, ability2, ability3, shiny, show_move_desc, show ability desc, the item list used in encounter]
async def instantiateSettings(where : str):
    pokebotsettings[where] = [50,49,1,.00012, True, True, False]

@bot.command(name = 'settings',
             help = '%settings <setting_name> [value]\n'
                    'e.g. %settings ability_one_chance 50\n'
                    'List: (ability_one_chance value) (ability_two_chance value)\n'
                    '(ability_hidden_chance value) (shiny_chance value)\n'
                    '(show_move_description True/False)'
                    '(encounter_item <listname>)')
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
    if setting == 'show_ability_description' or setting == 'show_ability':
        if value[0].lower() == 't':
            pokebotsettings[guild][5] = True
        elif value[0].lower() == 'f':
            pokebotsettings[guild][5] = False
        else:
            await ctx.send('Setting "show_ability_description" may only be True or False')
    if setting == 'encounter_item' or setting == 'item':
        if value in pkmnLists and pkmnLists[value][0] == 'i':
            pokebotsettings[guild][6] = value
        else:
            pokebotsettings[guild][6] = False
            msg += f'{value} not found in the custom item list. Capitalization matters, is it misspelled?\n' \
                   f'Default set to False (no items).\n'
    temp = pokebotsettings[guild]
    await ctx.send(f'{msg}'
                   f'Current settings:\n(Ability1/Ability2/AbilityHidden)\n**{temp[0],temp[1],temp[2]}**\n'
                   f'Shiny chance: {temp[3]} out of 1, **{temp[3]*100}%**\n'
                   f'Show move descriptions in %encounter: **{temp[4]}**\n'
                   f'Show ability description in %encounter: **{temp[5]}**\n'
                   f'Items in %encounter? {temp[6]}\n'
                   f'"%help settings" for help')
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
    up = True
    for x, y in pkmnLists.items():
        try:
            item = y[0] == 'i'
        except:
            item = False
        if item:
            howMany = len([0 for _,items in y[1:] for item in items])
        else:
            howMany = len(y)
        msg += ('\n - ' if up else ' / ') + f'{x} ({str(howMany) + (" i" if item else "")})'
        up = not up
    await ctx.send(msg)

@bot.command(name = 'list', aliases=['l'], help = '%list <listname> (add/show/del) poke1, poke2, etc\n'
                                   'or %list <listname> (add/show/del) 43% item1, item2, 10% item3, item4, etc\n'
                                   'In this case, the remaining 47% is no item, for %encounter and %random purposes.\n'
                                   'Lists are unique to people - don\'t forget everyone can see them!\n'
                                   'Use "%list <listname> access @mention" to give edit permissions to someone\n'
                                   'Their user id will also work (right click their profile --> copy id)')
async def pkmn_list(ctx, listname : str, which = 'show', *, pokelist = ''):
    areListsBroken = [x for x in list(pkmnLists.keys())]
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
    if ctx.author.id not in pkmnListsPriv:
        pkmnListsPriv[ctx.author.id] = []
    if which != 'access':
        pokelist = [pkmn_cap(x.strip()) for x in pokelist.split(',')]
        if len(pokelist)==1:
            pokelist = [pkmn_cap(x.strip()) for x in pokelist[0].split(' ')]
        bad = []
        correct = []
        tempmsg = ''
        #check for misspelled pokemon
        for x in pokelist:
            try:
                int(x[0])
                isItem = True
                break
            except:
                pass
            if x not in pkmnStats:
                bad.append(x)
                if x in pkmnLists:
                    tempmsg+=f'{x} : '+', '.join(pkmnLists[x])+'\n'
                else:
                    correct.append(lookup_poke(x))
        if not isItem and len(bad) > 0 and which == 'add':
            if tempmsg != '':
                tempmsg ='Right now, you can\'t have a list inside of a list:\n'+tempmsg
            for name in range(len(bad)):
                tempmsg += f'{bad[name]} --> {correct[name]}  |  '
            await ctx.send(f'{tempmsg[:-4]}\nThe list "{listname}" was not changed.')
            return
    if isItem:
        pokelist = re.findall(pokeweight, ', '.join(pokelist))
        pokelist = [(int(x), y.strip(',').split(', ')) for x,y in pokelist]
        bad = []
        for _,itemlist in pokelist:
            for item in itemlist:
                if item not in pkmnItems:
                    bad.append(item)
        if len(bad) > 0:
            await ctx.send(f'These were not recognized as items:\n{str(bad)}\n(List not changed.)')
            return
    if listname not in pkmnLists:
        pkmnLists[listname] = []
        if isItem:
            pkmnLists[listname].append('i')
        if ctx.author.id in pkmnListsPriv:
            pkmnListsPriv[ctx.author.id].append(listname)
        else:
            pkmnListsPriv[ctx.author.id] = [listname]
    if which == 'show':
        if len(pkmnLists[listname]) > 0:
            if isItem:
                msg = ''
                temp = pkmnLists[listname][1:]
                for item in temp:
                    msg += f'{str(item[0])}% - '
                    msg += ', '.join([a for b in item[1:] for a in b])
                    msg += ' | '
                await ctx.send(msg[:-3])
            else:
                await ctx.send(', '.join(pkmnLists[listname]))
        else:
            await ctx.send(f'List {listname} is empty')
    elif listname in pkmnListsPriv[ctx.author.id]:
        if which == 'add':
            for x in pokelist:
                pkmnLists[listname].append(x)
            await ctx.send(f'Successfully added.')
        elif which in ['del', 'delete', 'remove']:
            if not pokelist or pokelist == ['']:
                try:
                    msg = ', '.join(pkmnLists[listname])
                except:
                    msg = str(pkmnLists[listname])
                del pkmnLists[listname]
                await ctx.send(f'Everything ({msg}) was removed from list "{listname}"')
            else:
                msg = []
                if not isItem:
                    for x in pokelist:
                        try:
                            pkmnLists[listname].remove(x)
                        except:
                            msg.append(x)
                    if len(msg) > 0:
                        await ctx.send(f'Could not remove {", ".join(msg)}')
                    else:
                        await ctx.send(f'Successfully removed the pokemon.')
                else:
                    templist = [item for sublist in pkmnLists[listname][1:] for item in sublist]
                    for x in templist:
                        try:
                            templist.remove(x)
                        except:
                            msg.append(x)
                    if len(msg) > 0:
                        await ctx.send(f'Could not remove {", ".join(msg)}')
                    else:
                        await ctx.send(f'Successfully removed the items.')
                    templist = re.findall(pokeweight, ', '.join(templist))
                    pkmnLists[listname] = ['i'] + [[int(x), y] for x,y in templist]
        elif which == 'access':
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
                    pkmnListsPriv[temp].append(listname)
                except:
                    pkmnListsPriv[temp] = [listname]
                await ctx.send(f'Access given to {bot.get_user(temp)}')
    elif listname not in pkmnListsPriv[ctx.author.id]:
        users = [str(bot.get_user(x)) for x in pkmnListsPriv if listname in pkmnListsPriv[x]]
        if len(users) > 0:
            await ctx.send(f'{", ".join(users)} {"have" if len(users)>1 else "has"} '
                           f'edit access to this. Please ask {"one of" if len(users)>1 else ""} '
                           f'them to "%list {listname} access @mention" if you want access')
        else:
            pkmnListsPriv[ctx.author.id].append(listname)
            await ctx.send(f'No users linked to this list. You now have permission, please try again.')
    try:
        if isItem and pkmnLists[listname][0] != 'i':
            pkmnLists[listname].insert(0, 'i')
    except:
        pass
    await ctx.message.add_reaction('\N{CYCLONE}')
    save_obj(pkmnListsPriv, 'pkmnListsPriv')
    save_obj(pkmnLists, 'pkmnLists')
    if len(pkmnLists.keys()) < len(areListsBroken) - 1:
        await bot.appinfo.owner.send(f'{listname} {which} {pokelist}')

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
    bad = []
    if pkmnLists[list2][0] == 'i':
        skip = 1
    else:
        skip = 0
    for x in pkmnLists[list2][skip:]:
        try:
            pkmnLists[list1].remove(x)
            bad.append(x)
        except:
            pass
    await ctx.send(f'{", ".join(bad)}\n{"were" if len(bad) > 1 else "was"} removed from {list1}')

#######

#returns a random pokemon or item from given list
def pkmn_random_driver(listname : str) -> str:
    itemList = False
    if listname not in pkmnLists:
        return 'There was not a list with this name.\n'
    if pkmnLists[listname][0] == 'i':
        itemList = True
    if itemList:
        #remove the leading 'i'
        temp = pkmnLists[listname][1:]
        which = 0
        choice = True
        rand = random.randrange(1,101) - int(temp[0][0])
        while rand > 0 and which < len(temp):
            which += 1
            if which == len(temp):
                choice = False
                break
            rand -= int(temp[which][0])
        if choice:
            return random.choice(temp[which][1])
        else:
            return 'None'
    else:
        return random.choice(pkmnLists[listname])
    return 'None'

@bot.command(name = 'random', aliases = ['rl'],
             help = 'Get a random item/poke from a list.')
async def pkmn_randomitem_driver(ctx, listname : str):
    await ctx.send(pkmn_random_driver(listname))

#######

async def which_generation(gen : int) -> tuple:
    starters = ['Bulbasaur', 'Chikorita', 'Treecko', 'Turtwig', 'Snivy', 'Chespin', 'Rowlet', 'Grookey']
    start = 0
    end = 0
    #make sure the list is instantiated
    gen = sorted((0,8,gen))[1]
    try:
        start = list(pkmnStats).index(starters[gen-1])
    except:
        await instantiatePkmnStatList()
    if gen == 8:
        end = len(pkmnStats)
    else:
        end = list(pkmnStats).index(starters[gen])
    return start, end

@bot.command(name = 'filter', aliases = ['f'],
             help = '%filter <listname> <rank> <type1> <type2> [includeLowerRanks T/F]'
                                     ' <generation>\n'
                                     'type2 - can also be Any or None\n'
                                     'includeLowerRanks - if <rank> is ace, do you want starter/beginner/amateur/ace?\n'
                                     'generation - any number between 1 and 8 (kanto through galar)\n'
                                     '%filter forest beginner grass None\n'
                                     '  --> Adds beginner rank grass types to the list forest\n'
                                     '%filter forest ace bug any True 6\n'
                                     '  --> Adds up to Ace rank bug/Any types from gen 6 to the list forest')
async def pkmn_filter_list(ctx, listname : str, rank : ensure_rank,
                           type1 : str, type2 : str = 'Any',
                           includeLowerRanks : bool = False, generation : int = 0):
    type1 = type1.title()
    type2 = type2.title()

    #which ranks to find
    if includeLowerRanks:
        rank = ranks[:ranks.index(rank)+1]
    else:
        rank = [rank]
    if 0 < generation < 9:
        gen = await which_generation(generation)
    else:
        try:
            pkmnStats['Bulbasaur']
        except:
            await instantiatePkmnStatList()
        gen = (0, len(pkmnStats))
    filtered = []
    for x in list(pkmnStats.items())[gen[0]:gen[1]]:
        if x[1][-2] in rank and x[1][1] == type1:
            if type2 == 'Any' or type2 == x[1][2] or type2 == 'None' and x[1][2] == '':
                filtered.append(pkmn_cap(x[0]))

    #send the filtered list to %list then print it
    await pkmn_list(ctx = ctx, listname = listname, which = 'add', pokelist = ', '.join(filtered))
    await ctx.send(f'Pokemon in {listname}:')
    await pkmn_list(ctx = ctx, listname = listname, which = 'show')

#######

async def instantiateItemList():
    with open('PokeRoleItems.csv', 'r', encoding = "UTF-8") as file:
        reader = csv.reader(file)
        head = ''
        for row in reader:
            if row[1] == '':
                head = row[0]
                continue
            if head in pkmnItems:
                pkmnItems[head].append(row[0])
            else:
                pkmnItems[head] = [row[0]]
            pkmnItems[row[0]] = row[1:]
        pkmnItems.pop('Name')
        pkmnItems.pop('')

async def pkmnitemhelper(item):
    if len(pkmnItems.keys()) == 0:
        await instantiateItemList()
    return pkmnItems[item]

@bot.command(name = 'item', alias = ['items', 'i'], help = 'List an item\'s traits. "%item" for categories.')
async def pkmn_search_item(ctx, *, itemname = ''):
    try:
        itemname = itemname.title()
        found = await pkmnitemhelper(itemname)
    except:
        pass
    if itemname != '':
        try:
            output = f'__{itemname}__\n'

            if found[0] not in pkmnItems:
                order = [0,'Type Bonus', 'Value', 'Strength', 'Dexterity', 'Vitality', 'Special', 'Insight', 'Defense',
                         'Special Defense', 'Evasion', 'Accuracy', 0, 'Heal Amount']
                #this is an actual item
                output += f'**Price**: {found[-1] or "???"}\n'
                if found[13] != '':
                    output += f'**Pokemon**: {", ".join(found[-3])}\n'
                for name in range(1,len(order)):
                    if name == 13:
                        continue
                    if found[name] != '':
                        output += f'**{order[name]}**: {found[name]}\n'
                output += f'**Description**: {found[0].capitalize()}'
            else:
                #this is a category
                for x in range(len(found)):
                    output += f' - {found[x]}\n'
            await ctx.send(output)
        except:
            await ctx.send(f'{itemname} wasn\'t found in the item list.')
    else:
        temp = []
        for key in list(pkmnItems.keys()):
            if pkmnItems[key][0] in pkmnItems:
                temp.append(key)
        msg = ' - '
        wbool = False
        for x in temp:
            msg += x + ('\n - ' if wbool else ' / ')
            wbool = not wbool
        await ctx.send(msg)

#######

async def instantiateHabitatsList():
    with open('habitats.csv', 'r', encoding = 'UTF-8') as file:
        reader = csv.reader(file)
        head = ''
        for row in reader:
            if row[1] == '':
                head = row[0]
                continue
            if head not in pkmnHabitats:
                pkmnHabitats[head] = ['biome']
            pkmnHabitats[head].append(row[0])
        pkmnHabitats[row[0]] = row[1:]

async def pkmnhabitatshelper(habitat):
    if len(pkmnHabitats.keys()) == 0:
        await instantiateHabitatsList()
    return pkmnHabitats[habitat]

async def pkmnhabitatranks(pokemon : list) -> dict:
    level = dict()
    for poke in pokemon:
        rank = (await pkmnstatshelper(poke))[20]
        if rank not in level:
            level[rank] = []
        level[rank].append(poke)
    return level

@bot.command(name = 'habitat', aliases = ['biome'],
             help = 'List the pokemon for a biome that theworldofpokemon.com suggests.',
             hidden=True)
async def pkmn_search_habitat(ctx, *, habitat : str = ''):
    try:
        habitat = habitat.title()
        found = await pkmnhabitatshelper(habitat)
    except:
        pass
    if habitat != '':
        try:
            output = f'__{habitat}__\n'

            if found[0] != 'biome':
                # this is a biome with pokebois
                level = await pkmnhabitatranks(found)
                for rank, pokes in list(level.items()):
                    output += f'**{rank}**\n'
                    output += '  |  '.join(pokes) + '\n'
                await ctx.send(output)
            else:
                # this is an overarching theme
                output += ' - '
                wbool = False
                for x in found[1:]:
                    output += x + ('\n - ' if wbool else ' / ')
                    wbool = not wbool
                await ctx.send(output)
        except:
            await ctx.send(f'{habitat} wasn\'t found in the habitat list.')
    else:
        temp = []
        for key in list(pkmnHabitats.keys()):
            if pkmnHabitats[key][1] == 'biome':
                temp.append(key)
        msg = ' - '
        wbool = False
        for x in temp:
            msg += x + ('\n - ' if wbool else ' / ')
            wbool = not wbool
        await ctx.send(msg)

@bot.command(name = 'filterhabitat', aliases = ['fh'],
             help = '%filterhabitat <list> <rank=All> <includeLowerRanks=True> <habitat>\n'
                    'Transcribe pokemon from a habitat into a list (optionally by rank)',
             hidden = True)
async def pkmn_filter_habitat(ctx, listname : str, rank : typing.Optional[ensure_rank] = 'Master',
                              includeLowerRanks : typing.Optional[bool] = True, *, habitat : str):
    habitat = habitat.title()
    try:
        found = await pkmnhabitatshelper(habitat)
    except:
        await ctx.send(f'{habitat} wasn\'t recognized as a habitat.')
        return

    ranklist = await pkmnhabitatranks(found)
    ranklist = list(ranklist.items())
    if ranks[rank] < ranks['Master']:
        for i, key in enumerate(ranklist):
            if not includeLowerRanks and ranks[rank] == ranks[key[0]]:
                ranklist = ranklist[i]
                break
            elif ranks[key] > ranks[rank]:
                ranklist = ranklist[:i]
    pokes = []
    for poketuples in ranklist:
        for x in poketuples[1]:
            if x not in pkmnLists[listname]:
                pokes.append(x)
            else:
                # for wormadam and all them
                pokes.append(random.choice(pkmnLists[listname]))
    await pkmn_list(ctx, listname, 'add', ', '.join(pokes))

#######

async def instantiateAbilitiesList():
    with open('PokeRoleAbilities.csv', 'r', encoding = "UTF-8") as file:
        reader = csv.reader(file)
        head = ''
        for row in reader:
            if row[1] == '':
                head = row[0]
                continue
            if head in pkmnAbilities:
                pkmnAbilities[head].append(row[0])
            else:
                pkmnAbilities[head] = [row[0]]
            pkmnAbilities[row[0]] = row[1:]
        pkmnAbilities.pop('Name')
        pkmnAbilities.pop('')

async def pkmnabilitieshelper(ability):
    if len(pkmnAbilities.keys()) == 0:
        await instantiateAbilitiesList()
    return pkmnAbilities[ability.title()]

@bot.command(name = 'ability', aliases = ['a'], help = 'List a pokemon ability\'s traits')
async def pkmn_search_ability(ctx, *, abilityname : str):
    try:
        abilityname = abilityname.title()
        found = await pkmnabilitieshelper(abilityname)

        output = f'**{abilityname}:** {found[0]}'

        await ctx.send(output)
    except:
        await ctx.send(f'{abilityname} wasn\'t found in the ability list.')

#######

async def instantiatePkmnMoveList():
    with open('pokeMoveSorted.csv', 'r', newline = '', encoding = "UTF-8") as infile:
        reader = csv.reader(infile)
        for row in reader:
            pkmnMoves.update({row[0]: row[1:]})

async def pkmnmovehelper(move):
    if len(pkmnMoves.keys()) == 0:
        await instantiatePkmnMoveList()
    return pkmnMoves[move.title()]

@bot.command(name = 'move', aliases = ['m'], help = 'List a pokemon move traits')
async def pkmn_search_move(ctx, *, movename : str):
    try:
        found = await pkmnmovehelper(movename.title())

        output = f'__{movename.title()}__\n'
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

#####

async def instantiatePkmnStatList():
    with open('PokeroleStats.csv', 'r', newline = '', encoding = "WINDOWS-1252") as infile:
        reader = csv.reader(infile)
        for row in reader:
            pkmnStats.update({row[1]: [row[0]] + row[2:]})

async def pkmnstatshelper(poke : str):
    if len(pkmnStats.keys()) == 0:
        await instantiatePkmnStatList()
    return pkmnStats[poke]

@bot.command(name = 'stats', aliases = ['s'], help = 'List a pokemon\'s stats')
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
    output += f'**Base HP**: {found[3]}\n'
    output += f'**Strength**: {found[4]}{found[5]}\n'
    output += f'**Dexterity**: {found[6]}{found[7]}\n'
    output += f'**Vitality**: {found[8]}{found[9]}\n'
    output += f'**Special**: {found[10]}{found[11]}\n'
    output += f'**Insight**: {found[12]}{found[13]}\n'
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

async def instantiatePkmnLearnsList():
    ranks = {'Starter': 0, 'Beginner': 1, 'Amateur': 2, 'Ace': 3, 'Pro': 4, 'Master': 5, 'Champion': 6}
    with open('PokeLearnMovesFull.csv', 'r', newline = '', encoding = "UTF-8") as infile:
        reader = csv.reader(infile)
        for row in reader:
            value = row[1:]
            value[1::2] = [ranks[x] for x in value[1::2]]
            pkmnLearns.update({row[0][4:]: value})

async def pkmnlearnshelper(poke : str, rank : ensure_rank = 'Master'):
    if len(pkmnLearns.keys()) == 0:
        await instantiatePkmnLearnsList()
    rankorder = ['Starter', 'Beginner', 'Amateur', 'Ace', 'Pro', 'Master', 'Champion']
    found = pkmnLearns[poke]
    found[1::2] = [rankorder[x] for x in found[1::2]]
    done = False
    moves = dict()
    for x in range(0, len(found), 2):
        if done:
            break
        if found[x + 1] not in moves:
            if rank == 'Master' or rankorder.index(found[x+1]) <= rankorder.index(rank):
                moves[found[x + 1]] = [found[x]]
            else:
                done = True
        else:
            moves[found[x + 1]].append(found[x])

    return moves

@bot.command(name = 'pokelearns',
             aliases = ['canlearn', 'pl'],
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

async def pkmn_encounter(ctx, number : int, rank : str, pokelist : list) -> str:
    try:
        guild = ctx.guild.id
    except:
        guild = ctx.author.id
    if guild not in pokebotsettings:
        await instantiateSettings(guild)
    msg = ''
    rankrandom = False
    rankbase = False
    #rank = rank.title()
    if rank == 'Random':
        rankrandom = True
    if rank == 'Base':
        rankbase = True

    tempList = []
    for name in pokelist:
        name = name.strip()
        try:
            for x in pkmnLists[name]:
                tempList.append(x)
        except:
            tempList.append(name)
            #pokelist = [x.strip().title() for x in pokelist.split(',')]
            #if len(pokelist)==1:
            #    pokelist = [x.strip().title() for x in pokelist[0].split(' ')]
    pokelist = [pkmn_cap(item) for item in tempList]

    if number > 6:
        msg+='Can only create up to 6 pokes at once due to size\n'
        number = 6
    elif number < 1:
        number = 1

    if len(pokelist) == 0:
        return 'Need at least one pokemon in the list!'

    #exceptions for master rank: 6 extra social, HP + 2, DEF/S.DEF + 2

    #total attributes at a rank (base/social)
    #attributes are limited by poke
    attributeAmount = [0,2,4,6,8,8,14]
    #total skill points at a rank
    skillAmount = [5,9,12,14,15,15,16]
    #highest any single skill can be
    limit = [1,2,3,4,5,5,5]

    for pokeamount in range(number):
        #initialize base stats

        #no limits on socials (except max of 5)
        socials = [('Tough',1), ('Cool',1), ('Beauty',1), ('Clever',1), ('Cute',1)]
        #limited by rank
        skills = [('Brawl',0),('Channel',0),('Clash',0),('Evasion',0),
                  ('Alert',0),('Athletic',0),('Nature',0),('Stealth',0),
                  ('Allure',0),('Etiquette',0),('Intimidate',0),('Perform',0)]

        #get a poke from the list
        nextpoke = random.choice(pokelist)
        #get the attributes
        try:
            statlist = await pkmnstatshelper(nextpoke)
        except:
            nextpoke = lookup_poke(nextpoke)
            statlist = await pkmnstatshelper(nextpoke)
        if rankbase:
            #20 is suggested rank
            rank = statlist[20].title()
        if rankrandom:
            #just give them an arbitrary rank
            rank = random.choice(ranks[:-1])
        rankIndex = ranks.index(rank)
        #get all potential moves, up to the rank
        try:
            movelist = await pkmnlearnshelper(nextpoke, rank)
        except:
            movelist = []

        #3/4/6/8/10/12 == b.hp/str/dex/vit/spe/ins
        attributes = [int(statlist[3])] + [int(statlist[x]) for x in range(4, 13, 2)]

        baseattr = [x for x in attributes]
        maxattr = [0] + [int(statlist[x]) for x in range(5, 14, 2)]

        #pls dont crash the bot if something is messed up
        sanity = 30

        #distribute socials
        x = 0
        if rank == 'Master':
            extraSocial = 6
        else:
            extraSocial = 0
        while x < attributeAmount[rankIndex] + extraSocial and sanity > 0:
            temp = random.randint(1,len(socials))-1
            if socials[temp][1] < limit[rankIndex]:
                socials[temp] = (socials[temp][0], socials[temp][1] + 1)
                x = x + 1
            else:
                sanity = sanity - 1

        #distribute skills
        x = 0
        while x < skillAmount[rankIndex] and sanity > 0:
            temp = random.randint(1,len(skills))-1
            if skills[temp][1] < limit[rankIndex]:
                skills[temp] = (skills[temp][0], skills[temp][1] + 1)
                x = x + 1
            else:
                sanity = sanity - 1

        #only legendaries learn 'master' moves --> ensure its not a legendary
        if 'Master' not in movelist:
            #distribute stats last bc of legendaries
            x = 0
            while x < attributeAmount[rankIndex] and sanity > 0:
                #between 2 and max bc HP is at #0
                temp = random.randint(2,len(attributes))-1
                if attributes[temp] < maxattr[temp]:
                    attributes[temp] = attributes[temp] + 1
                    x = x + 1
                else:
                    sanity = sanity - 1

        #cut the movelist down to this number
        newMoves = []
        movelist = list(movelist.values())
        movelist = [item for sublist in movelist for item in sublist]
        for x in range(attributes[5] + 2):
            if len(movelist) == 0:
                break
            temp = random.choice(movelist)
            newMoves.append(temp)
            movelist.remove(temp)
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
        #calculate hp
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

        #if there's only one number then skip this
        if number != 1:
            msg += f'**{pokeamount+1}**.\n\n'
        msg += f'__{nextpoke}__  |  **{rank}**'
        msg += f'  |  {random.choice(natures)}'
        msg += (f'  |  ***SHINY***' if pokebotsettings[guild][3] >= random.random() else f'')

        msg += f'\n**Type**: {statlist[1]}{"" if statlist[2] == "" else "/"+statlist[2]}\n'

        #ability
        msg += f'**Ability:** {ability}\n'

        #item
        msg += f'**Item:** {item}\n'

        #⬤⦿⭘
        just = 0
        fullattr = [0]
        for attr in range(1,len(attributes)):
            a = int(baseattr[attr])
            b = int(attributes[attr])
            c = int(maxattr[attr])
            if c > just:
                just = c
            baseattr[attr] = '⬤'*a
            attributes[attr] = '⦿'*(b-a)
            maxattr[attr] = '⭘'*(c-b)
            fullattr.append(baseattr[attr]+attributes[attr]+maxattr[attr])
            d = int(socials[attr-1][1])
            socials[attr-1] = (socials[attr-1][0],'⬤'*d + '⭘'*(5-d))
        just += 12
        msg += f'**Total HP:** {attributes[0]}\n'
        msg += ('**Str:** '+fullattr[1]).ljust(just)+f' -- **{socials[0][0]}:**  {socials[0][1]}\n'
        msg += ('**Dex:** '+fullattr[2]).ljust(just)+f' -- **{socials[1][0]}:**  {socials[1][1]}\n'
        msg += ('**Vit:** '+fullattr[3]).ljust(just)+f' -- **{socials[2][0]}:**  {socials[2][1]}\n'
        msg += ('**Spe:** '+fullattr[4]).ljust(just)+f' -- **{socials[3][0]}:**  {socials[3][1]}\n'
        msg += ('**Ins:** '+fullattr[5]).ljust(just)+f' -- **{socials[4][0]}:**  {socials[4][1]}\n'



        #add the attributes + socials
        # msg += f'**Total HP:** {attributes[0]}\n'
        # msg += f'**Str `({baseattr[1]}-{maxattr[1]}):`** {attributes[1]}  | '
        # msg += f'**{socials[0][0]}:**  {socials[0][1]}\n'
        # msg += f'**Dex `({baseattr[2]}-{maxattr[2]}):`** {attributes[2]}  | '
        # msg += f'**{socials[1][0]}:**  {socials[1][1]}\n'
        # msg += f'**Vit `({baseattr[3]}-{maxattr[3]}):`** {attributes[3]}  | '
        # msg += f'**{socials[2][0]}:**  {socials[2][1]}\n'
        # msg += f'**Spe `({baseattr[4]}-{maxattr[4]}):`** {attributes[4]}  | '
        # msg += f'**{socials[3][0]}:**  {socials[3][1]}\n'
        # msg += f'**Ins `({baseattr[5]}-{maxattr[5]}):`** {attributes[5]}  | '
        # msg += f'**{socials[4][0]}:**  {socials[4][1]}\n'

        msg+= '\n'

        #add the socials (4 rows, 3 per line)
        for x in range(0,12,4):
            for y in range(4):
                msg += f'**{skills[x+y][0]}:**'.ljust(11) + ' '+str(skills[x+y][1]) + (' - ' if y!= 3 else '')
            msg+='\n'

        if pokebotsettings[guild][5] and abilitytext != '':
            msg += f'\n**{ability}**: {abilitytext[0]}\n'

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
                    found = await pkmnmovehelper(x)
                    if found[8][-9:-1] == 'Accuracy':
                        try:
                            accMod = int(found[8][-11])
                        except:
                            accMod = 0
                    else:
                        accMod = 0
                    msg += f'__{x.title()}__\n'
                    msg += f'**Type**: {found[0].capitalize()}'
                    msg += f' -- **{found[1].capitalize()}**\n'
                    msg += f'**Target**: {found[7]}'
                    msg += f' -- **Power**: {found[2]}\n'
                    msg += f'**Dmg Mods**: {(found[3] or "None")} + {(found[4] or "None")} ' \
                           f'+ {found[2]} = ' \
                           f'({(allAttr[found[3]] or 0)+(allAttr[found[4]] or 0)+int(found[2])}'
                    msg += f'{" STAB" if found[0].capitalize() in (statlist[1],statlist[2]) else ""})\n'
                    msg += f'**Acc Mods**: {(found[5] or "None")} + {(found[6] or "None")} = '
                    msg += f'({(allAttr[found[5]] or 0)+(allAttr[found[6]] or 0)}'
                    msg += f" - {accMod} Successes)\n" if accMod != 0 else ")\n"
                    msg += f'**Effect**: {found[8]}\n\n'
                except:
                    msg += f'__{x.title()}__\n\n'
        else:
            for x in movelist:
                msg += f'{x.title()}\n'


#    msglist = [msg]
#    while len(msglist[-1]) > 1995:
#        tempmsg = msglist[-1]
#        temp = tempmsg.rindex('\n',1500,1995)
#        msglist[-1] = tempmsg[:temp]
#        msglist.append(tempmsg[temp:])
#    for x in msglist:
#        await ctx.send(x)
    return msg

#####


@bot.command(name = 'encounter', aliases = ['e'],
             brief = 'Gets # poke at listed rank from a given list',
             help = 'Simple: %e poke(, poke2, list)\n'
                    '%encounter [1-6] (rank/base/random) <list of pokemon>\n'
                    '"base" means pokemon generated are at suggested ranks\n'
                    'e.g. %encounter 2 random eevee, squirtle, pidgey, list1')
async def pkmn_search_encounter(ctx, number : typing.Optional[int] = 1,
                                rank : typing.Optional[ensure_rank] = 'Base',
                                *, pokelist : (lambda x : x.split(', '))):
    #pokelist = pokelist.split(', ')
    msg = await pkmn_encounter(ctx, number, rank, pokelist)
    msglist = [msg]
    while len(msglist[-1]) > 1995:
        tempmsg = msglist[-1]
        temp = tempmsg.rindex('\n', 1500, 1995)
        msglist[-1] = tempmsg[:temp]
        msglist.append(tempmsg[temp:])
    for x in msglist:
        await ctx.send(x)

@bot.command(name = 'wEncounter', aliases = ['we'],
             brief = 'Weighted encounter. %help wEncounter',
             help = 'Simple: %we 95% poke1 5% poke2, list\n'
                    '%encounter [1-6] (rank/base/random) <True/False> [num]% list [num]% poke1, poke2, list2 [num]% etc\n'
                    'Same as %encounter, but the lists are weighted. Have a common and rare encounter in'
                    'the same area? This is the command you want.\n'
                    'separatePools: True sticks to the list you draw first. False does not.\n'
                    '(x% chance for the list vs x% chance per pokemon)\n'
                    'e.g. %wEncounter 2 base False 95% eevee, squirtle 5% list1, porygon\n')
async def weighted_pkmn_search(ctx, number : typing.Optional[int] = 1,
                                rank : typing.Optional[ensure_rank] = 'Base',
                               separatePools : typing.Optional[bool] = False, *, pokelist : sep_weights):
    #separate the pokelist string into a list of tuples (int(chance), str(pokemon, pokemon))
    #pokelist = re.findall(pokeweight, pokelist)
    #make the values useable
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
    msglist = [msg]
    while len(msglist[-1]) > 1995:
        tempmsg = msglist[-1]
        temp = tempmsg.rindex('\n',1500,1995)
        msglist[-1] = tempmsg[:temp]
        msglist.append(tempmsg[temp:])
    for x in msglist:
        await ctx.send(x)

@bot.command()
async def test(ctx):
    ctx.send('test')

#error handling:

@weighted_pkmn_search.error
async def info_error(ctx, error):
    if 'IndexError' in str(error):
        await ctx.send('Don\'t forget the percentages.\nFor example "40% bulbasaur, charmander 60% squirtle"')

@bot.event
async def on_command_error(ctx, error):
  await ctx.send(f"Error:\n{str(error)}\n*(This message self-destructs in 15 seconds)*", delete_after=15)

#####

bot.run(token)