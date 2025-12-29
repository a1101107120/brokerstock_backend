import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from collections import defaultdict

def generate_fubon_link(number, a, b):
    return f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco0/zco0.djhtm?a={number}&b={b}&BHID={a}"

def generate_fubon_detail_link(a, b, days=1):
    # d=1 is daily, d=5, 10, 20 for historical
    return f"https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm?a={a}&b={b}&c=E&d={days}"

def generate_histock_link(number, bno):
    return f"https://histock.tw/stock/brokertrace.aspx?bno={bno}&no={number}"

def fetch_top_buyers(link, record_type=1):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(link, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching {link}: {e}")
        return [], "", []

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'oMainTable'})
    if not table:
        return [], "", []

    rows = table.find_all('tr')
    try:
        date_text = rows[0].find('div', class_='t11').get_text()
        if '資料日期：' in date_text:
            date = date_text.split('資料日期：')[1].strip()
        else:
            date = datetime.now().strftime("%Y-%m-%d")
            print(f"Warning: '資料日期：' not found in text: {date_text}. Using current date: {date}")
    except (IndexError, AttributeError, ValueError) as e:
        date = datetime.now().strftime("%Y-%m-%d")
        print(f"Error parsing date from table at {link}: {e}. Using current date: {date}")

    def parse_table_side(side_table):
        data_list = []
        rows = side_table.find_all('tr')
        for index, row in enumerate(rows):
            if index < 2:
                continue
            
            script_tag = row.find('td').script
            if script_tag:
                script_content = script_tag.string.strip()
                # GenLink2stk('AS2330','台積電');
                match = re.search(r"GenLink2stk\('([^']+)','([^']+)'\)", script_content)
                if match:
                    codes_raw = match.group(1)
                    name_raw = match.group(2)
                    code = codes_raw[2:6] if codes_raw.startswith('AS') else codes_raw
                    name = f"{code}{name_raw}"
                else:
                    continue
            else:
                continue

            tds = row.find_all('td')
            if len(tds) < 4:
                continue
                
            buy = int(tds[1].text.strip().replace(",", ""))
            sell = int(tds[2].text.strip().replace(",", ""))
            dif = int(tds[3].text.strip().replace(",", ""))

            data_list.append({
                'name': name,
                'code': code,
                'buy': buy,
                'sell': sell,
                'dif': dif,
                'date': date,
                'type': record_type
            })
        return data_list

    buy_side = rows[2].find_all('table')[0]
    sell_side = rows[2].find_all('table')[1]

    buy_data = parse_table_side(buy_side)
    sell_data = parse_table_side(sell_side)

    return buy_data, date, sell_data

def get_merged_data(a, b, broker_name):
    BROKER_CONDITIONS = {
        "港商麥格理": {"buy_threshold": 300, "sell_threshold": -300},
        "default": {"buy_threshold": 60, "sell_threshold": -60},
    }
    
    link = generate_fubon_detail_link(a, b, days=1)
    buy_data, date, sell_data = fetch_top_buyers(link, record_type=1)
    
    thresholds = BROKER_CONDITIONS.get(broker_name, BROKER_CONDITIONS["default"])
    buy_threshold = thresholds["buy_threshold"]
    sell_threshold = thresholds["sell_threshold"]

    filtered_buy = [d for d in buy_data if d['dif'] >= buy_threshold]
    filtered_sell = [d for d in sell_data if d['dif'] <= sell_threshold]
    
    return filtered_buy, date, filtered_sell

def find_previous_workdays_range(date_str, num_workdays):
    if not date_str:
        print("Warning: find_previous_workdays_range received empty date_str.")
        return "Unknown Range"
        
    # Support both YYYYMMDD and YYYY-MM-DD
    if '-' in date_str:
        date_format = "%Y-%m-%d"
    else:
        date_format = "%Y%m%d"
        
    try:
        date = datetime.strptime(date_str, date_format)
    except ValueError as e:
        print(f"Error parsing date {date_str} with format {date_format}: {e}")
        return f"Invalid Date~{date_str}"

    workdays_found = 0
    current_date = date
    while workdays_found < num_workdays:
        current_date -= timedelta(days=1)
        if current_date.weekday() < 5:
            workdays_found += 1
    
    start_date = current_date.strftime(date_format)
    return f"{start_date}~{date_str}"

