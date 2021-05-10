from discord.ext import commands
from discord import File
from typing import Optional
from PIL import Image

import random
import os
import math

fileprefix = r'./pokeMap/tiles/'
eventprefix = r'./pokeMap/event_icons/'
BKGD_CROSS_PATH = r'./pokeMap/cross.png'

MAX_MAP_SIZE = 11
TILE_WIDTH = 174
# FLIP_CHANCE = .5
FLIP_CHANCE = 0
ENQUEUE_CHANCE = .4
BKGD_COLOR = 0x828282
#FILL_COLOR = 0xb7b7b7
TILE_GLOW = 14

#TODO:
# allow mixing tiles? combine 2 and choose the lightest colors for new tiles?

#which events should be shown on the map?
event_list = [
    ('treasure', 1),
    ('enemy', 1),
    ('trap', 1),
    ('hazard', 1),
    ('guild', 1),
    ('nothing', 1)
]

event_colors = {
    'treasure': 0x001100,
    'enemy': 0x000011,
    'trap': 0x001111,
    'hazard': 0x111100,
    'guild': 0x110000,
    'nothing': 0x101010
}

# color-blind friendly?
# event_colors = {
#     'treasure': 0xFFB000,
#     'enemy': 0xDC267F,
#     'trap': 0xFE6100,
#     'hazard': 0x785EF0,
#     'guild': 0x648FFF,
#     'nothing': 0
# }

event_icons = {
    'treasure': f'{eventprefix}bag2_small.png',
    'enemy': f'{eventprefix}skull_small.png',
    'trap': f'{eventprefix}confuse_trap_small.png',
    'hazard': f'{eventprefix}question_small.png',
    'guild': f'{eventprefix}accessory_small.png'
}

#store the images in this array on startup
tiles = []

#TODO: hardcode these for now? (rename the pictures to be descriptive?)
#organize the tiles based on which directions are available via index
tileMaps = {
    0 : [], #center. TODO: do something with these?
    1 : [], #UP
    2 : [], #UP-RIGHT
    3 : [], #RIGHT
    4 : [], #DOWN-RIGHT
    -1 : [], #DOWN
    -2 : [], #DOWN-LEFT
    -3 : [], #LEFT
    -4 : [] #UP-LEFT
}

tileSlots = [-4, 1, 2, -3, 0, 3, -2, -1, 4]
rotationMatrix = [1, 2, 3, 4, -1, -2, -3, -4]

def blend_hex(h1, h2):
    try:
        h1 = int(h1, 16)
    except:
        pass
    try:
        h2 = int(h2, 16)
    except:
        pass
    final = (h1 + h2) // 2
    return final

def get_random_tile(which = 0):
    return random.choice(tileMaps[which])

def new_angle(origin, rotation):
    newIndex = (rotationMatrix.index(origin)+rotation) % len(rotationMatrix)
    return rotationMatrix[newIndex]

def new_tile_angles(tile, rotation):
    angles = [new_angle(x, rotation) for x in tiles[tile][1]]
    return angles

def which_slot(x, y):
    return tileSlots[int(2*x+6*y)]

def abs_coord(coord):
    coord = tileSlots.index(coord)
    return coord%3-1, coord//3-1

def load_tiles():
    filenames = []
    for _, _, files in os.walk(fileprefix):
        filenames = files
    # try:
    #     (_, _, filenames) = next(os.walk(fileprefix))
    # except StopIteration:
    #     pass

    for file in filenames:
        file = fileprefix + file
        tempImg = Image.open(file)
        tileIndex = len(tiles)
        goodSides = []
        pixels = tempImg.load()
        width, height = tempImg.size
        width -= 1
        height -= 1

        for x in [0, .5, 1]:
            for y in [0, .5, 1]:
                #check for whitespace
                if pixels[math.floor(x*width), math.floor(y*height)] == (255, 255, 255, 255):
                    slot = which_slot(x, y)
                    tileMaps[slot].append(tileIndex)
                    if slot not in [-1, 0, 1]:
                        #the center of the piece is irrelevant
                        goodSides.append(slot)

        tiles.append((file, goodSides))

    tileMaps[-1].append(18)
    #print(tiles,'\n',tileMaps)
    # for x in tileMaps:
    #     print(x, tileMaps[x])

def separateEvents(*events):
    newEvents = []
    nothingTotal = 100
    partial = 0
    for i, x in enumerate(events):
        if i % 2 == 0:
            if i == len(events):
                newEvents.append((x, nothingTotal))
                return newEvents
            else:
                partial = x
        else:
            nothingTotal -= x
            newEvents.append((partial, x))

    trailingPercents = (len(event_list)-len(newEvents))/len(event_list)
    additions = [x[0] for x in event_list if x not in [y[0] for y in newEvents]]

    for add in additions:
        newEvents.append((add, trailingPercents))

    return newEvents

def form_map(size):
    # extend the y direction by 1 in order to include the event legend
    map = [[None for _x in range(MAX_MAP_SIZE)] for _y in range(MAX_MAP_SIZE+1)]
    queue = []
    requeue = []
    tile = get_random_tile()
    map[5][6] = [tile, False]
    for side in tiles[tile][1]:
        queue.insert(0,[5, 5, side])
    while size > 1:
        if queue:
            bundle = queue.pop()
        else:
            bundle = requeue.pop()

        coordx, coordy, tileDir = bundle
        changeX, changeY = abs_coord(tileDir)
        nextX = coordx + changeX
        nextY = coordy + changeY
        if not -1 < nextX < MAX_MAP_SIZE or \
                not 0 < nextY < MAX_MAP_SIZE+1 or \
                (map[nextX][nextY] and map[nextX][nextY] is not None):
            #out of bounds or taken
            continue
        if random.random() > FLIP_CHANCE:
            randTile = get_random_tile(-tileDir)
            rotation = None
            sides = tiles[randTile][1]
        else:
            rotation = random.choice(range(7))+1
            randTile = get_random_tile(rotationMatrix[rotation])
            sides = new_tile_angles(randTile, rotation)
        map[nextX][nextY] = [randTile, rotation]
        size -= 1

        for side in sides:
            #if random.random() < (size-len(queue))/100:
            if random.random() < ENQUEUE_CHANCE:
                queue.insert(0, [nextX, nextY, side])
            else:
                requeue.insert(0, [nextX, nextY, side])

    return map

def populate_map(dungeon, events, size):
    evets, wets = list(zip(*events))
    randEvents = random.choices(evets, weights = wets, k = size)
    for row in dungeon:
        for tile in row:
            if tile is not None:
                evt = randEvents.pop()
                tile.append(event_colors[evt] * TILE_GLOW)# * random.randint(6,12))

    return dungeon

def create_map(dungeon, legend):
    max_size = (TILE_WIDTH + 1) * MAX_MAP_SIZE
    lowX, lowY, highX, highY = max_size, max_size, 0, 0
    dungeonMap = Image.new(mode = 'RGB', size = (max_size, max_size), color = BKGD_COLOR)
    BKGD_CROSS = Image.open(BKGD_CROSS_PATH).convert('RGBA')
    for x in range(MAX_MAP_SIZE):
        for y in range(MAX_MAP_SIZE):
            if dungeon[x][y] is not None:
                tile_image = Image.open(tiles[dungeon[x][y][0]][0])
                # if the image should be flipped
                if dungeon[x][y][1] is not None:
                    cross_tmp = BKGD_CROSS.copy()
                    tile_image = Image.alpha_composite(cross_tmp, tile_image.rotate(dungeon[x][y][1]*45))
                color = dungeon[x][y][2]
                tile_image = Image.blend(tile_image, Image.new('RGBA', tile_image.size, color), .2)
                dungeonMap.paste(tile_image, (x*TILE_WIDTH, y*TILE_WIDTH))
                if x > highX:
                    highX = x
                if x < lowX:
                    lowX = x
                if y > highY:
                    highY = y
                if y < lowY:
                    lowY = y

    highX += 1
    highY += 1

    lowY -= 1
    widt = highX - lowX
    if widt < len(legend) - 1:
        highX += len(legend) - widt - 1
    for offset, evt in enumerate(legend):
        evt = evt[0]
        if evt == 'nothing':
            continue
        clr = blend_hex(event_colors[evt]*TILE_GLOW, BKGD_COLOR)
        tmp = Image.new('RGBA', (TILE_WIDTH, TILE_WIDTH), clr)
        event_img = Image.open(event_icons[evt])
        img_size = [x//2 for x in event_img.size]
        tmp.paste(event_img, img_size)
        dungeonMap.paste(tmp, ((lowX + offset)*TILE_WIDTH, (lowY*TILE_WIDTH)))

    box = (lowX * TILE_WIDTH, lowY * TILE_WIDTH, highX * TILE_WIDTH, highY * TILE_WIDTH)
    newDungeon = dungeonMap.crop(box = box)

    # newDungeon.show()

    return newDungeon

class Maps(commands.Cog):

    def __init__(self, bot):
        load_tiles()
        self.bot = bot

    @commands.command(
        name = 'dungeon',
        aliases = ['dg'],
        help = """Create a randomly generated dungeon!
        Format: `!dungeon (size 5-100) [seed] [event1, % of event1, event2, % of event2]`.
        Size is required, but the seed and the specified events are optional.
        Event chance is out of 100, unspecified events are equally likely.
        Putting an event at the end will make it fill the remaining slots.
        e.g. `!dungeon 20 treasure 10, enemy 50, nothing` will create a dungeon with 20 tiles,
        with each tile having a 10% chance for treasure, 50% chance for an enemy encounter, and 40% chance for nothing.
        Events: """ + ', '.join([x[0] for x in event_list])
    )
    async def make_map(self, ctx, size : int, seed: Optional[int], *events):
        if seed is None:
            random.seed()
        else:
            random.seed(seed)

        size = sorted((5,size,100))[1]

        newEvents = separateEvents(events)
        dungeonMap = form_map(size)
        dungeonMap = populate_map(dungeonMap, newEvents, size)
        #TODO: implement the event pictures here?
        dungeon = create_map(dungeonMap, newEvents)

        dungeon.save(f'tmpDungeon.png')

        #content = f'*{seed}*'
        await ctx.send(file = File(f'tmpDungeon.png'))

        os.remove(f'tmpDungeon.png')


def setup(bot):
    bot.add_cog(Maps(bot))