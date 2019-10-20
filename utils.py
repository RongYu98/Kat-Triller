import random

def generateKey():
    s = '!@#$%^&*()1234567890abcdefghijklnmopqrstuvwxyz'
    r_string = ''
    for x in range(0, 20):
        r_string += s[random.randint(0, 45)] # inclusive
    return r_string
