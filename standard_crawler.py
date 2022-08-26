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
import datetime


# json file로 변환하는 함수
def transform_to_json(dic, file_name):
    with open(file_name, 'w', encoding = 'UTF8') as f:
        json.dump(dic, f, ensure_ascii=False, indent = '\t')
        
        
# text 데이터 정제 함수        
def clean_data(string):
    regexed_str = re.sub("[\n]+", " ", string)
    regexed_str = re.sub("[\t]+", " ", string)
    return_string = regexed_str.replace("\n", " ")
    return return_string.strip()


# 테이블 형태 데이터 처리 함수
def small_table_parser(contents_node, header_node):
    total_lst = []
    for contents_idx in range(0, len(contents_node), len(header_node.find_all("th"))):
        sub_dict = {}
        for th in range(len(header_node.find_all("th"))):
            sub_dict[header_node.find_all("th")[th].text] = clean_data(contents_node[contents_idx + th].text)
        total_lst.append(sub_dict)
    return total_lst


# 표준 데이터 크롤러
def std_crawler(whole_dict, lst_page_soup, driver, std_idx):
    page_list_data = lst_page_soup.find_all("tbody")[1]
    row_lst = page_list_data.find_all("tr")
    
    driver.implicitly_wait(100)
    
    for standard in range(std_idx, len(row_lst) + 1):
        
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
                    
                    
                    content = clean_data(content)
                    content_2 = clean_data(content_2)
                    
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
                            
                        table_data_lst = small_table_parser(contents, data)
                        for tb_data in table_data_lst:
                            std[title].append(tb_data)
                        
                    #표준이력사항
                    elif title == "표준이력사항":
                        data = soup.find_all("div", {'class':"table list gray"})[1]
                        contents = data.find_all("td")
                        
                        table_data_lst = small_table_parser(contents, data)
                        std[title] = table_data_lst
                            
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
                            table_data_lst = small_table_parser(contents, data)
                            std[title] = table_data_lst

                # 나머지 데이터
                else:
                    content = soup.select(selector + "tr:nth-of-type({}) > td".format(row))[0].text
                    content = clean_data(content)
                    std[title] = content
                    
            now = time.localtime()
            now = "%04d/%02d/%02d %02d:%02d:%02d" % (now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)
            std['crawled_time'] = now
            whole_dict['stds'].append(std)
            
            driver.back()
            driver.refresh()
            
        except:
            print("Crawling error, No : ", num)
            is_success = False
            return whole_dict, is_success, standard
    
        driver.implicitly_wait(100)
    
    std_idx = 1    
    is_success = True
    return whole_dict, is_success, std_idx


# 페이지 넘기는 크롤러
def page_crawler(start_page, chrome_path, url, std_idx):
    driver = webdriver.Chrome(executable_path=chrome_path)
    driver.get(url)
    
    driver.find_element(By.CLASS_NAME, "last").click()
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    last_page = soup.find_all("a", {"class": "on"})[1].text
    driver.find_element(By.CLASS_NAME, "first").click()
    
    std_dict = {}
    std_dict['stds'] = []
    
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
                
                std_dict, is_success, std_idx = std_crawler(std_dict, lst_page_soup, driver, std_idx)
                
                if page_num == last_page:
                    is_success = True
                    return std_dict, int(page_num), is_success, std_idx
                
                else:
                    is_success = False
                # if is_success == False:
                #     return std_dict, int(page_num), is_success, std_idx
                
            # 다시 1페이지부터
            start = 2
            
            driver.find_element(By.CLASS_NAME, 'next').click()
            
    except:
        return std_dict, int(page_num), is_success, std_idx
    

# json 파일 dataframe으로 읽는 함수
def json_reader(filename):
    with open (filename, "r", encoding = 'UTF8') as f:
        data = json.load(f)
    
    df = pd.json_normalize(data['stds'])
    return df


# DB에 테이블이 생성되어 있다면 테이블에 데이터 넣는 함수
def db_process(filename, host, password, schema_name, table_name):
    try:
        db = pymysql.connect(host = host, port = 3306, user = 'root', password = password,
                        db = schema_name, charset = 'utf8')   # charset: 인코딩 설정
    except: 
        print("Can not connent to DB server. Please check the connection")
        return
    
    cursor = db.cursor()

    sql = 'INSERT INTO ' + table_name + ' (doc_num, doc_name_ko, doc_name_en, publish_date, final_date, json_data, crawled_time, tag) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'

    output_df = json_reader(filename)
    output_df = output_df.reset_index()

    with open (filename, "r", encoding = 'UTF8') as f:
        data = json.load(f)
        
    lst = data['stds']
            
    for i in range(len(output_df)):
        json_data = json.dumps(lst[i])
        try:
            cursor.execute(sql, (output_df.loc[i]["표준번호"], output_df.loc[i]["표준명(한글)"], output_df.loc[i]["표준명(영문)"], output_df.loc[i]["제정일"], output_df.loc[i]["최종개정확인일"], json_data, output_df.loc[i]["crawled_time"], filename[7:15]))
        except:
            if len(output_df.loc[i]["제정일"]) == 0:
                cursor.execute(sql, (output_df.loc[i]["표준번호"], output_df.loc[i]["표준명(한글)"], output_df.loc[i]["표준명(영문)"], None, output_df.loc[i]["최종개정확인일"], json_data, output_df.loc[i]["crawled_time"], filename[7:15]))
            else:
                print("There is a problem while inserting data number : ", i)
    db.commit()

    db.close()
    print("Done with inserting data to DB")
    return


# main 함수 = crawling --> json data --> DB 연동 및 데이터 inserting
def main(last_page_no, max_retry_num, chrome_path, url, host, password, schema_name, table_name):
    data_list = {}
    data_list['stds'] = []
    current_retry_count = 0
    std_idx = 1
    now = datetime.datetime.now()
    output_name = "output_{}.json".format(now.strftime('%Y%m%d'))
    
    while True:
        if current_retry_count >= max_retry_num:
            print("number of retry exceeds maximum retry number")
            print("last page of crawling is ", last_page_no)
            transform_to_json(data_list, output_name)
            break
            # return data_list, is_success, current_retry_count
        
        current_data_list, end_page_no, is_success, std_idx = page_crawler(last_page_no, chrome_path, url, std_idx)
        
        # merge current_data_list to data_list 
        for i in current_data_list['stds']:
            if i not in data_list['stds']:
                data_list['stds'].append(i)
                
        # if it couldn't reach the last page
        if is_success == False:
            current_retry_count = current_retry_count + 1
            transform_to_json(data_list, output_name)
            last_page_no = end_page_no
            print("Reconnecting to the page number : ", last_page_no)
        
        # if it reaches the last page
        elif is_success:
            print("Done with crawling")
            transform_to_json(data_list, output_name)
            break
            # return data_list, is_success, current_retry_count
            
    return db_process(output_name, host, password, schema_name, table_name)
        
        
url = "https://standard.go.kr/KSCI/standardIntro/getStandardSearchList.do?menuId=919&topMenuId=502"
main(1700, 10, r"C:\Users\gihok\chatbot\chromedriver.exe", url, "192.168.0.124", "linuxer", "std_crawled_data", "std_data_check")
