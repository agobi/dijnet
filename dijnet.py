#!/usr/bin/env python3
# vim: set fileencoding=utf-8 :

import configparser
import cgi
import sys
import os
import re
from pathlib import Path
from typing import Optional

import mechanicalsoup

from ui import UserInterface, ConsoleUserInterface

INIFILE = "dijnet.ini"
INITEMPLATE = "dijnet-template.ini"


def onclick_parser(onclick):
    link_start_index = onclick.find('\'') + 1
    onclick_link = onclick[link_start_index:-2]
    return onclick_link


def read_config(ini_file_name: str, template_file_name: str, app_directory: str, ui: UserInterface) \
        -> Optional[configparser.ConfigParser]:

    ini_file = Path(app_directory, ini_file_name)
    template_file = Path(app_directory, template_file_name)

    if ini_file.exists():
        config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        config.read(ini_file, encoding="UTF-8")
        return config

    ui.show_message(f"Nincs még {ini_file}, létrehozunk egyet")
    if not template_file.exists():
        ui.show_error(f"Nem található template ({template_file})")
        return None

    config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    config.read(template_file)
    ui.show_message(f"Az {ini_file} összeálltásához szükség lesz a dijnet.hu belépési adatokra.")
    config.set("global", "username", ui.ask("Username: "))
    config.set("global", "password", ui.ask("Password: "))

    ui.show_message(f"Megadhatja hogy a program hova mentse a számláit. (Pl.: C:\\, /home) " +
                    "Ha nem ad meg semmit a számlák a program mappájába lesznek mentve. " +
                    "A 'dijnet_szamlak' mappát a program mindnen esetben létrehozza.")
    config.set("global", "save_as", ui.ask("Mentés helye: "))
    
    ui.show_message(f"Megadhatja hogy a program hogyan rendezze számláit. " +
                    "A dijnet számlakeresés oldalán található táblázat oszlopneveit " +
                    "használhatja '|' karakterrel elválasztva egymástól. " +
                    "(Pl.: Számlakibocsátói azonosító|Állapot)")
    config.set('global', 'order_by', ui.ask("Rendezés szempotja: "))

    with open(ini_file, "w", encoding="utf-8") as f:
        config.write(f)
    return config


def get_app_directory():
    script = Path(sys.argv[0])
    return script.parent


def main(ui: UserInterface):
    config = read_config(INIFILE, INITEMPLATE, get_app_directory(), ui)

    username = config.get('global', 'username')
    password = config.get('global', 'password')
    url = config.get('global', 'url')
    login_page = url + config.get('global', 'login')
    logout_page = url + config.get('global', 'logout')
    order_by = config.get('global', 'order_by').split('|')
    root_folder = config.get('global', 'save_as')

    browser = mechanicalsoup.StatefulBrowser(soup_config={'features': 'lxml'})
    browser.open(login_page)
    browser.select_form('form[action="/ekonto/login/login_check_password"]')
    browser["username"] = username
    browser["password"] = password
    browser.submit_selected()

    if not browser.get_current_page().find(string="Ügyfél: "):
        ui.show_error("A bejelentkezés nem sikerült.")
        return

    browser.follow_link(link_text=u'Számlakeresés')
    assert browser.get_current_page().title.text == u'DÍJNET'

    browser.select_form(nr=0)
    browser.submit_selected()
    page = browser.get_current_page()
    szamla_table = page.select('table.szamla_table')[0]

    order_by_list = []

    for t_index, t_head in enumerate(szamla_table.find_all('th')):
        column_name = t_head.get_text(strip=True)
        if column_name in order_by:
            order_by_index = order_by.index(column_name)
            order_by_list.insert(order_by_index, t_index)

    order_by_list = list(filter(None, order_by_list)) 
    links = []
    order_by_path = []

    for row_index, row in enumerate(szamla_table.find_all('tr')):
        save_path = ['dijnet_szamlak']
        for item in order_by_list:
            path_text = row.contents[item].get_text(strip=True)
            clean_path = re.sub(r'[\\/\:*"<>\|\.%\$\^&£]', '_', path_text)
            save_path.append(clean_path)
        
        order_by_path.append(Path(root_folder, *save_path))
        
        bill_page = config.get('global', 'current_bill', vars={'szamla_id': row_index})
        links.append(url + bill_page)

    ui.show_message(f'Összesen {len(links)} db számla van...')
    
    for link_index, link in enumerate(links):
        browser.open(link)
        browser.follow_link(link_text=u'Letöltés')
        page = browser.get_current_page()
        messages = page.find_all('div', class_="xt_link_cell__download")
        link_text = ''

        for message in messages:
            if 'Hiteles számla' in message.text:
                link_text = message.text

        if link_text == '':
            link_text = '\xa0Terhelési összesítő nyomtatható verziója (PDF)'

        download_link = browser.find_link(link_text=link_text)

        data = browser.session.get(browser.absolute_url(download_link['href']))
        header = data.headers['Content-Disposition']
        value, params = cgi.parse_header(header)

        if not os.path.exists(Path(order_by_path[link_index], params['filename'])):
            if not os.path.exists(Path(order_by_path[link_index])):
                os.makedirs(Path(order_by_path[link_index]))
            with open(Path(order_by_path[link_index], params['filename']), "wb") as f:
                f.write(data.content)

        process_percent = (link_index + 1) / len(links)
        process_string = f'Letöltés {"{:.1%}".format(process_percent)}'
        process_in_bar = int(process_percent * 10)

        save_string = Path(order_by_path[link_index], params['filename'])

        ui.show_message("{0:15} {1}{2:10}{3} {4}".format(process_string,
                                                      "|",
                                                      ui.progress_bar(process_in_bar),
                                                      "|",
                                                      save_string))
        
        return_link = browser.get_current_page().select('a.xt_link__title')
        browser.follow_link(return_link[0])

    browser.open(logout_page)


if __name__ == "__main__":
    main(ConsoleUserInterface())
