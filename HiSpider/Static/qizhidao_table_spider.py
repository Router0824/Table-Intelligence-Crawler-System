"""
企知道网站爬虫 - 表格数据版本
专门针对表格结构优化的爬虫，支持分页功能
"""

import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime
import time
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode


class QizhidaoTableSpider:
    """企知道网站表格数据爬虫（支持分页）"""
    
    def __init__(self, url=None, max_pages=None):
        """
        初始化爬虫
        
        Args:
            url: 目标URL
            max_pages: 最大爬取页数，None表示爬取所有页
        """
        self.base_url = url or "https://qiye.qizhidao.com/batch-query-home"
        self.url = self.base_url
        self.max_pages = max_pages
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://qiye.qizhidao.com/'
        }
        self.companies_data = []
        self.current_page = 1
        self.total_pages = None
        
    def fetch_page(self, page_url=None):
        """获取页面内容"""
        url = page_url or self.url
        try:
            response = self.session.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            print(f"获取页面失败: {e}")
            return None
    
    def get_total_pages(self, soup):
        """从页面中提取总页数"""
        if self.total_pages:
            return self.total_pages
        
        # 查找分页元素
        pagination = soup.find('ul', class_=re.compile(r'pagination|page', re.I))
        if not pagination:
            pagination = soup.find('div', class_=re.compile(r'pagination|page', re.I))
        
        if pagination:
            # 查找所有页码元素
            page_numbers = pagination.find_all('li', class_='number')
            if page_numbers:
                # 获取最大的页码
                max_page = 0
                for page_li in page_numbers:
                    page_text = page_li.get_text(strip=True)
                    try:
                        page_num = int(page_text)
                        max_page = max(max_page, page_num)
                    except ValueError:
                        pass
                if max_page > 0:
                    self.total_pages = max_page
                    return max_page
            
            # 尝试从文本中提取总页数
            pagination_text = pagination.get_text()
            page_patterns = [
                re.compile(r'共\s*(\d+)\s*页', re.I),
                re.compile(r'(\d+)\s*页', re.I),
                re.compile(r'页\s*(\d+)', re.I),
            ]
            for pattern in page_patterns:
                match = pattern.search(pagination_text)
                if match:
                    self.total_pages = int(match.group(1))
                    return self.total_pages
        
        # 如果找不到分页信息，默认返回1
        return 1
    
    def get_page_url(self, page_number):
        """构建指定页面的URL"""
        # 如果URL中包含page参数，直接替换
        parsed_url = urlparse(self.base_url)
        query_params = parse_qs(parsed_url.query)
        
        # 更新或添加page参数
        query_params['page'] = [str(page_number)]
        
        # 重新构建URL
        new_query = urlencode(query_params, doseq=True)
        new_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}"
        
        return new_url
    
    def find_next_page_link(self, soup):
        """查找下一页链接"""
        # 方法1: 查找分页中的下一页按钮或链接
        pagination = soup.find('ul', class_=re.compile(r'pagination|page', re.I))
        if not pagination:
            pagination = soup.find('div', class_=re.compile(r'pagination|page', re.I))
        
        if pagination:
            # 查找当前页的下一个number元素
            current_page_li = None
            for li in pagination.find_all('li', class_='number'):
                if 'active' in li.get('class', []) or 'current' in li.get('class', []):
                    current_page_li = li
                    break
            
            if current_page_li:
                # 查找下一个number元素
                next_li = current_page_li.find_next_sibling('li', class_='number')
                if next_li:
                    link = next_li.find('a')
                    if link and link.get('href'):
                        return urljoin(self.base_url, link.get('href'))
            
            # 查找下一页按钮
            next_btn = pagination.find('a', class_=re.compile(r'next', re.I))
            if next_btn and next_btn.get('href'):
                return urljoin(self.base_url, next_btn.get('href'))
            
            # 查找包含数字的链接
            for li in pagination.find_all('li', class_='number'):
                link = li.find('a')
                if link:
                    page_text = link.get_text(strip=True)
                    try:
                        page_num = int(page_text)
                        if page_num == self.current_page + 1:
                            href = link.get('href')
                            if href:
                                return urljoin(self.base_url, href)
                    except ValueError:
                        pass
        
        return None
    
    def parse_table_data(self, soup):
        """解析表格数据"""
        # 查找企业信息表格
        table = soup.find('table')
        if not table:
            table = soup.find('div', class_='table-container')
            if table:
                table = table.find('table')
        
        if not table:
            return []
        
        # 提取表头
        headers = []
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # 如果没有表头，使用默认字段名
        if not headers:
            headers = ['序号', '企业名称', '登记状态', '统一社会信用代码', 
                      '法定代表人', '成立日期', '注册资本', '实缴资本']
        
        # 提取数据行
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        
        rows = tbody.find_all('tr')
        page_data = []
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            
            # 跳过表头行
            row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
            if any(keyword in row_text for keyword in ['序号', '名称', '企业']):
                if len(headers) == len(cells):
                    continue
            
            company_data = {}
            
            for i, cell in enumerate(cells):
                if i < len(headers):
                    value = cell.get_text(strip=True)
                    if value:
                        company_data[headers[i]] = value
                    
                    # 提取链接
                    link = cell.find('a')
                    if link and link.get('href'):
                        href = link.get('href')
                        if href.startswith('/'):
                            href = urljoin(self.base_url, href)
                        elif not href.startswith('http'):
                            href = urljoin(self.base_url, href)
                        company_data[f"{headers[i]}_链接"] = href
            
            if company_data:
                company_data['页码'] = self.current_page
                page_data.append(company_data)
        
        return page_data
    
    def parse_page(self, html_content):
        """解析页面内容"""
        if not html_content:
            return None
        
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 提取页面标题
        title = soup.find('title')
        title_text = title.text.strip() if title else "企知道"
        
        # 提取表格数据
        page_data = self.parse_table_data(soup)
        
        # 获取总页数
        total_pages = self.get_total_pages(soup)
        
        # 提取总数信息
        total_results = len(self.companies_data) + len(page_data)
        
        total_patterns = [
            re.compile(r'共[:\s]*(\d+)', re.I),
            re.compile(r'总计[:\s]*(\d+)', re.I),
            re.compile(r'总数[:\s]*(\d+)', re.I),
            re.compile(r'共找到[:\s]*(\d+)', re.I),
        ]
        
        page_text = soup.get_text()
        for pattern in total_patterns:
            match = pattern.search(page_text)
            if match:
                total_results = int(match.group(1))
                break
        
        return {
            'title': title_text,
            'total_pages': total_pages,
            'current_page': self.current_page,
            'total_results': total_results,
            'page_data': page_data
        }
    
    def crawl_all_pages(self):
        """爬取所有页面"""
        print("=" * 50)
        print("企知道网站表格数据爬虫 - 开始运行")
        print("=" * 50)
        print(f"基础URL: {self.base_url}")
        print()
        
        while True:
            print(f"正在爬取第 {self.current_page} 页...")
            
            # 获取当前页URL
            page_url = self.get_page_url(self.current_page)
            
            # 获取页面
            html_content = self.fetch_page(page_url)
            if not html_content:
                print(f"无法获取第 {self.current_page} 页内容")
                break
            
            # 解析页面
            data = self.parse_page(html_content)
            if not data:
                print(f"第 {self.current_page} 页解析失败")
                break
            
            # 添加当前页数据
            self.companies_data.extend(data['page_data'])
            print(f"第 {self.current_page} 页提取了 {len(data['page_data'])} 条企业信息")
            
            # 更新总页数
            if data.get('total_pages'):
                self.total_pages = data['total_pages']
            
            # 检查是否还有下一页
            if self.max_pages and self.current_page >= self.max_pages:
                print(f"已达到最大页数限制: {self.max_pages}")
                break
            
            if self.total_pages and self.current_page >= self.total_pages:
                print(f"已爬取所有页面 (共 {self.total_pages} 页)")
                break
            
            # 检查是否有数据
            if not data['page_data']:
                print("当前页无数据，停止爬取")
                break
            
            # 准备下一页
            self.current_page += 1
            time.sleep(1)  # 避免请求过快
        
        print(f"\n总共提取了 {len(self.companies_data)} 条企业信息")
        return {
            'title': data.get('title', '企知道') if 'data' in locals() else '企知道',
            'total_results': len(self.companies_data),
            'total_pages': self.current_page - 1,
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
                'total_pages': data.get('total_pages', 1),
                'url': self.base_url,
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
        # 爬取所有页面
        data = self.crawl_all_pages()
        
        if not data or not data.get('companies'):
            print("没有获取到数据")
            return None
        
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
    spider = QizhidaoTableSpider(max_pages=None)  # None表示爬取所有页
    result = spider.run()
    
    if result:
        print("\n" + "=" * 50)
        print("爬取完成！")
        print("=" * 50)
        print(f"提取了 {len(result['data']['companies'])} 条企业信息")
        print(f"爬取了 {result['data'].get('total_pages', 1)} 页")
        print(f"生成文件: {', '.join(result['files'])}")
    else:
        print("\n爬取失败，请检查网络连接和URL是否正确")


if __name__ == "__main__":
    main()

