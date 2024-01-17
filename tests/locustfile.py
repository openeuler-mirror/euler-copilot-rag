from locust import HttpUser, task, between

class ApiUser(HttpUser):
    host = "https://rag.test.osinfra.cn"  # 设置基础主机地址
    wait_time = between(1, 5)  # 用户执行任务之间的等待时间

    @task
    def query_api(self):
        endpoint = "/kb/get_stream_answer"  # API端点
        headers = {
            "Content-Type": "application/json",
            "Cookie": "HWWAFSESID=bd9b3735ee7c0fe814; HWWAFSESTIME=1701779051564"
        }
        payload = {
            "question": "aops-ceres介绍",
            "kb_sn": "Openeuler_80760377",
            "fetch_source": True
        }
        self.client.post(endpoint, json=payload, headers=headers)
