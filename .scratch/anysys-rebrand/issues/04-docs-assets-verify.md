# 04: 文档、资产与全量验证

**What to build:** 把仓库的开发者文档与图片资产统一到 AnySys：品牌化 5 份英文文档、归档上游贡献指南与变更日志、删除 FastAPI Cloud 部署文档、重做社交预览图、重截四张产品截图，并完成后端与 Playwright 全量验证。完成后，仓库表面与产品截图都不再呈现上游模板痕迹。

**Blocked by:** 01, 02, 03

**Status:** done

**Implemented:** 2026-10-31

- [x] 5 份英文文档（README、Docker Compose 部署、开发指南、后端 README、前端 README）使用 AnySys 名称并移除上游营销链接
- [x] `CONTRIBUTING.md` 与 `release-notes.md` 已归档到 `docs/upstream/`
- [x] FastAPI Cloud 的部署文档已删除，Docker Compose 为唯一部署路径
- [x] 社交预览图已用 AnySys 品牌重新生成
- [x] 登录、仪表盘、条目、管理后台四张产品截图已重截为 AnySys 中文界面
- [x] 后端 pytest 与 Playwright 全量通过
- [x] production 环境 `/docs` 与 `/redoc` 手动验证为 404
- [x] 最终用户可见面检查确认不存在 FastAPI 文案、链接或旧品牌图片

## Comments

2026-10-31：实现完成。

- 文档：5 份英文文档统一为 AnySys 标题与命名；README 移除 “Use this template”、FastAPI Cloud、上游仓库与发布说明链接，改为四张新截图与开发/部署入口；部署文档示例域名改为 `anysys.example.com`，删除生产 `/docs` URL 并注明生产文档禁用；开发文档删除 FastAPI Cloud 指引；前后端 README 去掉模板移除说明与 `.fastapicloudignore` 引用。技术栈说明、框架名称与官方文档链接保留。
- 归档：`CONTRIBUTING.md` 与 `release-notes.md` 移到 `docs/upstream/`，新增 `docs/upstream/README.md` 说明仅作历史参考。根目录 `deployment.md`（FastAPI Cloud）已删除，Docker Compose 成为唯一文档化部署路径。按 spec，`.github/workflows` 与 release automation scripts 未改动；归档后的笔记不被 AnySys 发布流程写入。`deploy.yml` workflow 与 `.fastapicloudignore` 同样未改动。
- 图片：`img/github-social-preview.svg` 用 AnySys 深色 logo（内嵌 PNG）重制，Chromium 渲染为 1280×640 PNG；删除旧 `dashboard-dark.png`、`docs.png`、`mailpit.png`、`react-email.png`，README 只引用新四图。
- 截图：用生产构建 + 独立 `anysys_screens` 数据库（5 个中文演示用户、4 条条目）在 1440×900、浅色主题、Asia/Shanghai 下截取登录、仪表盘、条目、管理后台四张图；未改动原有 `app` 开发库数据。
- 验证：`bunx tsc -p tsconfig.json --noEmit`、Biome、`bun run build` 通过；Playwright 全量 72 passed（对 production build + 独立数据库运行）；后端 `uv run bash scripts/test.sh` 64 passed（覆盖率 89%）；pre-commit 全部通过；`FASTAPI_ENV=production` 下 `/docs`、`/redoc` 在 `text/html`、`application/json`、`*/*` 三种 Accept 下均为 404，`/` 为 200，`/api/v1/openapi.json` 标题为 AnySys；前端源码、构建产物与 `img/` 资产扫描无 FastAPI 文案或链接。
- 说明：本地 `backend/htmlcov` 原为 root 拥有，导致 `scripts/test.sh` 的 coverage HTML 步骤失败；已将生成的目录重建为当前用户后全量脚本通过，不影响仓库内容。
