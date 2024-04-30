import requests
import json
import psycopg2
from psycopg2 import extras as ex

# 生成Token
def get_token():
    headers = {
        'Content-Type': 'application/json'
    }
    params = {'user': 'open_euler_hw',
              'password': 'oepkgs4huawei@2024@iJKV1Qi',
              'expireInSeconds': 36000
    }
    url = 'https://search.oepkgs.net/api/search/openEuler/genToken'
    response = requests.post(url, headers=headers, params=params)
    return response.json()['data']['Authorization']


# 循环请求
def poll_request(token, conn, cursor, sql, scrollId=''):
    headers = {
        'Content-Type': 'application/json', 
        'Authorization': token
    }
    url = 'https://search.oepkgs.net/api/search/openEuler/scroll?scrollId=' + scrollId


    response = requests.get(url, headers=headers)
    data = response.json()['data']
    scrollId = data['scrollId']
    totalHits = data['totalHits']
    data_list = data['list']
    write_data(data_list, conn, cursor, sql) # 写入数据库
    return scrollId, totalHits


# 创建表
def create_table(conn, cursor):
    cursor.execute("CREATE TABLE IF NOT EXISTS oe_compatibility_oepkgs (IDX SERIAL PRIMARY KEY, summary VARCHAR(800), repoType VARCHAR(30), openeuler_version VARCHAR(20), rpmPackUrl VARCHAR(300), srcRpmPackUrl VARCHAR(300), name VARCHAR(100), arch VARCHAR(20), id VARCHAR(30), rpmLicense VARCHAR(600), version VARCHAR(80), osVer VARCHAR(20));")   
    conn.commit()

# 数据写入数据库
def write_data(data, conn, cursor, sql):
    data_list = []
    for item in data:
        data_list.append((item['summary'], item['repoType'], item['os'], item['rpmPackUrl'], item['srcRpmPackUrl'], item['name'], item['arch'], item['id'], item['rpmLicense'], item['version'], item['osVer']))    
    ex.execute_values(cursor, sql, data_list, page_size=1200)    
    conn.commit()
    

if __name__ == '__main__':
    # 生成token
    token = get_token()
    # 连接数据库
    conn = psycopg2.connect(database="postgres", user="postgres", password="123456", host='localhost', port="5444")
    cursor = conn.cursor()
    # 创建表
    create_table(conn, cursor)
    # 插入语句
    sql = 'INSERT INTO oe_compatibility_oepkgs (summary, repoType, openeuler_version, rpmPackUrl, srcRpmPackUrl, name, arch, id, rpmLicense, version, osVer) VALUES %s'
    # 首次请求
    scrollId, totalHits = poll_request(token, conn, cursor, sql)
    # 循环请求数据入库
    totalHits -= 1000
    while totalHits > 0:
        print('totalHits:', totalHits)
        try:
            scrollId, _ = poll_request(token, conn, cursor, sql, scrollId)
            totalHits -= 1000
        except Exception as e:
            print('请求失败:', e)
            continue
    cursor.close()
    conn.close()
    print('数据写入完成！')    





































