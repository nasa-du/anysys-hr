# 02: 前端品牌基础与认证页面中文化

**What to build:** 建立 AnySys 的前端品牌基础（透明 logo、favicon、页脚、页面标题、共享文案与全局校验文案），并完成登录、注册、找回密码、重置密码四个认证页面的简体中文化。完成后，访客打开产品看到的是完整 AnySys 品牌与中文认证流程，浏览器标签、favicon、邮件重置流程也已中文。

**Blocked by:** 01

**Status:** done

**Implemented:** 2026-10-31

- [x] 浅色/深色主题分别使用正确的透明 AnySys 横版 logo，logo alt 为 AnySys
- [x] favicon 套件（32/180/192/512、`.ico`、apple-touch-icon）生效；`/vite.svg` 悬空引用与 favicon MIME 类型已修复
- [x] 页脚显示 `© {year} AnySys。保留所有权利。`，不再包含上游社交链接
- [x] 所有路由页面标题为 `页面名 - AnySys`
- [x] 登录、注册、找回密码、重置密码页面全部为简体中文，含表单校验、toast、aria 文案
- [x] 共享 toast/错误 fallback 与 Zod 全局校验文案已中文化
- [x] 重置密码邮件主题与正文为中文，Mailpit 断言通过
- [x] 认证相关 Playwright 测试使用中文选择器并通过
- [x] 认证页面与共享组件中不再出现 FastAPI 文案或上游链接
- [x] ADR-0002（只做简体中文、不引入 i18n）已写入

## Comments

2026-10-31：实现完成。

- 品牌资产：从根目录两张 2400×928 PNG 去底生成透明横版 logo（浅色主题深蓝+蓝、深色主题白+蓝）与 A 形图标；favicon 使用 A + 橙点、深蓝圆角底，输出 `favicon.ico`、32/180/192/512 PNG。`index.html` 的 `lang` 改为 `zh-CN`，移除 `/vite.svg` 悬空引用与 favicon MIME 错误，并移除旧 FastAPI SVG/favicon 资产。logo 按 192px 高、图标按 96px 输出并做调色板量化，避免为 24–64px 的展示尺寸加载 45 KB 级图片。
- 认证页面：登录、注册、忘记密码、重置密码全部中文，页面标题为 `页面名 - AnySys`；按 spec 术语表统一使用“忘记密码”“注册”，密码显示/隐藏与主题切换的 aria 文案同步中文化。仪表盘、条目、设置、管理后台的路由标题也在本 ticket 统一为中文（页面正文仍由 03 处理）；404 与错误回退页面的标签标题分别为“页面不存在 - AnySys”“出错了 - AnySys”。
- 共享层：toast 标题改为“操作成功/操作失败”，错误 fallback 统一为“出错了，请稍后重试。”；Sonner 的通知区域与关闭按钮 aria-label 改为“通知/关闭通知”；`main.tsx` 启用 Zod `zhCN` 全局 locale；认证表单的邮箱/密码/确认密码 schema 抽到 `src/lib/validation.ts`，后续页面可复用同一套中文校验文案；页脚改为仅版权信息。
- 成功提示改为读取 API 返回的 `Message`（找回密码与重置密码），避免前端与后端各自的文案漂移。
- 测试：认证 spec 全部改用中文选择器，并新增页面标题（含 404）、logo alt、页脚版权、favicon 套件（HTTP 200 + MIME）、toast aria 断言；Mailpit helper 增加主题读取，重置密码测试断言主题 `AnySys - 重置密码`、`lang="zh-CN"` 与中文正文。顺带修正 `user-settings.spec.ts` 中仍断言英文旧密码错误的一处（后端已在 01 中文化）。
- 验证：`bunx tsc -p tsconfig.json --noEmit`、`bun run build`、Biome 通过；后端 pytest 64 passed；Playwright 全量 69 passed；浅色/深色登录页截图人工确认 logo 透明与对比度。
- 代码审查跟进：同时修复了 01 中发现的后端问题（production `/docs`、`/redoc` 的浏览器请求原先被 SPA fallback 返回 200、OpenAPI 安全方案名被改名、UUID v7 测试依赖历史超级管理员数据），详见 01 的评论。
