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
login_page = url + config.get('global', 'login')
logout_page = url + config.get('global', 'logout')

browser = mechanicalsoup.StatefulBrowser(soup_config={'features': 'lxml'})
browser.open(login_page)
browser.select_form('form[action="/ekonto/login/login_check_password"]')
browser["username"] = username
browser["password"] = password
browser.submit_selected()

if not browser.get_current_page().find(string="Ügyfél: "):
    print("A bejelentkezes nem sikerult.", file=sys.stderr)
    sys.exit(1)

browser.follow_link(link_text=u'Számlakeresés')
assert browser.get_current_page().title.text == u'DÍJNET'

browser.select_form(nr=0)
browser.submit_selected()
page = browser.get_current_page()

links = []

for row in page.select('table.szamla_table')[0].find_all('tr'):
    links.append(url + onclick_parser(row.td['onclick']))

for link in links:
    browser.open(link)
    browser.follow_link(link_text=u'Letöltés')
    page = browser.get_current_page()
    messages = page.find_all('div', class_="xt_link_cell__download")
    link_text = ''

    for message in messages:
        if 'Hiteles számla' in message.text:
            link_text = message.text
    
    download_link = browser.find_link(link_text=link_text)

    data = browser.session.get(browser.absolute_url(download_link['href']))
    header = data.headers['Content-Disposition']
    value, params = cgi.parse_header(header)
    with open(params['filename'], "wb") as f:
        f.write(data.content)
    print(params['filename'])

    return_link = browser.get_current_page().select('a.xt_link__title')
    browser.follow_link(return_link[0])

browser.open(logout_page)
