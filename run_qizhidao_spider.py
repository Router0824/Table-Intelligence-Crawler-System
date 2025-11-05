"""
企知道爬虫快速启动脚本
提供交互式菜单选择不同版本的爬虫
"""

# -*- coding: utf-8 -*-
import sys
import os
import io

# 设置Windows控制台编码为UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'HiSpider', 'Static'))


def show_menu():
    """显示菜单"""
    print("\n" + "=" * 60)
    print("企知道网站爬虫 - 快速启动脚本")
    print("=" * 60)
    print("\n请选择要使用的爬虫版本:\n")
    print("1. 基础版本爬虫")
    print("   - 简单快速，适合基本数据爬取")
    print("   - 不支持分页功能")
    print()
    print("2. 高级版本爬虫")
    print("   - 包含反爬虫机制")
    print("   - 随机User-Agent、请求重试、延迟处理")
    print("   - 不支持分页功能")
    print()
    print("3. 表格数据爬虫（推荐用于分页）")
    print("   - 专门优化表格数据提取")
    print("   - 支持自动翻页功能")
    print("   - 可爬取所有页面数据")
    print()
    print("4. 智能爬虫（推荐用于复杂场景）")
    print("   - 使用Selenium处理JavaScript渲染")
    print("   - 支持验证码检测和处理")
    print("   - 支持自动翻页功能")
    print("   - 需要Chrome浏览器和ChromeDriver")
    print()
    print("0. 退出")
    print("=" * 60)


def run_basic_spider():
    """运行基础版本爬虫"""
    from qizhidao_spider import QizhidaoSpider
    print("\n正在启动基础版本爬虫...")
    spider = QizhidaoSpider()
    result = spider.run()
    
    if result:
        print("\n✓ 爬取完成！")
        print(f"  提取了 {len(result['data']['companies'])} 条企业信息")
        print(f"  生成文件: {', '.join(result['files'])}")
    else:
        print("\n✗ 爬取失败")


def run_advanced_spider():
    """运行高级版本爬虫"""
    from qizhidao_advanced_spider import QizhidaoAdvancedSpider
    print("\n正在启动高级版本爬虫...")
    spider = QizhidaoAdvancedSpider()
    result = spider.run()
    
    if result:
        print("\n✓ 爬取完成！")
        print(f"  提取了 {len(result['data']['companies'])} 条企业信息")
        print(f"  生成文件: {', '.join(result['files'])}")
    else:
        print("\n✗ 爬取失败")


def run_table_spider():
    """运行表格数据爬虫"""
    from qizhidao_table_spider import QizhidaoTableSpider
    
    max_pages = None
    is_cmdline_mode = len(sys.argv) > 1
    
    if len(sys.argv) > 2:
        # 从命令行参数获取页数
        try:
            max_pages = int(sys.argv[2])
            print(f"\n命令行模式：将爬取前 {max_pages} 页")
        except ValueError:
            pass
    
    # 只有在非命令行模式或没有指定页数时才需要交互输入
    if not is_cmdline_mode or max_pages is None:
        if max_pages is None:
            print("\n表格数据爬虫配置:")
            print("1. 爬取所有页面（默认）")
            print("2. 指定爬取页数")
            
            try:
                choice = input("\n请选择 (1/2，直接回车使用默认): ").strip()
                if choice == '2':
                    try:
                        max_pages = int(input("请输入要爬取的页数: "))
                    except ValueError:
                        print("输入无效，将爬取所有页面")
                        max_pages = None
            except (EOFError, KeyboardInterrupt):
                print("\n使用默认配置：爬取所有页面")
                max_pages = None
    else:
        # 命令行模式已指定页数，直接使用
        pass
    
    print("\n正在启动表格数据爬虫...")
    spider = QizhidaoTableSpider(max_pages=max_pages)
    result = spider.run()
    
    if result:
        print("\n✓ 爬取完成！")
        print(f"  提取了 {len(result['data']['companies'])} 条企业信息")
        print(f"  爬取了 {result['data'].get('total_pages', 1)} 页")
        print(f"  生成文件: {', '.join(result['files'])}")
    else:
        print("\n✗ 爬取失败")


def run_smart_spider():
    """运行智能爬虫"""
    from qizhidao_smart_spider import QizhidaoSmartSpider
    
    headless = False
    interactive = False
    url = None
    
    # 检查命令行参数
    is_cmdline_mode = len(sys.argv) > 1
    
    if len(sys.argv) > 2:
        # 从命令行参数获取模式
        for arg in sys.argv[2:]:
            arg_lower = arg.lower()
            if arg_lower in ['headless', 'true', '1']:
                headless = True
                print("\n使用无头模式运行智能爬虫")
            elif arg_lower in ['interactive', 'i', '交互']:
                interactive = True
                print("\n使用交互模式运行智能爬虫")
            elif arg.startswith('http'):
                url = arg
                print(f"\n使用指定URL: {url}")
    
    if not headless and not interactive:
        print("\n使用默认配置：有界面模式（便于处理验证码）")
    
    # 只有在非命令行模式时才需要交互输入
    if not is_cmdline_mode:
        if not headless:
            print("\n智能爬虫配置:")
            print("1. 有界面模式（推荐，便于处理验证码）")
            print("2. 无头模式（后台运行）")
            print("3. 交互模式（等待用户准备好后开始爬取）")
            
            try:
                choice = input("\n请选择 (1/2/3，直接回车使用有界面模式): ").strip()
                if choice == '2':
                    headless = True
                elif choice == '3':
                    interactive = True
            except (EOFError, KeyboardInterrupt):
                print("\n使用默认配置：有界面模式")
                headless = False
    
    print("\n正在启动智能爬虫...")
    if interactive:
        print("注意：交互模式已启用，请在浏览器中准备好结果页面后输入'开始爬取'")
    else:
        print("注意：如果遇到验证码，请在浏览器中手动完成验证")
    
    spider = QizhidaoSmartSpider(url=url, headless=headless, interactive=interactive)
    result = spider.run()
    
    if result:
        print("\n✓ 爬取完成！")
        print(f"  提取了 {len(result['data']['companies'])} 条企业信息")
        print(f"  爬取了 {result['data'].get('total_pages', 1)} 页")
        print(f"  生成文件: {', '.join(result['files'])}")
    else:
        print("\n✗ 爬取失败")


def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
    else:
        choice = None
    
    while True:
        if choice is None:
            show_menu()
            try:
                choice = input("\n请输入选项 (0-4): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\n程序退出")
                break
        
        if choice == '0':
            print("\n退出程序")
            break
        elif choice == '1':
            run_basic_spider()
            if len(sys.argv) > 1:  # 命令行模式，运行一次就退出
                break
        elif choice == '2':
            run_advanced_spider()
            if len(sys.argv) > 1:
                break
        elif choice == '3':
            run_table_spider()
            if len(sys.argv) > 1:
                break
        elif choice == '4':
            run_smart_spider()
            if len(sys.argv) > 1:
                break
        else:
            if choice is not None:
                print("\n无效选项，请重新选择")
            if len(sys.argv) > 1:  # 命令行模式，无效选项也退出
                print("可用选项: 1, 2, 3, 4")
                break
        
        if choice != '0' and choice is not None:
            if len(sys.argv) > 1:  # 命令行模式不等待输入
                break
            try:
                input("\n按回车键继续...")
            except (EOFError, KeyboardInterrupt):
                print("\n\n程序退出")
                break
        
        choice = None  # 重置选择，继续循环


if __name__ == "__main__":
    try:
        # 显示使用说明
        if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
            print("\n企知道爬虫快速启动脚本")
            print("=" * 60)
            print("\n使用方法:")
            print("  python run_qizhidao_spider.py              # 交互式菜单")
            print("  python run_qizhidao_spider.py 1            # 运行基础版本爬虫")
            print("  python run_qizhidao_spider.py 2            # 运行高级版本爬虫")
            print("  python run_qizhidao_spider.py 3 [页数]     # 运行表格数据爬虫（可选指定页数）")
            print("  python run_qizhidao_spider.py 4 [headless|interactive|URL] # 运行智能爬虫")
            print("    - headless: 无头模式")
            print("    - interactive: 交互模式（等待用户准备好）")
            print("    - URL: 直接使用结果页面URL（如: https://.../batch-query-result?...）")
            print("\n示例:")
            print("  python run_qizhidao_spider.py 3 5          # 爬取前5页")
            print("  python run_qizhidao_spider.py 4 headless   # 无头模式运行")
            print()
            sys.exit(0)
        
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()

