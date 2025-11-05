"""
企知道网站爬虫 - 基础版本
适用于简单的数据爬取场景
"""

import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime
import time
import os


class QizhidaoSpider:
    """企知道网站基础爬虫"""
    
    def __init__(self, url=None):
        """
        初始化爬虫
        
        Args:
            url: 目标URL，默认为企知道批量查询结果页面
        """
        self.url = url or "https://qiye.qizhidao.com/batch-query-home"
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.companies_data = []
        
    def fetch_page(self):
        """获取页面内容"""
        try:
            response = self.session.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            print(f"获取页面失败: {e}")
            return None
    
    def parse_page(self, html_content):
        """解析页面内容，提取企业信息"""
        if not html_content:
            return None
        
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 提取页面标题
        title = soup.find('title')
        title_text = title.text.strip() if title else "企知道"
        
        # 查找企业信息表格
        table = soup.find('table')
        if not table:
            # 尝试查找其他可能的表格容器
            table = soup.find('div', class_='table-container')
            if table:
                table = table.find('table')
        
        if not table:
            print("未找到企业信息表格")
            return None
        
        # 提取表头
        headers = []
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # 提取数据行
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:  # 跳过表头或空行
                continue
            
            company_data = {}
            
            # 如果已有表头，按表头提取数据
            if headers:
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        company_data[headers[i]] = cell.get_text(strip=True)
                        
                        # 提取链接
                        link = cell.find('a')
                        if link and link.get('href'):
                            company_data[f"{headers[i]}_链接"] = link.get('href')
            else:
                # 如果没有表头，使用默认字段名
                default_headers = ['序号', '企业名称', '登记状态', '统一社会信用代码', 
                                 '法定代表人', '成立日期', '注册资本', '实缴资本']
                for i, cell in enumerate(cells):
                    if i < len(default_headers):
                        company_data[default_headers[i]] = cell.get_text(strip=True)
            
            if company_data:
                self.companies_data.append(company_data)
        
        # 提取总数信息
        total_results = len(self.companies_data)
        
        # 查找可能的总数提示
        total_elements = soup.find_all(text=lambda text: text and ('共' in text or '总计' in text or '总数' in text))
        for elem in total_elements:
            import re
            numbers = re.findall(r'\d+', elem)
            if numbers:
                total_results = int(numbers[0])
                break
        
        return {
            'title': title_text,
            'total_results': total_results,
            'companies': self.companies_data
        }
    
    def save_to_json(self, data, filename=None):
        """保存数据到JSON文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"qizhidao_data_{timestamp}.json"
        
        output_data = {
            'metadata': {
                'title': data.get('title', '企知道'),
                'total_results': data.get('total_results', len(data.get('companies', []))),
                'url': self.url,
                'crawl_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            'companies': data.get('companies', []),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"数据已保存到: {filename}")
        return filename
    
    def save_to_excel(self, data, filename=None):
        """保存数据到Excel文件"""
        if not data.get('companies'):
            print("没有数据可保存")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"qizhidao_data_{timestamp}.xlsx"
        
        df = pd.DataFrame(data['companies'])
        df.to_excel(filename, index=False, engine='openpyxl')
        
        print(f"数据已保存到: {filename}")
        return filename
    
    def run(self, save_json=True, save_excel=True):
        """运行爬虫"""
        print("开始爬取企知道网站数据...")
        print(f"目标URL: {self.url}")
        
        # 获取页面
        html_content = self.fetch_page()
        if not html_content:
            print("无法获取页面内容")
            return None
        
        # 解析页面
        print("正在解析页面...")
        data = self.parse_page(html_content)
        if not data:
            print("页面解析失败")
            return None
        
        print(f"成功提取 {len(data['companies'])} 条企业信息")
        
        # 保存数据
        files = []
        if save_json:
            json_file = self.save_to_json(data)
            if json_file:
                files.append(json_file)
        
        if save_excel:
            excel_file = self.save_to_excel(data)
            if excel_file:
                files.append(excel_file)
        
        return {
            'data': data,
            'files': files
        }


def main():
    """主函数"""
    spider = QizhidaoSpider()
    result = spider.run()
    
    if result:
        print("\n爬取完成！")
        print(f"提取了 {len(result['data']['companies'])} 条企业信息")
        print(f"生成文件: {', '.join(result['files'])}")
    else:
        print("\n爬取失败，请检查网络连接和URL是否正确")


if __name__ == "__main__":
    main()

