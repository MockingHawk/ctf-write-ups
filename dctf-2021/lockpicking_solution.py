#!/usr/bin/env python3

import itertools
from netcat import Netcat
from flint import nmod_mat

class lfsr:
    def __init__(self, state, coefs):
        self.state = state
        self.coefs = coefs

    def next(self):
        n = sum([self.state[i] * self.coefs[i] for i in range(10)]) % 5039 #weird lsfr
        self.state = self.state[1:] + [n]
        return n

def unique(n):
    return len(set("%04d" % n)) == 4

ALL_NUMBERS = ["%04d" % n for n in range(10000) if unique(n)]

def check(pin, guess):
    a = 0
    b = 0
    for i in range(len(guess)):
        if guess[i] in pin:
            if pin.index(guess[i]) == i: a += 1
            else: b += 1
    return [a,b]

def possible_numbers(a,r):
    rep=[]
    b = r%8
    r//=8
    for i in range(10):
        if(r%2 == 1):
            rep.append(str(i))
        r//=2
    l = list(map(lambda x: "".join(x), list(itertools.permutations(rep))))

    new_possible_numbers = []
    for n in l:
        if(check('0123',n) == [a,b]):
            new_possible_numbers.append(n)
    return new_possible_numbers

def optimal_strategy(possible_numbers):
    if(len(possible_numbers) == 1):
        return [possible_numbers[0],1.0]

    if(len(possible_numbers) == 0):
        return ["",0]

    best_avg, best_question = 10**9, ""
    for question in possible_numbers:
        count = [[] for i in range(5)]
        for i in possible_numbers:
            count[check(question,i)[0]].append(i)
        avg_count = 0.0
        for children in count[:-1]:
            avg_count += optimal_strategy(children)[1] * len(children)
        if(avg_count <  best_avg):
            best_avg, best_question = avg_count, question
    return (best_question, 1 + best_avg/len(possible_numbers))

nc = Netcat('dctf1-chall-lockpicking.westeurope.azurecontainer.io', 7777)
print(nc.read())

magic_string = "0123"
for i in range(10):
    magic_string  = magic_string + str(i)*(2**(i+3))


pins = []
for i in range(20):

    nc.write(magic_string.encode() + b"\n")
    s = nc.read()

    hinta = s.split(b"\n")[0].split(b': ')[1]
    a = int(hinta[1]-48)

    hintb = s.split(b"\n")[0].split(b'B')[1]
    b = int(hintb.decode())

    possible_numbers_ac = possible_numbers(a,b)

    while True:
        question = optimal_strategy(possible_numbers_ac)[0]
        nc.write(str(question).encode() + b"\n")
        s = nc.read()

        if(b"Correct" in s):
            pins.append(int(question))
            print(s)
            break
            
        hint = s.split(b"\n")[0].split(b': ')[1]
        a,b = int(hint[1]-48), int(hint[3]-48)
        
        new_possible_numbers = []
        for n in possible_numbers_ac:
            if(check(question,n)[0] == a):
                new_possible_numbers.append(n)
        possible_numbers_ac = new_possible_numbers.copy()

indexes = [ALL_NUMBERS.index("%04d" % n) for n in pins]

mat = [indexes[i:i+10] for i in range(10)]
A = nmod_mat(mat,5039)
B = nmod_mat(10,1, indexes[10:],5039)

coefs = [int(n.str()) for n in A.solve(B).transpose().entries()]
rng = lfsr(indexes[10:], coefs)

for i in range(180):
    nc.write(str(ALL_NUMBERS[rng.next()]).encode() + b"\n")
    s = nc.read()
    print(s)