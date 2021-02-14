#!/usr/bin/env python3
# vim: set fileencoding=utf-8 :

import re
import cgi
import sys
import configparser
import mechanicalsoup

from pathlib import Path
from typing import Optional
from ui import UserInterface, ConsoleUserInterface

INIFILE = "dijnet.ini"
INITEMPLATE = "dijnet-template.ini"
LOGIN = '/ekonto/control/main'
LOGOUT = '/ekonto/control/logout'
CURRENT_BILL = '/ekonto/control/szamla_select?vfw_coll=szamla_list&vfw_rowid=${szamla_id}&exp=K'


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
    ui.show_message(f"Az {ini_file} összeállításához szükség lesz a dijnet.hu belépési adatokra.")
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


def set_hidden_config(config):
    config.set('global', 'login', LOGIN)
    config.set('global', 'logout', LOGOUT)
    config.set('global', 'current_bill', CURRENT_BILL)
    return config


def get_download_links(browser, get_all=False):
    browser.follow_link(link_text=u'Letöltés')
    page = browser.get_current_page()
    download_original = page.find_all('a', class_="xt_link__download")
    filtered = list(filter(lambda download_page: 'Acrobat Reader' not in download_page.text,
                           download_original))

    if not get_all:
        filtered = list(filter(lambda current: 'Hiteles számla' in current.text,
                               download_original))
        if filtered == []:
            filtered = list(filter(lambda current: '\xa0Terhelési összesítő nyomtatható verziója (PDF)' == current.text,
                                   download_original))
    
    return filtered


def download_contents(browser, get_all, file_root):
    filename = Path()
    for download_link in get_download_links(browser, get_all):

        data = browser.session.get(browser.absolute_url(download_link['href']))
        header = data.headers['Content-Disposition']
        _, params = cgi.parse_header(header)
        
        filename = Path(file_root, params['filename'])

        if not filename.exists():
            filename.parent.mkdir(parents=True, exist_ok=True)
            with open(filename, "wb") as f:
                f.write(data.content)

    return filename


def get_app_directory():
    script = Path(sys.argv[0])
    return script.parent


def main(ui: UserInterface):
    config = read_config(INIFILE, INITEMPLATE, get_app_directory(), ui)
    config = set_hidden_config(config)

    username = config.get('global', 'username')
    password = config.get('global', 'password')
    url = config.get('global', 'url')
    login_page = url + config.get('global', 'login')
    logout_page = url + config.get('global', 'logout')
    order_by = config.get('global', 'order_by').split('|')
    get_all = config.getboolean('global', 'download_all')
    if get_all and \
       'SzámlaszámBizonylatszám' not in order_by:
        order_by.append('SzámlaszámBizonylatszám')
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

    order_by_list = list(filter(lambda value: value is not None, order_by_list))
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

    for index, link in enumerate(links):
        browser.open(link)
        filename = download_contents(browser, get_all, order_by_path[index])
        process_percent = (index + 1) / len(links)
        process_string = f'Letöltés {"{:.1%}".format(process_percent)}'
        process_in_bar = int(process_percent * 10)

        ui.show_message("{0:15} {1}{2:10}{3} {4}".format(process_string,
                                                    "|",
                                                    ui.progress_bar(process_in_bar),
                                                    "|",
                                                    filename if not get_all else filename.parent),
                        True if index < len(links) else False)

        return_link = browser.find_link(link_text='\xa0vissza a listához')
        browser.follow_link(return_link)

    browser.open(logout_page)


if __name__ == "__main__":
    main(ConsoleUserInterface())
