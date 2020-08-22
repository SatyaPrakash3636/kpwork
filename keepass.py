#! /usr/bin/env python3.8

import argparse
import os
import sys
import fileinput
import getpass
from pykeepass import PyKeePass
import json
from json2html import *
from json2table import convert
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

parser = argparse.ArgumentParser(
    description='Description : Search for string including partial word in Keepass Database')
parser.add_argument(
    'inputfile', help='file which contains partial (or complete) strings to search')
parser.add_argument('keepassdb', help='Path to Keepass Database file')
parser.add_argument('emailto', help='TO Email ID (Comma separated)')
parser.add_argument('--subject', '-s',
                    help='Email subject for which scope is being checked')

args = parser.parse_args()
inpath = args.keepassdb
#print(f'inpath = {inpath}')
dbpath = inpath.split('/')[-1]
#print(f'dbpath : {dbpath}')
dbname = dbpath.split('.')[0]
#print(f'dbname : {dbname}')
toemail = args.emailto
outhtml = dbname + '.html'

# Email defination
def send_email(toaddr, FileName):
    fromaddr = "EAI.Admin.ACN@noreply.com"
    msg = MIMEMultipart('alternative')
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Keepass database search result"

    body = open(FileName).read()
    msg.attach(MIMEText(body, 'html'))

    server = smtplib.SMTP('smtp-eu.sanofi.com', 25)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr.split(','), text)
    server.quit()

try:
    dbpass = getpass.getpass(prompt='Enter the Keepass Password: ')
    f = open(args.inputfile)
    kp = PyKeePass(args.keepassdb, password=dbpass)
except FileNotFoundError as err:
    print(f"Exception : {err}")
except Exception:
    print(f"Exception: pykeepass.exceptions.CredentialsError, kindly provide correct password")

else:
    print(f"Looking for input data in {dbname} keepass")
    entry = kp.find_entries(title='.*', regex=True,
                            recursive=True, first=False)
    alldata = []
    for ent in entry:
        if ent.title:
            titlelo = (ent.title).lower()
        else:
            titlelo = 'blank'

        if ent.username:
            userlo = (ent.username).lower()
        else:
            userlo = 'blank'

        if ent.notes:
            noteslo = (ent.notes).lower()
        else:
            noteslo = 'blank'

        if ent.url:
            urllo = (ent.url).lower()
        else:
            urllo = 'blank'
        if ent.group:
            grouplo = str(ent.group).lower().split(': ')[1]
        else:
            grouplo = 'blank'

        datastr = f"{grouplo}::$$::{titlelo}::$$::{urllo}::$$::{noteslo}"
        alldata.append(datastr.lower())

# Deleting older output html file if exist
    if os.path.exists(f'{dbname}.html'):
        os.remove(f'{dbname}.html')


# Working with input server list(filtering duplicates and blank lines)
    inputnodupsnoblank = []
    with f:
        servers = f.readlines()
        inputnodups = list(set(servers))
        for line in inputnodups:
            if not line.isspace():
                inputnodupsnoblank.append(line.strip())
#    print(f'input with no dups: {inputnodups} and \n Input with no blank char : {inputnodupsnoblank} ')

# Searching for the server and related data in Keepass data
    combineddata = []
    finallistdups = []
    for data in alldata:
        for server in inputnodupsnoblank:
            if server.strip().lower() in data:
                finallistdups.append(server.strip())
                cdata = f"{server.lower().strip()}::$$::{data}"
                cdatalist = cdata.split("::$$::")
                combineddata.append(cdatalist)

    if finallistdups:
        finallist = list(set(finallistdups))

# Defining HTML style and writing list of server which were found in keepass DB
        with open(f'{dbname}.html', 'a') as f4:
            f4.write('<!DOCTYPE html> <html> <head> <meta name="description" content="Keepass Search Result"> <meta name="author" content="Satyaprakash Prasad"> ')
            f4.write("<style> body { background-color: darkslategrey; color: Silver; font-size: 1.1em; } h1 { color: coral; } #intro { font-size: 1.3em; } .colorful { color: orange; } .myTable { width: 100%; text-align: center; background-color: lemonchiffon; border-collapse: collapse; } .myTable th { background-color: goldenrod; color: white; } .myTable td { padding: 2px; border: 1px solid goldenrod; color: black } .myTable th { padding: 2px; border: 1px solid goldenrod; } </style> </head>")
            f4.write('<body>')
            f4.write(f'<h1>{len(finallist)} servers found in {dbname} Keepass</h1>')
            if args.subject:
                f4.write(f'<p id="intro">Email : {args.subject}</p>')
            f4.write(json2html.convert(json=finallist))

        for fserver in finallist:
            fserverdata = []
            fserverdictlist = []
            for listdata in combineddata:
                if fserver.lower() == listdata[0]:
                    fserverdata.append(listdata[1:])
                    fserverdict = {
                        'GROUP': listdata[1],
                        'TITLE': listdata[2],
                        'URL': listdata[3],
                        'NOTES': listdata[4]
                    }
                    fserverdictlist.append(fserverdict)
            nodupsfserverdictlist = []
            for i in range(len(fserverdictlist)):
                if fserverdictlist[i] not in fserverdictlist[i + 1:]:
                    nodupsfserverdictlist.append(fserverdictlist[i])
            serverjson = {
                fserver.lower(): nodupsfserverdictlist
            }

            build_direction = "TOP_TO_BOTTOM"
            table_attributes = {"class": "myTable"}
            with open(f'{dbname}.html', 'a') as f4:
                f4.write('<br>')
                f4.write(convert(serverjson, build_direction=build_direction,
                                 table_attributes=table_attributes))

        with open(f'{dbname}.html', 'a') as f4:
            f4.write('<br>')
            f4.write(f'<p id="intro">Below are the servers which are not in Keepass:</p>')
            notfound = list(set(inputnodupsnoblank) - set(finallist))
            f4.write(json2html.convert(json=notfound))
            f4.write('</body> </html>')
        #print(f'Input data : {inputnodupsnoblank}')
        #print(f'Final list: {finallist}')
        with open(f'{dbname}.html', 'rt') as f4:
            htmldata = f4.read()
            htmldata = htmldata.replace('<ul><li><table', '<table')
            htmldata = htmldata.replace('</table></li></ul>', '</table>')
        with open(f'{dbname}.html', 'wt') as f4:
            f4.write(htmldata)

        # for found in finallist:
        #     print(f'{found} found in Keepass')
        send_email(toemail, outhtml)
        print(f'Output has been emailed to "{toemail}"')

    else:
        with open(f'{dbname}.html', 'a') as f4:
            f4.write('<head> <meta name="description" content="Keepass Search Result"> <meta name="author" content="Satyaprakash Prasad"> </head>')
            f4.write("<style> body { background-color: darkslategrey; color: Silver; font-size: 1.1em; } h1 { color: coral; } #intro { font-size: 1.3em; } .colorful { color: orange; } .myTable { width: 100%; text-align: center; background-color: lemonchiffon; border-collapse: collapse; } .myTable th { background-color: goldenrod; color: white; } .myTable td { padding: 2px; border: 1px solid goldenrod; color: black } .myTable th { padding: 2px; border: 1px solid goldenrod; } </style>")
            f4.write(f'<h1>{len(finallistdups)} servers found in {dbname} Keepass</h1>')
            if args.subject:
                f4.write(f'<p id="intro">Email : {args.subject}</p>')
            f4.write('<p class="colorful">No servers found in Keepass</p>')

#        print('No servers found in Keepass')
        send_email(toemail, outhtml)
