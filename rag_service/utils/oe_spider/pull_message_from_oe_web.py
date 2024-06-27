import requests
import json

from oe_message_manager import OeMessageManager


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
        results=[]
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
        results=[]
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
        results=[]
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
            results+= response.json()["result"]["data"]
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
        results=[]
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
        f=open('rag_service/utils/oe_spider/organize.txt','r',encoding='utf-8')
        lines=f.readlines()
        st=0
        en=0
        filed_list=['role','name','personal_message']
        OeMessageManager.clear_oe_community_organization_structure()
        while st<len(lines):
            while en<len(lines) and lines[en]!='\n':
                en+=1
            lines[st]=lines[st].replace('\n','')
            committee_name=lines[st]
            for i in range(st+1,en):
                data=lines[i].replace('\n','').split(' ')
                info={'committee_name':committee_name}
                for j in range(min(len(filed_list),len(data))):
                    data[j]=data[j].replace('\n','')
                    if j==2:
                        data[j]=data[j].replace('_',' ')
                    info[filed_list[j]]=data[j]
                OeMessageManager.add_oe_community_organization_structure(info)
            st=en+1
            en=st

PullMessageFromOeWeb.oe_organize_message_handler()
