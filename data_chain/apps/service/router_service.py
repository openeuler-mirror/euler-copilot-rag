# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
from fastapi import FastAPI, Request, Depends
from fastapi.routing import APIRoute


def get_route_info(request: Request):
    route = request.scope.get("route")
    if isinstance(route, APIRoute):
        request_method = request.method
        route_path = route.path
        return request_method+' '+route_path
    return ''
