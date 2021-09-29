from PIL import Image, ImageDraw, ImageFont
from random import randrange

class Move:
    def __init__(self, name, acc1, acc2, pow1, pow2, acc_debuff):
        self.name = name
        self.acc1 = acc1
        self.pow1 = pow1
        self.acc2 = acc2
        self.pow2 = pow2
        self.acc_debuff = acc_debuff if acc_debuff != 0 else None

    def __str__(self):
        return f'{self.name} - a: {self.acc1} + {self.acc2} - {self.acc_debuff}, d: {self.pow1} + {self.pow2}\n'

class Pokemon:
    def __init__(self, number, name, my_type, ability, nature, base_hp,
                 stats, skills, socials, rank, moves : list[Move]):
        self.rank = rank
        self.socials = socials
        self.skills = skills
        self.stats = stats
        self.base_hp = int(base_hp)
        self.nature = nature
        self.ability = ability
        self.my_type = my_type
        self.number = number
        self.name = name
        self.moves = moves

    def add_move(self, move : Move):
        self.moves.append(move)

    def add_move(self, name, acc1, acc2, pow1, pow2, acc_debuff):
        self.moves.append(Move(name, acc1, acc2, pow1, pow2, acc_debuff))

    def create_stat_sheet(self):
        with Image.open('Pokemon_Stat_Sheet.png').convert('RGBA') as base:
            out = ImageDraw.Draw(base)

            add_word(out, 'number', self.number)
            add_word(out, 'name', self.name)
            add_word(out, 'my_type', self.my_type)
            add_word(out, 'ability', self.ability)
            add_word(out, 'nature', self.nature)
            add_word(out, 'rank', self.rank)
            draw_stats(out, self.stats)
            draw_socials(out, self.socials)
            draw_skills(out, self.skills)
            write_moves(out, self.moves)
            hp = f'{self.base_hp + self.stats[3]}'
            initiative = f'd6 + {self.stats[1] + self.skills[4]}'
            will = f'{self.stats[4] + 2}'
            evasion = f'{self.stats[1] + self.skills[3]}'
            clash = f'{self.stats[1] + self.skills[2]}'
            defense = f'{self.stats[2]} / {self.stats[4]}'
            draw_quick_reference(out, hp, will, initiative, evasion, clash, defense)

            base.show()


offsets = {
    'number': (2715, 587),
    "name": (2715, 705),
    'my_type': (1621, 2273),
    'ability': (2715, 835),
    'moves': (232,196),
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
    'nature': (2062, 1372)
}
font_size = {
    "number": 60,
    "name": 70,
    'my_type': 70,
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
move_horizontal_offset = 242
# move_vertical_offset = 24

#always has been
insight_offset = (11,2)

stat_offset = 180
dot_offset = 47

skill_offset = 73
skill_dot_offset = 31
skill_group_offset = 13


move_examples = [
    ('foresight', 0, 'SUPPORT'),
    ('quick attack', 2, 'STRENGTH'),
    ('endure', 0),
    ('counter', 0),
    ('feint', 0),
    # 'force palm', 'copycat', 'screech', 'reversal'
]
number = '477'
name = 'Riolu'
rank = 'Beginner'
my_type = 'fight'

ability = 'Inner Focus'

stats = [
    randrange(1,5) for x in range(5)
]
socials = [
    randrange(1,5) for x in range(5)
]
skills = [
    randrange(1,5) for x in range(12)
]
hp = 3
# hp = f'{3 + stats[3]}'
# initiative = f'd6 + {stats[1] + skills[4]}'
# will = f'{stats[4] + 2}'
# evasion = f'{stats[1] + skills[3]}'
# clash = f'{stats[1] + skills[2]}'
# defense = f'{stats[2]} / {stats[4]}'

nature = 'Brash'

def get_font(size):
    return ImageFont.truetype('Candara.ttf', size)

#
# def add_moves(draw_object, move_list):
#     fnt = get_font(font_size['move'])
#     bo = list(offsets['move'][:])
#     for i, x in enumerate(move_list):
#         draw_object.multiline_text((bo[0] + move_offset, bo[1]), x, font = fnt, fill = (0, 0, 0))
#         if i%2 == 0:
#             bo[0] += move_horizontal_offset
#         else:
#             bo[0] = offsets['move'][0]
#             bo[1] += move_vertical_offset
#
#
# def add_name(draw_object, name):
#     fnt = get_font(font_size['name'])
#     draw_object.multiline_text(offsets['name'], name, font = fnt, fill = (240, 240, 240))
#
#
# def add_type(draw_object, tp):
#     # change to accept lists
#     fnt = get_font(font_size['my_type'])
#     draw_object.multiline_text(offsets['my_type'], tp[0], font = fnt, fill = (245, 236, 210))
#
#
# def add_ability(draw_object, ab):
#     fnt = get_font(font_size['ability'])
#     draw_object.multiline_text(offsets['ability'], ab, font = fnt, fill = (62, 59, 54))
#
#
# def add_hp(draw_object, hp):
#     fnt = get_font(font_size['hp'])
#     draw_object.multiline_text(offsets['hp'], hp, font = fnt, fill = (0, 0, 0))

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

def write_moves(draw_object, moves : list[Move]):
    fnt = get_font(font_size['moves'])
    ofs = list(offsets['moves'])[:]
    for move in moves:
        # print(str(move))
        #move name
        write = move.name
        draw_object.multiline_text(ofs, write, font = fnt, fill = (0, 0, 0))
        # #move power
        # write = f'{move.pow2}'
        # next_offset = (ofs[0], ofs[1] + move_power_offset)
        # draw_object.multiline_text(next_offset, write, font = fnt, fill = (0, 0, 0))
        #move dice pool
        acc = (int(move.acc1) if move.acc1 else 0) + (int(move.acc2) if move.acc2 else 0)
        pow = (int(move.pow1) if move.pow1 else 0) + (int(move.pow2) if move.pow2 else 0)
        debuff = f' ( - {move.acc_debuff})' if move.acc_debuff else ''
        write = f'acc: {acc}{debuff}\npow: {pow}'
        # next_offset = (ofs[0], ofs[1] + move_dice_offset)
        next_offset = (ofs[0], ofs[1] + move_power_offset)
        draw_object.multiline_text(next_offset, write, font = fnt, fill = (0, 0, 0))
        ofs[1] += move_offset

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

# # def draw_dex_stats(draw_object, stats):
#     moves = [
#         'foresight', 'quick attack', 'endure', 'counter', 'feint', 'force palm', 'copycat', 'screech', 'reversal'
#     ]
#
#     stats = [
#         (2, 3), (2, 2), (1, 2), (1, 2), (1, 2)
#     ]
#
#     my_type = ['fight']
#
#     ability = 'Steadfast & Inner Focus'
#     # stats = [(3,2), (2, 3),...] # str, dex, etc, filled dots then empty
#     ofs = list(offsets['stats'])[:]
#     for i, x in enumerate(stats): #for stat in the list
#         tmp_stat = stats[i]
#         for _filled in range(tmp_stat[0]):
#             circle = (tuple(ofs), (ofs[0] + dot_offset, ofs[1] + dot_offset))
#             draw_object.ellipse(circle, fill = (62, 59, 54))
#             ofs[0] += dot_offset
#         for _empty in range(tmp_stat[1]):
#             circle = (tuple(ofs), (ofs[0] + dot_offset, ofs[1] + dot_offset))
#             draw_object.ellipse(circle, fill = (245, 236, 210))
#             ofs[0] += dot_offset
#         ofs[0] = offsets['stats'][0]
#         ofs[1] += stat_offset

# def create_dex_sheet():
#     offsets = {
#         "name": (45, 15),
#         'my_type': (315, 20),
#         'ability': (260, 280),
#         'move': (490,57),
#         'hp': (325, 215),
#         'stats': (362,67)
#     }
#     font_size = {
#         "name": 35,
#         'my_type': 30,
#         'ability': 20,
#         'move': 15,
#         'hp': 40
#     }
#
#     type_offset = 60
#     move_offset = 117
#     move_horizontal_offset = 242
#     move_vertical_offset = 24
#
#     stat_offset = 30
#     dot_offset = 12
#     with Image.open('Pokemon Template - Left Aligned Template.png').convert('RGBA') as base:
#         out = ImageDraw.Draw(base)
#
#         add_name(out, '447 Riolu')
#         add_hp(out, '3')
#         add_moves(out, moves)
#         add_type(out, my_type)
#         add_ability(out, ability)
#         draw_dex_stats(out, stats)
#
#         base.show()

# def create_stat_sheet():
#     with Image.open('Pokemon_Stat_Sheet.png').convert('RGBA') as base:
#         out = ImageDraw.Draw(base)
#
#         # add_name(out, '447 Riolu')
#         # add_hp(out, '3')
#         # add_moves(out, moves)
#         # add_type(out, my_type)
#         # add_ability(out, ability)
#         add_word(out, 'number', number)
#         add_word(out, 'name', name)
#         # add_word(out, 'moves', moves)
#         add_word(out, 'my_type', my_type)
#         add_word(out, 'ability', ability)
#         add_word(out, 'nature', nature)
#         draw_stats(out, stats)
#         draw_socials(out, stats)
#         draw_skills(out, skills)
#         draw_quick_reference(out, hp, will, initiative, evasion, clash, defense)
#
#         base.show()
# number, name, my_type, ability, base_hp,
#                  stats, skills, socials, rank, moves
move_list = [
    Move(x[0], stats[1], skills[0], stats[0], randrange(0,3), randrange(0,3)) for x in move_examples
]
pkmn = Pokemon(number, name, my_type, ability, nature, hp, stats, skills, socials, rank, move_list)
pkmn.create_stat_sheet()
#
# create_stat_sheet()