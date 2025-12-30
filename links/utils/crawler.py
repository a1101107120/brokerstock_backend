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


def fetch_fubon_zco0_data(link, target_date_str=None):
    if not target_date_str:
        # Default to today in YYYY-MM-DD
        target_date_str = datetime.now().strftime("%Y-%m-%d")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(link, headers=headers, timeout=10)
        response.raise_for_status()
        if response.encoding == 'ISO-8859-1':
            response.encoding = 'big5'
    except Exception as e:
        print(f"Error fetching {link}: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # The structure of zco0.djhtm is often a table where rows are dates or summary
    # We look for a table with id 'oMainTable'
    table = soup.find('table', {'id': 'oMainTable'})
    if not table:
        return {"buy": 0, "sell": 0, "net": 0, "date": target_date_str}

    rows = table.find_all('tr')

    # Target date formats to check (e.g. "2025-12-30" or "2025/12/30")
    target_date_slash = target_date_str.replace('-', '/')

    for row in rows:
        tds = row.find_all('td')
        if len(tds) < 4:
            continue

        # Get text of the first cell (Date)
        date_cell_text = tds[0].get_text().strip()

        # Check if this row contains our target date in any of the common formats
        if target_date_str in date_cell_text or target_date_slash in date_cell_text:
            try:
                # Fubon zco0 typically: Date, Buy, Sell, Net, ...
                buy = int(tds[1].text.strip().replace(",", ""))
                sell = int(tds[2].text.strip().replace(",", ""))
                net = int(tds[3].text.strip().replace(",", ""))
                return {"buy": buy, "sell": sell, "net": net, "date": target_date_str}
            except (ValueError, IndexError) as e:
                print(f"Error parsing zco0 row data: {e}")
                continue

    # Fallback: if no date match found in rows, check if there's a summary row
    # or if we should just return 0s
    return {"buy": 0, "sell": 0, "net": 0, "date": target_date_str}


def get_main_force_merged_data(number, a, b, date_str=None):
    link = generate_fubon_link(number, a, b)
    data = fetch_fubon_zco0_data(link, date_str)
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

    buy_list = []
    sell_list = []
    rows = table.find_all('tr')

    for row in rows:
        tds = row.find_all('td')
        # Check for the flat 10-column layout (5 columns for buy, 5 for sell)
        if len(tds) == 10:
            # Skip rows that are clearly headers or footers
            if "合計" in row.text or "平均" in row.text or "買超券商" in row.text:
                continue

            def parse_broker_td(name_td, buy_td, sell_td, net_td, percent_td):
                name = name_td.text.strip()
                if not name or "券商" in name:
                    return None

                # Try to get name from GenLink2bkr script if available
                script = name_td.find('script')
                if script and script.string:
                    m = re.search(
                        r"GenLink2bkr\('([^']+)','([^']+)'\)", script.string)
                    if m:
                        name = m.group(2)

                try:
                    buy_val = int(buy_td.text.strip().replace(',', ''))
                    sell_val = int(sell_td.text.strip().replace(',', ''))
                    net_val = int(net_td.text.strip().replace(',', ''))
                    percent_val = percent_td.text.strip()

                    if buy_val == 0 and sell_val == 0 and net_val == 0:
                        return None

                    return {
                        "name": name,
                        "buy": buy_val,
                        "sell": sell_val,
                        "net": net_val,
                        "percent": percent_val
                    }
                except (ValueError, IndexError):
                    return None

            # Left side: Buyers
            buy_item = parse_broker_td(tds[0], tds[1], tds[2], tds[3], tds[4])
            if buy_item:
                buy_list.append(buy_item)

            # Right side: Sellers
            sell_item = parse_broker_td(tds[5], tds[6], tds[7], tds[8], tds[9])
            if sell_item:
                sell_list.append(sell_item)

    # Fallback: if flat layout didn't yield results, try looking for nested tables
    if not buy_list and not sell_list:
        all_tables = table.find_all('table')
        found_sub_tables = []
        for st in all_tables:
            header_text = st.get_text()
            if "買進" in header_text and "賣出" in header_text and "買賣超" in header_text:
                found_sub_tables.append(st)

        def parse_nested_table(t):
            items = []
            for r in t.find_all('tr'):
                tds = r.find_all('td')
                if len(tds) < 5:
                    continue

                # Skip header rows
                if "券商" in tds[0].text or "買進" in tds[1].text:
                    continue

                name = tds[0].text.strip()
                script = tds[0].find('script')
                if script and script.string:
                    m = re.search(
                        r"GenLink2bkr\('([^']+)','([^']+)'\)", script.string)
                    if m:
                        name = m.group(2)

                try:
                    buy_v = int(tds[1].text.strip().replace(',', ''))
                    sell_v = int(tds[2].text.strip().replace(',', ''))
                    net_v = int(tds[3].text.strip().replace(',', ''))
                    if buy_v == 0 and sell_v == 0 and net_v == 0:
                        continue
                    items.append({
                        "name": name,
                        "buy": buy_v,
                        "sell": sell_v,
                        "net": net_v,
                        "percent": tds[4].text.strip()
                    })
                except:
                    continue
            return items

        if len(found_sub_tables) >= 2:
            buy_list = parse_nested_table(found_sub_tables[0])
            sell_list = parse_nested_table(found_sub_tables[1])
        elif len(found_sub_tables) == 1:
            buy_list = parse_nested_table(found_sub_tables[0])

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
