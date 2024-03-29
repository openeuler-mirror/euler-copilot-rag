import requests
import json

from oe_message_manager import OeMessageManager
class PullMeassageFromOeWeb():
    @staticmethod
    def pull_oe_compatibility_overall_unit():
        url='https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/hardwarecomp/findAll'
        headers = {  
            'Content-Type': 'application/json'
        }
        data={
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
                "dataSource": "",
                "solution": "",
                "certificationType": ""
            }
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        total_num=response.json()["result"]["totalCount"]
        data={
                "pages": {
                    "page": 1,
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
                "dataSource": "",
                "solution": "",
                "certificationType": ""
            }
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        OeMessageManager.clear_oe_compatibility_overall_unit()
        js=response.json()
        for i in range(len(js["result"]["hardwareCompList"])):
            for key in js["result"]["hardwareCompList"][i]:
                if type(js["result"]["hardwareCompList"][i][key])==list or type(js["result"]["hardwareCompList"][i][key])==dict or type(js["result"]["hardwareCompList"][i][key])==tuple: 
                    js["result"]["hardwareCompList"][i][key]=json.dumps(js["result"]["hardwareCompList"][i][key])
            OeMessageManager.add_oe_compatibility_overall_unit(js["result"]["hardwareCompList"][i])
    @staticmethod
    def pull_oe_compatibility_card():
        url='https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/drivercomp/findAll'
        headers = {  
            'Content-Type': 'application/json'
        }
        data={
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
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        total_num=response.json()["result"]["totalCount"]
        data={
                "pages": {
                    "page": 1,
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
                "dataSource": "",
                "solution": "",
                "certificationType": ""
            }
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        OeMessageManager.clear_oe_compatibility_card()
        js=response.json()
        for i in range(len(js["result"]["driverCompList"])):
            for key in js["result"]["driverCompList"][i]:
                if type(js["result"]["driverCompList"][i][key])==list or type(js["result"]["driverCompList"][i][key])==dict or type(js["result"]["driverCompList"][i][key])==tuple: 
                    js["result"]["driverCompList"][i][key]=json.dumps(js["result"]["driverCompList"][i][key])
            OeMessageManager.add_oe_compatibility_card(js["result"]["driverCompList"][i])
    @staticmethod
    def pull_oe_compatibility_open_source_software():
        url='https://www.openeuler.org/compatibility/api/web_backend/compat_software_info'
        headers = {  
            'Content-Type': 'application/json'
        }
        data={
                "page_size":1,
                "page_num":1
            }
        response=requests.get(
            url, 
            headers=headers, 
            data=data
        )
        total_num=response.json()["total"]
        data={
                "page_size":1,
                "page_num":total_num
            }
        response=requests.get(
            url, 
            headers=headers, 
            data=data
        )
        OeMessageManager.clear_oe_compatibility_open_source_software()
        js=response.json()
        for i in range(len(js["info"])):
            for key in js["info"][i]:
                if type(js["info"][i][key])==list or type(js["info"][i][key])==dict or type(js["info"][i][key])==tuple: 
                    js["info"][i][key]=json.dumps(js["info"][i][key])
            OeMessageManager.add_oe_compatibility_open_source_software(js["info"][i])
    @staticmethod
    def pull_oe_compatibility_commercial_software():
        url='https://www.openeuler.org/certification/software/communityChecklist'
        headers = {  
            'Content-Type': 'application/json'
        }
        data={
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
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        total_num=response.json()["result"]["totalNum"]
        data={
                "pageSize": total_num,
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
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        js=response.json()
        OeMessageManager.clear_oe_compatibility_commercial_software()
        for i in range(len(js["result"]["data"])):
            for key in js["result"]["data"][i]:
                if type(js["result"]["data"][i][key])==list or type(js["result"]["data"][i][key])==dict or type(js["result"]["data"][i][key])==tuple: 
                    js["result"]["data"][i][key]=json.dumps(js["result"]["data"][i][key])
            OeMessageManager.add_oe_compatibility_commercial_software(js["result"]["data"][i])
    @staticmethod
    def pull_oe_compatibility_open_source_software():
        url='https://www.openeuler.org/compatibility/api/web_backend/compat_software_info'
        headers = {  
            'Content-Type': 'application/json'
        }
        data={
                "page_size":1,
                "page_num":1
            }
        response=requests.get(
            url, 
            headers=headers, 
            data=data
        )
        total_num=response.json()["total"]
        data={
                "page_size":1,
                "page_num":total_num
            }
        response=requests.get(
            url, 
            headers=headers, 
            data=data
        )
        OeMessageManager.clear_oe_compatibility_open_source_software()
        js=response.json()
        for i in range(len(js["info"])):
            for key in js["info"][i]:
                if type(js["info"][i][key])==list or type(js["info"][i][key])==dict or type(js["info"][i][key])==tuple: 
                    js["info"][i][key]=json.dumps(js["info"][i][key])
            OeMessageManager.add_oe_compatibility_open_source_software(js["info"][i])
    @staticmethod
    def pull_oe_compatibility_solution():
        url='https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/solutioncomp/findAll'
        headers = {  
            'Content-Type': 'application/json'
        }
        data={
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
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        total_num=response.json()["result"]["totalCount"]
        data={
            "pages": {
                "page": 1,
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
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        js=response.json()
        OeMessageManager.clear_oe_compatibility_commercial_software()
        for i in range(len(js["result"]["solutionCompList"])):
            for key in js["result"]["solutionCompList"][i]:
                if type(js["result"]["solutionCompList"][i][key])==list or type(js["result"]["solutionCompList"][i][key])==dict or type(js["result"]["solutionCompList"][i][key])==tuple: 
                    js["result"]["solutionCompList"][i][key]=json.dumps(js["result"]["solutionCompList"][i][key])
            OeMessageManager.add_oe_compatibility_commercial_software(js["result"]["solutionCompList"][i])
    @staticmethod
    def pull_oe_compatibility_solution():
        url='https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/solutioncomp/findAll'
        headers = {  
            'Content-Type': 'application/json'
        }
        data={
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
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        total_num=response.json()["result"]["totalCount"]
        data={
            "pages": {
                "page": 1,
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
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        js=response.json()
        OeMessageManager.clear_oe_compatibility_solution()
        for i in range(len(js["result"]["solutionCompList"])):
            for key in js["result"]["solutionCompList"][i]:
                if type(js["result"]["solutionCompList"][i][key])==list or type(js["result"]["solutionCompList"][i][key])==dict or type(js["result"]["solutionCompList"][i][key])==tuple: 
                    js["result"]["solutionCompList"][i][key]=json.dumps(js["result"]["solutionCompList"][i][key])
            OeMessageManager.add_oe_compatibility_solution(js["result"]["solutionCompList"][i])
    @staticmethod
    def pull_oe_compatibility_osv():
        url='https://www.openeuler.org/api-euler/api-cve/cve-security-notice-server/osv/findAll'
        headers = {  
            'Content-Type': 'application/json'
        }
        data={
            "pages": {
                "page": 1,
                "size": 10
            },
            "keyword": "",
            "type": "",
            "osvName": ""
        }
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        total_num=response.json()["result"]["totalCount"]
        data={
            "pages": {
                "page": 1,
                "size": total_num
            },
            "keyword": "",
            "type": "",
            "osvName": ""
        }
        response=requests.post(
            url, 
            headers=headers, 
            json=data
        )
        js=response.json()
        OeMessageManager.clear_compatibility_osv()
        for i in range(len(js["result"]["osvList"])):
            for key in js["result"]["osvList"][i]:
                if type(js["result"]["osvList"][i][key])==list or type(js["result"]["osvList"][i][key])==dict or type(js["result"]["osvList"][i][key])==tuple: 
                    js["result"]["osvList"][i][key]=json.dumps(js["result"]["osvList"][i][key])
            OeMessageManager.add_oe_compatibility_osv(js["result"]["osvList"][i])