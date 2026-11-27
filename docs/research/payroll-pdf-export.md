# 中文工资条 PDF 与批量导出技术调研

- **Ticket**: [#57](https://github.com/nasa-du/anysys-hr/issues/57)（Wayfinder research）
- **上游地图**: [#45](https://github.com/nasa-du/anysys-hr/issues/45)
- **下游决策**: [#50 工资条与报表定稿](https://github.com/nasa-du/anysys-hr/issues/50)
- **状态**: 非规范性调研输入；最终决策以薪资 spec/ADR 为准。2026-11-27 合并到 `main`；实验脚本为 throwaway，未入库。
- **日期**: 2026-11-27
- **实验环境**: WSL2 Linux 6.18，12 vCPU，15 GiB RAM；Python 3.14.4；WeasyPrint 70.0；ReportLab 5.1.2；Playwright 1.65.2 / Chromium 1254；pypdf 7.2.0；openpyxl 3.1.5

## 结论速览

**推荐：WeasyPrint 70 + Jinja2 HTML/CSS + 静态 TrueType 版 Noto Sans SC（SIL OFL 1.1），服务端生成。** 单人工资条生成 1 页 A4 PDF；批量导出按“每位员工一个 PDF”打包 ZIP，另提供“一人一页的合并 PDF”供批量打印/归档。不引入无头浏览器，不新增 Excel 库。

关键实测结果（500 人、12 核桌面/WSL2）：

| 路径 | 500 份独立 PDF 耗时 | 单份大小 | 500 份 ZIP | 字体嵌入 | 文本抽取 |
|---|---:|---:|---:|---|---|
| **WeasyPrint + 静态 TTF，4 进程** | **19.2 s** | **40 KB** | **19.6 MB** | Type0 子集嵌入 | 中文正确 |
| WeasyPrint + 静态 TTF，单进程 | 67.4 s | 40 KB | 19.6 MB | Type0 子集嵌入 | 中文正确 |
| WeasyPrint + Noto CJK OTF | 约 93 s（100 份 18.7 s 推算） | 300 KB | 约 134 MB | Type0 子集嵌入 | 中文正确 |
| Chromium + 静态 TTF | 41.7 s | 40 KB | 19.2 MB | Type0 子集嵌入 | 出现兼容汉字（如 工→⼯） |
| Chromium + OTF | 约 73 s（3 份 145 ms 推算） | 219 KB | 约 110 MB | **Type3 轮廓，非字体嵌入** | 出现兼容汉字 |
| ReportLab + 静态 TTF | **5.8 s** | **49 KB** | 23.4 MB | TrueType 子集（FontFile2） | 中文正确 |

推荐不是“性能最快”，而是**综合集成成本、字体可移植性、中文文本正确性和部署重量**后的选择。ReportLab 单进程最快，但需要手写版式；Chromium 合并 PDF 最快，但部署重且中文字体嵌入有格式陷阱；WeasyPrint 在 FastAPI/Jinja2 技术栈中成本最低、行为最可控。

## 1. 现有工程约束

先确认仓库现状，避免推荐与现有依赖冲突：

| 事实 | 依据 |
|---|---|
| 后端 Python `>=3.14`，FastAPI + SQLModel + PostgreSQL | `backend/pyproject.toml` |
| 已有 `jinja2>=3.1.4`，用于邮件模板 | `backend/pyproject.toml`、`backend/app/utils.py` |
| 已有 `openpyxl>=3.1.5`，目前只用于 **XLSX 导入解析**，没有 XLSX 导出代码 | `backend/app/services/attendance/import_parsing.py`、`backend/pyproject.toml` |
| 没有 PDF 库，没有 Playwright Python 运行时依赖 | `backend/pyproject.toml`；全仓检索无 weasyprint/reportlab/pypdf/fpdf |
| 考勤导出是流式 CSV，UTF-8 BOM，`StreamingResponse` | `backend/app/api/routes/attendance/exports.py`、`backend/app/services/attendance/exports.py` |
| Docker 基础镜像 `python:3.14`（Debian），生产启动 4 个 uvicorn worker | `backend/Dockerfile` |
| 前端 React 19 + TanStack Router；`@playwright/test 1.63.0` 仅是 E2E 测试依赖 | `frontend/package.json` |
| 没有 Celery/RQ/Redis/BackgroundTasks 任务基础设施 | 全仓检索无任务队列 |
| UI 中文 only（ADR-0002）；考勤不写工资，工资侧只读 | `docs/attendance.md`、`docs/adr/0002-chinese-only-no-i18n.md` |

因此本调研的默认假设是：**工资条 PDF 是工资核算结果的只读投影**，不重新计算工资；批量导出属于偶发的重操作，但当前没有异步任务系统。

## 2. 候选方案对比

| 维度 | WeasyPrint 70 | Playwright + Chromium | ReportLab 5.x | 前端打印 |
|---|---|---|---|---|
| 与 FastAPI 集成 | 纯 Python 调用，可直接在服务层使用 | 需要浏览器进程/生命周期管理，通常要独立服务或浏览器池 | 纯 Python，直接调用 | 无服务端文件；浏览器手动打印 |
| 中文嵌入 | Pango/fontconfig；**自动嵌入并按字形子集化**；TTF/OTF 均可 | 依赖字体格式：静态 TTF 可嵌入 Type0；OTF/CFF 和 webfont 会退化为 Type3 轮廓 | `TTFont` 支持 TrueType 子集（FontFile2）；**CFF OTF 不支持**；内置 CJK CID 字体不嵌入 | 取决于客户端字体；输出不稳定 |
| 分页/表格跨页 | CSS Paged Media：`@page`、`break-*`、`thead` 重复；实测通过 | 浏览器打印 CSS；实测 `thead` 重复；`page.pdf` 支持 `pageRanges` | `Table(repeatRows=1)` 可靠；需要手写 Platypus 布局 | 依赖浏览器打印预览；批量不可控 |
| 每人一页 | `break-after: page`，实测 500 页严格对应 500 人 | 同左，实测 500/500 | 手动 `PageBreak` 或表格分页 | 需人工逐人打印 |
| 500 份性能 | 67 s 单进程 / 19 s 4 进程；合并 500 页 43 s | 42 s 逐份；合并 500 页 2.6 s | **5.8 s** | 无法批量 |
| PDF 大小（每份） | 40 KB（静态 TTF）/ 300 KB（OTF） | 40 KB（静态 TTF）/ 219 KB（OTF，Type3） | 49 KB | 取决于浏览器 |
| 部署依赖 | Pango/HarfBuzz/fontconfig + 字体；无需浏览器 | Chromium 413 MB + headless shell 283 MB + 系统库 + Playwright；进程管理复杂 | 纯 Python，无系统库 | 无服务端依赖 |
| 许可证 | BSD-3-Clause | Playwright Apache-2.0；Chromium BSD-3 及第三方 | BSD-3-Clause | 浏览器/操作系统许可 |
| 结论 | **推荐** | 备选；仅当必须复用浏览器渲染时 | 备选；性能/文本正确性优先时 | 仅可作为单人“打印”辅助，不做批量 |

### 2.1 其他候选

- **fpdf2**：纯 Python、支持 TTF 子集，但版式 API 比 ReportLab 更低层，中文字体仍需自带 TTF；许可证 LGPL-3.0，企业分发需评估。未进入最终候选。
- **Typst**：排版质量好、速度快，但需要额外二进制/工具链，CSS/HTML 复用为零；Python 绑定和部署稳定性未在本项目验证。未进入最终候选。
- **LibreOffice headless**：可把 DOCX/ODT 转 PDF，但镜像大、启动慢、版式不可控；不适合按人批量。
- **wkhtmltopdf**：基于已停止维护的 Qt WebKit，安全与中文排版风险高；不推荐。
- **xhtml2pdf**：底层仍是 ReportLab，CSS 支持弱，不能解决版式/字体问题；不推荐。

## 3. 推荐方案：WeasyPrint + Jinja2 + 静态 TTF

### 3.1 总体架构

```text
工资核算结果（已持久化/快照）
        │
        ▼
Jinja2 工资条 HTML 模板（A4、中文、公司抬头、月份、工号）
        │
        ▼
WeasyPrint（HTML/CSS → PDF，字体子集嵌入）
        │
        ├─ 单人：application/pdf（StreamingResponse/Response）
        ├─ 批量：每人一个 PDF → zipfile → SpooledTemporaryFile → ZIP 流
        └─ 批量打印/归档：一份合并 PDF（每人一页）
```

关键原则：

1. **PDF 是只读投影**：从已持久化的工资结果/快照读取，不在生成 PDF 时重新计算工资。这样工资条可复现、可审计，也避免与工资计算模块耦合。
2. **版式用 HTML/CSS 表达**：后端已有 Jinja2，模板可版本化；不需要 ReportLab 的 Python 布局代码。
3. **单人同步、批量受控**：单人生成 <1 s；批量在进程池中渲染并流式返回 ZIP；超过上限再考虑异步任务表（当前无队列基础设施）。
4. **不引入无头浏览器**：减少镜像体积、进程管理和字体格式不确定性。

### 3.2 中文字体策略

#### 推荐字体

- **Noto Sans SC**（思源黑体同源），SIL Open Font License 1.1。
- 需要 **Regular 400 + Bold 700 两个静态 TrueType（glyf）字体**，不要只给一个 Regular 让渲染器合成粗体。
- 字体文件与 `OFL.txt` 一起纳入部署（如果选择 vendoring）；若使用 Debian 包 `fonts-noto-cjk`，许可证文件随包安装。

#### 为什么是“静态 TTF”，不是 OTF、不是 variable TTF

这是本次实验最重要的发现之一。同一份 HTML、同一台机器：

| 字体格式 | 单份 PDF | 500 份耗时（单进程） | 说明 |
|---|---:|---:|---|
| 静态 TrueType（Regular+Bold） | **40 KB** | 67 s（134 ms/份） | 推荐 |
| Noto Sans CJK SC OTF（CFF） | 300 KB | 约 93 s（187 ms/份，100 份实测推算） | WeasyPrint 可正常嵌入，但 PDF 大 7.5 倍 |
| Noto Sans SC variable TTF | 40 KB | **约 680 s（1.36 s/份，3 份实测推算）** | WeasyPrint 每份都实例化可变字体，慢约 10 倍；不要用于批量 |

OTF 的 300 KB 不是“没子集化”，而是 CFF 子集本身比 TrueType glyf 子集大。WeasyPrint 对两者都会嵌入 Type0 子集，文本抽取均正确；但 ZIP 场景下 500 份从 20 MB 变成约 134 MB，差距不可忽略。

**落地方式（二选一，需 #50 定稿）：**

- **A. Vendoring（推荐，确定性最好）**：将静态 Regular/Bold TTF 放入仓库或构建上下文（约 20 MB），配合 `OFL.txt`。适合“版本固定、离线可构建、PDF 字节稳定”的要求。
- **B. 构建时生成**：从上游 `NotoSansSC[wght].ttf`（约 17 MB，variable TTF）用 `fontTools.varLib.instancer` 生成 `wght=400/700` 静态实例。`fontTools` 已是 WeasyPrint 的依赖，不需要额外运行时库。需要固定上游下载 URL + 校验和，并在构建日志中记录字体来源。
- **C. 兜底**：直接安装 Debian `fonts-noto-cjk`（Noto Sans CJK SC OTF）。Docker 改动最小，但每份 300 KB、500 份约 134 MB；适合“先上线、后优化”的 MVP。

> OFL 允许修改字体，但 **Modified Version 不得使用 Reserved Font Name（Noto Sans SC 的 OFL 文本中保留名为 “Source”）**，且修改版本必须继续以 OFL 分发。若采用 B，保留 `Noto Sans SC` 名称、不声称与 Adobe/Google 官方版本完全一致，并保留版权与许可文本即可；法律上仍建议在发布前做一次许可证审查。

#### 明确不要使用

- **Microsoft YaHei / 微软雅黑、SimSun / 宋体**：专有字体，当前仓库没有分发许可；Docker 中也不应依赖。实验机上虽已安装，但仅用于对比 Chromium 的嵌入路径，未进入任何交付物。
- **ReportLab 内置 `STSong-Light` 等 CID 字体**：ReportLab 文档明确说明这类 Asian Language Pack 字体“不需要嵌入，阅读器自带”；实测生成的 PDF 仅 2.4 KB，字体 `embedded=False`。在没有安装 Asian Font Pack 的阅读器/移动端会缺字或替换。
- **`full_fonts=True`**：WeasyPrint 默认 `full_fonts=False`，按字形子集嵌入；打开后会嵌入完整字体。实测单份从 39,956 字节变为 12,959,401 字节（约 324 倍），绝不要用于工资条。

#### 许可证要点

- Noto Sans SC / Noto Sans CJK 使用 **SIL OFL 1.1**。OFL 第 2 条允许字体“bundled, redistributed and/or sold with any software”，只要每份包含版权声明和许可证；第 5 条明确“**要求字体保持 OFL 不适用于使用该字体创建的文档**”。因此把字体子集嵌入 PDF 是允许的，PDF 本身不会被 OFL “传染”。
- 如果打包字体文件，必须在交付物中保留 `OFL.txt` / 版权声明；Debian 包会在 `/usr/share/doc/fonts-noto-cjk/copyright` 提供。
- Source Han Sans（思源黑体）同样是 OFL 1.1，保留名 “Source”；可以作为 Noto Sans SC 的替代。
- 字体许可证是“允许嵌入”，不等于“允许把字体文件单独售卖/再授权”；不要从系统中抽取微软雅黑等专有字体打包。

### 3.3 分页、表格跨页与“每人一页”

WeasyPrint 官方声明支持 CSS Paged Media 的 `@page` 规则、页面尺寸、页边距、命名页、页计数器，以及 CSS Fragmentation 的 `break-before` / `break-after` / `break-inside`（页面维度）。我们的实测：

- A4 工资条模板：`@page { size: A4; margin: 11mm 13mm 12mm; }`，每位员工 `<section class="slip">` + `break-after: page`。
- 500 人合并文档：**500 页，500/500 页均包含对应工号，无空白页**（WeasyPrint 与 Chromium 均验证）。
- 70 行跨页表格：2 页；`thead { display: table-header-group; }` 使第 2 页仍出现表头；`tr { break-inside: avoid; }` 防止行被拆开。
- 单人工资条正常内容严格 1 页；如果某员工项目过多导致溢出，WeasyPrint 会自动续页并重复表头，不会截断。是否允许“一人两页”是 #50 的产品决策；技术上可支持，但“每人一页”应作为默认版式约束，并在测试中断言 `page_count == 1`。

版式建议（供 #50 参考）：

- 公司抬头 + 工资所属期 + 发放日期；员工姓名、工号、部门、岗位、考勤周期；应发项目表、扣款项目表、实发合计（含大写）；页脚说明。
- 金额右对齐、千分位、两位小数；使用 `tabular-nums`（WeasyPrint 支持有限，若告警可忽略或改用固定宽度）。
- 表头重复和行不跨页是硬要求；不要用绝对定位拼版。
- 合并 PDF 的页序按工号排序，便于装订/分发。

### 3.4 批量 ZIP

推荐实现：

```python
with tempfile.SpooledTemporaryFile(max_size=64 * 1024 * 1024) as spool:
    with zipfile.ZipFile(spool, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for employee in employees:
            pdf_bytes = render_one(employee)  # WeasyPrint
            zf.writestr(safe_name(employee), pdf_bytes)
    spool.seek(0)
    # StreamingResponse 按 1 MiB 块读取 spool
```

实测（500 份 WeasyPrint 静态 TTF PDF）：

| 方式 | ZIP 大小 | 组装耗时 | 读取耗时 |
|---|---:|---:|---:|
| `ZIP_STORED` | 20.1 MB | 0.054 s | 0.003 s |
| `ZIP_DEFLATED` | 19.6 MB | 0.427 s | 0.002 s |

PDF 本身已压缩，deflate 只节省约 2–3%，但 0.4 s 的 CPU 成本可接受；如果追求最低延迟可用 `ZIP_STORED`。`SpooledTemporaryFile` 在 20 MB 时留在内存，OTF 方案约 134 MB 时会自动落盘，避免一次性占用大内存。

文件名与隐私：

- ZIP 内部文件名建议 `工资条-2026-10-{employee_no}-{name}.pdf`；Python `zipfile` 会写 UTF-8 文件名标志，Linux/macOS/Windows 10+ 一般正常。对旧版 Windows 或邮件网关，建议同时提供工号/ASCII 文件名。
- 必须清洗文件名中的 `/`、`\`、`..`、控制字符；姓名中的特殊字符不能成为路径。
- HTTP `Content-Disposition` 对外层 ZIP 用 ASCII fallback（如 `payroll-2026-10.zip`），如需中文文件名用 RFC 5987 `filename*=UTF-8''...`。
- **Python 标准库 `zipfile` 只能读取加密 ZIP，不能创建加密 ZIP**（官方文档明确说明）。如果 #50 要求“工资条 ZIP 必须带密码”，需要评估 `pyzipper`（AES）或 7z 外部工具；这属于新增依赖/运维决策，当前不在推荐路径内。
- PDF 级密码：WeasyPrint 本身不提供 PDF 加密选项；如必须加密，可在生成后用 **pypdf**（BSD-3，`PdfWriter.encrypt`，支持用户/所有者密码和权限）后处理。ReportLab 则原生支持 `StandardEncryption`。这会增加每份 PDF 的处理时间，需另做基准。

### 3.5 性能

完整实测（同一台 12 vCPU / 15 GiB WSL2 机器，合成数据，未包含数据库查询和网络传输）：

| 场景 | 耗时 | 吞吐 | 说明 |
|---|---:|---:|---|
| WeasyPrint 500 份，单进程 | 67.4 s | 7.4 份/s | 134.8 ms/份 |
| WeasyPrint 500 份，4 进程 | **19.2 s** | **26.1 份/s** | 3.5× 加速；输出字节与单进程一致 |
| WeasyPrint 合并 500 页 | 43.1 s | 86 ms/页 | 单份 1.89 MB；字体只嵌一次 |
| Chromium 500 份 | 41.7 s | 12.0 份/s | 83.4 ms/份；浏览器启动约 0.09 s |
| Chromium 合并 500 页 | **2.6 s** | 5.3 ms/页 | 单份 1.55 MB；吞吐最高 |
| ReportLab 500 份 | **5.8 s** | **85.8 份/s** | 11.65 ms/份 |

结论：

- **单份工资条**：WeasyPrint 约 0.13 s（含字体子集化），远低于 1 s 预算；不需要优化。
- **500 人 ZIP**：WeasyPrint 4 进程约 19 s；加 ZIP 组装约 0.4 s；加数据库查询/网络传输仍应在 30 s 量级。建议 #50 把“500 人批量 ZIP ≤ 30 s（目标机器）”写入性能预算，并在 staging 复测。
- **500 人合并 PDF**：WeasyPrint 约 43 s；Chromium 约 2.6 s，但 Chromium 的部署/字体代价高。如果“批量打印一份合并 PDF”是高频主路径，可重新评估 Chromium 仅用于合并 PDF；当前不建议为它引入第二套引擎。
- **并发注意**：生产是 4 个 uvicorn worker。若每个 worker 内再开 4 个渲染进程，最多 16 个 CPU 密集进程，可能超过实际 vCPU 数。建议按目标机器 vCPU 设置**全局/每 worker 的渲染并发**（例如每 worker 2 个，或独立进程池），并在 staging 压测；不要默认 `processes = uvicorn_workers × 4`。
- **内存**：WeasyPrint 500 份单进程峰值约 153 MB（父进程）；4 进程时每个子进程还会各占一份字体/文档内存，估算总量 4×150–250 MB。批量上限和进程数要一起定。

### 3.6 部署依赖（Docker）

WeasyPrint 官方要求：Python ≥ 3.11、Pango ≥ 1.44、pydyf、CFFI、tinyhtml5、tinycss2、cssselect2、Pyphen、Pillow、fontTools ≥ 4.59.2。Debian/Ubuntu 下使用 wheel 安装只需：

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
      fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
```

本次在 `python:3.14`（与 `backend/Dockerfile` 相同的 base）上做了真实 Docker 冒烟：

- `apt` 包名在 Debian trixie 上可用；`fonts-noto-cjk` 安装后 `fc-match 'Noto Sans CJK SC'` 正确匹配 Regular/Bold。
- 使用系统 OTF：PDF 299,981 字节，字体 `Type0 / Noto-Sans-CJK-SC`、`Noto-Sans-CJK-SC-Bold`，`embedded=True`，中文文本抽取正确。
- 使用挂载的静态 TTF + `@font-face`：PDF 39,956 字节，字体 `Type0 / Payroll`、`Payroll-Bold`，`embedded=True`，中文文本抽取正确。
- 镜像大小：`python:3.14` 基础 1,541.8 MB；冒烟镜像 1,823.0 MB，**增加约 281 MB**。其中 `fonts-noto-cjk` 安装约 91,217 KB（约 89 MB），`/usr/share/fonts/opentype/noto` 约 90 MB；其余为 Pango/HarfBuzz/fontconfig 和 Python 依赖（裸镜像 site-packages 约 93 MB，含 pypdf；在现有后端 venv 中增量会更小）。
- 如果不使用 `fonts-noto-cjk`、只带静态 TTF，可省约 90 MB 字体包，但仍需 Pango 系列系统库。

对比 Chromium：本机 Playwright 浏览器缓存 `chromium-1254` 约 **413 MB**，`chromium_headless_shell-1254` 约 **283 MB**；这还不含 Playwright 包和系统依赖。Playwright 官方 Docker 镜像说明其包含浏览器和系统依赖，且定位为测试/开发用途，并建议固定版本。对生产后端而言，这是明显的额外重量与进程管理成本。

其他部署注意：

- **字体版本固定**：apt 包或 vendored TTF 的版本变化会改变字形/断行；PDF 快照/审计场景应固定字体版本。测试断言用文本、页数、关键字段，不要做像素级黄金文件。
- **不要依赖宿主机字体**：Docker 中显式安装/COPY 字体；开发机可缺字体，故模板必须声明明确的 family + fallback，并在 CI 做一次中文渲染冒烟。
- **locale/timezone**：工资条日期由业务数据决定；WeasyPrint 不依赖系统 locale，但建议容器 `TZ=Asia/Shanghai` 或显式传入格式化后的日期字符串。
- **PDF/A（可选）**：WeasyPrint 支持 `pdf/a-1b`、`pdf/a-2b`、`pdf/a-3b`、`pdf/a-2u`、`pdf/a-3u` 等变体；如果工资条需要长期归档，可评估 `pdf_variant="pdf/a-3u"`。当前 #50 未要求，先不作为默认。

### 3.7 与 FastAPI 的集成方式

建议沿用现有考勤导出的模式，但把 CPU 密集的渲染移出事件循环：

- **单人 PDF**：同步 `def` 路由（FastAPI 会放线程池），查询已持久化结果 → 渲染 bytes → `Response(content=pdf, media_type="application/pdf")` 或 `StreamingResponse`。不要用 `async def` 直接调用 WeasyPrint。
- **批量 ZIP**：
  1. 在请求内一次性查询公司+月份+筛选结果，**关闭/释放数据库 session**；
  2. 将数据传入 `ProcessPoolExecutor`（或模块级进程池），每进程创建自己的 `FontConfiguration`；
  3. 主进程把返回的 PDF bytes 写入 `SpooledTemporaryFile` 的 ZIP；
  4. `StreamingResponse` 按块返回 ZIP。
- **不要**在渲染期间持有数据库事务/连接；500 人渲染 20–70 s，长事务会阻塞其他请求并放大连接池压力。
- **批量上限**：建议 MVP 设 500 人/请求硬上限；超过上限返回 4xx 或要求拆分。若产品需要 1000+ 或需要“提交后稍后下载”，当前没有任务队列，需要新增数据库任务表 + 后台 worker（FastAPI `BackgroundTasks` 在 4 worker/重启场景下不可靠，不建议单独使用）。
- **代理超时**：500 人 ZIP 约 20 s，合并 PDF 约 43 s；确认 Traefik/反向代理的响应超时和缓冲行为，避免网关提前断开。流式 ZIP 可以降低首字节延迟，但渲染仍在返回前完成；若代理超时较紧，考虑先返回 202 + 任务状态。
- **响应头**：`Content-Type: application/pdf` / `application/zip`；`Content-Disposition: attachment`；文件名 ASCII fallback；加 `Cache-Control: no-store`（工资条含 PII，不应被中间缓存）。
- **权限**：复用工资/考勤的 `attendance_access` 或工资模块的权限依赖；#50 明确“本期无 RBAC、所有登录用户可见全部”，但即使如此也要记录导出审计（谁、何时、公司、月份、筛选条件、人数），不要把金额写进普通日志。
- **审计**：如果 #50 要求“谁导出了什么”，建议一张轻量导出审计表（user_id, company_id, month, filter_hash, employee_count, format, created_at），不存 PDF 内容；失败/超时也记录。

### 3.8 Excel 导出

- 仓库已依赖 **openpyxl 3.1.5（MIT）**，目前只用于 XLSX 导入解析；**没有 XLSX 导出代码**。不要为了导出引入 xlsxwriter 等新库。
- 数百到数千行用普通 `Workbook` 即可；更大数据量用 `Workbook(write_only=True)`，官方文档说明读写优化模式可以“near constant memory consumption”处理大量数据。write-only 模式支持 `WriteOnlyCell` 设置样式/数字格式。
- 工资条/明细的金额写成**数值单元格**并设置 `number_format = '#,##0.00'`，不要写成带千分位的字符串，否则 Excel 无法求和；中文姓名/部门是 Unicode 字符串，不需要字体嵌入。
- 建议工作表：`工资明细`（一行一人或一行一项目，按 #50 字段定稿）、`部门汇总`（如需要）、`说明`（口径、月份、生成时间）。CSV 继续保留给程序/导入用；XLSX 给 HR 人工使用。
- openpyxl 写大文件时官方建议安装 `lxml`；当前后端依赖没有 `lxml`。数百人规模不必新增；若压测发现慢，再评估。
- 隐私：openpyxl 默认不加密 XLSX；如要求密码保护，需外部工具或额外库，和 PDF/ZIP 加密一起在 #50 决定。

## 4. 其他候选的实测与结论

### 4.1 Playwright / Chromium HTML→PDF

**能力**：`page.pdf()` 使用 print CSS 生成 PDF；支持 `format`、`print_background`、`prefer_css_page_size`、`margin`、`scale`、`display_header_footer`、`header_template`/`footer_template`、`page_ranges` 等。浏览器打印 CSS 的 `thead` 重复、`break-*` 均可用（实测 70 行表格 2 页，表头重复）。

**中文字体陷阱（本次环境，Playwright 1.65.2 / Chromium 1254）**：

| 字体来源/格式 | PDF 字体 | 是否嵌入 | 单份大小 | 文本抽取 |
|---|---|---|---:|---|
| `@font-face` OTF（CFF） | Type3 × 32 | 否（轮廓） | 86 KB | 兼容汉字 |
| `@font-face` variable TTF | Type3 × 32 | 否（轮廓） | 102 KB | 兼容汉字 |
| 系统 OTF（Noto Sans CJK，CFF） | Type3 × 86 | 否（轮廓） | 219 KB | 兼容汉字 |
| 系统静态 TTF（Regular+Bold） | Type0 NotoSansSC-Regular/Bold | **是** | 40 KB | 兼容汉字 |
| 系统 TTC（微软雅黑，专有，仅测试） | Type0 MicrosoftYaHei | 是 | 31 KB | 正确 |

结论：

- Chromium 只有在**系统安装的静态 TrueType** 字体上才稳定输出 Type0 嵌入字体；OTF/CFF、webfont、合成粗体都可能退化为 Type3 轮廓。Type3 视觉上仍能正确显示（我们渲染 PNG 检查通过），但不是标准字体嵌入，文本复制/搜索/可访问性会退化。
- 即使 Type0 嵌入，Chromium + Noto Sans SC 的 ToUnicode 会把部分汉字映射成兼容汉字（工→⼯、月→⽉、门→⻔、金→⾦、人→⼈）。视觉正常，但 PDF 文本搜索/复制可能不准；对工资条的“查找姓名/金额”是实际缺陷。
- 部署：Chromium 缓存 413 MB + headless shell 283 MB；需要浏览器进程生命周期、崩溃恢复、并发控制；Playwright 官方镜像定位为测试/开发。对 4 worker FastAPI 生产服务，复杂度明显高于 WeasyPrint。
- 性能：逐份 83 ms（500 份 41.7 s），合并 500 页仅 2.6 s（1.55 MB），是合并大文档的最快路径。若未来“合并打印 PDF”成为主路径且可接受静态 TTF 字体、可接受文本抽取缺陷，可重新评估；不建议作为工资条 ZIP 主路径。

### 4.2 ReportLab

**能力与限制**：

- `TTFont` 支持 TrueType（glyf）并做动态子集化，PDF 中写 `FontFile2`；实测静态 Noto Sans SC Regular/Bold 均嵌入，500 份 5.8 s，49 KB/份，文本抽取中文正确。
- **不支持 CFF/PostScript 轮廓的 OTF**：`TTFont` 注册 Noto CJK SC OTF 直接报 `TTFError: ... postscript outlines are not supported`。如果只有 OTF，需要先转静态 TTF，或退回 CID 字体。
- ReportLab 内置的 `UnicodeCIDFont('STSong-Light')` 等 CJK 字体**不嵌入**；官方文档原话是这类方案“nothing needs embedding in the PDF file; everything is on the reader”（不需要嵌入，一切依赖阅读器）。实测 PDF 仅 2.4 KB，字体 `embedded=False`。这不能用于对外分发的工资条。
- 分页：`Table(..., repeatRows=1)` 实测跨页表头重复；`PageBreak` 可控制每人一页；但所有版式都需要 Python 代码手写，字段/样式变化要改代码，不能复用 HTML/CSS/Jinja2。
- 许可证：BSD-3-Clause。

**结论**：ReportLab 是可信的备选，尤其适合“每天数千份、对文本抽取/PDF 体积极敏感、愿意维护 Python 版式代码”的场景。对本项目（FastAPI + Jinja2、数百人、版式会随 #50 调整），WeasyPrint 的维护成本更低。除非后续压测显示 WeasyPrint 无法满足性能预算，否则不选 ReportLab。

### 4.3 前端打印

- `window.print()` 调起浏览器打印对话框；用户可以“另存为 PDF”。这适合单人、临时、手工操作，但：
  - 无法在服务端批量生成文件或 ZIP；
  - 输出依赖客户端浏览器/操作系统/已安装字体，版式不可复现；
  - 工资数据必须已经渲染在浏览器中，增加暴露面；
  - 无法可靠审计“导出了什么”；
  - 每人一页/表头重复只能靠用户在打印预览中检查。
- 建议：如果产品需要，可在单人详情页提供“打印”按钮作为便利功能；**批量工资条与归档 PDF 必须服务端生成**。

## 5. 最小验证实验（可丢弃，未入库）

所有脚本、字体和输出都在 `/tmp/pdfresearch/`，未提交到仓库。实验内容：

1. **WeasyPrint 字体格式对比**：同一份 1 页工资条 HTML，分别用静态 TTF、Noto CJK OTF、variable TTF、系统 OTF 渲染；用 pypdf 检查 `/Font`、`/FontFile*`、页数和文本；用 pypdfium2 渲染 PNG 目视检查。
2. **WeasyPrint 500 份批量**：单进程与 4 进程；合并 500 页；ZIP stored/deflated；`full_fonts` 开/关。
3. **Chromium 对比**：Playwright 启动本机缓存的 Chromium，分别用 webfont OTF/TTF、系统 OTF、系统静态 TTF、系统 TTC 渲染；检查 Type0/Type3、嵌入标志、文本抽取、500 份与合并 500 页性能。
4. **ReportLab 对比**：静态 TTF 500 份；`UnicodeCIDFont('STSong-Light')` 嵌入检查；70 行 `repeatRows=1` 跨页表头检查。
5. **Docker 冒烟**：基于 `python:3.14` 安装 WeasyPrint + Pango + `fonts-noto-cjk`，在容器内渲染系统 OTF 和挂载的静态 TTF，确认字体匹配、Type0 嵌入、文本抽取、镜像体积。
6. **分页验证**：WeasyPrint 与 Chromium 的 70 行表格均 2 页且第 2 页有表头；两者合并 500 人 PDF 均 500 页、无空白页、工号逐页对应。
7. **目视检查**：WeasyPrint、Chromium、ReportLab 生成的工资条 PNG 均中文显示正确、金额/表格无重叠。

**实验局限（必须向 #50 说明）**：

- 合成数据、单机 WSL2，不是目标生产硬件；绝对耗时会有差异，应看相对比例和 staging 复测。
- 未做多请求并发压测；4 进程数据是单批次。
- 未在 Windows/macOS 阅读器、WPS、Adobe Acrobat 中逐一打开验证；PDF 字体嵌入用 pypdf 结构检查 + pypdfium2 渲染，不等于所有阅读器兼容性认证。
- Chromium 的 Type3/兼容汉字行为与版本、字体文件、构建有关；不要把本次结论当成所有 Chromium 版本的保证。
- 未验证 PDF/A、PDF/UA、加密 PDF、密码 ZIP 的完整链路；这些是 #50 可能需要追加的决策。
- 字体许可证结论基于 OFL 文本；正式发布前仍建议法务/合规复核。

### 结论置信度与未决项

- **高置信度**（本地 + 容器实测）：WeasyPrint/ReportLab/Chromium 的中文字体嵌入行为；Noto/OFL 许可条款；现有依赖事实；CSS 分页/表头重复；500 份 ZIP 的组装方式；Docker 包名与安装路径。
- **中置信度**：目标生产硬件上的绝对耗时与并发表现（WSL2 12 核，非生产机）；4 进程池在 4 个 uvicorn worker 下的总并发；静态 TTF 的最终落地方式（vendoring vs 构建时生成）；不同 PDF 阅读器（WPS/Acrobat/移动端）的兼容性。
- **低置信度/待 #50 决定**：Chromium 的 Type3/兼容汉字行为是否在其他版本稳定；是否需要 PDF/ZIP 密码保护；是否需要 PDF/A 或 PDF/UA；超过 500 人时的异步任务方案；字体许可证的最终法务意见。

## 6. 对 ticket #50 的具体建议

以下是可以直接带入《工资条与报表定稿》的技术决策：

1. **生成路径**：采用**服务端 WeasyPrint + Jinja2 HTML/CSS**；不做前端批量打印；不引入 Chromium/Playwright 到生产后端。ReportLab 仅作为性能兜底备选，不默认实现。
2. **数据来源**：工资条从**已持久化的工资结果/月结快照**读取，生成时不再计算工资；PDF 中体现工资所属期、发放日期、工号、公司抬头；保证同一月份重复导出结果一致。
3. **版式**：A4 纵向，**默认每位员工一页**；`@page` 控制页边距；`break-after: page` 分隔员工；`thead` 重复、`tr` 不跨页；测试断言每人 1 页（项目过多导致续页时显式记录/告警）。字段分组、显示/隐藏项、应发/社保/个税/实发四项合计由 #50 的字段配置决定；技术模板只消费配置后的数据。
4. **批量导出**：按公司+月份+部门/筛选结果，**每人一个 PDF 打包 ZIP**；另提供**一人一页的合并 PDF**用于批量打印/归档。ZIP 用标准库 `zipfile` + `SpooledTemporaryFile`，deflate 或 stored 均可；文件名包含工号和姓名并做安全清洗；外层文件名 ASCII fallback。
5. **字体**：**Noto Sans SC（SIL OFL 1.1）静态 TrueType Regular+Bold**；WeasyPrint 默认子集嵌入；随包提供 OFL 文本。禁止微软雅黑/宋体/STSong-Light；禁止 `full_fonts=True`。如果 #50 选择最简单的 Docker 方案，可先用 `fonts-noto-cjk` OTF 上线，但需接受 300 KB/份、500 份约 134 MB，并计划后续切 TTF。
6. **性能预算**：单人 PDF p95 < 1 s；500 人 ZIP ≤ 30 s（目标机器、4 渲染进程）；合并 500 页 PDF ≤ 60 s；单请求硬上限 500 人。超过上限/需要可靠异步时，新增任务表 + 后台 worker，不用只靠 `BackgroundTasks`。
7. **部署**：后端 Docker 增加 Pango/HarfBuzz 系统库和 Noto 字体（或 vendored TTF）；不增加 Chromium；更新开发环境说明和 CI 的中文 PDF 冒烟测试；固定字体版本。
8. **Excel**：继续使用现有 **openpyxl 3.1.5（MIT）**，不新增 xlsxwriter；大表用 `Workbook(write_only=True)`；金额写数值并设 `#,##0.00`；CSV 流式导出保留。
9. **隐私/审计**：所有 PDF/ZIP 导出走登录鉴权并复用工资可见性规则；响应加 `Cache-Control: no-store`；记录导出审计（人、时间、公司、月份、筛选、人数、格式），不记录金额；如要求 PDF/ZIP 密码，WeasyPrint 本身不支持，需 pypdf/ReportLab 后处理或 pyzipper/7z，作为独立决策。
10. **并发/集成**：渲染放进程池，数据库查询在渲染前完成并释放 session；按目标 vCPU 限制总渲染进程数（注意 4 个 uvicorn worker 的乘数效应）；确认 Traefik/代理超时；ZIP 用 `StreamingResponse` 分块返回。
11. **#50 仍需拍板的产品项**（非本报告能决定）：字段分组与显隐、单人/批量/部门汇总的报表边界、生成时点（实时 vs 快照）、是否允许员工自助导出、导出审计范围、是否需要密码保护/PDF/A。

## 7. 参考来源

以下均为本次调研直接读取的官方文档、源码或许可证文本（访问日期 2026-11-27）：

### WeasyPrint

- 安装要求与 Debian/Ubuntu 包名：<https://doc.courtbouillon.org/weasyprint/stable/first_steps.html>
- Python API、字体自动嵌入/子集化、`write_pdf` 选项：<https://doc.courtbouillon.org/weasyprint/stable/api_reference.html#fonts>
- 支持的 CSS Paged Media / Fragmentation：<https://doc.courtbouillon.org/weasyprint/stable/features.html#css-paged-media-module-level-3>、<https://doc.courtbouillon.org/weasyprint/stable/features.html#css-fragmentation-module-level-3-4>
- 默认选项 `full_fonts=False` 等：<https://github.com/Kozea/WeasyPrint/blob/main/weasyprint/__init__.py>
- BSD-3-Clause 许可证：<https://github.com/Kozea/WeasyPrint/blob/main/LICENSE>
- 官方文档中的 PDF/A 变体与命令选项：<https://doc.courtbouillon.org/weasyprint/stable/features.html>

### Playwright / Chromium

- `page.pdf()` API 与选项：<https://playwright.dev/python/docs/api/class-page#page-pdf>
- Docker 镜像说明（含浏览器与系统依赖、版本固定、测试/开发定位）：<https://playwright.dev/python/docs/docker>
- Apache-2.0 许可证：<https://github.com/microsoft/playwright/blob/main/LICENSE>
- CDP `Page.printToPDF` 参数：<https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF>

### ReportLab

- 字体章节（CID/Asian Language Pack 不嵌入；TrueType 子集）：<https://docs.reportlab.com/reportlab/userguide/ch2_fonts/>；源码版 <https://github.com/MrBitBucket/reportlab-mirror/blob/master/docs/userguide/ch2a_fonts.py>
- TTFont 动态子集与 `FontFile2`：<https://github.com/MrBitBucket/reportlab-mirror/blob/master/src/reportlab/pdfbase/ttfonts.py>
- BSD-3-Clause 许可证：<https://github.com/MrBitBucket/reportlab-mirror/blob/master/LICENSE>

### 字体与许可证

- Noto CJK 的 SIL OFL 1.1：<https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE>
- Source Han Sans 的 SIL OFL 1.1：<https://github.com/adobe-fonts/source-han-sans/blob/master/LICENSE.txt>
- Noto Sans SC（Google Fonts，variable TTF）：<https://github.com/google/fonts/tree/main/ofl/notosanssc>
- Debian `fonts-noto-cjk` 包：<https://packages.debian.org/trixie/fonts-noto-cjk>
- OFL 1.1 官方文本（含文档嵌入条款）：<https://openfontlicense.org/open-font-license-official-text/>

### 其他

- openpyxl 优化模式（read-only / write-only）：<https://openpyxl.readthedocs.io/en/stable/optimized.html>
- openpyxl MIT 许可证：<https://pypi.org/project/openpyxl/>
- pypdf BSD-3-Clause 许可证：<https://github.com/py-pdf/pypdf/blob/main/LICENSE>
- pypdf `PdfWriter.encrypt`（PDF 密码/权限）：<https://pypdf.readthedocs.io/en/stable/modules/PdfWriter.html#pypdf.PdfWriter.encrypt>
- Python `zipfile`（可读加密 ZIP，但不能创建加密 ZIP）：<https://docs.python.org/3/library/zipfile.html>
- Python `SpooledTemporaryFile`：<https://docs.python.org/3/library/tempfile.html#tempfile.SpooledTemporaryFile>
- MDN `window.print()`：<https://developer.mozilla.org/en-US/docs/Web/API/Window/print>
- 仓库内现有实现：`backend/pyproject.toml`、`backend/Dockerfile`、`backend/app/api/routes/attendance/exports.py`、`backend/app/services/attendance/exports.py`、`frontend/package.json`
