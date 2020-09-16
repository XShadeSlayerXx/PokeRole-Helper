import re
import random

pokeweight = re.compile(r'(\d+)%?,? ([\-\',\sA-z]+)(?= \d|$)')

#to hold a list of pokemon/items with weights
#if no weight is given then it is assumed to be 100
class pokeList:
    def __init__(self, isItem = False):
        #check isItem here or when calling?
        self.isItem = isItem
        #weights is a list of ints, pokemon is a list of lists of strings correlated to weights
        self.weights, self.pokemon = [], []

    def returnWeights(self, pokestr : str) -> list:
        try:
            int(pokestr[0])
        except:
            pokestr = '100 '+pokestr
        return re.findall(pokeweight, pokestr)

    def add(self, pokestr : str):
        pokeweighted = self.returnWeights(pokestr)

        for x in range(0,pokeweighted,2):
            if pokeweighted[x] in self.weights:
                w = self.weights.index(pokeweighted[x])
                self.pokemon[w].append(pokeweighted[x+1])
            else:
                self.weights.append(pokeweighted[x])
                self.pokemon.append(pokeweighted[x+1])

    def setItem(self, item : bool):
        self.isItem = item

    def item(self) -> bool:
        return self.isItem

    #try to remove the pokemon at the given weights (100 is none is given)
    def sub(self, pokestr : str):
        pokeweighted = self.returnWeights(pokestr)
        odds = pokeweighted[0::2]
        pokelists = pokeweighted[1::2]
        tempnew = self.pokemon[:]
        for x in range(odds):
            try:
                where = self.weights.index(odds[x])
            except:
                raise ValueError(f'{odds[x]}% is not in the list. List not changed.')
            for y in pokelists:
                try:
                    tempnew[where].remove(y)
                except:
                    #the pokemon wasn't in the list. print to console for testing?
                    #also make sure all pokemon are same capitalization
                    pass

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
        for x in range(len(self.weights)):
            msg += f'{x}% - {"  |  ".join(self.pokemon[x])}'
        return msg