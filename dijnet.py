#!/usr/bin/env python2

import mechanize
from bs4 import BeautifulSoup
import os
import cgi
import sys
import ConfigParser

config = ConfigParser.SafeConfigParser()
config.read("dijnet.ini")

br = mechanize.Browser()
br.open("http://dijnet.hu")

br.select_form("loginform")
br["username"] = config.get("global", "username")
br["password"] = config.get("global", "password")
br.submit()
if br.title() != 'D\xcdJNET':
    print >> sys.stderr, "A bejelentkezes nem sikerult."
    sys.exit(1)

br.follow_link(text='Sz\xe1mlakeres\xe9s')
assert br.title() == 'D\xcdJNET'

br.select_form(nr=0)
resp = br.submit()
soup = BeautifulSoup(resp.get_data(), "lxml")

urls = [t.td.a["href"] for t in soup.find_all('table')[1].find_all('tr') ]

for url in urls:
    br.follow_link(predicate=lambda link: ('href', href) in link.attrs)
    br.follow_link(text='Let\xf6lt\xe9s')
    try:
        link = br.find_link(text='\xa0Sz\xe1mla nyomtathat\xf3 verzi\xf3ja (PDF) - Hiteles sz\xe1mla')
    except:
        link = br.find_link(text='\xa0Hiteles sz\xe1mla')
    (fn, info) = br.retrieve(link.absolute_url, "tmp")
    header = info.getheader('Content-Disposition')
    value, params = cgi.parse_header(header)
    os.rename(fn, params['filename'])
    print params['filename']
    br.follow_link(text='[IMG]\xa0vissza a list\xe1hoz')
