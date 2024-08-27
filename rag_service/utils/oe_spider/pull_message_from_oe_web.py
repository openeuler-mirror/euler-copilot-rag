import multiprocessing

import requests
import json
import copy
from datetime import datetime
import os
import yaml
from yaml import SafeLoader
from oe_message_manager import OeMessageManager
import argparse
import urllib.parse


class PullMessageFromOeWeb:
    @staticmethod
    def pull_oe_compatibility_overall_unit(pg_url):
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
        for i in range(total_num // 10 + (total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i + 1,
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
        OeMessageManager.clear_oe_compatibility_overall_unit(pg_url)
        for i in range(len(results)):
            for key in results[i]:
                if isinstance(results[i][key], (dict, list, tuple)):
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_overall_unit(pg_url, results[i])

    @staticmethod
    def pull_oe_compatibility_card(pg_url):
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
        for i in range(total_num // 10 + (total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i + 1,
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
        OeMessageManager.clear_oe_compatibility_card(pg_url)
        for i in range(len(results)):
            for key in results[i]:
                if isinstance(results[i][key], (dict, list, tuple)):
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_card(pg_url, results[i])

    @staticmethod
    def pull_oe_compatibility_commercial_software(pg_url):
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
        for i in range(total_num // 10 + (total_num % 10 != 0)):
            data = {
                "pageSize": i + 1,
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
        OeMessageManager.clear_oe_compatibility_commercial_software(pg_url)
        for i in range(len(results)):
            for key in results[i]:
                if isinstance(results[i][key], (dict, list, tuple)):
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_commercial_software(pg_url, results[i])

    @staticmethod
    def pull_oe_compatibility_open_source_software(pg_url):
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
        for i in range(total_num // 10 + (total_num % 10 != 0)):
            data = {
                "page_size": i + 1,
                "page_num": 10
            }
            response = requests.get(
                url,
                headers=headers,
                data=data
            )
            results += response.json()["info"]
        OeMessageManager.clear_oe_compatibility_open_source_software(pg_url)
        for i in range(len(results)):
            for key in results[i]:
                if isinstance(results[i][key], (dict, list, tuple)):
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_open_source_software(pg_url, results[i])

    @staticmethod
    def pull_oe_compatibility_oepkgs(pg_url, oepkgs_info):
        headers = {
            'Content-Type': 'application/json'
        }
        params = {'user': oepkgs_info.get('oepkgs_user', ''),
                  'password': oepkgs_info.get('oepkgs_pwd', ''),
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
            url = 'https://search.oepkgs.net/api/search/openEuler/scroll?scrollId=' + scrollId
            response = requests.get(url, headers=headers)
            data = response.json()['data']
            data_list = data['list']
            results += data_list
            totalHits -= 1000
        OeMessageManager.clear_oe_compatibility_oepkgs(pg_url)
        for i in range(len(results)):
            for key in results[i]:
                if isinstance(results[i][key], (dict, list, tuple)):
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_oepkgs(pg_url, results[i])

    @staticmethod
    def pull_oe_compatibility_solution(pg_url):
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
        for i in range(total_num // 10 + (total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i + 1,
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
        OeMessageManager.clear_oe_compatibility_solution(pg_url)
        for i in range(len(results)):
            for key in results[i]:
                if isinstance(results[i][key], (dict, list, tuple)):
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_solution(pg_url, results[i])

    @staticmethod
    def pull_oe_compatibility_osv(pg_url):
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
        for i in range(total_num // 10 + (total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i + 1,
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
            results[i]['details'] = 'https://www.openeuler.org/zh/approve/approve-info/?id=' + str(results[i]['id'])
        OeMessageManager.clear_compatibility_osv(pg_url)
        for i in range(len(results)):
            for key in results[i]:
                if isinstance(results[i][key], (dict, list, tuple)):
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_osv(pg_url, results[i])

    @staticmethod
    def pull_oe_compatibility_security_notice(pg_url):
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
        for i in range(total_num // 10 + (total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i + 1,
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
                            tmp_dict['id'] = int(str(tmp_dict['id']) + str(cnt))
                            tmp_dict['openeuler_version'] = openeuler_version
                            tmp_dict['cveId'] = cve_id
                            new_results.append(tmp_dict)
                            tmp_dict[
                                'details'] = 'https://www.openeuler.org/zh/security/security-bulletins/detail/?id=' + \
                                             tmp_dict['securityNoticeNo']
                            cnt += 1
        results = new_results
        OeMessageManager.clear_oe_compatibility_security_notice(pg_url)
        for i in range(len(results)):
            for key in results[i]:
                if isinstance(results[i][key], (dict, list, tuple)):
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_security_notice(pg_url, results[i])

    @staticmethod
    def pull_oe_compatibility_cve_database(pg_url):
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
        for i in range(total_num // 10 + (total_num % 10 != 0)):
            data = {
                "pages": {
                    "page": i + 1,
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

        for i in range(len(results)):
            results[i]['details'] = 'https://www.openeuler.org/zh/security/cve/detail/?cveId=' + \
                                    results[i]['cveId'] + '&packageName=' + results[i]['packageName']
        OeMessageManager.clear_oe_compatibility_cve_database(pg_url)
        for i in range(len(results)):
            for key in results[i]:
                if isinstance(results[i][key], (dict, list, tuple)):
                    results[i][key] = json.dumps(results[i][key])
            OeMessageManager.add_oe_compatibility_cve_database(pg_url, results[i])

    @staticmethod
    def pull_oe_openeuler_sig(pg_url):
        sig_url_base = 'https://www.openeuler.org/api-dsapi/query/sig/info'
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            "community": "openeuler",
            "page": 1,
            "pageSize": 12,
            "search": "fuzzy"
        }
        sig_url = sig_url_base + '?' + urllib.parse.urlencode(data)
        response = requests.post(
            sig_url,
            headers=headers,
            json=data
        )
        results_all = []
        total_num = response.json()["data"][0]["total"]
        for i in range(total_num // 12 + (total_num % 12 != 0)):
            data = {
                "community": "openeuler",
                "page": i + 1,
                "pageSize": 12,
                "search": "fuzzy"
            }
            sig_url = sig_url_base + '?' + urllib.parse.urlencode(data)
            response = requests.post(
                sig_url,
                headers=headers,
                json=data
            )
            results_all += response.json()["data"][0]["data"]

        results_members = []
        results_repos = []
        for i in range(len(results_all)):
            temp_members = []
            sig_name = results_all[i]['sig_name']
            repos_url_base = 'https://www.openeuler.org/api-dsapi/query/sig/repo/committers'
            repos_url = repos_url_base + '?community=openeuler&sig=' + sig_name
            response = requests.get(repos_url)
            results = response.json()["data"]
            committers = results['committers']
            maintainers = results['maintainers']
            if committers is None:
                committers = []
            if maintainers is None:
                maintainers = []
            results_all[i]['committers'] = committers
            results_all[i]['maintainers'] = maintainers
            for key in results_all[i]:
                if key == "committer_info" or key == "maintainer_info":  # solve with members
                    if results_all[i][key] is not None:
                        for member in results_all[i][key]:
                            member['sig_name'] = sig_name
                            temp_members.append(member)
                elif key == "repos":  # solve with repos
                    if results_all[i][key] is not None:
                        for repo in results_all[i][key]:
                            results_repos.append({'repo': repo, 'url': 'https://gitee.com/' + repo,
                                                  'sig_name': sig_name,
                                                  'committers': committers,
                                                  'maintainers': maintainers})
                else:  # solve others
                    if isinstance(results_all[i][key], (dict, list, tuple)):
                        results_all[i][key] = json.dumps(results_all[i][key])

            results_members += temp_members

        temp_results_members = []
        seen = set()
        for d in results_members:
            if d['gitee_id'] not in seen:
                seen.add(d['gitee_id'])
                temp_results_members.append(d)
        results_members = temp_results_members

        OeMessageManager.clear_oe_openeuler_sig_group(pg_url)
        for i in range(len(results_all)):
            for key in results_all[i]:
                if isinstance(results_all[i][key], (dict, list, tuple)):
                    results_all[i][key] = json.dumps(results_all[i][key])
            OeMessageManager.add_oe_openeuler_sig_group(pg_url, results_all[i])

        OeMessageManager.clear_oe_openeuler_sig_members(pg_url)
        for i in range(len(results_members)):
            for key in results_members[i]:
                if isinstance(results_members[i][key], (dict, list, tuple)):
                    results_members[i][key] = json.dumps(results_members[i][key])
            OeMessageManager.add_oe_openeuler_sig_members(pg_url, results_members[i])

        OeMessageManager.clear_oe_openeuler_sig_repos(pg_url)
        for i in range(len(results_repos)):
            for key in results_repos[i]:
                if isinstance(results_repos[i][key], (dict, list, tuple)):
                    results_repos[i][key] = json.dumps(results_repos[i][key])
            OeMessageManager.add_oe_openeuler_sig_repos(pg_url, results_repos[i])

        OeMessageManager.clear_oe_sig_group_to_repos(pg_url)
        for i in range(len(results_repos)):
            repo_name = results_repos[i]['repo']
            group_name = results_repos[i]['sig_name']
            OeMessageManager.add_oe_sig_group_to_repos(pg_url, group_name, repo_name)

        OeMessageManager.clear_oe_sig_group_to_members(pg_url)
        for i in range(len(results_all)):
            committers = set(json.loads(results_all[i]['committers']))
            maintainers = set(json.loads(results_all[i]['maintainers']))
            group_name = results_all[i]['sig_name']

            all_members = committers.union(maintainers)

            for member_name in all_members:
                if member_name in committers and member_name in maintainers:
                    role = 'committer & maintainer'
                elif member_name in committers:
                    role = 'committer'
                elif member_name in maintainers:
                    role = 'maintainer'

                OeMessageManager.add_oe_sig_group_to_members(pg_url, group_name, member_name, role=role)


        OeMessageManager.clear_oe_sig_repos_to_members(pg_url)
        for i in range(len(results_repos)):
            repo_name = results_repos[i]['repo']
            committers = set(json.loads(results_repos[i]['committers']))
            maintainers = set(json.loads(results_repos[i]['maintainers']))

            all_members = committers.union(maintainers)

            for member_name in all_members:
                if member_name in committers and member_name in maintainers:
                    role = 'committer & maintainer'
                elif member_name in committers:
                    role = 'committer'
                elif member_name in maintainers:
                    role = 'maintainer'

                OeMessageManager.add_oe_sig_repos_to_members(pg_url, repo_name, member_name, role=role)

    @staticmethod
    def oe_organize_message_handler(pg_url):
        f = open('./doc/organize.txt', 'r', encoding='utf-8')
        lines = f.readlines()
        st = 0
        en = 0
        filed_list = ['role', 'name', 'personal_message']
        OeMessageManager.clear_oe_community_organization_structure(pg_url)
        while st < len(lines):
            while en < len(lines) and lines[en] != '\n':
                en += 1
            lines[st] = lines[st].replace('\n', '')
            committee_name = lines[st]
            for i in range(st + 1, en):
                data = lines[i].replace('\n', '').split(' ')
                info = {'committee_name': committee_name}
                for j in range(min(len(filed_list), len(data))):
                    data[j] = data[j].replace('\n', '')
                    if j == 2:
                        data[j] = data[j].replace('_', ' ')
                    info[filed_list[j]] = data[j]
                OeMessageManager.add_oe_community_organization_structure(pg_url, info)
            st = en + 1
            en = st

    @staticmethod
    def oe_openeuler_version_message_handler(pg_url):
        f = open('./docs/openeuler_version.txt', 'r', encoding='utf-8')
        lines = f.readlines()
        filed_list = ['openeuler_version', 'kernel_version', 'publish_time', 'version_type']
        OeMessageManager.clear_oe_community_openEuler_version(pg_url)
        for line in lines:
            tmp_list = line.replace('\n', '').split(' ')
            tmp_list[2] = datetime.strptime(tmp_list[2], "%Y-%m-%d")
            tmp_dict = {}
            for i in range(len(filed_list)):
                tmp_dict[filed_list[i]] = tmp_list[i]
            OeMessageManager.add_oe_community_openEuler_version(pg_url, tmp_dict)


def work(args):
    func_map = {'card': PullMessageFromOeWeb.pull_oe_compatibility_card,
                'commercial_software': PullMessageFromOeWeb.pull_oe_compatibility_commercial_software,
                'cve_database': PullMessageFromOeWeb.pull_oe_compatibility_cve_database,
                'oepkgs': PullMessageFromOeWeb.pull_oe_compatibility_oepkgs,
                'solution':PullMessageFromOeWeb.pull_oe_compatibility_solution,
                'open_source_software': PullMessageFromOeWeb.pull_oe_compatibility_open_source_software,
                'overall_unit': PullMessageFromOeWeb.pull_oe_compatibility_overall_unit,
                'security_notice': PullMessageFromOeWeb.pull_oe_compatibility_security_notice,
                'osv': PullMessageFromOeWeb.pull_oe_compatibility_osv,
                'openeuler_version_message': PullMessageFromOeWeb.oe_openeuler_version_message_handler,
                'organize_message': PullMessageFromOeWeb.oe_organize_message_handler,
                'openeuler_sig': PullMessageFromOeWeb.pull_oe_openeuler_sig}
    prompt_map = {'card': 'openEuler支持的板卡信息',
                  'commercial_software': 'openEuler支持的商业软件',
                  'cve_database': 'openEuler的cve信息',
                  'oepkgs': 'openEuler支持的软件包信息',
                  'solution':'openEuler支持的解决方案',
                  'open_source_software': 'openEuler支持的开源软件信息',
                  'overall_unit': 'openEuler支持的整机信息',
                  'security_notice': 'openEuler官网的安全公告',
                  'osv': 'openEuler相关的osv厂商',
                  'openeuler_version_message': 'openEuler的版本信息',
                  'organize_message': 'openEuler社区成员组织架构',
                  'openeuler_sig': 'openeuler_sig（openEuler SIG组成员信息）'}
    method = args['method']
    pg_host = args['pg_host']
    pg_port = args['pg_port']
    pg_user = args['pg_user']
    pg_pwd = args['pg_pwd']
    pg_database = args['pg_database']
    oepkgs_user = args['oepkgs_user']
    oepkgs_pwd = args['oepkgs_pwd']
    oe_spider_method = args['oe_spider_method']
    if method == 'init_pg_info':
        if pg_host is None or pg_port is None or pg_pwd is None or pg_pwd is None or pg_database is None:
            print('请入完整pg配置信息')
            exit()
        pg_info = {'pg_host': pg_host, 'pg_port': pg_port,
                   'pg_user': pg_user, 'pg_pwd': pg_pwd, 'pg_database': pg_database}
        if not os.path.exists('./config'):
            os.mkdir('./config')
        with open('./config/pg_info.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(pg_info, f)
    elif method == 'init_oepkgs_info':
        if oepkgs_user is None or oepkgs_pwd is None:
            print('请入完整oepkgs配置信息')
            exit()
        oepkgs_info = {'oepkgs_user': oepkgs_user, 'oepkgs_pwd': oepkgs_pwd}
        if not os.path.exists('./config'):
            os.mkdir('./config')
        with open('./config/oepkgs_info.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(oepkgs_info, f)
    elif method == 'update_oe_table':
        if not os.path.exists('./config/pg_info.yaml'):
            print('请先配置postgres数据库信息')
            exit()
        if (oe_spider_method == 'all' or oe_spider_method == 'oepkgs') and not os.path.exists(
                './config/oepkgs_info.yaml'):
            print('请先配置oepkgs用户信息')
            exit()
        pg_info = {}
        try:
            with open('./config/pg_info.yaml', 'r', encoding='utf-8') as f:
                pg_info = yaml.load(f, Loader=SafeLoader)
        except:
            print('postgres数据库配置文件加载失败')
            exit()
        pg_host = pg_info.get('pg_host', '') + ':' + pg_info.get('pg_port', '')
        pg_user = pg_info.get('pg_user', '')
        pg_pwd = pg_info.get('pg_pwd', '')
        pg_database = pg_info.get('pg_database', '')
        pg_url = f'postgresql+psycopg2://{pg_user}:{pg_pwd}@{pg_host}/{pg_database}'
        if oe_spider_method == 'all' or oe_spider_method == 'oepkgs':
            with open('./config/oepkgs_info.yaml', 'r', encoding='utf-8') as f:
                try:
                    oepkgs_info = yaml.load(f, Loader=SafeLoader)
                except:
                    print('oepkgs配置信息读取失败')
                    exit()
        if oe_spider_method == 'all':
            for func in func_map:
                try:
                    if func == 'oepkgs':
                        func_map[func](pg_url, oepkgs_info)
                    else:
                        func_map[func](pg_url)
                    print(prompt_map[func] + '入库成功')
                except Exception as e:
                    print(f'{prompt_map[func]}入库失败由于:{e}')
        else:
            try:
                if oe_spider_method == 'oepkgs':
                    func_map[oe_spider_method](pg_url, oepkgs_info)
                else:
                    func_map[oe_spider_method](pg_url)
                print(prompt_map[oe_spider_method] + '入库成功')
            except Exception as e:
                print(f'{prompt_map[oe_spider_method]}入库失败由于:{e}')


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", type=str, required=True,
                        choices=['init_pg_info', 'init_oepkgs_info', 'update_oe_table'],
                        help='''脚本使用模式，有初始化pg信息、初始化oepkgs账号信息和爬取openEuler官网数据的功能''')
    parser.add_argument("--pg_host", default=None, required=False, help="postres的ip")
    parser.add_argument("--pg_port", default=None, required=False, help="postres的端口")
    parser.add_argument("--pg_user", default=None, required=False, help="postres的用户")
    parser.add_argument("--pg_pwd", default=None, required=False, help="postres的密码")
    parser.add_argument("--pg_database", default=None, required=False, help="postres的数据库")
    parser.add_argument("--oepkgs_user", default=None, required=False, help="语料库所在postres的ip")
    parser.add_argument("--oepkgs_pwd", default=None, required=False, help="语料库所在postres的端口")
    parser.add_argument(
        "--oe_spider_method", default='all', required=False,
        choices=['all', 'card', 'commercial_software', 'cve_database', 'oepkgs','solution','open_source_software',
                 'overall_unit', 'security_notice', 'osv', 'cve_database', 'openeuler_version_message',
                 'organize_message', 'openeuler_sig'],
        help="需要爬取的openEuler数据类型，有all(所有内容)，card（openEuler支持的板卡信息）,commercial_software（openEuler支持的商业软件）,"
             "cve_database（openEuler的cve信息）,oepkgs（openEuler支持的软件包信息）,solution(openEuler支持的解决方案),open_source_software（openEuler支持的开源软件信息）,"
             "overall_unit（openEuler支持的整机信息）,security_notice（openEuler官网的安全公告）,osv（openEuler相关的osv厂商）,"
             "cve_database（openEuler的cve漏洞）,openeuler_version_message（openEuler的版本信息）,"
             "organize_message（openEuler社区成员组织架构）,openeuler_sig（openEuler SIG组成员信息）")
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = init_args()
    work(vars(args))
