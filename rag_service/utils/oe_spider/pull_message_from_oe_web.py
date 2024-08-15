import requests
import json
import copy
from datetime import datetime
from oe_message_manager import OeMessageManager
from rag_service.security.config import config


class PullMessageFromOeWeb:
    @staticmethod
    def pull_oe_compatibility_overall_unit():
        url = 'https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/hardwarecomp/findAll'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "pages": {
                "page": 1,
                "size": 10
            },
            "architecture": "",
            "keyword": "",
            "cpu": "",
            "os": "",
            "testOrganization": "",
            "type": "",
            "cardType": "",
            "lang": "zh",
            "dataSource": "assessment",
            "solution": "",
            "certificationType": ""
        }

        response = requests.post(
            url,
            headers=headers,
            json=data
        )
        results = []
        total_num = response.json()["result"]["totalCount"]
        for i in range(total_num//10+(total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i+1,
                    "size": 10
                },
                "architecture": "",
                "keyword": "",
                "cpu": "",
                "os": "",
                "testOrganization": "",
                "type": "",
                "cardType": "",
                "lang": "zh",
                "dataSource": "assessment",
                "solution": "",
                "certificationType": ""
            }
            response = requests.post(
                url,
                headers=headers,
                json=data
            )
            results += response.json()["result"]["hardwareCompList"]
        OeMessageManager.clear_oe_compatibility_overall_unit()
        for i in range(len(results)):
            for key in results[i]:
                if type(results[i][key]) == list or type(
                        results[i][key]) == dict or type(
                        results[i][key]) == tuple:
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_overall_unit(results[i])

    @staticmethod
    def pull_oe_compatibility_card():
        url = 'https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/drivercomp/findAll'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "pages": {
                "page": 1,
                "size": 10
            },
            "architecture": "",
            "keyword": "",
            "cpu": "",
            "os": "",
            "testOrganization": "",
            "type": "",
            "cardType": "",
            "lang": "zh",
            "dataSource": "assessment",
            "solution": "",
            "certificationType": ""
        }
        response = requests.post(
            url,
            headers=headers,
            json=data
        )
        results = []
        total_num = response.json()["result"]["totalCount"]
        for i in range(total_num//10+(total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i+1,
                    "size": 10
                },
                "architecture": "",
                "keyword": "",
                "cpu": "",
                "os": "",
                "testOrganization": "",
                "type": "",
                "cardType": "",
                "lang": "zh",
                "dataSource": "",
                "solution": "",
                "certificationType": ""
            }
            response = requests.post(
                url,
                headers=headers,
                json=data
            )
            results += response.json()["result"]["driverCompList"]
        OeMessageManager.clear_oe_compatibility_card()
        for i in range(len(results)):
            for key in results[i]:
                if type(results[i][key]) == list or type(
                        results[i][key]) == dict or type(
                        results[i][key]) == tuple:
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_card(results[i])

    @staticmethod
    def pull_oe_compatibility_commercial_software():
        url = 'https://www.openeuler.org/certification/software/communityChecklist'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "pageSize": 1,
            "pageNo": 1,
            "testOrganization": "",
            "osName": "",
            "keyword": "",
            "dataSource": [
                "assessment"
            ],
            "productType": [
                "软件"
            ]
        }
        response = requests.post(
            url,
            headers=headers,
            json=data
        )
        results = []
        total_num = response.json()["result"]["totalNum"]
        for i in range(total_num//10+(total_num % 10 != 0)):
            data = {
                "pageSize": i+1,
                "pageNo": 10,
                "testOrganization": "",
                "osName": "",
                "keyword": "",
                "dataSource": [
                    "assessment"
                ],
                "productType": [
                    "软件"
                ]
            }
            response = requests.post(
                url,
                headers=headers,
                json=data
            )
            results += response.json()["result"]["data"]
        OeMessageManager.clear_oe_compatibility_commercial_software()
        for i in range(len(results)):
            for key in results[i]:
                if type(results[i][key]) == list or type(results[i][key]) == dict or type(
                        results[i][key]) == tuple:
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_commercial_software(results[i])

    @staticmethod
    def pull_oe_compatibility_open_source_software():
        url = 'https://www.openeuler.org/compatibility/api/web_backend/compat_software_info'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "page_size": 1,
            "page_num": 1
        }
        response = requests.get(
            url,
            headers=headers,
            data=data
        )
        results = []
        total_num = response.json()["total"]
        for i in range(total_num//10+(total_num % 10 != 0)):
            data = {
                "page_size": i+1,
                "page_num": 10
            }
            response = requests.get(
                url,
                headers=headers,
                data=data
            )
            results += response.json()["info"]
        OeMessageManager.clear_oe_compatibility_open_source_software()
        for i in range(len(results)):
            for key in results[i]:
                if type(results[i][key]) == list or type(results[i][key]) == dict or type(
                        results[i][key]) == tuple:
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_open_source_software(results[i])

    @staticmethod
    def pull_oe_compatibility_oepkgs():
        headers = {
            'Content-Type': 'application/json'
        }
        params = {'user': config['oepkg_user_account'],
                  'password': config['oepkg_user_pwd'],
                  'expireInSeconds': 36000
                  }
        url = 'https://search.oepkgs.net/api/search/openEuler/genToken'
        response = requests.post(url, headers=headers, params=params)
        token = response.json()['data']['Authorization']
        headers = {
            'Content-Type': 'application/json',
            'Authorization': token
        }
        url = 'https://search.oepkgs.net/api/search/openEuler/scroll?scrollId='
        response = requests.get(url, headers=headers)
        data = response.json()['data']
        scrollId = data['scrollId']
        totalHits = data['totalHits']
        data_list = data['list']
        results = data_list
        totalHits -= 1000

        while totalHits > 0:
            url = 'https://search.oepkgs.net/api/search/openEuler/scroll?scrollId='+scrollId
            response = requests.get(url, headers=headers)
            data = response.json()['data']
            data_list = data['list']
            results += data_list
            totalHits -= 1000
        OeMessageManager.clear_oe_compatibility_oepkgs()
        for i in range(len(results)):
            for key in results[i]:
                if type(results[i][key]) == list or type(results[i][key]) == dict or type(
                        results[i][key]) == tuple:
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_oepkgs(results[i])

    @staticmethod
    def pull_oe_compatibility_solution():
        url = 'https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/solutioncomp/findAll'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "pages": {
                "page": 1,
                "size": 1
            },
            "architecture": "",
            "keyword": "",
            "cpu": "",
            "os": "",
            "testOrganization": "",
            "type": "",
            "cardType": "",
            "lang": "zh",
            "dataSource": "assessment",
            "solution": "",
            "certificationType": ""
        }
        response = requests.post(
            url,
            headers=headers,
            json=data
        )
        results = []
        total_num = response.json()["result"]["totalCount"]
        for i in range(total_num//10+(total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i+1,
                    "size": total_num
                },
                "architecture": "",
                "keyword": "",
                "cpu": "",
                "os": "",
                "testOrganization": "",
                "type": "",
                "cardType": "",
                "lang": "zh",
                "dataSource": "assessment",
                "solution": "",
                "certificationType": ""
            }
            response = requests.post(
                url,
                headers=headers,
                json=data
            )
            results += response.json()["result"]["solutionCompList"]
        OeMessageManager.clear_oe_compatibility_solution()
        for i in range(len(results)):
            for key in results[i]:
                if type(results[i][key]) == list or type(
                        results[i][key]) == dict or type(
                        results[i][key]) == tuple:
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_solution(results[i])

    @staticmethod
    def pull_oe_compatibility_osv():
        url = 'https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/osv/findAll'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "pages": {
                "page": 1,
                "size": 10
            },
            "keyword": "",
            "type": "",
            "osvName": ""
        }
        response = requests.post(
            url,
            headers=headers,
            json=data
        )
        results = []
        total_num = response.json()["result"]["totalCount"]
        for i in range(total_num//10+(total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i+1,
                    "size": 10
                },
                "keyword": "",
                "type": "",
                "osvName": ""
            }
            response = requests.post(
                url,
                headers=headers,
                json=data
            )
            results += response.json()["result"]["osvList"]
        for i in range(len(results)):
            results[i]['details'] = 'https://www.openeuler.org/zh/approve/approve-info/?id='+str(results[i]['id'])
        OeMessageManager.clear_compatibility_osv()
        for i in range(len(results)):
            for key in results[i]:
                if type(results[i][key]) == list or type(
                        results[i][key]) == dict or type(results[i][key]) == tuple:
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_osv(results[i])

    @staticmethod
    def pull_oe_compatibility_security_notice():
        url = 'https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/securitynotice/findAll'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "pages": {
                "page": 1,
                "size": 1
            },
            "keyword": "",
            "type": [],
            "date": [],
            "affectedProduct": [],
            "affectedComponent": "",
            "noticeType": "cve"
        }
        response = requests.post(
            url,
            headers=headers,
            json=data
        )
        results = []
        total_num = response.json()["result"]["totalCount"]
        for i in range(total_num//10+(total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i+1,
                    "size": 10
                },
                "keyword": "",
                "type": [],
                "date": [],
                "affectedProduct": [],
                "affectedComponent": "",
                "noticeType": "cve"
            }
            response = requests.post(
                url,
                headers=headers,
                json=data
            )
            results += response.json()["result"]["securityNoticeList"]

        new_results = []
        for i in range(len(results)):
            openeuler_version_list = results[i]['affectedProduct'].split(';')
            cve_id_list = results[i]['cveId'].split(';')
            cnt = 0
            for openeuler_version in openeuler_version_list:
                if len(openeuler_version) > 0:
                    for cve_id in cve_id_list:
                        if len(cve_id) > 0:
                            tmp_dict = copy.deepcopy(results[i])
                            del tmp_dict['affectedProduct']
                            tmp_dict['id'] = int(str(tmp_dict['id'])+str(cnt))
                            tmp_dict['openeuler_version'] = openeuler_version
                            tmp_dict['cveId'] = cve_id
                            new_results.append(tmp_dict)
                            tmp_dict['details'] = 'https://www.openeuler.org/zh/security/security-bulletins/detail/?id='+tmp_dict['securityNoticeNo']
                            cnt += 1
        results = new_results
        OeMessageManager.clear_oe_compatibility_security_notice()
        for i in range(len(results)):
            for key in results[i]:
                if type(results[i][key]) == list or type(
                    results[i][key]) == dict or type(
                        results[i][key]) == tuple:
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_security_notice(results[i])

    @staticmethod
    def pull_oe_compatibility_cve_database():
        url = 'https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/cvedatabase/findAll'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "pages": {
                "page": 1,
                "size": 1
            },
            "keyword": "",
            "status": "",
            "year": "",
            "score": "",
            "noticeType": "cve"
        }
        response = requests.post(
            url,
            headers=headers,
            json=data
        )
        js = response.json()
        results = []
        total_num = response.json()["result"]["totalCount"]
        for i in range(total_num//10+(total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i+1,
                    "size": 10
                },
                "keyword": "",
                "status": "",
                "year": "",
                "score": "",
                "noticeType": "cve"
            }
            response = requests.post(
                url,
                headers=headers,
                json=data
            )
            results += response.json()["result"]["cveDatabaseList"]
            break
        for i in range(len(results)):
            results[i]['details'] = 'https://www.openeuler.org/zh/security/cve/detail/?cveId=' + \
                results[i]['cveId']+'&packageName='+results[i]['packageName']
        OeMessageManager.clear_oe_compatibility_cve_database()
        for i in range(len(results)):
            for key in results[i]:
                if type(results[i][key]) == list or type(
                    results[i][key]) == dict or type(
                        results[i][key]) == tuple:
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_cve_database(results[i])

    @staticmethod
    def oe_organize_message_handler():
        f = open('rag_service/utils/oe_spider/organize.txt', 'r', encoding='utf-8')
        lines = f.readlines()
        st = 0
        en = 0
        filed_list = ['role', 'name', 'personal_message']
        OeMessageManager.clear_oe_community_organization_structure()
        while st < len(lines):
            while en < len(lines) and lines[en] != '\n':
                en += 1
            lines[st] = lines[st].replace('\n', '')
            committee_name = lines[st]
            for i in range(st+1, en):
                data = lines[i].replace('\n', '').split(' ')
                info = {'committee_name': committee_name}
                for j in range(min(len(filed_list), len(data))):
                    data[j] = data[j].replace('\n', '')
                    if j == 2:
                        data[j] = data[j].replace('_', ' ')
                    info[filed_list[j]] = data[j]
                OeMessageManager.add_oe_community_organization_structure(info)
            st = en+1
            en = st

    @staticmethod
    def oe_openeuler_version_message_handler():
        f = open('rag_service/utils/oe_spider/openeuler_version.txt', 'r', encoding='utf-8')
        lines = f.readlines()
        filed_list = ['openeuler_version', 'kernel_version', 'publish_time', 'version_type']
        OeMessageManager.clear_oe_community_openEuler_version()
        for line in lines:
            tmp_list = line.replace('\n','').split(' ')
            tmp_list[2] = datetime.strptime(tmp_list[2], "%Y-%m-%d")
            tmp_dict = {}
            for i in range(len(filed_list)):
                tmp_dict[filed_list[i]] = tmp_list[i]
            OeMessageManager.add_oe_community_openEuler_version(tmp_dict)

