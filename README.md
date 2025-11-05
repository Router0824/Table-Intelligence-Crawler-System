# 企知道网站爬虫

一个功能完善的企知道网站爬虫工具集，支持多种爬取模式，包括基础爬虫、高级爬虫、表格数据爬虫和智能爬虫（Selenium）。

## 功能特性

- 🚀 **多种爬虫版本**：提供4种不同版本的爬虫，适应不同场景需求
- 🔄 **自动翻页**：智能爬虫和表格爬虫支持自动翻页，可爬取所有页面数据
- 🛡️ **反爬虫机制**：高级版本包含随机User-Agent、请求重试、延迟处理等
- 🤖 **Selenium支持**：智能爬虫使用Selenium处理JavaScript渲染和验证码
- 📊 **多格式导出**：支持JSON和Excel格式导出
- ⚡ **性能优化**：缓存机制、批量解析、减少等待时间等优化

## 项目结构

```
.
├── HiSpider/
│   └── Static/
│       ├── qizhidao_spider.py          # 基础版本爬虫
│       ├── qizhidao_advanced_spider.py # 高级版本爬虫
│       ├── qizhidao_table_spider.py    # 表格数据爬虫
│       └── qizhidao_smart_spider.py    # 智能爬虫（推荐）
├── run_qizhidao_spider.py              # 快速启动脚本
├── requirements.txt                     # 依赖包列表
└── README.md                            # 项目说明文档
```

## 安装要求

### 系统要求

- Python 3.7+
- Chrome浏览器（智能爬虫需要）
- ChromeDriver（智能爬虫需要，通常会自动下载）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖包说明

- `requests` - HTTP请求库
- `beautifulsoup4` - HTML解析库
- `selenium` - 浏览器自动化（智能爬虫需要）
- `pandas` - 数据处理
- `openpyxl` - Excel文件处理
- `lxml` - XML/HTML解析器

## 使用方法

### 快速开始

```bash
# 交互式菜单
python run_qizhidao_spider.py

# 直接运行智能爬虫（推荐）
python run_qizhidao_spider.py 4 interactive

# 运行表格数据爬虫
python run_qizhidao_spider.py 3

# 运行高级版本爬虫
python run_qizhidao_spider.py 2
```

### 命令行参数

#### 基础用法

```bash
python run_qizhidao_spider.py [版本号] [选项]
```

#### 版本说明

- `1` - 基础版本爬虫（简单快速，不支持分页）
- `2` - 高级版本爬虫（包含反爬虫机制，不支持分页）
- `3` - 表格数据爬虫（支持自动翻页）
- `4` - 智能爬虫（Selenium，支持验证码和自动翻页，推荐）

#### 智能爬虫选项

```bash
# 交互模式（等待用户准备好后开始）
python run_qizhidao_spider.py 4 interactive

# 无头模式（后台运行）
python run_qizhidao_spider.py 4 headless

# 直接使用结果页面URL
python run_qizhidao_spider.py 4 https://qiye.qizhidao.com/batch-query-result?matchId=...
```

#### 表格数据爬虫选项

```bash
# 爬取前5页
python run_qizhidao_spider.py 3 5
```

### 代码示例

#### 使用智能爬虫（推荐）

```python
from HiSpider.Static.qizhidao_smart_spider import QizhidaoSmartSpider

# 创建爬虫实例
spider = QizhidaoSmartSpider(
    url=None,              # 目标URL（可选）
    headless=False,        # 是否无头模式
    interactive=False      # 是否交互模式
)

# 运行爬虫
result = spider.run(save_json=True, save_excel=True)

if result:
    print(f"爬取了 {result['data']['total_results']} 条数据")
    print(f"生成文件: {result['files']}")
```

#### 使用表格数据爬虫

```python
from HiSpider.Static.qizhidao_table_spider import QizhidaoTableSpider

# 创建爬虫实例（限制爬取5页）
spider = QizhidaoTableSpider(max_pages=5)

# 运行爬虫
result = spider.run()
```

## 爬虫版本对比

| 特性 | 基础版本 | 高级版本 | 表格爬虫 | 智能爬虫 |
|------|---------|---------|---------|---------|
| 自动翻页 | ❌ | ❌ | ✅ | ✅ |
| 反爬虫机制 | ❌ | ✅ | ✅ | ✅ |
| JavaScript支持 | ❌ | ❌ | ❌ | ✅ |
| 验证码处理 | ❌ | ❌ | ❌ | ✅ |
| 交互模式 | ❌ | ❌ | ❌ | ✅ |
| 性能优化 | ⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

## 性能优化说明

智能爬虫（qizhidao_smart_spider.py）已进行以下优化：

1. **缓存机制**：缓存分页元素和表格元素，减少重复查找
2. **批量解析**：一次性解析所有行的HTML，减少BeautifulSoup初始化次数
3. **减少等待时间**：优化各种等待时间，提升爬取速度
4. **最小化滚动**：使用最小化滚动操作，减少不必要的页面操作
5. **简化检查**：简化数据稳定性检查，减少重复验证

## 输出文件

爬虫会生成以下格式的文件：

- **JSON格式**：`qizhidao_data_YYYYMMDD_HHMMSS.json`
- **Excel格式**：`qizhidao_data_YYYYMMDD_HHMMSS.xlsx`

## 注意事项

1. **法律合规**：请确保您的使用符合相关法律法规和网站服务条款
2. **频率控制**：建议适当控制爬取频率，避免对目标网站造成压力
3. **验证码**：智能爬虫需要手动处理验证码，请在有界面模式下运行
4. **ChromeDriver**：确保Chrome浏览器和ChromeDriver版本匹配

## 常见问题

### Q: 智能爬虫无法启动？
A: 请确保已安装Chrome浏览器，并且ChromeDriver版本与Chrome版本匹配。

### Q: 爬取速度慢？
A: 智能爬虫已优化，如果仍感觉慢，可以：
- 使用无头模式（headless）
- 减少等待时间（修改代码中的sleep参数）
- 关闭调试模式（设置`_debug_mode = False`）

### Q: 遇到验证码怎么办？
A: 智能爬虫会自动检测验证码并等待用户手动解决。请在浏览器中完成验证后，程序会自动继续。

### Q: 如何爬取特定页面？
A: 使用智能爬虫的交互模式或直接提供结果页面URL：
```bash
python run_qizhidao_spider.py 4 https://qiye.qizhidao.com/batch-query-result?matchId=...
```

## 开发计划

- [ ] 添加更多反爬虫策略
- [ ] 支持更多数据导出格式
- [ ] 添加数据去重和清洗功能
- [ ] 支持并发爬取
- [ ] 添加Web界面

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

本项目采用MIT许可证。详见 [LICENSE](LICENSE) 文件。

## 作者

- 项目维护者：Router
- 项目地址：https://github.com/Router0824/Table-Intelligence-Crawler-System

## 致谢

感谢所有为这个项目做出贡献的开发者！


