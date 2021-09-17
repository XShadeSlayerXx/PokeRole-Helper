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

cannotRotate = [
    'big-cliff.png',
    'cliff.png',
    'crosswalk-pit.png',
    'empty-cliffs.png',
    'entrance.png',
    'exit.png',
    'hook_overlook.png',
    'ridged-intersection.png',
    'staircase.png',
    'up-pit-left.png'
]

MAX_MAP_SIZE = 11
TILE_WIDTH = 174
FLIP_CHANCE = .25
# FLIP_CHANCE = 0
ENQUEUE_CHANCE = .4
# ENQUEUE_CHANCE = 1
BKGD_COLOR = 0x828282
#FILL_COLOR = 0xb7b7b7
TILE_GLOW = 14

#TODO:
# allow mixing tiles? combine 2 and choose the lightest colors for new tiles?

class Tile:
    def __init__(self, path : str, directions = None):#, canRotate : bool = True):
        if directions is None:
            directions = set()
        self.directions = set(directions)
        self.canRotate = path not in cannotRotate
        self.image = fileprefix + path
        if not self.directions:
            self.directions = self.findDirections()

    def checkSubset(self, other : list):
        return set(other) <= self.directions

    def findDirections(self):
        file = self.image #fileprefix + name
        with Image.open(file) as tempImg:
            pixels = tempImg.load()
            width, height = tempImg.size
        goodSides = set()
        width -= 1
        height -= 1

        bad = False

        for x in [0, .5, 1]:
            for y in [0, .5, 1]:
                if pixels[math.floor(x * width), math.floor(y * height)] == (184,184,184,255):
                    self.canRotate = False
                    bad = True
                    continue
                #check for whitespace
                if pixels[math.floor(x * width), math.floor(y * height)] == (255, 255, 255, 255):
                    slot = getAngle(y, x)
                    if slot not in [-1]:
                        #the center of the piece is irrelevant for now
                        goodSides.add(slot)
                        tileMaps[slot].append(self)
                    # pixels[math.floor(x * width), math.floor(y * height)] = (255, 0, 0, 255)
        # im = Image.new("RGBA", (width+1, height+1))
        # tmpList = [pixels[x, y] for y in range(height+1) for x in range(width+1)]
        # print(goodSides)
        # im.putdata(tmpList)
        # im.show()
        # input()

        # self.canRotate = self.check2d(pixels)

        return goodSides

    # @staticmethod
    # def check2d(pixel_list, width = TILE_WIDTH, height = TILE_WIDTH):
    #     color = 184
    #     for y in range(height):
    #         for x in range(width):
    #             if pixel_list[x, y] == (color, color, color, 255):
    #                 return False
    #     return True

angleMatrix = {(0, 0): 315,
               (0, .5): 0,
               (0, 1): 45,
               (.5, 0): 270,
               (.5, .5): -1,
               (.5, 1): 90,
               (1, 0): 225,
               (1, .5): 180,
               (1, 1): 135}

def getAngle(x, y):
    return angleMatrix[(x, y)]




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
    # -1 : [], #center. TODO: do something with these?
    0 : [], #UP
    45 : [], #UP-RIGHT
    90 : [], #RIGHT
    135 : [], #DOWN-RIGHT
    # 180 : [], #DOWN #it's literally empty
    225 : [], #DOWN-LEFT
    270 : [], #LEFT
    315 : [] #UP-LEFT
}

tileSlots = [315, 0, 45, 270, -1, 90, 225, 180, 135]
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

def get_random_tile(which = None):
    if which is None:
        # which = random.choice([x for x in tileMaps.keys() if x is not -1])
        which = random.choice(list(tileMaps.keys()))
    return random.choice(tileMaps[which%360])

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
        tiles.append(Tile(path = file))
    #     file = fileprefix + file
    #     tempImg = Image.open(file)
    #     tileIndex = len(tiles)
    #     goodSides = []
    #     pixels = tempImg.load()
    #     width, height = tempImg.size
    #     width -= 1
    #     height -= 1
    #
    #     for x in [0, .5, 1]:
    #         for y in [0, .5, 1]:
    #             #check for whitespace
    #             if pixels[math.floor(x*width), math.floor(y*height)] == (255, 255, 255, 255):
    #                 slot = which_slot(x, y)
    #                 tileMaps[slot].append(tileIndex)
    #                 if slot not in [-1, 0, 1]:
    #                     #the center of the piece is irrelevant
    #                     goodSides.append(slot)
    #
    #     tiles.append((file, goodSides))
    #
    # tileMaps[-1].append(18)
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
    xStart = 5
    yStart = 6
    # extend the y direction by 1 in order to include the event legend
    map_tiles = [[None for _x in range(MAX_MAP_SIZE)] for _y in range(MAX_MAP_SIZE + 1)]
    queue = []
    requeue = []
    tile = get_random_tile()
    map_tiles[xStart][yStart] = [tile, False]
    for side in tile.directions:
        queue.insert(0,[xStart, yStart, side]) #5, 5??????
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
                (map_tiles[nextX][nextY] and map_tiles[nextX][nextY] is not None):
            #out of bounds or taken
            continue
        if random.random() > FLIP_CHANCE and (-tileDir)%360 != 180:
            randTile = get_random_tile(-tileDir)
            rotation = None
            sides = randTile.directions
        else:
            #can rotate by 90, 180, or 270 degrees. when applicable, can upgrade from 90 -> 45
            rotation = random.choice(list(range(90,360,90)))
            need_to_continue = True
            while need_to_continue:
                while (rotation-tileDir)%360 == 180:
                    rotation = random.choice(list(range(90,360,90)))
                # print('rot:',rotation,' ~ dir:', tileDir)
                # randTile = get_random_tile(rotationMatrix[rotation])
                randTile = get_random_tile((rotation-tileDir)%360)
                # rotation = rotation
                # sides = new_tile_angles(randTile, rotation)
                sides = [(x-rotation)%360 for x in randTile.directions]
                # print('oldSides: ',randTile.directions,' ~ newSides: ',sides)
                if randTile.canRotate:
                    need_to_continue = False

        map_tiles[nextX][nextY] = [randTile, rotation]
        size -= 1

        for side in sides:
            #if random.random() < (size-len(queue))/100:
            if random.random() < ENQUEUE_CHANCE:
                queue.insert(0, [nextX, nextY, side])
            else:
                requeue.insert(0, [nextX, nextY, side])

    return map_tiles

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
                tile_image = Image.open(dungeon[x][y][0].image)
                # tile_image = Image.open(tiles[dungeon[x][y][0]][0])
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
        # for x, y in tileMaps.items():
        #     print(x, y)

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