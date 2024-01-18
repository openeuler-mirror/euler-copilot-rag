# 导入 requests 包
import os

from rag_service.original_document_fetchers.assets_collector.utils.browser_util import get_browser

# 配置代理
os.environ['http_proxy'] = 'http://**:**.@proxyhk.huawei.com:8080'
os.environ['https_proxy'] = 'http://**:**.@proxyhk.huawei.com:8080'
os.environ['no_proxy'] = '127.0.0.1,localhost'

browser = get_browser()

browser.get('https://www.hiascend.com/document/detail/zh/mindstudio/60RC2/quickstart/migrationtoolms_000003.html')
browser.implicitly_wait(3)
browser.save_screenshot('test_screenshot.png')
browser.quit()
