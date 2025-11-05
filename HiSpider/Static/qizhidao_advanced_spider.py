"""
企知道网站爬虫 - 高级版本
包含反爬虫机制、请求重试、随机延迟等功能
"""

import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime
import time
import random
import re
from fake_useragent import UserAgent


class QizhidaoAdvancedSpider:
    """企知道网站高级爬虫"""
    
    def __init__(self, url=None, max_retries=3, delay_range=(1, 3)):
        """
        初始化爬虫
        
        Args:
            url: 目标URL
            max_retries: 最大重试次数
            delay_range: 延迟时间范围（秒）
        """
        self.url = url or "https://qiye.qizhidao.com/batch-query-home"
        self.max_retries = max_retries
        self.delay_range = delay_range
        self.session = requests.Session()
        self.ua = UserAgent()
        self.companies_data = []
        
    def get_random_headers(self):
        """获取随机请求头"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://qiye.qizhidao.com/'
        }
    
    def random_delay(self):
        """随机延迟"""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
    
    def fetch_page(self, retry_count=0):
        """获取页面内容（带重试机制）"""
        try:
            headers = self.get_random_headers()
            
            # 随机延迟
            self.random_delay()
            
            response = self.session.get(
                self.url, 
                headers=headers, 
                timeout=30,
                allow_redirects=True
            )
            
            response.raise_for_status()
            
            # 检测是否包含验证码或人机校验
            if self.detect_captcha(response.text):
                print("警告: 检测到验证码或人机校验，可能需要手动处理")
            
            response.encoding = 'utf-8'
            return response.text
            
        except requests.exceptions.Timeout:
            if retry_count < self.max_retries:
                print(f"请求超时，正在重试 ({retry_count + 1}/{self.max_retries})...")
                time.sleep(2 ** retry_count)  # 指数退避
                return self.fetch_page(retry_count + 1)
            else:
                print("请求超时，已达到最大重试次数")
                return None
                
        except requests.exceptions.HTTPError as e:
            if retry_count < self.max_retries and e.response.status_code in [429, 503, 502]:
                print(f"HTTP错误 {e.response.status_code}，正在重试 ({retry_count + 1}/{self.max_retries})...")
                time.sleep(2 ** retry_count)
                return self.fetch_page(retry_count + 1)
            else:
                print(f"HTTP错误: {e}")
                return None
                
        except requests.RequestException as e:
            if retry_count < self.max_retries:
                print(f"请求失败: {e}，正在重试 ({retry_count + 1}/{self.max_retries})...")
                time.sleep(2 ** retry_count)
                return self.fetch_page(retry_count + 1)
            else:
                print(f"获取页面失败: {e}")
                return None
    
    def detect_captcha(self, html_content):
        """检测页面中是否包含验证码"""
        captcha_keywords = [
            '验证码', 'captcha', '人机校验', 'verify', 
            '安全验证', '滑动验证', '点击验证'
        ]
        html_lower = html_content.lower()
        return any(keyword in html_content or keyword.lower() in html_lower 
                  for keyword in captcha_keywords)
    
    def parse_page(self, html_content):
        """解析页面内容，提取企业信息"""
        if not html_content:
            return None
        
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 提取页面标题
        title = soup.find('title')
        title_text = title.text.strip() if title else "企知道"
        
        # 多种方式查找表格
        table = None
        
        # 方式1: 直接查找table标签
        table = soup.find('table')
        
        # 方式2: 查找包含表格的容器
        if not table:
            containers = soup.find_all(['div', 'section'], class_=re.compile(r'table|list|data|result', re.I))
            for container in containers:
                table = container.find('table')
                if table:
                    break
        
        # 方式3: 查找特定的表格ID或类名
        if not table:
            table = soup.find('table', id=re.compile(r'table|data|list|result', re.I))
        
        if not table:
            table = soup.find('table', class_=re.compile(r'table|data|list|result', re.I))
        
        if not table:
            print("未找到企业信息表格，尝试其他解析方式...")
            # 尝试从列表或其他结构中提取
            return self.parse_alternative_structure(soup)
        
        # 提取表头
        headers = []
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # 如果没有表头，尝试从第一行获取
        if not headers:
            first_row = table.find('tr')
            if first_row:
                first_cells = first_row.find_all(['th', 'td'])
                # 检查第一行是否是表头（通常包含特定关键词）
                header_keywords = ['序号', '名称', '企业', '状态', '代码', '法人', '日期', '资本']
                first_row_text = first_row.get_text()
                if any(keyword in first_row_text for keyword in header_keywords):
                    headers = [cell.get_text(strip=True) for cell in first_cells]
        
        # 提取数据行
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        
        for idx, row in enumerate(rows):
            # 跳过表头行
            if idx == 0 and headers and len(headers) > 0:
                row_text = row.get_text()
                if any(keyword in row_text for keyword in ['序号', '名称', '企业']):
                    continue
            
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:  # 跳过空行
                continue
            
            company_data = {}
            
            # 如果已有表头，按表头提取数据
            if headers:
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        value = cell.get_text(strip=True)
                        if value:  # 只保存非空值
                            company_data[headers[i]] = value
                        
                        # 提取链接
                        link = cell.find('a')
                        if link:
                            href = link.get('href')
                            if href:
                                # 处理相对URL
                                if href.startswith('/'):
                                    href = f"https://qiye.qizhidao.com{href}"
                                elif not href.startswith('http'):
                                    href = f"https://qiye.qizhidao.com/{href}"
                                company_data[f"{headers[i]}_链接"] = href
            else:
                # 如果没有表头，使用默认字段名
                default_headers = ['序号', '企业名称', '登记状态', '统一社会信用代码', 
                                 '法定代表人', '成立日期', '注册资本', '实缴资本']
                for i, cell in enumerate(cells):
                    if i < len(default_headers):
                        value = cell.get_text(strip=True)
                        if value:
                            company_data[default_headers[i]] = value
                        
                        link = cell.find('a')
                        if link and link.get('href'):
                            href = link.get('href')
                            if href.startswith('/'):
                                href = f"https://qiye.qizhidao.com{href}"
                            elif not href.startswith('http'):
                                href = f"https://qiye.qizhidao.com/{href}"
                            company_data[f"{default_headers[i]}_链接"] = href
            
            if company_data:
                self.companies_data.append(company_data)
        
        # 提取总数信息
        total_results = len(self.companies_data)
        
        # 查找可能的总数提示
        total_patterns = [
            re.compile(r'共[:\s]*(\d+)', re.I),
            re.compile(r'总计[:\s]*(\d+)', re.I),
            re.compile(r'总数[:\s]*(\d+)', re.I),
            re.compile(r'共找到[:\s]*(\d+)', re.I),
            re.compile(r'(\d+)[:\s]*条记录', re.I),
            re.compile(r'(\d+)[:\s]*家企业', re.I),
        ]
        
        page_text = soup.get_text()
        for pattern in total_patterns:
            match = pattern.search(page_text)
            if match:
                total_results = int(match.group(1))
                break
        
        return {
            'title': title_text,
            'total_results': total_results,
            'companies': self.companies_data
        }
    
    def parse_alternative_structure(self, soup):
        """尝试从非表格结构中提取数据"""
        print("尝试从列表或其他结构中提取数据...")
        # 这里可以根据实际页面结构实现其他解析方式
        # 例如从div列表、JSON数据等提取
        return None
    
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
        print("=" * 50)
        print("企知道网站高级爬虫 - 开始运行")
        print("=" * 50)
        print(f"目标URL: {self.url}")
        print(f"最大重试次数: {self.max_retries}")
        print(f"延迟范围: {self.delay_range}秒")
        print()
        
        # 获取页面
        print("正在获取页面...")
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
        print(f"页面显示总数: {data['total_results']} 条")
        
        # 保存数据
        files = []
        if save_json:
            print("\n正在保存JSON文件...")
            json_file = self.save_to_json(data)
            if json_file:
                files.append(json_file)
        
        if save_excel:
            print("正在保存Excel文件...")
            excel_file = self.save_to_excel(data)
            if excel_file:
                files.append(excel_file)
        
        return {
            'data': data,
            'files': files
        }


def main():
    """主函数"""
    spider = QizhidaoAdvancedSpider()
    result = spider.run()
    
    if result:
        print("\n" + "=" * 50)
        print("爬取完成！")
        print("=" * 50)
        print(f"提取了 {len(result['data']['companies'])} 条企业信息")
        print(f"生成文件: {', '.join(result['files'])}")
    else:
        print("\n爬取失败，请检查网络连接和URL是否正确")


if __name__ == "__main__":
    main()

