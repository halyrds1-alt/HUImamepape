#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Psycho Search Bot v4.2 — Исправленная админка
"""

import telebot
from telebot import types
import requests
import sqlite3
import os
import time
import re
import hashlib
from datetime import datetime
from threading import Thread

# ========== КОНФИГ ==========
BOT_TOKEN = "8648067466:AAGAFikXJFUH3nlLMYd-O5B04BWSHBAI2kI"
ADMIN_IDS = [7811061945, 8679197041, 6747528307]
OWNER_USERNAME = "@runet3"

SEARCH_URL = "http://2.27.15.63:3000/search"
API_KEY = "9834912966"

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "psycho_bot.db")
BANNERS_PATH = os.path.dirname(os.path.abspath(__file__))

# ========== БД ==========
def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        reg_date TEXT,
        last_active TEXT,
        searches INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def add_user(uid, username, first_name):
    conn = sqlite3.connect(DB_PATH, timeout=20)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?,?,?,0)",
                 (uid, username or '', first_name or '', datetime.now().isoformat(), datetime.now().isoformat()))
    else:
        c.execute("UPDATE users SET last_active=? WHERE user_id=?", (datetime.now().isoformat(), uid))
    conn.commit()
    conn.close()

def count_search(uid):
    conn = sqlite3.connect(DB_PATH, timeout=20)
    c = conn.cursor()
    c.execute("UPDATE users SET searches=searches+1 WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()

def get_user_searches(uid):
    conn = sqlite3.connect(DB_PATH, timeout=20)
    c = conn.cursor()
    c.execute("SELECT searches FROM users WHERE user_id=?", (uid,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def all_users():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    u = c.fetchall()
    conn.close()
    return u

def bot_stats():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), COALESCE(SUM(searches),0) FROM users")
    total, searches = c.fetchone()
    conn.close()
    return total or 0, searches or 0

# ========== УМНОЕ ОПРЕДЕЛЕНИЕ ==========
def detect_query_type(text):
    text = text.strip()
    
    if text.startswith('/car '):
        return 'car', text[5:].strip()
    if text.startswith('/snils '):
        return 'snils', text[7:].strip()
    if text.startswith('/inn '):
        return 'inn', text[5:].strip()
    
    digits = re.sub(r'\D', '', text)
    
    if len(digits) >= 10 and len(digits) <= 12:
        return 'phone', digits
    
    if '@' in text:
        return 'email', text
    
    if re.match(r'^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$', text.upper()):
        return 'car', text.upper()
    
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', text):
        return 'ip', text
    
    words = text.split()
    if len(words) >= 2:
        return 'fio', text
    
    return 'unknown', text

# ========== ПОИСК ==========
def search_api(query):
    try:
        url = f"{SEARCH_URL}?key={API_KEY}&quest={query}"
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if 'error' not in data:
                return data
    except Exception as e:
        print(f"[API] Ошибка: {e}")
    return None

# ========== ПАРСИНГ ==========
def parse_results(data):
    if not data:
        return None
    
    phones, fios, names, surnames, patronymics = [], [], [], [], []
    emails, addresses, cities = [], [], []
    passports, birthdates, genders = [], [], []
    logins, passwords, nicknames = [], [], []
    vk_ids, ok_ids, tg_ids, twitter_names = [], [], [], []
    ip_addresses, countries = [], []
    bank_cards, sber_ids = [], []
    car_plates, sources = [], []
    
    phone_info = data.get('phone_info', {})
    operator = phone_info.get('operator', '')
    region = phone_info.get('region', '')
    
    results = data.get('results', [])
    
    for item in results:
        phone = item.get('📞Телефон') or item.get('📞Телефон 2') or item.get('📞Телефон 3') or item.get('📞Телефон 4')
        if phone and phone != 'None':
            phones.append(str(phone))
        
        fio = item.get('👤ФИО') or item.get('👤Полное имя')
        if fio:
            fios.append(str(fio))
        
        name = item.get('👤Имя')
        if name and name != 'None':
            names.append(str(name))
        
        surname = item.get('👤Фамилия')
        if surname and surname != 'None':
            surnames.append(str(surname))
        
        patr = item.get('👤Отчество')
        if patr and patr != 'None':
            patronymics.append(str(patr))
        
        email = item.get('✉️Почта') or item.get('✉️Почта 2')
        if email and email != 'None' and '@' in str(email):
            emails.append(str(email))
        
        address = item.get('📍Адрес') or item.get('address_reg') or item.get('address_actual')
        if address and address != 'None' and address != 'NULL':
            addresses.append(str(address))
        
        city = item.get('🏙️Город')
        if city and city != 'None':
            cities.append(str(city))
        
        passport = item.get('passport_short') or item.get('passport_full') or item.get('passport_info')
        if passport:
            passports.append(str(passport))
        
        bdate = item.get('🎂Дата рождения') or item.get('birthday') or item.get('bdate')
        if bdate and bdate != 'None' and bdate != 'NULL':
            birthdates.append(str(bdate))
        
        gender = item.get('🚻Пол')
        if gender and gender != 'None' and gender != 'NULL':
            genders.append(str(gender))
        
        login = item.get('👤Логин')
        if login:
            logins.append(str(login))
        
        pwd = item.get('🗝️Хэш пароль') or item.get('🔑Пароль') or item.get('hash_passwd')
        if pwd:
            passwords.append(str(pwd)[:40] + '...')
        
        nick = item.get('🔸Никнейм') or item.get('nickname')
        if nick and nick != 'None':
            nicknames.append(str(nick))
        
        vk = item.get('🪪Ид вк')
        if vk:
            vk_ids.append(str(vk))
        
        ok = item.get('ok_id')
        if ok and ok != '0':
            ok_ids.append(str(ok))
        
        tg = item.get('tg_id')
        if tg:
            tg_ids.append(str(tg))
        
        tw = item.get('screen_name')
        if tw:
            twitter_names.append(str(tw))
        
        ip = item.get('🌐IP-адрес') or item.get('last_ip')
        if ip and ip != 'None':
            ip_addresses.append(str(ip))
        
        country = item.get('🌍Страна')
        if country and country != 'None' and country != 'NULL':
            countries.append(str(country))
        
        card = item.get('💳Номер карты') or item.get('💳 Банковская карта') or item.get('💳Id карты')
        if card:
            bank_cards.append(str(card))
        
        sber = item.get('💳Сбер ID')
        if sber:
            sber_ids.append(str(sber))
        
        car = item.get('car_plate')
        if car:
            car_plates.append(str(car))
        
        source = item.get('🏫Источник') or item.get('site')
        if source:
            sources.append(str(source))
    
    def unique(lst):
        seen = set()
        return [x for x in lst if x and x != 'None' and x != 'NULL' and not (x in seen or seen.add(x))]
    
    return {
        'operator': operator, 'region': region,
        'phones': unique(phones), 'fios': unique(fios),
        'names': unique(names), 'surnames': unique(surnames),
        'patronymics': unique(patronymics), 'emails': unique(emails),
        'addresses': unique(addresses), 'cities': unique(cities),
        'passports': unique(passports), 'birthdates': unique(birthdates),
        'genders': unique(genders), 'logins': unique(logins),
        'passwords': unique(passwords), 'nicknames': unique(nicknames),
        'vk_ids': unique(vk_ids), 'ok_ids': unique(ok_ids),
        'tg_ids': unique(tg_ids), 'twitter': unique(twitter_names),
        'ips': unique(ip_addresses), 'countries': unique(countries),
        'cards': unique(bank_cards), 'sber_ids': unique(sber_ids),
        'cars': unique(car_plates), 'sources': unique(sources)
    }

def has_data(p):
    if not p: return False
    return any([p['phones'], p['fios'], p['emails'], p['addresses'],
               p['passports'], p['birthdates'], p['logins'], p['nicknames'],
               p['vk_ids'], p['ips'], p['cards'], p['cars']])

def count_all(p):
    if not p: return 0
    return sum([len(p[k]) for k in ['phones','fios','names','surnames','patronymics',
               'emails','addresses','cities','passports','birthdates','genders',
               'logins','passwords','nicknames','vk_ids','ok_ids','tg_ids','twitter',
               'ips','countries','cards','sber_ids','cars']])

# ========== HTML ==========
def build_html(parsed, query, qtype):
    total = count_all(parsed)
    type_names = {'phone': 'Телефон', 'fio': 'ФИО', 'email': 'Email', 'car': 'Авто', 'snils': 'СНИЛС', 'inn': 'ИНН', 'ip': 'IP'}
    type_name = type_names.get(qtype, '')
    
    html = f'''<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Psycho Search — {query[:30]}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a0f;color:#c0c0c0;font-family:'Segoe UI',system-ui,sans-serif;padding:24px}}
.cont{{max-width:960px;margin:0 auto;background:#0d0d14;border:1px solid #1a1a24;border-radius:16px;padding:28px}}
.head{{text-align:center;padding:20px 0 24px;border-bottom:2px solid #1a0000;margin-bottom:24px}}
.logo{{font-size:32px;font-weight:900;letter-spacing:-1px;background:linear-gradient(135deg,#8b0000,#cc0000);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.qinfo{{display:flex;justify-content:center;gap:12px;margin-top:12px;flex-wrap:wrap}}
.qtag{{background:#1a0000;color:#cc0000;padding:4px 14px;border-radius:16px;font-size:12px;font-weight:600}}
.qval{{color:#888;font-size:14px;font-family:'SF Mono',monospace}}
.stats{{display:flex;justify-content:center;gap:16px;margin:20px 0}}
.stat{{background:#0f0f18;border:1px solid #1a1a24;border-radius:12px;padding:14px 22px;text-align:center}}
.snum{{font-size:30px;font-weight:800;color:#cc0000}}
.stxt{{font-size:10px;color:#666;text-transform:uppercase;letter-spacing:2px;margin-top:4px}}
.block{{background:#0f0f18;border:1px solid #1a1a24;border-radius:12px;padding:14px;margin-bottom:10px}}
.btitle{{font-size:13px;font-weight:700;color:#cc0000;margin-bottom:10px;padding-left:10px;border-left:3px solid #8b0000;text-transform:uppercase;letter-spacing:1px}}
.row{{display:flex;padding:5px 0;border-bottom:1px solid #14141c}}
.lbl{{width:100px;color:#666;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;flex-shrink:0}}
.val{{flex:1;color:#ccc;font-size:12px;word-break:break-all;font-family:'SF Mono',monospace}}
.tags{{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px}}
.tag{{background:#1a0000;color:#cc0000;padding:2px 10px;border-radius:12px;font-size:10px}}
.foot{{text-align:center;margin-top:20px;padding-top:14px;border-top:1px solid #1a1a24;color:#444;font-size:10px;letter-spacing:1px}}
</style></head>
<body>
<div class="cont">
<div class="head"><div class="logo">Psycho Search</div>
<div class="qinfo">{'<span class="qtag">'+type_name+'</span>' if type_name else ''}<span class="qval">{query[:60]}</span></div></div>
<div class="stats"><div class="stat"><div class="snum">{total}</div><div class="stxt">найдено</div></div></div>'''
    
    if parsed['operator'] or parsed['region']:
        html += '<div class="block"><div class="btitle">Оператор / Регион</div>'
        if parsed['operator']:
            html += f'<div class="row"><span class="lbl">Оператор</span><span class="val">{parsed["operator"]}</span></div>'
        if parsed['region']:
            html += f'<div class="row"><span class="lbl">Регион</span><span class="val">{parsed["region"]}</span></div>'
        html += '</div>'
    
    sections = [
        ('Телефоны', 'phones'), ('ФИО', 'fios'), ('Имена', 'names'),
        ('Фамилии', 'surnames'), ('Отчества', 'patronymics'),
        ('Email', 'emails'), ('Адреса', 'addresses'), ('Города', 'cities'),
        ('Паспорта', 'passports'), ('Даты рождения', 'birthdates'),
        ('Пол', 'genders'), ('Логины', 'logins'), ('Пароли', 'passwords'),
        ('Никнеймы', 'nicknames'), ('VK ID', 'vk_ids'), ('OK ID', 'ok_ids'),
        ('TG ID', 'tg_ids'), ('Twitter', 'twitter'), ('IP', 'ips'),
        ('Страны', 'countries'), ('Карты', 'cards'), ('Сбер ID', 'sber_ids'),
        ('Авто', 'cars')
    ]
    
    for title, key in sections:
        if parsed[key]:
            html += f'<div class="block"><div class="btitle">{title}</div>'
            for item in parsed[key][:15]:
                html += f'<div class="row"><span class="lbl">{title}</span><span class="val">{item}</span></div>'
            html += '</div>'
    
    if parsed['sources']:
        html += '<div class="block"><div class="btitle">Источники</div><div class="tags">'
        for s in parsed['sources'][:30]:
            html += f'<span class="tag">{s[:60]}</span>'
        html += '</div></div>'
    
    html += f'<div class="foot">Psycho Search · {datetime.now().strftime("%d.%m.%Y %H:%M")}</div></div></body></html>'
    return html

# ========== АНИМАЦИЯ ПОИСКА ==========
def search_animation(msg, uid):
    dots = ['', '.', '..', '...']
    for i in range(4):
        try:
            bot.edit_message_text(f"Поиск{dots[i]}", uid, msg.message_id)
            time.sleep(0.5)
        except:
            pass

# ========== ОСНОВНАЯ ЛОГИКА ==========
def process_search(m, query, uid):
    msg = bot.send_message(uid, "Поиск")
    
    anim = Thread(target=search_animation, args=(msg, uid))
    anim.start()
    
    qtype, formatted_query = detect_query_type(query)
    data = search_api(formatted_query)
    parsed = parse_results(data)
    
    anim.join()
    
    try:
        bot.delete_message(uid, msg.message_id)
    except:
        pass
    
    if data and has_data(parsed):
        count_search(uid)
        total = count_all(parsed)
        
        html = build_html(parsed, formatted_query, qtype)
        
        filename = f"Psycho_{hashlib.md5(query.encode()).hexdigest()[:8]}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        with open(filename, 'rb') as f:
            bot.send_document(uid, f, caption=f"Запрос: {query[:50]}\nНайдено: {total}")
        
        os.remove(filename)
        
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Новый поиск", callback_data="search"))
        kb.add(types.InlineKeyboardButton("Меню", callback_data="menu"))
        bot.send_message(uid, "Готово", reply_markup=kb)
    else:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Попробовать снова", callback_data="search"))
        kb.add(types.InlineKeyboardButton("Меню", callback_data="menu"))
        bot.send_message(uid, f"По запросу «{query[:50]}» ничего не найдено", reply_markup=kb)

# ========== БАННЕРЫ ==========
def get_banner(name):
    path = os.path.join(BANNERS_PATH, name)
    if os.path.exists(path):
        return open(path, 'rb')
    return None

# ========== БОТ ==========
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = m.from_user.id
    add_user(uid, m.from_user.username or '', m.from_user.first_name or '')
    
    banner = get_banner('menu.jpg')
    caption = "Psycho Search\n\nДобро пожаловать в Psycho Search — бесплатный бот для поиска информации.\n\nВыберите действие в меню ниже:"
    
    if banner:
        bot.send_photo(uid, banner, caption=caption, reply_markup=main_menu(uid))
        banner.close()
    else:
        bot.send_message(uid, caption, reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: True)
def auto_search(m):
    uid = m.from_user.id
    text = m.text.strip()
    
    if text.startswith('/'):
        return
    
    qtype, _ = detect_query_type(text)
    
    if qtype in ['phone', 'fio', 'email', 'car', 'snils', 'inn', 'ip']:
        process_search(m, text, uid)

def main_menu(uid):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("Поиск", callback_data="search"))
    kb.add(types.InlineKeyboardButton("Профиль", callback_data="profile"))
    kb.add(types.InlineKeyboardButton("Поддержка", callback_data="support"))
    if uid in ADMIN_IDS:
        kb.add(types.InlineKeyboardButton("Админ", callback_data="admin"))
    return kb

@bot.callback_query_handler(func=lambda c: c.data == "menu")
def menu_cb(call):
    uid = call.from_user.id
    
    banner = get_banner('menu.jpg')
    caption = "Psycho Search\n\nДобро пожаловать в Psycho Search — бесплатный бот для поиска информации.\n\nВыберите действие в меню ниже:"
    
    if banner:
        bot.send_photo(uid, banner, caption=caption, reply_markup=main_menu(uid))
        banner.close()
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
    else:
        try:
            bot.edit_message_text(caption, uid, call.message.message_id, reply_markup=main_menu(uid))
        except:
            bot.send_message(uid, caption, reply_markup=main_menu(uid))

@bot.callback_query_handler(func=lambda c: c.data == "search")
def search_cb(call):
    uid = call.from_user.id
    
    text = """<b>Введите данные для поиска:</b>

<b>Личность:</b>
<code>Иванов Иван Иванович</code> — ФИО

<b>Контакты:</b>
<code>79991234567</code> — номер телефона
<code>example@mail.ru</code> — email

<b>Транспорт:</b>
<code>/car А123БВ177</code> — автомобиль

<b>Документы:</b>
<code>/snils snils12345678901</code> — СНИЛС
<code>/inn inn123456789012</code> — ИНН

Можно просто отправить номер или ФИО — бот сам определит тип"""
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Назад", callback_data="menu"))
    
    try:
        bot.edit_message_text(text, uid, call.message.message_id, parse_mode='HTML', reply_markup=kb)
    except:
        bot.send_message(uid, text, parse_mode='HTML', reply_markup=kb)
    
    bot.register_next_step_handler_by_chat_id(uid, lambda m: process_search(m, m.text.strip(), uid))

@bot.callback_query_handler(func=lambda c: c.data == "profile")
def profile_cb(call):
    uid = call.from_user.id
    searches = get_user_searches(uid)
    
    banner = get_banner('profile.jpg')
    caption = f"<b>Профиль</b>\n\nID: <code>{uid}</code>\nПоисков: <b>{searches}</b>\nВладелец: {OWNER_USERNAME}"
    
    if banner:
        bot.send_photo(uid, banner, caption=caption, parse_mode='HTML')
        banner.close()
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
        
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Назад", callback_data="menu"))
        bot.send_message(uid, "Меню", reply_markup=kb)
    else:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Назад", callback_data="menu"))
        try:
            bot.edit_message_text(caption, uid, call.message.message_id, parse_mode='HTML', reply_markup=kb)
        except:
            bot.send_message(uid, caption, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "support")
def support_cb(call):
    uid = call.from_user.id
    
    banner = get_banner('help.jpg')
    caption = f"<b>Поддержка</b>\n\nПо всем вопросам: {OWNER_USERNAME}"
    
    if banner:
        bot.send_photo(uid, banner, caption=caption, parse_mode='HTML')
        banner.close()
        try:
            bot.delete_message(uid, call.message.message_id)
        except:
            pass
        
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Назад", callback_data="menu"))
        bot.send_message(uid, "Меню", reply_markup=kb)
    else:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Назад", callback_data="menu"))
        try:
            bot.edit_message_text(caption, uid, call.message.message_id, parse_mode='HTML', reply_markup=kb)
        except:
            bot.send_message(uid, caption, parse_mode='HTML', reply_markup=kb)

# ========== АДМИН ==========
@bot.callback_query_handler(func=lambda c: c.data == "admin")
def admin_cb(call):
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "Доступ запрещён", True)
        return
    
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton("Статистика", callback_data="adm_stats"))
    kb.add(types.InlineKeyboardButton("Рассылка", callback_data="adm_send"))
    kb.add(types.InlineKeyboardButton("Назад", callback_data="menu"))
    
    try:
        bot.edit_message_text("<b>Админ-панель</b>", call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, "<b>Админ-панель</b>", parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "adm_stats")
def adm_stats_cb(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    total, searches = bot_stats()
    text = f"<b>Статистика</b>\n\nПользователей: <b>{total}</b>\nПоисков: <b>{searches}</b>"
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Назад", callback_data="admin"))
    
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "adm_send")
def adm_send_cb(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    try:
        bot.edit_message_text("Введите текст рассылки:", call.message.chat.id, call.message.message_id)
    except:
        bot.send_message(call.message.chat.id, "Введите текст рассылки:")
    
    bot.register_next_step_handler(call.message, do_broadcast)

def do_broadcast(m):
    if m.from_user.id not in ADMIN_IDS:
        return
    
    users = all_users()
    ok = 0
    for u in users:
        try:
            bot.send_message(u[0], m.text)
            ok += 1
        except:
            pass
        time.sleep(0.05)
    
    bot.send_message(m.chat.id, f"Отправлено: {ok}/{len(users)}")

if __name__ == "__main__":
    init_db()
    print("Psycho Search v4.2 запущен")
    print(f"Админы: {ADMIN_IDS}")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(10)
