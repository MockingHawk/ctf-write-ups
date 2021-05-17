# Lockpicking
## Statement

>We were playing a game of cows and bulls and decided 260 guesses was enough for 200 pins. <br>
`nc dctf1-chall-lockpicking.westeurope.azurecontainer.io 7777`

A hint is also given:
> But this isn't a regular game of cows and bulls.

The following file `lockpicking.py` is running on the remote server:

```python
from random import randint
from signal import signal, alarm, SIGALRM
from secret import solvable, flag

class lsfr:
    def __init__(self):
        self.state = [randint(0, 5039) for _ in range(10)]
        while True:
            self.coefs = [randint(0, 5039) for _ in range(10)]
            if solvable(self): 
                break

    def next(self):
        n = sum([self.state[i] * self.coefs[i] for i in range(10)]) % 5039
        self.state = self.state[1:] + [n]
        return n

def check(pin, guess):
    a = 0
    b = 0
    for i in range(len(guess)):
        if guess[i] in pin:
            if pin.index(guess[i]) == i: a += 1
            else: b += 1
    return [a,b]

def unique(n):
    return len(set("%04d" % n)) == 4

def play():
    i = 0
    print("Flag is locked under %d pins, you have %d guesses." % (N, r))

    for _ in range(r):
        guess = input("Enter pin %d:\n>" % (i+1))
        a, b = check(pins[i], guess)
        if a == 4 and b == 0:
            i += 1
            if i == N:
                print("Congratulations! Here is the flag: %s" % flag)
                return
            else:
                print("Correct, onto the next one!")
        else: 
            print("Wrong! Hint: A%dB%d" % (a,b))

    print("Out of guesses, exiting...")


def timeout(a, b):
    print("\nOut of time. Exiting...")
    exit()

signal(SIGALRM, timeout) 
alarm(5 * 60) 

rng = lsfr()
r = 260
N = 200

all = ["%04d" % n for n in range(10000) if unique(n)]

pins = [all[rng.next()] for _ in range(N)]

play()

```
## Analysis
For those wondering, cows and bulls is a game where one player choses a number with exactly foUr different digits, and the other player must make guesses to find the secret. At each round, the guesser gives a valid number, and the game master replies with the number of correct digits in the correct position (the bulls), and the number of correct digits in the wrong position (the cows).

The above program then makes us play the game 200 times, but gives us only 260 guesses in total, which is not much. 

Let's see how we can manage to hack the game.

### Reversing lfsr
The first thing to remark is that the numbers chosen by the program are generated with a lfsr ([Linear-feedback shift register](https://en.wikipedia.org/wiki/Linear-feedback_shift_register)), over the field GF(5039), with a sequence length of 10, ie, that the next output from the generator depends only on the last 10 values previously outputted, and on 10 internal coefficients.

If we call `x_i` the outputs of the lfsr and  `c_i` its coefficient, we have the following formula to generate `x_10` for example :  `x_0*c_0 + x_1*c_1 + ... + x_9*c_9 = x_10`. 

If we gather all these equations for `x_10` up to `x_19`, we then have theoretically enough equations to inverse the system and find the coefficients, if the matrix of the `x_i` is non singular. However, the condition `solvable` in the original file must assure this.

I provide the following code to inverse the matrix of the `x_i` to retrieve the coefficients. We can then instantiate a new instance of `lfsr` that will give us the correct numbers for following rounds. (I modified the constructor of `lfsr` for additional simplicity).
```python
from flint import nmod_mat

indexes = [ALL_NUMBERS.index("%04d" % n) for n in pins[:20]]

mat = [indexes[i:i+10] for i in range(10)]
A = nmod_mat(mat,5039)
B = nmod_mat(10,1, indexes[10:],5039)

coefs = [int(n.str()) for n in A.solve(B).transpose().entries()]
rng = lfsr(indexes[10:], coefs)

```
However, reversing the lfsr only works for rounds 20-200, and we still need to find a way to retrieve the first pins. 

### Finding the first pins the normal way
The first idea that I had was just to solve the bulls and cows game normally, and then combine it with the previous method for the later rounds.

I used [this implementation](https://github.com/vpavlenko/bulls-and-cows/blob/master/solver.py)to try it on the spot. However, it appears that the average number of rounds needed to solve a game is about 5.2-5.4 rounds, and if we make the computations, we only have `260-180 = 80` guesses for 20 pins. The distribution is pretty well centered, and we would need a tremendous amount of luck to solve 20 pins in 80 moves.

I then thought that we could optimize the lfsr reversing to need less than 20 rounds, but careful analysis showed that even with 9 equations instead of 10, we could not reduce the space search at all in the general case. In average, my solution reached round 170.

The only thing left was then to rig the game itself, and this is when I finally understood the hint.

### Taking advantage of the implementation
After looking carefully at the code, I saw that no checking was made at all on the input:

```python
def check(pin, guess):
    a = 0
    b = 0
    for i in range(len(guess)):
        if guess[i] in pin:
            if pin.index(guess[i]) == i: a += 1
            else: b += 1
    return [a,b]
```
We could then make guesses of arbitraty length, and still have a meaningful answer for the cows answer.

I then decided to input a string containing each digit a certain amount of time to be able to guess if they were present in only one guess. The easiest way to do this is to create a number that contains 2^0 times the digit 0, 2^1 times the digit 1 and so on, and to decompose it back in binary to get the correct digits after answer from the server. I decided to put `x` for the first 4 digits to avoid confusion in case of a collision.

My code is as follows for the generation and the decoding:
```python
magic_string = "xxxx"
for i in range(10):
    magic_string  = magic_string + str(i)*(2**i))

def possible_numbers(b):
    answer=[]
    for i in range(10):
        if(b%2 == 1):
            answer.append(str(i))
        b//=2
    return list(map(lambda x: "".join(x), list(itertools.permutations(answer))))
```
With only one guess, we are then able to reduced the search space from 5039 entries to only 24.

However, with the previous implementation of the bull and cows solver copied from github, we still seem to take too many guesses, as I can only reach around pin 180. 

### Improving the algorithm
The previous algorithm was relying on entropy to select a good guess to make at each step, while still being efficient. However, we are now down to a mere 24 possibilites, so I decided to implement the optimal algorithm, that relies on exploring the graph of possibilites at each step. 

The code is pretty basic, so I just copy it here :

```python
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
```

After all this, we still can't get to the flag, and we reach only pin 190.
At this point, the only possibility that I see is to pray for a correct seed, or to take advantage of the 4 digits in the `magic_string` that I spared earlier.

### Taking advantage of the first digits
I then decided not to pray, and I slightly modified the `magic_string` to contain 8 times digit 0, 16 times the digit 1 etc... I replaced the `xxxx` by the guess `0123` and slightly modified my decoding to get rid of the guesses that did not match the correct difference with `0123`. 

The updated code is this one :
```python
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
```

Finally after trying this last version, I managed to get the flag
```console
'Congratulations! Here is the flag: dctf{N0_way_y0u_gu3ss3d_that_w1thout_ch34t1ng}\n'
```
The full code of my solution is available [here](lockpicking_solution.py).

