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
            print(
                f"Warning: '資料日期：' not found in text: {date_text}. Using current date: {date}")
    except (IndexError, AttributeError, ValueError) as e:
        date = datetime.now().strftime("%Y-%m-%d")
        print(
            f"Error parsing date from table at {link}: {e}. Using current date: {date}")

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
                match = re.search(
                    r"GenLink2stk\('([^']+)','([^']+)'\)", script_content)
                if match:
                    codes_raw = match.group(1)
                    name_raw = match.group(2)
                    code = codes_raw[2:6] if codes_raw.startswith(
                        'AS') else codes_raw
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

    thresholds = BROKER_CONDITIONS.get(
        broker_name, BROKER_CONDITIONS["default"])
    buy_threshold = thresholds["buy_threshold"]
    sell_threshold = thresholds["sell_threshold"]

    filtered_buy = [d for d in buy_data if d['dif'] >= buy_threshold]
    filtered_sell = [d for d in sell_data if d['dif'] <= sell_threshold]

    return filtered_buy, date, filtered_sell


def fetch_fubon_zco0_data(link):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(link, headers=headers, timeout=10)
        response.raise_for_status()
        # The page might be encoded in Big5
        if response.encoding == 'ISO-8859-1':
            response.encoding = 'big5'
    except Exception as e:
        print(f"Error fetching {link}: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract date - usually in a div with class 't11'
    date = datetime.now().strftime("%Y-%m-%d")
    date_div = soup.find('div', class_='t11')
    if date_div:
        date_match = re.search(r"(\d{4}/\d{1,2}/\d{1,2})", date_div.get_text())
        if date_match:
            date = date_match.group(1).replace('/', '-')

    # Find the main table for broker data
    # The structure of zco0.djhtm is a bit different
    # We are looking for the table row that contains the broker's buy/sell for the stock
    # Usually it's in a table with id 'oMainTable' or just the first large table
    table = soup.find('table', {'id': 'oMainTable'})
    if not table:
        return {"buy": 0, "sell": 0, "net": 0, "date": date}

    rows = table.find_all('tr')
    # Row 2 (index 2) usually contains the summarized data for the broker/stock
    if len(rows) > 2:
        tds = rows[2].find_all('td')
        if len(tds) >= 4:
            try:
                buy = int(tds[1].text.strip().replace(",", ""))
                sell = int(tds[2].text.strip().replace(",", ""))
                net = int(tds[3].text.strip().replace(",", ""))
                return {"buy": buy, "sell": sell, "net": net, "date": date}
            except ValueError:
                pass

    return {"buy": 0, "sell": 0, "net": 0, "date": date}


def get_main_force_merged_data(number, a, b):
    link = generate_fubon_link(number, a, b)
    data = fetch_fubon_zco0_data(link)
    return data


def fetch_stock_main_force_data(stock_number, date_str=None):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # Use the specific URL format with date parameters e and f
    link = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a={stock_number}&e={date_str}&f={date_str}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(link, headers=headers, timeout=10)
        response.raise_for_status()
        if response.encoding == 'ISO-8859-1':
            response.encoding = 'big5'
    except Exception as e:
        print(f"Error fetching stock main force {link}: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract date from page if possible, otherwise use passed date
    date = date_str
    date_div = soup.find('div', class_='t11')
    if date_div:
        date_match = re.search(r"(\d{4}/\d{1,2}/\d{1,2})", date_div.get_text())
        if date_match:
            date = date_match.group(1).replace('/', '-')

    # The main table usually has id 'oMainTable'
    table = soup.find('table', {'id': 'oMainTable'})
    if not table:
        # Fallback: find the first table with enough rows
        tables = soup.find_all('table')
        for t in tables:
            if len(t.find_all('tr')) > 10:
                table = t
                break

    if not table:
        return {"buy_list": [], "sell_list": [], "date": date}

    # Find the Buyers and Sellers sub-tables
    # Instead of relying on rows[2], let's find all nested tables and check their headers
    all_tables = table.find_all('table')
    buy_list = []
    sell_list = []

    found_sub_tables = []
    for st in all_tables:
        header_text = st.get_text()
        if "買進" in header_text and "賣出" in header_text and "買賣超" in header_text:
            found_sub_tables.append(st)

    def parse_ranking_table(t):
        items = []
        r = t.find_all('tr')
        for i, row in enumerate(r):
            tds = row.find_all('td')
            # Fubon's zco page usually has 5 columns: Broker, Buy, Sell, Net, Percent
            if len(tds) < 5:
                continue

            # Skip if it's a header row (contains "券商" or "買進")
            if "券商" in tds[0].text or "買進" in tds[1].text:
                continue

            # Broker name usually inside GenLink2bkr script or just text
            name_td = tds[0]
            name = name_td.text.strip()
            script = name_td.find('script')
            if script and script.string:
                m = re.search(
                    r"GenLink2bkr\('([^']+)','([^']+)'\)", script.string)
                if m:
                    name = m.group(2)

            try:
                # Remove commas and handle negative numbers
                buy_val = int(tds[1].text.strip().replace(',', ''))
                sell_val = int(tds[2].text.strip().replace(',', ''))
                net_val = int(tds[3].text.strip().replace(',', ''))
                percent_val = tds[4].text.strip()

                # Basic validation: if all values are 0, it might be an empty row
                if buy_val == 0 and sell_val == 0 and net_val == 0:
                    continue

                items.append({
                    "name": name,
                    "buy": buy_val,
                    "sell": sell_val,
                    "net": net_val,
                    "percent": percent_val
                })
            except (ValueError, IndexError):
                continue
        return items

    if len(found_sub_tables) >= 2:
        buy_list = parse_ranking_table(found_sub_tables[0])
        sell_list = parse_ranking_table(found_sub_tables[1])
    elif len(found_sub_tables) == 1:
        # If only one table found, it might be a different layout
        buy_list = parse_ranking_table(found_sub_tables[0])

    return {
        "buy_list": buy_list,
        "sell_list": sell_list,
        "date": date
    }


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
