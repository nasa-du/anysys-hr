# AnySys 产品化：品牌、简体中文、日期格式与 UUID v7

**Status:** ready-for-agent

## Problem Statement

当前仓库仍然是上游 FastAPI 全栈模板：界面全英文、品牌为 FastAPI、页脚与社交链接指向上游项目、UUID 使用 v4、日期没有统一的展示规范。团队要把这个仓库作为 **AnySys** 产品的基础，但现有用户可见面会让访客、员工和客户看到明显的上游模板痕迹。

未来的产品方向是人事管理系统（考勤、排班、薪资计算等后续实现）。在进入领域功能之前，需要先建立稳定的品牌、语言、时间与标识基础，否则后续每个模块都会继承模板的英文文案、FastAPI 痕迹和不一致的日期/ID 约定。

## Solution

进行一次完整的产品化改造：

- 把 **AnySys** 品牌落到所有用户可见面：前端页面、浏览器标题与 favicon、页脚、邮件、API 错误文案与 API 文档标题。
- 全站改为**简体中文**，不引入 i18n 框架、不做语言切换。
- 日期统一为 `YYYY-MM-DD`，需要时间时用 `YYYY-MM-DD HH:mm`，固定 **Asia/Shanghai** 展示；API 继续 ISO 8601，数据库继续存 UTC。
- 所有 UUID 主键/外键改为 **UUID v7**，由服务端生成。
- 同步刷新部署文档、README、社交预览图与产品截图。
- 本轮不实现人事业务功能，不改领域模型；`User` 与 `Item` 仍是占位实体，`Item` 中文化后暂称"条目"。

## User Stories

1. 作为访客，我希望登录页显示 AnySys 品牌，以便确认自己打开的是正确的产品。
2. 作为访客，我希望浏览器标签标题显示"登录 - AnySys"，以便在多个标签页中快速识别。
3. 作为访客，我希望 favicon 显示 AnySys 图标，以便在产品被加入书签后仍可辨认。
4. 作为浅色主题用户，我希望看到适合浅色背景的 AnySys 横版 logo，以便品牌清晰可见。
5. 作为深色主题用户，我希望看到适合深色背景的 AnySys 横版 logo，以便品牌清晰可见。
6. 作为用户，我希望页脚只显示 AnySys 版权信息，而不是上游模板文案或 FastAPI 社交链接。
7. 作为用户，我希望在页面任何位置都看不到 FastAPI 名称、FastAPI 链接或上游仓库链接。
8. 作为中文用户，我希望登录、注册、找回密码、重置密码页面全部使用简体中文。
9. 作为中文用户，我希望表单校验错误使用中文，以便快速理解并修正输入。
10. 作为中文用户，我希望登录失败、密码错误、账号停用等提示使用中文。
11. 作为中文用户，我希望仪表盘标题、欢迎语和统计文案使用简体中文。
12. 作为中文用户，我希望侧边栏导航、用户菜单、退出登录、主题切换等文案使用简体中文。
13. 作为中文用户，我希望设置页的个人信息、修改密码、外观设置等文案使用简体中文。
14. 作为中文用户，我希望条目页的标题、说明、新建/编辑/删除对话框、按钮和 toast 全部使用简体中文。
15. 作为中文用户，我希望管理后台的用户列表、角色、状态、创建用户对话框和操作提示全部使用简体中文。
16. 作为中文用户，我希望 404 页面和错误回退页面使用简体中文，而不是英文默认文案。
17. 作为屏幕阅读器用户，我希望 aria-label、sr-only 文案和无障碍提示也是简体中文。
18. 作为中文用户，我希望所有页面标题使用"页面名 - AnySys"的中文格式。
19. 作为中文用户，我希望主题菜单中的"浅色/深色/跟随系统"等选项使用简体中文。
20. 作为中文用户，我希望"姓名、邮箱、密码、登录、注册、忘记密码、重置密码"等术语在全站保持一致。
21. 作为 API 使用者，我希望自定义业务错误返回中文，以便直接展示给用户。
22. 作为 API 使用者，我希望未认证时返回中文 401 提示，而不是英文 `Not authenticated`。
23. 作为 API 使用者，我希望常见请求校验失败时返回中文 422 提示，而不是英文 Pydantic 默认消息。
24. 作为 API 使用者，我希望错误响应结构保持不变，只改变文案语言，以免破坏前端和第三方集成。
25. 作为开发者，我希望 OpenAPI 文档标题显示 AnySys，而不是上游项目名。
26. 作为安全负责人，我希望生产环境关闭 `/docs` 和 `/redoc`，避免暴露内部 API 文档。
27. 作为开发者，我希望开发环境仍可访问 `/docs` 和 `/redoc`，以便调试。
28. 作为重置密码的用户，我希望收到中文邮件，主题为"AnySys - 重置密码"，正文包含清晰的中文操作说明。
29. 作为被管理员创建的账号用户，我希望收到中文的新账号邮件，主题为"AnySys - 新账号"。
30. 作为超级管理员，我希望测试邮件使用中文，主题为"AnySys - 测试邮件"。
31. 作为邮件收件人，我希望邮件 HTML 的 `lang` 为 `zh-CN`，以便邮件客户端正确排版。
32. 作为管理员，我希望在条目表格中看到"创建时间"列，格式为 `YYYY-MM-DD HH:mm`。
33. 作为管理员，我希望在用户管理表格中看到"创建时间"列，格式为 `YYYY-MM-DD HH:mm`。
34. 作为跨时区用户，我希望所有时间按 Asia/Shanghai 展示，以便团队内部时间一致。
35. 作为用户，我不希望看到"3 分钟前"这类相对时间，而希望看到确定的绝对时间。
36. 作为开发者，我希望新建用户和条目的主键都是 UUID v7，以便获得更好的数据库索引局部性。
37. 作为开发者，我希望外键 `owner_id` 与新主键一样使用 UUID v7。
38. 作为 API 使用者，我希望 ID 仍然以字符串形式返回，接口契约不因 v7 改变。
39. 作为未来的维护者，我希望有一条 ADR 解释为什么选择 UUID v7 而不是 v4。
40. 作为未来的维护者，我希望有一条 ADR 解释为什么只做简体中文、不引入 i18n 框架。
41. 作为开发者，我希望 README 和部署文档使用 AnySys 名称，并移除上游 FastAPI 营销链接。
42. 作为部署者，我希望 Docker Compose 是文档中唯一的部署路径，不再看到 FastAPI Cloud 部署说明。
43. 作为仓库访客，我希望 GitHub 社交预览图展示 AnySys 品牌。
44. 作为 README 读者，我希望产品截图展示 AnySys 的中文界面，而不是 FastAPI 旧界面。
45. 作为维护者，我希望上游贡献指南与变更日志被归档到 `docs/upstream/`，以便追溯但不再干扰主文档。
46. 作为维护者，我希望后端测试断言中文错误文案与 UUID v7。
47. 作为维护者，我希望 Playwright 测试断言中文界面、AnySys 品牌与创建时间格式。
48. 作为维护者，我希望本轮不引入新的前端单元测试框架，继续复用现有 pytest 与 Playwright 两套测试设施。
49. 作为产品负责人，我希望本轮不实现考勤、排班、薪资等领域功能，以便先完成品牌与基础设施改造。
50. 作为产品负责人，我希望内部包名、Compose 服务名、数据库名和 CI workflow 本轮保持不变，以降低回归风险。

## Implementation Decisions

- **品牌**：产品名统一为 `AnySys`；`PROJECT_NAME=AnySys`；本轮 UI 不出现"人事管理系统"字样；页脚为 `© {year} AnySys。保留所有权利。`，不放社交链接；`Logo` 的 alt 设为 `AnySys`。
- **语言**：只做简体中文，不引入 i18n 框架、不做语言切换；前端文案直接写成中文；代码注释、日志、开发者文档保持英文。
- **术语**：使用"你"而非"您"；统一为 仪表盘 / 条目 / 管理后台 / 设置 / 登录 / 注册 / 忘记密码 / 重置密码 / 姓名 / 邮箱；`Item` 是占位实体，暂译"条目"，等 HR 实体落地后替换。
- **Logo 与 favicon**：从现有两张 2400×928 PNG 派生透明横版资产（浅色主题用深蓝 + 蓝，深色主题用白 + 蓝）；favicon 使用"A + 橙点"图形，深蓝圆角方块背景，输出 32/180/192/512 PNG、`.ico` 与 apple-touch-icon；同时修复 `index.html` 中不存在的 `/vite.svg` 引用与 favicon MIME 类型错误。
- **前端中文化范围**：认证页面（登录/注册/找回/重置）、应用外壳（侧边栏/用户菜单/主题菜单）、仪表盘、设置、条目页、管理后台、404 与错误回退、toast、aria/sr-only、页面标题。共享的 toast/错误 fallback 与 Zod 全局校验文案先统一处理，再按页面上层文案分批完成。
- **后端错误**：自定义业务错误全部中文；框架级 401 通过自定义依赖/异常处理返回中文；常见 Pydantic 422 通过自定义 `RequestValidationError` 处理器映射为中文；原始技术细节继续写日志；错误响应结构不变。
- **API 文档**：FastAPI/OpenAPI 标题使用 `PROJECT_NAME=AnySys`；`/docs` 与 `/redoc` 仅在 development 开放，生产环境返回 404；OpenAPI JSON 路径保持现有约定。
- **日期**：新增前端格式化工具，纯日期输出 `YYYY-MM-DD`，含时间输出 `YYYY-MM-DD HH:mm`，固定 `Asia/Shanghai`，不使用相对时间；Items 与 Admin 用户表格新增"创建时间"列；API 继续 ISO 8601，数据库继续 UTC，不做时区迁移。
- **UUID v7**：使用 Python 3.14 标准库 `uuid.uuid7()`；仅修改 SQLModel 主键的 `default_factory`，外键类型不变；不需要数据库迁移；已有 v4 数据（如有）保持原样；前端继续按字符串处理；接受 v7 可推断创建时间/顺序的取舍，暂不增加 `public_id`。
- **邮件**：以 `packages/react-email` 为唯一源文件，三个模板改为 `zh-CN` 中文文案，主题改为 `AnySys - 重置密码 / 新账号 / 测试邮件`；保留 Jinja 占位符；重新导出到 `backend/app/email-templates/`；不手工编辑导出后的 HTML；邮件不引入 logo 图片，保持文字品牌。
- **文档**：品牌化 5 份英文文档（`README.md`、`deployment-docker-compose.md`、`development.md`、`backend/README.md`、`frontend/README.md`），保留技术栈说明；`CONTRIBUTING.md` 与 `release-notes.md` 移到 `docs/upstream/`；删除 FastAPI Cloud 的 `deployment.md`，Docker Compose 为唯一部署路径；`deploy.yml` workflow 本轮不动。
- **图片资产**：用 AnySys logo 重新生成 `img/github-social-preview.*`；实现完成后用 Playwright 重截登录、仪表盘、条目、管理后台四张产品截图。
- **ADR**：写 `docs/adr/0001-uuid-v7-primary-keys.md` 与 `docs/adr/0002-chinese-only-no-i18n.md`。
- **不改动**：根 `package.json` 名称、`bun.lock`、Compose 服务名、数据库名、镜像名、CI workflow、Git 远程与分支策略；不实现任何人事领域功能；不引入新的前端测试框架。

## Testing Decisions

- 好的测试只验证**外部行为**：HTTP 响应、渲染后的 DOM、真实邮件 HTML；不依赖内部函数名、组件结构或实现细节。
- **Seam 1：后端 HTTP API（现有）**。使用 `backend/tests/api/routes/` 的 pytest + FastAPI `TestClient` + Postgres。验证：
  - 通过 API 创建 User/Item 后，返回的 `id` 与 `owner_id` 解析后 `uuid.UUID(...).version == 7`。
  - 自定义业务错误、401、常见 422 返回中文文案。
  - 原有字段、状态码、分页契约不变。
  - 重置密码邮件 HTML 可通过现有 superuser 接口获取并断言中文内容。
  - 现有 `test_items` / `test_users` / `test_login` 的英文断言同步改为中文。
- **Seam 2：浏览器端到端（现有）**。使用 `frontend/tests/*.spec.ts` 的 Playwright + Mailpit。验证：
  - 认证、仪表盘、设置、条目、管理后台页面的中文文案与页面标题。
  - 页脚版权、logo alt、favicon 引用、页面中不存在 FastAPI 文案或上游链接。
  - Items 与 Admin 表格的"创建时间"单元格匹配 `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$`。
  - 重置密码邮件主题与正文为中文，复用现有 `waitForEmailHtml`。
  - 现有 spec 的英文选择器全部改为中文选择器。
- **Prior art**：后端参考 `tests/api/routes/test_items.py`、`test_users.py`、`test_login.py`；前端参考 `tests/login.spec.ts`、`items.spec.ts`、`admin.spec.ts`、`reset-password.spec.ts`、`user-settings.spec.ts`。
- **不新增 seam**：不引入 Vitest 或其他前端单元测试框架；日期格式在 E2E 中断言；logo 视觉正确性靠人工目检和截图。
- **人工验证**：以 `FASTAPI_ENV=production` 启动后端，`curl /docs` 与 `/redoc` 期望 404；浅色/深色主题下检查透明 logo 与 favicon；最终检查四张截图。
- **前置条件**：后端测试需要 Postgres；Playwright 需要完整 Compose 栈（含 Mailpit）。

## Out of Scope

- 考勤、排班、薪资计算等人事领域功能。
- 领域模型改造；`User` 与 `Item` 仍是占位实体。
- i18n 框架、语言切换、英文界面保留。
- 内部包名、Compose 服务名、数据库名、镜像名、根 `package.json` 名称、`bun.lock` 名称。
- CI workflow 修改、Git 远程配置、默认分支调整。
- Logo 矢量化（没有 SVG 源文件，只产出透明 PNG 与 favicon）。
- 邮件中加入 logo 或其他图片。
- 将开发者文档翻译成中文。
- 与本次目标无关的既有缺陷修复（例如找回密码在未配置 SMTP 时的断言异常、`app/frontend` 仅在 Docker 构建产物中存在）。
- 重新截取四张指定截图之外的图片。

## Further Notes

- 仓库目前没有任何 commit、也没有配置远程；移动或删除文件前需确认目标位置，删除的 `deployment.md` 内容可从上游仓库恢复。
- Python 版本为 3.14，`uuid.uuid7()` 来自标准库，不需要新增依赖。
- `PROJECT_NAME` 同时驱动 FastAPI 标题、OpenAPI 标题、邮件主题和发件人显示名；统一设为 `AnySys` 可覆盖大部分后端品牌。
- 邮件的唯一源文件是 `packages/react-email`，后端 HTML 是导出产物；修改后必须重新导出，不能只改 HTML。
- Zod 的全局中文 locale 视当前版本能力而定；若不可用，则在表单 schema 中显式提供中文消息。
- 本轮术语"条目"只是占位；未来做员工、考勤、排班、薪资时，应建立 `CONTEXT.md` 术语表并替换占位实体。
- 实现中发现：`password-recovery-html-content` 的响应头名 `"subject:"` 含非法字符，中文主题会触发 HTTP 客户端的头校验失败；该头是非标准调试字段且无消费者，已从响应中移除，端点保持仅返回 HTML，已纳入 ticket 01。
- 测试与实现都以本 spec 与两份 ADR 为准；若实现中发现冲突，先更新 spec/ADR 再改代码。
