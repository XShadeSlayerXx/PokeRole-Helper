from PIL import Image, ImageDraw, ImageFont
from os.path import exists
from numpy import asarray, uint8

image_path = './images/HOME'

class Move:
    def __init__(
            self,
            name,
            acc1 = None,
            acc2 = None,
            pow1 = None,
            pow2 = None,
            acc_debuff = None
        ):
        self.name = name
        self.acc1 = acc1
        self.pow1 = pow1
        self.acc2 = acc2
        self.pow2 = pow2
        self.acc_debuff = acc_debuff if acc_debuff != 0 else None

    def __str__(self):
        return f'{self.name} - a: {self.acc1} + {self.acc2} - {self.acc_debuff}, d: {self.pow1} + {self.pow2}\n'

class Pokemon:
    #stats: list of stats as ints, in order
    # socials: list of the socials as ints, in order.
    # skills: list of the skills as ints, in order.

    # moves: list of the moves as type Move
    def __init__(self, number, name, my_type, ability, nature, base_hp,
                 stats, skills, socials, rank, moves, max_stats = None):
        if max_stats is None:
            max_stats = [12] * 5
        self.rank = rank
        self.socials = socials
        self.skills = skills
        self.stats = stats
        self.max_stats = max_stats
        self.base_hp = int(base_hp)
        self.nature = nature
        self.ability = ability
        self.my_type = my_type
        self.number = number.replace('#', '')
        self.name = name
        self.moves = moves
        self.image = get_image(self.number, self.name)

    def add_move(self, move : Move):
        self.moves.append(move)

    def add_move_stats(self, name, acc1, acc2, pow1, pow2, acc_debuff):
        self.moves.append(Move(name, acc1, acc2, pow1, pow2, acc_debuff))

    def create_stat_sheet(self) -> Image:
        base = Image.open('Pokemon_Stat_Sheet.png').convert('RGBA')
        out = ImageDraw.Draw(base)

        add_word(out, 'number', f'#{self.number}')
        add_word(out, 'name', self.name)
        add_word(out, 'my_type', self.my_type)
        add_word(out, 'ability', self.ability)
        add_word(out, 'nature', self.nature)
        add_word(out, 'rank', self.rank)
        draw_stats(out, self.stats)
        draw_max_stats(out, self.max_stats)
        draw_socials(out, self.socials)
        draw_skills(out, self.skills)
        write_moves(out, self.moves)

        if self.image: draw_image(base, self.image)

        hp = f'{self.base_hp}'
        initiative = f'd6 + {self.stats[1] + self.skills[4]}'
        will = f'{self.stats[4] + 2}'
        evasion = f'{self.stats[1] + self.skills[3]}'
        clash = f'{self.stats[1] + self.skills[2]}'
        defense = f'{self.stats[2]} / {self.stats[4]}'
        draw_quick_reference(out, hp, will, initiative, evasion, clash, defense)

        return base


offsets = {
    'number': (2715, 587),
    "name": (2715, 705),
    'my_type': (1500, 2300),
    'ability': (2715, 835),
    'moves': (231,196),
    'hp': (2825, 1370),
    'will': (2825, 1508),
    'stats': (318,1415),
    'skills': (1046, 1380),
    'socials': (1485, 1415),
    'rank': (2819, 2285),
    'initiative': (2808, 1824),
    'evasion': (2790, 2047),
    'clash': (2758, 2113),
    'defense': (2831, 2188),
    'nature': (2062, 1372),
    'image': (2086, 490)
}
font_size = {
    "number": 60,
    "name": 70,
    'my_type': 50,
    'ability': 60,
    'moves': 40,
    'hp': 60,
    'rank': 60,
    'nature': 80,
    'reference': 40
}

type_offset = 60
move_offset = 217
move_power_offset = 46
move_dice_offset = 119
move_horizontal_offset = 530
move_boxh_offset = 460
move_boxv_offset = 168
move_boxtotal_offset = 20
move_radius = 50

#always has been
insight_offset = (11,2)

stat_offset = 180
dot_offset = 47

skill_offset = 73
skill_dot_offset = 31
skill_group_offset = 13

def get_image(number, name):
    if name.startswith('Mega'):
        add_on = 'M'
    elif name.startswith('Galar'):
        add_on = 'G'
    elif name.startswith('Alola'):
        add_on = 'A'
    else:
        add_on = ''
    path = image_path + str(number) + add_on + '.png'
    if not exists(path = path):
        path = None
    return path

def get_font(size):
    return ImageFont.truetype('Candara.ttf', size)

def add_word(draw_object, which, what):
    fnt = get_font(font_size[which])
    draw_object.multiline_text(offsets[which], what, font = fnt, fill = (0, 0, 0))

def draw_stats(draw_object, stats):
    ofs = list(offsets['stats'])[:]
    for i, dots in enumerate(stats):
        for num in range(dots):
            circle = ((ofs[0], ofs[1]), (ofs[0]+dot_offset,ofs[1]+dot_offset))
            draw_object.ellipse(circle, fill = (62, 59, 54))
            ofs[0] += dot_offset
        ofs[0] = offsets['stats'][0]
        ofs[1] += stat_offset
        if i == 3:
            ofs[0] += insight_offset[0]
            ofs[1] += insight_offset[1]

def draw_max_stats(draw_object, stats):
    clr = (0,167,189)
    ofs = list(offsets['stats'])[:]
    for i, dots in enumerate(stats):
        rect = ((ofs[0]+dot_offset*dots-2, ofs[1]), (ofs[0]+dot_offset*12,ofs[1]+dot_offset))
        draw_object.rectangle(rect, fill = clr)
        ofs[1] += stat_offset
        if i == 3:
            ofs[0] += insight_offset[0]
            ofs[1] += insight_offset[1]

def draw_socials(draw_object, socials):
    ofs = list(offsets['socials'])[:]
    for dots in socials:
        for num in range(dots):
            circle = ((ofs[0], ofs[1]), (ofs[0]+dot_offset,ofs[1]+dot_offset))
            draw_object.ellipse(circle, fill = (62, 59, 54))
            ofs[0] += dot_offset
        ofs[0] = offsets['socials'][0]
        ofs[1] += stat_offset

def draw_skills(draw_object, skills):
    ofs = list(offsets['skills'])[:]
    for i, dots in enumerate(skills):
        for num in range(dots):
            circle = ((ofs[0], ofs[1]), (ofs[0]+skill_dot_offset,ofs[1]+skill_dot_offset))
            draw_object.ellipse(circle, fill = (62, 59, 54))
            ofs[0] += skill_dot_offset
        ofs[0] = offsets['skills'][0]
        ofs[1] += skill_offset
        if i % 4 == 3:
            ofs[1] += skill_group_offset

def write_moves(draw_object, moves):
    fnt = get_font(font_size['moves'])
    ofs = list(offsets['moves'])[:]
    for i, move in enumerate(moves):
        #prepare the area with a white square
        draw_object.rounded_rectangle(((ofs[0] - move_boxtotal_offset, ofs[1] - move_boxtotal_offset),
                                       (ofs[0] + move_boxh_offset, ofs[1] + move_boxv_offset)),
                                      fill = (255,255,255),
                                      radius = move_radius)
        # print(str(move))
        #move name
        write = move.name.title()
        draw_object.multiline_text(ofs, write, font = fnt, fill = (0, 0, 0))
        # #move power
        # write = f'{move.pow2}'
        # next_offset = (ofs[0], ofs[1] + move_power_offset)
        # draw_object.multiline_text(next_offset, write, font = fnt, fill = (0, 0, 0))
        #move dice pool
        try:
            acc = (int(move.acc1) if move.acc1 else 0) + (int(move.acc2) if move.acc2 else 0)
        except:
            acc = '???'
        try:
            pow = (int(move.pow1) if move.pow1 else 0) + (int(move.pow2) if move.pow2 else 0)
        except:
            pow = '???'
        debuff = f' ( - {move.acc_debuff})' if move.acc_debuff else ''
        write = f'acc: {acc}{debuff}\npow: {pow}'
        # next_offset = (ofs[0], ofs[1] + move_dice_offset)
        next_offset = (ofs[0], ofs[1] + move_power_offset)
        draw_object.multiline_text(next_offset, write, font = fnt, fill = (0, 0, 0))
        ofs[1] += move_offset
        if i % 5 == 4:
            ofs[0] += move_horizontal_offset
            ofs[1] = offsets['moves'][1]

def draw_image(draw_object, image):
    with Image.open(image) as img:
        tmp = asarray(img).copy()

        tmp = Image.fromarray(tmp)

        draw_object.paste(tmp, offsets['image'], mask = tmp)

def draw_quick_reference(draw_object, hp, will, initiative, evasion, clash, defense):
    # hp and will have same font
    fnt = get_font(font_size['hp'])
    draw_object.multiline_text(offsets['hp'], hp, font = fnt, fill = (0, 0, 0))
    draw_object.multiline_text(offsets['will'], will, font = fnt, fill = (0, 0, 0))
    # the rest have the same font
    fnt = get_font(font_size['reference'])
    draw_object.multiline_text(offsets['initiative'], initiative, font = fnt, fill = (0, 0, 0))
    draw_object.multiline_text(offsets['evasion'], evasion, font = fnt, fill = (0, 0, 0))
    draw_object.multiline_text(offsets['clash'], clash, font = fnt, fill = (0, 0, 0))
    draw_object.multiline_text(offsets['defense'], defense, font = fnt, fill = (0, 0, 0))



if __name__ == "__main__":
    from random import randrange

    move_examples = [
        ('foresight', 0, 'SUPPORT'),
        ('quick attack', 2, 'STRENGTH'),
        ('endure', 0),
        ('counter', 0),
        ('feint', 0),
        ('thunder shock', 0),
        ('thunderbolt', 0),
        ('fake out', 0),
        ('volt tackle', 0),
        ('wish', 0),
        ('stone edge', 0),
        ('thunder fang', 0),
        ('earthquake', 0),
        ('take down', 0),
    ]
    number = str(randrange(1, 900))
    name = 'Riolu'
    rank = 'Beginner'
    my_type = 'Dragon / Fighting'

    ability = 'Inner Focus'

    stats = [
        randrange(1, 5) for x in range(5)
    ]
    max_stats = [
        randrange(5, 8) for x in range(5)
    ]
    # max_stats = None
    socials = [
        randrange(1, 5) for x in range(5)
    ]
    skills = [
        randrange(1, 5) for x in range(12)
    ]
    hp = 3

    nature = 'Brash'

    move_list = [
        Move(x[0], stats[1], skills[0], stats[0], randrange(0, 3), randrange(0, 3)) for x in move_examples
    ]
    pkmn = Pokemon(number, name, my_type, ability, nature, hp, stats, skills, socials, rank, move_list, max_stats)
    pkmn.create_stat_sheet().show()