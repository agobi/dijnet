#!/usr/bin/env python3
# vim: set fileencoding=utf-8 :

import configparser
import cgi
import sys

import mechanicalsoup


def onclick_parser(onclick):
    link_start_index = onclick.find('\'') + 1
    onclick_link = onclick[link_start_index:-2]
    return onclick_link


config = configparser.ConfigParser()
config.read("dijnet.ini")

username = config.get('global', 'username')
password = config.get('global', 'password')
url = config.get('global', 'url')
loginPage = url + config.get('global', 'login')
logoutPage = url + config.get('global', 'logout')

br = mechanicalsoup.StatefulBrowser(soup_config={'features': 'lxml'})
br.open(loginPage)
br.select_form('form[action="/ekonto/login/login_check_password"]')
br["username"] = username
br["password"] = password
br.submit_selected()

if not br.get_current_page().find(string="Ügyfél: "):
    print("A bejelentkezes nem sikerult.", file=sys.stderr)
    sys.exit(1)

br.follow_link(link_text=u'Számlakeresés')
assert br.get_current_page().title.text == u'DÍJNET'

br.select_form(nr=0)
br.submit_selected()
page = br.get_current_page()

links = []

for t in page.select('table.szamla_table')[0].find_all('tr'):
    links.append(url + onclick_parser(t.td['onclick']))

for link in links:
    br.open(link)
    br.follow_link(link_text=u'Letöltés')
    page = br.get_current_page()
    messages = page.find_all('div', class_="xt_link_cell__download")
    linkText = ''

    for message in messages:
        if 'Hiteles számla' in message.text:
            linkText = message.text
    
    download_link = br.find_link(link_text=linkText)

    data = br.session.get(br.absolute_url(download_link['href']))
    header = data.headers['Content-Disposition']
    value, params = cgi.parse_header(header)
    with open(params['filename'], "wb") as f:
        f.write(data.content)
    print(params['filename'])

    return_link = br.get_current_page().select('a.xt_link__title')
    br.follow_link(return_link[0])

br.open(logoutPage)
