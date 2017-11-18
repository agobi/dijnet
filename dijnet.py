#!/usr/bin/env python2
# vim: set fileencoding=utf-8 :

import ConfigParser
import cgi
import sys

import mechanicalsoup

config = ConfigParser.SafeConfigParser()
config.read("dijnet.ini")

br = mechanicalsoup.StatefulBrowser(soup_config={'features': 'lxml'})
br.open("http://dijnet.hu")

br.select_form("#login-form")
br["username"] = config.get("global", "username")
br["password"] = config.get("global", "password")
br.submit_selected()
if not br.get_current_page().find(string="Ügyfél: "):
    print >> sys.stderr, "A bejelentkezes nem sikerult."
    sys.exit(1)

br.follow_link(link_text=u'Számlakeresés')
assert br.get_current_page().title.text == u'DÍJNET'

br.select_form(nr=0)
br.submit_selected()
page = br.get_current_page()

links = [t.td.a for t in page.select('table.szamla_table')[0].find_all('tr')]

for link in links:
    br.follow_link(link)
    br.follow_link(link_text=u'Letöltés')

    download_link = br.find_link(link_text=u'\xa0Számla nyomtatható verziója (PDF) - Hiteles számla')

    data = br.session.get(br.absolute_url(download_link['href']))
    header = data.headers['Content-Disposition']
    value, params = cgi.parse_header(header)
    with open(params['filename'], "w") as f:
        f.write(data.content)
    print params['filename']

    return_link = br.get_current_page().select('a.xt_link__title')
    br.follow_link(return_link[0])
