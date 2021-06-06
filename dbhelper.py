import sqlite3
from sqlite3 import Error
import csv
import os

db_file = 'pokerole.db'

# TODO: function to return whole table as list
#  (for items and generational stuff)
#  implement the other lists too
#  add evolution stuff and backwards search for %e moves

def create_connection(file):
    connection = None
    try:
        connection = sqlite3.connect(file)
    except Error as e:
        print(e)
    return connection

class Database:
    def __init__(self):
        self.connection = create_connection(db_file)
        # self.instantiateAllLists()

    def reloadLists(self):
        try:
            self.connection.close()
        except:
            pass
        finally:
            os.remove(db_file)
            self.connection = create_connection(db_file)
            self.instantiateAllLists()

    def instantiateAllLists(self):
        self.instantiatePkmnLearnsList()
        self.instantiatePkmnStatList()
        self.instantiatePkmnMoveList()
        self.instantiatePkmnAbilityList()
        self.instantiateEvoList()

    def close_connection(self):
        self.connection.close()

    def create_table(self, name, values):
        # values in the format
        # name type conditions, name2 type2 conditions2, etc
        cmd = f"CREATE TABLE IF NOT EXISTS {name} ( {values} );"
        try:
            cursor = self.connection.cursor()
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

    def custom_query(self, query, multiple : bool = True):
        cursor = self.connection.cursor()
        cursor.execute(query)
        if multiple:
            rows = cursor.fetchall()
        else:
            rows = cursor.fetchone()

        cursor.close()
        return rows

    def query_table(self, tablename, qtype, val):
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT * FROM {tablename} WHERE {qtype}='{val}'")
        rows = cursor.fetchall()

        cursor.close()
        return rows

    def delete_table(self, tablename):
        cursor = self.connection.cursor()
        cursor.execute(f'DROP TABLE {tablename}')

        cursor.close()
        self.connection.commit()

    #TODO: initialize evolution table
    # and modify %encounter to aggregate the moves
    # (in a dictionary of sets?)
    # .
    # P.S. you can use cursor_result.fetchone() to check if an entry exists
    # Return [this] + previousEvoFunc()

    def instantiateEvoList(self):
        cursor = self.connection.cursor()
        tblnm = 'pkmnEvo'
        vals = """
        name text PRIMARY KEY,
        previous text
        """
        self.create_table(tblnm, vals)
        with open('pokeEvoListFull.csv', 'r', newline = '', encoding = "UTF-8") as infile:
            reader = csv.reader(infile)
            next(reader)  #skip the header
            for row in reader:
                tmp = ','.join('?' * len(row))
                cursor.execute(f'INSERT OR REPLACE INTO {tblnm} values ({tmp})', row)
        cursor.close()
        self.connection.commit()

    def instantiatePkmnStatList(self):
        cursor = self.connection.cursor()
        tblnm = 'pkmnStats'
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
        gender text
        """
        self.create_table(tblnm, vals)
        with open('PokeroleStats.csv', 'r', newline = '', encoding = "WINDOWS-1252") as infile:
            reader = csv.reader(infile)
            next(reader)  #skip the header
            for row in reader:
                tmp = ','.join('?' * len(row))
                newrow = [row[0][1:]] + row[1:]
                cursor.execute(f'INSERT OR REPLACE INTO {tblnm} values ({tmp})', newrow)
        cursor.close()
        self.connection.commit()

    def instantiatePkmnLearnsList(self):
        cursor = self.connection.cursor()
        tblnm = 'pkmnLearns'
        vals = 'number integer NOT NULL, name text PRIMARY KEY' + ''.join(
            [f', move{x} text, rank{x} integer' for x in range(28)])
        ranks = {'Starter': 0, 'Beginner': 1, 'Amateur': 2, 'Ace': 3, 'Pro': 4, 'Master': 5, 'Champion': 6}
        self.create_table(tblnm, vals)
        with open('PokeLearnMovesFull.csv', 'r', newline = '', encoding = "UTF-8") as infile:
            reader = csv.reader(infile)
            for row in reader:
                value = row[1:]
                value[1::2] = [ranks[x] for x in value[1::2]]
                value += [None] * (56 - len(value))  #pad value to number of moves maximum
                num = row[0][:3]
                nam = row[0][4:]
                tmp = ','.join('?' * 58)
                newrow = [num, nam] + value
                cursor.execute(f'INSERT OR REPLACE INTO {tblnm} values ({tmp})', newrow)
        cursor.close()
        self.connection.commit()

    def instantiatePkmnMoveList(self):
        cursor = self.connection.cursor()
        tblnm = 'pkmnMoves'
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
        effect text
        """
        self.create_table(tblnm, vals)
        with open('pokeMoveSorted.csv', 'r', newline = '', encoding = "UTF-8") as infile:
            reader = csv.reader(infile)
            for row in reader:
                tmp = ','.join('?' * len(row))
                cursor.execute(f'INSERT OR REPLACE INTO {tblnm} values ({tmp})', row)
        cursor.close()
        self.connection.commit()

    def instantiatePkmnAbilityList(self):
        cursor = self.connection.cursor()
        tblnm = 'pkmnAbilities'
        vals = """
        name text PRIMARY KEY,
        description text NOT NULL
        """
        self.create_table(tblnm, vals)
        with open('PokeRoleAbilities.csv', 'r', newline = '', encoding = "UTF-8") as infile:
            reader = csv.reader(infile)
            next(reader)  #skip the header
            for row in reader:
                tmp = ','.join('?' * len(row))
                cursor.execute(f'INSERT OR REPLACE INTO {tblnm} values ({tmp})', row)
        self.connection.commit()