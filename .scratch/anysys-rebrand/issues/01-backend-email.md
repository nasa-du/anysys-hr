# 01: 后端与邮件基础：UUID v7、中文错误、API 文档品牌、中文邮件

**What to build:** 新建用户和条目时获得 UUID v7 主键与外键；所有 API 用户可见错误以中文返回；API 文档标题为 AnySys 且生产环境关闭；重置密码、新账号、测试三封邮件为简体中文。完成后，后端与邮件侧的用户可见面已经是 AnySys，并且 ID/错误/邮件契约都有自动化验证。

**Blocked by:** None (can start immediately)

**Status:** done

**Implemented:** 2026-10-31

- [x] 通过 API 新建用户和条目时，返回的主键与 `owner_id` 解析后均为 UUID version 7，API 契约不变
- [x] 约 25 条自定义业务错误、框架级 401、常见 Pydantic 422 均返回中文，响应结构保持不变
- [x] development 环境下 FastAPI/OpenAPI 标题为 AnySys，`/docs` 与 `/redoc` 可用
- [x] production 环境下 `/docs` 与 `/redoc` 返回 404（启动后手动验证）
- [x] 三封邮件为简体中文，HTML `lang="zh-CN"`，主题为 `AnySys - 重置密码 / 新账号 / 测试邮件`
- [x] 邮件以 React Email 源码为准重新导出，未手工编辑导出产物
- [x] ADR-0001（UUID v7 主键）已写入
- [x] 后端 pytest 全绿，原有英文错误断言已同步改为中文

## Comments

2026-10-31：实现完成。

- 错误文案：自定义业务错误、成功提示、OAuth2 401（`未登录或登录状态已过期`）与常见 422 已中文化；422 走自定义 `RequestValidationError` 处理器，仅替换 `msg`，保留 `type`/`loc`/`input`/`ctx` 结构；日志保留原始 `msg`/`ctx`，但不记录可能含密码的 `input`。
- UUID v7：`User.id` 与 `Item.id` 的 `default_factory` 改为 `uuid.uuid7()`；外键类型与 API 字符串契约不变，无需迁移。
- API 文档：`PROJECT_NAME` 默认值与本地 `.env` 均为 `AnySys`；`/docs`、`/redoc` 仅在 `FASTAPI_ENV=development` 注册，production 下实测 404，`/api/v1/openapi.json` 保持可用且标题为 AnySys。
- 邮件：三份 React Email 源文件改为简体中文并重新导出；主题为 `AnySys - 重置密码`、`AnySys - 新账号`、`AnySys - 测试邮件`；HTML `lang="zh-CN"`。重置密码邮件通过现有 superuser HTML 接口做 HTTP 级断言；其余两封以导出产物与源码检查确认。
- 偏差说明：`password-recovery-html-content` 的响应头名 `"subject:"` 含非法字符，中文主题会触发 HTTP 客户端头校验失败；该头是非标准调试字段且无消费者，已从响应中移除，端点保持仅返回 HTML。已在 spec 中记录。
- 验证：`uv run pytest` 全绿；`mypy app`、`ty check app`、`ruff check/format` 全部通过；production 文档开关以 `FASTAPI_ENV=production` 手动验证。

2026-10-31：代码审查跟进修复。

- `/docs` 与 `/redoc` 在 production 下此前会被前端 SPA fallback 接住：浏览器 `Accept: text/html` 得到 200 + index.html，并非 404。现在 production 下显式注册两个 404 路由（`include_in_schema=False`），两种 Accept 均实测 404；development 仍为 200。
- 子类 `ChineseOAuth2PasswordBearer` 默认会把 OpenAPI 安全方案名改为 `ChineseOAuth2PasswordBearer`；已传入 `scheme_name="OAuth2PasswordBearer"` 恢复原契约，并新增 openapi.json 断言。
- `test_create_item` 的 `owner_id` UUID v7 断言此前依赖超级管理员 id，遇到历史 v4 超级管理员会失败；改为先通过 `/users/signup` 创建用户并登录，再用该用户创建条目。
- 移除 `recover_password_html_content` 冗余的 `HTMLResponse` 包装（路由已声明 `response_class=HTMLResponse`）；`main.py` 复用同一个 `is_development` 判断。
