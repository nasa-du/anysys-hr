# 03: 应用页面中文化与创建时间列

**What to build:** 完成登录后的应用页面中文化：侧边栏、用户菜单、主题菜单、仪表盘、设置、404 与错误页、条目页、管理后台。同时在条目表格与用户管理表格中新增"创建时间"列，统一按 Asia/Shanghai 展示为 `YYYY-MM-DD HH:mm`。完成后，登录后的整个使用路径都是中文 AnySys 界面，日期规范真正落地。

**Blocked by:** 02

**Status:** done

**Implemented:** 2026-10-31

- [x] 侧边栏、用户菜单、主题菜单、仪表盘、设置页全部为简体中文
- [x] 404 页面与错误回退页面为简体中文
- [x] 条目页与管理后台（含新建/编辑/删除对话框、按钮、toast）全部为简体中文
- [x] 条目表格与用户管理表格新增"创建时间"列
- [x] 创建时间按 Asia/Shanghai 展示，格式为 `YYYY-MM-DD HH:mm`，不使用相对时间
- [x] API 继续返回 ISO 8601、数据库继续存 UTC，未做时区迁移
- [x] 应用页面与共享组件中不再出现 FastAPI 文案或上游链接
- [x] 应用页面相关 Playwright 测试使用中文选择器并通过
- [x] Playwright 断言创建时间单元格匹配 `YYYY-MM-DD HH:mm`

## Comments

2026-10-31：实现完成。

- 应用外壳：侧边栏、用户菜单、仪表盘、设置、条目页、管理后台、404 与错误回退全部简体中文；共享 DataTable、分页、对话框/抽屉与侧边栏的无障碍文案同步中文化。
- 创建时间：新增 `frontend/src/lib/datetime.ts`，使用 `Intl.DateTimeFormat` 固定 `Asia/Shanghai`，按 `formatToParts` 组装 `YYYY-MM-DD` 与 `YYYY-MM-DD HH:mm`，无新增依赖、不输出相对时间；条目表格与用户管理表格新增“创建时间”列，空值显示 `-`。
- 契约未变：API 继续返回 ISO 8601（UTC `Z`），数据库继续存 UTC，未做时区迁移。
- 测试：items/admin spec 改用中文选择器；新增创建时间断言，在浏览器时区为 `America/New_York` 的情况下验证单元格等于 API `created_at` 经 UTC+8 换算后的 `YYYY-MM-DD HH:mm`，并匹配 `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$`；login spec 新增应用外壳中文文案与 FastAPI 零残留断言。
- 验证：`bunx tsc -p tsconfig.json --noEmit`、`bun run build`、Biome 通过；Playwright 全量 72 passed。

2026-10-31：代码审查跟进。

- 补齐仪表盘、条目、设置、管理后台的页面标题 Playwright 断言（`页面名 - AnySys`），覆盖 spec 的“页面标题”验证项。
- `EditUser` 复用 `lib/validation.ts` 的 `passwordSchema`，与 `AddUser`/`ChangePassword` 保持一致。
- 审查提出的 DataTable 分页、ID 复制列与未使用的 `ui/pagination.tsx` 均为上游模板既有代码；本 ticket 只做了文案中文化，未改变其行为，按 spec 的“无关既有缺陷”范围不在此轮处理。
- 复查：`bunx tsc -p tsconfig.json --noEmit`、Biome、`bun run build` 通过；Playwright 全量 72 passed。
