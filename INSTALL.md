# 安装指南

## 快速安装

### 1. 安装Python

确保你的系统已安装Python 3.7或更高版本：

```bash
# 检查Python版本
python --version
# 或
python3 --version
```

如果未安装，请从 [Python官网](https://www.python.org/downloads/) 下载并安装。

**Windows用户注意**：安装时请勾选 "Add Python to PATH"。

### 2. 安装依赖包

#### 方法一：使用pip直接安装（推荐）

```bash
pip install -r requirements.txt
```

#### 方法二：使用国内镜像源（如果下载慢）

```bash
# 使用清华大学镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用阿里云镜像源
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### 3. 安装Chrome浏览器（智能爬虫需要）

智能爬虫（版本4）需要Chrome浏览器：

- **下载地址**: https://www.google.com/chrome/
- **要求**: 最新稳定版

### 4. 配置ChromeDriver（智能爬虫需要）

#### Windows系统

1. 查看Chrome版本：
   - 打开Chrome浏览器
   - 地址栏输入 `chrome://version/`
   - 记录Chrome版本号（例如：120.0.6099.109）

2. 下载匹配的ChromeDriver：
   - 访问 https://chromedriver.chromium.org/downloads
   - 或使用 https://googlechromelabs.github.io/chrome-for-testing/
   - 下载与Chrome版本匹配的ChromeDriver

3. 配置ChromeDriver：
   - 方法一：将 `chromedriver.exe` 放到项目根目录
   - 方法二：将 `chromedriver.exe` 添加到系统PATH环境变量

#### Linux/macOS系统

```bash
# 下载ChromeDriver
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE/chromedriver_linux64.zip
unzip chromedriver_linux64.zip

# 移动到系统目录并设置权限
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

## 验证安装

运行以下命令验证环境是否配置正确：

```bash
# 1. 检查Python版本
python --version

# 2. 检查依赖包是否安装
python -c "import requests, bs4, selenium, pandas, openpyxl, lxml; print('✓ 所有依赖包已安装')"

# 3. 检查ChromeDriver（如果使用智能爬虫）
chromedriver --version

# 4. 测试导入爬虫类
python -c "import sys; sys.path.insert(0, 'HiSpider/Static'); from qizhidao_smart_spider import QizhidaoSmartSpider; print('✓ 爬虫类导入成功')"

# 5. 测试启动脚本
python run_qizhidao_spider.py --help
```

## 使用虚拟环境（推荐）

为避免与系统Python环境冲突，建议使用虚拟环境：

### Windows

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### Linux/macOS

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 常见问题

### Q1: 提示找不到ChromeDriver？

**解决方案**：
- 确保已下载ChromeDriver
- 将ChromeDriver添加到系统PATH，或放在项目根目录
- 确保ChromeDriver版本与Chrome浏览器版本匹配

### Q2: Selenium版本不匹配？

**解决方案**：
```bash
pip install --upgrade selenium
```

### Q3: Chrome版本与ChromeDriver不匹配？

**解决方案**：
1. 查看Chrome版本：`chrome://version/`
2. 下载匹配的ChromeDriver
3. 替换旧的ChromeDriver

### Q4: 安装依赖包失败？

**解决方案**：
1. 升级pip：`pip install --upgrade pip`
2. 使用国内镜像源（见上方）
3. 检查网络连接
4. 逐个安装：`pip install requests`，然后逐个安装其他包

### Q5: 导入模块失败？

**解决方案**：
```bash
# 确保在项目根目录运行
cd /path/to/qizhidao-spider

# 添加路径
python -c "import sys; sys.path.insert(0, 'HiSpider/Static')"
```

### Q6: Windows下pip命令不可用？

**解决方案**：
- 使用 `python -m pip` 代替 `pip`
- 或重新安装Python并勾选"Add Python to PATH"

## 完整依赖列表

| 包名 | 版本 | 用途 |
|------|------|------|
| requests | >=2.28.0 | HTTP请求库 |
| beautifulsoup4 | >=4.11.0 | HTML解析库 |
| selenium | >=4.8.0 | 浏览器自动化 |
| pandas | >=1.5.0 | 数据处理 |
| openpyxl | >=3.0.0 | Excel文件处理 |
| lxml | >=4.9.0 | XML/HTML解析器 |
| fake-useragent | >=1.2.0 | 随机User-Agent生成 |

## 下一步

安装完成后，请查看 [README.md](README.md) 了解如何使用爬虫。

## 获取帮助

如果遇到问题，请：
1. 查看 [README.md](README.md) 中的常见问题部分
2. 检查 [环境配置说明.txt](环境配置说明.txt) 或 environment.txt
3. 提交Issue到GitHub仓库

