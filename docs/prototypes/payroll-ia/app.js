/* Payroll IA prototype — interaction shell.
 * Throwaway code: in-memory data, a simplified evaluator, no persistence. */
(() => {
  "use strict";

  const Data = window.PayrollData;
  const H = Data.helpers;
  const db = Data.createDb();
  const INITIAL_FIELD_DEFAULTS = Object.fromEntries(db.fieldDefs.map((field) => [field.field_key, field.default_formula]));

  const COMPOSITION_ALIASES = [
    ["base_salary", "基本工资"], ["hightemp_subsidy", "高温补贴"], ["performance_salary", "绩效工资"],
    ["overtime_pay", "加班费标准"], ["confidentiality_allowance", "保密津贴"], ["social_subsidy", "社保补贴"],
    ["noncompete_subsidy", "竞业补贴"], ["total_package", "工资金额合计"],
  ];
  const WORKDAY_PARAM_ALIASES = [
    ["avg_pay_days", "月均计薪天数"], ["work_hours", "日工作小时"], ["ot_mult_weekday", "工作日加班倍数"],
    ["ot_mult_weekend", "周末加班倍数"], ["ot_mult_holiday", "节假日加班倍数"], ["min_wage", "最低薪资"],
  ];

  function paramAliases() {
    const seen = new Set();
    const rows = [
      ...WORKDAY_PARAM_ALIASES,
      ...db.globalParams.filter((param) => param.type === "number").map((param) => [param.key, param.label]),
    ];
    return rows.filter(([key]) => {
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function formulaAliases() {
    const fields = db.fieldDefs.filter((f) => f.is_active !== false).map((f) => ({ label: f.label, token: f.field_key }));
    const amounts = COMPOSITION_ALIASES.map(([key, label]) => ({ label, token: key }));
    const params = paramAliases().map(([key, label]) => ({ label: `{${label}}`, token: `{${key}}` }));
    return { fields, amounts, params, all: [...fields, ...amounts, ...params].sort((a, b) => b.label.length - a.label.length) };
  }

  function displayFormulaToStorage(formula) {
    let out = String(formula || "");
    for (const alias of formulaAliases().all) out = out.split(alias.label).join(alias.token);
    return out;
  }

  function storageFormulaToDisplay(formula) {
    let out = String(formula || "");
    for (const [key, label] of paramAliases()) out = out.split(`{${key}}`).join(`{${label}}`);
    const asciiAliases = [...db.fieldDefs.map((f) => ({ token: f.field_key, label: f.label })), ...COMPOSITION_ALIASES.map(([key, label]) => ({ token: key, label }))]
      .sort((a, b) => b.token.length - a.token.length);
    for (const alias of asciiAliases) {
      out = out.replace(new RegExp(`\\b${escapeRegExp(alias.token)}\\b`, "g"), alias.label);
    }
    return out;
  }

  /* ---------------------------------------------------------------- icons */

  const ICONS = {
    wallet: '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
    list: '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
    calculator: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8"/><path d="M8 10h.01"/><path d="M12 10h.01"/><path d="M16 10h.01"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/><path d="M8 18h.01"/><path d="M12 18h.01"/><path d="M16 18h.01"/>',
    file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h5"/>',
    "bar-chart": '<path d="M3 3v18h18"/><path d="M7 16v-5"/><path d="M12 16V7"/><path d="M17 16v-8"/>',
    layers: '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
    settings: '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2Z"/><circle cx="12" cy="12" r="3"/>',
    sliders: '<path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><path d="M1 14h6"/><path d="M9 8h6"/><path d="M17 16h6"/>',
    briefcase: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><path d="M2 12h20"/>',
    building: '<path d="M3 21h18"/><path d="M5 21V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v16"/><path d="M15 21V9h2a2 2 0 0 1 2 2v10"/><path d="M9 7h2"/><path d="M9 11h2"/><path d="M9 15h2"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>',
    calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "x-circle": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6"/><path d="m15 9-6 6"/>',
    alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.6 2.3c-.7.4-1.1 1-1.1 1.8v.4"/><path d="M12 17h.01"/>',
    edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    trash: '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>',
    refresh: '<path d="M3 12a9 9 0 0 1 15.5-6.2L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 21v-5h5"/>',
    lock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    unlock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 7.5-2"/>',
    plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-left": '<path d="m15 18-6-6 6-6"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
    "arrow-left": '<path d="M19 12H5"/><path d="m11 18-6-6 6-6"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    play: '<path d="m7 4 13 8-13 8Z"/>',
    history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    columns: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 3v18"/><path d="M3 9h18"/>',
    filter: '<path d="M3 4h18"/><path d="M6 8h12"/><path d="M10 12h4"/><path d="M11 16h2"/>',
    package: '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    printer: '<path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    network: '<rect x="9" y="3" width="6" height="5" rx="1"/><rect x="3" y="16" width="6" height="5" rx="1"/><rect x="15" y="16" width="6" height="5" rx="1"/><path d="M12 8v4"/><path d="M6 16v-2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2"/>',
    "arrow-up-right": '<path d="M7 17 17 7"/><path d="M8 7h9v9"/>',
    "more-horizontal": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    menu: '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    ban: '<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/>',
    archive: '<rect x="2" y="4" width="20" height="5" rx="1"/><path d="M4 9v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9"/><path d="M10 13h4"/>',
    copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "rotate-ccw": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
    zap: '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z"/>',
    database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
  };

  function icon(name, cls = "") {
    const content = ICONS[name] || ICONS.info;
    return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${content}</svg>`;
  }

  /* ---------------------------------------------------------------- state */

  const state = {
    db,
    variant: "A",
    theme: "light",
    preview: "normal",
    narrow: false,
    mobileNav: false,
    companyMenuOpen: false,
    page: "list",
    pageByVariant: { A: "list", B: "list", C: "cockpit" },
    companyId: "c1",
    month: "2026-11",
    listFilters: { dept: "all", position: "all", cost: "all", q: "" },
    listColumns: db.fieldDefs.filter((f) => f.list_default).map((f) => f.field_key),
    selectedComposition: "STD",
    selectedScheme: "STD",
    selectedWorkday: "STD",
    fieldScheme: "STD",
    fieldKey: "base_pay",
    compositionVersionOpen: null,
    payslipEmployeeId: "E101",
    payslipFilter: "all",
    calcRunning: false,
    exportJobSeq: 1,
    overlay: null,
    toast: null,
    wizard: null,
  };

  let toastTimer = null;
  let calcTimer = null;
  let lastOverlayKey = "";

  /* ---------------------------------------------------------------- helpers */

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function money(value, options = {}) {
    const n = Number(value || 0);
    const magnitude = Math.abs(n);
    const formatted = magnitude >= 0.005
      ? magnitude.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : "0.00";
    return `${!options.abs && n < -0.005 ? "-" : ""}¥${formatted}`;
  }

  function moneyPlain(value) {
    return Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function num(value, digits = 2) {
    return Number(value || 0).toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  function pct(value, digits = 1) {
    if (value == null || !Number.isFinite(Number(value))) return "—";
    return `${Number(value).toFixed(digits)}%`;
  }

  function monthLabel(monthKey) {
    if (!monthKey) return "—";
    const [y, m] = monthKey.split("-");
    return `${y} 年 ${Number(m)} 月`;
  }

  function currentCompany() {
    return db.companies.find((c) => c.id === state.companyId) || db.companies[0];
  }

  function currentMonth() {
    return db.months[state.month] || null;
  }

  function monthsForCompany() {
    if (state.companyId !== "c1") return [];
    return Object.keys(db.months).sort();
  }

  const STATE_META = {
    draft: { label: "草稿", cls: "badge-gray", icon: "edit" },
    calculated: { label: "已核算", cls: "badge-blue", icon: "calculator" },
    confirmed: { label: "已确认", cls: "badge-orange", icon: "check-circle" },
    paid: { label: "已发", cls: "badge-green", icon: "lock" },
  };

  function stateBadge(month) {
    const meta = STATE_META[month?.state] || STATE_META.draft;
    return `<span class="badge ${meta.cls}">${meta.label}</span>`;
  }

  function sourceBadge(source) {
    const meta = {
      plan: { label: "构成", cls: "badge-purple" },
      formula: { label: "公式", cls: "badge-blue" },
      import: { label: "导入", cls: "badge-green" },
      fixed: { label: "固定值", cls: "badge-gray" },
    }[source] || { label: source, cls: "badge-gray" };
    return `<span class="badge ${meta.cls}">${meta.label}</span>`;
  }

  function flagsBadges(month) {
    if (!month) return "";
    const flags = H.monthFlags(db, month);
    const items = [];
    if (flags.needsRecalc) items.push(`<span class="badge badge-orange">${icon("alert")} 待重算</span>`);
    if (flags.attendanceStale) items.push(`<span class="badge badge-red">${icon("clock")} 考勤已变化</span>`);
    if (flags.scopeStale) items.push(`<span class="badge badge-red">${icon("users")} 范围已变化</span>`);
    if (flags.configStale) items.push(`<span class="badge badge-orange">${icon("settings")} 配置已更新</span>`);
    if (flags.lastFailed) items.push(`<span class="badge badge-red">${icon("x-circle")} 最近批次失败</span>`);
    if (month.state === "paid" && month.paidSnapshot) items.push(`<span class="badge badge-green">${icon("lock")} 快照 v${month.paidSnapshot.version}</span>`);
    return items.join("");
  }

  function pageLabel(page) {
    return {
      list: "工资列表",
      import: "月度导入",
      calc: "核算与确认",
      payslips: "工资条",
      cost: "成本统计",
      compositions: "薪资构成",
      schemes: "计算方案",
      workday: "工作日参数",
      assembly: "岗位装配",
      fields: "字段与公式",
      globals: "全局参数",
      cockpit: "薪资驾驶舱",
    }[page] || page;
  }

  function pageSub(page) {
    return {
      list: "按月查看员工薪资结果；字段顺序与显隐来自全局字段定义，明细抽屉保留来源与公式追溯。",
      import: "统一「公司 + 月份」输入：考勤自有 9 个值只读锁定月汇总，文件只承载薪资自有列，预览分色标注来源、冲突与错误。",
      calc: "核算前检查考勤、范围、装配与输入版本；批次冻结配置快照，确认与发工资条有独立门槛。",
      payslips: "正式工资条取最新已发快照，预览工资条取当前成功批次；批量导出走异步任务，产物 24 小时过期。",
      cost: "按冻结成本中心路径（含下级）聚合应发、社保、个税与实发，对比当前预算并给出三态预警；未分配单列。",
      compositions: "公司级可复用的薪资包标准金额；身份稳定、版本不可变，岗位只引用身份。",
      schemes: "仅承载字段公式集合；方案级覆盖优先于字段默认公式，工作与计薪参数不在这里。",
      workday: "计薪天数、日工时、加班倍数与最低工资；由岗位装配引用，与考勤规则分离。",
      assembly: "岗位是薪资构成、计算方案、工作日参数的一对一装配点；未装配岗位会阻塞核算。",
      fields: "全系统一份字段定义；类别决定一致性校验，默认公式与方案覆盖分离，公式编辑器提供实时试算。",
      globals: "系统级法定口径参数，全公司共享；修改后当前月标记待重算，历史月沿用快照。",
      cockpit: "以「本月要处理什么」为主入口：状态、待办、异常与快捷操作；配置与月度工作仍然分离。",
    }[page] || "";
  }

  const MONTHLY_PAGES = ["list", "import", "calc", "payslips", "cost"];
  const CONFIG_PAGES = ["compositions", "schemes", "workday", "assembly", "fields", "globals"];
  const ALL_PAGES = [...MONTHLY_PAGES, ...CONFIG_PAGES, "cockpit"];
  const VALID_PAGES = {
    A: [...MONTHLY_PAGES, ...CONFIG_PAGES],
    B: [...MONTHLY_PAGES, ...CONFIG_PAGES],
    C: [...MONTHLY_PAGES, ...CONFIG_PAGES, "cockpit"],
  };
  const CONFIG_TABS = [
    { page: "compositions", label: "薪资构成" },
    { page: "schemes", label: "计算方案" },
    { page: "workday", label: "工作日参数" },
    { page: "assembly", label: "岗位装配" },
    { page: "fields", label: "字段与公式" },
    { page: "globals", label: "全局参数" },
  ];
  const MONTHLY_TABS = [
    { page: "list", label: "工资列表" },
    { page: "import", label: "月度导入" },
    { page: "calc", label: "核算与确认" },
    { page: "payslips", label: "工资条" },
    { page: "cost", label: "成本统计" },
  ];

  function setState(patch, options = {}) {
    Object.assign(state, patch);
    if (options.sync !== false) syncUrl();
    render();
  }

  function goPage(page, patch = {}) {
    Object.assign(state, patch);
    state.page = page;
    state.pageByVariant[state.variant] = page;
    state.mobileNav = false;
    syncUrl();
    render();
  }

  function goMonth(month) {
    if (!db.months[month]) return;
    state.month = month;
    if (state.page === "payslips") {
      const source = H.monthResults(db, db.months[month]);
      state.payslipEmployeeId = source && source.results[0] ? source.results[0].employeeId : "E101";
    }
    syncUrl();
    render();
  }

  function parseUrl() {
    const params = new URLSearchParams(window.location.search);
    const variant = (params.get("variant") || "A").toUpperCase();
    state.variant = ["A", "B", "C"].includes(variant) ? variant : "A";
    const company = params.get("company");
    if (company && db.companies.some((c) => c.id === company)) state.companyId = company;
    const month = params.get("month");
    if (month && db.months[month]) state.month = month;
    state.theme = params.get("theme") === "dark" ? "dark" : "light";
    const preview = params.get("preview");
    if (["normal", "loading", "empty", "error"].includes(preview)) state.preview = preview;
    state.narrow = params.get("narrow") === "1";
    const page = params.get("page");
    const valid = VALID_PAGES[state.variant] || VALID_PAGES.A;
    state.page = page && valid.includes(page) ? page : state.variant === "C" ? "cockpit" : "list";
    state.pageByVariant[state.variant] = state.page;
    const employee = params.get("employee");
    if (employee) state.payslipEmployeeId = employee;
    const cost = params.get("cost");
    if (cost) state.listFilters.cost = cost;
  }

  function syncUrl() {
    const params = new URLSearchParams();
    params.set("variant", state.variant);
    params.set("page", state.page);
    params.set("month", state.month);
    params.set("theme", state.theme);
    params.set("company", state.companyId);
    if (state.preview !== "normal") params.set("preview", state.preview);
    if (state.narrow) params.set("narrow", "1");
    if (state.page === "payslips") params.set("employee", state.payslipEmployeeId);
    if (state.listFilters.cost !== "all" && state.page === "list") params.set("cost", state.listFilters.cost);
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  }

  function showToast(message, type = "success") {
    state.toast = { message, type };
    renderOverlayRoot();
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      state.toast = null;
      renderOverlayRoot();
    }, 3000);
  }

  function applyTheme() {
    document.documentElement.classList.toggle("dark", state.theme === "dark");
  }

  function applyNarrow() {
    document.body.classList.toggle("narrow", state.narrow);
  }

  function overlayKey() {
    const o = state.overlay;
    if (!o) return "";
    return `${o.type}:${o.key || ""}`;
  }

  /* ---------------------------------------------------------------- render */

  function render() {
    applyTheme();
    applyNarrow();
    const app = document.getElementById("app");
    if (!app) return;
    app.innerHTML = `
      <a class="skip-link" href="#main-content">跳到主要内容</a>
      ${state.mobileNav ? `<div class="mobile-nav-backdrop" data-action="close-mobile-nav"></div>` : ""}
      <div class="app">
        ${renderSidebar()}
        <div class="main">
          ${renderTopbar()}
          <main class="content wide" id="main-content">${renderCurrentPage()}</main>
        </div>
      </div>`;
    renderPrototypeBar();
    renderOverlayRoot();
    const key = overlayKey();
    if (key && key !== lastOverlayKey) focusAutofocus();
    lastOverlayKey = key;
  }

  function focusAutofocus() {
    const target = document.querySelector("[data-autofocus]");
    if (!target) return;
    target.focus();
    if (target.tagName === "TEXTAREA" && typeof target.setSelectionRange === "function") {
      const end = target.value.length;
      target.setSelectionRange(end, end);
    }
  }

  function navItem(page, label, iconName, badge = "", activeOverride = null) {
    const active = activeOverride == null ? state.page === page : activeOverride;
    return `<button class="nav-item ${active ? "active" : ""}" data-action="nav" data-page="${page}">
      ${icon(iconName)}<span>${esc(label)}</span>${badge ? `<span class="nav-badge">${badge}</span>` : ""}
    </button>`;
  }

  function renderSidebar() {
    const month = currentMonth();
    const flags = month ? H.monthFlags(db, month) : null;
    const alerts = state.companyId === "c1" && month ? (flags.lastFailed ? 1 : 0) + (flags.attendanceStale ? 1 : 0) : 0;
    const groups = state.variant === "A"
      ? `
        <div class="nav-label">薪资月度</div>
        ${navItem("list", "工资列表", "list")}
        ${navItem("import", "月度导入", "upload")}
        ${navItem("calc", "核算与确认", "calculator", alerts || "")}
        ${navItem("payslips", "工资条", "file")}
        ${navItem("cost", "成本统计", "bar-chart")}
        <div class="nav-label">薪资配置</div>
        ${navItem("compositions", "薪资构成", "package")}
        ${navItem("schemes", "计算方案", "sliders")}
        ${navItem("workday", "工作日参数", "clock")}
        ${navItem("assembly", "岗位装配", "briefcase")}
        ${navItem("fields", "字段与公式", "columns")}
        ${navItem("globals", "全局参数", "settings")}`
      : state.variant === "B"
        ? `
        <div class="nav-label">薪资管理</div>
        ${navItem("list", "薪资月度工作台", "calendar", "", MONTHLY_PAGES.includes(state.page))}
        ${navItem("compositions", "薪资配置中心", "settings", "", CONFIG_PAGES.includes(state.page))}
        <div class="nav-note">月度工作台内切换 导入 / 核算 / 工资条 / 成本；配置中心内切换 6 类配置。</div>`
        : `
        <div class="nav-label">薪资管理</div>
        ${navItem("cockpit", "薪资驾驶舱", "bar-chart")}
        <div class="nav-label">本月工作</div>
        ${navItem("list", "工资列表", "list")}
        ${navItem("import", "月度导入", "upload")}
        ${navItem("calc", "核算与确认", "calculator", alerts || "")}
        ${navItem("payslips", "工资条", "file")}
        ${navItem("cost", "成本统计", "bar-chart")}
        <div class="nav-label">配置</div>
        ${navItem("compositions", "配置中心", "settings", "", CONFIG_PAGES.includes(state.page))}`;
    return `<aside class="sidebar ${state.mobileNav ? "mobile-open" : ""}" aria-label="侧边栏">
      <div class="logo">
        <div class="logo-mark">A</div>
        <div class="logo-text"><strong>AnySys HR</strong><span class="sub">薪资管理原型</span></div>
      </div>
      <nav class="nav" aria-label="主导航">
        <div class="nav-label">已交付模块</div>
        <button class="nav-item nav-stub" data-action="stub" data-label="基础管理">${icon("building")}<span>基础管理</span><span class="nav-badge">已实现</span></button>
        <button class="nav-item nav-stub" data-action="stub" data-label="考勤管理">${icon("calendar")}<span>考勤管理</span><span class="nav-badge">已实现</span></button>
        ${groups}
      </nav>
      <div class="sidebar-footer">
        <button class="nav-item" data-action="toggle-theme" title="切换深色 / 浅色">${icon(state.theme === "dark" ? "sun" : "moon")}<span>${state.theme === "dark" ? "浅色主题" : "深色主题"}</span></button>
        <div class="user-row" style="margin-top:8px">
          <div class="avatar">管</div>
          <div class="user-meta"><strong>管理员</strong><span class="sub">admin@example.com</span></div>
        </div>
      </div>
    </aside>`;
  }

  function renderTopbar() {
    const crumbs = ["薪资管理"];
    if (state.page === "cockpit") crumbs.push("薪资驾驶舱");
    else if (CONFIG_PAGES.includes(state.page)) crumbs.push("薪资配置", pageLabel(state.page));
    else crumbs.push("薪资月度", pageLabel(state.page));
    const crumbHtml = crumbs
      .map((c, i) => {
        const last = i === crumbs.length - 1;
        return `${i ? icon("chevron-right") : ""}${last ? `<strong>${esc(c)}</strong>` : `<span>${esc(c)}</span>`}`;
      })
      .join("");
    const company = currentCompany();
    const companyMenu = state.companyMenuOpen
      ? `<div class="company-menu" role="menu">
          <div class="company-menu-head">切换当前公司</div>
          ${db.companies.map((item) => `<button class="company-menu-item ${item.id === state.companyId ? "active" : ""}" data-action="select-company" data-company="${item.id}" role="menuitem">
            <span class="company-menu-dot"></span>
            <span class="company-menu-text"><strong>${esc(item.name)}</strong><span class="company-menu-meta">${esc(item.code)} · ${item.id === "c1" ? "薪资样例数据" : "暂无薪资数据"}</span></span>
            ${item.id === state.companyId ? icon("check") : ""}
          </button>`).join("")}
          <div class="company-menu-foot"><button class="btn btn-ghost btn-sm" data-action="stub" data-label="公司管理">${icon("settings")} 公司管理</button></div>
        </div>`
      : "";
    return `<header class="topbar">
      <div class="inline" style="min-width:0">
        <button class="mobile-menu-btn" data-action="toggle-mobile-nav" aria-label="打开导航">${icon("menu")}</button>
        <div class="breadcrumb">${crumbHtml}</div>
      </div>
      <div class="topbar-right">
        <div class="company-switch-wrap">
          <button class="company-switch" data-action="toggle-company-menu" aria-haspopup="menu" aria-expanded="${state.companyMenuOpen ? "true" : "false"}">${icon("building")}<span>${esc(company.name)}</span><span class="code">${esc(company.code)}</span>${icon("chevron-down")}</button>
          ${companyMenu}
        </div>
        <button class="btn btn-icon btn-outline" data-action="toggle-theme" title="切换深色 / 浅色" aria-label="切换深色 / 浅色">${icon(state.theme === "dark" ? "sun" : "moon")}</button>
        <div class="avatar" title="管理员">管</div>
      </div>
    </header>`;
  }

  function renderPrototypeBar() {
    const bar = document.getElementById("prototype-bar");
    if (!bar) return;
    const names = {
      A: "A · 双区模块独立",
      B: "B · 月份工作台 + 配置中心",
      C: "C · 任务驾驶舱 + 模式",
    };
    bar.innerHTML = `
      <button class="pb-btn" data-action="variant-prev" title="上一个方案（←）" aria-label="上一个方案">${icon("chevron-left")}</button>
      <span class="pb-label"><span class="pb-tag">原型</span><span class="pb-variant">${names[state.variant]}</span></span>
      <button class="pb-btn" data-action="variant-next" title="下一个方案（→）" aria-label="下一个方案">${icon("chevron-right")}</button>
      <span class="pb-divider"></span>
      <button class="pb-btn" data-action="toggle-theme" title="切换深色 / 浅色">${icon(state.theme === "dark" ? "sun" : "moon")} ${state.theme === "dark" ? "浅色" : "深色"}</button>
      <button class="pb-btn" data-action="toggle-narrow" title="窄屏预览">${icon("columns")} ${state.narrow ? "退出窄屏" : "窄屏"}</button>
      <button class="pb-btn" data-action="open-flow">${icon("network")} 页面流程</button>
      <button class="pb-btn" data-action="open-diff">${icon("layers")} 需求差异</button>
      <button class="pb-btn" data-action="open-questions">${icon("help")} 讨论问题</button>
      <span class="pb-label">状态
        <select data-select="preview" aria-label="预览状态">
          <option value="normal" ${state.preview === "normal" ? "selected" : ""}>正常</option>
          <option value="loading" ${state.preview === "loading" ? "selected" : ""}>加载中</option>
          <option value="empty" ${state.preview === "empty" ? "selected" : ""}>空数据</option>
          <option value="error" ${state.preview === "error" ? "selected" : ""}>错误</option>
        </select>
      </span>
      <button class="pb-btn" data-action="reset-prototype">${icon("refresh")} 重置</button>
    `;
  }

  /* ---------------------------------------------------------------- page dispatch */

  function renderCurrentPage() {
    if (state.preview !== "normal") return renderPreviewState();
    if (state.page === "cockpit") return renderCockpit();
    if (state.variant === "A") return renderAPage(state.page);
    if (state.variant === "B") return CONFIG_PAGES.includes(state.page) ? renderConfigHub(state.page) : renderWorkbench(state.page);
    return CONFIG_PAGES.includes(state.page) ? renderConfigCenter(state.page) : renderMode(state.page);
  }

  function pageHead(title, sub, actions = "") {
    return `<div class="page-head">
      <div><h1 class="page-title">${esc(title)}</h1><p class="page-sub">${sub}</p></div>
      <div class="actions">${actions}</div>
    </div>`;
  }

  function pageActions(page) {
    const month = currentMonth();
    if (page === "import") {
      const allowed = importAllowed(month);
      return `<button class="btn btn-primary btn-sm" data-action="open-import-wizard" ${allowed ? "" : 'disabled title="当前月状态不允许导入"'}>${icon("plus")} 新建导入</button>`;
    }
    if (page === "list") return `<button class="btn btn-outline btn-sm" data-action="open-columns">${icon("columns")} 列设置</button><button class="btn btn-outline btn-sm" data-action="go-page" data-page="import">${icon("upload")} 月度导入</button>`;
    if (page === "payslips") return `<button class="btn btn-primary btn-sm" data-action="open-export">${icon("download")} 批量导出</button>`;
    if (page === "cost") return `<span class="badge badge-gray">${icon("info")} 只读报表</span>`;
    if (page === "compositions") return `<button class="btn btn-primary btn-sm" data-action="open-new-composition">${icon("plus")} 新建薪资构成</button>`;
    if (page === "schemes") return `<button class="btn btn-primary btn-sm" data-action="open-new-scheme">${icon("plus")} 新建计算方案</button>`;
    if (page === "workday") return `<button class="btn btn-primary btn-sm" data-action="open-new-workday">${icon("plus")} 新建参数集</button>`;
    if (page === "fields") return `<button class="btn btn-primary btn-sm" data-action="open-new-field">${icon("plus")} 新增字段</button>`;
    if (page === "assembly") return month ? `<span class="badge badge-gray">${icon("calendar")} ${monthLabel(state.month)}</span>` : "";
    if (page === "globals") return `<button class="btn btn-primary btn-sm" data-action="open-new-global-param">${icon("plus")} 新增全局参数</button><span class="badge badge-purple">${icon("database")} 系统级</span>`;
    return "";
  }

  function renderAPage(page) {
    const monthly = MONTHLY_PAGES.includes(page);
    return `
      ${pageHead(pageLabel(page), pageSub(page), pageActions(page))}
      ${monthly ? renderMonthBar() : renderConfigContext()}
      ${renderBody(page)}`;
  }

  function renderConfigContext() {
    return `<div class="config-context">
      ${icon("info")}
      <div><strong>公司级配置</strong> · 修改后当前月标记「配置已更新」并推荐重算；历史月沿用最近成功批次快照，不会被改写。<span class="muted">（法定参数与字段定义除外，见「全局参数 / 字段与公式」）</span></div>
    </div>`;
  }

  function renderBody(page) {
    switch (page) {
      case "list": return renderListBody();
      case "import": return renderImportBody();
      case "calc": return renderCalcBody();
      case "payslips": return renderPayslipsBody();
      case "cost": return renderCostBody();
      case "compositions": return renderCompositionsBody();
      case "schemes": return renderSchemesBody();
      case "workday": return renderWorkdayBody();
      case "assembly": return renderAssemblyBody();
      case "fields": return renderFieldsBody();
      case "globals": return renderGlobalsBody();
      default: return renderListBody();
    }
  }

  function renderTabs(tabs, current, action = "nav") {
    return `<div class="tabs" role="tablist">
      ${tabs.map((tab) => `<button class="tab ${tab.page === current ? "active" : ""}" data-action="${action}" data-page="${tab.page}" role="tab" aria-selected="${tab.page === current}">${esc(tab.label)}${tab.badge ? `<span class="tab-count">${tab.badge}</span>` : ""}</button>`).join("")}
    </div>`;
  }

  function renderWorkbench(page) {
    const content = renderBody(page);
    const tabs = MONTHLY_TABS.map((t) => ({ ...t }));
    return `
      ${renderMonthRibbon()}
      ${renderTabs(tabs, page)}
      <div class="pay-workbench-body">
        ${pageHead(pageLabel(page), pageSub(page), pageActions(page))}
        ${content}
      </div>`;
  }

  function renderConfigHub(page) {
    if (state.companyId !== "c1") return `${pageHead(pageLabel(page), pageSub(page))}${companyEmpty()}`;
    const unconfigured = db.positions.filter((p) => !p.payroll).length;
    const tabs = CONFIG_TABS.map((t) => ({ ...t, badge: t.page === "assembly" && unconfigured ? unconfigured : "" }));
    return `
      <div class="config-hero">
        <div>
          <div class="config-hero-title">${icon("settings")} 薪资配置中心</div>
          <p>配置在这里统一维护；月度工作台只消费配置结果。当前 ${db.compositions.length} 套构成、${db.schemes.length} 个方案、${db.workdayParams.length} 组工作日参数、${db.fieldDefs.length} 个字段。</p>
        </div>
        <div class="config-health">
          <span class="badge ${unconfigured ? "badge-orange" : "badge-green"}">${unconfigured ? `${unconfigured} 个岗位未装配` : "岗位装配完整"}</span>
          <span class="badge badge-gray">引擎 ${db.engineVersion}</span>
        </div>
      </div>
      ${renderTabs(tabs, page)}
      <div class="pay-workbench-body">
        ${pageHead(pageLabel(page), pageSub(page), pageActions(page))}
        ${renderBody(page)}
      </div>`;
  }

  function renderMode(page) {
    const month = currentMonth();
    return `
      <div class="mode-head">
        <button class="btn btn-ghost btn-sm" data-action="nav" data-page="cockpit">${icon("arrow-left")} 返回驾驶舱</button>
        <div class="mode-title">${pageLabel(page)}</div>
        <div class="spacer"></div>
        ${month ? stateBadge(month) : ""}
      </div>
      ${month ? renderMonthBar({ compact: true }) : ""}
      ${renderBody(page)}`;
  }

  function renderConfigCenter(page) {
    if (state.companyId !== "c1") return `${pageHead(pageLabel(page), pageSub(page))}${companyEmpty()}`;
    return `
      <div class="config-center">
        <aside class="config-rail" aria-label="配置分区">
          <div class="config-rail-title">配置中心</div>
          ${CONFIG_TABS.map((tab) => `<button class="rail-item ${tab.page === page ? "active" : ""}" data-action="nav" data-page="${tab.page}">${esc(tab.label)}${tab.page === "assembly" && db.positions.some((p) => !p.payroll) ? `<span class="rail-dot"></span>` : ""}</button>`).join("")}
        </aside>
        <div class="config-main">
          ${pageHead(pageLabel(page), pageSub(page), pageActions(page))}
          ${renderBody(page)}
        </div>
      </div>`;
  }

  /* ---------------------------------------------------------------- month bar / gates */

  function employeeScope(month) {
    if (!month) return [];
    return H.employeesInScope(db, month.companyId, month.key);
  }

  function unconfiguredEmployees(month) {
    return employeeScope(month).filter((emp) => {
      const position = db.positions.find((p) => p.id === emp.positionId);
      return !position || !position.payroll;
    });
  }

  function calcGates(month, context = "calc") {
    if (!month) return [];
    const scope = employeeScope(month);
    const unconfigured = unconfiguredEmployees(month);
    const flags = H.monthFlags(db, month);
    const success = flags.success;
    const gates = [
      {
        key: "attendance_locked",
        label: "考勤月已锁定",
        status: month.attendance.locked && month.attendance.status !== "missing" ? "pass" : "fail",
        detail: month.attendance.locked ? `考勤快照 v${month.attendance.version} · ${month.attendance.summaryCount} 人` : "考勤月尚未锁定，不能核算",
      },
      {
        key: "summary",
        label: "员工考勤月汇总完整",
        status: month.attendance.summaryCount >= scope.length && scope.length > 0 ? "pass" : "fail",
        detail: `${month.attendance.summaryCount}/${scope.length} 人有汇总`,
      },
      {
        key: "assembly",
        label: "岗位薪资装配完整",
        status: unconfigured.length === 0 ? "pass" : "fail",
        detail: unconfigured.length ? `${unconfigured.length} 人所在岗位未装配：${unconfigured.map((e) => e.name).join("、")}` : "全部在册员工岗位已装配",
      },
      {
        key: "last_run",
        label: "最近核算批次成功",
        status: flags.lastFailed || (!success && context === "confirm") ? "fail" : success ? "pass" : "warn",
        detail: flags.lastFailed ? H.lastRun(db, month).error || "最近批次失败" : success ? `最近成功批次 ${success.id}` : "尚无成功批次",
      },
      {
        key: "input_version",
        label: "输入版本与成功批次一致",
        status: success ? (flags.inputChanged ? (context === "confirm" ? "fail" : "warn") : "pass") : context === "confirm" ? "fail" : "warn",
        detail: success ? `当前 v${month.inputVersion} · 批次 v${success.inputVersion}` : "尚无成功批次",
      },
      {
        key: "attendance_fresh",
        label: "考勤来源未变化",
        status: flags.attendanceStale ? "fail" : "pass",
        detail: flags.attendanceStale ? "考勤锁定快照已变化，需重新核算" : "与最近批次一致",
      },
      {
        key: "scope",
        label: "员工范围未变化",
        status: flags.scopeStale ? "fail" : "pass",
        detail: flags.scopeStale ? "范围与最近成功批次不一致" : "与最近成功批次一致",
      },
      {
        key: "config",
        label: "配置快照状态",
        status: flags.configStale ? "warn" : "pass",
        detail: flags.configStale ? "配置已更新；确认与发放只警告，不阻断" : "与最近批次一致",
      },
    ];
    return gates;
  }

  function gateStatusIcon(status) {
    if (status === "pass") return `<span class="gate-icon pass">${icon("check-circle")}</span>`;
    if (status === "fail") return `<span class="gate-icon fail">${icon("x-circle")}</span>`;
    if (status === "warn") return `<span class="gate-icon warn">${icon("alert")}</span>`;
    return `<span class="gate-icon">${icon("info")}</span>`;
  }

  function canCalculate(month) {
    if (!month || month.state === "paid" || month.state === "confirmed") return false;
    const gates = calcGates(month);
    return !gates.some((g) => g.status === "fail" && ["attendance_locked", "summary", "assembly"].includes(g.key));
  }

  function canConfirm(month) {
    if (!month || month.state !== "calculated") return false;
    const flags = H.monthFlags(db, month);
    return Boolean(flags.success) && !flags.inputChanged && !flags.attendanceStale && !flags.scopeStale && !flags.lastFailed;
  }

  function monthPrimaryAction(month) {
    if (!month) return "";
    if (month.state === "paid") return `<button class="btn btn-outline btn-sm" data-action="open-unlock">${icon("unlock")} 解锁</button>`;
    if (month.state === "confirmed") return `<button class="btn btn-primary btn-sm" data-action="open-pay">${icon("file")} 发工资条</button>`;
    if (month.state === "calculated") {
      const ok = canConfirm(month);
      return `<button class="btn btn-primary btn-sm" data-action="open-confirm" ${ok ? "" : 'disabled title="确认门槛未满足，请在核算页查看检查项"'}>${icon("check-circle")} 确认</button>`;
    }
    const ok = canCalculate(month);
    return `<button class="btn btn-primary btn-sm" data-action="calculate" ${ok ? "" : 'disabled title="核算前检查未通过"'}>${state.calcRunning ? `${icon("refresh", "spin")} 核算中…` : `${icon("play")} 开始核算`}</button>`;
  }

  function renderMonthBar(options = {}) {
    const month = currentMonth();
    if (!month) {
      return `<div class="notice info">${icon("info")} 当前公司暂无薪资月份。切换公司或前往基础管理维护公司。</div>`;
    }
    const flags = H.monthFlags(db, month);
    const optionsHtml = monthsForCompany().map((key) => {
      const m = db.months[key];
      return `<option value="${key}" ${key === state.month ? "selected" : ""}>${monthLabel(key)} · ${STATE_META[m.state].label}</option>`;
    }).join("");
    const success = flags.success;
    return `<div class="month-bar ${options.compact ? "compact" : ""}">
      <div class="month-main">
        <span class="month-switch">${icon("calendar")}
          <select data-select="month" aria-label="选择薪资月份">${optionsHtml}</select>
        </span>
        ${stateBadge(month)}
        <span class="month-meta">输入版本 <strong>v${month.inputVersion}</strong> · ${success ? `最近成功核算 ${esc(success.finishedAt)}` : "尚无成功批次"} · 考勤 ${month.attendance.locked ? `已锁定 v${month.attendance.version}` : "未锁定"}</span>
        <span class="month-flags">${flagsBadges(month)}</span>
        <span class="spacer"></span>
        <div class="month-actions">
          <button class="btn btn-outline btn-sm" data-action="go-page" data-page="import">${icon("upload")} 导入</button>
          ${month.state === "calculated" ? `<button class="btn btn-outline btn-sm" data-action="calculate" ${canCalculate(month) ? "" : "disabled"}>${icon("refresh")} 重新核算</button>` : ""}
          ${month.state === "confirmed" ? `<button class="btn btn-outline btn-sm" data-action="open-unconfirm">${icon("rotate-ccw")} 取消确认</button>` : ""}
          ${monthPrimaryAction(month)}
        </div>
      </div>
      ${options.compact ? "" : `<div class="month-foot">
        <span>${icon("info")} ${H.monthClass(db, month.key) === "current" ? "当前薪资月：重算采用最新配置" : "历史薪资月：重算沿用最近成功批次快照"}</span>
        <span>${month.state === "paid" ? "已发月份锁定；解锁需理由并保留快照" : "确认 / 发放需考勤新鲜、输入版本未变、范围未变"}</span>
      </div>`}
    </div>`;
  }

  function renderMonthRibbon() {
    const month = currentMonth();
    if (!month) return `<div class="notice info">${icon("info")} 当前公司暂无薪资月份。</div>`;
    const stateOrder = ["draft", "calculated", "confirmed", "paid"];
    const currentIndex = stateOrder.indexOf(month.state);
    const steps = [
      { key: "import", label: "月度导入", page: "import", done: month.inputVersion > 0, current: month.state === "draft" },
      { key: "calc", label: "核算", page: "calc", done: currentIndex >= 1, current: month.state === "draft" },
      { key: "confirm", label: "确认", page: "calc", done: currentIndex >= 2, current: month.state === "calculated" },
      { key: "paid", label: "发工资条", page: "payslips", done: currentIndex >= 3, current: month.state === "confirmed" },
    ];
    const optionsHtml = monthsForCompany().map((key) => `<option value="${key}" ${key === state.month ? "selected" : ""}>${monthLabel(key)} · ${STATE_META[db.months[key].state].label}</option>`).join("");
    return `<div class="workbench-ribbon">
      <div class="ribbon-top">
        <span class="month-switch">${icon("calendar")}<select data-select="month" aria-label="选择薪资月份">${optionsHtml}</select></span>
        ${stateBadge(month)}
        <span class="month-meta">v${month.inputVersion} · 考勤 ${month.attendance.locked ? `锁定 v${month.attendance.version}` : "未锁定"}</span>
        <span class="month-flags">${flagsBadges(month)}</span>
        <span class="spacer"></span>
        ${monthPrimaryAction(month)}
      </div>
      <div class="stepper">
        ${steps.map((step, i) => `<button class="step ${step.done ? "done" : ""} ${step.current ? "current" : ""}" data-action="nav" data-page="${step.page}">
          <span class="step-dot">${step.done ? icon("check") : i + 1}</span>
          <span class="step-label">${step.label}</span>
        </button>${i < steps.length - 1 ? `<span class="step-line ${step.done ? "done" : ""}"></span>` : ""}`).join("")}
      </div>
    </div>`;
  }

  /* ---------------------------------------------------------------- preview states */

  function renderPreviewState() {
    const title = pageLabel(state.page);
    if (state.preview === "loading") {
      return `${pageHead(title, pageSub(state.page))}
        <div class="skeleton-page">
          <div class="skeleton-cards">${Array.from({ length: 4 }, () => '<div class="skeleton-card"><div class="skeleton w-30"></div><div class="skeleton w-70"></div><div class="skeleton w-50"></div></div>').join("")}</div>
          <div class="card" style="padding:16px"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton w-70"></div><div class="skeleton"></div></div>
        </div>`;
    }
    if (state.preview === "empty") {
      return `${pageHead(title, pageSub(state.page))}
        <div class="empty"><div class="empty-icon">${icon("inbox")}</div><h3>暂无数据</h3><p>这是「空数据」预览状态。正常数据请把底部状态切回「正常」。</p><button class="btn btn-outline btn-sm" data-action="set-preview" data-preview="normal">${icon("refresh")} 恢复数据</button></div>`;
    }
    return `${pageHead(title, pageSub(state.page))}
      <div class="empty"><div class="empty-icon">${icon("alert")}</div><h3>页面加载失败</h3><p>演示错误状态：接口返回 500，或考勤快照读取失败。真实实现应区分可重试与不可重试错误。</p><button class="btn btn-primary btn-sm" data-action="set-preview" data-preview="normal">${icon("refresh")} 重试</button></div>`;
  }

  /* ---------------------------------------------------------------- overlay shell */

  function modal({ title, sub, body, foot, size = "", key = "" }) {
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal ${size}" role="dialog" aria-modal="true" aria-label="${esc(title)}" data-key="${esc(key)}">
        <div class="modal-head">
          <div><h2 class="modal-title">${esc(title)}</h2>${sub ? `<p class="modal-sub">${sub}</p>` : ""}</div>
          <button class="btn btn-ghost btn-icon" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">${body}</div>
        ${foot ? `<div class="modal-foot">${foot}</div>` : ""}
      </div>`;
  }

  function sheet({ title, sub, body, foot, key = "" }) {
    return `<div class="sheet-backdrop" data-action="close-overlay"></div>
      <div class="sheet" role="dialog" aria-modal="true" aria-label="${esc(title)}" data-key="${esc(key)}">
        <div class="sheet-head">
          <div><h2 class="sheet-title">${esc(title)}</h2>${sub ? `<p class="sheet-sub">${sub}</p>` : ""}</div>
          <button class="btn btn-ghost btn-icon" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="sheet-body">${body}</div>
        ${foot ? `<div class="sheet-foot">${foot}</div>` : ""}
      </div>`;
  }

  function renderOverlayRoot() {
    const root = document.getElementById("overlay-root");
    if (!root) return;
    let html = "";
    if (state.overlay) html += renderOverlay(state.overlay);
    if (state.toast) {
      html += `<div class="toast ${state.toast.type}">${icon(state.toast.type === "error" ? "alert" : "check-circle")}<span>${esc(state.toast.message)}</span></div>`;
    }
    root.innerHTML = html;
  }

  function openOverlay(type, props = {}) {
    state.overlay = { type, ...props };
    renderOverlayRoot();
    focusAutofocus();
  }

  function closeOverlay() {
    state.overlay = null;
    renderOverlayRoot();
  }

  /* ---------------------------------------------------------------- common bits */

  function notice(type, text) {
    const iconName = type === "danger" ? "x-circle" : type === "warn" ? "alert" : "info";
    return `<div class="notice ${type === "danger" ? "danger" : type === "warn" ? "warn" : "info"}">${icon(iconName)}<div>${text}</div></div>`;
  }

  function kpi(label, value, hint = "", cls = "") {
    return `<div class="kpi ${cls}"><div class="kpi-label">${label}</div><div class="kpi-value">${value}</div>${hint ? `<div class="kpi-hint">${hint}</div>` : ""}</div>`;
  }

  function emptyState({ title, desc, actions = "", iconName = "inbox" }) {
    return `<div class="empty"><div class="empty-icon">${icon(iconName)}</div><h3>${esc(title)}</h3><p>${desc}</p>${actions}</div>`;
  }

  function companyEmpty() {
    return emptyState({
      title: `${currentCompany().name} 暂无薪资数据`,
      desc: "当前公司还没有薪资月份或配置。原型为荣新矿业准备了完整样例；可在顶栏切回荣新矿业，或查看空状态设计。",
      actions: `<button class="btn btn-primary btn-sm" data-action="select-company" data-company="c1">${icon("arrow-left")} 返回荣新矿业</button>`,
      iconName: "building",
    });
  }

  /* ---------------------------------------------------------------- payroll list */

  function sourceForMonth(month = currentMonth()) {
    return month ? H.monthResults(db, month) : null;
  }

  function departmentDepth(dept) {
    let depth = 0;
    let current = dept;
    while (current && current.parentId) {
      depth += 1;
      current = db.departments.find((d) => d.id === current.parentId);
    }
    return depth;
  }

  function departmentOptions(selected = "all") {
    const rows = [];
    const walk = (parentId, depth) => {
      for (const dept of db.departments.filter((d) => d.parentId === parentId).sort((a, b) => a.order - b.order)) {
        rows.push(`<option value="${dept.id}" ${selected === dept.id ? "selected" : ""}>${"　".repeat(depth)}${esc(dept.name)}</option>`);
        walk(dept.id, depth + 1);
      }
    };
    walk(null, 0);
    return `<option value="all" ${selected === "all" ? "selected" : ""}>全部部门（含下级）</option>${rows.join("")}`;
  }

  function costCenterOptions(selected = "all") {
    const rows = [];
    const walk = (parentId, depth) => {
      for (const cc of db.costCenters.filter((c) => c.parentId === parentId).sort((a, b) => a.code.localeCompare(b.code))) {
        rows.push(`<option value="${cc.code}" ${selected === cc.code ? "selected" : ""}>${"　".repeat(depth)}${esc(cc.name)}（含下级）</option>`);
        walk(cc.id, depth + 1);
      }
    };
    walk(null, 0);
    return `<option value="all" ${selected === "all" ? "selected" : ""}>全部成本中心（含下级）</option><option value="unassigned" ${selected === "unassigned" ? "selected" : ""}>未分配</option>${rows.join("")}`;
  }

  function positionOptions(selected = "all") {
    return `<option value="all" ${selected === "all" ? "selected" : ""}>全部岗位</option>${db.positions.map((p) => `<option value="${p.id}" ${selected === p.id ? "selected" : ""}>${esc(p.name)}</option>`).join("")}`;
  }

  function deptPathIncludes(path, deptId) {
    return (path || []).some((step) => step.id === deptId);
  }

  function filteredResults(source) {
    if (!source) return [];
    const { dept, position, cost, q } = state.listFilters;
    const keyword = q.trim().toLowerCase();
    return source.results.filter((row) => {
      if (dept !== "all" && !deptPathIncludes(row.deptPath, dept)) return false;
      if (position !== "all" && row.positionId !== position) return false;
      if (cost === "unassigned" && row.costPath.length) return false;
      if (cost !== "all" && cost !== "unassigned" && !row.costPath.some((step) => step.code === cost)) return false;
      if (keyword && !`${row.employeeNo} ${row.employeeName}`.toLowerCase().includes(keyword)) return false;
      return true;
    }).sort((a, b) => a.employeeNo.localeCompare(b.employeeNo));
  }

  function listFields(source) {
    const defs = source?.fieldDefs || db.fieldDefs;
    return state.listColumns
      .map((key) => defs.find((f) => f.field_key === key))
      .filter(Boolean)
      .sort((a, b) => a.display_order - b.display_order);
  }

  function isMoneyField(field) {
    return ["earning", "addon", "deduction", "total"].includes(field.category);
  }

  function listCell(field, result) {
    const value = result.values[field.field_key];
    if (value == null) return "—";
    return isMoneyField(field) ? moneyPlain(value) : num(value, 2);
  }

  function listTotal(field, results) {
    if (!results.length) return "—";
    const total = results.reduce((acc, row) => acc + Number(row.values[field.field_key] || 0), 0);
    return isMoneyField(field) ? moneyPlain(total) : num(total, 2);
  }

  function renderListBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const month = currentMonth();
    if (!month) return emptyState({ title: "暂无薪资月", desc: "请先创建薪资月。", iconName: "calendar" });
    const source = sourceForMonth(month);
    const flags = H.monthFlags(db, month);
    if (!source) {
      const actions = month.state === "draft"
        ? `<button class="btn btn-primary btn-sm" data-action="go-page" data-page="import">${icon("upload")} 去导入</button><button class="btn btn-outline btn-sm" data-action="go-page" data-page="calc">${icon("calculator")} 查看核算检查</button>`
        : `<button class="btn btn-primary btn-sm" data-action="go-page" data-page="calc">${icon("calculator")} 去核算</button>`;
      return `${notice("info", `当前月份为 <strong>${STATE_META[month.state].label}</strong>，尚无成功核算结果。工资列表只读取已发快照或当前成功批次。`)}
        ${emptyState({ title: "还没有可展示的薪资结果", desc: "先在「月度导入」提交当月输入，并在「核算与确认」通过检查后开始核算。", actions, iconName: "calculator" })}`;
    }
    const rows = filteredResults(source);
    const fields = listFields(source);
    const totals = H.aggregateResults(rows);
    const filtersActive = state.listFilters.dept !== "all" || state.listFilters.position !== "all" || state.listFilters.cost !== "all" || state.listFilters.q;
    const notices = [];
    if (flags.needsRecalc) notices.push(notice("warn", "当前结果早于最近一次输入 / 考勤 / 范围变化，列表仍展示上一次成功结果；确认与发放已阻断，需重新核算。"));
    if (flags.lastFailed) notices.push(notice("danger", `最近一次核算失败：${esc(H.lastRun(db, month)?.error || "未知错误")}。失败批次不改变当前结果。`));
    if (month.state === "paid") notices.push(notice("info", `已发月份读取 <strong>已发快照 v${month.paidSnapshot?.version || 1}</strong>；解锁或重算不会改写已发版本。`));
    const unconfigured = unconfiguredEmployees(month);
    if (unconfigured.length) notices.push(notice("warn", `${unconfigured.length} 名在册员工所在岗位未装配薪资配置：${unconfigured.map((e) => esc(e.name)).join("、")}。核算会整体失败。`));
    return `
      <div class="stat-grid">
        ${kpi("结果人数", `${rows.length}<small> / ${source.results.length} 人</small>`, source.source === "paid" ? "已发快照" : "当前成功批次")}
        ${kpi("应发合计", money(totals.gross), "gross")}
        ${kpi("代扣合计", money(Math.abs(totals.social + totals.tax)), "社保 + 个税")}
        ${kpi("实发合计", money(totals.net), "net", totals.net < 0 ? "negative" : "")}
      </div>
      ${notices.join("")}
      <div class="card payroll-card">
        <div class="card-head">
          <div class="inline">
            <h3>${monthLabel(month.key)}</h3>
            <span class="badge badge-gray">${source.source === "paid" ? `已发快照 v${month.paidSnapshot.version}` : `当前成功批次 ${month.lastRunId}`}</span>
            <span class="badge badge-gray">${fields.length} 列可见</span>
          </div>
          <div class="inline">
            <button class="btn btn-outline btn-sm" data-action="open-columns">${icon("columns")} 列设置</button>
            <button class="btn btn-outline btn-sm" data-action="download-payroll-detail">${icon("download")} 导出明细</button>
          </div>
        </div>
        <div class="filter-bar">
          <label>部门<select data-select="list-dept">${departmentOptions(state.listFilters.dept)}</select></label>
          <label>岗位<select data-select="list-position">${positionOptions(state.listFilters.position)}</select></label>
          <label>成本中心<select data-select="list-cost">${costCenterOptions(state.listFilters.cost)}</select></label>
          <label class="search-field">${icon("search")}<input class="input" data-input="list-search" placeholder="搜索工号 / 姓名" value="${esc(state.listFilters.q)}"></label>
          ${filtersActive ? `<button class="btn btn-ghost btn-sm" data-action="clear-list-filters">${icon("x")} 清除筛选</button>` : ""}
          <span class="spacer"></span>
          <span class="sub">点击行查看全部字段、来源与公式</span>
        </div>
        <div class="table-wrap">
          <table class="table payroll-table">
            <thead><tr>
              <th>工号</th><th>姓名</th><th>部门</th><th>岗位</th><th>成本归属</th>
              ${fields.map((f) => `<th class="${isMoneyField(f) ? "num" : ""}" title="${esc(f.field_key)}">${esc(f.label)}</th>`).join("")}
            </tr></thead>
            <tbody>
              ${rows.map((row) => `<tr class="clickable" data-action="open-employee" data-employee="${row.employeeId}">
                <td class="nowrap">${esc(row.employeeNo)}</td>
                <td class="nowrap name">${esc(row.employeeName)}</td>
                <td class="nowrap">${esc(row.deptName)}</td>
                <td class="nowrap">${esc(row.positionName)}</td>
                <td class="nowrap">${row.costPath.length ? esc(row.costPath[row.costPath.length - 1].name) : '<span class="muted">未分配</span>'}</td>
                ${fields.map((f) => `<td class="${isMoneyField(f) ? "num" : ""}">${listCell(f, row)}</td>`).join("")}
              </tr>`).join("")}
            </tbody>
            <tfoot><tr class="total-row">
              <td colspan="5">合计 · ${rows.length} 人</td>
              ${fields.map((f) => `<td class="${isMoneyField(f) ? "num" : ""}">${listTotal(f, rows)}</td>`).join("")}
            </tr></tfoot>
          </table>
        </div>
        ${rows.length === 0 ? `<div class="table-empty">没有符合筛选条件的员工。${filtersActive ? `<button class="btn btn-ghost btn-sm" data-action="clear-list-filters">清除筛选</button>` : ""}</div>` : ""}
        <div class="card-foot">
          <span>${icon("info")} 列顺序与显隐来自全局字段定义；列表合计只对当前筛选结果求和。</span>
          <span class="sub">${source.source === "paid" ? "数据源：已发快照" : `数据源：${source.label}`}</span>
        </div>
      </div>`;
  }

  /* ---------------------------------------------------------------- employee detail */

  function openEmployeeDetail(employeeId) {
    openOverlay("employee-detail", { employeeId });
  }

  function renderEmployeeDetailOverlay(overlay) {
    const month = currentMonth();
    const source = sourceForMonth(month);
    if (!source) return modal({ title: "薪资明细", body: notice("info", "当前月份尚无成功结果。") });
    const row = source.results.find((r) => r.employeeId === overlay.employeeId);
    if (!row) return modal({ title: "薪资明细", body: notice("warn", "该员工不在当前数据源范围内。") });
    const defs = source.fieldDefs || db.fieldDefs;
    const scheme = H.schemeFor(db, row.config.schemeCode);
    const grouped = {};
    for (const category of ["earning", "addon", "deduction", "reference"]) {
      grouped[category] = defs.filter((f) => f.category === category && f.is_active !== false && f.calc_mode !== "total");
    }
    const subtype = (field) => {
      if (field.calc_mode === "formula") return `<code class="formula-inline" title="${esc(H.effectiveFormula(field, scheme) || "")}">${esc(H.effectiveFormula(field, scheme) || "")}</code>`;
      if (field.calc_mode === "plan") return `<span class="muted">取构成 · ${esc(field.source_key)}</span>`;
      if (field.calc_mode === "import") return `<span class="muted">取输入 · ${esc(field.source_key)}</span>`;
      return `<span class="muted">固定值</span>`;
    };
    const subtotal = (key) => `<tr class="subtotal-row"><td>${esc(defs.find((f) => f.field_key === key)?.label || key)}</td><td class="num">${money(row.values[key])}</td><td><span class="badge badge-gray">小计</span></td><td class="sub">${esc(key)}</td></tr>`;
    const checks = H.consistencyChecks(row);
    const paid = month.state === "paid";
    const canManual = !paid && month.state !== "confirmed";
    return sheet({
      title: `${row.employeeName} · ${monthLabel(month.key)}`,
      sub: `${row.employeeNo} · ${esc(row.deptPath.map((d) => d.name).join(" / "))} · ${esc(row.positionName)} · ${row.costPath.length ? esc(row.costPath.map((c) => c.name).join(" / ")) : "未分配成本中心"}`,
      body: `
        <div class="stat-grid compact">
          ${kpi("应发", money(row.values.gross), "gross")}
          ${kpi("社保", money(Math.abs(row.values.social_this)), "代扣")}
          ${kpi("个税", money(Math.abs(row.values.tax)), "代扣")}
          ${kpi("实发", money(row.values.net), "net")}
        </div>
        ${paid ? notice("info", `本行来自<strong>已发快照 v${month.paidSnapshot.version}</strong>，字段标签、顺序与显隐为发放时冻结值。`) : ""}
        <div class="section-title">金额字段与来源</div>
        <table class="table detail-table">
          <thead><tr><th>字段</th><th class="num">值</th><th>来源</th><th>公式 / 取数</th></tr></thead>
          <tbody>
            ${["earning", "addon", "deduction"].map((category) => `
              <tr class="group-row"><td colspan="4">${Data.CATEGORY[category]}</td></tr>
              ${grouped[category].map((field) => `<tr>
                <td>${esc(field.label)} <span class="sub">${esc(field.field_key)}</span></td>
                <td class="num">${money(row.values[field.field_key])}</td>
                <td>${sourceBadge(field.calc_mode)}</td>
                <td class="formula-cell">${subtype(field)}</td>
              </tr>`).join("")}
              ${category === "earning" ? subtotal("normal_pay") : category === "addon" ? subtotal("addon_sum") : subtotal("deduct_sum")}
            `).join("")}
          </tbody>
        </table>
        <div class="section-title">考勤来源（只读）</div>
        <div class="mini-table-wrap">
          <table class="mini-table">
            <thead><tr><th>考勤月</th><th>锁定版本</th><th>工作日出勤</th><th>周末出勤</th><th>带薪假</th><th>工作日加班</th><th>周末加班</th><th>节假日加班</th><th>考勤扣款</th></tr></thead>
            <tbody><tr>
              <td>${month.key}</td><td>v${month.attendance.version}</td>
              <td>${num(row.values.weekday_attended, 1)} / ${num(row.values.weekday_full, 0)}</td>
              <td>${num(row.values.weekend_attended, 1)} / ${num(row.values.weekend_full, 0)}</td>
              <td>${num(row.values.paid_leave_days, 1)}</td>
              <td>${num(row.values.ot_weekday_hours, 1)}h</td>
              <td>${num(row.values.ot_weekend_hours, 1)}h</td>
              <td>${num(row.values.ot_holiday_hours, 1)}h</td>
              <td>${money(row.values.attendance_deduct)}</td>
            </tr></tbody>
          </table>
        </div>
        <div class="section-title">配置快照</div>
        <div class="snapshot-grid">
          <div><span class="sub">薪资构成</span><strong>${esc(row.config.compositionName)} · v${row.config.compositionVersion}</strong></div>
          <div><span class="sub">计算方案</span><strong>${esc(row.config.schemeName)}</strong></div>
          <div><span class="sub">工作日参数</span><strong>${esc(row.config.workdayName)}</strong></div>
          <div><span class="sub">公式引擎</span><strong>${esc(row.config.engineVersion)}</strong></div>
          <div><span class="sub">核算批次</span><strong>${paid ? month.paidSnapshot.runId : month.lastRunId}</strong></div>
          <div><span class="sub">输入版本</span><strong>v${paid ? month.paidSnapshot.inputVersion : month.inputVersion}</strong></div>
        </div>
        <div class="section-title">一致性校验</div>
        <div class="check-list">
          ${checks.map((check) => `<div class="check-row ${check.pass ? "pass" : "fail"}">${check.pass ? icon("check-circle") : icon("x-circle")}<span>${esc(check.label)}</span><span class="spacer"></span><span class="sub">${money(check.actual)} / ${money(check.expected)}</span></div>`).join("")}
        </div>`,
      foot: `${canManual ? `<button class="btn btn-outline btn-sm" data-action="open-manual" data-employee="${row.employeeId}">${icon("edit")} 手工录入</button>` : ""}
        <span class="spacer"></span>
        <button class="btn btn-outline btn-sm" data-action="close-overlay">关闭</button>
        <button class="btn btn-primary btn-sm" data-action="open-payslip-employee" data-employee="${row.employeeId}">${icon("file")} 查看工资条</button>`,
      key: `employee-${row.employeeId}`,
    });
  }

  function renderColumnsOverlay() {
    const groups = ["earning", "addon", "deduction", "reference", "total"];
    return modal({
      title: "列设置",
      sub: "列顺序与显隐来自全局字段定义；原型允许本次查看临时勾选，不写回配置。",
      body: `<div class="column-groups">
        ${groups.map((category) => {
          const fields = db.fieldDefs.filter((f) => f.category === category && f.is_active !== false).sort((a, b) => a.display_order - b.display_order);
          return `<div class="column-group">
            <div class="column-group-title">${Data.CATEGORY[category]}<span class="sub">${fields.length} 个字段</span></div>
            <div class="column-options">
              ${fields.map((field) => `<label class="check-option"><input type="checkbox" data-column="${field.field_key}" ${state.listColumns.includes(field.field_key) ? "checked" : ""}><span>${esc(field.label)} <span class="sub">${esc(field.field_key)}</span></span></label>`).join("")}
            </div>
          </div>`;
        }).join("")}
      </div>`,
      foot: `<button class="btn btn-ghost btn-sm" data-action="reset-columns">恢复默认列</button><span class="spacer"></span><span class="sub">已选 ${state.listColumns.length} 列</span><button class="btn btn-primary btn-sm" data-action="close-overlay">完成</button>`,
      size: "lg",
      key: "columns",
    });
  }

  function renderManualInputOverlay(overlay) {
    const month = currentMonth();
    if (!month || month.state === "paid") {
      return modal({ title: "手工录入", body: notice("danger", "已发月份锁定，不能修改输入。需先解锁并取消确认。") });
    }
    if (month.state === "confirmed") {
      return modal({ title: "手工录入", body: notice("warn", "已确认月份不能直接修改输入；请先取消确认。") });
    }
    const input = month.inputs[overlay.employeeId] || {};
    const payrollFields = db.fieldDefs.filter((f) => f.calc_mode === "import" && Data.PAYROLL_IMPORT_FIELDS.includes(f.field_key));
    const attendanceFields = db.fieldDefs.filter((f) => Data.ATTENDANCE_FIELDS.includes(f.field_key));
    return modal({
      title: "手工录入",
      sub: `${monthLabel(month.key)} · 保存后输入版本递增，当前结果标记待重算；不会自动重算。`,
      body: `
        <div class="section-title">薪资自有字段</div>
        <div class="form-grid">
          ${payrollFields.map((field) => `<div class="field">
            <label>${esc(field.label)} <span class="sub">${esc(field.field_key)}</span></label>
            <input class="input" type="number" step="0.01" data-manual-field="${field.field_key}" value="${Number(input[field.source_key] || 0)}">
            <span class="hint">${esc(Data.CALC_MODE[field.calc_mode])}字段</span>
          </div>`).join("")}
        </div>
        <div class="section-title">考勤自有字段（只读）</div>
        <div class="mini-table-wrap">
          <table class="mini-table">
            <thead><tr>${attendanceFields.map((f) => `<th>${esc(f.label)}</th>`).join("")}</tr></thead>
            <tbody><tr>${attendanceFields.map((f) => `<td>${num(input[f.source_key] || 0, 2)}</td>`).join("")}</tr></tbody>
          </table>
        </div>
        <div class="notice info">${icon("info")}<div>考勤自有 9 个值只从考勤模块已锁定月汇总读取，薪资不提供手工编辑；文件导入也不会覆盖它们。</div></div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="save-manual" data-employee="${overlay.employeeId}">${icon("check")} 保存输入</button>`,
      size: "lg",
      key: `manual-${overlay.employeeId}`,
    });
  }

  function saveManualInput(employeeId) {
    const month = currentMonth();
    if (!month || month.state === "paid" || month.state === "confirmed") {
      showToast("当前月状态不允许手工录入", "error");
      return;
    }
    const values = {};
    document.querySelectorAll("[data-manual-field]").forEach((el) => {
      values[el.dataset.manualField] = Number(el.value || 0);
    });
    month.inputs[employeeId] = { ...(month.inputs[employeeId] || {}), ...values };
    month.inputVersion += 1;
    month.manualValues[employeeId] = {
      at: "2026-11-28 09:00",
      by: "管理员",
      fields: Object.keys(values),
    };
    month.events.push({ at: "2026-11-28 09:00", type: "input", label: `手工录入 · ${employeeName(employeeId)}`, by: "管理员", reason: "" });
    closeOverlay();
    render();
    showToast(`手工输入已保存，输入版本升至 v${month.inputVersion}；请重新核算`);
  }

  function employeeName(employeeId) {
    return db.employees.find((e) => e.id === employeeId)?.name || employeeId;
  }

  /* ---------------------------------------------------------------- monthly import */

  const IMPORT_SAMPLE = `工号,姓名,工作日出勤,周末出勤,话费,车补,其他,生产奖,提成,行政扣减,本期社保,本期个税,已发
E101,冯芷茵,20,4,100,300,0,300,0,0,-735,-180,0
E102,刘衍英,20,2,100,200,0,0,0,0,-892.5,-255,0
E103,周玉琼,20,6,100,300,0,400,0,0,-735,-180,0
E103,周玉琼,20,6,100,300,0,400,0,0,-735,-180,0
E104,陈敏,20,2,120,300,0,300,0,0,-735,-180,0
E105,李金辉,19.5,6,100,200,0,400,0,0,-735,-180,0
E106,黄佳誉,20,4,100,300,0,0,0,0,-1470,-270,0
E107,梁林高,20,0,100,200,100,0,0,0,-892.5,-255,0
E108,黄国锋,20,10,100,300,0,500,0,0,-735,-180,0
E109,申佳林,20,0,100,200,0,0,0,-50,-892.5,-255,0
E110,张伟,18,4,100,300,0,300,0,0,-735,-180,0
E111,张伟,20,2,100,200,0,0,0,0,-892.5,-255,0
E112,王强,20,0,100,200,0,0,0,0,-735,-180,0
E115,陈晓,20,4,100,300,0,0,0,0,-1470,-270,0
E999,测试员工,20,0,100,0,0,0,0,0,0,0,0`;

  function batchStatusBadge(status) {
    const map = {
      committed: { label: "生效", cls: "badge-green" },
      superseded: { label: "已替代", cls: "badge-gray" },
      preview: { label: "预览", cls: "badge-blue" },
      expired: { label: "已过期", cls: "badge-gray" },
    };
    const meta = map[status] || { label: status, cls: "badge-gray" };
    return `<span class="badge ${meta.cls}">${meta.label}</span>`;
  }

  function importAllowed(month) {
    return Boolean(month && (month.state === "draft" || month.state === "calculated"));
  }

  function renderImportBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const month = currentMonth();
    if (!month) return emptyState({ title: "暂无薪资月", desc: "请先创建薪资月。", iconName: "calendar" });
    const allowed = importAllowed(month);
    const committed = [...month.batches].reverse().find((b) => b.status === "committed");
    const sampleInput = month.inputs[employeeScope(month)[0]?.id] || {};
    const attendanceState = !month.attendance.locked
      ? { label: "未锁定", cls: "badge-red" }
      : month.attendance.status === "stale"
        ? { label: "已变化", cls: "badge-orange" }
        : { label: "已锁定", cls: "badge-green" };
    return `
      ${allowed ? "" : notice("warn", month.state === "paid" ? "已发月份锁定输入与批次。解锁并取消确认后才能重新导入。" : "已确认月份不能直接导入；请先在「核算与确认」取消确认。")}
      <div class="import-grid">
        <div class="card">
          <div class="card-head">
            <div><h3>${icon("calendar")} 考勤来源</h3><span class="sub">只读 · 来自考勤模块已锁定月汇总</span></div>
            <span class="badge ${attendanceState.cls}">${attendanceState.label}</span>
          </div>
          <div class="card-body">
            <div class="source-line">
              <div><span class="sub">考勤月</span><strong>${month.key}</strong></div>
              <div><span class="sub">锁定快照</span><strong>v${month.attendance.version}</strong></div>
              <div><span class="sub">汇总人数</span><strong>${month.attendance.summaryCount} 人</strong></div>
              <div><span class="sub">最近拉取</span><strong>${esc(month.attendance.pulledAt || "—")}</strong></div>
            </div>
            ${!month.attendance.locked ? notice("danger", "考勤月未锁定。可以导入薪资自有列，但不能核算；请先到考勤管理完成月结。") : ""}
            ${month.attendance.status === "stale" ? notice("warn", "考勤锁定快照在最近一次核算后发生变化。薪资结果保持不变，但确认与发放已阻断，需要重新核算。") : ""}
            <div class="section-title">考勤自有 9 值 <span class="sub">（示例：${esc(employeeScope(month)[0]?.name || "—")}）</span></div>
            <div class="attendance-values">
              ${Data.ATTENDANCE_FIELDS.map((key) => {
                const field = db.fieldDefs.find((f) => f.field_key === key);
                return `<div class="att-value"><span>${esc(field?.label || key)}</span><strong>${num(sampleInput[key] || 0, 2)}</strong></div>`;
              }).join("")}
            </div>
            <div class="card-foot-inline">
              <button class="btn btn-outline btn-sm" data-action="refresh-attendance">${icon("refresh")} 刷新考勤来源</button>
              <span class="sub">文件中的同名列会被识别但不生效</span>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-head">
            <div><h3>${icon("upload")} 薪资月度输入</h3><span class="sub">当前态 + 批次审计</span></div>
            <span class="badge badge-gray">输入版本 v${month.inputVersion}</span>
          </div>
          <div class="card-body">
            <div class="source-line">
              <div><span class="sub">当前生效批次</span><strong>${committed ? esc(committed.id) : "无"}</strong></div>
              <div><span class="sub">文件</span><strong>${committed ? esc(committed.fileName) : "—"}</strong></div>
              <div><span class="sub">行数 / 列数</span><strong>${committed ? `${committed.rows} / ${committed.columns}` : "—"}</strong></div>
              <div><span class="sub">提交时间</span><strong>${committed ? esc(committed.committedAt) : "—"}</strong></div>
            </div>
            <div class="source-line">
              <div><span class="sub">手工值</span><strong>${Object.keys(month.manualValues).length} 人</strong></div>
              <div><span class="sub">覆盖式刷新</span><strong>出现列 × 全范围</strong></div>
              <div><span class="sub">批次撤销</span><strong>不支持</strong></div>
              <div><span class="sub">原文件字节</span><strong>不保留</strong></div>
            </div>
            <div class="import-actions">
              <button class="btn btn-primary btn-sm" data-action="open-import-wizard" ${allowed ? "" : "disabled"}>${icon("plus")} 新建导入</button>
              <button class="btn btn-outline btn-sm" data-action="download-import-template">${icon("download")} 下载模板</button>
              <button class="btn btn-outline btn-sm" data-action="go-page" data-page="list">${icon("edit")} 逐人手工录入</button>
            </div>
            <div class="notice info">${icon("info")}<div>文件只承载 <strong>9 个薪资自有列</strong>；考勤自有 9 值由服务端从锁定月拉取。提交只更新输入，不自动核算。</div></div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-head"><div><h3>${icon("history")} 导入批次</h3><span class="sub">同一「公司 + 月份」同时只有一个生效批次</span></div><span class="badge badge-gray">${month.batches.length} 个批次</span></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>批次</th><th>来源</th><th>文件</th><th>状态</th><th class="num">行数</th><th class="num">列数</th><th>输入版本</th><th>提交时间</th><th>说明</th></tr></thead>
            <tbody>
              ${month.batches.length ? [...month.batches].reverse().map((batch) => `<tr>
                <td class="nowrap"><span class="name">${esc(batch.id)}</span></td>
                <td>${batch.source === "file" ? "文件" : "手工"}</td>
                <td class="nowrap">${esc(batch.fileName)}</td>
                <td>${batchStatusBadge(batch.status)}</td>
                <td class="num">${batch.rows}</td>
                <td class="num">${batch.columns}</td>
                <td>v${batch.inputVersion}</td>
                <td class="nowrap">${esc(batch.committedAt)}</td>
                <td class="sub">${esc(batch.note || "")}</td>
              </tr>`).join("") : `<tr><td colspan="9" class="table-empty-cell">本月尚无导入批次。</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-head"><div><h3>${icon("info")} 导入规则</h3><span class="sub">与 ADR-0008 一致</span></div></div>
        <div class="card-body rules-grid">
          <div><strong>出现列 × 全范围</strong><p>文件中出现的每个薪资自有列，对全范围员工覆盖；不在文件中的员工按 0 写入该列。</p></div>
          <div><strong>未出现的列不动</strong><p>文件没有携带的列保持当前值；手工值与导入值共用当前态。</p></div>
          <div><strong>考勤列只识别不生效</strong><p>文件中的考勤自有列会在映射与预览中标注为「忽略」，实际值始终来自锁定月汇总。</p></div>
          <div><strong>范围外忽略</strong><p>离职、未入职或其他公司员工按警告忽略，不写入。</p></div>
          <div><strong>无撤销</strong><p>录错以新批次覆盖；旧批次置为「已替代」，保留元数据与行级结果。</p></div>
          <div><strong>提交不核算</strong><p>输入版本递增并标记待重算；核算与确认仍需显式执行。</p></div>
        </div>
      </div>`;
  }

  function openImportWizard() {
    const month = currentMonth();
    if (!month || !importAllowed(month)) {
      showToast("当前月状态不允许导入", "error");
      return;
    }
    state.wizard = { step: 1, text: "", mapping: {}, preview: null, cleaned: false, fileName: "", error: null };
    openOverlay("import-wizard");
  }

  function parseCsvLines(text) {
    return String(text || "")
      .replace(/^﻿/, "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0)
      .map((line) => line.split(",").map((cell) => cell.trim()));
  }

  function autoMapping(headers) {
    const mapping = {};
    for (const header of headers) {
      const clean = header.trim();
      if (!clean) continue;
      const importCol = Data.IMPORT_COLUMNS.find((col) => col.header === clean);
      if (importCol) {
        mapping[clean] = importCol.key;
        continue;
      }
      if (Data.ATTENDANCE_COLUMN_ALIASES[clean]) {
        mapping[clean] = Data.ATTENDANCE_COLUMN_ALIASES[clean];
        continue;
      }
      mapping[clean] = "ignore";
    }
    return mapping;
  }

  function loadImportSample() {
    const headers = parseCsvLines(IMPORT_SAMPLE)[0] || [];
    state.wizard.text = IMPORT_SAMPLE;
    state.wizard.mapping = autoMapping(headers);
    state.wizard.step = 2;
    state.wizard.fileName = "payroll-2026-11-sample.csv";
    state.wizard.error = null;
    renderOverlayRoot();
  }

  function mappingOptions(selected) {
    const groups = [
      { label: "忽略", items: [{ value: "ignore", label: "忽略此列" }] },
      { label: "标识", items: Data.IMPORT_COLUMNS.filter((c) => ["employee_no", "employee_name"].includes(c.key)).map((c) => ({ value: c.key, label: c.header })) },
      { label: "薪资自有列", items: Data.IMPORT_COLUMNS.filter((c) => !["employee_no", "employee_name"].includes(c.key)).map((c) => ({ value: c.key, label: c.header })) },
      { label: "考勤自有列（识别但不生效）", items: Object.entries(Data.ATTENDANCE_COLUMN_ALIASES).map(([label, key]) => ({ value: key, label })) },
    ];
    return groups.map((group) => `<optgroup label="${group.label}">${group.items.map((item) => `<option value="${item.value}" ${selected === item.value ? "selected" : ""}>${item.label}</option>`).join("")}</optgroup>`).join("");
  }

  function renderImportWizardOverlay() {
    const wiz = state.wizard;
    const month = currentMonth();
    if (!wiz) return "";
    const headers = parseCsvLines(wiz.text)[0] || [];
    const dataRows = parseCsvLines(wiz.text).slice(1);
    const steps = [
      { n: 1, label: "上传 / 粘贴" },
      { n: 2, label: "列映射" },
      { n: 3, label: "预览校验" },
    ];
    const stepBar = `<div class="wizard-steps">${steps.map((s) => `<div class="wizard-step ${wiz.step === s.n ? "active" : ""} ${wiz.step > s.n ? "done" : ""}"><span class="wizard-dot">${wiz.step > s.n ? icon("check") : s.n}</span><span>${s.label}</span></div>`).join("")}</div>`;
    let body = "";
    let foot = "";
    if (wiz.step === 1) {
      body = `
        <div class="notice info">${icon("info")}<div>导入月份 <strong>${monthLabel(month.key)}</strong>；提交后输入版本从 v${month.inputVersion} 升至 v${month.inputVersion + 1}。当前考勤月${month.attendance.locked ? `已锁定（v${month.attendance.version}）` : "未锁定"}。</div></div>
        <div class="upload-zone">
          <div class="upload-icon">${icon("upload")}</div>
          <strong>拖入 CSV，或选择文件</strong>
          <p>首行为列名；仅支持 CSV。原型不解析真实文件字节，选择文件只会记录文件名。</p>
          <input type="file" accept=".csv,text/csv" data-input="import-file" class="file-input">
          <div class="inline"><button class="btn btn-outline btn-sm" data-action="load-import-sample">${icon("file")} 载入示例文件</button><span class="sub">示例含未知员工、重复行、姓名不一致、缺失员工与考勤列。</span></div>
        </div>
        <div class="field full"><label>或直接粘贴 CSV</label><textarea class="input textarea" rows="8" data-input="import-csv" placeholder="工号,姓名,话费,车补,...">${esc(wiz.text)}</textarea></div>
        ${wiz.error ? notice("danger", esc(wiz.error)) : ""}`;
      foot = `<button class="btn btn-ghost btn-sm" data-action="close-overlay">取消</button><span class="spacer"></span><button class="btn btn-primary btn-sm" data-action="wizard-next" ${wiz.text.trim() ? "" : "disabled"}>下一步 · 列映射</button>`;
    } else if (wiz.step === 2) {
      const mappedPayroll = Object.entries(wiz.mapping).filter(([, v]) => Data.PAYROLL_IMPORT_FIELDS.includes(v));
      const attendanceMapped = Object.entries(wiz.mapping).filter(([, v]) => Data.ATTENDANCE_FIELDS.includes(v));
      const employeeMapped = Object.values(wiz.mapping).includes("employee_no");
      const duplicateTargets = Object.values(wiz.mapping).filter((v) => v !== "ignore" && v !== "employee_name" && !Data.ATTENDANCE_FIELDS.includes(v));
      const duplicates = duplicateTargets.filter((v, i, arr) => arr.indexOf(v) !== i);
      body = `
        <div class="notice info">${icon("info")}<div>文件共 <strong>${dataRows.length}</strong> 行数据、<strong>${headers.length}</strong> 列。考勤自有列可以映射，但提交时不会生效。</div></div>
        <div class="table-wrap">
          <table class="table mapping-table">
            <thead><tr><th>文件列</th><th>示例值</th><th>映射到</th><th>说明</th></tr></thead>
            <tbody>
              ${headers.map((header, i) => {
                const target = wiz.mapping[header] || "ignore";
                const isAttendance = Data.ATTENDANCE_FIELDS.includes(target);
                const isEmployee = ["employee_no", "employee_name"].includes(target);
                const sample = dataRows[0]?.[i] || "";
                return `<tr>
                  <td class="nowrap"><span class="name">${esc(header)}</span></td>
                  <td class="nowrap sub">${esc(sample)}</td>
                  <td><select class="select" data-select="mapping" data-column="${esc(header)}">${mappingOptions(target)}</select></td>
                  <td class="sub">${isAttendance ? "考勤自有列：仅识别，值不生效" : isEmployee ? "员工标识 / 参考" : target === "ignore" ? "忽略" : "薪资自有列：参与覆盖式刷新"}</td>
                </tr>`;
              }).join("")}
            </tbody>
          </table>
        </div>
        ${employeeMapped ? "" : notice("danger", "必须把「工号」映射到员工标识。")}
        ${duplicates.length ? notice("danger", `同一系统字段被映射了多次：${duplicates.join("、")}`) : ""}
        ${attendanceMapped.length ? notice("warn", `文件中的 ${attendanceMapped.map(([h]) => esc(h)).join("、")} 是考勤自有列；预览会显示忽略原因，不会覆盖考勤来源。`) : ""}
        ${wiz.error ? notice("danger", esc(wiz.error)) : ""}`;
      foot = `<button class="btn btn-ghost btn-sm" data-action="wizard-back">上一步</button><span class="spacer"></span><button class="btn btn-primary btn-sm" data-action="wizard-next" ${employeeMapped && mappedPayroll.length && !duplicates.length ? "" : "disabled"}>下一步 · 预览校验</button>`;
    } else {
      if (!wiz.preview) buildImportPreview();
      const preview = wiz.preview;
      const blocking = preview.counts.errors > 0 && !wiz.cleaned;
      body = `
        <div class="preview-summary">
          <span class="badge badge-gray">文件 ${preview.counts.total} 行</span>
          <span class="badge badge-green">有效 ${preview.counts.valid} 行</span>
          <span class="badge badge-red">错误 ${preview.counts.errors}</span>
          <span class="badge badge-orange">警告 ${preview.counts.warnings}</span>
          <span class="badge badge-gray">将清零 ${preview.counts.zeroed} 人</span>
          <span class="badge badge-orange">覆盖手工值 ${preview.counts.manual}</span>
        </div>
        <div class="source-legend">
          <span><i class="dot attendance"></i>考勤拉取（只读）</span>
          <span><i class="dot file"></i>文件写入</span>
          <span><i class="dot manual"></i>覆盖手工值</span>
          <span><i class="dot zero"></i>缺失将清零</span>
          <span><i class="dot error"></i>错误行</span>
        </div>
        <div class="table-wrap preview-table-wrap">
          <table class="table preview-table">
            <thead><tr><th>行</th><th>工号</th><th>姓名</th><th>工作日出勤</th><th>周末出勤</th><th class="num">话费</th><th class="num">生产奖</th><th class="num">本期社保</th><th class="num">本期个税</th><th>状态</th></tr></thead>
            <tbody>
              ${preview.rows.map((row) => `<tr class="${row.status === "error" ? "row-error" : row.status === "ignored" ? "row-muted" : ""}">
                <td>${row.line}</td>
                <td class="nowrap">${esc(row.employeeNo || "—")}</td>
                <td class="nowrap">${esc(row.employeeName || "—")}</td>
                <td class="src-cell src-attendance">${row.values.weekday_attended != null ? num(row.values.weekday_attended, 1) : "—"}</td>
                <td class="src-cell src-attendance">${row.values.weekend_attended != null ? num(row.values.weekend_attended, 1) : "—"}</td>
                <td class="num src-cell src-${row.sources.phone_allowance || "none"}">${row.values.phone_allowance != null ? moneyPlain(row.values.phone_allowance) : "—"}</td>
                <td class="num src-cell src-${row.sources.production_bonus || "none"}">${row.values.production_bonus != null ? moneyPlain(row.values.production_bonus) : "—"}</td>
                <td class="num src-cell src-${row.sources.social_this || "none"}">${row.values.social_this != null ? moneyPlain(row.values.social_this) : "—"}</td>
                <td class="num src-cell src-${row.sources.tax || "none"}">${row.values.tax != null ? moneyPlain(row.values.tax) : "—"}</td>
                <td><span class="badge ${row.status === "error" ? "badge-red" : row.status === "ignored" ? "badge-gray" : row.status === "zeroed" || row.status === "warning" ? "badge-orange" : "badge-green"}">${row.statusLabel}</span></td>
              </tr>`).join("")}
            </tbody>
          </table>
        </div>
        ${preview.messages.length ? `<div class="section-title">错误与警告</div><div class="preview-messages">${preview.messages.map((msg) => `<div class="preview-message ${msg.severity}">${icon(msg.severity === "error" ? "x-circle" : "alert")}<span class="msg-row">第 ${msg.line} 行</span><span class="msg-col">${esc(msg.column || "—")}</span><code>${esc(msg.code)}</code><span>${esc(msg.message)}</span></div>`).join("")}</div>` : ""}
        ${blocking ? notice("danger", "存在阻断错误，不能提交。可以逐条返回修改，或仅保留有效行后提交（原型演示）。") : ""}
        ${wiz.cleaned ? notice("warn", "已移除错误行；缺失员工仍会按覆盖式刷新清零。") : ""}`;
      foot = `<button class="btn btn-ghost btn-sm" data-action="wizard-back">上一步</button>
        ${preview.counts.errors > 0 && !wiz.cleaned ? `<button class="btn btn-outline btn-sm" data-action="clean-import-preview">${icon("trash")} 仅保留有效行</button>` : ""}
        <span class="spacer"></span>
        <button class="btn btn-primary btn-sm" data-action="commit-import" ${blocking || preview.counts.valid === 0 ? "disabled" : ""}>${icon("check")} 提交导入</button>`;
    }
    return modal({
      title: "月度导入",
      sub: `${monthLabel(month.key)} · 上传 / 映射 / 预览 / 提交`,
      body: `${stepBar}${body}`,
      foot,
      size: "lg",
      key: `import-${wiz.step}`,
    });
  }

  function buildImportPreview() {
    const wiz = state.wizard;
    const month = currentMonth();
    const lines = parseCsvLines(wiz.text);
    const headers = lines[0] || [];
    const dataRows = lines.slice(1);
    const mapping = wiz.mapping;
    const payrollTargets = new Set(Object.values(mapping).filter((v) => Data.PAYROLL_IMPORT_FIELDS.includes(v)));
    const attendanceTargets = Object.values(mapping).filter((v) => Data.ATTENDANCE_FIELDS.includes(v));
    const employeeNoIndex = headers.findIndex((h) => mapping[h] === "employee_no");
    const employeeNameIndex = headers.findIndex((h) => mapping[h] === "employee_name");
    const scope = employeeScope(month);
    const scopeIds = new Set(scope.map((e) => e.id));
    const seen = new Set();
    const rows = [];
    const messages = [];
    const counts = { total: dataRows.length, valid: 0, errors: 0, warnings: 0, zeroed: 0, manual: 0 };
    const addMessage = (line, column, code, severity, message) => messages.push({ line, column, code, severity, message });
    if (attendanceTargets.length) {
      addMessage("—", "考勤列", "attendance_column_ignored", "warning", `文件中的 ${attendanceTargets.length} 个考勤自有列已忽略；实际值来自考勤锁定月 v${month.attendance.version}，预览中的蓝色列为服务端拉取值。`);
    }
    dataRows.forEach((cells, index) => {
      const line = index + 2;
      const employeeNo = employeeNoIndex >= 0 ? (cells[employeeNoIndex] || "").trim() : "";
      const nameFromFile = employeeNameIndex >= 0 ? (cells[employeeNameIndex] || "").trim() : "";
      const employee = scope.find((e) => e.no === employeeNo) || db.employees.find((e) => e.no === employeeNo);
      const warnings = [];
      let status = "ok";
      let statusLabel = "可提交";
      const values = {};
      const sources = {};
      if (!employeeNo) {
        status = "error"; statusLabel = "缺少工号";
        addMessage(line, "工号", "missing_employee_no", "error", "该行没有工号，无法匹配员工。");
      } else if (!employee) {
        status = "error"; statusLabel = "未知员工";
        addMessage(line, "工号", "unknown_employee", "error", `工号 ${employeeNo} 不存在。`);
      } else if (!scopeIds.has(employee.id)) {
        status = "ignored"; statusLabel = "范围外忽略";
        addMessage(line, "工号", "out_of_scope", "warning", `${employee.name}（${employeeNo}）不在本月在册范围，已忽略。`);
      } else if (seen.has(employee.id)) {
        status = "error"; statusLabel = "重复行";
        addMessage(line, "工号", "duplicate_employee", "error", `工号 ${employeeNo} 在本文件中重复出现。`);
      } else {
        seen.add(employee.id);
        if (nameFromFile && nameFromFile !== employee.name) {
          warnings.push(`name_mismatch`);
          addMessage(line, "姓名", "name_mismatch", "warning", `工号匹配但姓名不一致：源=${nameFromFile}，系统=${employee.name}；以工号为准。`);
        }
        for (const header of headers) {
          const target = mapping[header];
          if (!Data.PAYROLL_IMPORT_FIELDS.includes(target)) continue;
          const raw = (cells[headers.indexOf(header)] || "").trim();
          const value = raw === "" ? 0 : Number(raw);
          if (!Number.isFinite(value)) {
            status = "error"; statusLabel = "数值错误";
            addMessage(line, header, "invalid_number", "error", `「${header}」不是有效数字：${raw}`);
            continue;
          }
          values[target] = value;
          const manualFields = month.manualValues[employee.id]?.fields || [];
          if (manualFields.includes(fieldSourceKey(target))) {
            sources[target] = "manual";
            counts.manual += 1;
            warnings.push("manual_overwrite");
            addMessage(line, header, "manual_overwrite", "warning", `将覆盖 ${employee.name} 的手工值（${fieldLabel(target)}）。`);
          } else {
            sources[target] = "file";
          }
        }
        // Attendance values are always displayed from the locked month.
        const input = month.inputs[employee.id] || {};
        values.weekday_attended = input.weekday_attended;
        values.weekend_attended = input.weekend_attended;
      }
      if (status === "error") counts.errors += 1;
      else if (status === "ignored") counts.warnings += 1;
      else counts.valid += 1;
      if (status === "ok" && warnings.length) { status = "warning"; statusLabel = "可提交（有警告）"; }
      rows.push({
        line, employeeNo, employeeName: employee?.name || nameFromFile || "", employeeId: employee?.id || null,
        status, statusLabel, values, sources, messages: warnings,
      });
    });
    // In-scope employees missing from the file: the present columns are zeroed.
    for (const emp of scope) {
      if (seen.has(emp.id)) continue;
      const values = {};
      const sources = {};
      for (const target of payrollTargets) { values[target] = 0; sources[target] = "zero"; }
      const input = month.inputs[emp.id] || {};
      values.weekday_attended = input.weekday_attended;
      values.weekend_attended = input.weekend_attended;
      counts.zeroed += 1;
      counts.valid += 1;
      addMessage("—", "全范围", "missing_employee_zeroed", "warning", `${emp.name}（${emp.no}）不在文件中，出现的 ${payrollTargets.size} 个薪资列将按 0 写入。`);
      rows.push({
        line: "—", employeeNo: emp.no, employeeName: emp.name, employeeId: emp.id,
        status: "zeroed", statusLabel: "缺失将清零", values, sources, messages: ["missing_employee_zeroed"],
      });
    }
    counts.warnings = messages.filter((m) => m.severity === "warning").length;
    wiz.preview = { rows, messages, counts, payrollTargets: [...payrollTargets], attendanceTargets };
    return wiz.preview;
  }

  function fieldLabel(fieldKey) {
    return db.fieldDefs.find((f) => f.field_key === fieldKey)?.label || fieldKey;
  }

  function fieldSourceKey(fieldKey) {
    const field = db.fieldDefs.find((f) => f.field_key === fieldKey);
    return field?.source_key || fieldKey;
  }

  function cleanImportPreview() {
    const preview = state.wizard.preview;
    preview.rows = preview.rows.filter((row) => row.status !== "error");
    preview.counts.errors = 0;
    preview.counts.valid = preview.rows.filter((row) => ["ok", "warning", "zeroed"].includes(row.status)).length;
    preview.counts.zeroed = preview.rows.filter((row) => row.status === "zeroed").length;
    preview.messages = preview.messages.filter((msg) => msg.code !== "unknown_employee" && msg.code !== "duplicate_employee" && msg.code !== "missing_employee_no" && msg.code !== "invalid_number");
    preview.counts.warnings = preview.messages.filter((msg) => msg.severity === "warning").length;
    state.wizard.cleaned = true;
    renderOverlayRoot();
  }

  function commitImport() {
    const wiz = state.wizard;
    const month = currentMonth();
    const preview = wiz.preview;
    if (!preview) return;
    if (preview.counts.errors > 0 && !wiz.cleaned) {
      showToast("存在阻断错误，不能提交", "error");
      return;
    }
    let overwrittenManual = 0;
    for (const row of preview.rows) {
      if (!row.employeeId) continue;
      if (row.status === "error" || row.status === "ignored") continue;
      const input = month.inputs[row.employeeId] || {};
      for (const target of preview.payrollTargets) {
        if (!(target in row.values)) continue;
        input[fieldSourceKey(target)] = row.values[target];
        if (row.sources[target] === "manual") {
          overwrittenManual += 1;
          const manual = month.manualValues[row.employeeId];
          if (manual) {
            manual.fields = (manual.fields || []).filter((field) => field !== fieldSourceKey(target));
            if (!manual.fields.length) delete month.manualValues[row.employeeId];
          }
        }
      }
      month.inputs[row.employeeId] = input;
    }
    month.inputVersion += 1;
    const batchId = `B-${month.key.replace("-", "")}-${String(month.batches.length + 1).padStart(2, "0")}`;
    for (const batch of month.batches) if (batch.status === "committed") batch.status = "superseded";
    month.batches.push({
      id: batchId,
      source: "file",
      fileName: wiz.fileName || `payroll-${month.key}.csv`,
      status: "committed",
      rows: preview.rows.filter((r) => ["ok", "warning", "zeroed"].includes(r.status)).length,
      columns: preview.payrollTargets.length,
      committedAt: "2026-11-28 09:25",
      inputVersion: month.inputVersion,
      note: `覆盖式刷新；${overwrittenManual} 个手工值被覆盖；${preview.counts.zeroed} 人清零`,
    });
    month.events.push({ at: "2026-11-28 09:25", type: "input", label: `导入提交 · ${batchId}`, by: "管理员", reason: "" });
    state.wizard = null;
    closeOverlay();
    render();
    showToast(`批次 ${batchId} 已提交，输入版本升至 v${month.inputVersion}；请重新核算`);
  }

  /* ---------------------------------------------------------------- calculation & lifecycle */

  function canPay(month) {
    if (!month || month.state !== "confirmed") return false;
    const flags = H.monthFlags(db, month);
    return Boolean(flags.success) && !flags.inputChanged && !flags.attendanceStale && !flags.scopeStale && !flags.lastFailed;
  }

  function renderGateList(gates, mode = "calc") {
    return `<div class="gate-list">
      ${gates.map((gate) => `<div class="gate-row ${gate.status}">
        ${gateStatusIcon(gate.status)}
        <div class="gate-text"><strong>${esc(gate.label)}</strong><span>${esc(gate.detail)}</span></div>
        <span class="badge ${gate.status === "pass" ? "badge-green" : gate.status === "fail" ? "badge-red" : gate.status === "warn" ? "badge-orange" : "badge-gray"}">${gate.status === "pass" ? "通过" : gate.status === "fail" ? "阻断" : gate.status === "warn" ? "警告" : "信息"}</span>
      </div>`).join("")}
    </div>`;
  }

  function renderCalcBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const month = currentMonth();
    if (!month) return emptyState({ title: "暂无薪资月", desc: "请先创建薪资月。", iconName: "calendar" });
    const flags = H.monthFlags(db, month);
    const gates = calcGates(month);
    const success = flags.success;
    const checks = success
      ? [
          { key: "normal_pay", label: "normal_pay = ROUND(Σ 计薪项, 2)" },
          { key: "addon_sum", label: "addon_sum = ROUND(Σ 加减项, 2)" },
          { key: "gross", label: "gross = ROUND(normal_pay + addon_sum, 2)" },
          { key: "deduct_sum", label: "deduct_sum = ROUND(Σ 代扣项, 2)" },
          { key: "net", label: "net = ROUND(gross + deduct_sum, 2)" },
        ].map((check) => {
          const rows = H.monthResults(db, month)?.results || [];
          const results = rows.flatMap((row) => H.consistencyChecks(row));
          const subset = results.filter((r) => r.key === check.key);
          const passed = subset.filter((r) => r.pass).length;
          return { ...check, passed, total: subset.length };
        })
      : [];
    const primary = month.state === "calculated"
      ? `<button class="btn btn-primary" data-action="open-confirm" ${canConfirm(month) ? "" : "disabled"}>${icon("check-circle")} 确认工资表</button>`
      : month.state === "confirmed"
        ? `<button class="btn btn-primary" data-action="open-pay" ${canPay(month) ? "" : "disabled"}>${icon("file")} 发工资条</button>`
        : month.state === "paid"
          ? `<button class="btn btn-outline" data-action="open-unlock">${icon("unlock")} 解锁已发月</button>`
          : canCalculate(month)
            ? `<button class="btn btn-primary" data-action="open-calculate">${state.calcRunning ? `${icon("refresh", "spin")} 核算中…` : `${icon("play")} 开始核算`}</button>`
            : "";
    return `
      <div class="calc-hero">
        <div>
          <div class="calc-state">${stateBadge(month)} <span class="calc-state-label">${STATE_META[month.state].label}</span></div>
          <h2>${monthLabel(month.key)} · ${currentCompany().name}</h2>
          <p>${month.state === "draft" ? "草稿月：先完成导入与考勤月结，再开始核算。" : month.state === "calculated" ? "已核算：结果可查看、可重算；确认前请核对门槛。" : month.state === "confirmed" ? "已确认：结果锁定；发放后生成正式快照。" : "已发：结果与输入锁定；解锁需理由并保留快照。"}</p>
          <div class="calc-flags">${flagsBadges(month)}</div>
        </div>
        <div class="calc-actions">${primary}${month.state === "calculated" ? `<button class="btn btn-outline" data-action="calculate" ${canCalculate(month) ? "" : "disabled"}>${icon("refresh")} 重新核算</button>` : ""}${month.state === "confirmed" ? `<button class="btn btn-outline" data-action="open-unconfirm">${icon("rotate-ccw")} 取消确认</button>` : ""}${month.state === "paid" ? `<button class="btn btn-outline" data-action="go-page" data-page="payslips">${icon("file")} 查看工资条</button>` : ""}</div>
      </div>
      ${flags.lastFailed ? notice("danger", `最近一次核算失败：<strong>${esc(H.lastRun(db, month)?.error || "未知错误")}</strong>。失败批次不写入结果，当前结果仍来自 ${success ? success.id : "更早批次"}。`) : ""}
      ${flags.needsRecalc ? notice("warn", "当前结果已过期（输入、考勤或范围变化）。确认与发放被阻断；请重新核算。") : ""}
      <div class="calc-grid">
        <div class="card">
          <div class="card-head"><div><h3>${icon("check-circle")} 核算前检查</h3><span class="sub">硬门槛失败则整批不写入结果</span></div><span class="badge ${gates.some((g) => g.status === "fail") ? "badge-red" : "badge-green"}">${gates.filter((g) => g.status === "fail").length} 项阻断</span></div>
          <div class="card-body">${renderGateList(gates)}</div>
        </div>
        <div class="card">
          <div class="card-head"><div><h3>${icon("zap")} 生命周期</h3><span class="sub">draft → calculated → confirmed → paid</span></div></div>
          <div class="card-body">
            <div class="lifecycle">
              ${["draft", "calculated", "confirmed", "paid"].map((key, i) => `<div class="life-step ${month.state === key ? "current" : ""} ${["draft", "calculated", "confirmed", "paid"].indexOf(month.state) > i ? "done" : ""}"><span class="life-dot">${["draft", "calculated", "confirmed", "paid"].indexOf(month.state) > i ? icon("check") : i + 1}</span><strong>${STATE_META[key].label}</strong></div>`).join("")}
            </div>
            <div class="notice info">${icon("info")}<div>${H.monthClass(db, month.key) === "current" ? "当前薪资月：重算采用最新配置。" : "历史薪资月：重算沿用最近成功批次配置快照。"}</div></div>
            <div class="demo-box">
              <div class="demo-head">${icon("sliders")} 演示状态</div>
              <div class="demo-actions">
                <button class="btn btn-outline btn-sm" data-action="toggle-attendance-stale" ${month.state === "paid" ? "disabled" : ""}>${icon("clock")} ${month.attendance.status === "stale" ? "恢复考勤锁定" : "模拟考勤解锁"}</button>
                <button class="btn btn-outline btn-sm" data-action="toggle-scope-stale" ${month.state === "paid" ? "disabled" : ""}>${icon("users")} ${month.scopeStale ? "恢复范围一致" : "模拟范围变化"}</button>
              </div>
              <p class="sub">用于检查「待重算 / 考勤过期 / 范围变化」横幅与确认门槛；已发月不参与。</p>
            </div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-head"><div><h3>${icon("history")} 核算批次</h3><span class="sub">每次尝试都留痕；成功批次快照配置、输入与考勤来源</span></div><span class="badge badge-gray">${month.runs.length} 个批次</span></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>批次</th><th>触发</th><th>状态</th><th>开始时间</th><th class="num">耗时</th><th>配置快照</th><th>输入</th><th>考勤</th><th class="num">人数</th><th class="num">应发</th><th class="num">实发</th><th>操作</th></tr></thead>
            <tbody>
              ${month.runs.length ? [...month.runs].reverse().map((run) => `<tr class="clickable" data-action="open-run" data-run="${run.id}">
                <td class="nowrap"><span class="name">${esc(run.id)}</span></td>
                <td>${{ manual: "手动", recalc: "重算", import: "导入后" }[run.trigger] || esc(run.trigger)}</td>
                <td><span class="badge ${run.status === "success" ? "badge-green" : "badge-red"}">${run.status === "success" ? "成功" : "失败"}</span></td>
                <td class="nowrap">${esc(run.startedAt)}</td>
                <td class="num">${num(run.durationMs / 1000, 1)}s</td>
                <td class="sub">引擎 ${esc(run.configSnapshot.engineVersion)}</td>
                <td>v${run.inputVersion}</td>
                <td>v${run.attendanceVersion}</td>
                <td class="num">${run.employeeCount}</td>
                <td class="num">${run.totals ? money(run.totals.gross) : "—"}</td>
                <td class="num">${run.totals ? money(run.totals.net) : "—"}</td>
                <td><button class="btn btn-ghost btn-sm" data-action="open-run" data-run="${run.id}">${icon("eye")} 详情</button></td>
              </tr>`).join("") : `<tr><td colspan="12" class="table-empty-cell">本月尚无核算批次。</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
      <div class="calc-grid">
        <div class="card">
          <div class="card-head"><div><h3>${icon("shield")} 一致性校验</h3><span class="sub">按字段类别锚定；任一员工失败则整批失败</span></div><span class="badge ${checks.every((c) => c.passed === c.total) ? "badge-green" : "badge-red"}">${checks.length ? `${checks.filter((c) => c.passed === c.total).length}/${checks.length} 通过` : "尚无结果"}</span></div>
          <div class="card-body">
            ${checks.length ? `<div class="check-list">${checks.map((check) => `<div class="check-row ${check.passed === check.total ? "pass" : "fail"}">${check.passed === check.total ? icon("check-circle") : icon("x-circle")}<span>${esc(check.label)}</span><span class="spacer"></span><span class="sub">${check.passed}/${check.total} 员工</span></div>`).join("")}</div>` : `<div class="table-empty-cell">成功核算后显示校验结果。</div>`}
          </div>
        </div>
        <div class="card">
          <div class="card-head"><div><h3>${icon("clock")} 月份事件</h3><span class="sub">确认 / 取消确认 / 发放 / 解锁均留痕</span></div></div>
          <div class="card-body">
            <div class="timeline">
              ${[...month.events].reverse().map((event) => `<div class="timeline-item"><span class="timeline-dot ${event.type}"></span><div><strong>${esc(event.label)}</strong><span class="sub">${esc(event.at)} · ${esc(event.by)}${event.reason ? ` · ${esc(event.reason)}` : ""}</span></div></div>`).join("") || `<div class="table-empty-cell">暂无事件。</div>`}
            </div>
          </div>
        </div>
      </div>`;
  }

  function startCalculation() {
    const month = currentMonth();
    if (!month) return;
    if (!canCalculate(month)) {
      openOverlay("calc-blocked");
      return;
    }
    closeOverlay();
    state.calcRunning = true;
    render();
    window.clearTimeout(calcTimer);
    calcTimer = window.setTimeout(() => {
      const computed = H.computeMonth(db, month.key);
      state.calcRunning = false;
      const seq = String(month.runs.length + 1).padStart(2, "0");
      const runId = `R-${month.key.replace("-", "")}-${seq}`;
      if (computed.errors.length) {
        const run = H.makeRunRecord(runId, month.key, month.state === "draft" ? "manual" : "recalc", "failed", "2026-11-28 09:30", "2026-11-28 09:30", 4, month.inputVersion, month.attendance.version, computed.results.length, null, "管理员", `${computed.errors.length} 名员工核算失败：${computed.errors.slice(0, 3).map((e) => `${e.employeeName}（${e.message}）`).join("；")}`);
        month.runs.push(run);
        month.events.push({ at: "2026-11-28 09:30", type: "failed", label: `核算失败 · ${runId}`, by: "管理员", reason: run.error });
        render();
        showToast("核算失败，未写入结果；请查看批次错误", "error");
        return;
      }
      const run = H.makeRunRecord(runId, month.key, month.state === "draft" ? "manual" : "recalc", "success", "2026-11-28 09:30", "2026-11-28 09:31", 6, month.inputVersion, month.attendance.version, computed.results.length, computed.totals, "管理员", null);
      month.results = computed.results;
      month.runs.push(run);
      month.lastRunId = run.id;
      month.state = "calculated";
      month.attendance.status = "fresh";
      month.attendance.pulledAt = "2026-11-28 09:30";
      month.configStale = false;
      month.scopeStale = false;
      month.events.push({ at: "2026-11-28 09:31", type: "calculated", label: `核算成功 · ${runId}`, by: "管理员", reason: "" });
      render();
      showToast(`核算成功：${computed.results.length} 人，应发 ${money(computed.totals.gross)}`);
    }, 850);
  }

  function doConfirm() {
    const month = currentMonth();
    if (!month) return;
    if (!canConfirm(month)) {
      showToast("确认门槛未满足，请查看检查项", "error");
      return;
    }
    month.state = "confirmed";
    month.events.push({ at: "2026-11-28 09:35", type: "confirmed", label: "确认工资表", by: "管理员", reason: "" });
    closeOverlay();
    render();
    showToast("工资表已确认；下一步可发工资条");
  }

  function doUnconfirm() {
    const month = currentMonth();
    if (!month || month.state !== "confirmed") return;
    month.state = "calculated";
    month.events.push({ at: "2026-11-28 09:36", type: "unconfirmed", label: "取消确认", by: "管理员", reason: "" });
    closeOverlay();
    render();
    showToast("已取消确认，可重新核算");
  }

  function doPay() {
    const month = currentMonth();
    if (!month) return;
    if (!canPay(month)) {
      showToast("发放门槛未满足，请查看检查项", "error");
      return;
    }
    const source = H.monthResults(db, month);
    const version = (month.paidSnapshot?.version || 0) + 1;
    month.state = "paid";
    month.paidSnapshot = {
      version,
      paidAt: "2026-11-28 09:40",
      by: "管理员",
      runId: month.lastRunId,
      results: H.clone(month.results),
      fieldDefs: H.clone(db.fieldDefs),
      totals: source ? H.clone(source.totals) : H.aggregateResults(month.results),
      configSummary: { engineVersion: db.engineVersion, composition: "岗位当前版本", scheme: "岗位计算方案", workday: "岗位工作日参数" },
      attendanceVersion: month.attendance.version,
      inputVersion: month.inputVersion,
    };
    month.events.push({ at: "2026-11-28 09:40", type: "paid", label: `标记已发 · 快照 v${version}`, by: "管理员", reason: "" });
    closeOverlay();
    goPage("payslips");
    showToast(`已标记发放并生成正式快照 v${version}`);
  }

  function doUnlock(reason) {
    const month = currentMonth();
    if (!month || month.state !== "paid") return;
    if (!reason || reason.trim().length < 2) {
      showToast("解锁必须填写理由", "error");
      return;
    }
    month.state = "confirmed";
    month.events.push({ at: "2026-11-28 09:42", type: "unlocked", label: "解锁已发月", by: "管理员", reason: reason.trim() });
    closeOverlay();
    render();
    showToast(`已解锁，保留已发快照 v${month.paidSnapshot?.version || 1}；可取消确认后重新核算`);
  }

  function toggleAttendanceStale() {
    const month = currentMonth();
    if (!month || month.state === "paid") return;
    month.attendance.status = month.attendance.status === "stale" ? "fresh" : "stale";
    month.attendance.version += month.attendance.status === "stale" ? 1 : 0;
    render();
    showToast(month.attendance.status === "stale" ? "已模拟考勤解锁：结果标记待重算，确认与发放阻断" : "已恢复考勤锁定快照");
  }

  function toggleScopeStale() {
    const month = currentMonth();
    if (!month || month.state === "paid") return;
    month.scopeStale = !month.scopeStale;
    render();
    showToast(month.scopeStale ? "已模拟员工范围变化：确认与发放阻断" : "已恢复范围一致");
  }

  function renderCalcBlockedOverlay() {
    const month = currentMonth();
    const gates = calcGates(month).filter((g) => g.status === "fail");
    return modal({
      title: "核算前检查未通过",
      sub: `${monthLabel(month.key)} · 失败批次不会写入结果`,
      body: `${notice("danger", "以下硬门槛阻断核算：")}${renderGateList(gates)}${gates.some((g) => g.key === "attendance_locked" || g.key === "summary") ? `<div class="notice info">${icon("info")}<div>考勤未锁定或缺汇总：请到「考勤管理」完成月结后，再回本页刷新考勤来源。</div></div>` : ""}${gates.some((g) => g.key === "assembly") ? `<div class="notice info">${icon("info")}<div>岗位未装配：到「岗位装配」补齐薪资构成、计算方案与工作日参数。</div></div>` : ""}`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">返回</button>${gates.some((g) => g.key === "assembly") ? `<button class="btn btn-primary btn-sm" data-action="nav" data-page="assembly">${icon("briefcase")} 去岗位装配</button>` : ""}`,
      size: "lg",
      key: "calc-blocked",
    });
  }

  function renderConfirmOverlay() {
    const month = currentMonth();
    const gates = calcGates(month, "confirm");
    return modal({
      title: "确认工资表",
      sub: `${monthLabel(month.key)} · 确认后结果锁定；发放前可取消确认`,
      body: `${renderGateList(gates)}${notice("info", "确认要求：最近批次成功、输入版本未变、考勤新鲜、范围未变。配置已更新只警告，不阻断。")}`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="do-confirm" ${canConfirm(month) ? "" : "disabled"}>${icon("check-circle")} 确认工资表</button>`,
      size: "lg",
      key: "confirm",
    });
  }

  function renderPayOverlay() {
    const month = currentMonth();
    const gates = calcGates(month, "confirm");
    return modal({
      title: "发工资条 / 标记已发",
      sub: `${monthLabel(month.key)} · 发放会追加一版自包含已发快照`,
      body: `${renderGateList(gates)}${notice("warn", "发放后输入与结果锁定；工资条读取该快照。解锁需理由，已发版本保留，重付追加新版本。")}`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="do-pay" ${canPay(month) ? "" : "disabled"}>${icon("file")} 标记已发</button>`,
      size: "lg",
      key: "pay",
    });
  }

  function renderUnlockOverlay() {
    const month = currentMonth();
    return modal({
      title: "解锁已发月",
      sub: `${monthLabel(month.key)} · 已发快照 v${month.paidSnapshot?.version || 1} 保留`,
      body: `<div class="field full"><label>解锁理由 <span class="req">*</span></label><textarea class="input textarea" rows="4" data-input="unlock-reason" placeholder="例如：9 月个税导入错误，需取消确认后重算并重付"></textarea><span class="hint">解锁后月份回到「已确认」；结果与已发快照不被改写。重算前需先取消确认。</span></div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-danger btn-sm" data-action="do-unlock">${icon("unlock")} 确认解锁</button>`,
      size: "sm",
      key: "unlock",
    });
  }

  function renderRunDetailOverlay(overlay) {
    const month = currentMonth();
    const run = [...month.runs, ...db.runs].find((r) => r.id === overlay.runId);
    if (!run) return modal({ title: "核算批次", body: notice("warn", "批次不存在。") });
    return sheet({
      title: `核算批次 ${run.id}`,
      sub: `${monthLabel(run.monthKey)} · ${run.status === "success" ? "成功" : "失败"} · ${esc(run.startedAt)}`,
      body: `
        <div class="stat-grid compact">
          ${kpi("人数", run.employeeCount)}
          ${kpi("应发", run.totals ? money(run.totals.gross) : "—")}
          ${kpi("实发", run.totals ? money(run.totals.net) : "—")}
          ${kpi("耗时", `${num(run.durationMs / 1000, 1)}s`)}
        </div>
        ${run.error ? notice("danger", esc(run.error)) : ""}
        <div class="section-title">冻结上下文</div>
        <div class="snapshot-grid">
          <div><span class="sub">触发</span><strong>${{ manual: "手动", recalc: "重新核算", import: "导入后" }[run.trigger] || esc(run.trigger)}</strong></div>
          <div><span class="sub">算子</span><strong>${esc(run.operator)}</strong></div>
          <div><span class="sub">输入版本</span><strong>v${run.inputVersion}</strong></div>
          <div><span class="sub">考勤快照</span><strong>v${run.attendanceVersion}</strong></div>
          <div><span class="sub">配置快照</span><strong>${esc(run.configSnapshot.engineVersion)}</strong></div>
          <div><span class="sub">字段定义</span><strong>${esc(run.configSnapshot.fieldDefs)}</strong></div>
        </div>
        <div class="section-title">配置快照内容</div>
        <div class="mini-table-wrap"><table class="mini-table"><tbody>
          <tr><th>薪资构成</th><td>${esc(run.configSnapshot.compositions)}</td></tr>
          <tr><th>计算方案</th><td>${esc(run.configSnapshot.schemes)}</td></tr>
          <tr><th>工作日参数</th><td>${esc(run.configSnapshot.workday)}</td></tr>
          <tr><th>输入快照</th><td>${esc(run.inputSnapshot)}</td></tr>
          <tr><th>考勤来源</th><td>${esc(run.attendanceSnapshot)}</td></tr>
        </tbody></table></div>
        ${run.totals ? `<div class="section-title">聚合汇总</div><div class="snapshot-grid"><div><span class="sub">正常出勤工资</span><strong>${money(run.totals.normal)}</strong></div><div><span class="sub">应发</span><strong>${money(run.totals.gross)}</strong></div><div><span class="sub">社保</span><strong>${money(run.totals.social)}</strong></div><div><span class="sub">个税</span><strong>${money(run.totals.tax)}</strong></div><div><span class="sub">实发</span><strong>${money(run.totals.net)}</strong></div></div>` : ""}
        <div class="notice info">${icon("info")}<div>失败批次不写结果；成功批次只保留聚合与快照，逐人值会被下一次成功批次覆盖（已发快照除外）。</div></div>`,
      foot: `<span class="spacer"></span><button class="btn btn-outline btn-sm" data-action="close-overlay">关闭</button>`,
      key: `run-${run.id}`,
    });
  }

  /* ---------------------------------------------------------------- payslips */

  function payslipMode(month) {
    if (!month) return "none";
    if (month.state === "paid") return "official";
    if (month.state === "calculated" || month.state === "confirmed") return "preview";
    return "none";
  }

  function filteredPayslipResults(source) {
    if (!source) return [];
    return source.results
      .filter((row) => state.payslipFilter === "all" || deptPathIncludes(row.deptPath, state.payslipFilter))
      .sort((a, b) => a.employeeNo.localeCompare(b.employeeNo));
  }

  function renderPayslipsBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const month = currentMonth();
    if (!month) return emptyState({ title: "暂无薪资月", desc: "请先创建薪资月。", iconName: "calendar" });
    const source = H.monthResults(db, month);
    const mode = payslipMode(month);
    if (!source || mode === "none") {
      return `${notice("info", `当前月份为 <strong>${STATE_META[month.state].label}</strong>；工资条需要当前成功核算结果或已发快照。`)}
        ${emptyState({ title: "暂无可生成的工资条", desc: "先在「核算与确认」完成一次成功核算；已发月份自动切换为正式工资条。", actions: `<button class="btn btn-primary btn-sm" data-action="go-page" data-page="calc">${icon("calculator")} 去核算</button>`, iconName: "file" })}`;
    }
    const rows = filteredPayslipResults(source);
    if (!rows.some((r) => r.employeeId === state.payslipEmployeeId)) {
      state.payslipEmployeeId = rows[0]?.employeeId || source.results[0]?.employeeId;
    }
    const row = source.results.find((r) => r.employeeId === state.payslipEmployeeId) || rows[0];
    if (!row) {
      return emptyState({ title: "没有符合条件的员工", desc: "清空部门筛选后重试。", actions: `<button class="btn btn-outline btn-sm" data-action="clear-payslip-filter">清除筛选</button>`, iconName: "user" });
    }
    const defs = source.fieldDefs || db.fieldDefs;
    const flags = H.monthFlags(db, month);
    const official = mode === "official";
    const visibleFields = (category) => defs.filter((f) => f.category === category && f.visible && f.is_active !== false).sort((a, b) => a.display_order - b.display_order);
    const valueOf = (key) => row.values[key] || 0;
    const displayValue = (field) => ["deduction"].includes(field.category) ? money(Math.abs(valueOf(field.field_key))) : money(valueOf(field.field_key));
    const group = (category, title, subtotalKey, note) => {
      const fields = visibleFields(category);
      if (!fields.length) return "";
      return `<div class="payslip-group">
        <div class="payslip-group-title">${title}${note ? `<span class="sub">${note}</span>` : ""}</div>
        ${fields.map((field) => `<div class="payslip-row"><span>${esc(field.label)}</span><span class="num">${displayValue(field)}</span></div>`).join("")}
        ${subtotalKey ? `<div class="payslip-row subtotal"><span>${esc(defs.find((f) => f.field_key === subtotalKey)?.label || subtotalKey)}</span><span class="num">${money(Math.abs(valueOf(subtotalKey)))}</span></div>` : ""}
      </div>`;
    };
    const exportJobs = db.exportJobs.filter((job) => job.monthKey === month.key);
    return `
      <div class="payslip-banner ${official ? "official" : "preview"}">
        ${icon(official ? "lock" : "eye")}
        <div><strong>${official ? `正式工资条 · 已发快照 v${month.paidSnapshot.version}` : "预览工资条 · 未发放"}</strong>
        <span>${official ? "取最新已发快照；解锁或重算不会改写已发出的一版。" : `取当前成功批次 ${month.lastRunId}；页眉标注明细状态，不能作为发放凭证。`}</span></div>
        <span class="spacer"></span>
        ${flags.needsRecalc ? `<span class="badge badge-orange">待重算</span>` : ""}
        ${flags.lastFailed ? `<span class="badge badge-red">最近批次失败</span>` : ""}
        ${official ? "" : `<span class="badge badge-blue">未确认 / 未发放</span>`}
      </div>
      ${!official && flags.needsRecalc ? notice("warn", "本月结果早于最近输入 / 考勤 / 范围变化；预览会显示待重算状态，批量导出前建议先重新核算。") : ""}
      <div class="payslip-layout">
        <div class="payslip-list card">
          <div class="card-head"><div><h3>员工</h3><span class="sub">${rows.length} 人 · ${source.source === "paid" ? "已发快照" : "当前成功批次"}</span></div></div>
          <div class="payslip-filter">
            <select class="select" data-select="payslip-dept"><option value="all" ${state.payslipFilter === "all" ? "selected" : ""}>全部部门</option>${departmentOptions(state.payslipFilter).replace(/^<option value="all"[^>]*>[^<]*<\/option>/, "")}</select>
          </div>
          <div class="payslip-employees">
            ${rows.map((item) => `<button class="payslip-employee ${item.employeeId === row.employeeId ? "active" : ""}" data-action="select-payslip-employee" data-employee="${item.employeeId}">
              <span class="avatar sm">${esc(item.employeeName.slice(0, 1))}</span>
              <span class="payslip-employee-meta"><strong>${esc(item.employeeName)}</strong><span>${esc(item.employeeNo)} · ${esc(item.deptName)}</span></span>
              <span class="payslip-employee-net">${money(item.values.net)}</span>
            </button>`).join("")}
          </div>
        </div>
        <div class="payslip-wrap">
          <div class="payslip ${official ? "official" : "preview"}">
            <div class="payslip-watermark">${official ? "正式" : "预览 · 未发放"}</div>
            <div class="payslip-head">
              <div>
                <div class="payslip-company">${esc(currentCompany().name)}</div>
                <div class="payslip-title">工资条</div>
                <div class="payslip-period">${monthLabel(month.key)} · ${official ? "正式工资条" : "预览工资条（未发放）"}</div>
              </div>
              <div class="payslip-head-right">
                <div class="payslip-no">${esc(row.employeeNo)}</div>
                <div class="sub">${official ? `已发快照 v${month.paidSnapshot.version}` : `当前批次 ${month.lastRunId}`}</div>
              </div>
            </div>
            <div class="payslip-meta">
              <div><span>姓名</span><strong>${esc(row.employeeName)}</strong></div>
              <div><span>部门</span><strong>${esc(row.deptPath.map((d) => d.name).join(" / "))}</strong></div>
              <div><span>岗位</span><strong>${esc(row.positionName)}</strong></div>
              <div><span>成本归属</span><strong>${row.costPath.length ? esc(row.costPath.map((c) => c.name).join(" / ")) : "未分配"}</strong></div>
            </div>
            <div class="payslip-summary">
              <div><span>应发工资</span><strong>${money(valueOf("gross"))}</strong></div>
              <div><span>社保（代扣）</span><strong>${money(Math.abs(valueOf("social_this")))}</strong></div>
              <div><span>个税（代扣）</span><strong>${money(Math.abs(valueOf("tax")))}</strong></div>
              <div class="net"><span>实发工资</span><strong>${money(valueOf("net"))}</strong></div>
            </div>
            <div class="payslip-groups">
              ${group("earning", "计薪项", "normal_pay")}
              ${group("addon", "加减项", "addon_sum")}
              ${group("deduction", "代扣项", "deduct_sum", "本期社保 / 个税 / 已发")}
              ${group("reference", "参考项", null, "仅展示，不参与合计")}
            </div>
            <div class="payslip-foot">
              <div class="payslip-foot-grid">
                <div><span>核算批次</span><strong>${official ? month.paidSnapshot.runId : month.lastRunId}</strong></div>
                <div><span>配置</span><strong>${esc(row.config.compositionName)} v${row.config.compositionVersion} · ${esc(row.config.schemeName)}</strong></div>
                <div><span>考勤来源</span><strong>${month.key} · 锁定快照 v${official ? month.paidSnapshot.attendanceVersion : month.attendance.version}</strong></div>
                <div><span>输入版本 / 引擎</span><strong>v${official ? month.paidSnapshot.inputVersion : month.inputVersion} · ${esc(row.config.engineVersion)}</strong></div>
              </div>
              <div class="payslip-signature"><span>制表：管理员</span><span>${official ? `版本：v${month.paidSnapshot.version}` : "预览：不作为发放凭证"}</span><span>第 1 / 1 页</span></div>
            </div>
          </div>
          <div class="payslip-actions">
            <button class="btn btn-outline btn-sm" data-action="download-single-payslip">${icon("download")} 下载 PDF</button>
            <button class="btn btn-outline btn-sm" data-action="open-export">${icon("package")} 批量导出</button>
            <span class="spacer"></span>
            <span class="sub">${official ? "正式工资条为只读单据；重付追加新版本。" : "PDF 由服务端生成；预览导出会固定当前成功批次。"}</span>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-head"><div><h3>${icon("history")} 导出任务</h3><span class="sub">异步任务 + 24 小时产物；审计不存金额</span></div><span class="badge badge-gray">${exportJobs.length} 个任务</span></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>任务</th><th>类型</th><th>数据源</th><th class="num">人数</th><th>状态</th><th>进度</th><th>创建</th><th>有效期</th><th class="num">下载</th><th>操作</th></tr></thead>
            <tbody>
              ${exportJobs.length ? [...exportJobs].reverse().map((job) => `<tr>
                <td class="nowrap"><span class="name">${esc(job.id)}</span></td>
                <td>${esc(exportFormatLabel(job.format))}</td>
                <td class="sub">${esc(job.sourceLabel)}</td>
                <td class="num">${job.count}</td>
                <td><span class="badge ${job.status === "succeeded" ? "badge-green" : job.status === "failed" ? "badge-red" : job.status === "expired" ? "badge-gray" : "badge-blue"}">${exportStatusLabel(job.status)}</span></td>
                <td><div class="progress" style="width:120px"><span style="width:${job.progress}%;background:${job.status === "failed" ? "var(--danger)" : job.status === "succeeded" ? "var(--success)" : "var(--primary)"}"></span></div></td>
                <td class="nowrap sub">${esc(job.createdAt)}</td>
                <td class="nowrap sub">${esc(job.expiresAt || "—")}</td>
                <td class="num">${job.downloads || 0}</td>
                <td><button class="btn btn-ghost btn-sm" data-action="download-export" data-job="${job.id}">${icon("download")} 下载</button></td>
              </tr>`).join("") : `<tr><td colspan="10" class="table-empty-cell">尚无导出任务。</td></tr>`}
            </tbody>
          </table>
        </div>
        <div class="card-foot"><span>${icon("info")} 批量上限 1000 人；ZIP 每人一份 PDF，合并 PDF 每人一页；Excel 为扁平明细。产物过期返回 410。</span></div>
      </div>`;
  }

  function exportFormatLabel(format) {
    return { zip: "ZIP · 每人一份 PDF", merged: "合并 PDF", excel: "Excel 明细" }[format] || format;
  }

  function exportStatusLabel(status) {
    return { queued: "排队中", running: "生成中", succeeded: "可下载", failed: "失败", expired: "已过期" }[status] || status;
  }

  function renderExportOverlay() {
    const month = currentMonth();
    const source = sourceForMonth(month);
    if (!source) return modal({ title: "批量导出", body: notice("info", "当前月份尚无成功结果。") });
    const official = payslipMode(month) === "official";
    const count = filteredPayslipResults(source).length;
    return modal({
      title: "批量导出工资条",
      sub: `${monthLabel(month.key)} · ${official ? "正式工资条（已发快照）" : "预览工资条（当前成功批次）"}`,
      body: `
        <div class="field full"><label>导出格式</label>
          <div class="radio-list">
            <label class="radio-option"><input type="radio" name="export-format" value="zip" checked><span><strong>ZIP · 每人一份 PDF</strong><em>按筛选结果逐人生成 PDF 后打包；推荐用于分发。</em></span></label>
            <label class="radio-option"><input type="radio" name="export-format" value="merged"><span><strong>合并 PDF</strong><em>每人一页 A4，重复表头；用于集中打印或存档。</em></span></label>
            <label class="radio-option"><input type="radio" name="export-format" value="excel"><span><strong>Excel 明细</strong><em>一行一人的扁平表；批量工资条的 Excel 版式。</em></span></label>
          </div>
        </div>
        <div class="source-line">
          <div><span class="sub">数据源</span><strong>${official ? `已发快照 v${month.paidSnapshot.version}` : `当前成功批次 ${month.lastRunId}`}</strong></div>
          <div><span class="sub">筛选范围</span><strong>${state.payslipFilter === "all" ? "全部部门" : db.departments.find((d) => d.id === state.payslipFilter)?.name || "全部"}</strong></div>
          <div><span class="sub">人数</span><strong>${count} / 1000</strong></div>
          <div><span class="sub">产物有效期</span><strong>24 小时</strong></div>
        </div>
        ${count === 0 ? notice("danger", "当前筛选没有员工，无法创建导出任务。") : count > 1000 ? notice("danger", "超过 1000 人上限，请缩小筛选范围。") : ""}
        <div class="notice info">${icon("info")}<div>批量渲染走独立 worker 与共享卷；任务完成前不要关闭页面（原型会模拟进度）。无 PDF/ZIP 密码、无 PDF/A、无永久归档。</div></div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="create-export" ${count === 0 || count > 1000 ? "disabled" : ""}>${icon("play")} 创建导出任务</button>`,
      size: "lg",
      key: "export",
    });
  }

  function exportSourceLabel(month) {
    const official = payslipMode(month) === "official";
    return official ? `已发快照 v${month.paidSnapshot.version}` : `当前成功批次 ${month.lastRunId}`;
  }

  function createExportJob() {
    const month = currentMonth();
    const source = sourceForMonth(month);
    const format = document.querySelector('input[name="export-format"]:checked')?.value || "zip";
    const count = filteredPayslipResults(source).length;
    if (!count) {
      showToast("没有可导出的员工", "error");
      return;
    }
    const id = `EXP-${String(1000 + state.exportJobSeq)}`;
    state.exportJobSeq += 1;
    const job = {
      id, monthKey: month.key, type: "batch", format, sourceLabel: exportSourceLabel(month), count,
      status: "queued", progress: 0, createdAt: "2026-11-28 09:50", expiresAt: "", downloads: 0, lastDownloadedBy: "",
    };
    db.exportJobs.push(job);
    closeOverlay();
    render();
    showToast(`导出任务 ${id} 已创建，正在后台生成`);
    window.setTimeout(() => {
      job.status = "running"; job.progress = 45;
      if (state.page === "payslips") render();
    }, 500);
    window.setTimeout(() => {
      job.status = "succeeded"; job.progress = 100;
      job.expiresAt = "2026-11-29 09:50";
      if (state.page === "payslips") render();
      showToast(`导出任务 ${id} 已完成，产物 24 小时内有效`);
    }, 1800);
  }

  function downloadExport(jobId) {
    const job = db.exportJobs.find((j) => j.id === jobId);
    if (!job) return;
    if (job.status === "succeeded") {
      job.downloads = (job.downloads || 0) + 1;
      job.lastDownloadedBy = "管理员";
      render();
      showToast(`${job.id} 开始下载（原型不生成真实字节）`);
    } else if (job.status === "expired") {
      showToast("产物已过期（410）；请重新创建导出任务", "error");
    } else if (job.status === "failed") {
      showToast("任务失败；请重新创建或联系管理员", "error");
    } else {
      showToast("任务仍在生成中", "error");
    }
  }

  function downloadSinglePayslip() {
    const month = currentMonth();
    const id = `EXP-${String(1000 + state.exportJobSeq)}`;
    state.exportJobSeq += 1;
    db.exportJobs.push({
      id, monthKey: month.key, type: "single", format: "pdf",
      sourceLabel: exportSourceLabel(month), count: 1,
      status: "succeeded", progress: 100, createdAt: "2026-11-28 09:52", expiresAt: "2026-11-29 09:52", downloads: 1, lastDownloadedBy: "管理员",
    });
    render();
    showToast(`已生成 ${employeeName(state.payslipEmployeeId)} 的 PDF（原型不生成真实字节）`);
  }

  /* ---------------------------------------------------------------- cost statistics */

  function budgetStatusBadge(status) {
    const map = {
      normal: { label: "正常", cls: "badge-green" },
      warn: { label: "接近预警", cls: "badge-orange" },
      over: { label: "超预算", cls: "badge-red" },
      none: { label: "未设预算", cls: "badge-gray" },
    };
    const meta = map[status] || map.none;
    return `<span class="badge ${meta.cls}">${meta.label}</span>`;
  }

  function sourceStateBanner(month, source, flags) {
    if (!source) return "";
    if (source.source === "paid") {
      return `<div class="cost-source paid">${icon("lock")}<div><strong>数据源：已发快照 v${month.paidSnapshot.version}</strong><span>金额冻结于发放时；解锁或重算不改变本报表。预算是当前配置，对任意月份生效。</span></div><span class="spacer"></span><span class="badge badge-green">正式</span></div>`;
    }
    return `<div class="cost-source current">${icon("calculator")}<div><strong>数据源：当前成功批次 ${month.lastRunId}</strong><span>${month.state === "confirmed" ? "已确认，尚未发放。" : "未确认，以下为预览数字。"}新鲜度徽标不阻断查看，但会阻断确认与发放。</span></div><span class="spacer"></span>${flags.needsRecalc ? `<span class="badge badge-orange">待重算</span>` : ""}${flags.lastFailed ? `<span class="badge badge-red">最近批次失败</span>` : ""}${month.state !== "confirmed" ? `<span class="badge badge-blue">预览</span>` : ""}</div>`;
  }

  function renderCostBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const month = currentMonth();
    if (!month) return emptyState({ title: "暂无薪资月", desc: "请先创建薪资月。", iconName: "calendar" });
    const stats = H.costStats(db, month.key);
    const flags = H.monthFlags(db, month);
    if (!stats) {
      return `${notice("info", `当前月份为 <strong>${STATE_META[month.state].label}</strong>，尚无成功核算批次；成本报表不会用零值伪造一棵树。`)}
        ${emptyState({ title: "暂无可统计的成本数据", desc: "完成一次成功核算后，报表按冻结成本中心路径聚合；已发月份自动读取已发快照。", actions: `<button class="btn btn-primary btn-sm" data-action="go-page" data-page="calc">${icon("calculator")} 去核算</button>`, iconName: "bar-chart" })}`;
    }
    const rowHtml = (row) => `<tr class="clickable cost-row depth-${Math.min(row.depth, 3)}" data-action="open-cost-drill" data-code="${row.code}">
      <td><span class="cost-name" style="padding-left:${row.depth * 18}px">${row.depth ? `<span class="tree-line">└</span>` : ""}<strong>${esc(row.name)}</strong><span class="sub code">${esc(row.code)}</span>${row.active === false ? `<span class="badge badge-gray">停用</span>` : ""}</span></td>
      <td class="num">${row.headcount || "—"}</td>
      <td class="num">${money(row.gross)}</td>
      <td class="num">${money(Math.abs(row.social))}</td>
      <td class="num">${money(Math.abs(row.tax))}</td>
      <td class="num">${money(row.net)}</td>
      <td class="num">${row.budget ? money(row.budget) : "—"}</td>
      <td class="cost-rate">${row.budget ? `<div class="progress"><span style="width:${Math.min(100, row.rate)}%;background:${row.status === "over" ? "var(--danger)" : row.status === "warn" ? "var(--warning)" : "var(--success)"}"></span></div><span class="rate-label ${row.status}">${pct(row.rate)}</span>` : `<span class="sub">—</span>`}</td>
      <td>${budgetStatusBadge(row.status)}</td>
    </tr>`;
    return `
      ${sourceStateBanner(month, stats.source, flags)}
      <div class="stat-grid">
        ${kpi("公司应发", money(stats.company.gross), `${stats.company.count} 人 · 含未分配`)}
        ${kpi("公司预算", money(stats.company.budget), "根预算之和")}
        ${kpi("预算执行率", pct(stats.company.rate), "按应发工资")}
        ${kpi("预警成本中心", `${stats.warnCount}<small> 个</small>`, "接近预警 + 超预算", stats.warnCount ? "warning" : "")}
      </div>
      ${stats.coverageWarning ? notice("warn", "有根成本中心未设预算但其子树存在支出，公司预算未覆盖该部分。") : ""}
      <div class="card">
        <div class="card-head">
          <div><h3>${icon("bar-chart")} 成本支出统计 · ${monthLabel(month.key)}</h3><span class="sub">冻结成本中心路径（含下级）· 父行含全部下级 · 未分配计入公司合计</span></div>
          <div class="inline"><span class="badge badge-gray">${icon("info")} 预算为当前配置</span></div>
        </div>
        <div class="table-wrap">
          <table class="table cost-table">
            <thead><tr><th>成本中心</th><th class="num">人数</th><th class="num">应发</th><th class="num">社保</th><th class="num">个税</th><th class="num">实发</th><th class="num">月度预算</th><th>执行率</th><th>状态</th></tr></thead>
            <tbody>
              ${stats.rows.map(rowHtml).join("")}
              <tr class="clickable cost-row unassigned-row" data-action="open-cost-drill" data-code="unassigned">
                <td><span class="cost-name"><strong>未分配</strong><span class="sub">无成本中心归属</span></span></td>
                <td class="num">${stats.unassigned.count || "—"}</td>
                <td class="num">${money(stats.unassigned.gross)}</td>
                <td class="num">${money(Math.abs(stats.unassigned.social))}</td>
                <td class="num">${money(Math.abs(stats.unassigned.tax))}</td>
                <td class="num">${money(stats.unassigned.net)}</td>
                <td class="num">—</td>
                <td><span class="sub">不计预算</span></td>
                <td><span class="badge badge-gray">未分配</span></td>
              </tr>
            </tbody>
            <tfoot><tr class="total-row">
              <td>公司合计</td><td class="num">${stats.company.count}</td>
              <td class="num">${money(stats.company.gross)}</td>
              <td class="num">${money(Math.abs(stats.company.social))}</td>
              <td class="num">${money(Math.abs(stats.company.tax))}</td>
              <td class="num">${money(stats.company.net)}</td>
              <td class="num">${money(stats.company.budget)}</td>
              <td class="cost-rate">${stats.company.budget ? `<div class="progress"><span style="width:${Math.min(100, stats.company.rate)}%;background:${stats.company.status === "over" ? "var(--danger)" : stats.company.status === "warn" ? "var(--warning)" : "var(--success)"}"></span></div><span class="rate-label ${stats.company.status}">${pct(stats.company.rate)}</span>` : "—"}</td>
              <td>${budgetStatusBadge(stats.company.status)}</td>
            </tr></tfoot>
          </table>
        </div>
        <div class="card-foot"><span>${icon("info")} 预算口径：父预算覆盖整个子树，子预算只作分解参考；公司预算 = 根预算之和，禁止父子相加。预算 0 = 未设预算。</span><span class="sub">点击任意行下钻</span></div>
      </div>
      <div class="cost-notes">
        <div><strong>金额列</strong><span>固定取 gross / social_this / tax / net；已发（paid_advance）是发放时点的扣减，不参与成本统计。</span></div>
        <div><strong>人数</strong><span>数据源中有结果的去重员工数，含 0 与负数结果；未做 FTE 折算。</span></div>
        <div><strong>历史归属</strong><span>按核算时冻结的成本中心全路径，不按员工当前归属；组织调整不会改写历史。</span></div>
      </div>`;
  }

  function openCostDrill(code) {
    openOverlay("cost-drill", { code });
  }

  function renderCostDrillOverlay(overlay) {
    const month = currentMonth();
    const source = sourceForMonth(month);
    if (!source) return modal({ title: "成本下钻", body: notice("info", "当前月份尚无成功结果。") });
    const code = overlay.code;
    const employees = code === "unassigned"
      ? source.results.filter((row) => !(row.costPath || []).length)
      : source.results.filter((row) => (row.costPath || []).some((step) => step.code === code));
    const totals = H.aggregateResults(employees);
    const node = code === "unassigned" ? { name: "未分配", code: "UNASSIGNED" } : db.costCenters.find((c) => c.code === code);
    const canFilter = code === "unassigned" || db.costCenters.some((c) => c.code === code);
    return modal({
      title: `成本下钻 · ${node?.name || code}`,
      sub: `${monthLabel(month.key)} · ${source.label} · 含全部下级`,
      body: `
        <div class="stat-grid compact">
          ${kpi("人数", totals.count)}
          ${kpi("应发", money(totals.gross))}
          ${kpi("社保 + 个税", money(Math.abs(totals.social + totals.tax)))}
          ${kpi("实发", money(totals.net))}
        </div>
        ${code === "unassigned" ? notice("warn", "未分配支出计入公司合计，但不参与任何成本中心预算或预警。请到基础管理为员工补设成本中心。") : ""}
        <div class="table-wrap">
          <table class="table cost-drill-table">
            <thead><tr><th>工号</th><th>姓名</th><th>部门</th><th>岗位</th><th>成本归属</th><th class="num">应发</th><th class="num">社保</th><th class="num">个税</th><th class="num">实发</th></tr></thead>
            <tbody>
              ${employees.map((row) => `<tr>
                <td>${esc(row.employeeNo)}</td><td class="name">${esc(row.employeeName)}</td>
                <td>${esc(row.deptName)}</td>
                <td>${esc(row.positionName)}</td>
                <td class="sub">${row.costPath.length ? esc(row.costPath[row.costPath.length - 1].name) : "未分配"}</td>
                <td class="num">${money(row.values.gross)}</td>
                <td class="num">${money(Math.abs(row.values.social_this))}</td>
                <td class="num">${money(Math.abs(row.values.tax))}</td>
                <td class="num">${money(row.values.net)}</td>
              </tr>`).join("") || `<tr><td colspan="9" class="table-empty-cell">该成本中心下没有员工结果。</td></tr>`}
            </tbody>
          </table>
        </div>
        <div class="notice info">${icon("info")}<div>姓名与工号：已发快照取发放时冻结值；当前批次取员工档案。归属始终取核算时冻结路径。</div></div>`,
      foot: `${canFilter ? `<button class="btn btn-outline btn-sm" data-action="drill-to-list" data-code="${code}">${icon("list")} 在工资列表中筛选</button>` : ""}<span class="spacer"></span><button class="btn btn-outline btn-sm" data-action="close-overlay">关闭</button>`,
      size: "lg",
      key: `cost-${code}`,
    });
  }

  /* ---------------------------------------------------------------- configuration: compositions */

  function positionsUsing(kind, code) {
    return db.positions.filter((p) => p.payroll && p.payroll[kind] === code);
  }

  function employeeCountForPosition(positionId) {
    return db.employees.filter((emp) => emp.positionId === positionId && emp.status !== "resigned").length;
  }

  function markConfigStale() {
    for (const month of Object.values(db.months)) {
      if (month.state !== "paid" && month.results?.length) month.configStale = true;
    }
  }

  function compositionTotal(amounts) {
    return H.round2(Data.COMPOSITION_ITEMS.reduce((acc, item) => acc + Number(amounts[item.key] || 0), 0));
  }

  function renderCompositionsBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const selected = db.compositions.find((c) => c.code === state.selectedComposition) || db.compositions[0];
    const current = selected.versions.reduce((best, v) => (v.version > best.version ? v : best), selected.versions[0]);
    const using = positionsUsing("compositionCode", selected.code);
    return `
      <div class="card">
        <div class="card-head"><div><h3>${icon("package")} 薪资构成</h3><span class="sub">身份稳定 + 版本不可变；岗位只引用身份，当前版本取最高版本号</span></div><span class="badge badge-gray">${db.compositions.length} 套</span></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>编码</th><th>名称</th><th class="num">当前版本</th><th class="num">合计</th><th class="num">明细项</th><th>使用岗位</th><th>最近更新</th><th>操作</th></tr></thead>
            <tbody>
              ${db.compositions.map((comp) => {
                const version = comp.versions.reduce((best, v) => (v.version > best.version ? v : best), comp.versions[0]);
                const positions = positionsUsing("compositionCode", comp.code);
                return `<tr class="clickable ${comp.code === selected.code ? "is-current" : ""}" data-action="select-composition" data-code="${comp.code}">
                  <td class="nowrap"><span class="name">${esc(comp.code)}</span></td>
                  <td>${esc(comp.name)}</td>
                  <td class="num">v${version.version}</td>
                  <td class="num">${money(version.amounts.total_package)}</td>
                  <td class="num">${Data.COMPOSITION_ITEMS.length}</td>
                  <td>${positions.length ? positions.map((p) => esc(p.name)).join("、") : '<span class="muted">未使用</span>'}</td>
                  <td class="nowrap sub">${esc(version.createdAt)}</td>
                  <td><button class="btn btn-ghost btn-sm" data-action="select-composition" data-code="${comp.code}">${icon("eye")} 查看</button><button class="btn btn-ghost btn-sm" data-action="open-new-composition-version" data-code="${comp.code}">${icon("plus")} 新版本</button></td>
                </tr>`;
              }).join("")}
            </tbody>
          </table>
        </div>
      </div>
      <div class="grid-2">
        <div class="card">
          <div class="card-head"><div><h3>${esc(selected.name)} · v${current.version}</h3><span class="sub">${esc(selected.code)} · ${esc(current.note || "")}</span></div><span class="badge badge-blue">当前版本</span></div>
          <div class="card-body">
            <table class="table compact-table">
              <thead><tr><th>项目</th><th class="num">标准金额</th></tr></thead>
              <tbody>
                ${Data.COMPOSITION_ITEMS.map((item) => `<tr><td>${esc(item.label)} <span class="sub">${esc(item.key)}</span></td><td class="num">${money(current.amounts[item.key])}</td></tr>`).join("")}
                <tr class="total-row"><td>工资金额合计 <span class="sub">total_package</span></td><td class="num">${money(current.amounts.total_package)}</td></tr>
              </tbody>
            </table>
            <div class="notice info">${icon("info")}<div><code>total_package</code> 强校验 = 明细项之和；不相等时不能保存。历史版本不可修改，只能新建版本。</div></div>
            <div class="inline" style="margin-top:12px"><button class="btn btn-primary btn-sm" data-action="open-new-composition-version" data-code="${selected.code}">${icon("plus")} 新建版本</button><button class="btn btn-outline btn-sm" data-action="open-new-composition">${icon("package")} 新建构成</button></div>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><div><h3>${icon("history")} 版本历史</h3><span class="sub">旧版本保留以追溯</span></div><span class="badge badge-gray">${selected.versions.length} 版</span></div>
          <div class="card-body">
            <div class="version-list">
              ${[...selected.versions].sort((a, b) => b.version - a.version).map((v) => `<div class="version-item ${v.version === current.version ? "current" : ""}">
                <div class="version-head"><strong>v${v.version}</strong>${v.version === current.version ? `<span class="badge badge-blue">当前</span>` : `<span class="badge badge-gray">历史</span>`}<span class="spacer"></span><span class="sub">${esc(v.createdAt)} · ${esc(v.createdBy)}</span></div>
                <div class="version-note">${esc(v.note || "无备注")}</div>
                <div class="version-amounts"><span>合计 <strong>${money(v.amounts.total_package)}</strong></span><span>基本 <strong>${money(v.amounts.base_salary)}</strong></span><span>绩效 <strong>${money(v.amounts.performance_salary)}</strong></span></div>
              </div>`).join("")}
            </div>
            <div class="section-title">使用岗位</div>
            <div class="chip-list">${using.length ? using.map((p) => `<span class="chip">${esc(p.name)}</span>`).join("") : '<span class="muted">暂无岗位引用</span>'}</div>
            <div class="notice info">${icon("info")}<div>新建版本后，未来核算自动使用最高版本；历史批次快照保留当时金额。</div></div>
          </div>
        </div>
      </div>`;
  }

  function renderCompositionFormOverlay(overlay) {
    const isVersion = overlay.mode === "version";
    const comp = isVersion ? db.compositions.find((c) => c.code === overlay.code) : null;
    const current = comp ? comp.versions.reduce((best, v) => (v.version > best.version ? v : best), comp.versions[0]) : null;
    const amounts = current ? current.amounts : { base_salary: 0, hightemp_subsidy: 0, performance_salary: 0, overtime_pay: 0, confidentiality_allowance: 0, social_subsidy: 0, noncompete_subsidy: 0 };
    return modal({
      title: isVersion ? `新建版本 · ${comp.name}` : "新建薪资构成",
      sub: isVersion ? `当前 v${current.version}；保存后生成 v${current.version + 1}，旧版本保留` : "创建身份与 v1；合计由明细自动汇总并强校验",
      body: `
        <div class="form-grid">
          ${isVersion ? "" : `<div class="field"><label>编码 <span class="req">*</span></label><input class="input" data-comp-meta="code" placeholder="如 PROD" value=""></div>
          <div class="field"><label>名称 <span class="req">*</span></label><input class="input" data-comp-meta="name" placeholder="如 生产岗位薪资构成" value=""></div>`}
          ${Data.COMPOSITION_ITEMS.map((item) => `<div class="field"><label>${esc(item.label)} <span class="sub">${esc(item.key)}</span></label><input class="input" type="number" step="0.01" data-comp-amount="${item.key}" value="${Number(amounts[item.key] || 0)}"></div>`).join("")}
          <div class="field full"><label>工资金额合计 <span class="sub">自动汇总 · 强校验</span></label><div class="total-readout" id="comp-total">${money(compositionTotal(amounts))}</div></div>
          <div class="field full"><label>版本备注</label><input class="input" data-comp-meta="note" placeholder="${isVersion ? "说明本次调整原因" : "初始版本说明"}"></div>
        </div>
        <div class="notice info">${icon("info")}<div>金额精确到 2 位小数；保存后不可修改，只能新建版本。当前原型以合计 = Σ 明细作为 <code>total_package</code> 校验。</div></div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="save-composition" data-mode="${overlay.mode}" data-code="${overlay.code || ""}">${icon("check")} ${isVersion ? "创建版本" : "创建构成"}</button>`,
      size: "lg",
      key: `composition-${overlay.mode}-${overlay.code || ""}`,
    });
  }

  function saveComposition(mode, code) {
    const amounts = {};
    document.querySelectorAll("[data-comp-amount]").forEach((el) => { amounts[el.dataset.compAmount] = Number(el.value || 0); });
    amounts.total_package = compositionTotal(amounts);
    const note = document.querySelector('[data-comp-meta="note"]')?.value || "";
    if (mode === "version") {
      const comp = db.compositions.find((c) => c.code === code);
      const current = comp.versions.reduce((best, v) => (v.version > best.version ? v : best), comp.versions[0]);
      comp.versions.push({ version: current.version + 1, createdAt: "2026-11-28 10:00", createdBy: "管理员", note, amounts });
    } else {
      const newCode = (document.querySelector('[data-comp-meta="code"]')?.value || "").trim().toUpperCase();
      const name = (document.querySelector('[data-comp-meta="name"]')?.value || "").trim();
      if (!newCode || !name) { showToast("编码与名称必填", "error"); return; }
      if (db.compositions.some((c) => c.code === newCode)) { showToast("编码已存在", "error"); return; }
      db.compositions.push({ code: newCode, name, versions: [{ version: 1, createdAt: "2026-11-28 10:00", createdBy: "管理员", note, amounts }] });
      state.selectedComposition = newCode;
    }
    markConfigStale();
    closeOverlay();
    render();
    showToast(mode === "version" ? "新版本已创建；未来核算使用新版本" : "薪资构成已创建");
  }

  /* ---------------------------------------------------------------- configuration: schemes */

  function renderSchemesBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const selected = db.schemes.find((s) => s.code === state.selectedScheme) || db.schemes[0];
    const using = positionsUsing("schemeCode", selected.code);
    const formulaFields = db.fieldDefs.filter((f) => f.calc_mode === "formula" && f.is_active !== false).sort((a, b) => a.display_order - b.display_order);
    const overrides = Object.keys(selected.overrides || {});
    const source = sourceForMonth();
    const sample = source?.results.find((r) => r.config.schemeCode === selected.code) || source?.results[0];
    return `
      <div class="card">
        <div class="card-head"><div><h3>${icon("sliders")} 计算方案</h3><span class="sub">仅字段公式集合；构成、工作日参数由岗位分别装配</span></div><span class="badge badge-gray">${db.schemes.length} 个方案</span></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>编码</th><th>名称</th><th class="num">方案覆盖</th><th>使用岗位</th><th>最近更新</th><th>操作</th></tr></thead>
            <tbody>
              ${db.schemes.map((scheme) => {
                const positions = positionsUsing("schemeCode", scheme.code);
                const count = Object.keys(scheme.overrides || {}).length;
                return `<tr class="clickable ${scheme.code === selected.code ? "is-current" : ""}" data-action="select-scheme" data-code="${scheme.code}">
                  <td class="nowrap"><span class="name">${esc(scheme.code)}</span></td>
                  <td>${esc(scheme.name)}</td>
                  <td class="num">${count}</td>
                  <td>${positions.length ? positions.map((p) => esc(p.name)).join("、") : '<span class="muted">未使用</span>'}</td>
                  <td class="nowrap sub">${esc(scheme.updatedAt)}</td>
                  <td><button class="btn btn-ghost btn-sm" data-action="select-scheme" data-code="${scheme.code}">${icon("eye")} 查看</button><button class="btn btn-ghost btn-sm" data-action="open-new-scheme">${icon("plus")} 新建</button></td>
                </tr>`;
              }).join("")}
            </tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-head"><div><h3>${esc(selected.name)} · 生效公式</h3><span class="sub">方案级覆盖优先，否则使用字段默认公式；非公式字段不在此配置</span></div><span class="badge ${overrides.length ? "badge-orange" : "badge-gray"}">${overrides.length} 个覆盖</span></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>字段</th><th>默认公式</th><th>方案覆盖</th><th>生效公式</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              ${formulaFields.map((field) => {
                const override = selected.overrides?.[field.field_key];
                const effective = override || field.default_formula;
                return `<tr>
                  <td class="nowrap"><span class="name">${esc(field.label)}</span> <span class="sub">${esc(field.field_key)}</span></td>
                  <td class="formula-cell"><code class="formula-inline">${esc(field.default_formula)}</code></td>
                  <td class="formula-cell">${override ? `<code class="formula-inline override">${esc(override)}</code>` : '<span class="muted">—</span>'}</td>
                  <td class="formula-cell"><code class="formula-inline">${esc(effective)}</code></td>
                  <td>${override ? '<span class="badge badge-orange">覆盖</span>' : '<span class="badge badge-gray">默认</span>'}</td>
                  <td><button class="btn btn-ghost btn-sm" data-action="open-formula-editor" data-scope="scheme" data-scheme="${selected.code}" data-field="${field.field_key}">${icon("edit")} 配置</button></td>
                </tr>`;
              }).join("")}
            </tbody>
          </table>
        </div>
        <div class="card-foot"><span>${icon("info")} 计划字段（构成 / 导入）由字段定义的取数方式决定；公式引擎版本 ${esc(db.engineVersion)}。</span><span class="sub">${using.length ? `使用岗位：${using.map((p) => esc(p.name)).join("、")}` : "暂无岗位使用"}</span></div>
      </div>
      <div class="grid-2">
        <div class="card">
          <div class="card-head"><div><h3>${icon("play")} 试算样例</h3><span class="sub">当前月 · ${sample ? esc(sample.employeeName) : "暂无结果"}</span></div><button class="btn btn-outline btn-sm" data-action="open-formula-editor" data-scope="scheme" data-scheme="${selected.code}" data-field="net">${icon("play")} 打开试算</button></div>
          <div class="card-body">
            ${sample ? `<div class="stat-grid compact">${kpi("应发", money(sample.values.gross))}${kpi("社保", money(Math.abs(sample.values.social_this)))}${kpi("个税", money(Math.abs(sample.values.tax)))}${kpi("实发", money(sample.values.net))}</div><div class="notice info">${icon("info")}<div>试算使用与核算相同的编译器与求值器；不写入结果。样例员工 ${esc(sample.employeeName)}（${esc(sample.employeeNo)}）。</div></div>` : `<div class="table-empty-cell">当前月尚无该方案的成功结果。</div>`}
          </div>
        </div>
        <div class="card">
          <div class="card-head"><div><h3>${icon("history")} 修订记录</h3><span class="sub">追加式变更；保留前后文本与操作者</span></div><span class="badge badge-gray">${(selected.revisions || []).length} 条</span></div>
          <div class="card-body">
            ${(selected.revisions || []).length ? `<div class="revision-list">${[...selected.revisions].reverse().map((rev) => `<div class="revision-item"><div class="inline"><span class="badge badge-blue">${esc(rev.field)}</span><strong>${esc(rev.by)}</strong><span class="sub">${esc(rev.at)}</span></div><p>${esc(rev.note || "无备注")}</p><div class="formula-diff"><code class="old">${esc(rev.from)}</code><code class="new">${esc(rev.to)}</code></div></div>`).join("")}</div>` : `<div class="table-empty-cell">暂无方案级修订。</div>`}
          </div>
        </div>
      </div>`;
  }

  function renderSchemeFormOverlay() {
    return modal({
      title: "新建计算方案",
      sub: "创建后为空白公式集；方案覆盖按字段追加",
      body: `<div class="form-grid"><div class="field"><label>编码 <span class="req">*</span></label><input class="input" data-scheme-meta="code" placeholder="如 SALES"></div><div class="field"><label>名称 <span class="req">*</span></label><input class="input" data-scheme-meta="name" placeholder="如 销售提成方案"></div></div><div class="notice info">${icon("info")}<div>计算方案不包含金额、工作日参数或字段显隐；新增覆盖后建议立即试算。</div></div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="save-scheme">${icon("check")} 创建方案</button>`,
      size: "sm",
      key: "scheme-new",
    });
  }

  function saveScheme() {
    const code = (document.querySelector('[data-scheme-meta="code"]')?.value || "").trim().toUpperCase();
    const name = (document.querySelector('[data-scheme-meta="name"]')?.value || "").trim();
    if (!code || !name) { showToast("编码与名称必填", "error"); return; }
    if (db.schemes.some((s) => s.code === code)) { showToast("编码已存在", "error"); return; }
    db.schemes.push({ code, name, overrides: {}, updatedAt: "2026-11-28 10:05", revisions: [] });
    state.selectedScheme = code;
    state.fieldScheme = code;
    closeOverlay();
    render();
    showToast("计算方案已创建；请配置公式并装配岗位");
  }

  /* ---------------------------------------------------------------- configuration: workday */

  function renderWorkdayBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const selected = db.workdayParams.find((w) => w.code === state.selectedWorkday) || db.workdayParams[0];
    const using = positionsUsing("workdayCode", selected.code);
    return `
      <div class="card">
        <div class="card-head"><div><h3>${icon("clock")} 工作日 / 考勤参数</h3><span class="sub">计薪天数、日工时、加班倍数、最低工资；与考勤规则分离</span></div><span class="badge badge-gray">${db.workdayParams.length} 组</span></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>编码</th><th>名称</th><th class="num">月均计薪天数</th><th class="num">日工时</th><th class="num">工作日 / 周末 / 节假日倍数</th><th class="num">最低薪资</th><th>使用岗位</th><th>更新</th><th>操作</th></tr></thead>
            <tbody>
              ${db.workdayParams.map((params) => {
                const positions = positionsUsing("workdayCode", params.code);
                return `<tr class="clickable ${params.code === selected.code ? "is-current" : ""}" data-action="select-workday" data-code="${params.code}">
                  <td class="nowrap"><span class="name">${esc(params.code)}</span></td><td>${esc(params.name)}</td>
                  <td class="num">${num(params.avg_pay_days, 2)}</td><td class="num">${num(params.work_hours, 1)}h</td>
                  <td class="num">${num(params.ot_mult_weekday, 2)} / ${num(params.ot_mult_weekend, 2)} / ${num(params.ot_mult_holiday, 2)}</td>
                  <td class="num">${money(params.min_wage)}</td>
                  <td>${positions.length ? positions.map((p) => esc(p.name)).join("、") : '<span class="muted">未使用</span>'}</td>
                  <td class="nowrap sub">${esc(params.updatedAt)}</td>
                  <td><button class="btn btn-ghost btn-sm" data-action="open-edit-workday" data-code="${params.code}">${icon("edit")} 编辑</button></td>
                </tr>`;
              }).join("")}
            </tbody>
          </table>
        </div>
      </div>
      <div class="grid-2">
        <div class="card">
          <div class="card-head"><div><h3>${esc(selected.name)} · 参数</h3><span class="sub">公式中以 <code>{参数名}</code> 引用</span></div><span class="badge badge-blue">${esc(selected.code)}</span></div>
          <div class="card-body">
            <div class="param-grid">
              <div><span class="sub">avg_pay_days</span><strong>${num(selected.avg_pay_days, 2)}</strong><em>月平均计薪天数</em></div>
              <div><span class="sub">work_hours</span><strong>${num(selected.work_hours, 1)} h</strong><em>日工作小时</em></div>
              <div><span class="sub">ot_mult_weekday</span><strong>${num(selected.ot_mult_weekday, 2)}</strong><em>工作日加班倍数</em></div>
              <div><span class="sub">ot_mult_weekend</span><strong>${num(selected.ot_mult_weekend, 2)}</strong><em>周末加班倍数</em></div>
              <div><span class="sub">ot_mult_holiday</span><strong>${num(selected.ot_mult_holiday, 2)}</strong><em>节假日加班倍数</em></div>
              <div><span class="sub">min_wage</span><strong>${money(selected.min_wage)}</strong><em>最低薪资</em></div>
            </div>
            <div class="inline" style="margin-top:12px"><button class="btn btn-primary btn-sm" data-action="open-edit-workday" data-code="${selected.code}">${icon("edit")} 编辑参数</button><button class="btn btn-outline btn-sm" data-action="open-new-workday">${icon("plus")} 新建参数集</button></div>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><div><h3>${icon("briefcase")} 引用岗位</h3><span class="sub">修改后引用岗位的当前月标记待重算</span></div></div>
          <div class="card-body">
            <div class="chip-list">${using.length ? using.map((p) => `<span class="chip">${esc(p.name)} · ${employeeCountForPosition(p.id)} 人</span>`).join("") : '<span class="muted">暂无岗位引用</span>'}</div>
            <div class="notice warn">${icon("alert")}<div>工作日参数不是考勤规则：考勤模块的宽限、加班归属与日结果不在这里维护。</div></div>
          </div>
        </div>
      </div>`;
  }

  function renderWorkdayFormOverlay(overlay) {
    const editing = overlay.mode === "edit" ? db.workdayParams.find((w) => w.code === overlay.code) : null;
    const values = editing || { avg_pay_days: 21.75, work_hours: 8, ot_mult_weekday: 1.5, ot_mult_weekend: 2, ot_mult_holiday: 3, min_wage: 2040 };
    const fields = [
      ["avg_pay_days", "月平均计薪天数"], ["work_hours", "日工作小时"],
      ["ot_mult_weekday", "工作日加班倍数"], ["ot_mult_weekend", "周末加班倍数"],
      ["ot_mult_holiday", "节假日加班倍数"], ["min_wage", "最低薪资"],
    ];
    return modal({
      title: editing ? `编辑工作日参数 · ${editing.name}` : "新建工作日参数集",
      sub: "修改会追加修订记录；当前月引用岗位标记待重算",
      body: `<div class="form-grid">
        ${editing ? "" : `<div class="field"><label>编码 <span class="req">*</span></label><input class="input" data-workday-meta="code" placeholder="如 PROD"></div><div class="field"><label>名称 <span class="req">*</span></label><input class="input" data-workday-meta="name" placeholder="如 生产工时"></div>`}
        ${fields.map(([key, label]) => `<div class="field"><label>${label} <span class="sub">${key}</span></label><input class="input" type="number" step="0.01" data-workday-field="${key}" value="${Number(values[key])}"></div>`).join("")}
      </div><div class="notice warn">${icon("alert")}<div>修改后当前月引用岗位标记「配置已更新」并推荐重算；历史月沿用最近成功批次快照。</div></div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="save-workday" data-mode="${overlay.mode}" data-code="${overlay.code || ""}">${icon("check")} 保存</button>`,
      size: "lg",
      key: `workday-${overlay.mode}-${overlay.code || ""}`,
    });
  }

  function saveWorkday(mode, code) {
    const values = {};
    document.querySelectorAll("[data-workday-field]").forEach((el) => { values[el.dataset.workdayField] = Number(el.value || 0); });
    let target;
    if (mode === "edit") {
      target = db.workdayParams.find((w) => w.code === code);
      const before = { ...target };
      Object.assign(target, values, { updatedAt: "2026-11-28 10:10" });
      db.configRevisions.push({ at: "2026-11-28 10:10", by: "管理员", scope: "workday", target: code, note: `更新 ${Object.keys(values).join("、")}`, before, after: { ...values } });
    } else {
      const newCode = (document.querySelector('[data-workday-meta="code"]')?.value || "").trim().toUpperCase();
      const name = (document.querySelector('[data-workday-meta="name"]')?.value || "").trim();
      if (!newCode || !name) { showToast("编码与名称必填", "error"); return; }
      if (db.workdayParams.some((w) => w.code === newCode)) { showToast("编码已存在", "error"); return; }
      db.workdayParams.push({ code: newCode, name, ...values, updatedAt: "2026-11-28 10:10" });
      state.selectedWorkday = newCode;
    }
    markConfigStale();
    closeOverlay();
    render();
    showToast(mode === "edit" ? "工作日参数已更新；当前月标记配置已更新" : "工作日参数集已创建");
  }

  /* ---------------------------------------------------------------- configuration: assembly */

  function positionCurrentCount(positionId) {
    const month = currentMonth();
    if (!month) return 0;
    return H.employeesInScope(db, month.companyId, month.key).filter((emp) => emp.positionId === positionId).length;
  }

  function renderAssemblyBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const unconfigured = db.positions.filter((p) => !p.payroll);
    const previewEmployees = [...db.employees.filter((e) => e.status !== "resigned")].sort((a, b) => {
      const aAssembly = db.positions.find((p) => p.id === a.positionId)?.payroll ? 1 : 0;
      const bAssembly = db.positions.find((p) => p.id === b.positionId)?.payroll ? 1 : 0;
      return aAssembly - bAssembly || a.no.localeCompare(b.no);
    });
    return `
      ${unconfigured.length ? notice("warn", `<strong>${unconfigured.length} 个岗位未装配</strong>：${unconfigured.map((p) => {
        const total = employeeCountForPosition(p.id);
        const current = positionCurrentCount(p.id);
        return `${esc(p.name)}（在册 ${total} 人${total !== current ? `，本月 ${current} 人` : ""}）`;
      }).join("、")}。这些岗位的员工在对应月份会阻断核算；本月无在册员工的未装配岗位只影响后续月份。`) : notice("info", "全部岗位已完成薪资装配。")}
      <div class="card">
        <div class="card-head"><div><h3>${icon("briefcase")} 岗位薪资装配</h3><span class="sub">岗位 : 构成 / 方案 / 工作日参数 = 1 : 1；员工通过岗位获得配置</span></div><span class="badge badge-gray">${db.positions.length} 个岗位</span></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>岗位</th><th class="num">在册员工</th><th>薪资构成</th><th>计算方案</th><th>工作日参数</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              ${db.positions.map((position) => {
                const assembly = position.payroll;
                const comp = assembly ? db.compositions.find((c) => c.code === assembly.compositionCode) : null;
                const compVersion = comp ? comp.versions.reduce((best, v) => (v.version > best.version ? v : best), comp.versions[0]) : null;
                const scheme = assembly ? db.schemes.find((s) => s.code === assembly.schemeCode) : null;
                const workday = assembly ? db.workdayParams.find((w) => w.code === assembly.workdayCode) : null;
                return `<tr class="${assembly ? "" : "row-warn"}">
                  <td><span class="name">${esc(position.name)}</span> <span class="sub">${esc(position.id)}</span></td>
                  <td class="num">${employeeCountForPosition(position.id)}${employeeCountForPosition(position.id) !== positionCurrentCount(position.id) ? `<div class="sub">本月 ${positionCurrentCount(position.id)}</div>` : ""}</td>
                  <td>${comp ? `${esc(comp.name)} · v${compVersion.version}` : '<span class="muted">—</span>'}</td>
                  <td>${scheme ? esc(scheme.name) : '<span class="muted">—</span>'}</td>
                  <td>${workday ? `${esc(workday.name)} · ${num(workday.avg_pay_days, 2)} 天` : '<span class="muted">—</span>'}</td>
                  <td>${assembly ? '<span class="badge badge-green">已装配</span>' : '<span class="badge badge-red">未装配</span>'}</td>
                  <td><button class="btn btn-ghost btn-sm" data-action="open-assembly" data-position="${position.id}">${icon("edit")} ${assembly ? "修改装配" : "去装配"}</button></td>
                </tr>`;
              }).join("")}
            </tbody>
          </table>
        </div>
        <div class="card-foot"><span>${icon("info")} 岗位是基础管理已有实体；薪资装配以新增 1:1 表实现，不修改基础管理既有字段。</span><span class="sub">配置变更只影响未来核算</span></div>
      </div>
      <div class="card">
        <div class="card-head"><div><h3>${icon("users")} 员工配置展开预览</h3><span class="sub">员工只绑定岗位，自动带出三项配置</span></div></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>员工</th><th>岗位</th><th>构成</th><th>方案</th><th>工作日</th><th>薪资月状态</th></tr></thead>
            <tbody>
              ${previewEmployees.map((emp) => {
                const position = db.positions.find((p) => p.id === emp.positionId);
                const assembly = position?.payroll;
                return `<tr>
                  <td><span class="name">${esc(emp.name)}</span> <span class="sub">${esc(emp.no)}</span></td>
                  <td>${esc(position?.name || "—")}</td>
                  <td>${assembly ? esc(assembly.compositionCode) : '<span class="badge badge-red">未装配</span>'}</td>
                  <td>${assembly ? esc(assembly.schemeCode) : "—"}</td>
                  <td>${assembly ? esc(assembly.workdayCode) : "—"}</td>
                  <td><span class="badge badge-gray">随公司月份</span></td>
                </tr>`;
              }).join("")}
            </tbody>
          </table>
        </div>
      </div>`;
  }

  function renderAssemblyOverlay(overlay) {
    const position = db.positions.find((p) => p.id === overlay.position);
    if (!position) return modal({ title: "岗位装配", body: notice("warn", "岗位不存在。") });
    const assembly = position.payroll || {};
    return modal({
      title: `岗位装配 · ${position.name}`,
      sub: `${employeeCountForPosition(position.id)} 名在册员工通过该岗位获得薪资配置`,
      body: `
        <div class="form-grid">
          <div class="field"><label>薪资构成 <span class="req">*</span></label><select class="select" data-assembly="compositionCode">${db.compositions.map((comp) => {
            const version = comp.versions.reduce((best, v) => (v.version > best.version ? v : best), comp.versions[0]);
            return `<option value="${comp.code}" ${assembly.compositionCode === comp.code ? "selected" : ""}>${esc(comp.name)} · v${version.version} · ${money(version.amounts.total_package)}</option>`;
          }).join("")}</select><span class="hint">只引用身份；未来核算自动取最高版本</span></div>
          <div class="field"><label>计算方案 <span class="req">*</span></label><select class="select" data-assembly="schemeCode">${db.schemes.map((scheme) => `<option value="${scheme.code}" ${assembly.schemeCode === scheme.code ? "selected" : ""}>${esc(scheme.name)}</option>`).join("")}</select><span class="hint">方案只决定公式</span></div>
          <div class="field"><label>工作日参数 <span class="req">*</span></label><select class="select" data-assembly="workdayCode">${db.workdayParams.map((params) => `<option value="${params.code}" ${assembly.workdayCode === params.code ? "selected" : ""}>${esc(params.name)}</option>`).join("")}</select><span class="hint">计薪天数与加班倍数</span></div>
        </div>
        ${!position.payroll ? notice("warn", "该岗位未装配，其员工当前会阻断核算。保存后解除阻断。") : ""}
        <div class="notice info">${icon("info")}<div>装配修改后当前月标记「配置已更新」并推荐重算；历史月沿用最近成功批次快照。</div></div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="save-assembly" data-position="${position.id}">${icon("check")} 保存装配</button>`,
      size: "lg",
      key: `assembly-${position.id}`,
    });
  }

  function saveAssembly(positionId) {
    const position = db.positions.find((p) => p.id === positionId);
    const value = {};
    document.querySelectorAll("[data-assembly]").forEach((el) => { value[el.dataset.assembly] = el.value; });
    if (!value.compositionCode || !value.schemeCode || !value.workdayCode) {
      showToast("三项配置都必须选择", "error");
      return;
    }
    position.payroll = value;
    markConfigStale();
    closeOverlay();
    render();
    showToast(`岗位「${position.name}」已装配；当前月标记配置已更新`);
  }

  /* ---------------------------------------------------------------- configuration: fields & formulas */

  function renderFieldsBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const scheme = H.schemeFor(db, state.fieldScheme) || db.schemes[0];
    const categories = ["earning", "addon", "deduction", "total", "reference"];
    let order = [];
    let orderError = null;
    try {
      order = H.topoOrder(db.fieldDefs, scheme);
    } catch (error) {
      orderError = error;
    }
    const countOverride = Object.keys(scheme.overrides || {}).length;
    const groups = categories.map((category) => ({
      category,
      fields: db.fieldDefs.filter((f) => f.category === category).sort((a, b) => a.display_order - b.display_order),
    })).filter((group) => group.fields.length);
    return `
      <div class="card">
        <div class="card-head">
          <div><h3>${icon("columns")} 字段定义</h3><span class="sub">全系统一份；方案只覆盖公式，不另设显隐 / 分组</span></div>
          <div class="inline">
            <label class="inline-label">查看方案<select class="select" data-select="field-scheme">${db.schemes.map((s) => `<option value="${s.code}" ${s.code === scheme.code ? "selected" : ""}>${esc(s.name)}</option>`).join("")}</select></label>
            <span class="badge badge-orange">${countOverride} 个方案覆盖</span>
          </div>
        </div>
        <div class="table-wrap">
          <table class="table field-def-table">
            <thead><tr><th>字段</th><th>类别</th><th>计算方式</th><th>默认公式 / 取数</th><th>方案覆盖</th><th class="num">顺序</th><th>显示</th><th>状态</th><th>操作</th></tr></thead>
            <tbody>
              ${groups.map((group) => `
                <tr class="group-row"><td colspan="9">${Data.CATEGORY[group.category]} <span class="sub">${group.fields.length} 个字段 · ${group.category === "total" ? "合计项参与一致性校验" : group.category === "reference" ? "参考项不参与金额合计" : "类别决定小计锚点"}</span></td></tr>
                ${group.fields.map((field) => {
                  const override = scheme.overrides?.[field.field_key];
                  const effective = field.calc_mode === "formula" ? (override || field.default_formula) : null;
                  return `<tr class="${field.is_active === false ? "row-muted" : ""}">
                    <td class="nowrap"><span class="name">${esc(field.label)}</span> <span class="sub">${esc(field.field_key)}</span>${field.is_system ? '<span class="badge badge-gray">系统</span>' : '<span class="badge badge-purple">自定义</span>'}</td>
                    <td>${Data.CATEGORY[field.category]}</td>
                    <td>${sourceBadge(field.calc_mode)}</td>
                    <td class="formula-cell">${field.calc_mode === "formula" ? `<code class="formula-inline" title="${esc(field.default_formula || "")}">${esc(field.default_formula || "")}</code>` : field.calc_mode === "plan" ? `<span class="sub">取构成 ${esc(field.source_key)}</span>` : field.calc_mode === "import" ? `<span class="sub">取输入 ${esc(field.source_key)}</span>` : `<span class="sub">固定 ${esc(field.fixed_value ?? 0)}</span>`}</td>
                    <td class="formula-cell">${override ? `<code class="formula-inline override" title="${esc(override)}">${esc(override)}</code>` : '<span class="muted">—</span>'}</td>
                    <td class="num">${field.display_order}</td>
                    <td><input type="checkbox" data-field-visible="${field.field_key}" ${field.visible ? "checked" : ""} ${field.category === "total" ? "disabled" : ""} title="${field.category === "total" ? "合计项由小计 / 汇总展示" : "控制工资条显示"}"></td>
                    <td>${field.is_active === false ? '<span class="badge badge-gray">停用</span>' : '<span class="badge badge-green">启用</span>'}</td>
                    <td class="nowrap">
                      ${field.calc_mode === "formula" ? `<button class="btn btn-ghost btn-sm" data-action="open-formula-editor" data-scope="field" data-field="${field.field_key}">${icon("edit")} 默认</button><button class="btn btn-ghost btn-sm" data-action="open-formula-editor" data-scope="scheme" data-scheme="${scheme.code}" data-field="${field.field_key}">${icon("layers")} 覆盖</button>` : ""}
                      <button class="btn btn-ghost btn-sm" data-action="toggle-field" data-field="${field.field_key}">${field.is_active === false ? "启用" : "停用"}</button>
                    </td>
                  </tr>`;
                }).join("")}
              `).join("")}
            </tbody>
          </table>
        </div>
        <div class="card-foot"><span>${icon("info")} 公式以 ASCII 字段键存储；中文标签只作编辑器别名。金额字段必须显式 <code>ROUND(...,2)</code>。</span><span class="sub">${db.fieldDefs.length} 个字段 · 引擎 ${esc(db.engineVersion)}</span></div>
      </div>
      <div class="grid-2">
        <div class="card">
          <div class="card-head"><div><h3>${icon("network")} 依赖拓扑序</h3><span class="sub">引擎按引用自动排序；循环引用在保存时拒绝</span></div><span class="badge ${orderError ? "badge-red" : "badge-green"}">${orderError ? "存在环" : `${order.length} 个公式字段`}</span></div>
          <div class="card-body">
            ${orderError ? notice("danger", esc(orderError.message)) : `<div class="order-flow">${order.map((key, i) => `${i ? `<span class="order-arrow">${icon("chevron-right")}</span>` : ""}<span class="order-chip">${esc(db.fieldDefs.find((f) => f.field_key === key)?.label || key)}</span>`).join("")}</div>`}
            <div class="notice info">${icon("info")}<div>默认公式中 <code>performance</code> 依赖后声明的 <code>overtime_pay_actual</code>：顺序由依赖图决定，而不是 display_order。</div></div>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><div><h3>${icon("shield")} 五条一致性校验</h3><span class="sub">按类别锚定；任一失败整批核算失败</span></div></div>
          <div class="card-body">
            <div class="check-list">
              <div class="check-row pass">${icon("check-circle")}<span>normal_pay = ROUND(Σ 计薪项, 2)</span></div>
              <div class="check-row pass">${icon("check-circle")}<span>addon_sum = ROUND(Σ 加减项, 2)</span></div>
              <div class="check-row pass">${icon("check-circle")}<span>gross = ROUND(normal_pay + addon_sum, 2)</span></div>
              <div class="check-row pass">${icon("check-circle")}<span>deduct_sum = ROUND(Σ 代扣项, 2)</span></div>
              <div class="check-row pass">${icon("check-circle")}<span>net = ROUND(gross + deduct_sum, 2)</span></div>
            </div>
            <div class="notice warn">${icon("alert")}<div>新增自定义金额字段后，必须同步更新对应小计公式；类别不是展示分组，而是校验语义。</div></div>
          </div>
        </div>
      </div>`;
  }

  function openFormulaEditor(fieldKey, scope = "scheme", schemeCode = state.fieldScheme) {
    const field = db.fieldDefs.find((f) => f.field_key === fieldKey);
    if (!field) return;
    const scheme = H.schemeFor(db, schemeCode) || db.schemes[0];
    const current = scope === "scheme" ? (scheme.overrides?.[fieldKey] || field.default_formula || "") : (field.default_formula || "");
    openOverlay("formula-editor", {
      scope, schemeCode: scheme.code, fieldKey,
      formula: storageFormulaToDisplay(current),
      original: scope === "scheme" ? scheme.overrides?.[fieldKey] || null : field.default_formula,
      note: "",
    });
  }

  function formulaErrorLabel(code) {
    return {
      unknown_field: "未知字段",
      unknown_parameter: "未知参数",
      unknown_function: "未知函数",
      arity_error: "参数个数错误",
      division_by_zero: "除数为零",
      cycle: "循环引用",
      formula_value_scale: "金额精度不符",
      unexpected_char: "无法识别的字段名 / 字符",
      empty_formula: "公式为空",
      missing_value: "缺少字段值",
      missing_parameter: "缺少参数值",
      non_finite: "结果非有限数",
      unexpected_token: "语法错误",
      expected_paren: "括号不匹配",
      trailing_token: "多余内容",
    }[code] || code;
  }

  function formulaFeedbackHtml(overlay) {
    const trial = H.trialFormula(db, {
      schemeCode: overlay.schemeCode,
      fieldKey: overlay.fieldKey,
      formula: displayFormulaToStorage(overlay.formula),
      monthKey: state.month,
    });
    if (!trial.ok) {
      return `<div class="formula-error">${icon("x-circle")}<div><strong>${esc(formulaErrorLabel(trial.error))}</strong><p><code>${esc(trial.error)}</code> · ${esc(trial.message)}</p></div></div>`;
    }
    const result = trial.result;
    return `<div class="formula-ok">${icon("check-circle")}<div><strong>试算通过 · ${esc(employeeName(trial.employee.id))}（${esc(trial.employee.no)}）</strong><p>字段值 <span class="formula-value">${money(trial.value)}</span> · 应发 ${money(result.values.gross)} · 实发 ${money(result.values.net)}</p><p class="sub">使用与核算相同的解析 / 依赖排序 / 精度检查；试算不写入结果。</p></div></div>`;
  }

  function updateFormulaFeedback() {
    const overlay = state.overlay;
    if (!overlay || overlay.type !== "formula-editor") return;
    const feedback = document.getElementById("formula-feedback");
    if (feedback) feedback.innerHTML = formulaFeedbackHtml(overlay);
    const count = document.getElementById("formula-count");
    if (count) count.textContent = `${overlay.formula.length} / 2000 字符`;
  }

  function insertFormulaToken(token) {
    const overlay = state.overlay;
    if (!overlay || overlay.type !== "formula-editor") return;
    const input = document.getElementById("formula-input");
    const start = input ? input.selectionStart : overlay.formula.length;
    const end = input ? input.selectionEnd : overlay.formula.length;
    overlay.formula = overlay.formula.slice(0, start) + token + overlay.formula.slice(end);
    if (input) {
      input.value = overlay.formula;
      const pos = start + token.length;
      input.focus();
      input.setSelectionRange(pos, pos);
    }
    updateFormulaFeedback();
  }

  function renderFormulaEditorOverlay(overlay) {
    const field = db.fieldDefs.find((f) => f.field_key === overlay.fieldKey);
    const scheme = H.schemeFor(db, overlay.schemeCode) || db.schemes[0];
    if (!field) return modal({ title: "公式编辑器", body: notice("warn", "字段不存在。") });
    const formulaFields = db.fieldDefs.filter((f) => f.is_active !== false);
    const fieldGroups = Data.CATEGORY_ORDER
      .map((category) => ({
        category,
        label: Data.CATEGORY[category],
        fields: formulaFields.filter((f) => f.category === category).sort((a, b) => a.display_order - b.display_order),
      }))
      .filter((group) => group.fields.length);
    const functions = [
      ["ROUND(", "ROUND 四舍五入"], ["SUM(", "SUM 求和"], ["MIN(", "MIN 最小值"], ["MAX(", "MAX 最大值"],
      ["ABS(", "ABS 绝对值"], ["IF(", "IF 条件"],
    ];
    return modal({
      title: `公式编辑器 · ${field.label}`,
      sub: `${overlay.scope === "scheme" ? `方案覆盖 · ${scheme.name}` : "字段默认公式"} · 编辑区显示中文名 · 金额字段必须显式 ROUND(...,2)`,
      body: `
        <div class="formula-layout">
          <div class="formula-main">
            <div class="formula-toolbar">
              <span class="badge badge-blue">引擎 ${esc(db.engineVersion)}</span>
              <span class="badge badge-gray" id="formula-count">${overlay.formula.length} / 2000 字符</span>
              <span class="spacer"></span>
              <button class="btn btn-ghost btn-sm" data-action="restore-formula">${icon("rotate-ccw")} 恢复默认</button>
            </div>
            <textarea class="formula-input" id="formula-input" data-input="formula" data-autofocus spellcheck="false" rows="7" placeholder="ROUND(基本工资 / 工作日满勤 * 工作日出勤, 2)">${esc(overlay.formula)}</textarea>
            <div id="formula-feedback">${formulaFeedbackHtml(overlay)}</div>
            <div class="formula-meta">
              <span>默认公式：<code>${esc(storageFormulaToDisplay(INITIAL_FIELD_DEFAULTS[field.field_key] || "—"))}</code></span>
              ${overlay.scope === "scheme" ? `<span>当前覆盖：${overlay.original ? `<code>${esc(storageFormulaToDisplay(overlay.original))}</code>` : "无"}</span>` : ""}
            </div>
            <div class="field full"><label>修订备注</label><input class="input" data-formula-note placeholder="说明本次修改原因（保留在修订记录）" value="${esc(overlay.note || "")}"></div>
            <div class="notice info">${icon("info")}<div>编辑区与面板显示中文名；点击中文名插入中文名；保存时统一转换为规范 ASCII 键后落库（ADR-0007）。保存时校验语法、引用、参数个数、循环、精度。安全限额：2,000 字符 / 500 token / 深度 100 / 20,000 步。</div></div>
          </div>
          <aside class="formula-palette">
            <div class="palette-section">
              <div class="palette-title">字段 <span class="palette-hint">面板显示中文名，插入中文名</span></div>
              ${fieldGroups.map((group) => `<div class="palette-group"><div class="palette-subtitle">${group.label}</div><div class="palette-chips">${group.fields.map((f) => `<button class="palette-chip field" data-action="insert-formula" data-token="${esc(f.label)}" title="插入 ${esc(f.label)}">${esc(f.label)}</button>`).join("")}</div></div>`).join("")}
            </div>
            <div class="palette-section"><div class="palette-title">构成金额</div><div class="palette-chips">${COMPOSITION_ALIASES.map(([key, label]) => `<button class="palette-chip amount" data-action="insert-formula" data-token="${esc(label)}" title="插入 ${esc(label)}">${esc(label)}</button>`).join("")}</div></div>
            <div class="palette-section"><div class="palette-title">函数</div><div class="palette-chips">${functions.map(([token, label]) => `<button class="palette-chip fn" data-action="insert-formula" data-token="${token}" title="${esc(label)}">${esc(label)}</button>`).join("")}</div></div>
            <div class="palette-section"><div class="palette-title">参数（插入 { }）</div><div class="palette-chips">${paramAliases().map(([key, label]) => `<button class="palette-chip param" data-action="insert-formula" data-token="{${esc(label)}}" title="插入 {${esc(label)}}">${esc(label)}</button>`).join("")}</div></div>
          </aside>
        </div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><span class="spacer"></span><button class="btn btn-outline btn-sm" data-action="validate-formula">${icon("play")} 试算</button><button class="btn btn-primary btn-sm" data-action="save-formula">${icon("check")} 保存公式</button>`,
      size: "lg",
      key: `formula-${overlay.scope}-${overlay.schemeCode}-${overlay.fieldKey}`,
    });
  }

  function restoreFormulaDefault() {
    const overlay = state.overlay;
    if (!overlay || overlay.type !== "formula-editor") return;
    const field = db.fieldDefs.find((f) => f.field_key === overlay.fieldKey);
    if (overlay.scope === "scheme") {
      const scheme = H.schemeFor(db, overlay.schemeCode);
      delete scheme.overrides[overlay.fieldKey];
      overlay.formula = storageFormulaToDisplay(field.default_formula);
    } else {
      overlay.formula = storageFormulaToDisplay(INITIAL_FIELD_DEFAULTS[overlay.fieldKey] || field.default_formula);
    }
    renderOverlayRoot();
    updateFormulaFeedback();
  }

  function saveFormula() {
    const overlay = state.overlay;
    if (!overlay || overlay.type !== "formula-editor") return;
    const field = db.fieldDefs.find((f) => f.field_key === overlay.fieldKey);
    const storedFormula = displayFormulaToStorage(overlay.formula).trim();
    const trial = H.trialFormula(db, { schemeCode: overlay.schemeCode, fieldKey: overlay.fieldKey, formula: storedFormula, monthKey: state.month });
    if (!trial.ok) {
      showToast(`公式校验失败：${formulaErrorLabel(trial.error)}`, "error");
      return;
    }
    const note = document.querySelector("[data-formula-note]")?.value || "";
    const scheme = H.schemeFor(db, overlay.schemeCode);
    const before = overlay.scope === "scheme" ? scheme.overrides?.[overlay.fieldKey] || null : field.default_formula;
    if (overlay.scope === "scheme") {
      if (storedFormula === field.default_formula.trim()) delete scheme.overrides[overlay.fieldKey];
      else scheme.overrides[overlay.fieldKey] = storedFormula;
      scheme.updatedAt = "2026-11-28 10:20";
      scheme.revisions.push({
        at: "2026-11-28 10:20", by: "管理员", field: overlay.fieldKey,
        from: before || "(默认)", to: storedFormula, note,
      });
    } else {
      field.default_formula = storedFormula;
      db.configRevisions.push({
        at: "2026-11-28 10:20", by: "管理员", scope: "field-default", target: overlay.fieldKey,
        note, before, after: storedFormula,
      });
    }
    markConfigStale();
    closeOverlay();
    render();
    showToast("公式已保存；当前月标记配置已更新并推荐重算");
  }

  /* ---------------------------------------------------------------- configuration: global params */

  function renderGlobalsBody() {
    if (state.companyId !== "c1") return companyEmpty();
    const groups = [...new Set(db.globalParams.map((param) => param.group))];
    const revisions = db.configRevisions.filter((rev) => rev.scope === "global").slice(-5).reverse();
    return `
      <div class="card">
        <div class="card-head"><div><h3>${icon("database")} 全局法定参数</h3><span class="sub">系统级、全公司共享；公式中以 <code>{参数名}</code> 引用</span></div><span class="badge badge-purple">${db.globalParams.length} 个参数</span></div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>参数</th><th>分组</th><th>类型</th><th>值</th><th>说明</th><th>更新</th><th>操作</th></tr></thead>
            <tbody>
              ${groups.map((group) => `<tr class="group-row"><td colspan="7">${esc(group)}</td></tr>${db.globalParams.filter((p) => p.group === group).map((param) => `<tr>
                <td class="nowrap"><span class="name">${esc(param.label)}</span> <span class="sub">${esc(param.key)}</span></td>
                <td>${esc(param.group)}</td>
                <td>${param.type === "json" ? "JSON" : "数值"}</td>
                <td class="nowrap">${param.type === "json" ? `<code class="formula-inline">${esc(JSON.stringify(param.value))}</code>` : `<strong>${esc(param.value)}</strong>`}</td>
                <td class="sub">${esc(param.description)}</td>
                <td class="nowrap sub">${esc(param.updatedAt)}</td>
                <td><button class="btn btn-ghost btn-sm" data-action="open-global-param" data-key="${param.key}">${icon("edit")} 编辑</button></td>
              </tr>`).join("")}`).join("")}
            </tbody>
          </table>
        </div>
        <div class="card-foot"><span>${icon("info")} 修改当前配置会影响未发月份的核算；历史月沿用成功批次快照。个税 / 社保本期仍由导入提供，参数只作口径与试算。</span></div>
      </div>
      <div class="grid-2">
        <div class="card">
          <div class="card-head"><div><h3>${icon("zap")} 内置函数</h3><span class="sub">公式 V1 白名单</span></div></div>
          <div class="card-body">
            <div class="chip-list">
              <span class="chip fn">ROUND(x, n) 四舍五入</span>
              <span class="chip fn">SUM(a, b, …) 求和</span>
              <span class="chip fn">MIN / MAX / ABS</span>
              <span class="chip fn">IF(条件, 真值, 假值) 惰性</span>
              <span class="chip">+ - * / ( )</span>
              <span class="chip">&gt; &lt; &gt;= &lt;= == !=</span>
            </div>
            <div class="notice warn">${icon("alert")}<div>不支持文本 / 日期 / 查找函数、AND / OR / NOT、累进税率表引用；个税与社保本期保持导入。</div></div>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><div><h3>${icon("history")} 最近修订</h3><span class="sub">追加式快照</span></div></div>
          <div class="card-body">
            ${revisions.length ? `<div class="revision-list">${revisions.map((rev) => `<div class="revision-item"><div class="inline"><span class="badge badge-blue">${esc(rev.target)}</span><strong>${esc(rev.by)}</strong><span class="sub">${esc(rev.at)}</span></div><p>${esc(rev.note || "无备注")}</p></div>`).join("")}</div>` : `<div class="table-empty-cell">暂无全局参数修订。</div>`}
          </div>
        </div>
      </div>`;
  }

  function renderGlobalParamOverlay(overlay) {
    const param = db.globalParams.find((p) => p.key === overlay.key);
    if (!param) return modal({ title: "全局参数", body: notice("warn", "参数不存在。") });
    return modal({
      title: `编辑全局参数 · ${param.label}`,
      sub: `${esc(param.key)} · ${param.type === "json" ? "JSON 值" : "数值"} · 系统级`,
      body: `
        <div class="field full"><label>${esc(param.label)}</label>
          ${param.type === "json"
            ? `<textarea class="input textarea" rows="6" data-global-value>${esc(JSON.stringify(param.value, null, 2))}</textarea>`
            : `<input class="input" type="number" step="0.00001" data-global-value value="${esc(param.value)}">`}
          <span class="hint">${esc(param.description)}</span>
        </div>
        <div class="notice warn">${icon("alert")}<div>修改后当前未发月份标记「配置已更新」并推荐重算；历史月沿用最近成功批次快照。</div></div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="save-global-param" data-key="${param.key}">${icon("check")} 保存</button>`,
      size: "sm",
      key: `global-${param.key}`,
    });
  }

  function renderNewGlobalParamOverlay() {
    const groups = [...new Set(db.globalParams.map((param) => param.group))];
    return modal({
      title: "新增全局参数",
      sub: "系统级、全公司共享；数值型参数会进入公式编辑器「参数」面板，JSON 参数仅作配置",
      body: `
        <div class="form-grid">
          <div class="field"><label>参数键 <span class="req">*</span></label><input class="input" data-new-param="key" placeholder="如 meal_standard"><span class="hint">小写字母开头的 snake_case；保存后不可改</span></div>
          <div class="field"><label>显示名 <span class="req">*</span></label><input class="input" data-new-param="label" placeholder="如 餐补标准"><span class="hint">公式中显示为 {显示名}，落库为 {参数键}</span></div>
          <div class="field"><label>分组</label><input class="input" data-new-param="group" list="param-group-options" placeholder="如 自定义"><datalist id="param-group-options">${groups.map((group) => `<option value="${esc(group)}"></option>`).join("")}</datalist></div>
          <div class="field"><label>类型</label><select class="select" data-new-param="type"><option value="number">数值</option><option value="json">JSON</option></select></div>
          <div class="field full"><label>值 <span class="req">*</span></label><textarea class="input textarea" rows="3" data-new-param="value" placeholder="300，或 [{&quot;level&quot;:&quot;A&quot;,&quot;amount&quot;:500}]"></textarea><span class="hint">数值型参数可被公式以 {显示名} 引用；JSON 参数不进入公式面板。</span></div>
          <div class="field full"><label>说明</label><input class="input" data-new-param="description" placeholder="用途与口径"></div>
        </div>
        <div class="notice info">${icon("info")}<div>新增数值参数后立即出现在公式编辑器「参数」面板；修改后当前月标记「配置已更新」并推荐重算。</div></div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="save-new-global-param">${icon("check")} 新增参数</button>`,
      size: "lg",
      key: "global-new",
    });
  }

  function saveNewGlobalParam() {
    const key = (document.querySelector('[data-new-param="key"]')?.value || "").trim();
    const label = (document.querySelector('[data-new-param="label"]')?.value || "").trim();
    const group = (document.querySelector('[data-new-param="group"]')?.value || "").trim() || "自定义";
    const type = document.querySelector('[data-new-param="type"]')?.value || "number";
    const raw = (document.querySelector('[data-new-param="value"]')?.value || "").trim();
    const description = (document.querySelector('[data-new-param="description"]')?.value || "").trim();
    if (!/^[a-z][a-z0-9_]*$/.test(key)) { showToast("参数键必须是小写字母开头的 snake_case", "error"); return; }
    if (!label) { showToast("显示名必填", "error"); return; }
    if (db.globalParams.some((param) => param.key === key) || WORKDAY_PARAM_ALIASES.some(([paramKey]) => paramKey === key)) {
      showToast("参数键已存在", "error");
      return;
    }
    const reservedLabels = new Set([
      ...db.fieldDefs.map((field) => field.label),
      ...COMPOSITION_ALIASES.map(([, alias]) => alias),
      ...WORKDAY_PARAM_ALIASES.map(([, alias]) => alias),
      ...db.globalParams.map((param) => param.label),
    ]);
    if (reservedLabels.has(label)) { showToast("显示名与现有字段 / 构成金额 / 参数中文名重复，需唯一", "error"); return; }
    if (!raw) { showToast("参数值必填", "error"); return; }
    let value;
    if (type === "json") {
      try {
        value = JSON.parse(raw);
      } catch {
        showToast("JSON 格式无效", "error");
        return;
      }
    } else {
      value = Number(raw);
      if (!Number.isFinite(value)) { showToast("请输入有效数值", "error"); return; }
    }
    db.globalParams.push({ key, label, value, type, group, description, updatedAt: "2026-11-28 10:35" });
    db.configRevisions.push({ at: "2026-11-28 10:35", by: "管理员", scope: "global", target: key, note: "新增全局参数", before: null, after: value });
    markConfigStale();
    closeOverlay();
    render();
    showToast(`全局参数「${label}」已新增${type === "number" ? "；已进入公式参数面板" : ""}`);
  }

  function saveGlobalParam(key) {
    const param = db.globalParams.find((p) => p.key === key);
    if (!param) return;
    const el = document.querySelector("[data-global-value]");
    let value;
    if (param.type === "json") {
      try {
        value = JSON.parse(el.value);
      } catch {
        showToast("JSON 格式无效", "error");
        return;
      }
    } else {
      value = Number(el.value);
      if (!Number.isFinite(value)) { showToast("请输入有效数值", "error"); return; }
    }
    const before = H.clone(param.value);
    param.value = value;
    param.updatedAt = "2026-11-28 10:25";
    db.configRevisions.push({ at: "2026-11-28 10:25", by: "管理员", scope: "global", target: key, note: "更新全局参数", before, after: value });
    markConfigStale();
    closeOverlay();
    render();
    showToast("全局参数已更新；当前月标记配置已更新");
  }

  function saveFieldConfig(fieldKey) {
    const field = db.fieldDefs.find((f) => f.field_key === fieldKey);
    if (!field) return;
    field.is_active = field.is_active === false;
    markConfigStale();
    render();
    showToast(field.is_active ? "字段已启用" : "字段已停用；历史值保留，不再参与计算");
  }

  /* ---------------------------------------------------------------- cockpit (variant C) */

  function renderCockpit() {
    if (state.companyId !== "c1") return companyEmpty();
    const month = currentMonth();
    if (!month) return emptyState({ title: "暂无薪资月", desc: "请先创建薪资月。", iconName: "calendar" });
    const source = sourceForMonth(month);
    const flags = H.monthFlags(db, month);
    const stats = H.costStats(db, month.key);
    const scope = employeeScope(month);
    const unconfigured = unconfiguredEmployees(month);
    const committed = [...month.batches].reverse().find((b) => b.status === "committed");
    const runs = [...month.runs].reverse().slice(0, 3);
    const runningJobs = db.exportJobs.filter((job) => ["queued", "running"].includes(job.status)).length;
    const negativeNet = source ? source.results.filter((row) => row.values.net < 0).length : 0;
    const budgetAlerts = stats ? stats.rows.filter((row) => row.status === "warn" || row.status === "over") : [];
    const tasks = [
      { icon: "upload", title: "月度导入", desc: committed ? `生效批次 ${committed.id} · 输入 v${month.inputVersion}` : "尚未提交薪资月度输入", status: committed ? "已提交" : "未导入", cls: committed ? "green" : "gray", page: "import", action: "去导入" },
      { icon: "calendar", title: "考勤来源", desc: !month.attendance.locked ? "考勤月未锁定" : month.attendance.status === "stale" ? "锁定快照已变化" : `锁定快照 v${month.attendance.version} · ${month.attendance.summaryCount} 人`, status: !month.attendance.locked ? "未锁定" : month.attendance.status === "stale" ? "已变化" : "已锁定", cls: !month.attendance.locked ? "red" : month.attendance.status === "stale" ? "orange" : "green", page: "calc", action: "查看" },
      { icon: "briefcase", title: "岗位装配", desc: unconfigured.length ? `${unconfigured.map((e) => e.positionId).filter((v, i, a) => a.indexOf(v) === i).length} 个岗位未装配` : "全部在册岗位已装配", status: unconfigured.length ? `${unconfigured.length} 人阻断` : "完整", cls: unconfigured.length ? "red" : "green", page: "assembly", action: unconfigured.length ? "去装配" : "查看" },
      { icon: "calculator", title: "核算", desc: flags.lastFailed ? `最近批次失败：${H.lastRun(db, month)?.error || ""}` : flags.success ? `成功批次 ${flags.success.id}` : "尚无成功批次", status: flags.lastFailed ? "失败" : flags.needsRecalc ? "待重算" : flags.success ? "已核算" : "待核算", cls: flags.lastFailed ? "red" : flags.needsRecalc ? "orange" : flags.success ? "green" : "gray", page: "calc", action: flags.needsRecalc || !flags.success ? "去核算" : "查看" },
      { icon: "check-circle", title: "确认", desc: month.state === "confirmed" || month.state === "paid" ? "工资表已确认" : month.state === "calculated" ? "等待确认；确认后锁定结果" : "核算成功后进入确认", status: month.state === "confirmed" || month.state === "paid" ? "已确认" : month.state === "calculated" ? "待确认" : "未就绪", cls: month.state === "confirmed" || month.state === "paid" ? "green" : month.state === "calculated" ? "orange" : "gray", page: "calc", action: "查看" },
      { icon: "file", title: "工资条", desc: month.state === "paid" ? `正式工资条 · 快照 v${month.paidSnapshot?.version || 1}` : source ? "预览工资条可用；发放后转为正式" : "尚无成功结果", status: month.state === "paid" ? "正式" : source ? "预览" : "未生成", cls: month.state === "paid" ? "green" : source ? "blue" : "gray", page: "payslips", action: "查看" },
      { icon: "package", title: "导出任务", desc: runningJobs ? `${runningJobs} 个任务生成中` : "暂无进行中的导出", status: runningJobs ? "生成中" : "空闲", cls: runningJobs ? "blue" : "gray", page: "payslips", action: "查看" },
    ];
    const alerts = [];
    if (flags.lastFailed) alerts.push({ type: "danger", title: "最近核算批次失败", desc: H.lastRun(db, month)?.error || "", action: "calc" });
    if (flags.attendanceStale) alerts.push({ type: "warn", title: "考勤来源已变化", desc: "结果保持不变，确认与发放阻断；需重新核算。", action: "calc" });
    if (flags.scopeStale) alerts.push({ type: "warn", title: "员工范围已变化", desc: "需重新核算后结果才包含新范围。", action: "calc" });
    if (flags.configStale) alerts.push({ type: "warn", title: "配置已更新", desc: "当前月推荐重算；确认与发放只警告，不阻断。", action: "calc" });
    if (unconfigured.length) alerts.push({ type: "danger", title: "岗位未装配", desc: unconfigured.map((e) => `${e.name}（${e.positionId}）`).join("、"), action: "assembly" });
    if (budgetAlerts.length) alerts.push({ type: "warn", title: `${budgetAlerts.length} 个成本中心预算预警`, desc: budgetAlerts.map((row) => `${row.name} ${pct(row.rate)}`).join(" · "), action: "cost" });
    if (negativeNet) alerts.push({ type: "warn", title: `${negativeNet} 人实发为负`, desc: "负实发只警告，不阻断批次。", action: "list" });
    return `
      <div class="cockpit-hero">
        <div>
          <div class="eyebrow">${icon("bar-chart")} 薪资驾驶舱</div>
          <h1>${monthLabel(month.key)} · ${esc(currentCompany().name)}</h1>
          <p>先看「本月要处理什么」，再进入导入、核算、工资条或成本统计。配置与月度工作保持分离。</p>
        </div>
        <div class="cockpit-hero-side">
          <span class="badge ${STATE_META[month.state].cls}">${STATE_META[month.state].label}</span>
          <span class="sub">输入 v${month.inputVersion} · 考勤 ${month.attendance.locked ? `锁定 v${month.attendance.version}` : "未锁定"}</span>
          ${monthPrimaryAction(month)}
        </div>
      </div>
      ${renderMonthBar({ compact: true })}
      <div class="stat-grid cockpit-kpis">
        ${kpi("在册人数", `${scope.length}`, "含试用期")}
        ${kpi("应发合计", source ? money(source.totals.gross) : "—", source ? source.label : "尚无成功批次")}
        ${kpi("实发合计", source ? money(source.totals.net) : "—", source ? "net" : "—")}
        ${kpi("预算执行率", stats ? pct(stats.company.rate) : "—", stats ? `预算 ${money(stats.company.budget)}` : "尚无成本数据")}
        ${kpi("成本预警", stats ? `${stats.warnCount}<small> 个</small>` : "—", stats ? "接近预警 + 超预算" : "—", stats && stats.warnCount ? "warning" : "")}
      </div>
      <div class="cockpit-grid">
        <div class="card">
          <div class="card-head"><div><h3>${icon("list")} 本月待办</h3><span class="sub">按流程顺序；状态来自薪资月与批次</span></div><span class="badge badge-gray">${tasks.filter((t) => ["red", "orange"].includes(t.cls)).length} 项待处理</span></div>
          <div class="cockpit-tasks">
            ${tasks.map((task) => `<button class="cockpit-task" data-action="nav" data-page="${task.page}">
              <span class="task-icon">${icon(task.icon)}</span>
              <span class="task-body"><strong>${esc(task.title)}</strong><span>${esc(task.desc)}</span></span>
              <span class="badge badge-${task.cls}">${esc(task.status)}</span>
              <span class="task-action">${esc(task.action)} ${icon("chevron-right")}</span>
            </button>`).join("")}
          </div>
        </div>
        <div class="card">
          <div class="card-head"><div><h3>${icon("alert")} 异常与提醒</h3><span class="sub">非阻断项也会在这里露出</span></div><span class="badge ${alerts.length ? "badge-orange" : "badge-green"}">${alerts.length} 条</span></div>
          <div class="cockpit-alerts">
            ${alerts.length ? alerts.map((alert) => `<button class="cockpit-alert ${alert.type}" data-action="nav" data-page="${alert.action}">
              <span class="alert-icon">${icon(alert.type === "danger" ? "x-circle" : "alert")}</span>
              <span class="task-body"><strong>${esc(alert.title)}</strong><span>${esc(alert.desc)}</span></span>
              ${icon("chevron-right")}
            </button>`).join("") : `<div class="empty compact"><div class="empty-icon">${icon("check-circle")}</div><h3>本月没有异常</h3><p>导入、考勤、装配与核算状态都正常。</p></div>`}
          </div>
          <div class="section-title">快捷操作</div>
          <div class="quick-actions">
            <button class="btn btn-outline btn-sm" data-action="nav" data-page="import">${icon("upload")} 导入</button>
            <button class="btn btn-outline btn-sm" data-action="nav" data-page="calc">${icon("calculator")} 核算</button>
            <button class="btn btn-outline btn-sm" data-action="nav" data-page="payslips">${icon("file")} 工资条</button>
            <button class="btn btn-outline btn-sm" data-action="nav" data-page="cost">${icon("bar-chart")} 成本</button>
            <button class="btn btn-outline btn-sm" data-action="nav" data-page="compositions">${icon("settings")} 配置</button>
          </div>
        </div>
      </div>
      <div class="grid-2">
        <div class="card">
          <div class="card-head"><div><h3>${icon("history")} 最近核算</h3><span class="sub">失败批次也保留</span></div><button class="btn btn-ghost btn-sm" data-action="nav" data-page="calc">全部批次 ${icon("arrow-right")}</button></div>
          <div class="table-wrap">
            <table class="table compact-table">
              <thead><tr><th>批次</th><th>状态</th><th>时间</th><th class="num">应发</th><th class="num">实发</th></tr></thead>
              <tbody>${runs.length ? runs.map((run) => `<tr class="clickable" data-action="open-run" data-run="${run.id}"><td>${esc(run.id)}</td><td><span class="badge ${run.status === "success" ? "badge-green" : "badge-red"}">${run.status === "success" ? "成功" : "失败"}</span></td><td class="sub nowrap">${esc(run.startedAt)}</td><td class="num">${run.totals ? money(run.totals.gross) : "—"}</td><td class="num">${run.totals ? money(run.totals.net) : "—"}</td></tr>`).join("") : `<tr><td colspan="5" class="table-empty-cell">尚无核算批次。</td></tr>`}</tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><div><h3>${icon("settings")} 配置健康</h3><span class="sub">月度工作只消费配置</span></div><button class="btn btn-ghost btn-sm" data-action="nav" data-page="compositions">配置中心 ${icon("arrow-right")}</button></div>
          <div class="card-body">
            <div class="config-health-grid">
              <div><strong>${db.compositions.length}</strong><span>薪资构成</span></div>
              <div><strong>${db.schemes.length}</strong><span>计算方案</span></div>
              <div><strong>${db.workdayParams.length}</strong><span>工作日参数</span></div>
              <div class="${unconfigured.length ? "danger" : ""}"><strong>${unconfigured.length}</strong><span>未装配岗位</span></div>
              <div><strong>${db.fieldDefs.length}</strong><span>字段定义</span></div>
              <div><strong>${db.globalParams.length}</strong><span>全局参数</span></div>
            </div>
            <div class="notice info">${icon("info")}<div>配置修改后当前月标记「配置已更新」；历史月沿用最近成功批次快照。</div></div>
          </div>
        </div>
      </div>`;
  }

  /* ---------------------------------------------------------------- field form / simple confirm */

  function renderFieldFormOverlay() {
    return modal({
      title: "新增薪资字段",
      sub: "自定义字段会进入全局字段定义；需同步更新对应小计公式",
      body: `<div class="form-grid">
        <div class="field"><label>字段键 <span class="req">*</span></label><input class="input" data-field-meta="key" placeholder="如 meal_allowance"><span class="hint">小写字母 / 数字 / 下划线，创建后不可改</span></div>
        <div class="field"><label>显示名 <span class="req">*</span></label><input class="input" data-field-meta="label" placeholder="如 餐补"></div>
        <div class="field"><label>类别</label><select class="select" data-field-meta="category">${Object.entries(Data.CATEGORY).map(([key, label]) => `<option value="${key}">${label}</option>`).join("")}</select><span class="hint">类别决定一致性校验归属</span></div>
        <div class="field"><label>计算方式</label><select class="select" data-field-meta="calc_mode">${Object.entries(Data.CALC_MODE).map(([key, label]) => `<option value="${key}">${label}</option>`).join("")}</select></div>
        <div class="field full"><label>默认公式</label><input class="input" data-field-meta="formula" placeholder="ROUND(..., 2)"><span class="hint">计算方式为「公式」时必填；金额字段必须显式 ROUND</span></div>
        <div class="field"><label>取数键（构成 / 导入）</label><input class="input" data-field-meta="source" placeholder="如 meal_allowance"></div>
        <div class="field"><label>固定值</label><input class="input" type="number" step="0.01" data-field-meta="fixed" placeholder="0"></div>
        <div class="field"><label>显示顺序</label><input class="input" type="number" data-field-meta="order" value="330"></div>
        <div class="field"><label>工资条显示</label><label class="check-option"><input type="checkbox" data-field-meta="visible" checked><span>显示</span></label></div>
      </div>
      <div class="notice warn">${icon("alert")}<div>新增计薪 / 加减 / 代扣字段后，必须把它加入对应小计公式，否则五条一致性校验会失败。自定义字段默认不在工资列表显示，可在列设置中勾选。</div></div>`,
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-primary btn-sm" data-action="save-field">${icon("check")} 新增字段</button>`,
      size: "lg",
      key: "field-new",
    });
  }

  function saveNewField() {
    const key = (document.querySelector('[data-field-meta="key"]')?.value || "").trim();
    const label = (document.querySelector('[data-field-meta="label"]')?.value || "").trim();
    const category = document.querySelector('[data-field-meta="category"]')?.value || "earning";
    const calcMode = document.querySelector('[data-field-meta="calc_mode"]')?.value || "formula";
    const formula = (document.querySelector('[data-field-meta="formula"]')?.value || "").trim();
    const source = (document.querySelector('[data-field-meta="source"]')?.value || "").trim();
    const fixed = Number(document.querySelector('[data-field-meta="fixed"]')?.value || 0);
    const order = Number(document.querySelector('[data-field-meta="order"]')?.value || 330);
    const visible = Boolean(document.querySelector('[data-field-meta="visible"]')?.checked);
    if (!/^[a-z][a-z0-9_]*$/.test(key)) { showToast("字段键必须是小写字母开头的 snake_case", "error"); return; }
    if (!label) { showToast("显示名必填", "error"); return; }
    if (db.fieldDefs.some((f) => f.field_key === key)) { showToast("字段键已存在", "error"); return; }
    const reservedLabels = new Set([
      ...db.fieldDefs.map((f) => f.label),
      ...COMPOSITION_ALIASES.map(([, alias]) => alias),
      ...paramAliases().map(([, alias]) => alias),
    ]);
    if (reservedLabels.has(label)) { showToast("显示名与现有字段 / 构成金额 / 参数中文名重复；公式编辑器按中文名解析，需唯一", "error"); return; }
    if (calcMode === "formula") {
      try { H.parseFormula(formula); } catch (error) { showToast(`公式语法错误：${error.message}`, "error"); return; }
    }
    if ((calcMode === "plan" || calcMode === "import") && !source) { showToast("取数键必填", "error"); return; }
    db.fieldDefs.push({
      field_key: key, label, category, calc_mode: calcMode,
      source_key: calcMode === "plan" || calcMode === "import" ? source : null,
      default_formula: calcMode === "formula" ? formula : null,
      fixed_value: calcMode === "fixed" ? fixed : null,
      display_order: order, visible, list_default: false, is_system: false, is_active: true,
    });
    markConfigStale();
    closeOverlay();
    render();
    showToast("字段已新增；请同步更新对应小计公式");
  }

  function renderUnconfirmOverlay() {
    return modal({
      title: "取消确认",
      sub: "取消后月份回到「已核算」，可重新核算；已发快照不受影响。",
      body: notice("info", "取消确认不会删除结果或批次；确认与发放门槛需重新满足。"),
      foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">取消</button><button class="btn btn-danger btn-sm" data-action="do-unconfirm">${icon("rotate-ccw")} 取消确认</button>`,
      size: "sm",
      key: "unconfirm",
    });
  }

  /* ---------------------------------------------------------------- flow / diff / questions */

  function flowOverlay() {
    const variant = state.variant;
    const box = (title, sub, cls = "") => `<div class="flow-box ${cls}"><strong>${title}</strong>${sub ? `<span>${sub}</span>` : ""}</div>`;
    const arrow = `<div class="flow-arrow">${icon("arrow-right")}</div>`;
    let content = "";
    if (variant === "A") {
      content = `<div class="flow-canvas flow-two">
        <div class="flow-col">
          <div class="flow-col-head">薪资配置 · 低频、公司级</div>
          ${box("薪资构成", "身份 + 不可变版本")}${arrow}
          ${box("计算方案", "字段公式覆盖")}${arrow}
          ${box("工作日参数", "计薪天数 / 工时 / 倍数")}${arrow}
          ${box("岗位装配", "1:1 绑定三项配置", "accent")}
          <div class="flow-pair">${box("字段与公式", "全局字段定义 + 默认公式")}${box("全局参数", "系统级法定口径")}</div>
        </div>
        <div class="flow-divider"></div>
        <div class="flow-col">
          <div class="flow-col-head">薪资月度 · 每月、按公司 + 月份</div>
          ${box("月度导入", "考勤拉取 + 薪资文件 + 预览提交")}${arrow}
          ${box("核算与确认", "检查 → 核算 → 确认", "accent")}${arrow}
          ${box("工资条", "正式 / 预览 + 批量导出")}${arrow}
          ${box("成本统计", "冻结路径聚合 + 预算预警")}
          <div class="flow-note">工资列表在核算后随时查看；明细抽屉追溯来源与公式。</div>
        </div>
      </div>`;
    } else if (variant === "B") {
      content = `<div class="flow-canvas flow-loop">
        <div class="flow-col-head">薪资月度工作台 · 月份是上下文</div>
        <div class="flow-loop-row">
          ${box("导入", "批次 / 预览 / 输入版本")}${arrow}
          ${box("核算", "检查 / 批次 / 快照", "accent")}${arrow}
          ${box("确认", "门槛 + 锁定")}${arrow}
          ${box("发工资条", "正式快照 / 导出")}
        </div>
        <div class="flow-under">工作台顶部常驻月份切换、状态条与四步 stepper；页签：工资列表 / 导入 / 核算 / 工资条 / 成本统计。</div>
        <div class="flow-separator"><span>配置中心 · 独立入口，不随月份切换</span></div>
        <div class="flow-loop-row small">
          ${box("薪资构成", "")}${box("计算方案", "")}${box("工作日参数", "")}${box("岗位装配", "")}${box("字段与公式", "")}${box("全局参数", "")}
        </div>
      </div>`;
    } else {
      content = `<div class="flow-canvas flow-cockpit">
        <div class="flow-col-head">薪资驾驶舱 · 看「本月要处理什么」</div>
        <div class="flow-cockpit-hero">${box("KPI + 月份状态", "人数 / 应发 / 实发 / 预算 / 预警", "accent")}<div class="flow-side">${box("待办清单", "导入 / 考勤 / 装配 / 核算 / 确认 / 工资条")}${box("异常收件箱", "失败批次 / 过期 / 预算 / 负实发")}</div></div>
        <div class="flow-loop-row">
          ${box("工资列表", "动态列 + 明细抽屉")}${arrow}
          ${box("月度导入", "向导 + 预览")}${arrow}
          ${box("核算与确认", "检查 + 生命周期")}${arrow}
          ${box("工资条", "正式 / 预览")}${arrow}
          ${box("成本统计", "树 + 下钻")}
        </div>
        <div class="flow-under">每个模式顶部保留「返回驾驶舱」；配置中心从侧边栏进入，内部用左侧配置分区导航。</div>
      </div>`;
    }
    return modal({
      title: "页面流程",
      sub: `当前方案 ${state.variant} · ${state.variant === "A" ? "双区模块独立" : state.variant === "B" ? "月份工作台 + 配置中心" : "任务驾驶舱 + 模式"}`,
      body: `${content}
        <div class="notice info">${icon("info")}<div><strong>建议评审路径：</strong>${variant === "A" ? "从工资列表看结果与明细 → 月度导入预览 → 核算检查与确认 → 工资条 → 成本下钻 → 配置区新建构成 / 配置公式 / 装配岗位。" : variant === "B" ? "在月份工作台走一遍 导入 → 核算 → 确认 → 工资条；观察月份 stepper 与页签上下文；再到配置中心横向比较六类配置。" : "从驾驶舱的待办与异常进入导入 / 核算 / 工资条 / 成本；返回驾驶舱检查状态变化；最后从侧边栏进入配置中心。"}</div></div>`,
      size: "lg",
      key: "flow",
    });
  }

  function diffOverlay() {
    const rows = [
      ["导航", "顶部页签 + 纵向长页堆叠；考勤与薪资混在同一面板", "薪资独立模块；配置（低频、公司级）与月度工作（每月、按公司 + 月份）分离", "两种工作节奏不同：配置需要横向比较与版本，月度工作需要月份上下文与状态机"],
      ["配置结构", "构成 / 方案 / 工作日 / 岗位 / 字段 / 参数分散在同一长页", "配置区独立：薪资构成、计算方案、工作日参数、岗位装配、字段与公式、全局参数", "配置一次、复用多岗位；不应被月度操作打断"],
      ["月度状态", "工资列表 + 发布工资条按钮；没有核算批次与状态门", "draft → calculated → confirmed → paid；确认 / 发放需检查考勤、输入版本与范围", "把「能算」「可确认」「已发放」分开，避免静默改数"],
      ["月度导入", "文本域 + 解析 + 确认导入；列映射与错误报告较弱", "批次向导：上传 / 粘贴 → 列映射 → 预览校验 → 提交；来源分色、错误行、清零、覆盖手工值", "导入应可审计、可回退；考勤列只识别不生效"],
      ["公式编辑", "字段表 + 文本公式；缺少插入与实时试算", "字段 / 函数 / 参数插入、实时试算、错误诊断、依赖拓扑序、修订记录", "业务人员自助配置需要低门槛与可解释错误"],
      ["工资列表", "一张宽表 + 点击看字段明细", "动态列 / 部门（含下级）/ 岗位 / 成本中心（含下级）/ 未分配筛选 / 合计 / 明细抽屉", "列表回答「谁拿了多少」，抽屉回答「为什么是这个数」"],
      ["工资条", "发布到员工端 H5；未区分配置与快照", "正式（最新已发快照）/ 预览（当前成功批次）分离；异步 ZIP / 合并 PDF / Excel；24h 产物", "发放凭证必须可复现；员工端 H5 在本 effort 之外"],
      ["成本统计", "成本架构面板内联统计 + 预算", "独立月度报表；冻结成本中心全路径（含下级）、未分配单列、三态预警、下钻到人", "组织调整不应改写历史；预算口径与部门汇总并列"],
      ["权限", "RBAC + 部门数据范围过滤", "本期沿用登录；所有登录用户拥有薪资全部权限；API 预留 payroll_access", "RBAC 是另一个 effort；不要让原型暗示未实现的能力"],
      ["状态与异常", "主要覆盖正常路径", "加载 / 空 / 错误；考勤过期 / 未锁定 / 范围变化 / 未装配 / 失败批次 / 配置已更新", "异常状态是薪资月的一等公民，不是补丁"],
    ];
    return modal({
      title: "与需求原型的差异",
      sub: "对比 docs/requirement/rx-hr-prototype.html 的薪资相关面板；差异均为 IA / 交互层面，功能口径以 ADR-0006～0011 为准",
      body: `<div class="table-wrap"><table class="table diff-table">
        <thead><tr><th>维度</th><th>需求原型</th><th>本原型</th><th>为什么</th></tr></thead>
        <tbody>${rows.map((row) => `<tr>${row.map((cell, i) => `<td class="${i === 0 ? "nowrap name" : ""}">${esc(cell)}</td>`).join("")}</tr>`).join("")}</tbody>
      </table></div>
      <div class="notice info">${icon("info")}<div>本原型不实现 RBAC、员工端 H5、审批流、银行代发、历史迁移与自动个税；这些都在 map 的 Out of scope。</div></div>`,
      size: "lg",
      key: "diff",
    });
  }

  function questionsOverlay() {
    const questions = [
      ["整体 IA", "A 双区模块独立 / B 月份工作台 + 配置中心 / C 任务驾驶舱 + 模式，选哪个？是否需要混合（例如 A 的侧边栏 + B 的月份 stepper）？"],
      ["配置边界", "六类配置是否都应独立成页？「字段与公式」和「计算方案」的边界是否清楚，还是应该合并？全局参数放在配置区还是系统设置？"],
      ["月度主入口", "默认落地应是工资列表、月份工作台还是驾驶舱？「核算与确认」是否值得独立成页，还是放进工资列表的月份状态条？"],
      ["月份上下文", "月份应放在顶栏全局切换还是只在月度页内？切换配置页再回来是否保留月份？B 的 stepper 是否比 A 的月份条更清楚？"],
      ["公式编辑器", "字段 / 函数 / 参数面板 + 实时试算是否足够？试算样例用真实员工还是合成样例？保存时阻断错误 vs 允许保存草稿？"],
      ["导入预览", "来源分色（考勤 / 文件 / 手工 / 清零 / 错误）是否可读？错误行是阻断提交，还是「仅保留有效行」？缺失员工按 0 清零是否需要在提交前二次确认？"],
      ["工资列表", "默认列是否合适？成本中心（含下级）筛选放在列表还是成本报表？明细抽屉的分区（字段 / 考勤 / 快照 / 校验）是否过重？"],
      ["工资条与导出", "正式 / 预览的呈现是否足够区分？批量导出放在工资条页还是独立「导出任务」页？导出任务表是否需要常驻？"],
      ["成本统计", "树表 + 下钻 + 三态预算是否满足？「未分配」与公司合计的呈现是否清楚？是否需要在工资列表与成本报表之间提供更强的互链？"],
      ["状态与异常", "当前覆盖加载 / 空 / 错误、考勤过期、未锁定、范围变化、未装配、失败批次、配置已更新；还缺哪些真实状态（例如并发导入、导出失败、负数实发）？"],
    ];
    return modal({
      title: "讨论问题",
      sub: "逐条记录选择；确认后把结论写回 ticket #52 的 resolution，并更新原型 README 的评审结论",
      body: `<div class="question-list">${questions.map(([title, body], i) => `<div class="question-item"><span class="question-no">${i + 1}</span><div><strong>${esc(title)}</strong><p>${esc(body)}</p></div></div>`).join("")}</div>
      <div class="notice info">${icon("info")}<div>重点建议先定 1–4 的 IA 问题；5–10 是交互细节，可在定稿前逐条裁剪。</div></div>`,
      size: "lg",
      key: "questions",
    });
  }

  /* ---------------------------------------------------------------- overlay dispatch */

  function renderOverlay(overlay) {
    switch (overlay.type) {
      case "employee-detail": return renderEmployeeDetailOverlay(overlay);
      case "columns": return renderColumnsOverlay();
      case "manual": return renderManualInputOverlay(overlay);
      case "import-wizard": return renderImportWizardOverlay(overlay);
      case "calc-blocked": return renderCalcBlockedOverlay();
      case "confirm": return renderConfirmOverlay();
      case "pay": return renderPayOverlay();
      case "unconfirm": return renderUnconfirmOverlay();
      case "unlock": return renderUnlockOverlay();
      case "run-detail": return renderRunDetailOverlay(overlay);
      case "export": return renderExportOverlay();
      case "cost-drill": return renderCostDrillOverlay(overlay);
      case "composition-form": return renderCompositionFormOverlay(overlay);
      case "scheme-form": return renderSchemeFormOverlay();
      case "workday-form": return renderWorkdayFormOverlay(overlay);
      case "assembly": return renderAssemblyOverlay(overlay);
      case "formula-editor": return renderFormulaEditorOverlay(overlay);
      case "global-param": return renderGlobalParamOverlay(overlay);
      case "global-param-new": return renderNewGlobalParamOverlay();
      case "field-form": return renderFieldFormOverlay();
      case "flow": return flowOverlay();
      case "diff": return diffOverlay();
      case "questions": return questionsOverlay();
      default:
        return modal({ title: "未实现", body: notice("warn", `原型未实现叠加层：${esc(overlay.type)}`), foot: `<button class="btn btn-outline btn-sm" data-action="close-overlay">关闭</button>` });
    }
  }

  /* ---------------------------------------------------------------- interactions */

  function switchVariant(delta) {
    const order = ["A", "B", "C"];
    const index = order.indexOf(state.variant);
    const next = order[(index + delta + order.length) % order.length];
    state.variant = next;
    if (!VALID_PAGES[next].includes(state.page)) state.page = next === "C" ? "cockpit" : "list";
    state.pageByVariant[next] = state.page;
    state.overlay = null;
    state.companyMenuOpen = false;
    syncUrl();
    render();
  }

  function rerenderPreservingFocus() {
    const active = document.activeElement;
    const inputName = active?.getAttribute?.("data-input");
    const id = active?.id;
    const start = active?.selectionStart;
    const end = active?.selectionEnd;
    render();
    let el = null;
    if (inputName) el = document.querySelector(`[data-input="${inputName}"]`);
    else if (id) el = document.getElementById(id);
    if (el) {
      el.focus();
      if (start != null && typeof el.setSelectionRange === "function") {
        try { el.setSelectionRange(start, end); } catch { /* select elements */ }
      }
    }
  }

  function downloadCsv(filename, rows) {
    const csv = rows.map((row) => row.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(",")).join("\r\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  document.addEventListener("click", (event) => {
    const el = event.target.closest("[data-action]");
    if (!el) return;
    const action = el.dataset.action;
    if (el.tagName === "BUTTON" || el.getAttribute("role") === "button") event.preventDefault();
    switch (action) {
      case "stub":
        state.companyMenuOpen = false;
        render();
        showToast(`${el.dataset.label || "该模块"} 已实现；本原型聚焦薪资管理`, "success");
        break;
      case "nav":
        state.overlay = null;
        state.companyMenuOpen = false;
        goPage(el.dataset.page);
        break;
      case "go-page":
        state.overlay = null;
        goPage(el.dataset.page);
        break;
      case "toggle-theme":
        state.theme = state.theme === "dark" ? "light" : "dark";
        syncUrl();
        render();
        break;
      case "toggle-narrow":
        state.narrow = !state.narrow;
        syncUrl();
        render();
        break;
      case "toggle-mobile-nav":
        state.mobileNav = !state.mobileNav;
        render();
        break;
      case "close-mobile-nav":
        state.mobileNav = false;
        render();
        break;
      case "toggle-company-menu":
        state.companyMenuOpen = !state.companyMenuOpen;
        render();
        break;
      case "select-company": {
        state.companyId = el.dataset.company;
        state.companyMenuOpen = false;
        state.overlay = null;
        state.month = "2026-11";
        syncUrl();
        render();
        showToast(`已切换到 ${currentCompany().name}`);
        break;
      }
      case "variant-prev":
        switchVariant(-1);
        break;
      case "variant-next":
        switchVariant(1);
        break;
      case "open-flow":
        openOverlay("flow");
        break;
      case "open-diff":
        openOverlay("diff");
        break;
      case "open-questions":
        openOverlay("questions");
        break;
      case "set-preview":
        state.preview = el.dataset.preview;
        syncUrl();
        render();
        break;
      case "reset-prototype":
        window.location.assign(`${window.location.pathname}?variant=${state.variant}`);
        break;
      case "close-overlay":
        closeOverlay();
        break;

      /* list */
      case "open-columns":
        openOverlay("columns");
        break;
      case "open-employee":
        openEmployeeDetail(el.dataset.employee);
        break;
      case "open-manual":
        openOverlay("manual", { employeeId: el.dataset.employee });
        break;
      case "save-manual":
        saveManualInput(el.dataset.employee);
        break;
      case "reset-columns":
        state.listColumns = db.fieldDefs.filter((f) => f.list_default).map((f) => f.field_key);
        render();
        break;
      case "clear-list-filters":
        state.listFilters = { dept: "all", position: "all", cost: "all", q: "" };
        syncUrl();
        render();
        break;
      case "open-payslip-employee":
        state.payslipEmployeeId = el.dataset.employee;
        state.overlay = null;
        goPage("payslips");
        break;
      case "drill-to-list":
        state.listFilters.cost = el.dataset.code;
        state.overlay = null;
        goPage("list");
        break;
      case "select-payslip-employee":
        state.payslipEmployeeId = el.dataset.employee;
        syncUrl();
        render();
        break;
      case "clear-payslip-filter":
        state.payslipFilter = "all";
        render();
        break;
      case "download-payroll-detail": {
        const source = sourceForMonth();
        if (!source) { showToast("当前月份尚无成功结果", "error"); break; }
        const rows = filteredResults(source);
        const fields = listFields(source);
        downloadCsv(`payroll-detail-${state.month}.csv`, [
          ["工号", "姓名", "部门", "岗位", "成本归属", ...fields.map((f) => f.label), "应发", "实发"],
          ...rows.map((row) => [
            row.employeeNo, row.employeeName, row.deptName, row.positionName,
            row.costPath.length ? row.costPath[row.costPath.length - 1].name : "未分配",
            ...fields.map((f) => row.values[f.field_key]),
            row.values.gross, row.values.net,
          ]),
        ]);
        showToast(`已导出 ${rows.length} 人明细 CSV（原型）`);
        break;
      }

      /* import */
      case "open-import-wizard":
        openImportWizard();
        break;
      case "load-import-sample":
        loadImportSample();
        break;
      case "wizard-next": {
        const wiz = state.wizard;
        if (!wiz) break;
        if (wiz.step === 1) {
          const headers = parseCsvLines(wiz.text)[0] || [];
          if (!headers.length) { wiz.error = "请先粘贴或载入 CSV"; renderOverlayRoot(); break; }
          if (!Object.keys(wiz.mapping).length) wiz.mapping = autoMapping(headers);
          wiz.step = 2;
          wiz.error = null;
        } else if (wiz.step === 2) {
          const hasEmployee = Object.values(wiz.mapping).includes("employee_no");
          const payrollCount = Object.values(wiz.mapping).filter((v) => Data.PAYROLL_IMPORT_FIELDS.includes(v)).length;
          if (!hasEmployee) { wiz.error = "必须映射工号"; renderOverlayRoot(); break; }
          if (!payrollCount) { wiz.error = "至少映射一个薪资自有列"; renderOverlayRoot(); break; }
          wiz.step = 3;
          wiz.preview = null;
          wiz.cleaned = false;
          wiz.error = null;
        }
        renderOverlayRoot();
        break;
      }
      case "wizard-back":
        if (state.wizard) state.wizard.step = Math.max(1, state.wizard.step - 1);
        renderOverlayRoot();
        break;
      case "clean-import-preview":
        cleanImportPreview();
        break;
      case "commit-import":
        commitImport();
        break;
      case "refresh-attendance": {
        const month = currentMonth();
        if (month) {
          month.attendance.pulledAt = "2026-11-28 10:30";
          render();
          showToast(month.attendance.locked ? "已重新读取考勤锁定快照" : "考勤月未锁定，读取不到汇总", month.attendance.locked ? "success" : "error");
        }
        break;
      }
      case "download-import-template":
        downloadCsv("payroll-import-template.csv", [Data.IMPORT_COLUMNS.map((col) => col.header)]);
        showToast("模板 CSV 已下载（仅表头）");
        break;

      /* calculation */
      case "calculate":
      case "open-calculate":
        startCalculation();
        break;
      case "open-confirm":
        openOverlay("confirm");
        break;
      case "do-confirm":
        doConfirm();
        break;
      case "open-pay":
        openOverlay("pay");
        break;
      case "do-pay":
        doPay();
        break;
      case "open-unconfirm":
        openOverlay("unconfirm");
        break;
      case "do-unconfirm":
        doUnconfirm();
        break;
      case "open-unlock":
        openOverlay("unlock");
        break;
      case "do-unlock": {
        const reason = document.querySelector('[data-input="unlock-reason"]')?.value || "";
        doUnlock(reason);
        break;
      }
      case "open-run":
        openOverlay("run-detail", { runId: el.dataset.run });
        break;
      case "toggle-attendance-stale":
        toggleAttendanceStale();
        break;
      case "toggle-scope-stale":
        toggleScopeStale();
        break;

      /* payslips & exports */
      case "open-export":
        openOverlay("export");
        break;
      case "create-export":
        createExportJob();
        break;
      case "download-export":
        downloadExport(el.dataset.job);
        break;
      case "download-single-payslip":
        downloadSinglePayslip();
        break;

      /* cost */
      case "open-cost-drill":
        openCostDrill(el.dataset.code);
        break;

      /* config */
      case "select-composition":
        state.selectedComposition = el.dataset.code;
        render();
        break;
      case "open-new-composition":
        openOverlay("composition-form", { mode: "new", code: "" });
        break;
      case "open-new-composition-version":
        openOverlay("composition-form", { mode: "version", code: el.dataset.code });
        break;
      case "save-composition":
        saveComposition(el.dataset.mode, el.dataset.code);
        break;
      case "select-scheme":
        state.selectedScheme = el.dataset.code;
        state.fieldScheme = el.dataset.code;
        render();
        break;
      case "open-new-scheme":
        openOverlay("scheme-form");
        break;
      case "save-scheme":
        saveScheme();
        break;
      case "select-workday":
        state.selectedWorkday = el.dataset.code;
        render();
        break;
      case "open-new-workday":
        openOverlay("workday-form", { mode: "new", code: "" });
        break;
      case "open-edit-workday":
        openOverlay("workday-form", { mode: "edit", code: el.dataset.code });
        break;
      case "save-workday":
        saveWorkday(el.dataset.mode, el.dataset.code);
        break;
      case "open-assembly":
        openOverlay("assembly", { position: el.dataset.position });
        break;
      case "save-assembly":
        saveAssembly(el.dataset.position);
        break;
      case "open-formula-editor":
        openFormulaEditor(el.dataset.field, el.dataset.scope || "scheme", el.dataset.scheme || state.fieldScheme);
        break;
      case "insert-formula":
        insertFormulaToken(el.dataset.token || "");
        break;
      case "restore-formula":
        restoreFormulaDefault();
        break;
      case "validate-formula": {
        updateFormulaFeedback();
        const overlay = state.overlay;
        const trial = H.trialFormula(db, { schemeCode: overlay.schemeCode, fieldKey: overlay.fieldKey, formula: displayFormulaToStorage(overlay.formula), monthKey: state.month });
        showToast(trial.ok ? `试算通过：${money(trial.value)}` : `试算失败：${formulaErrorLabel(trial.error)}`, trial.ok ? "success" : "error");
        break;
      }
      case "save-formula":
        saveFormula();
        break;
      case "open-new-field":
        openOverlay("field-form");
        break;
      case "save-field":
        saveNewField();
        break;
      case "toggle-field":
        saveFieldConfig(el.dataset.field);
        break;
      case "open-global-param":
        openOverlay("global-param", { key: el.dataset.key });
        break;
      case "open-new-global-param":
        openOverlay("global-param-new");
        break;
      case "save-new-global-param":
        saveNewGlobalParam();
        break;
      case "save-global-param":
        saveGlobalParam(el.dataset.key);
        break;
      default:
        showToast(`未实现的动作：${action}`, "error");
    }
  });

  document.addEventListener("change", (event) => {
    const target = event.target;
    if (target.matches("[data-select]")) {
      const name = target.dataset.select;
      const value = target.value;
      if (name === "preview") {
        state.preview = value;
        if (value !== "normal") syncUrl();
        render();
      } else if (name === "month") {
        goMonth(value);
      } else if (name === "list-dept") {
        state.listFilters.dept = value;
        render();
      } else if (name === "list-position") {
        state.listFilters.position = value;
        render();
      } else if (name === "list-cost") {
        state.listFilters.cost = value;
        syncUrl();
        render();
      } else if (name === "payslip-dept") {
        state.payslipFilter = value;
        render();
      } else if (name === "field-scheme") {
        state.fieldScheme = value;
        render();
      } else if (name === "mapping") {
        state.wizard.mapping[target.dataset.column] = value;
        renderOverlayRoot();
      }
      return;
    }
    if (target.matches("[data-column]")) {
      const key = target.dataset.column;
      if (target.checked) {
        if (!state.listColumns.includes(key)) state.listColumns.push(key);
      } else {
        state.listColumns = state.listColumns.filter((item) => item !== key);
        if (!state.listColumns.length) state.listColumns = [key];
      }
      renderOverlayRoot();
      return;
    }
    if (target.matches("[data-field-visible]")) {
      const field = db.fieldDefs.find((f) => f.field_key === target.dataset.fieldVisible);
      if (field) {
        field.visible = target.checked;
        markConfigStale();
        render();
      }
      return;
    }
    if (target.matches('[data-input="import-file"]')) {
      const file = target.files && target.files[0];
      if (!file) return;
      state.wizard.fileName = file.name;
      const reader = new FileReader();
      reader.onload = () => {
        state.wizard.text = String(reader.result || "");
        const headers = parseCsvLines(state.wizard.text)[0] || [];
        state.wizard.mapping = autoMapping(headers);
        state.wizard.step = 2;
        state.wizard.error = null;
        renderOverlayRoot();
        showToast(`已读取 ${file.name}`);
      };
      reader.readAsText(file, "utf-8");
    }
  });

  document.addEventListener("input", (event) => {
    const target = event.target;
    const name = target.getAttribute("data-input");
    if (name === "list-search") {
      state.listFilters.q = target.value;
      rerenderPreservingFocus();
    } else if (name === "formula" && state.overlay?.type === "formula-editor") {
      state.overlay.formula = target.value;
      updateFormulaFeedback();
    } else if (name === "import-csv" && state.wizard) {
      state.wizard.text = target.value;
      const next = document.querySelector('[data-action="wizard-next"]');
      if (next) next.disabled = !target.value.trim();
    } else if (target.matches("[data-comp-amount]")) {
      const total = Array.from(document.querySelectorAll("[data-comp-amount]")).reduce((acc, el) => acc + Number(el.value || 0), 0);
      const readout = document.getElementById("comp-total");
      if (readout) readout.textContent = money(H.round2(total));
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (state.overlay) {
        closeOverlay();
        event.preventDefault();
      } else if (state.mobileNav || state.companyMenuOpen) {
        state.mobileNav = false;
        state.companyMenuOpen = false;
        render();
      }
      return;
    }
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      const tag = (event.target.tagName || "").toLowerCase();
      if (["input", "textarea", "select"].includes(tag) || event.target.isContentEditable || event.metaKey || event.ctrlKey || event.altKey) return;
      if (!state.overlay) {
        switchVariant(event.key === "ArrowLeft" ? -1 : 1);
        event.preventDefault();
      }
      return;
    }
    if ((event.key === "Enter" || event.key === " ") && event.target.matches('[role="button"][data-action]')) {
      event.preventDefault();
      event.target.click();
    }
  });

  parseUrl();
  render();
})();
