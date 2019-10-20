import random
import smtplib

def generateKey():
    s = '()1234567890abcdefghijklnmopqrstuvwxyz'
    r_string = ''
    for x in range(0, 20):
        r_string += s[random.randint(0, 37)] # inclusive
    return '<'+r_string+'>'

# sender = "Pur-Religion <ubuntu@cse356-project.cloud.compas.cs.stonybrook.edu>>"
def sendEmail(key_string, reciever):
    message ="""
From: Kat Triller <ubuntu@cse356-project.cloud.compas.cs.stonybrook.edu>
To: {} <{}>
Subject: Our New Religion

Are you interested in joining our new religion of cat trilling?
See secret key below:
{}""".format(reciever, reciever, key_string)
    try:
        smtpObj = smtplib.SMTP('localhost')
        smtpObj.sendmail(sender, receivers, message)
    except:
        print("Let us trill in unison")
        
