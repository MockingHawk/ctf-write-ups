# A primed hash candidate
## Statement

>After the rather embarrassing first attempt at securing our login, our student intern has drastically improved our security by adding more parameters. Good luck getting in now!

We are then given access to a remote server running the following python code :

```python
ERROR = "Wrong password with hash "
SUCCESS = "Login successful!\nFlag: REDACTED\n"
PASSWD = 91918419847262345220747548257014204909656105967816548490107654667943676632784144361466466654437911844
secret1 = "REDACTED"
secret2 = "REDACTED"
secret3 = int("xxx")

def hash(data):
    out = 0
    data = [ord(x) ^ ord(y) for x,y in zip(data,secret1*len(data))]
    data.extend([ord(c) for c in secret2])
    for c in data:
        out *= secret3
        out += c
    return out

data = input("Please enter password below\n")

try:
    while True:
        if hash(data) == PASSWD:
            print(SUCCESS)
            break
        else:
            print(ERROR + str(hash(data)))
            data = input("Please enter password below\n")
except EOFError:
    pass

```
## Analysis
We see that the server asks us for a password. It then hashes it using a custom function and compares it to the  `PASSWD` value. We then need to find an input producing the given hash. As the server is kind enough to give us the hash of inputs we feed him, this will be  useful for our attack.

The hashing function works in three steps:
1. Our input is xored with the word `secret1`.
2. `secret2` is appended to the previous xored string.
3. The final string is then mapped to an integer using a pseudo base-conversion.


### Finding secret3
The first thing to remark is that an null string is a valid input:
```
Please enter password below

Wrong password with hash 102600138716356059007219996705144046117627968461
```
The given hash is then `f(secret2)` where `f` is the pseudo-conversion function.

For any given input `m` its hash is then `hash(m) = f(m xor secret1) * secret3^len(secret2) + f(secret2)`. We then know that `secret3` divides `gcd(hash(1)-f(secret2), hash(0)-f(secret2))`. We compute the gcd using sage for example :

```python
sage: hash0 = 19005887928914280732260134378748151614599045204546
sage: hash1 = 18783496307853128677280688327194704466734557942945
sage: fsecret2 = 102600138716356059007219996705144046117627968461
sage: gcd01 = gcd(hash0-fsecret2, hash1-fsecret2)
sage: factor(gcd01)
233^20
```
We then deduce that `secret3 = 233`.

### Finding secret2
This step is actually not necessary since we already know `fsecret2`, but we can stll invert the base-conversion function that encrypted `secret2` by converting the integer in base 10 to an integer base 233, and displaying each 'digit' as an ascii character.

```python
chars = []
fsecret2 = 102600138716356059007219996705144046117627968461
while fsecret2 > 0:
    modulo = fsecret2%233
    chars.append(chr(modulo))
    fsecret2 = fsecret2//233
print(b"".join(chars[::-1]))
```
Running the code gives us `secret2 = 'ks(3n*cl3p%3925(*4*2'`

### Finding secret1
To find `secret1`, we can process similarly as we did in the last step. First, we need to hash a very long input, to make sure that all characters of `secret1` are indeed xored at one point.

We can then take the hash of `20*'0' = '00000000000000000000'`, which should be long enough. We find that 
`hash(20*'0') = 18126456734850052517766482160657835416461226894114798664396414018388402487161697110017734000706`
Then, we can substract the known part from `secret2` and `secret3` to stay with the interesting stuff.

We end with the following code :

```python
chars = []
bighash = 18126456734850052517766482160657835416461226894114798664396414018388402487161697110017734000706
interestingpart = (bighash - fsecret2) // (233**20)
while interestingpart > 0:
    modulo = interestingpart%233
    chars.append(chr(modulo ^ ord('0')))
    interestingpart = interestingpart//233
print("".join(chars[::-1]))
```
Running the code gives us `el3PH4nT$el3PH4nT$el`, we then deduce that `secret1 = 'el3PH4nT$'`

### Decoding the password
Now that we know all the secrets, we are able to compute back the password from the hash `PASSWD`. The only difficulty is that we don't know the length of the original password, and so we can't use the same trick as before without modifying it, as we don't know which character of `secret1` to xor from.

Nevertheless, we are only interested in the length of the password modulus the length of `secret1`, so we can bruteforce this part.

```python
for l in range(len(secret1)):
    interestingpart = (PASSWD-fsecret2)//233**20
    index = l
    chars = []
    while interestingpart>0:
        modulo = interestingpart%233
        chars.append(chr(modulo ^ ord(secret1[index%9])))
        index=(index+8)%9
        interestingpart = interestingpart//233
    if(hash("".join(chars[::-1])) == PASSWD):
        print("".join(chars[::-1]))
```
This gives us a collision for the given hash: `GZZ9t3W3Ar34un44m8PLXX6`.

We can get the flag now:
```console
Please enter password below
GZZ9t3W3Ar34un44m8PLXX6
Login successful!
Flag: sdctf{W0W_s3cur1ty_d1d_dRaStIcAlLy_1mpr0v3}
```

