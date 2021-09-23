from discord.ext import commands
from discord import File, Embed
from typing import Optional
from PIL import Image, ImageDraw
import numpy as np
from sys import maxsize as MAXSIZE
from dislash import slash_command, ActionRow, Button, ButtonStyle, ResponseType, Option, OptionType
from io import BytesIO

import random
import os
import math

TEST_GUILDS = [669326419641237509]

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

background_colors = [
    ('cyan','aquamarine'),
    ('crimson','salmon'),
    ('hotpink','pink'),
    ('tomato','darkorange'),
    ('gold','khaki'),
    ('plum','lavender'),
    ('Fuchsia','darkviolet'),
    ('indigo','purple'),
    ('slateblue','thistle'),
    ('green','springgreen'),
    ('darkolivegreen','olive'),
    ('teal','lightseagreen'),
    ('aqua','steelblue'),
    ('deepskyblue','navy'),
    ('royalblue','darkred'),
    ('firebrick','darkslateblue'),
    ('lime','turquoise')
]

MAX_MAP_SIZE = 11
TILE_WIDTH = 174
FLIP_CHANCE = .05
# FLIP_CHANCE = 0
ENQUEUE_CHANCE = .7
# ENQUEUE_CHANCE = 1
BKGD_COLOR = 0x828282
#FILL_COLOR = 0xb7b7b7
TILE_GLOW = 14
TILE_OPACITY = 255
# TILE_OPACITY = 180

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

        for x in [0, .5, 1]:
            for y in [0, .5, 1]:
                #check for whitespace
                if pixels[math.floor(x * width), math.floor(y * height)] == (255, 255, 255, 255):
                    slot = getAngle(y, x)
                    if slot not in [-1]:
                        #the center of the piece is irrelevant for now
                        goodSides.add(slot)
                        tileMaps[slot].append(self)

        return goodSides

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
    'guild': f'{eventprefix}accessory_small.png',
    'nothing' : f'{eventprefix}badge_small.png'
}

#so many events
event_order = [
    'random',
    'treasure',
    'enemy',
    'trap',
    'hazard',
    'guild',
    'nothing'
]

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

def form_map(size):
    xStart = 5
    yStart = 6
    # extend the y direction by 1 in order to include the event legend
    map_tiles = [[None for _x in range(MAX_MAP_SIZE)] for _y in range(MAX_MAP_SIZE + 1)]
    queue = []
    requeue = []
    tile = get_random_tile()
    map_tiles[xStart][yStart] = [tile, False]
    tmpDirs = list(tile.directions)
    random.shuffle(tmpDirs)
    for side in tmpDirs:#tile.directions:
        queue.insert(0,[xStart, yStart, side]) #5, 5??????
    while size > 1:
        if queue:
            bundle = queue.pop()
        elif requeue:
            bundle = requeue.pop()
        else:
            size = 0
            continue

        coordx, coordy, tileDir = bundle
        changeX, changeY = abs_coord(tileDir)
        nextX = coordx + changeX
        nextY = coordy + changeY
        if not -1 < nextX < MAX_MAP_SIZE-1 or \
                not 0 < nextY < MAX_MAP_SIZE or \
                (map_tiles[nextX][nextY] and map_tiles[nextX][nextY] is not None):
            #out of bounds or taken
            continue
        if random.random() > FLIP_CHANCE and tileDir != 0:
            randTile = get_random_tile(tileDir+180)
            rotation = None
            sides = randTile.directions
        else:
            #can rotate by 90, 180, or 270 degrees. when applicable, can upgrade from 90 -> 45
            rotation = random.choice(list(range(90,360,90)))
            need_to_continue = True
            sanity = 200
            while need_to_continue and sanity > 0:
                sanity -= 1
                while (rotation-tileDir)%360 == 180:
                    rotation = random.choice(list(range(90,360,90)))
                randTile = get_random_tile((rotation-tileDir)%360)
                sides = [(x-rotation)%360 for x in randTile.directions]
                if randTile.canRotate:
                    need_to_continue = False

        map_tiles[nextX][nextY] = [randTile, rotation]
        size -= 1

        tmpDirs = list(sides)
        random.shuffle(tmpDirs)
        for side in tmpDirs:#sides:
            if random.random() < ENQUEUE_CHANCE:
                where = random.randrange(len(queue)+1)
                queue.insert(where, [nextX, nextY, side])
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

def generate_gradient(colour1: str, colour2: str, width: int, height: int) -> Image:
    """Generate a vertical gradient."""
    base = Image.new('RGB', (width, height), colour1)
    top = Image.new('RGB', (width, height), colour2)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def create_alpha_mask(side_width, border, transparency) -> Image:
    tmp = Image.new('RGBA', (TILE_WIDTH, TILE_WIDTH), (0,0,0,transparency))
    draw = ImageDraw.Draw(tmp, "RGBA")
    draw.rectangle(((border,border), (side_width-border, side_width-border)),(0,0,0,255))
    return tmp

def create_map(dungeon, legend):
    offset_amt = 20
    # paste the iamges slightly closer together, and take the higher white or dark sections from overlap?
    #   or simply blend them together on a transparent background, and paste this onto a gradient image before crop
    max_size = (TILE_WIDTH + 1) * MAX_MAP_SIZE
    TILE_OFFSET = TILE_WIDTH - TILE_WIDTH//offset_amt    # 5% smaller
    lowX, lowY, highX, highY = max_size, max_size, 0, 0
    dungeonMap = Image.new(mode = 'RGBA', size = (max_size, max_size), color = (130, 130, 130, 0)) #BKGD_COLOR)
    bkg_clr = random.choice(background_colors)
    # dungeonMap = generate_gradient(bkg_clr[0], bkg_clr[1], max_size, max_size)
    gradient_map = generate_gradient(bkg_clr[0], bkg_clr[1], max_size, max_size)
    # BKGD_CROSS = Image.open(BKGD_CROSS_PATH).convert('RGBA')
    ALPHA_TILE_MASK = create_alpha_mask(TILE_WIDTH, offset_amt//2, 127)
    for x in range(MAX_MAP_SIZE):
        for y in range(MAX_MAP_SIZE):
            if dungeon[x][y] is not None:
                tile_image = Image.open(dungeon[x][y][0].image)
                # tile_image = Image.open(tiles[dungeon[x][y][0]][0])
                # if the image should be flipped
                # if dungeon[x][y][1] is not None:
                #     cross_tmp = BKGD_CROSS.copy()
                #     tile_image = Image.alpha_composite(cross_tmp, tile_image.rotate(dungeon[x][y][1]*45))
                if legend:
                    color = dungeon[x][y][2]
                    tile_image = Image.blend(tile_image, Image.new('RGBA', tile_image.size, color), .2)
                # dungeonMap.paste(tile_image, (x*TILE_WIDTH, y*TILE_WIDTH))
                dungeonMap.paste(tile_image, (x*TILE_OFFSET, y*TILE_OFFSET), ALPHA_TILE_MASK)
                if x > highX:
                    highX = x
                if x < lowX:
                    lowX = x
                if y > highY:
                    highY = y
                if y < lowY:
                    lowY = y

    #make the image opaque
    np_dungeon = np.array(dungeonMap)
    np_dungeon[:, :, 3] = (255 * (np_dungeon[:, :, 3] > 100)).astype(np.uint8)
    if TILE_OPACITY < 255:
        np_dungeon[:, :, 3][np_dungeon[:, :, 0] == 131] = TILE_OPACITY #this currently changes the tile background alpha value
    red, green, blue, _ = np_dungeon.T

    # keep 184, 131, 9, 71
    # change 193, 162, 178
    gray_areas = np.logical_or(red == 193, red == 162, red == 177)

    np_dungeon[..., :-1][gray_areas.T] = (255, 255, 255)
    dungeonMap = Image.fromarray(np_dungeon)

    gradient_map.paste(dungeonMap, mask = dungeonMap)
    dungeonMap = gradient_map

    highX += 1
    highY += 1

    if legend:
        lowY -= 1 #put this right over the rest of the map
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

    # box = (lowX * TILE_WIDTH, lowY * TILE_WIDTH, highX * TILE_WIDTH, highY * TILE_WIDTH)
    box = (lowX * TILE_OFFSET, lowY * TILE_OFFSET, highX * TILE_OFFSET, highY * TILE_OFFSET)
    newDungeon = dungeonMap.crop(box = box)

    # newDungeon.show()

    return newDungeon, TILE_OFFSET

def Make_WASD():
    rows = [
        ActionRow(
            Button(
                style = ButtonStyle.green,
                label = "Event",
                custom_id = "event"
            ),
            Button(
                style = ButtonStyle.blurple,
                label = "↑",
                custom_id = "up"
            ),
            Button(
                style = ButtonStyle.green,
                label = "Update",
                custom_id = "dungeon"
            )
        ),
            ActionRow(
            Button(
                style = ButtonStyle.blurple,
                label = "←",
                custom_id = "left"
            ),
            Button(
                style = ButtonStyle.blurple,
                label = "↓",
                custom_id = "down"
            ),
            Button(
                style = ButtonStyle.blurple,
                label = "→",
                custom_id = "right"
            )
        ),
            ActionRow(
                Button(
                    style = ButtonStyle.red,
                    label = 'delete',
                    custom_id = 'delete'
                )
            )
    ]
    return rows

async def Pillow_reply(inter, content, image, filename, include_descriptions : bool = True):
    dungeon = image
    if include_descriptions:
        components = Make_WASD()
    else:
        components = []
    with BytesIO() as image_binary:
        dungeon.save(image_binary, 'PNG')
        image_binary.seek(0)
        # im = Image.open(image_binary)
        # im.show()
        # filename = f'Dungeon-Size-{size}-Seed-{seed}.png'
        # filename = 'dungeon.png'
        file = File(fp = image_binary, filename = filename)
        # embed = Embed().set_image(url = f'attachment://{filename}')
        msg = await inter.reply(content = content,
                                file = file,
                                # embed = embed,
                                # file = File(f'Dungeon-Size-{size}-Seed-{seed}.png'),
                                components = components,
                                fetch_response_message = False)

    return msg

def Modify_Dungeon_Message(msg : str, what : str, howMuch : int = None,
                           edge : int = None):
    #msg example
    # f'(1,1) - Event: nothing\n' \
    # f'Size: {size} - Seed: {seed}'
    if what == 'event':
        all = msg.split(' - ', maxsplit = 1)
        after = all[1].split('\n')
        # combine all[0] + 'Event: ' + new + after[1]
        #  dont forget to replace the split stuff
        # separate out Event: event
        result = after[0][7:]
        # get the next one in line
        result = event_order[(event_order.index(result)+1)%len(event_order)]
        #splice the stuff together
        result = all[0] + ' - Event: ' + result + '\n' + after[1]
    elif what == 'dungeon':
        # do this in the actual method? dont have access to the creation stuff here
        pass
    elif what == 'up':
        all = msg.split(' - ', maxsplit = 1)
        coords = all[0].split(',')
        # y coord excluding paranthesis
        y_axis = int(coords[1][:-1])
        if y_axis != 1:
            y_axis -= 1
            result = coords[0] + ',' + str(y_axis) + ') - ' + all[1]
        else:
            result = msg
    elif what == 'down':
        all = msg.split(' - ', maxsplit = 1)
        coords = all[0].split(',')
        # y coord excluding paranthesis
        y_axis = int(coords[1][:-1])
        if y_axis < edge:
            y_axis += 1
            result = coords[0] + ',' + str(y_axis) + ') - ' + all[1]
        else:
            result = msg
    elif what == 'left':
        all = msg.split(' - ', maxsplit = 1)
        coords = all[0].split(',')
        # x coord excluding paranthesis
        x_axis = int(coords[0][1:])
        if x_axis != 1:
            x_axis -= 1
            result = '('+ str(x_axis) + ',' + coords[1] + ' - ' + all[1]
        else:
            result = msg
    elif what == 'right':
        all = msg.split(' - ', maxsplit = 1)
        coords = all[0].split(',')
        # x coord excluding paranthesis
        x_axis = int(coords[0][1:])
        if x_axis < edge:
            x_axis += 1
            result = '('+ str(x_axis) + ',' + coords[1] + ' - ' + all[1]
        else:
            result = msg
    else:
        print(f'Error: Unknown Button {what} passed in.')
    return result

def Separate_Params(msg : str):
    all = msg.split(' - ')
    eventsize = all[1].split('\n')
    coords = all[0][1:-1].split(',')
    x, y = int(coords[0]), int(coords[1])
    event = eventsize[0][7:]
    # size = int(eventsize[1][6:])
    # seed = int(all[2][6:])

    return x, y, event#, size, seed

def Add_Event(image, event, x, y, offset):
    dungeon = image.copy()
    real_x = (x - 1) * offset + offset//4
    real_y = (y - 1) * offset + offset//4
    event_image = Image.open(event_icons[event])

    event_image = event_image.convert("RGBA")
    dungeon = dungeon.convert("RGBA")

    dungeon.alpha_composite(event_image, (real_x, real_y))

    return dungeon

class Maps(commands.Cog):

    def __init__(self, bot):
        load_tiles()
        self.bot = bot
        self.msg = None
        self.on_click = None
        self.timeout = 1 * 60 * 10 # 10 minutes
        # self.timeout = 1 * 10
        self.prev_msg = None

    @slash_command(
        desciption="Create a dungeon with control buttons from {size} and {seed}.",
        # guild_ids = TEST_GUILDS,
        options = [
            Option('size', 'Number of dungeon tiles between 5 and 100', OptionType.INTEGER),
            Option('seed', 'RNG seed (integer)', OptionType.STRING)
        ]
    )
    async def dungeon(self, inter, size : int = None, seed : int = None):
        if seed is None:
            seed = random.randrange(MAXSIZE)
        random.seed(seed)

        if size is None:
            size = random.randrange(10,40)
        else:
            size = sorted((5,size,100))[1]

        dungeonMap = form_map(size)

        newEvents = None
        dungeon, TILE_OFFSET = create_map(dungeonMap, newEvents)
        width, height = dungeon.size
        width //= TILE_OFFSET
        height //= TILE_OFFSET

        # dungeon.save(f'Dungeon-Size-{size}-Seed-{seed}.png')

        content = f'(1,1) - Event: nothing\n' \
                  f'Size: {size} - Seed: {seed}'
        filename = f'Dungeon-Size-{size}-Seed-{seed}.png'
        #a necessary evil
        timeout_msg = 'Creating your dungeon...\n' \
                      f'The dungeon controls will timeout after {self.timeout//60} minutes of inactivity.'
        await inter.reply(content = timeout_msg, ephemeral = True)

        self.msg = await Pillow_reply(inter = inter, content = content,
                           image = dungeon, filename = filename)

        # os.remove(f'Dungeon-Size-{size}-Seed-{seed}.png')

        self.on_click = self.msg.create_click_listener(timeout = self.timeout)

        # inter = await msg.wait_for_button()
        @self.on_click.matching_id('up')
        async def on_left_button(inter):
            # print(inter.message.content)
            # print(inter.component)
            content = Modify_Dungeon_Message(inter.message.content, inter.component.custom_id)
            await inter.reply(content = content, type = ResponseType.UpdateMessage)

        @self.on_click.matching_id('down')
        async def on_left_button(inter):
            content = Modify_Dungeon_Message(inter.message.content, inter.component.custom_id, edge = height)
            await inter.reply(content = content, type = ResponseType.UpdateMessage)

        @self.on_click.matching_id('left')
        async def on_left_button(inter):
            content = Modify_Dungeon_Message(inter.message.content, inter.component.custom_id)
            await inter.reply(content = content, type = ResponseType.UpdateMessage)

        @self.on_click.matching_id('right')
        async def on_left_button(inter):
            content = Modify_Dungeon_Message(inter.message.content, inter.component.custom_id, edge = width)
            await inter.reply(content = content, type = ResponseType.UpdateMessage)

        @self.on_click.matching_id('event')
        async def on_left_button(inter):
            #event_order
            content = Modify_Dungeon_Message(inter.message.content, inter.component.custom_id)
            await inter.reply(content = content, type = ResponseType.UpdateMessage)

        @self.on_click.matching_id('dungeon')
        async def on_dungeon_button(inter):
            x, y, event = Separate_Params(inter.message.content)
            if event in ['random']:
                event = random.choice(list(event_icons.keys()))
            content = f'({x},{y}) - Event: {event}'
            filename = f'tmp_Size-{size}-Seed-{seed}.png'
            tmp_dungeon = Add_Event(dungeon, event, x, y, TILE_OFFSET)
            # tmp_dungeon.show()
            timeout_msg = 'Updating...'
            await inter.reply(content = timeout_msg, ephemeral = False, delete_after = 1)
            if self.prev_msg:
                await self.prev_msg.delete()
                self.prev_msg = None
            self.prev_msg = await Pillow_reply(inter = inter, content = content,
                                     image = tmp_dungeon, filename = filename,
                                          include_descriptions = False)

        @self.on_click.matching_id('delete')
        async def on_delete_button(inter):
            await self.msg.delete()
            if self.prev_msg:
                await self.prev_msg.delete()
                self.prev_msg = None

        @self.on_click.timeout
        async def on_timeout():
            if self.prev_msg:
                await self.prev_msg.delete()
                self.prev_msg = None
            await self.msg.edit(content = '(Timed out)\n'+self.msg.content.split('\n')[1],
                           components = [])

    @commands.command(
        name = 'dungeon',
        aliases = ['dg'],
        help = """Updated: Create a randomly generated dungeon!
        Format: `!dungeon (size 5-100) [events? T/F] [seed]`.
        Size is required, but including events and the seed are optional.
        e.g. `!dungeon 20 True 12345` will create a dungeon with 20 tiles, events, and the seed will be 12345.
        Events: """ + ', '.join([x[0] for x in event_list])
    )
    async def make_map(self, ctx, size : int = None,
                       events : Optional[bool] = False, seed: Optional[int] = None):#, *events):
        if seed is None:
            seed = random.randrange(MAXSIZE)
        random.seed(seed)

        if size is None:
            size = random.randrange(10,40)
        else:
            size = sorted((5,size,100))[1]

        # newEvents = separateEvents(events)
        dungeonMap = form_map(size)
        #TODO: implement the event pictures here?
        if events:
            newEvents = event_list #[x[0] for x in event_list]
            dungeonMap = populate_map(dungeonMap, newEvents, size)
        else:
            newEvents = None
        dungeon, _ = create_map(dungeonMap, newEvents)

        dungeon.save(f'Dungeon-Size-{size}-Seed-{seed}.png')

        #content = f'*{seed}*'
        await ctx.send(file = File(f'Dungeon-Size-{size}-Seed-{seed}.png'))

        os.remove(f'Dungeon-Size-{size}-Seed-{seed}.png')


def setup(bot):
    bot.add_cog(Maps(bot))