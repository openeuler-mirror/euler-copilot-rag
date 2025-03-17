# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import copy
import logging


class Node:
    def __init__(self, dep, pre_id):
        self.dep = dep
        self.pre_id = pre_id
        self.pre_nearest_children_id = {}
        self.children_id = {}
        self.data_frame = None


logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')


class DictTree:
    def __init__(self):
        self.root = 0
        self.node_list = [Node(0, -1)]

    def load_data(self, data_dict):
        for key in data_dict:
            self.insert_data(key, data_dict[key])
        self.init_pre()

    def insert_data(self, keyword, data_frame):
        if not isinstance(keyword,str):
            return
        if len(keyword) == 0:
            return
        node_index = self.root
        try:
            for i in range(len(keyword)):
                if keyword[i] not in self.node_list[node_index].children_id.keys():
                    self.node_list.append(Node(self.node_list[node_index].dep+1, 0))
                    self.node_list[node_index].children_id[keyword[i]] = len(self.node_list)-1
                node_index = self.node_list[node_index].children_id[keyword[i]]
        except Exception as e:
            logging.error(f'关键字插入失败由于：{e}')
            return
        self.node_list[node_index].data_frame = data_frame

    def init_pre(self):
        q = [self.root]
        l = 0
        r = 1
        try:
            while l < r:
                node_index = q[l]
                self.node_list[node_index].pre_nearest_children_id = self.node_list[self.node_list[node_index].pre_id].children_id.copy()
                l += 1
                for key, val in self.node_list[node_index].children_id.items():
                    q.append(val)
                    r += 1
                    if key in self.node_list[node_index].pre_nearest_children_id.keys():
                        pre_id = self.node_list[node_index].pre_nearest_children_id[key]
                        self.node_list[val].pre_id = pre_id
                    self.node_list[node_index].pre_nearest_children_id[key] = val
        except Exception as e:
            logging.error(f'字典树前缀构建失败由于：{e}')
            return

    def get_results(self, content: str):
        content = content.lower()
        pre_node_index = self.root
        nex_node_index = None
        results = []
        logging.info(f'当前问题{content}')
        try:
            for i in range(len(content)):
                if content[i] in self.node_list[pre_node_index].pre_nearest_children_id.keys():
                    nex_node_index = self.node_list[pre_node_index].pre_nearest_children_id[content[i]]
                else:
                    nex_node_index = 0
                if self.node_list[pre_node_index].dep >= self.node_list[nex_node_index].dep:
                    if self.node_list[pre_node_index].data_frame is not None:
                        results.extend(copy.deepcopy(self.node_list[pre_node_index].data_frame))
                pre_node_index = nex_node_index
                logging.info(f'当前深度{self.node_list[pre_node_index].dep}')
            if self.node_list[pre_node_index].data_frame is not None:
                results.extend(copy.deepcopy(self.node_list[pre_node_index].data_frame))
        except Exception as e:
            logging.error(f'结果获取失败由于：{e}')
        return results
