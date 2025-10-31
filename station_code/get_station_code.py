import requests
from requests import status_codes
from bs4 import BeautifulSoup
import re
import os
import sys
import json
import datetime
from datetime import timezone,timedelta
import csv
import pprint
import time
import codecs
import hashlib
import pathlib


def get_last_update():
    base = pathlib.Path(os.getcwd())
    json_file_path = base.joinpath("lastupdate.json")
    json_open = codecs.open(json_file_path, 'r', 'utf-8')
    json_load = json.load(json_open)

    return json_load['lastupdate']


def save_last_update(last_update):
    base = pathlib.Path(os.getcwd())
    json_file_path = base.joinpath("lastupdate.json")
    with codecs.open(json_file_path, 'w', 'utf-8') as json_open:

        create_data = {'lastupdate': last_update}
        json.dump(create_data, json_open, indent=4, ensure_ascii=False)

###
def create_station_code_csv_file():

    tokyo_tz = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.now(tokyo_tz)

    filename = f'station_code_{str(dt.year)}{str(dt.month)}{str(dt.day)}{str(dt.hour)}{str(dt.minute)}{str(dt.second)}.csv'

    base = pathlib.Path(os.getcwd())
    file_path = base.joinpath(filename)

    return file_path


###

def remove_duplicates(lst):

    result = []
    for line in lst:
        if line not in result:
            result.append(line)
    
    return result

###

def do_get_region_and_line():

    ret_region_and_line_list = []

    url = f'https://ja.ysrl.org/atc/station-code.html'
    res = requests.get(url)

    if res.status_code != 200:
        print("HTTP STATUS : ", res.status_code, " --> ", status_codes._codes[res.status_code][0]  )
        return

    soup = BeautifulSoup(res.text, 'html.parser')

    tables = soup.find_all("table", {"class":"yow-table-s"})

    for table in tables:

        # 1 ライン抜き出し
        rows = table.find_all("tr")

        for row in rows:

            for a_tags in row.find_all('a', href=True):

                for a_tag in a_tags:

                    # href から regionとlineを抽出する
                    number = re.findall(r'\d+', a_tags['href'])
                    # region と line のコードを配列に追加
                    ret_region_and_line_list.append(number)
                    return ret_region_and_line_list


    return ret_region_and_line_list


#####
def do_scraping(region, line, csv_writer):

    url = f'https://ja.ysrl.org/atc/code.php?region={region}&line={line}'
    res = requests.get(url)

    if res.status_code != 200:
        print("HTTP STATUS : ", res.status_code, " --> ", status_codes._codes[res.status_code][0]  )
        return

    time.sleep(1)  # 1秒間スリープ
    # レスポンスの HTML から BeautifulSoup オブジェクトを作る
    soup = BeautifulSoup(res.text, 'html.parser')

    # テーブルを指定(テーブルが複数あることを考慮)
    tables = soup.find_all("table", {"class":"yow-table"})

    for table in tables:

        # 1 ライン抜き出し
        rows = table.find_all("tr")

        #3桁の数字-3桁の数字
        regex = r'([0-9]{3}-[0-9]{3})'

        regex2 = '(線区-駅順)'    

        #with open(create_station_code_csv_file(),'a', encoding='sjis', newline='') as csv_file :

            #writer = csv.writer(csv_file)

        all_array = []

        for row in rows:

            row_array = []
            row_array.append(region)

            for cell in row.find_all(['td', 'th']):

                if bool(re.match(regex, cell.get_text())):
                    result = cell.get_text().split("-")

                    row_array.append(result[0])
                    row_array.append(result[1])

                elif bool(re.match(regex2, cell.get_text())):
                    row_array = []
                    break
                else:
                    #print(cell.get_text())
                    if len(row_array) == 1:
                        row_array.append('')
                        row_array.append('')
                    else:
                        row_array.append(cell.get_text())

            #print(row_array)
            if len(row_array) > 0:
                all_array.append(row_array)

        #print(all_array)
        csv_writer.writerows(all_array)


def check_update_data(lastupdate):

    url = f'https://ja.ysrl.org/atc/station-code.html'
    res = requests.get(url)

    if res.status_code != 200:
        print("HTTP STATUS : ", res.status_code, " --> ", status_codes._codes[res.status_code][0]  )
        return ""

    # レスポンスの HTML から BeautifulSoup オブジェクトを作る
    soup = BeautifulSoup(res.content.decode("utf-8", "ignore"), 'html.parser')
    # 最終更新日の文字列を取得
    get_last_update = soup.find(class_="atc-report-updated").get_text()    

    if lastupdate == get_last_update:
        return ""
    else:
        print('更新あり : ', get_last_update)

    return get_last_update

def main():

    last_update = check_update_data(get_last_update())

    if last_update == "":
        print('更新なし : 処理終了')
        return    

    print("更新データがあります。スクレイピングを実行します")
    print("1: はい\r\n2: いいえ")
    m = 1
    if m == 2:
        print("処理を終了します")
        return

    ret_region_and_line_list = do_get_region_and_line()

    # 重複削除
    rails_list = remove_duplicates(ret_region_and_line_list)
    print(len(rails_list))

    csv_file_path = create_station_code_csv_file()

    print("-=-=-=-=-=-=-=- 実行中 -=-=-=-=-=-=-=-")
    with open(csv_file_path,'a', encoding='utf8', newline='') as csv_file :

        csv_writer = csv.writer(csv_file)

        for ret_region_and_line in rails_list:
            do_scraping(ret_region_and_line[0], ret_region_and_line[1], csv_writer)

    print("-=-=-=-=-=-=-=- 実行完了 -=-=-=-=-=-=-=-")

    # 最終更新日をファイルに保存する
    save_last_update(last_update)

    # ファイルハッシュ計算
    with open(csv_file_path, 'rb') as file:
        # ファイルを読み取る
        fileData = file.read()
        # sha256
        hash_sha256 = hashlib.sha256(fileData).hexdigest()
        print('file hash(sha256)  : ' + hash_sha256.upper())


if __name__ == '__main__':

    main()





