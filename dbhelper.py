import json
import sqlite3
from pathlib import Path
from sqlite3 import Error
import csv
import os

db_file_v2 = 'pokerole.db'
db_file_v3 = 'pokerole_v3.db'
data_path = 'pokerole_data/'
versions = ['v2.0', 'v3.0']
data_folders = {
    'pkmn': '/Pokedex',
    'moves': '/Moves',
    'abilities': '/Abilities',
    'items': '/items'
}

table_names = {
    'pkmnStats': 'pkmnStats',
    'pkmnLearns': 'pkmnLearns',
    'pkmnMoves': 'pkmnMoves',
    'pkmnAbilities': 'pkmnAbilities',
    'pkmnItems': 'pkmnItems',
    'pkmnEvo': 'pkmnEvo'
}

def create_connection(file):
    connection = None
    try:
        connection = sqlite3.connect(file)
    except Error as e:
        print(e)
    return connection

def get_generation(number : str) -> int:
    if 'A' in number or 'B' in number: #Alolan or Beast
        return 7
    elif 'G' in number: #Galar
        return 8
    elif 'D' in number: #Delta... (Pokemon Insurgence?)
        return -1
    elif 'M' in number: #Mega
        number = number[:number.index("M")]
    elif 'H' in number: #Hisuian
        return 9
    elif 'P' in number: #Paldean
        return 10
    elif 'F' in number:
        number = number[:number.index("F")]
    number = int(number)
    cutoffs = [0, 151, 251, 386, 493, 649, 721, 809, 898]
    for i, num in enumerate(cutoffs):
        if number <= num:
            return i
    return 9

class Database:
    def __init__(self):
        self.connection = create_connection(db_file_v3)
        self.connection_old = create_connection(db_file_v2)
        for version in versions:
            self.checkIntegrity(version=version)

    def get_cursor(self, version : str = "v3.0"):
        if version in ["v2.0", "v2", "2"]:
            return self.connection_old.cursor()
        return self.connection.cursor()

    def connection_commit(self, version : str = "v3.0"):
        if version in ["v2.0", "v2", "2"]:
            return self.connection_old.commit()
        return self.connection.commit()

    def reloadLists(self, version : str = "v3.0"):
        if version in ["v2.0", "v2", "2"]:
            try:
                self.connection_old.close()
            except:
                pass
            finally:
                os.remove(db_file_v2)
                self.connection_old = create_connection(db_file_v2)
                self.instantiateAllLists(version="v2.0")

        else:
            try:
                self.connection.close()
            except:
                pass
            finally:
                os.remove(db_file_v3)
                self.connection = create_connection(db_file_v3)
                self.instantiateAllLists(version="v3.0")

    def checkIntegrity(self, version = "v3.0"):
        cursor = self.get_cursor(version=version)
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name NOT LIKE "SQLITE_%"')
        result = cursor.fetchall()
        result = [x[0] for x in result] #strip the single tuple to be a readable string
        cursor.close()

        for val in table_names.values():
            if val not in result:
                print(f'Needed to refresh the {version} tables, "{val}" was missing')
                self.reloadLists(version=version)
                break

    def instantiateAllLists(self, version : str = "v3.0"):
        self.build_tables(version=version)
        self.instantiatePokemonLists(version=version)
        self.instantiateMoveList(version=version)
        self.instantiateAbilityList(version=version)

        self.instantiatePkmnItemList()
        # self.instantiateItemList()

    def close_connection(self):
        self.connection.close()

    def create_table(self, name, values, version : str = "v3.0"):
        # values in the format
        # name type conditions, name2 type2 conditions2, etc
        cmd = f"CREATE TABLE IF NOT EXISTS {name} ( {values} );"
        try:
            cursor = self.get_cursor(version)
            cursor.execute(cmd)
        except Error as e:
            print(e)
        finally:
            cursor.close()

    def insert_into_table(self, tablename, values):
        cursor = self.connection.cursor()
        tmp = ','.join('?' * len(values))
        cursor.execute(f'INSERT INTO {tablename} values ({tmp})', values)

        tmp = cursor.lastrowid
        cursor.close()
        self.connection.commit()
        return tmp

    def custom_query(self, query, multiple : bool = True, version : str = "v3.0"):
        cursor = self.get_cursor(version)
        cursor.execute(query)
        if multiple:
            rows = cursor.fetchall()
        else:
            rows = cursor.fetchone()

        cursor.close()
        return rows

    def query_table(self, tablename, qtype, val, version : str = "v3.0"):
        cursor = self.get_cursor(version)
        cursor.execute(f'SELECT * FROM {tablename} WHERE {qtype}="{val}"')
        rows = cursor.fetchall()

        cursor.close()
        return rows

    def delete_table(self, tablename):
        cursor = self.connection.cursor()
        cursor.execute(f'DROP TABLE {tablename}')

        cursor.close()
        self.connection.commit()

    def build_tables(self, version : str = "v3.0"):
        tblnm = table_names['pkmnEvo']
        vals = """
        name text PRIMARY KEY,
        previous text
        """
        self.create_table(tblnm, vals, version=version)
        #####
        tblnm = table_names['pkmnStats']
        vals = """
        number text NOT NULL,
        name text PRIMARY KEY,
        type1 text NOT NULL,
        type2 text,
        hp integer NOT NULL,
        str integer NOT NULL,
        maxstr integer NOT NULL,
        dex integer NOT NULL,
        maxdex integer NOT NULL,
        vit integer NOT NULL,
        maxvit integer NOT NULL,
        spc integer NOT NULL,
        maxspc integer NOT NULL,
        ins integer NOT NULL,
        maxins integer NOT NULL,
        ability text,
        ability2 text,
        abilityhidden text,
        abilityevent text,
        unevolved text,
        form text,
        rank text,
        gender text,
        generation integer NOT NULL
        """
        self.create_table(tblnm, vals, version=version)
        #####
        tblnm = table_names['pkmnLearns']
        vals = 'number integer NOT NULL, name text PRIMARY KEY' + ''.join(
            [f', move{x} text, rank{x} integer' for x in range(28)])
        self.create_table(tblnm, vals, version=version)
        #####
        tblnm = table_names['pkmnMoves']
        vals = """
        name text PRIMARY KEY,
        type text NOT NULL,
        pwrtype text NOT NULL,
        power integer NOT NULL,
        dmg1 text,
        dmg2 text,
        acc1 text,
        acc2 text,
        foe text NOT NULL,
        effect text,
        description text
        """
        self.create_table(tblnm, vals, version=version)
        #####
        tblnm = table_names['pkmnAbilities']
        vals = """
        name text PRIMARY KEY,
        effect text NOT NULL,
        description text
        """
        self.create_table(tblnm, vals, version=version)
        #####
        tblnm = table_names['pkmnItems']
        vals = """
        name text PRIMARY KEY,
        description text,
        type_bonus text,
        value text,
        strength text,
        dexterity text,
        vitality text,
        special text,
        insight text,
        defense text,
        special_defense text,
        evasion text,
        accuracy text,
        specific_pokemon text,
        heal_amount text,
        suggested_price text,
        pmd_price text,
        category text
        """
        self.create_table(tblnm, vals, version=version)


    def instantiatePokemonLists(self, version : str = "v3.0"):
        print("Creating the pokemon tables...")
        # the pokemon in the pokemon folder contain stats, evo info, and the learns list
        stat_table = table_names['pkmnStats']
        evo_table = table_names['pkmnEvo']
        learns_table = table_names['pkmnLearns']
        pkmn_cursor = self.get_cursor(version)
        p = Path(data_path + version + data_folders['pkmn'])
        for raw_poke in p.iterdir():
            with open(raw_poke, encoding="utf-8") as f:
                try:
                    tmp_info = json.load(f)
                    # evolutions first
                    evolutions = tmp_info['Evolutions']
                    tmp = ','.join('?' * 2)
                    canEvolve = False
                    for evo in evolutions:
                        if "To" in evo and evo["Kind"] != "Mega": canEvolve = True
                        if "From" in evo:
                            evo_info = [tmp_info['Name'], evo["From"]]
                            pkmn_cursor.execute(f'INSERT OR REPLACE INTO {evo_table} values ({tmp})', evo_info)

                    # then stats
                    generation = get_generation(tmp_info['DexID'])
                    form = "F" in tmp_info["DexID"]
                    stat_info = [tmp_info['Number'], tmp_info['Name'],
                                 tmp_info['Type1'], tmp_info['Type2'],
                                 tmp_info['BaseHP'],
                                 tmp_info['Strength'], tmp_info['MaxStrength'],
                                 tmp_info['Dexterity'], tmp_info['MaxDexterity'],
                                 tmp_info['Vitality'], tmp_info['MaxVitality'],
                                 tmp_info['Special'], tmp_info['MaxSpecial'],
                                 tmp_info['Insight'], tmp_info['MaxInsight'],
                                 tmp_info['Ability1'], tmp_info['Ability2'],
                                 tmp_info['HiddenAbility'], tmp_info['EventAbilities'],
                                 canEvolve, form,
                                 tmp_info['RecommendedRank'], tmp_info['GenderType'],
                                 generation]
                    tmp = ','.join('?' * len(stat_info))
                    pkmn_cursor.execute(f'INSERT OR REPLACE INTO {stat_table} values ({tmp})', stat_info)

                    # then the learnset

                    ranks = {'Starter': 0, 'Beginner': 1, 'Amateur': 2,
                             'Ace': 3, 'Pro': 4, 'Master': 5, 'Champion': 6,
                             'Rookie': -1, 'Standard': -2, 'Advanced': -3, 'Expert': -4}
                    moves = [tmp_info['Number'], tmp_info['Name']]  # pokedex num and name
                    for move in tmp_info['Moves']:
                        moves.append(move['Name'])
                        moves.append(ranks[move['Learned']])
                    moves += [None] * (58 - len(moves))  # pad value to number of moves maximum
                    tmp = ','.join('?' * 58)
                    pkmn_cursor.execute(f'INSERT OR REPLACE INTO {learns_table} values ({tmp})', moves)
                except KeyError as e: # need to implement the new ranks
                    print(e)
                except json.JSONDecodeError as e:
                    print(raw_poke, e)
                except Exception as e:
                    print("unknown exception: ", raw_poke, e)
        pkmn_cursor.close()
        self.connection_commit(version)

    def instantiateMoveList(self, version : str = "v3.0"):
        print("Creating the move table...")
        move_table = table_names['pkmnMoves']
        move_cursor = self.get_cursor(version)
        p = Path(data_path + version + data_folders['moves'])
        for raw_move in p.iterdir():
            with open(raw_move, encoding="utf-8") as f:
                try:
                    tmp_move = json.load(f)
                    # we can also pull Attributes, Added Effects, and _id
                    move_info = [tmp_move['Name'], tmp_move['Type'], tmp_move['Category'],
                                 tmp_move['Power'], tmp_move['Damage1'], tmp_move['Damage2'],
                                 tmp_move['Accuracy1'], tmp_move['Accuracy2'], tmp_move['Target'],
                                 tmp_move['Effect'], tmp_move['Description']]
                    tmp = ','.join('?' * len(move_info))
                    move_cursor.execute(f'INSERT OR REPLACE INTO {move_table} values ({tmp})', move_info)
                except Exception as e:
                    print(raw_move, e)
        move_cursor.close()
        self.connection_commit(version)

    def instantiateAbilityList(self, version : str = "v3.0"):
        print("Creating the ability tables...")
        ability_table = table_names['pkmnAbilities']
        ability_cursor = self.get_cursor(version)
        p = Path(data_path + version + data_folders['abilities'])
        for raw_ability in p.iterdir():
            with open(raw_ability, encoding="utf-8") as f:
                try:
                    tmp_ability = json.load(f)
                    # we can also pull _id
                    ability_info = [tmp_ability['Name'], tmp_ability['Effect'], tmp_ability['Description']]
                    tmp = ','.join('?' * len(ability_info))
                    ability_cursor.execute(f'INSERT OR REPLACE INTO {ability_table} values ({tmp})', ability_info)
                except Exception as e:
                    print(raw_ability, e)
        ability_cursor.close()
        self.connection_commit(version)

    def instantiateItemList(self, version : str = "v3.0"):
        print("Creating the item tables...")
        items_table = table_names['pkmnItems']
        # need a way to add custom items?
        item_cursor = self.get_cursor(version)
        p = Path(data_path + data_folders['items'])
        for raw_move in p.iterdir():
            with open(raw_move, encoding="utf-8") as f:
                try:
                    tmp_move = json.load(f)
                    # TODO: items need to be completely reworked to fit the new github format
                #     # we can also pull Attributes, Added Effects, and _id
                #     item_info = [tmp_move['Name'], tmp_move['Description'], tmp_move['ForTypes'],
                #                  tmp_move['Value'], tmp_move['Damage1'], tmp_move['Damage2'],
                #                  tmp_move['Accuracy1'], tmp_move['Accuracy2'], tmp_move['Target'],
                #                  tmp_move['Effect'], tmp_move['Description']]
                #     tmp = ','.join('?' * len(item_info))
                #     item_cursor.execute(f'INSERT OR REPLACE INTO {items_table} values ({tmp})', item_info)
                except Exception as e:
                    print(raw_move, e)
        item_cursor.close()
        self.connection_commit(version)

    def instantiatePkmnItemList(self):
        cursor = self.get_cursor(version="v2.0")
        tblnm = table_names['pkmnItems']
        vals = """
        name text PRIMARY KEY,
        description text,
        type_bonus text,
        value text,
        strength text,
        dexterity text,
        vitality text,
        special text,
        insight text,
        defense text,
        special_defense text,
        evasion text,
        accuracy text,
        specific_pokemon text,
        heal_amount text,
        suggested_price text,
        pmd_price text,
        category text
        """

        self.create_table(tblnm, vals)
        with open('PokeRoleItems.csv', 'r', newline = '', encoding = "UTF-8") as infile:
            reader = csv.reader(infile)
            next(reader)  #skip the header
            category = False
            for row in reader:
                tmp = ','.join('?' * (len(row)+1))
                if row[1] == '':
                    category = row[0]
                row.append(('' if row[1] == '' else category))
                cursor.execute(f'INSERT OR REPLACE INTO {tblnm} values ({tmp})', row)
        self.connection.commit()