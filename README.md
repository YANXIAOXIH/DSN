
# Cloudflare IP 域名信息提取器

[![CI Status](https://github.com/YANXIAOXIH/DSN/actions/workflows/main.yml/badge.svg)](https://github.com/YANXIAOXIH/DSN/actions/workflows/main.yml)

一个使用 GitHub Actions 自动从动态网页提取特定域名解析出的 IP 地址及其对应的国家/地区信息，并将结果保存到仓库中的项目。

## 项目简介

本项目旨在解决从包含动态加载内容（如 JavaScript 渲染的搜索结果）的网页中抓取数据的需求。具体来说，它会定期访问 [https://www.nslookup.io/](https://www.nslookup.io/) 网站，查询指定域名（当前为 `bpb.yousef.isegaro.com`）的 DNS A 记录，提取解析出的 IP 地址和这些 IP 归属的国家/地区。提取到的国家名会进一步被翻译成中文。

最终结果以 `IP#国家(中文)` 的格式，去重后保存到仓库根目录下的文本文档。

## 主要功能

*   **动态网页抓取**：使用 Python 和 Selenium (配合 selenium-stealth) 模拟浏览器行为，加载并解析 JavaScript 动态渲染的内容。
*项目。

## ✨ 功能特性 (Features)

*   **自动抓取**: 定时通过 GitHub Actions 自动访问 [nslookup.io](https://www.nslookup.io/) 查询特定域名的 DNS 记录。
*   **动态内容处理**: 使用 Selenium 和 Chrome WebDriver 模拟浏览器行为，处理 JavaScript 动态加载的内容。
*   **智能反爬虫**: 集成 `selenium-stealth` 以降低被网站识别为机器人的风险。
*   **IP 与国家提取**: 使用正则表达式精确匹配并提取 IP 地址和其所在的国家/地区。
*   **国家名称翻译**: 将提取到的英文国家名通过 `deep_translator` (Google Translate) 翻译为中文。
*   **结果去重与格式化**: 对提取到的 `IP#国家(中文)` 结果进行去重，并按 IP 地址排序。
*   **自动更新**: 将提取并处理后的结果自动提交回 GitHub 仓库。
*   **调试友好**: 在 Action 运行失败或特定阶段自动保存截图和页面源码作为 Artifacts，方便调试。

## 🎯 目标网页与提取内容 (Target Website & Extraction)

*   **目标网页**: `https://www.nslookup.io/domains/bpb.yousef.isegaro.com/dns-records/` (主要关注 Google DNS 视图)
*   **提取内容**:
    *   A 记录的 IPv4 地址
    *   该 IP 地址对应的国家/地区名称 (中文)
*   **输出格式**: `IP地址#国家中文名` (例如: `1.2.3.4#美国`)
*   **输出文件**: `文本文档`

## 🚀   **信息提取**：通过正则表达式从 HTML 源码中精确匹配 IP 地址和其对应的地理位置信息（城市、州/省、国家）。
*   **数据处理**：
    *   提取英文国家名。
 如何工作 (How It Works)

1.  **GitHub Action 触发**: 工作流按预定时间 (例如每12小时) 或手动触发。
2.  **环境设置**: 在 Ubuntu Runner 上设置 Python, Chrome 浏览器, ChromeDriver。
3.  **依赖安装**: 安装必要的 Python 库 (`selenium`, `requests`, `selenium-stealth`, `deep_translator`)。
4.  **执行 Python 脚本 (`main.py`)    *   使用 `deep_translator` (调用 Google Translate) 将英文国家名翻译为中文。
    **:
    *   使用 Selenium (配合 `selenium-stealth`) 启动一个无头 Chrome 浏览器。
    *   对特定翻译结果进行修正（例如："韩国，共和国" -> "韩国"；"英国英国和北爱尔兰" -> "英国"）。
    *   对提取到的 `IP#国家` 结果*   导航到目标 URL。
    *   尝试处理可能出现的 Cookie 同意弹窗。
    *   切换到 "Google DNS" 选项卡。
    *   等待 DNS 记录动态加载完成。
    *进行去重。
*   **自动化更新**：利用 GitHub Actions 实现：
    *   定时执行（当前配置为每12小时一次）。
    *   如果文本文档内容发生变化，则获取页面 HTML 源码。
    *   使用正则表达式从 HTML 中提取 IP 地址和对应的英文国家名。
自动提交 (commit) 并推送 (push) 更新到仓库。
*   **结果输出**：提取到的IP和英文国家名翻译成中文。
    *   对结果进行去重和格式化。
    *   将最终结果写入文本文档。
5.  **结果提交**: 以 `IP#国家` 的格式，按 IP 排序后，保存在仓库根目录的文本文档中。

## 技术栈

*   **Python 3.10+**txt` 文件内容发生变化，Action 会自动将其 commit 并 push 回本仓库。
6.  **产
*   **Selenium**: 浏览器自动化，处理动态网页。
*   **selenium-stealth**: 增强物上传**: 无论成功与否，都会上传运行过程中的调试截图和 HTML 源码作为 Artifacts。 Selenium，使其更难被反爬虫机制检测。
*   **Requests**: (虽然主要使用 Selenium，但保留

## 🛠️ 技术栈 (Tech Stack)

*   **语言**: Python 3.10+
*   **核心库**:
    *   `selenium`: 浏览器自动化，处理动态网页。
    *以备不时之需)。
*   **re (正则表达式)**: 用于从 HTML 中匹配和提取数据   `selenium-stealth`: 增强 Selenium 的隐匿性，反反爬虫。
    *   `。
*   **deep_translator**: 用于将英文国家名翻译成中文。
*   **GitHub Actionsrequests`: (备用) HTTP 请求。
    *   `re`: 正则表达式模块，用于数据提取。
    **: 用于自动化执行、构建和更新。

## 如何工作

1.  **GitHub Action 触发**：*   `deep_translator`: 用于将国家名翻译成中文 (使用 Google Translate 引擎)。
*   **CI
    *   根据 `.github/workflows/main.yml` 中定义的 `schedule` (定时任务) /CD**: GitHub Actions

## ⚙️ 配置与使用 (Configuration & Usage)

1.  **Fork触发。
    *   也可以通过 `workflow_dispatch` 手动触发。
2.  **(可选) 修改目标   Chrome 浏览器和对应的 ChromeDriver 被安装。
    *   所需的 Python 依赖 (`selenium`, `requests`,域名**: 如果需要查询不同的域名，请修改 Python 脚本中的 `url` 变量。
     `selenium-stealth`, `deep_translator`) 被安装。
3.  **Python 脚本执行
    # 在 main.py 的 __main__ 部分
    url = "https://www.nslookup.main.py`)**：
    *   初始化 Selenium WebDriver (Chrome 无头模式) 并应用 `selenium-steio/domains/YOUR_TARGET_DOMAIN.COM/dns-records/"
3.  **(可选) alth`。
    *   导航到目标 URL：`https://www.nslookup.io/domains/bp调整 Action 触发频率**: 修改 `.github/workflows/main.yml` 文件中的 `schedule` cron 表达式。
b.yousef.isegaro.com/dns-records/`。
    *   尝试快速    ```yaml
    on:
      schedule:
        - cron: '0 */12 * * *处理可能存在的 Cookie 同意弹窗。
    *   显式点击 "Google DNS" 选项卡以' # 当前为每12小时
    # ...
    ```
4.  **(可选) 配置 Git确保数据源一致性。
    *   等待页面 JavaScript 加载并渲染 DNS 记录。
    *   获取完整的页面 HTML 源码。
    *   使用预定义的正则表达式从 HTML 中提取所有 A 记录的 IP 用户信息**: 为了 Action 能够提交更改，建议在仓库的 "Settings" -> "Secrets and variables" -> 地址、城市和英文国家名。
    *   对提取到的每个英文国家名，调用翻译函数（ "Actions" 中添加以下 Secrets (如果需要自定义提交者信息):
    *   `GIT_USER_EMAIL`:内置缓存）将其翻译成中文。
    *   对特定翻译结果进行标准化处理。
    *   将 ` 你的 Git 提交邮箱
    *   `GIT_USER_NAME`: 你的 Git 用户名
    如果未设置，Action 将使用默认的 GitHub Action 用户信息。