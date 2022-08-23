import json
import re
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import collections
collections.Callable = collections.abc.Callable

import pymysql
import pandas as pd

def to_json(dic, file_name):
    with open(file_name, 'w', encoding = 'UTF8') as f:
        json.dump(dic, f, ensure_ascii=False, indent = '\t')
        
def cleaning_data(string):
    regexed_str = re.sub("[\n]+", " ", string)
    regexed_str = re.sub("[\t]+", " ", string)
    return_string = regexed_str.replace("\n", " ")
    return return_string.strip()

def table_parser(contents, data, std, title):
    for contents_idx in range(0, len(contents), len(data.find_all("th"))):
        sub_dict = {}
        for th in range(len(data.find_all("th"))):
            sub_dict[data.find_all("th")[th].text] = cleaning_data(contents[contents_idx + th].text)
        std[title].append(sub_dict)

def std_crawler(dict, lst_page_soup, driver):
    page_list_data = lst_page_soup.find_all("tbody")[1]
    row_lst = page_list_data.find_all("tr")
    
    driver.implicitly_wait(100)
    
    for standard in range(1, len(row_lst) + 1):
        
        # data 개수 체크
        num = int(lst_page_soup.select("#tabs-container > div.table.list > table > tbody > tr:nth-of-type({}) > td:nth-of-type(1)".format(standard))[0].text)
        
        driver.implicitly_wait(100)
        
        #crawling 작업
        try:
            driver.find_element(By.XPATH, '//*[@id="tabs-container"]/div[2]/table/tbody/tr[{}]/td[2]/a'.format(standard)).click()
            
            std = {}
            
            result_html = driver.page_source
            soup = BeautifulSoup(result_html, 'html.parser')
            
            # 테이블 row 개수
            table_data = soup.find("div", {'class':'table view'})
            table_data = table_data.find('tbody').children

            table_lst = []
            for child in table_data:
                table_lst.append(child)
            for i in table_lst:
                if i == "\n":
                    table_lst.remove(i)
            
                                    
            for row in range(1, len(table_lst) + 1):
                selector = "#contents > div > div.content_inner > div.table.view > table > tbody > "
                title = soup.select(selector + "tr:nth-of-type({}) > th".format(row))[0].text
                
                # 인용표준, 기술기준 데이터 / index text를 비교하는 if 문으로 바꾸기 / 가독성 고려
                if title == "인용표준" or title == "기술기준":
                    title = soup.select(selector + "tr:nth-of-type({}) > th".format(row))[0].text
                    content = soup.select(selector + "tr:nth-of-type({}) > td".format(row))[0].text
                    
                    title_2 = soup.select(selector + "tr:nth-of-type({}) > th:nth-of-type(2)".format(row))[0].text
                    content_2 = soup.select(selector + "tr:nth-of-type({}) > td:nth-of-type(2)".format(row))[0].text
                    
                    
                    content = cleaning_data(content)
                    content_2 = cleaning_data(content_2)
                    
                    std[title] = content
                    std[title_2] = content_2
                    
                #테이블 데이터 처리 / 유형별로 파악해서 if 문 바꾸기 / 아예 클래스를 만들어서 기존 항목에 추가 제거의 경우에 처리할 경우 / 테이블 파싱하는 함수 만들기 (colspan 예외 처리도)
                elif title == "국제표준 부합화" or title == "표준이력사항" or title == "인증심사기준":
                    std[title] = []
                    
                    # 국제표준 부합화
                    if title == "국제표준 부합화":
                        sub_dict = {}
                        data = soup.find("div", {'class':"table list gray"})
                        contents = data.find_all("td")
                        
                        if "colspan" in contents[0].attrs:
                            for j in range(int(contents[0].attrs["colspan"])):
                                sub_dict[data.find_all("th")[j].text] = contents[0].text
                            std[title].append(sub_dict)
                            contents = contents[1:]
                            
                        table_parser(contents, data, std, title)
                            
                        
                    #표준이력사항
                    elif title == "표준이력사항":
                        data = soup.find_all("div", {'class':"table list gray"})[1]
                        contents = data.find_all("td")
                        
                        table_parser(contents, data, std, title)
                            
                            
                    #인증심사기준
                    else:
                        sub_dict = {}
                        data = soup.find_all("div", {'class':"table list gray"})[2]
                        contents = data.find_all("td")
                        if len(contents) == 1:
                            for i in range(int(contents[0].attrs["colspan"])):
                                sub_dict[data.find_all("th")[i].text] = contents[0].text
                            std[title].append(sub_dict)
                        
                        else:
                            table_parser(contents, data, std, title)

                # 나머지 데이터
                else:
                    content = soup.select(selector + "tr:nth-of-type({}) > td".format(row))[0].text
                    content = cleaning_data(content)
                    std[title] = content
                    
            now = time.localtime()
            now = "%04d/%02d/%02d %02d:%02d:%02d" % (now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)
            std['crawled_time'] = now
            dict['stds'].append(std)
            
            driver.back()
            driver.refresh()
            
        except:
            print("Crawling error, No : ", num)
            is_success = False
            return dict, is_success
    
        driver.implicitly_wait(100)
    is_success = True
    return dict, is_success

def page_crawl(start_page, chrome_path):
    driver = webdriver.Chrome(executable_path=chrome_path)
    driver.get("https://standard.go.kr/KSCI/standardIntro/getStandardSearchList.do?menuId=919&topMenuId=502")
    
    driver.find_element(By.CLASS_NAME, "last").click()
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    last_page = soup.find_all("a", {"class": "on"})[1].text
    driver.find_element(By.CLASS_NAME, "first").click()
    
    dict = {}
    dict['stds'] = []
    
    start_page = int(start_page)
    if start_page % 10 == 0:
        num_next = start_page // 10 - 1
    else:
        num_next = start_page // 10

    for i in range(num_next):
        driver.find_element(By.CLASS_NAME, 'next').click()
        
    page_source = driver.page_source
    lst_page_soup = BeautifulSoup(page_source, 'html.parser')

    # 페이지 버튼 갯수
    page_button_data = lst_page_soup.find("div", {'class':"page"})
    li_lst = page_button_data.find_all("li")
    li_lst = [button.text for button in li_lst]
    start = li_lst.index(str(start_page))
    
    is_success = False
    page_num = 0
    
    try:
        while True:
            for page in range(start + 1, len(li_lst) - 1):
                driver.find_element(By.XPATH, '//*[@id="tabs-container"]/div[3]/div/div/ul/li[{}]/a'.format(page)).click()
                page_num = driver.find_element(By.XPATH, '//*[@id="tabs-container"]/div[3]/div/div/ul/li[{}]/a'.format(page)).text
                
                page_source = driver.page_source
                lst_page_soup = BeautifulSoup(page_source, 'html.parser')
                driver.implicitly_wait(100)
                
                dict, is_success = std_crawler(dict, lst_page_soup, driver)
                
                if page_num == last_page:
                    is_success = True
                    return dict, int(page_num), is_success
                
            # 다시 1페이지부터
            start = 2
            
            driver.find_element(By.CLASS_NAME, 'next').click()
            
    except:
        return dict, int(page_num), is_success
    
    
def main(last_page_no, max_retry_num, chrome_path):
    datalist = {}
    datalist['stds'] = []
    current_retry_count = 0
    
    
    while True:
        if current_retry_count >= max_retry_num:
            print("number of retry exceeds maximum retry number")
            print("last page of crawling is ", last_page_no)
            return datalist, is_success, current_retry_count
        
        
        current_data_list, end_page_no, is_success = page_crawl(last_page_no, chrome_path)
        
        # merge current_data_list to datalist 
        for i in current_data_list['stds']:
            if i not in datalist['stds']:
                datalist['stds'].append(i)
                
        if is_success == False:
            current_retry_count = current_retry_count + 1
            to_json(datalist, "output_new.json")
            last_page_no = end_page_no
            print("Reconnecting to the page number : ", last_page_no)
            
        elif is_success:
            print("Done with crawling")
            to_json(datalist, "output_new.json")
            return datalist, is_success, current_retry_count
        

result, status, current_retry_count = main(1, 10, r"C:\Users\gihok\chatbot\chromedriver.exe")

# to_json(result, "output_new_all.json")
# print(status)
# print(current_retry_count)



def json_reader(filename):
    with open (filename, "r", encoding = 'UTF8') as f:
        data = json.load(f)
    
    df = pd.json_normalize(data['stds'])
    return df

def db_process(filename, host, password, db_name, table_name):
    db = pymysql.connect(host = host, port = 3306, user = 'root', password = password,
                     db = db_name, charset = 'utf8')   # charset: 인코딩 설정

    cursor = db.cursor()

    sql = 'INSERT INTO ' + table_name + ' (id, doc_num, doc_name_ko, doc_name_en, publish_date, final_date, json_data, crawled_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'

    output_df = json_reader(filename)
    output_df = output_df.reset_index()

    with open (filename, "r", encoding = 'UTF8') as f:
        data = json.load(f)
        
    lst = data['stds']
    std_lst = []
    for i in range(len(lst)):
        if lst[i] not in std_lst:
            std_lst.append(lst[i])
            

    # 정상적으로 작동됨
    for i in range(len(output_df)):
        json_data = json.dumps(std_lst[i])
        try:
            cursor.execute(sql, (output_df.loc[i][0], output_df.loc[i][1], output_df.loc[i][2], output_df.loc[i][3], output_df.loc[i][7], output_df.loc[i][8], json_data, output_df.loc[i][23]))
        except:
            if len(output_df.loc[i][7]) == 0:
                cursor.execute(sql, (output_df.loc[i][0], output_df.loc[i][1], output_df.loc[i][2], output_df.loc[i][3], None, output_df.loc[i][8], json_data, output_df.loc[i][23]))
            else:
                print(i)
    db.commit()

    db.close()

# db_process("output_all_std.json", "192.168.0.124", "linuxer", "std_crawled_data", "std_data")