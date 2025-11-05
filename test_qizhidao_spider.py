"""
企知道爬虫测试脚本
用于测试各个版本的爬虫功能
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'HiSpider', 'Static'))

from qizhidao_spider import QizhidaoSpider
from qizhidao_advanced_spider import QizhidaoAdvancedSpider
from qizhidao_table_spider import QizhidaoTableSpider
from qizhidao_smart_spider import QizhidaoSmartSpider


def test_basic_spider():
    """测试基础版本爬虫"""
    print("\n" + "=" * 50)
    print("测试基础版本爬虫")
    print("=" * 50)
    spider = QizhidaoSpider()
    result = spider.run(save_json=True, save_excel=False)
    return result


def test_advanced_spider():
    """测试高级版本爬虫"""
    print("\n" + "=" * 50)
    print("测试高级版本爬虫")
    print("=" * 50)
    spider = QizhidaoAdvancedSpider()
    result = spider.run(save_json=True, save_excel=False)
    return result


def test_table_spider():
    """测试表格数据爬虫"""
    print("\n" + "=" * 50)
    print("测试表格数据爬虫（支持分页）")
    print("=" * 50)
    spider = QizhidaoTableSpider(max_pages=2)  # 只测试前2页
    result = spider.run(save_json=True, save_excel=False)
    return result


def test_smart_spider():
    """测试智能爬虫"""
    print("\n" + "=" * 50)
    print("测试智能爬虫（Selenium，支持分页和验证码）")
    print("=" * 50)
    print("注意：智能爬虫需要Chrome浏览器和ChromeDriver")
    spider = QizhidaoSmartSpider(headless=False)
    result = spider.run(save_json=True, save_excel=False)
    return result


def main():
    """主测试函数"""
    print("企知道爬虫测试脚本")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        if test_name == 'basic':
            test_basic_spider()
        elif test_name == 'advanced':
            test_advanced_spider()
        elif test_name == 'table':
            test_table_spider()
        elif test_name == 'smart':
            test_smart_spider()
        else:
            print(f"未知的测试类型: {test_name}")
            print("可用选项: basic, advanced, table, smart")
    else:
        print("请选择要测试的爬虫版本:")
        print("1. 基础版本 (basic)")
        print("2. 高级版本 (advanced)")
        print("3. 表格数据版本 (table)")
        print("4. 智能版本 (smart)")
        print("\n使用方法: python test_qizhidao_spider.py [版本名称]")
        print("例如: python test_qizhidao_spider.py table")


if __name__ == "__main__":
    main()

