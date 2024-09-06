# Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import os
import random
import copy

from chat2DB.logger import get_logger


class Node:
    def __init__(self, dep, pre_id):
        self.dep = dep
        self.pre_id = pre_id
        self.pre_nearest_children_id = {}
        self.children_id = {}
        self.data_frame = None


class Dict_tree:
    def __init__(self, data_dict):
        self.logger = get_logger()
        self.root = 0
        self.node_list = [Node(0, -1)]
        for key in data_dict:
            self.insert_data(key, data_dict[key])
        self.init_pre()

    def insert_data(self, keyword, data_frame):
        if len(keyword) == 0:
            return
        node_index = self.root
        try:
            for i in range(len(keyword)):
                if keyword[i] not in self.node_list[node_index].children_id.keys():
                    self.node_list.append(Node(self.node_list[node_index].dep+1, node_index))
                    self.node_list[node_index].children_id[keyword[i]] = len(self.node_list)-1
                node_index = self.node_list[node_index].children_id[keyword[i]]
        except Exception as e:
            self.logger(f'关键字插入失败由于：{e}')
            return
        self.node_list[node_index].data_frame = data_frame

    def init_pre(self):
        q = [self.root]
        self.node_list[self.root].pre_nearest_children_id = self.node_list[self.root].children_id.copy()
        l = 0
        r = 1
        try:
            while l < r:
                node_index = q[l]
                l += 1
                for key, val in self.node_list[node_index].children_id.items():
                    q.append(val)
                    r += 1
                    if key in self.node_list[node_index].pre_nearest_children_id.keys():
                        pre_id = self.node_list[node_index].pre_nearest_children_id[key]
                        self.node_list[val].pre_id = pre_id
                        self.node_list[val].pre_nearest_children_id = self.node_list[pre_id].pre_nearest_children_id.copy()
                    else:
                        self.node_list[val].pre_id = 0
                    for ckey, cval in self.node_list[val].children_id.items():
                        self.node_list[val].pre_nearest_children_id[ckey] = cval
        except Exception as e:
            self.logger(f'字典树前缀构建失败由于：{e}')
            return

    def get_results(self, content: str):
        content = content.lower()
        pre_node_index = self.root
        nex_node_index = None
        results = []
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
            if self.node_list[pre_node_index].data_frame is not None:
                results.extend(copy.deepcopy(self.node_list[pre_node_index].data_frame))
        except Exception as e:
            self.logger(f'结果获取失败由于：{e}')
        return results
