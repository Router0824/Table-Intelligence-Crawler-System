"""
企知道网站爬虫 - 智能版本
使用Selenium处理JavaScript渲染、验证码和人机校验
支持自动翻页功能
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime
import time
import random
import re
import os


class QizhidaoSmartSpider:
    """企知道网站智能爬虫（使用Selenium）"""
    
    def __init__(self, url=None, headless=False, implicit_wait=10, interactive=False):
        """
        初始化爬虫
        
        Args:
            url: 目标URL（可以是首页或结果页URL）
            headless: 是否使用无头模式
            implicit_wait: 隐式等待时间（秒）
            interactive: 是否使用交互模式（等待用户准备好后开始）
        """
        self.base_url = url or "https://qiye.qizhidao.com/batch-query-home"
        self.url = self.base_url
        self.headless = headless
        self.implicit_wait = implicit_wait
        self.interactive = interactive
        self.driver = None
        self.companies_data = []
        self.current_page = 1
        self.total_pages = None
        self.crawled_pages = set()  # 记录已爬取的页码，避免重复
        # 缓存机制：减少重复查找
        self._pagination_cache = None  # 缓存分页元素
        self._table_cache = None  # 缓存表格元素
        self._debug_mode = False  # 调试模式开关，默认关闭以提升速度
        
    def init_driver(self):
        """初始化WebDriver"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # 反爬虫设置
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        
        # 用户代理
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        # 其他设置
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(self.implicit_wait)
            self.driver.maximize_window()
            
            # 移除webdriver特征
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            print("WebDriver初始化成功", flush=True)
            return True
        except Exception as e:
            print(f"WebDriver初始化失败: {e}", flush=True)
            print("请确保已安装Chrome浏览器和ChromeDriver", flush=True)
            return False
    
    def human_like_delay(self):
        """模拟人类行为的延迟"""
        delay = random.uniform(1, 3)
        time.sleep(delay)
    
    def is_result_page(self, url=None):
        """
        判断是否在结果页面（而非登录页面的redirect参数）
        
        Args:
            url: 要检查的URL，如果为None则使用当前页面URL
            
        Returns:
            bool: 如果URL真正指向结果页面返回True，否则返回False
        """
        if url is None:
            try:
                url = self.driver.current_url
            except:
                return False
        
        url_lower = url.lower()
        
        # 排除登录页面（即使redirect参数包含batch-query-result）
        if 'login' in url_lower or 'www.qizhidao.com/login' in url_lower:
            return False
        
        # 真正的结果页面URL应该包含batch-query-result在路径中
        # 例如: https://qiye.qizhidao.com/batch-query-result?matchId=...
        if 'qiye.qizhidao.com/batch-query-result' in url_lower:
            return True
        
        # 或者URL路径部分包含batch-query-result
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path.lower()
            if 'batch-query-result' in path:
                return True
        except:
            pass
        
        return False
    
    def scroll_page(self, minimal=True):
        """模拟人类滚动页面（优化：减少滚动次数）"""
        try:
            if minimal:
                # 最小化滚动：只滚动到底部然后回顶部（触发懒加载）
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.3)  # 减少等待时间
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.2)
            else:
                # 完整滚动（仅在必要时使用）
                scroll_height = self.driver.execute_script("return document.body.scrollHeight")
                for i in range(2):  # 减少滚动次数：从3次改为2次
                    scroll_to = random.randint(0, scroll_height)
                    self.driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                    time.sleep(random.uniform(0.3, 0.8))  # 减少等待时间
                
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)  # 减少等待时间
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.3)  # 减少等待时间
        except Exception as e:
            if self._debug_mode:
                print(f"滚动页面时出错: {e}")
    
    def detect_captcha(self):
        """检测页面中是否包含验证码"""
        captcha_keywords = [
            '验证码', 'captcha', '人机校验', 'verify', 
            '安全验证', '滑动验证', '点击验证', 'geetest'
        ]
        
        try:
            # 先检查URL，如果在结果页面，通常不会有验证码
            if self.is_result_page():
                # 在结果页面，通常验证码已经解决，但还是检查一下
                pass
            
            page_source = self.driver.page_source.lower()
            
            # 检查关键词
            found_keyword = False
            for keyword in captcha_keywords:
                if keyword.lower() in page_source:
                    # 但要排除页面上可能包含这些词汇但不是验证码的情况
                    # 如果页面已经显示了数据表格，可能不是验证码
                    if 'table' in page_source or '企业' in page_source:
                        # 如果页面有数据，可能是误判，再检查一下元素
                        found_keyword = True
                        break
            
            # 如果没找到关键词，直接返回False
            if not found_keyword:
                # 但还是检查一下元素
                pass
            else:
                # 找到了关键词，检查元素确认
                pass
            
            # 查找常见的验证码元素
            captcha_selectors = [
                'div[id*="captcha"]',
                'div[class*="captcha"]',
                'div[id*="verify"]',
                'div[class*="verify"]',
                'iframe[src*="captcha"]',
                'iframe[src*="geetest"]'
            ]
            
            for selector in captcha_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            # 检查元素大小，很小的可能是隐藏的
                            size = element.size
                            if size['height'] > 50 and size['width'] > 50:
                                return True
                except:
                    continue
            
            # 如果没有明显可见的验证码元素，且页面有数据内容，返回False
            if 'table' in page_source or '企业名称' in self.driver.page_source:
                return False
            
            return False if not found_keyword else True
        except Exception as e:
            print(f"[调试] 验证码检测异常: {e}")
            return False
    
    def wait_for_captcha_solve(self, timeout=300):
        """等待用户手动解决验证码"""
        print("\n" + "=" * 50)
        print("检测到验证码或人机校验")
        print("=" * 50)
        print("请在浏览器中完成验证码验证")
        print(f"等待时间: {timeout} 秒")
        print("提示：完成验证后，程序会自动检测并继续运行")
        print("=" * 50 + "\n")
        
        start_time = time.time()
        check_count = 0
        no_captcha_count = 0  # 连续检测到无验证码的次数
        
        while time.time() - start_time < timeout:
            try:
                # 检查driver是否仍然有效
                try:
                    current_url = self.driver.current_url
                except Exception as e:
                    print(f"浏览器会话检查失败: {e}")
                    # 尝试重新加载页面
                    try:
                        self.driver.get(self.base_url)
                        time.sleep(2)
                        print("已重新加载页面")
                    except:
                        print("无法重新加载页面")
                        time.sleep(2)
                        continue
                
                # 检测验证码是否已解决
                has_captcha = self.detect_captcha()
                
                if not has_captcha:
                    no_captcha_count += 1
                    # 连续3次检测都无验证码，认为已解决
                    if no_captcha_count >= 3:
                        print("\n✓ 验证码已解决，等待页面稳定...")
                        time.sleep(3)  # 等待页面稳定
                        # 再次确认页面已加载
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                        except:
                            pass
                        print("✓ 页面已稳定，继续爬取...")
                        return True
                else:
                    # 如果又检测到验证码，重置计数
                    no_captcha_count = 0
                
                check_count += 1
                if check_count % 5 == 0:  # 每10秒显示一次进度
                    elapsed = int(time.time() - start_time)
                    remaining = timeout - elapsed
                    status = "仍有验证码" if has_captcha else "未检测到验证码"
                    print(f"等待中... 已等待 {elapsed} 秒，剩余 {remaining} 秒 ({status})")
                
                time.sleep(2)
            except Exception as e:
                print(f"等待验证码时出错: {e}")
                # 尝试重新加载页面
                try:
                    self.driver.refresh()
                    time.sleep(2)
                except Exception as refresh_error:
                    print(f"刷新页面失败: {refresh_error}")
                    time.sleep(2)
        
        print("\n等待验证码超时")
        return False
    
    def wait_for_url_change(self, original_url, timeout=30, check_interval=1):
        """等待URL变化"""
        print(f"[调试] 等待URL变化...", flush=True)
        print(f"[调试] 原始URL: {original_url}", flush=True)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                current_url = self.driver.current_url
                if current_url != original_url:
                    print(f"[调试] ✓ URL已变化: {current_url}", flush=True)
                    return current_url
                time.sleep(check_interval)
            except Exception as e:
                print(f"[调试] 检查URL时出错: {e}", flush=True)
                time.sleep(check_interval)
        
        print(f"[调试] URL未变化，使用当前URL", flush=True)
        return self.driver.current_url
    
    def wait_for_result_page(self, timeout=60):
        """等待页面跳转到结果页面"""
        print(f"[调试] 等待跳转到结果页面...", flush=True)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_url = self.driver.current_url
                print(f"[调试] 当前URL: {current_url}", flush=True)
                
                # 检查是否已跳转到结果页面
                if self.is_result_page(current_url):
                    print(f"[调试] ✓ 已跳转到结果页面", flush=True)
                    # 等待页面加载完成
                    time.sleep(2)
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        # 尝试查找表格，确认数据已加载
                        try:
                            table = self.driver.find_element(By.TAG_NAME, "table")
                            if table:
                                print(f"[调试] ✓ 页面数据已加载", flush=True)
                                return True
                        except:
                            # 即使没找到table，也认为已跳转
                            print(f"[调试] ✓ 已跳转到结果页面（表格可能动态加载）", flush=True)
                            return True
                    except:
                        print(f"[调试] ✓ 已跳转到结果页面（等待超时但继续）", flush=True)
                        return True
                
                # 检查验证码
                if self.detect_captcha():
                    print(f"[调试] 检测到验证码，等待用户解决...", flush=True)
                    if not self.wait_for_captcha_solve():
                        print("[错误] 验证码处理失败或超时", flush=True)
                        return False
                    # 验证码解决后，继续检查URL
                    continue
                
                time.sleep(1)
            except Exception as e:
                print(f"[调试] 等待结果页面时出错: {e}", flush=True)
                time.sleep(1)
        
        print(f"[警告] 等待结果页面超时", flush=True)
        return False
    
    def load_page(self, url=None):
        """加载页面"""
        target_url = url or self.url
        try:
            print(f"[调试] 正在加载页面: {target_url}", flush=True)
            self.driver.get(target_url)
            self.human_like_delay()
            
            # 等待页面加载
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                print("页面加载超时，但继续尝试...", flush=True)
            
            # 检查是否已经在结果页面
            current_url = self.driver.current_url
            print(f"[调试] 当前URL: {current_url}", flush=True)
            
            if self.is_result_page(current_url):
                print("[调试] 已在结果页面，跳过验证码检测和跳转等待", flush=True)
            else:
                # 检测验证码
                print("[调试] 正在检测验证码...", flush=True)
                has_captcha = self.detect_captcha()
                print(f"[调试] 验证码检测结果: {'有验证码' if has_captcha else '无验证码'}", flush=True)
                
                if has_captcha:
                    print("[调试] 检测到验证码，等待用户解决...", flush=True)
                    if not self.wait_for_captcha_solve():
                        print("[错误] 验证码处理失败或超时", flush=True)
                        return False
                    # 验证码解决后，等待URL变化或重新检测
                    print("[调试] 验证码解决，检查URL变化...", flush=True)
                    current_url = self.wait_for_url_change(target_url, timeout=10)
                
                # 如果不在结果页面，等待跳转
                if not self.is_result_page(current_url):
                    print("[调试] 等待页面跳转到结果页面...", flush=True)
                    if not self.wait_for_result_page(timeout=60):
                        print("[警告] 未跳转到结果页面，但继续尝试...", flush=True)
            
            # 模拟人类行为
            try:
                self.scroll_page()
            except Exception as e:
                print(f"滚动页面时出错（可忽略）: {e}", flush=True)
            
            # 最终确认当前URL
            final_url = self.driver.current_url
            print(f"[调试] 最终URL: {final_url}", flush=True)
            
            return True
        except Exception as e:
            error_msg = str(e)
            if "invalid session id" in error_msg.lower() or "session" in error_msg.lower():
                print(f"浏览器会话失效: {e}", flush=True)
                print("尝试重新初始化浏览器...", flush=True)
                # 尝试重新初始化
                try:
                    if self.driver:
                        self.driver.quit()
                    time.sleep(1)
                    if self.init_driver():
                        return self.load_page(url)
                except:
                    pass
            else:
                print(f"加载页面时出错: {e}", flush=True)
            return False
    
    def get_total_pages(self):
        """从页面中提取总页数（改进：查找真实总页数）"""
        if self.total_pages:
            return self.total_pages
        
        print("[调试] 正在查找分页元素...", flush=True)
        
        try:
            # 查找分页元素 - 多种选择器
            pagination = None
            selectors = [
                'ul.el-pager',  # Element UI的分页组件
                'ul.pagination',
                'div.pagination',
                'ul[class*="page"]',
                'div[class*="page"]',
                'ul[class*="pagination"]',
                'nav[class*="pagination"]'
            ]
            
            for selector in selectors:
                try:
                    pagination = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"[调试] 找到分页容器: {selector}", flush=True)
                    break
                except NoSuchElementException:
                    continue
            
            if not pagination:
                print("[调试] 未找到分页容器，检查页面是否包含分页信息...", flush=True)
                # 检查页面文本中是否有页码信息
                page_text = self.driver.page_source
                if 'number' in page_text.lower() or 'pagination' in page_text.lower():
                    print("[调试] 页面包含分页相关文本，但未找到元素", flush=True)
                return None  # 返回None表示无法确定，让程序继续尝试
            
            # 方法1: 查找分页组件中的总页数文本（Element UI通常有总页数显示）
            try:
                # 查找分页组件周围的文本，可能包含"共 X 页"或"X 页"
                pagination_parent = pagination.find_element(By.XPATH, './..')  # 父元素
                parent_text = pagination_parent.text
                print(f"[调试] 分页父元素文本: {parent_text[:200]}", flush=True)
                
                # 查找总页数模式
                total_page_patterns = [
                    re.compile(r'共\s*(\d+)\s*页', re.I),
                    re.compile(r'(\d+)\s*页', re.I),
                    re.compile(r'共\s*(\d+)', re.I),
                    re.compile(r'总计\s*(\d+)\s*页', re.I),
                    re.compile(r'总\s*(\d+)\s*页', re.I),
                ]
                
                for pattern in total_page_patterns:
                    match = pattern.search(parent_text)
                    if match:
                        total_pages = int(match.group(1))
                        if total_pages > 1:  # 确保是合理的总页数
                            self.total_pages = total_pages
                            print(f"[调试] 从父元素文本提取到总页数: {self.total_pages}", flush=True)
                            return self.total_pages
            except:
                pass
            
            # 方法2: 查找所有页码元素，包括可能被隐藏的最后一页
            page_elements = pagination.find_elements(By.CSS_SELECTOR, 'li.number, li[class*="number"], a[class*="number"]')
            if not page_elements:
                # 尝试其他可能的选择器
                page_elements = pagination.find_elements(By.CSS_SELECTOR, 'li, a')
                page_elements = [e for e in page_elements if e.text.strip().isdigit()]
            
            if page_elements:
                print(f"[调试] 找到 {len(page_elements)} 个页码元素", flush=True)
                page_numbers = []
                for element in page_elements:
                    page_text = element.text.strip()
                    try:
                        page_num = int(page_text)
                        if 1 <= page_num <= 10000:  # 扩大范围
                            page_numbers.append(page_num)
                            print(f"[调试] 找到页码: {page_num}", flush=True)
                    except ValueError:
                        pass
                
                if page_numbers:
                    max_page = max(page_numbers)
                    # 如果最大页码较大（>7），可能是真实总页数
                    # 如果最大页码较小（<=7），可能需要查找更多页码或通过其他方式
                    if max_page >= 7:
                        # 尝试查找"下一页"按钮或"..."后的页码
                        try:
                            # 查找是否有"..."或"下一页"等元素
                            next_btn = pagination.find_elements(By.CSS_SELECTOR, 'button.btn-next, a.btn-next, li.next, .next')
                            if next_btn:
                                print(f"[调试] 找到下一页按钮，最大页码可能是部分页码", flush=True)
                                # 如果找到下一页按钮，说明可能还有更多页
                                # 尝试点击最后一页或查找总页数
                                # 暂时使用最大页码，但会在循环中继续尝试
                        except:
                            pass
                    
                    # 如果最大页码小于等于7，可能是部分显示，需要继续尝试
                    if max_page <= 7:
                        print(f"[调试] 最大页码 {max_page} 可能只是部分显示，将在爬取时动态检测", flush=True)
                        # 返回None，让程序继续尝试，不设置上限
                        return None
                    else:
                        self.total_pages = max_page
                        print(f"[调试] 使用最大页码作为总页数: {self.total_pages}", flush=True)
                        return max_page
            
            # 方法3: 从分页文本中提取
            pagination_text = pagination.text
            print(f"[调试] 分页文本: {pagination_text[:200]}", flush=True)
            patterns = [
                re.compile(r'共\s*(\d+)\s*页', re.I),
                re.compile(r'(\d+)\s*页', re.I),
                re.compile(r'共\s*(\d+)', re.I),
            ]
            for pattern in patterns:
                match = pattern.search(pagination_text)
                if match:
                    self.total_pages = int(match.group(1))
                    print(f"[调试] 从文本提取到总页数: {self.total_pages}", flush=True)
                    return self.total_pages
            
        except NoSuchElementException as e:
            print(f"[调试] 未找到分页元素: {e}", flush=True)
        except Exception as e:
            print(f"[调试] 获取总页数时出错: {e}", flush=True)
        
        print("[调试] 无法确定总页数，将在爬取时动态检测", flush=True)
        return None  # 返回None，让程序继续尝试
    
    def click_next_page(self):
        """进入下一页（优先使用前端元素点击方式，优化速度）"""
        try:
            next_page = self.current_page + 1
            next_page_text = str(next_page)
            
            print(f"[调试] 准备翻页到第 {next_page} 页", flush=True)
            
            # 方法1: 优先使用前端元素点击（优化：直接查找已知元素）
            try:
                    # 优化：使用缓存的分页元素，减少查找次数
                pagination = None
                if self._pagination_cache:
                    try:
                        if self._pagination_cache.is_displayed():
                            pagination = self._pagination_cache
                    except:
                        self._pagination_cache = None
                
                if not pagination:
                    try:
                        pagination = self.driver.find_element(By.CSS_SELECTOR, 'ul.el-pager')
                        self._pagination_cache = pagination  # 缓存分页元素
                    except NoSuchElementException:
                        try:
                            pagination = self.driver.find_element(By.CSS_SELECTOR, 'ul.pagination')
                            self._pagination_cache = pagination
                        except NoSuchElementException:
                            pagination = None
                
                if pagination:
                    # 检查是否有可见的下一页页码（避免超出范围）
                    all_number_elements = pagination.find_elements(By.CSS_SELECTOR, 'li.number')
                    visible_pages = [int(e.text.strip()) for e in all_number_elements if e.text.strip().isdigit()]
                    max_visible = max(visible_pages) if visible_pages else 0
                    
                    # 如果目标页码超出可见范围，尝试使用"下一页"按钮
                    if next_page > max_visible and max_visible > 0:
                        print(f"[调试] 目标页码 {next_page} 超出可见范围（最大可见: {max_visible}），尝试使用下一页按钮", flush=True)
                        try:
                            next_btn = pagination.find_element(By.CSS_SELECTOR, 'button.btn-next, a.btn-next, li.next')
                            if next_btn and not next_btn.get_attribute('disabled'):
                                self.driver.execute_script("arguments[0].click();", next_btn)
                                print(f"[调试] ✓ 已点击下一页按钮", flush=True)
                                time.sleep(1.5)
                                # 验证翻页是否成功
                                try:
                                    active_element = pagination.find_element(By.CSS_SELECTOR, 'li.number.active')
                                    new_active_page = int(active_element.text.strip())
                                    if new_active_page > self.current_page:
                                        self.current_page = new_active_page
                                        print(f"[调试] ✓ 通过下一页按钮成功翻到第 {new_active_page} 页", flush=True)
                                        return True
                                    else:
                                        print(f"[警告] 点击下一页后页码未变化，可能已到达最后一页", flush=True)
                                        return False
                                except:
                                    # 如果验证失败，也认为成功（已点击）
                                    self.current_page = next_page
                                    return True
                            else:
                                print(f"[调试] 下一页按钮已禁用或不存在，可能已到达最后一页", flush=True)
                                return False
                        except NoSuchElementException:
                            print(f"[调试] 未找到下一页按钮，尝试直接查找页码元素", flush=True)
                    
                    # 直接查找目标页码元素（优化：只使用最快的方式）
                    try:
                        # 直接通过XPath查找，最快
                        next_page_element = pagination.find_element(By.XPATH, f'.//li[contains(@class, "number") and text()="{next_page_text}"]')
                    except NoSuchElementException:
                        # 如果直接查找失败，遍历所有number元素
                        number_elements = pagination.find_elements(By.CSS_SELECTOR, 'li.number')
                        next_page_element = None
                        for element in number_elements:
                            if element.text.strip() == next_page_text:
                                next_page_element = element
                                break
                    
                    if next_page_element:
                        # 使用JavaScript点击（更快更可靠）
                        self.driver.execute_script("arguments[0].click();", next_page_element)
                        print(f"[调试] ✓ 已点击页码 {next_page_text}", flush=True)
                        
                        # 等待页面加载和验证翻页成功（优化：减少等待时间）
                        time.sleep(0.8)  # 减少等待时间：从1.5秒改为0.8秒
                        
                        # 验证翻页成功：最多尝试5次，每次0.3秒
                        for attempt in range(5):
                            try:
                                # 检查active类是否更新
                                active_element = pagination.find_element(By.CSS_SELECTOR, 'li.number.active')
                                active_text = active_element.text.strip()
                                if active_text == next_page_text:
                                    # 等待表格数据更新（优化：减少等待和检查次数）
                                    try:
                                        # 等待表格行出现（缩短超时时间）
                                        WebDriverWait(self.driver, 2).until(
                                            lambda d: len(d.find_elements(By.CSS_SELECTOR, "table tr")) > 1
                                        )
                                        time.sleep(0.5)  # 减少等待时间：从1秒改为0.5秒
                                        # 简化数据稳定性检查：只检查一次
                                        if self._debug_mode:
                                            rows_count = len(self.driver.find_elements(By.CSS_SELECTOR, "table tr"))
                                            print(f"[调试] ✓ 确认翻页到第 {next_page_text} 页，数据已加载（{rows_count}行）", flush=True)
                                    except:
                                        time.sleep(1)  # 如果等待失败，减少额外等待：从2秒改为1秒
                                    
                                    # 更新current_page（关键修复：避免重复读取）
                                    self.current_page = next_page
                                    return True
                            except:
                                pass
                            time.sleep(0.3)
                        
                        # 如果active类验证失败，检查URL（优化：简化检查）
                        current_url = self.driver.current_url
                        if f'page={next_page}' in current_url:
                            # 等待表格数据更新（优化：缩短等待时间）
                            try:
                                WebDriverWait(self.driver, 2).until(
                                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "table tr")) > 1
                                )
                                time.sleep(0.5)  # 减少等待时间
                                if self._debug_mode:
                                    rows_count = len(self.driver.find_elements(By.CSS_SELECTOR, "table tr"))
                                    print(f"[调试] ✓ URL确认翻页成功，数据已加载（{rows_count}行）", flush=True)
                            except:
                                time.sleep(1)  # 减少等待时间
                            
                            # 更新current_page（关键修复）
                            self.current_page = next_page
                            return True
                        
                        # 即使验证失败，也更新current_page（已点击，假设成功）
                        # 但等待一下确保数据加载（优化：减少等待时间）
                        time.sleep(0.5)
                        if self._debug_mode:
                            print(f"[调试] 已点击，假设翻页成功（等待数据加载）", flush=True)
                        self.current_page = next_page
                        return True
                    else:
                        print(f"[调试] 未找到页码 {next_page_text} 的元素", flush=True)
                else:
                    print("[调试] 未找到分页容器", flush=True)
                    
            except Exception as click_error:
                print(f"[调试] 前端元素点击失败: {click_error}", flush=True)
            
            # 方法2: 如果前端元素点击失败，使用URL参数方式（备选方案）
            print("[调试] 尝试URL参数方式翻页...", flush=True)
            try:
                current_url = self.driver.current_url
                
                # 构建下一页URL
                if 'page=' in current_url:
                    import re
                    next_page_url = re.sub(r'page=\d+', f'page={next_page}', current_url)
                else:
                    separator = '&' if '?' in current_url else '?'
                    next_page_url = f"{current_url}{separator}page={next_page}"
                
                # 直接跳转（优化：减少等待时间）
                self.driver.get(next_page_url)
                time.sleep(0.8)  # 减少等待时间：从1.5秒改为0.8秒
                
                # 等待表格数据更新（优化：缩短超时时间）
                try:
                    WebDriverWait(self.driver, 2).until(
                        lambda d: len(d.find_elements(By.TAG_NAME, "tr")) > 1
                    )
                except:
                    time.sleep(0.5)  # 减少等待时间
                
                # 快速验证
                new_url = self.driver.current_url
                if f'page={next_page}' in new_url:
                    print(f"[调试] ✓ URL方式翻页成功，数据已加载", flush=True)
                    # 更新current_page（关键修复）
                    self.current_page = next_page
                    return True
                else:
                    # 即使URL不匹配，也更新current_page（已跳转）
                    print(f"[警告] URL未完全匹配，但已跳转（等待数据加载）", flush=True)
                    time.sleep(1)  # 额外等待确保数据加载
                    self.current_page = next_page
                    return True
                    
            except Exception as url_error:
                print(f"[错误] URL方式翻页失败: {url_error}", flush=True)
            
            return False
            
        except Exception as e:
            print(f"[错误] 翻页失败: {e}", flush=True)
            return False
    
    def parse_table_data(self):
        """解析表格数据"""
        try:
            # 获取页面源码
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            # 调试：检查页面内容
            current_url = self.driver.current_url
            print(f"[调试] 当前URL: {current_url}", flush=True)
            
            # 查找表格 - 多种方式
            table = None
            
            # 方式1: 使用Selenium直接查找table元素（优化：使用缓存）
            table_element = None
            if self._table_cache:
                try:
                    # 尝试使用缓存的表格元素
                    if self._table_cache.is_displayed():
                        table_element = self._table_cache
                except:
                    self._table_cache = None
            
            if not table_element:
                try:
                    table_element = self.driver.find_element(By.TAG_NAME, "table")
                    self._table_cache = table_element  # 缓存表格元素
                    if table_element:
                        table_html = table_element.get_attribute('outerHTML')
                        table = BeautifulSoup(table_html, 'lxml').find('table')
                        if table:
                            if self._debug_mode:
                                print("[调试] 通过Selenium找到表格")
                except:
                    pass
            else:
                # 使用缓存的表格元素
                table_html = table_element.get_attribute('outerHTML')
                table = BeautifulSoup(table_html, 'lxml').find('table')
            
            # 方式2: 直接查找table标签
            if not table:
                table = soup.find('table')
            
            # 方式3: 查找包含表格的容器
            if not table:
                table_containers = soup.find_all(['div', 'section'], class_=re.compile(r'table|list|data|result', re.I))
                for container in table_containers:
                    table = container.find('table')
                    if table:
                        print(f"[调试] 在容器中找到表格")
                        break
            
            # 方式3: 查找特定的表格ID或类名
            if not table:
                for selector in ['table[id*="table"]', 'table[class*="table"]', 'table[id*="data"]', 'table[class*="data"]']:
                    try:
                        table = soup.select_one(selector)
                        if table:
                            print(f"[调试] 通过选择器找到表格: {selector}")
                            break
                    except:
                        pass
            
            # 方式4: 检查是否有表格结构的div（某些网站用div模拟表格）
            if not table:
                # 查找包含表头的div
                header_divs = soup.find_all('div', class_=re.compile(r'header|thead', re.I))
                for header_div in header_divs:
                    parent = header_div.find_parent()
                    if parent:
                        rows = parent.find_all('div', class_=re.compile(r'row|item|tr', re.I))
                        if len(rows) > 1:
                            print(f"[调试] 找到div表格结构")
                            # 这里可以用div结构解析，暂时先返回空，后续可以扩展
                            break
            
            if not table:
                print(f"[调试] 未找到表格，尝试查找所有可能的表格结构...")
                # 输出页面的一些关键信息用于调试
                page_text = soup.get_text()[:500]  # 前500个字符
                print(f"[调试] 页面文本片段: {page_text[:200]}...")
                return []
            
            # 提取表头
            headers = []
            thead = table.find('thead')
            if thead:
                header_row = thead.find('tr')
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            if not headers:
                headers = ['序号', '企业名称', '登记状态', '统一社会信用代码', 
                          '法定代表人', '成立日期', '注册资本', '实缴资本']
            
            # 提取数据行 - 优先使用Selenium获取真实的行数据（不依赖tbody）
            rows = []
            try:
                # 直接使用Selenium查找table内的所有tr元素（最可靠）
                table_element = self.driver.find_element(By.TAG_NAME, "table")
                
                # 直接查找table内的所有tr（包括tbody内和table直接的tr）
                selenium_rows = table_element.find_elements(By.CSS_SELECTOR, "tr")
                
                if len(selenium_rows) > 0:
                    if self._debug_mode:
                        print(f"[调试] 通过Selenium在table中找到 {len(selenium_rows)} 行数据", flush=True)
                    # 优化：批量解析HTML，减少BeautifulSoup初始化次数
                    rows_html = []
                    for row in selenium_rows:
                        try:
                            html = row.get_attribute('outerHTML')
                            if html:
                                rows_html.append(html)
                        except:
                            continue
                    
                    # 批量解析所有行的HTML（优化：一次性解析所有HTML）
                    if rows_html:
                        combined_html = '<table>' + ''.join(rows_html) + '</table>'
                        try:
                            combined_soup = BeautifulSoup(combined_html, 'lxml')
                            rows = combined_soup.find_all('tr')
                        except:
                            # 如果批量解析失败，回退到逐行解析
                            for html in rows_html:
                                try:
                                    soup_row = BeautifulSoup(html, 'lxml').find('tr')
                                    if soup_row:
                                        rows.append(soup_row)
                                except:
                                    continue
                    
                    if self._debug_mode:
                        print(f"[调试] 成功解析 {len(rows)} 行HTML", flush=True)
                        if len(rows) < len(selenium_rows):
                            print(f"[警告] 解析的行数({len(rows)})少于Selenium找到的行数({len(selenium_rows)})，可能部分行解析失败", flush=True)
            except Exception as e:
                print(f"[调试] Selenium方式失败: {e}，尝试使用BeautifulSoup", flush=True)
                # 如果Selenium失败，使用BeautifulSoup
                tbody = table.find('tbody')
                if not tbody:
                    tbody = table
                
                # 查找tbody内的所有tr（不使用recursive=False，因为可能嵌套）
                rows = tbody.find_all('tr')
                print(f"[调试] 通过BeautifulSoup找到 {len(rows)} 行数据", flush=True)
            
            if not rows or len(rows) <= 1:
                if self._debug_mode:
                    print(f"[调试] 未找到足够的数据行（只有 {len(rows)} 行），尝试查找页面中所有table tr元素", flush=True)
                # 如果表格内找不到，尝试查找页面中所有table tr（优化：批量解析）
                try:
                    all_trs = self.driver.find_elements(By.CSS_SELECTOR, "table tr")
                    if len(all_trs) > len(rows):
                        if self._debug_mode:
                            print(f"[调试] 在页面中找到 {len(all_trs)} 个table tr元素", flush=True)
                        rows_html = []
                        for tr in all_trs:
                            try:
                                html = tr.get_attribute('outerHTML')
                                if html:
                                    rows_html.append(html)
                            except:
                                continue
                        
                        # 批量解析（优化）
                        if rows_html:
                            combined_html = '<table>' + ''.join(rows_html) + '</table>'
                            try:
                                combined_soup = BeautifulSoup(combined_html, 'lxml')
                                rows = combined_soup.find_all('tr')
                            except:
                                rows = []
                                for html in rows_html:
                                    try:
                                        soup_row = BeautifulSoup(html, 'lxml').find('tr')
                                        if soup_row:
                                            rows.append(soup_row)
                                    except:
                                        continue
                        
                        if self._debug_mode:
                            print(f"[调试] 成功解析 {len(rows)} 行HTML（从页面所有table tr）", flush=True)
                except Exception as e:
                    if self._debug_mode:
                        print(f"[调试] 查找页面tr元素失败: {e}", flush=True)
            
            if not rows or len(rows) <= 1:
                print(f"[调试] 未找到任何数据行（只有 {len(rows)} 行）", flush=True)
                return []
            
            page_data = []
            header_skipped = False  # 标记是否已跳过表头
            
            # 定义表头关键词（用于识别重复的表头行）
            header_keywords = ['序号', '企业名称', '企业名', '公司名称', '登记状态', '统一社会信', 
                             '法定代表人', '成立日期', '注册资本', '实缴资本', '核准日期', 
                             '营业期限', '所属省份', '所属城市', '所属区县', '电话', '邮箱', 
                             '纳税人识', '纳税人识别']
            
            for idx, row in enumerate(rows):
                if row is None:
                    continue
                    
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    if self._debug_mode:
                        print(f"[调试] 第 {idx+1} 行单元格数不足: {len(cells)}", flush=True)
                    continue
                
                # 获取行文本内容
                row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                
                # 检查是否为表头行（检查所有行，不仅仅是前两行）
                is_header = False
                
                # 方法1: 检查是否包含多个表头关键词（如果一行包含3个或以上表头关键词，很可能是表头）
                keyword_count = sum(1 for keyword in header_keywords if keyword in row_text)
                if keyword_count >= 3:
                    # 进一步验证：检查单元格内容是否都是表头关键词（短文本，无URL）
                    has_urls = False
                    all_short_text = True
                    for cell in cells:
                        text = cell.get_text(strip=True)
                        # 检查是否有链接
                        if cell.find('a') and cell.find('a').get('href'):
                            has_urls = True
                        # 检查文本长度（表头通常是短文本）
                        if len(text) > 20:  # 如果文本超过20个字符，不太像表头
                            all_short_text = False
                    
                    # 如果包含多个关键词，且没有URL，且文本较短，很可能是表头
                    if not has_urls and all_short_text:
                        is_header = True
                        if self._debug_mode:
                            print(f"[调试] 第 {idx+1} 行识别为重复表头行（包含{keyword_count}个表头关键词），跳过", flush=True)
                        continue
                
                # 方法2: 对于前两行，使用更宽松的判断（兼容第一行表头）
                if not header_skipped and idx < 2:
                    if any(keyword in row_text for keyword in header_keywords[:5]):  # 只检查前5个关键词
                        # 检查是否真的是表头（通常是第一行，或者单元格数和表头匹配）
                        if idx == 0 or (len(headers) > 0 and len(cells) == len(headers)):
                            is_header = True
                            header_skipped = True
                            if self._debug_mode:
                                print(f"[调试] 第 {idx+1} 行识别为表头行，跳过", flush=True)
                            continue
                
                # 检查是否有实际数据（不是空行）
                has_data = False
                cell_count = 0
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if text and len(text.strip()) > 0:
                        cell_count += 1
                        if len(text.strip()) > 1:  # 有实际内容（不是单个字符）
                            has_data = True
                
                # 如果有效单元格少于2个，认为是空行或无效行
                if cell_count < 2 or not has_data:
                    if self._debug_mode:
                        print(f"[调试] 第 {idx+1} 行为空行或无效行（有效单元格: {cell_count}），跳过", flush=True)
                    continue
                
                company_data = {}
                
                # 如果表头数量不匹配，尝试按位置提取
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        value = cell.get_text(strip=True)
                        if value:
                            company_data[headers[i]] = value
                    else:
                        # 如果单元格数多于表头，按位置存储
                        value = cell.get_text(strip=True)
                        if value:
                            company_data[f"列{i+1}"] = value
                    
                    # 提取链接
                    link = cell.find('a')
                    if link and link.get('href'):
                        href = link.get('href')
                        if href.startswith('/'):
                            href = f"https://qiye.qizhidao.com{href}"
                        elif not href.startswith('http'):
                            href = f"https://qiye.qizhidao.com/{href}"
                        # 如果这是企业名称列，添加链接
                        if i < len(headers) and '企业' in headers[i]:
                            company_data[f"{headers[i]}_链接"] = href
                        else:
                            company_data[f"链接{i+1}"] = href
                
                # 如果提取到数据，保存
                if company_data:
                    company_data['页码'] = self.current_page
                    page_data.append(company_data)
                    if self._debug_mode:
                        print(f"[调试] 成功提取第 {idx+1} 行数据: {list(company_data.keys())[:3]}...", flush=True)
            
            print(f"[调试] 成功解析 {len(page_data)} 条企业数据", flush=True)
            return page_data
            
        except Exception as e:
            print(f"解析表格数据时出错: {e}", flush=True)
            return []
    
    def crawl_all_pages(self):
        """爬取所有页面"""
        print("=" * 50, flush=True)
        print("企知道网站智能爬虫 - 开始运行", flush=True)
        print("=" * 50, flush=True)
        print(f"基础URL: {self.base_url}", flush=True)
        print(f"无头模式: {self.headless}", flush=True)
        print(flush=True)
        
        # 初始化WebDriver
        if not self.init_driver():
            return None
        
        try:
            if self.interactive:
                # 交互模式：等待用户准备好
                print("\n" + "=" * 60)
                print("交互模式已启用")
                print("=" * 60)
                print("1. 浏览器将打开，请在浏览器中完成登录和验证")
                print("2. 导航到结果页面（显示企业数据的页面）")
                print("3. 准备就绪后，请在浏览器中保持结果页面打开")
                print("4. 然后回到这里输入 '开始爬取' 或按回车键")
                print("=" * 60 + "\n")
                
                # 加载初始页面
                print("[步骤0] 正在打开浏览器...", flush=True)
                if not self.load_page():
                    print("页面加载失败，退出爬取", flush=True)
                    return None
                
                # 检查当前URL，如果已经在结果页面，自动开始
                current_url = self.driver.current_url
                print(f"[调试] 当前URL: {current_url}", flush=True)
                
                auto_start = False
                if self.is_result_page(current_url):
                    print("[提示] 检测到已在结果页面，可以自动开始爬取", flush=True)
                    print("[提示] 如果您已在结果页面准备好了，程序将自动开始", flush=True)
                    auto_start = True
                
                if not auto_start:
                    # 等待用户输入
                    try:
                        user_input = input("\n请输入 '开始爬取' 或按回车键继续（输入 '退出' 取消）: ").strip().lower()
                        if user_input in ['退出', 'exit', 'quit', 'q']:
                            print("用户取消爬取", flush=True)
                            return None
                        elif user_input in ['开始爬取', '开始', 'start', 's', '']:
                            print("\n[用户确认] 开始爬取数据...\n", flush=True)
                        else:
                            print("无效输入，将尝试自动开始...", flush=True)
                    except (EOFError, KeyboardInterrupt):
                        print("\n[自动模式] 检测到非交互环境，自动开始爬取...\n", flush=True)
                
                # 再次检查当前URL（用户可能已经导航）
                final_url = self.driver.current_url
                print(f"[调试] 准备开始时的URL: {final_url}", flush=True)
                
                if not self.is_result_page(final_url):
                    print("[警告] 当前不在结果页面（当前在登录页面）", flush=True)
                    print("[提示] 请先在浏览器中完成登录，然后导航到结果页面", flush=True)
                    print("[提示] 结果页面URL应该类似: https://qiye.qizhidao.com/batch-query-result?matchId=...", flush=True)
                    # 等待用户导航
                    print("[提示] 等待您导航到结果页面...", flush=True)
                    wait_start = time.time()
                    while time.time() - wait_start < 60:  # 最多等待60秒
                        time.sleep(2)
                        final_url = self.driver.current_url
                        if self.is_result_page(final_url):
                            print(f"[调试] ✓ 已检测到结果页面: {final_url}", flush=True)
                            break
                        print(f"[调试] 等待中... 当前URL: {final_url}", flush=True)
                    
                    if not self.is_result_page(final_url):
                        print("[错误] 超时：仍未在结果页面，无法继续爬取", flush=True)
                        return None
            else:
                # 自动模式：加载第一页（load_page内部已处理验证码和页面跳转）
                print("\n[步骤1] 正在加载页面...", flush=True)
                if not self.load_page():
                    print("页面加载失败，退出爬取", flush=True)
                    return None
                print("[步骤1] 页面加载完成\n", flush=True)
                
                # 再次确认当前URL（可能在加载过程中已跳转）
                final_url = self.driver.current_url
                print(f"[调试] 步骤1完成后的URL: {final_url}", flush=True)
                
            # 如果URL已经跳转到结果页面，可能需要刷新或等待数据加载（优化：减少滚动和等待）
            if self.is_result_page(final_url):
                if self._debug_mode:
                    print("[调试] ✓ 确认在结果页面，等待数据加载...", flush=True)
                time.sleep(1.5)  # 减少等待时间：从3秒改为1.5秒
                
                # 优化：使用最小化滚动（仅在必要时触发懒加载）
                try:
                    self.scroll_page(minimal=True)  # 使用最小化滚动
                except Exception as e:
                    if self._debug_mode:
                        print(f"[调试] 滚动页面时出错（可忽略）: {e}", flush=True)
            
            # 获取总页数
            print("\n[步骤2] 正在获取总页数...", flush=True)
            self.total_pages = self.get_total_pages()
            print(f"[步骤2] 检测到总页数: {self.total_pages}\n", flush=True)
            
            # 如果没找到分页，尝试直接解析当前页
            if self.total_pages == 1:
                print("[提示] 未检测到分页信息，尝试解析当前页面数据...", flush=True)
            elif self.total_pages is None:
                print("[提示] 无法确定总页数，将在爬取时动态检测（遇到无法翻页时停止）...", flush=True)
            
            while True:
                print(f"\n{'='*50}", flush=True)
                print(f"[步骤3] 正在爬取第 {self.current_page} 页...", flush=True)
                print(f"{'='*50}", flush=True)
                
                # 在主循环开始处添加严格的重复检测
                print(f"[调试] 准备爬取第 {self.current_page} 页", flush=True)
                print(f"[调试] 已爬取页面: {sorted(self.crawled_pages)}", flush=True)
                
                # 严格检查是否已爬取
                if self.current_page in self.crawled_pages:
                    print(f"[严重警告] 第 {self.current_page} 页已爬取，跳过避免重复", flush=True)
                    
                    # 如果已爬取，直接尝试下一页
                    if self.total_pages and self.current_page >= self.total_pages:
                        print(f"已爬取所有页面 (共 {self.total_pages} 页)", flush=True)
                        break
                    else:
                        # 检查下一页是否也已爬取（避免死循环）
                        next_page_num = self.current_page + 1
                        if next_page_num in self.crawled_pages:
                            print(f"[严重警告] 下一页 {next_page_num} 也已爬取，可能陷入循环！", flush=True)
                            # 尝试找到下一个未爬取的页面
                            found_next = False
                            for test_page in range(next_page_num, next_page_num + 10):
                                if test_page not in self.crawled_pages:
                                    print(f"[调试] 尝试跳转到未爬取的页面 {test_page}", flush=True)
                                    # 尝试直接跳转到该页
                                    try:
                                        pagination = self.driver.find_element(By.CSS_SELECTOR, 'ul.el-pager')
                                        page_elements = pagination.find_elements(By.CSS_SELECTOR, 'li.number')
                                        for elem in page_elements:
                                            if elem.text.strip() == str(test_page):
                                                self.driver.execute_script("arguments[0].click();", elem)
                                                time.sleep(2)
                                                self.current_page = test_page
                                                found_next = True
                                                break
                                    except:
                                        pass
                                    if found_next:
                                        break
                            
                            if not found_next:
                                print(f"[错误] 无法找到未爬取的页面，可能已完成所有页面", flush=True)
                                break
                        else:
                            # 正常翻页到下一页
                            print(f"[步骤3.3] 进入第 {next_page_num} 页...", flush=True)
                            if not self.click_next_page():
                                print(f"[错误] 无法进入第 {next_page_num} 页", flush=True)
                                break
                    
                    # 重新验证翻页后的页码
                    try:
                        pagination = self.driver.find_element(By.CSS_SELECTOR, 'ul.el-pager')
                        active_element = pagination.find_element(By.CSS_SELECTOR, 'li.number.active')
                        active_page = int(active_element.text.strip())
                        if active_page != self.current_page:
                            print(f"[调试] 翻页后页码更新：{self.current_page} -> {active_page}", flush=True)
                            self.current_page = active_page
                    except:
                        pass
                    
                    continue  # 跳过当前页处理
                
                # 确保页面已加载
                current_url_check = self.driver.current_url
                print(f"[调试] 当前页面URL: {current_url_check}", flush=True)
                
                # 验证当前页是否匹配（通过active页码确认）
                try:
                    pagination = self.driver.find_element(By.CSS_SELECTOR, 'ul.el-pager')
                    active_element = pagination.find_element(By.CSS_SELECTOR, 'li.number.active')
                    active_page_text = active_element.text.strip()
                    if active_page_text.isdigit():
                        active_page = int(active_page_text)
                        if active_page != self.current_page:
                            print(f"[警告] 激活页码({active_page})与当前页({self.current_page})不匹配", flush=True)
                            
                            # 如果页码变小，说明可能跳回了，这是严重错误
                            if active_page < self.current_page:
                                print(f"[严重错误] 页码从 {self.current_page} 跳回 {active_page}，可能已到达最后一页或网站不支持该页码", flush=True)
                                # 如果跳回的页面已爬取，说明陷入循环
                                if active_page in self.crawled_pages:
                                    print(f"[严重错误] 跳回的页面 {active_page} 已爬取，停止爬取避免死循环", flush=True)
                                    break
                                else:
                                    # 检查是否是因为页码超出范围（如网站只支持到第10页，但尝试访问第11页）
                                    all_number_elements = pagination.find_elements(By.CSS_SELECTOR, 'li.number')
                                    visible_pages = [int(e.text.strip()) for e in all_number_elements if e.text.strip().isdigit()]
                                    max_visible = max(visible_pages) if visible_pages else 0
                                    
                                    if self.current_page > max_visible and max_visible > 0:
                                        print(f"[提示] 当前页码 {self.current_page} 超出可见范围（最大可见: {max_visible}），已到达最后一页", flush=True)
                                        break
                                    
                                    print(f"[调试] 更新页码为 {active_page}", flush=True)
                                    self.current_page = active_page
                                    # 重新检查是否已爬取
                                    if self.current_page in self.crawled_pages:
                                        print(f"[警告] 更新后的页码 {self.current_page} 已爬取过，跳过", flush=True)
                                        if self.total_pages and self.current_page >= self.total_pages:
                                            break
                                        else:
                                            # 检查是否还有下一页
                                            try:
                                                next_btn = pagination.find_elements(By.CSS_SELECTOR, 'button.btn-next, a.btn-next, li.next')
                                                if next_btn and not next_btn[0].get_attribute('disabled'):
                                                    next_page_num = self.current_page + 1
                                                    if not self.click_next_page():
                                                        break
                                                    continue
                                                else:
                                                    print(f"[提示] 下一页按钮已禁用或不存在，已到达最后一页", flush=True)
                                                    break
                                            except:
                                                break
                                    continue
                            else:
                                # 页码变大，正常更新
                                print(f"[调试] 更新页码为 {active_page}", flush=True)
                                self.current_page = active_page
                                # 如果更新后的页码已爬取过，跳过
                                if self.current_page in self.crawled_pages:
                                    print(f"[警告] 更新后的页码 {self.current_page} 已爬取过，跳过", flush=True)
                                    if self.total_pages and self.current_page >= self.total_pages:
                                        break
                                    else:
                                        next_page_num = self.current_page + 1
                                        if not self.click_next_page():
                                            break
                                        continue
                except:
                    pass  # 如果找不到分页元素，忽略
                
                # 如果不在结果页面，尝试刷新
                if not self.is_result_page(current_url_check):
                    print("[警告] 不在结果页面，尝试刷新...", flush=True)
                    try:
                        self.driver.refresh()
                        time.sleep(3)
                    except:
                        pass
                
                # 等待表格数据稳定（优化：简化检查，减少等待时间）
                try:
                    if self._debug_mode:
                        print(f"[调试] 等待表格数据稳定...", flush=True)
                    # 简化：只等待表格行出现，不再进行复杂的稳定性检查
                    try:
                        WebDriverWait(self.driver, 2).until(
                            lambda d: len(d.find_elements(By.CSS_SELECTOR, "table tr")) > 1
                        )
                        time.sleep(0.3)  # 减少等待时间：从0.5秒改为0.3秒
                        if self._debug_mode:
                            rows_count = len(self.driver.find_elements(By.CSS_SELECTOR, "table tr"))
                            print(f"[调试] ✓ 表格数据已稳定（{rows_count}行）", flush=True)
                    except:
                        time.sleep(0.5)  # 减少等待时间：从1秒改为0.5秒
                except:
                    time.sleep(0.5)  # 减少等待时间
                
                # 解析当前页数据
                print(f"[步骤3.1] 正在解析页面数据...", flush=True)
                page_data = self.parse_table_data()
                
                if page_data:
                    # 去重：检查当前页数据是否与已有数据重复
                    unique_page_data = []
                    seen_keys = set()  # 用于快速检查重复
                    
                    for item in page_data:
                        # 使用企业名称或统一社会信用代码作为唯一标识
                        key = None
                        if '企业名称' in item:
                            key = item['企业名称']
                        elif '统一社会信用代码' in item:
                            key = item['统一社会信用代码']
                        elif '序号' in item and '企业名称' in item:
                            key = f"{item.get('序号', '')}_{item.get('企业名称', '')}"
                        
                        if key and key not in seen_keys:
                            # 检查是否与已有数据重复
                            is_duplicate = False
                            for existing_item in self.companies_data:
                                if '企业名称' in existing_item and '企业名称' in item:
                                    if existing_item['企业名称'] == item['企业名称']:
                                        is_duplicate = True
                                        break
                                elif '统一社会信用代码' in existing_item and '统一社会信用代码' in item:
                                    if existing_item['统一社会信用代码'] == item['统一社会信用代码']:
                                        is_duplicate = True
                                        break
                            
                            if not is_duplicate:
                                unique_page_data.append(item)
                                seen_keys.add(key)
                            else:
                                print(f"[调试] 发现重复数据，跳过: {key[:50]}...", flush=True)
                    
                    if len(unique_page_data) != len(page_data):
                        print(f"[警告] 当前页发现 {len(page_data) - len(unique_page_data)} 条重复数据，已过滤", flush=True)
                    
                    # 检查是否与上一页数据重复（通过第一条数据判断）
                    if len(self.companies_data) > 0 and len(unique_page_data) > 0:
                        last_item = self.companies_data[-1]
                        first_item = unique_page_data[0]
                        
                        # 比较企业名称或统一社会信用代码
                        is_same = False
                        if '企业名称' in last_item and '企业名称' in first_item:
                            if last_item['企业名称'] == first_item['企业名称']:
                                is_same = True
                        elif '统一社会信用代码' in last_item and '统一社会信用代码' in first_item:
                            if last_item['统一社会信用代码'] == first_item['统一社会信用代码']:
                                is_same = True
                        
                        if is_same:
                            print(f"[警告] 检测到数据重复！当前页第一条数据与上一页最后一条相同，可能页面未更新", flush=True)
                            print(f"[调试] 跳过当前页，尝试翻页...", flush=True)
                            # 标记为已爬取，避免重复
                            self.crawled_pages.add(self.current_page)
                            # 直接进入下一页
                            if self.total_pages and self.current_page >= self.total_pages:
                                print(f"已爬取所有页面 (共 {self.total_pages} 页)", flush=True)
                                break
                            else:
                                next_page_num = self.current_page + 1
                                print(f"[步骤3.3] 进入第 {next_page_num} 页...", flush=True)
                                if not self.click_next_page():
                                    print(f"[错误] 无法进入第 {next_page_num} 页", flush=True)
                                    break
                                continue
                    
                    if unique_page_data:
                        self.companies_data.extend(unique_page_data)
                        print(f"[步骤3.2] 第 {self.current_page} 页提取了 {len(unique_page_data)} 条企业信息（去重后）", flush=True)
                        # 标记该页已爬取（关键修复：避免重复读取）
                        self.crawled_pages.add(self.current_page)
                        print(f"[调试] 已标记第 {self.current_page} 页为已爬取", flush=True)
                    else:
                        print(f"[警告] 第 {self.current_page} 页解析的数据全部为重复数据，跳过", flush=True)
                        self.crawled_pages.add(self.current_page)
                else:
                    print(f"[警告] 第 {self.current_page} 页无数据，尝试继续...", flush=True)
                    # 即使无数据也标记为已爬取，避免重复尝试
                    self.crawled_pages.add(self.current_page)
                
                # 检查是否还有下一页
                if self.total_pages and self.current_page >= self.total_pages:
                    print(f"已爬取所有页面 (共 {self.total_pages} 页)", flush=True)
                    break
                
                # 进入下一页（注意：click_next_page内部已更新current_page）
                next_page_num = self.current_page + 1
                print(f"[步骤3.3] 进入第 {next_page_num} 页...", flush=True)
                
                # 尝试翻页
                if not self.click_next_page():
                    print(f"[错误] 无法进入第 {next_page_num} 页", flush=True)
                    # 检查是否真的没有下一页了
                    try:
                        # 检查是否有下一页按钮或更多页码
                        pagination = self.driver.find_element(By.CSS_SELECTOR, 'ul.el-pager')
                        next_btn = pagination.find_elements(By.CSS_SELECTOR, 'button.btn-next, a.btn-next, li.next, .next')
                        # 检查下一页按钮是否被禁用
                        if next_btn:
                            is_disabled = next_btn[0].get_attribute('disabled') or 'disabled' in next_btn[0].get_attribute('class') or ''
                            if is_disabled:
                                print(f"[提示] 下一页按钮已禁用，已到达最后一页", flush=True)
                                break
                        
                        # 检查当前页是否是最后一个可见页码
                        active_element = pagination.find_element(By.CSS_SELECTOR, 'li.number.active')
                        active_page = int(active_element.text.strip())
                        all_number_elements = pagination.find_elements(By.CSS_SELECTOR, 'li.number')
                        visible_pages = [int(e.text.strip()) for e in all_number_elements if e.text.strip().isdigit()]
                        max_visible = max(visible_pages) if visible_pages else 0
                        
                        if active_page >= max_visible and max_visible > 0:
                            # 如果当前页是最后一个可见页码，可能还有更多页
                            # 尝试点击下一页按钮
                            try:
                                next_btn = pagination.find_element(By.CSS_SELECTOR, 'button.btn-next, a.btn-next, li.next')
                                if next_btn and not next_btn.get_attribute('disabled'):
                                    print(f"[调试] 尝试点击下一页按钮...", flush=True)
                                    self.driver.execute_script("arguments[0].click();", next_btn)
                                    time.sleep(2)
                                    # 检查是否成功翻页
                                    new_active = pagination.find_element(By.CSS_SELECTOR, 'li.number.active')
                                    new_active_page = int(new_active.text.strip())
                                    if new_active_page > active_page:
                                        self.current_page = new_active_page
                                        print(f"[调试] 通过下一页按钮成功翻到第 {new_active_page} 页", flush=True)
                                        continue
                                    else:
                                        print(f"[提示] 已到达最后一页", flush=True)
                                        break
                            except:
                                pass
                    except:
                        pass
                    
                    # 如果total_pages已设置，且当前页已到达，则停止
                    if self.total_pages and self.current_page >= self.total_pages:
                        print(f"已是最后一页，停止爬取", flush=True)
                        break
                    else:
                        print(f"[提示] 翻页失败，可能已到达最后一页，停止爬取", flush=True)
                        break
                
                # 检测验证码（注意：current_page已在click_next_page中更新）
                if self.detect_captcha():
                    if not self.wait_for_captcha_solve():
                        break
                
                # 不再需要手动增加current_page，因为click_next_page已经更新了
            
            print(f"\n总共提取了 {len(self.companies_data)} 条企业信息", flush=True)
            
            return {
                'title': '企知道',
                'total_results': len(self.companies_data),
                'total_pages': self.current_page,
                'companies': self.companies_data
            }
            
        finally:
            # 关闭浏览器
            if self.driver:
                self.driver.quit()
                print("\n浏览器已关闭")
    
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
    # 设置headless=False以便手动处理验证码
    spider = QizhidaoSmartSpider(headless=False)
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

