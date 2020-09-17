import re
import random

pokeweight = re.compile(r'(\d+)%?,? ([\-\',\sA-z]+)(?= \d|$)')

#TODO: balance weights over 100, and return 'None' for random'd weights between max and 100

#to hold a list of pokemon/items with weights
#if no weight is given then it is assumed to be 100
def returnWeights(pokestr : str) -> list:
    try:
        int(pokestr[0])
    except:
        pokestr = '100 '+pokestr
    temp = re.findall(pokeweight, pokestr)
    temp = [(x[0], x[1].replace(',','').split(' ')) for x in temp]
    return temp


class PokeList:
    def __init__(self, pokestr = None, isItem = False, weights : list = [], pokemon : list = []):
        #check isItem here or when calling?
        self.isItem = isItem
        #weights is a list of ints, pokemon is a list of lists of strings correlated to weights
        self.weights, self.pokemon = [weights, pokemon]
        print('initial print: ',self.weights, self.pokemon)
        if pokestr is not None:
            for x in returnWeights(pokestr):
                self.weights.append(int(x[0]))
                self.pokemon.append(x[1])

    def add(self, pokestr : str = None, odds : list = None, pokes : list = None):
        if pokestr is not None:
            self.addw(returnWeights(pokestr))
            return
        if len(odds) != len(pokes):
            raise AssertionError('The list sizes need to be equivalent.')
        print('odds: ', odds, 'pokes: ', pokes)
        self.addw([(odds[x], pokes[x]) for x in range(len(odds))])

    def addw(self, pokeweighted : list):
        print('pokeweighted: ',pokeweighted)
        for x in range(0,len(pokeweighted)):
            print('pw: ',pokeweighted[x][0],'sw: ',self.weights)
            weight = int(pokeweighted[x][0])
            if weight in self.weights:
                w = self.weights.index(weight)
                #append one at a time to the list
                for poke in pokeweighted[x][1]:
                    #ignore duplicates
                    if poke not in self.pokemon[w]:
                        self.pokemon[w].append(poke)
            else:
                print('else')
                self.weights.append(weight)
                self.pokemon.append(pokeweighted[x][1])

    def setItem(self, item : bool):
        self.isItem = item

    def isEmpty(self) -> bool:
        return True if len(self.weights) == 0 else False

    def changeOdds(self, originalOdds : int, newOdds : int):
        for i,x in enumerate(self.weights):
            if x == originalOdds:
                self.weights[i] = newOdds

    def changePokes(self, originalPokes : list, newPokes : list):
        for i, x in enumerate(self.pokemon):
            if x == originalPokes:
                self.pokemon[i] = newPokes

    def getOdds(self):
        return self.weights

    def getPokemon(self):
        return self.pokemon

    def getSize(self) -> int:
        return len(self.weights)

    #try to remove the pokemon at the given weights (100 is none is given)
    def sub(self, pokestr : str = None, odds : list = None, pokelists : list = None):
        if pokestr is not None:
            pokeweighted = returnWeights(pokestr)
            odds = pokeweighted[0::2]
            pokelists = pokeweighted[1::2]
        elif odds is None or pokelists is None:
            raise AssertionError(f'Bad arguments passed.')
        tempnew = self.pokemon[:]
        for x in range(len(odds)):
            try:
                where = self.weights.index(odds[x])
            except:
                raise ValueError(f'{odds[x]}% is not in the list. List not changed.')
            for y in pokelists[where]:
                try:
                    tempnew[where].remove(y)
                except:
                    #the pokemon wasn't in the list. print to console for testing?
                    #also make sure all pokemon are same capitalization
                    print('unable to remove: ',y)
                    pass
        self.pokemon = tempnew[:]

    def __add__(self, other):
        print("before", self.weights, self.pokemon)
        self.add(odds = other.weights, pokes = other.pokemon)
        print("after", self.weights, self.pokemon)
        #idek
        return self

    def __sub__(self, other):
        self.sub(odds = other.weights, pokelists = other.pokemon)
        return self

    def first(self):
        return self.pokemon[0][0]

    def clear(self):
        self.pokemon.clear()
        self.weights.clear()

    #return a random poke, if rList is True then return a list of pokes
    def random(self, rList : bool = False) -> str:
        which = 0
        odds = self.weights
        rand = random.randrange(1,101) - odds[0]
        while rand > 0 and which < len(odds) - 1:
            which += 1
            rand -= odds[which]
        if rList:
            #return a list
            return self.pokemon[which]
        else:
            #return a single poke
            return random.choice(self.pokemon[which])

    #returns a list of tuples, (weight, list of pokemon)
    def toList(self) -> list:
        return [(self.weights[x],self.pokemon[x]) for x in range(len(self.weights))]

    def __repr__(self):
        msg = ''
        for i, x in enumerate(self.weights):
            msg += f'{x}% - {"  |  ".join(self.pokemon[i])}\n'
        return msg