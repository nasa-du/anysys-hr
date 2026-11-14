/* Attendance IA prototype — interaction shell.
 * Throwaway code: in-memory data, no persistence, no production hardening. */
(() => {
  "use strict";

  const Data = window.AttendanceData;
  const db = Data.createDb();

  /* ---------------------------------------------------------------- icons */

  const ICONS = {
    dashboard:
      '<rect x="3" y="3" width="7" height="7" rx="1.2"/><rect x="14" y="3" width="7" height="7" rx="1.2"/><rect x="3" y="14" width="7" height="7" rx="1.2"/><rect x="14" y="14" width="7" height="7" rx="1.2"/>',
    building:
      '<path d="M3 21h18"/><path d="M5 21V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v16"/><path d="M15 21V9h2a2 2 0 0 1 2 2v10"/><path d="M9 7h2"/><path d="M9 11h2"/><path d="M9 15h2"/>',
    network:
      '<rect x="9" y="3" width="6" height="5" rx="1"/><rect x="3" y="16" width="6" height="5" rx="1"/><rect x="15" y="16" width="6" height="5" rx="1"/><path d="M12 8v4"/><path d="M6 16v-2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v2"/>',
    users:
      '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>',
    briefcase:
      '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/><path d="M2 12h20"/>',
    wallet:
      '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
    settings:
      '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2Z"/><circle cx="12" cy="12" r="3"/>',
    plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "chevron-right": '<path d="m9 18 6-6-6-6"/>',
    "chevron-down": '<path d="m6 9 6 6 6-6"/>',
    "chevron-left": '<path d="m15 18-6-6 6-6"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
    "arrow-left": '<path d="M19 12H5"/><path d="m11 18-6-6 6-6"/>',
    "arrow-up-right": '<path d="M7 17 17 7"/><path d="M8 7h9v9"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "x-circle": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6"/><path d="m15 9-6 6"/>',
    alert:
      '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.6 2.3c-.7.4-1.1 1-1.1 1.8v.4"/><path d="M12 17h.01"/>',
    edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    trash:
      '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>',
    refresh:
      '<path d="M3 12a9 9 0 0 1 15.5-6.2L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 21v-5h5"/>',
    "rotate-ccw": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
    lock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    unlock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 7.5-2"/>',
    calendar:
      '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "map-pin": '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    upload:
      '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
    download:
      '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
    file:
      '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h5"/>',
    copy:
      '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    sync:
      '<path d="M21 12a9 9 0 0 0-15.5-6.2L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 15.5 6.2L21 16"/><path d="M21 21v-5h-5"/>',
    play: '<path d="m7 4 13 8-13 8Z"/>',
    list: '<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    inbox:
      '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z"/>',
    sliders:
      '<path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><path d="M1 14h6"/><path d="M9 8h6"/><path d="M17 16h6"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
    history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>',
    zap: '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z"/>',
    coffee: '<path d="M17 8h1a4 4 0 1 1 0 8h-1"/><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z"/><path d="M6 2v2"/><path d="M10 2v2"/><path d="M14 2v2"/>',
    "more-horizontal": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    "bar-chart": '<path d="M3 3v18h18"/><path d="M7 16v-5"/><path d="M12 16V7"/><path d="M17 16v-8"/>',
    timer: '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2"/><path d="M9 2h6"/>',
    menu: '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>',
    "log-out": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
    flag: '<path d="M4 22V4"/><path d="M4 4c5-3 8 3 13 0v9c-5 3-8-3-13 0"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    command: '<path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3V6a3 3 0 1 0-3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3Z"/>',
    ban: '<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/>',
    package:
      '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
  };

  function icon(name, cls = "") {
    const content = ICONS[name] || "";
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
    page: "schedule",
    pageByVariant: { A: "schedule", B: "schedule", C: "cockpit" },
    month: "2026-09",
    companyId: "c1",
    // scheduling
    scheduleView: "plan",
    selectedPlanId: "all",
    scopeFilter: "all",
    selectedEmployeeId: "E103",
    selectedDate: null,
    showExceptions: true,
    employeeSearch: "",
    // results
    resultTab: "days",
    resultFilter: "all",
    resultDept: "all",
    resultStatus: "all",
    resultSearch: "",
    resultAdjusted: false,
    resultPage: 1,
    resultDate: null,
    // import
    importType: "punch",
    // rules
    holidayMonth: "2026-09",
    // overlays / transient
    overlay: null,
    toast: null,
    draft: null,
    wizard: null,
    flash: null,
  };

  let lastOverlayKey = "";
  let toastTimer = null;

  /* ---------------------------------------------------------------- helpers */

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];
  const SHIFT_CLASS = {
    ADM: "ADM",
    TEC: "TEC",
    YL: "YL",
    EARLY: "EARLY",
    MID: "MID",
    NIGHT: "NIGHT",
    DAWN: "DAWN",
  };

  function pad2(n) {
    return String(n).padStart(2, "0");
  }
  function dayNum(date) {
    return Number(date.slice(8, 10));
  }
  function weekdayCN(date) {
    return `周${WEEKDAYS[Data.weekdayIndex(date)]}`;
  }
  function dateCN(date) {
    return `${Number(date.slice(5, 7))}月${dayNum(date)}日 ${weekdayCN(date)}`;
  }
  function monthCN(month) {
    return `${month.slice(0, 4)} 年 ${Number(month.slice(5, 7))} 月`;
  }
  function monthLabel(month) {
    return `${Number(month.slice(5, 7))} 月`;
  }
  function minutesLabel(min) {
    if (!min) return "0";
    const h = Math.floor(min / 60);
    const m = min % 60;
    return h ? `${h}h${m ? ` ${m}m` : ""}` : `${m}m`;
  }
  function hoursLabel(min) {
    return (min / 60).toFixed(2);
  }
  function money(n) {
    return Number(n || 0).toFixed(2);
  }
  function nowLabel() {
    return "2026-11-14 10:30";
  }

  function currentCompany() {
    return db.companies.find((c) => c.id === state.companyId) || db.companies[0];
  }
  function companyEmployees() {
    return db.employees.filter((e) => e.companyId === state.companyId);
  }
  function activeEmployees(month = state.month) {
    return companyEmployees().filter(
      (e) => e.status !== "resigned" && Data.employedInMonth(e, month),
    );
  }
  function monthState(month = state.month) {
    return (
      db.months[month] || {
        status: "draft",
        isStale: true,
        calculatedAt: null,
        confirmedAt: null,
        lockedAt: null,
        unlockReason: null,
      }
    );
  }
  function isEditable(month = state.month) {
    return ["draft", "calculated"].includes(monthState(month).status);
  }
  function isLocked(month = state.month) {
    return monthState(month).status === "locked";
  }
  function companyPlans(month = state.month) {
    return db.plans.filter(
      (p) => p.companyId === state.companyId && p.month === month && p.status === "enabled",
    );
  }
  function committedBatch(dataType, month = state.month) {
    return (
      db.importBatches.find(
        (b) =>
          b.companyId === state.companyId &&
          b.dataType === dataType &&
          b.month === month &&
          b.status === "committed",
      ) || null
    );
  }
  function committedBatches(month = state.month) {
    return ["punch", "trip", "ot", "leave"]
      .map((t) => committedBatch(t, month))
      .filter(Boolean);
  }
  function resultsForMonth(month = state.month) {
    return db.results[month] || [];
  }
  function summariesForMonth(month = state.month) {
    return db.summaries[month] || [];
  }
  function getShift(code) {
    return Data.getShift(db, code);
  }
  function getEmployee(id) {
    return Data.getEmployee(db, id);
  }
  function employeeName(id) {
    const emp = getEmployee(id);
    return emp ? emp.name : id;
  }
  function employeeDeptName(id) {
    const emp = getEmployee(id);
    return emp ? Data.deptPath(db, emp.deptId) : "";
  }
  function deptOptions(includeAll = true) {
    const rows = db.departments.filter((d) => d.companyId === state.companyId);
    return (
      (includeAll ? [{ value: "all", label: "全部部门" }] : []) .concat(
        rows.map((d) => ({ value: d.id, label: Data.deptPath(db, d.id) })),
      )
    );
  }
  function planScopeLabel(plan) {
    if (!plan) return "";
    if (plan.scopeType === "all") return "全公司";
    if (plan.scopeType === "dept") {
      return plan.scopeIds.map((id) => Data.getDept(db, id)?.name || id).join("、");
    }
    if (plan.scopeType === "position") {
      return plan.scopeIds
        .map((id) => db.positions.find((p) => p.id === id)?.name || id)
        .join("、");
    }
    return plan.scopeIds.map((id) => employeeName(id)).join("、");
  }
  function planSpecificityLabel(plan) {
    return { all: "全公司", dept: "部门", position: "岗位", employee: "员工" }[
      plan.scopeType
    ];
  }
  function shiftChip(code, extra = "") {
    const shift = getShift(code);
    if (!shift) return `<span class="shift-chip shift-muted">未知班次</span>`;
    return `<span class="shift-chip shift-${SHIFT_CLASS[code] || "ADM"} ${extra}" title="${esc(
      shift.name,
    )} ${shift.start}–${shift.end}">${esc(shift.name)}</span>`;
  }
  function shiftChipCode(code) {
    const shift = getShift(code);
    if (!shift) return "";
    return `<span class="shift-code shift-${SHIFT_CLASS[code] || "ADM"}">${esc(
      shift.code,
    )}</span>`;
  }
  function shiftDot(code) {
    return `<span class="shift-dot shift-${SHIFT_CLASS[code] || "ADM"}"></span>`;
  }
  function shiftTime(code) {
    const shift = getShift(code);
    if (!shift) return "";
    return `${shift.start}–${shift.end}${shift.crossDay ? " +1" : ""}`;
  }

  const STATUS_META = {
    normal: { label: "正常", cls: "badge-green" },
    late: { label: "迟到", cls: "badge-orange" },
    early: { label: "早退", cls: "badge-orange" },
    missing_punch: { label: "缺卡", cls: "badge-amber" },
    absent: { label: "旷工", cls: "badge-red" },
    overtime: { label: "OA 加班", cls: "badge-purple" },
    trip_out: { label: "外出", cls: "badge-blue" },
    trip_business: { label: "出差", cls: "badge-blue" },
    personal_leave: { label: "事假", cls: "badge-gray" },
    paid_leave: { label: "带薪假", cls: "badge-teal" },
    comp_leave: { label: "补休", cls: "badge-indigo" },
    rest: { label: "休息", cls: "badge-gray" },
    unscheduled_attendance: { label: "未排班出勤", cls: "badge-teal" },
  };
  function statusMeta(status) {
    return STATUS_META[status] || { label: status || "—", cls: "badge-gray" };
  }
  function statusBadge(status) {
    const meta = statusMeta(status);
    return `<span class="badge ${meta.cls}">${esc(meta.label)}</span>`;
  }
  function monthStatusBadge(month = state.month) {
    const ms = monthState(month);
    const labels = {
      draft: "草稿",
      calculated: "已计算",
      confirmed: "已确认",
      locked: "已锁定",
    };
    const cls = {
      draft: "status-draft",
      calculated: "status-calculated",
      confirmed: "status-confirmed",
      locked: "status-locked",
    };
    return `<span class="status-pill ${cls[ms.status]}"><span class="dot"></span>${
      labels[ms.status]
    }${ms.isStale && ms.status !== "locked" ? " · 已过期" : ""}</span>`;
  }
  function dayTypeBadge(date) {
    const label = Data.dayTypeLabel(db, date);
    const cls = label === "法定节假日" ? "holiday" : label === "调休上班" ? "adjusted" : "";
    return `<span class="cal-daytype ${cls}">${esc(label)}</span>`;
  }
  function flagsLabel(code) {
    return (
      {
        late: "迟到",
        early: "早退",
        missing_punch: "缺卡",
        break_punch_missing: "午休卡缺失",
        absent: "旷工",
        overtime: "加班",
        oa_ot_only: "仅 OA 加班",
        trip: "外出/出差",
        leave: "请假",
        unscheduled_attendance: "未排班出勤",
        punch_during_leave: "请假期间打卡",
        leave_trip_conflict: "请假与出差同日",
        leave_ot_conflict: "请假与加班同日",
        multiple_leave_requests: "同日多张假单",
        leave_on_non_workday: "请假落在非排班日",
        leave_days_excess: "请假天数超出",
        leave_range_uncovered: "请假区间无排班",
        comp_offset_no_ot: "补休无可抵加班",
        comp_offset_unused: "补休未用完",
        out_of_window_punch: "窗口外打卡",
        no_valid_punch: "无有效打卡",
        manual_adjustment: "人工调整",
      }[code] || code
    );
  }
  function flagChip(code) {
    const danger = ["absent", "leave_ot_conflict", "leave_trip_conflict"].includes(code);
    const warn = [
      "late",
      "early",
      "missing_punch",
      "break_punch_missing",
      "unscheduled_attendance",
      "punch_during_leave",
      "comp_offset_no_ot",
      "comp_offset_unused",
      "out_of_window_punch",
    ].includes(code);
    const info = ["trip", "leave", "overtime", "manual_adjustment"].includes(code);
    const cls = danger ? "danger" : warn ? "warn" : info ? "info" : "";
    return `<span class="flag-chip ${cls}">${esc(flagsLabel(code))}</span>`;
  }
  function isExceptionResult(r) {
    if (!r) return false;
    if (["absent", "missing_punch", "late", "early", "unscheduled_attendance"].includes(r.dayStatus)) {
      return true;
    }
    return (r.dayFlags || []).some((f) =>
      [
        "leave_trip_conflict",
        "leave_ot_conflict",
        "comp_offset_no_ot",
        "comp_offset_unused",
        "punch_during_leave",
        "out_of_window_punch",
      ].includes(f),
    );
  }
  function exceptionResults(month = state.month) {
    return resultsForMonth(month).filter(isExceptionResult);
  }

  /* ---------------------------------------------------------------- URL / render root */

  function parseUrl() {
    const params = new URLSearchParams(window.location.search);
    const variant = (params.get("variant") || "A").toUpperCase();
    state.variant = ["A", "B", "C"].includes(variant) ? variant : "A";
    const month = params.get("month");
    if (month === "2026-09" || month === "2026-10") state.month = month;
    state.theme = params.get("theme") === "dark" ? "dark" : "light";
    const preview = params.get("preview");
    if (["normal", "loading", "empty", "error"].includes(preview)) state.preview = preview;
    state.narrow = params.get("narrow") === "1";
    const view = params.get("view");
    if (view === "employee" || view === "plan") state.scheduleView = view;
    const employee = params.get("employee");
    if (employee && getEmployee(employee)) {
      state.selectedEmployeeId = employee;
    }
    const validPages = {
      A: ["schedule", "import", "results", "rules", "shifts"],
      B: ["schedule", "import", "results", "rules", "shifts"],
      C: ["cockpit", "schedule", "import", "results", "rules"],
    };
    const page = params.get("page");
    if (page && validPages[state.variant].includes(page)) state.page = page;
    else state.page = state.variant === "C" ? "cockpit" : "schedule";
    state.pageByVariant[state.variant] = state.page;
  }

  function syncUrl() {
    const params = new URLSearchParams();
    params.set("variant", state.variant);
    params.set("page", state.page);
    params.set("month", state.month);
    params.set("theme", state.theme);
    if (state.preview !== "normal") params.set("preview", state.preview);
    if (state.narrow) params.set("narrow", "1");
    if (state.scheduleView !== "plan") params.set("view", state.scheduleView);
    if (state.scheduleView === "employee" && state.selectedEmployeeId) {
      params.set("employee", state.selectedEmployeeId);
    }
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}?${params.toString()}`,
    );
  }

  function setState(patch, options = {}) {
    Object.assign(state, patch);
    if (options.sync !== false) syncUrl();
    render();
  }

  function showToast(message, type = "success") {
    state.toast = { message, type };
    render();
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      state.toast = null;
      render();
    }, 2800);
  }

  function setFlash(message, type = "success") {
    state.flash = { message, type };
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
    if (key && key !== lastOverlayKey) {
      const target = document.querySelector("[data-autofocus]");
      if (target) target.focus();
    }
    lastOverlayKey = key;
  }

  /* ---------------------------------------------------------------- shell */

  function renderSidebar() {
    const navA = [
      { key: "schedule", icon: "calendar", label: "排班工作台" },
      { key: "import", icon: "upload", label: "导入中心", badge: importAttention() },
      { key: "results", icon: "inbox", label: "考勤结果", badge: exceptionResults().length },
      { key: "rules", icon: "sliders", label: "规则与节假日" },
      { key: "shifts", icon: "clock", label: "班次" },
    ];
    return `<aside class="sidebar ${state.mobileNav ? "mobile-open" : ""}" aria-label="侧边栏">
      <div class="logo">
        <div class="logo-mark">A</div>
        <div class="logo-text"><strong>AnySys HR</strong><span class="sub">考勤管理原型</span></div>
      </div>
      <nav class="nav" aria-label="主导航">
        <div class="nav-label">基础管理</div>
        ${["公司", "部门", "员工", "岗位", "成本中心"]
          .map(
            (label, i) =>
              `<button class="nav-item" data-action="stub" data-label="${label}" title="基础管理已实现，本原型聚焦考勤">${icon(
                ["building", "network", "users", "briefcase", "wallet"][i],
              )}<span>${label}</span></button>`,
          )
          .join("")}
        <div class="nav-label">考勤管理</div>
        ${
          state.variant === "A"
            ? navA
                .map(
                  (item) =>
                    `<button class="nav-item ${state.page === item.key ? "active" : ""}" data-action="nav" data-page="${item.key}" data-autofocus="${item.key === "schedule" ? "1" : ""}">${icon(
                      item.icon,
                    )}<span>${item.label}</span>${
                      item.badge
                        ? `<span class="nav-badge">${item.badge}</span>`
                        : ""
                    }</button>`,
                )
                .join("")
            : `<button class="nav-item active" data-action="nav" data-page="${
                state.variant === "C" ? "cockpit" : "schedule"
              }">${icon("calendar")}<span>考勤管理</span></button>`
        }
      </nav>
      <div class="sidebar-footer">
        <button class="nav-item" data-action="toggle-theme" title="切换深色 / 浅色">${icon(
          state.theme === "dark" ? "sun" : "moon",
        )}<span>${state.theme === "dark" ? "浅色主题" : "深色主题"}</span></button>
        <div class="user-row" style="margin-top:8px">
          <div class="avatar">管</div>
          <div class="user-meta"><strong>管理员</strong><span class="sub">admin@example.com</span></div>
        </div>
      </div>
    </aside>`;
  }

  function importAttention() {
    const previews = db.importBatches.filter(
      (b) => b.companyId === state.companyId && b.status === "preview",
    ).length;
    return previews || "";
  }

  function renderTopbar() {
    const crumbs = [];
    crumbs.push("基础管理");
    crumbs.push(state.variant === "C" && state.page === "cockpit" ? "考勤驾驶舱" : "考勤管理");
    const pageLabel = {
      schedule: "排班工作台",
      import: "导入中心",
      results: "考勤结果",
      rules: "规则与节假日",
      shifts: "班次",
      cockpit: "驾驶舱",
    }[state.page];
    if (pageLabel && !(state.variant === "C" && state.page === "cockpit")) {
      crumbs.push(pageLabel);
    }
    const crumbHtml = crumbs
      .map((c, i) => {
        const isLast = i === crumbs.length - 1;
        return `${i ? icon("chevron-right") : ""}${
          isLast ? `<strong>${esc(c)}</strong>` : `<span>${esc(c)}</span>`
        }`;
      })
      .join("");
    const company = currentCompany();
    const companyMenu = state.companyMenuOpen
      ? `<div class="company-menu" role="menu">
          <div class="company-menu-head">切换当前公司</div>
          ${db.companies
            .map(
              (item) => `<button class="company-menu-item ${
                item.id === state.companyId ? "active" : ""
              }" data-action="select-company" data-company="${item.id}" role="menuitem">
                <span class="company-menu-dot"></span>
                <span class="company-menu-text"><strong>${esc(item.name)}</strong><span class="company-menu-meta">${esc(
                  item.code,
                )} · ${
                  item.id === "c1" ? "考勤样例数据" : "暂无考勤数据"
                }</span></span>
                ${item.id === state.companyId ? icon("check") : ""}
              </button>`,
            )
            .join("")}
          <div class="company-menu-foot"><button class="btn btn-ghost btn-sm" data-action="stub" data-label="公司管理">${icon(
            "settings",
          )} 公司管理</button></div>
        </div>`
      : "";
    return `<header class="topbar">
      <div class="inline" style="min-width:0">
        <button class="mobile-menu-btn" data-action="toggle-mobile-nav" aria-label="打开导航">${icon(
          "menu",
        )}</button>
        <div class="breadcrumb">${crumbHtml}</div>
      </div>
      <div class="topbar-right">
        <div class="company-switch-wrap">
          <button class="company-switch" data-action="toggle-company-menu" aria-haspopup="menu" aria-expanded="${
            state.companyMenuOpen ? "true" : "false"
          }">${icon("building")}<span>${esc(company.name)}</span><span class="code">${esc(
            company.code,
          )}</span>${icon("chevron-down")}</button>
          ${companyMenu}
        </div>
        <button class="btn btn-icon btn-outline" data-action="toggle-theme" title="切换深色 / 浅色" aria-label="切换深色 / 浅色">${icon(
          state.theme === "dark" ? "sun" : "moon",
        )}</button>
        <div class="avatar" title="管理员">管</div>
      </div>
    </header>`;
  }

  function renderPrototypeBar() {
    const bar = document.getElementById("prototype-bar");
    if (!bar) return;
    const names = {
      A: "A · 模块独立",
      B: "B · 单工作台 + 页签",
      C: "C · 异常优先驾驶舱",
    };
    bar.innerHTML = `
      <button class="pb-btn" data-action="variant-prev" title="上一个方案（←）" aria-label="上一个方案">${icon(
        "chevron-left",
      )}</button>
      <span class="pb-label"><span class="pb-tag">原型</span><span class="pb-variant">${
        names[state.variant]
      }</span></span>
      <button class="pb-btn" data-action="variant-next" title="下一个方案（→）" aria-label="下一个方案">${icon(
        "chevron-right",
      )}</button>
      <span class="pb-divider"></span>
      <button class="pb-btn" data-action="toggle-theme" title="切换深色 / 浅色">${icon(
        state.theme === "dark" ? "sun" : "moon",
      )} ${state.theme === "dark" ? "浅色" : "深色"}</button>
      <button class="pb-btn" data-action="toggle-narrow" title="窄屏预览">${icon(
        "grid",
      )} ${state.narrow ? "退出窄屏" : "窄屏"}</button>
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
    if (state.page === "cockpit") return renderCockpitPage();
    const embedded = state.variant !== "A";
    const content = renderPageContent(state.page, embedded);
    if (state.variant === "A") return content;
    if (state.variant === "B") return renderWorkbench(content);
    return renderCMode(content);
  }

  function pageHead(title, sub, actions = "") {
    return `<div class="page-head">
      <div><h1 class="page-title">${esc(title)}</h1><p class="page-sub">${sub}</p></div>
      <div class="actions">${actions}</div>
    </div>`;
  }

  function renderPageContent(page, embedded) {
    const map = {
      schedule: renderSchedulePage,
      import: renderImportPage,
      results: renderResultsPage,
      rules: renderRulesPage,
      shifts: renderShiftsPage,
    };
    const fn = map[page] || renderSchedulePage;
    return fn({ embedded });
  }

  function previewGuard(renderNormal) {
    if (state.preview === "loading") return renderSkeletonPage();
    if (state.preview === "error") return renderErrorPage();
    if (state.preview === "empty") return renderEmptyPage();
    return renderNormal();
  }

  function renderSkeletonPage() {
    return `<div class="skeleton-page">
      <div class="skeleton" style="height:26px;width:220px;margin-bottom:14px"></div>
      <div class="skeleton-cards" style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:14px">
        ${Array.from({ length: 5 }, () => `<div class="skeleton-card" style="height:82px"></div>`).join("")}
      </div>
      <div class="skeleton-card" style="height:360px"></div>
    </div>`;
  }

  function renderErrorPage() {
    return `<div class="empty error-state" style="padding:70px 20px">
      <div class="empty-icon">${icon("alert")}</div>
      <h3>页面加载失败</h3>
      <p>原型模拟的服务端错误。可以切换回正常状态，或重试当前页面。</p>
      <div class="inline" style="justify-content:center">
        <button class="btn btn-primary" data-action="set-preview" data-preview="normal">${icon(
          "refresh",
        )} 重试</button>
        <button class="btn btn-outline" data-action="open-questions">${icon("help")} 查看讨论问题</button>
      </div>
    </div>`;
  }

  function renderEmptyPage() {
    return `<div class="empty" style="padding:70px 20px">
      <div class="empty-icon">${icon("calendar")}</div>
      <h3>当前公司还没有考勤数据</h3>
      <p>先创建班次与排班方案，再导入打卡和 OA 申请。也可以切换到「荣新矿业」查看完整样例。</p>
      <div class="inline" style="justify-content:center">
        <button class="btn btn-primary" data-action="nav" data-page="shifts">${icon("clock")} 先建班次</button>
        <button class="btn btn-outline" data-action="nav" data-page="schedule">${icon("calendar")} 去排班</button>
      </div>
    </div>`;
  }

  function renderCompanyEmpty() {
    return `<div class="empty" style="padding:56px 20px">
      <div class="empty-icon">${icon("building")}</div>
      <h3>${esc(currentCompany().name)} 暂无考勤数据</h3>
      <p>原型为第二家公司准备了空数据，用于检查无数据引导与公司上下文切换。切换回「荣新矿业」可继续评审。</p>
      <button class="btn btn-primary" data-action="select-company" data-company="c1">${icon(
        "arrow-left",
      )} 返回荣新矿业</button>
    </div>`;
  }

  /* ---------------------------------------------------------------- placeholder pages (filled below) */

  /* ================================================================ schedule */

  function selectedPlan() {
    if (state.selectedPlanId === "all") return null;
    return db.plans.find((p) => p.id === state.selectedPlanId) || null;
  }

  function scopedEmployees(month = state.month) {
    const list = activeEmployees(month);
    if (state.scopeFilter.startsWith("dept:")) {
      const id = state.scopeFilter.slice(5);
      const ids = new Set(Data.deptDescendants(db, id));
      return list.filter((e) => ids.has(e.deptId));
    }
    if (state.scopeFilter.startsWith("emp:")) {
      const id = state.scopeFilter.slice(4);
      return list.filter((e) => e.id === id);
    }
    return list;
  }

  function employeeListEmployees(month = state.month) {
    const list = activeEmployees(month);
    if (state.scopeFilter.startsWith("dept:")) {
      const id = state.scopeFilter.slice(5);
      const ids = new Set(Data.deptDescendants(db, id));
      return list.filter((e) => ids.has(e.deptId));
    }
    return list;
  }

  function planEmployeesFor(plan, month = state.month) {
    return activeEmployees(month).filter((e) => Data.planCovers(db, plan, e));
  }

  function manualCountFor(empId, month = state.month) {
    return Object.values(db.exceptions).filter(
      (ex) => ex.employeeId === empId && Data.monthOf(ex.date) === month,
    ).length;
  }

  function renderMonthBar(actions = "") {
    return `<div class="month-bar">
      <div class="month-nav">
        <button data-action="month-prev" aria-label="上一个月" ${
          state.month === "2026-09" ? "disabled" : ""
        }>${icon("chevron-left")}</button>
        <strong>${monthCN(state.month)}</strong>
        <button data-action="month-next" aria-label="下一个月" ${
          state.month === "2026-10" ? "disabled" : ""
        }>${icon("chevron-right")}</button>
      </div>
      ${monthStatusBadge()}
      <span class="sub">${esc(currentCompany().name)} · 时间口径 Asia/Shanghai</span>
      <span class="spacer"></span>
      <div class="inline">${actions}</div>
    </div>`;
  }

  function renderSchedulePage({ embedded } = {}) {
    if (state.companyId === "c2") {
      return embedded ? renderCompanyEmpty() : pageHead("排班工作台", "当前公司暂无考勤数据") + renderCompanyEmpty();
    }
    return previewGuard(() => {
      const stats = Data.monthStats(db, state.month);
      const conflictList = Data.conflicts(db, state.month);
      const actions = `<button class="btn btn-primary btn-sm" data-action="open-plan-editor">${icon(
        "plus",
      )} 新建方案</button>`;
      const head = embedded
        ? ""
        : pageHead(
            "排班工作台",
            "按「方案视图」看一张方案怎么排，或按「员工明细」看一个人这个月怎么上。方案保存即展开为员工日明细；人工例外永远优先。",
            actions,
          );
      if (!companyPlans().length) {
        return `${head}${renderNoPlanState()}`;
      }
      return `${head}
        ${embedded ? "" : renderMonthBar()}
        ${renderScheduleBanners()}
        ${renderScheduleKpis(stats, conflictList)}
        <div class="schedule-layout">
          <aside class="schedule-side">
            ${renderPlanList()}
            ${state.scheduleView === "employee" ? renderEmployeeList() : renderScopeTree()}
          </aside>
          <section class="schedule-main">
            ${renderScheduleToolbar(conflictList)}
            ${renderCalendar()}
            ${state.scheduleView === "employee" ? renderEmployeeCalendarSummary() : renderCalendarHint()}
          </section>
        </div>`;
    });
  }

  function renderNoPlanState() {
    return `<div class="empty" style="padding:56px 20px">
      <div class="empty-icon">${icon("calendar")}</div>
      <h3>${monthCN(state.month)} 还没有排班方案</h3>
      <p>方案按「公司 + 月份 + 范围」创建，保存时展开为员工日明细。可以从上月复制，也可以新建一张方案。</p>
      <div class="inline" style="justify-content:center">
        <button class="btn btn-primary" data-action="open-plan-editor">${icon("plus")} 新建方案</button>
        <button class="btn btn-outline" data-action="open-copy-month">${icon("copy")} 从 9 月复制</button>
      </div>
    </div>`;
  }

  function renderScheduleBanners() {
    const ms = monthState();
    const pending = db.pendingEmployees.filter((id) => getEmployee(id));
    const conflictList = Data.conflicts(db, state.month);
    const parts = [];
    if (ms.status === "locked") {
      parts.push(`<div class="banner danger">${icon(
        "lock",
      )}<div><strong>本月已锁定。</strong>排班、导入与人工例外均只读。解锁需在「考勤结果」填写理由，并重新计算。</div></div>`);
    } else if (ms.status === "confirmed") {
      parts.push(`<div class="banner info">${icon(
        "shield",
      )}<div><strong>本月已确认。</strong>修改排班或人工例外前，需要先在「考勤结果」撤销确认。</div></div>`);
    }
    if (ms.isStale && ms.status !== "locked") {
      parts.push(`<div class="banner warn">${icon(
        "alert",
      )}<div><strong>当前结果已过期。</strong>排班或导入数据在本月计算后发生变化；结果仍可查看，重算后生效。</div><div class="banner-actions"><button class="btn btn-sm btn-outline" data-action="nav" data-page="results">去重算</button></div></div>`);
    }
    if (pending.length) {
      const names = pending
        .map((id) => {
          const emp = getEmployee(id);
          return `${esc(emp.name)}（${emp.hireDate} 入职）`;
        })
        .join("、");
      parts.push(`<div class="banner info">${icon(
        "user",
      )}<div><strong>${pending.length} 名员工尚未同步进排班：</strong>${names}。同步前这些日期会显示为未排班。</div><div class="banner-actions"><button class="btn btn-sm btn-outline" data-action="open-sync-people">同步人员</button></div></div>`);
    }
    if (conflictList.length) {
      parts.push(`<div class="banner warn">${icon(
        "alert",
      )}<div><strong>${conflictList.length} 处同一天班次时间重叠。</strong>系统只警告、不阻止保存；请确认是否需要调整。</div><div class="banner-actions"><button class="btn btn-sm btn-outline" data-action="open-conflicts">查看冲突</button></div></div>`);
    }
    return parts.join("");
  }

  function renderScheduleKpis(stats, conflictList) {
    const pending = db.pendingEmployees.length;
    return `<div class="kpi-grid">
      <div class="kpi">
        <div class="kpi-label">${icon("users")} 在册员工</div>
        <div class="kpi-value">${stats.employees}<small>人</small></div>
        <div class="kpi-sub">本月在职 / 试用期</div>
      </div>
      <div class="kpi primary">
        <div class="kpi-label">${icon("calendar")} 已排班人日</div>
        <div class="kpi-value">${stats.workDays}<small>人日</small></div>
        <div class="kpi-sub">含人工例外 ${stats.manual} 条</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">${icon("edit")} 人工例外</div>
        <div class="kpi-value">${stats.manual}<small>条</small></div>
        <div class="kpi-sub">方案展开永不覆盖</div>
      </div>
      <div class="kpi ${conflictList.length ? "warn" : ""}">
        <div class="kpi-label">${icon("alert")} 排班冲突</div>
        <div class="kpi-value">${conflictList.length}<small>处</small></div>
        <div class="kpi-sub">时间重叠，仅警告</div>
      </div>
      <div class="kpi ${stats.unscheduled ? "warn" : ""}">
        <div class="kpi-label">${icon("clock")} 未排班人日</div>
        <div class="kpi-value">${stats.unscheduled}<small>人日</small></div>
        <div class="kpi-sub">${pending ? `待同步 ${pending} 人` : "无方案覆盖的日期"}</div>
      </div>
    </div>`;
  }

  function renderPlanList() {
    const plans = companyPlans();
    return `<div class="panel">
      <div class="panel-head">
        <div><h3>排班方案</h3><div class="sub">${plans.length} 张启用方案</div></div>
        <button class="btn btn-sm btn-ghost" data-action="open-plan-editor">${icon("plus")} 新建</button>
      </div>
      <div class="panel-body tight">
        <div class="plan-list">
          ${renderAllPlanCard()}
          ${plans.map((plan) => renderPlanCard(plan)).join("")}
        </div>
      </div>
    </div>`;
  }

  function renderAllPlanCard() {
    return `<div class="plan-card ${state.selectedPlanId === "all" ? "active" : ""}" role="button" tabindex="0" data-action="select-plan" data-id="all">
      <div class="plan-card-top">
        <div>
          <div class="plan-name">全部方案 · 合并视图</div>
          <div class="plan-meta">按精确度解析后的员工日排班：员工 &gt; 岗位 &gt; 部门 &gt; 全公司</div>
        </div>
        <span class="plan-coverage">${activeEmployees().length} 人</span>
      </div>
      <div class="plan-badges">
        <span class="badge badge-blue">合并</span>
        <span class="badge badge-gray">含人工例外</span>
      </div>
    </div>`;
  }

  function renderPlanCard(plan) {
    const coverage = Data.planCoverage(db, state.month, plan.id);
    const scope = planScopeLabel(plan);
    const pattern = Object.entries(
      Object.values(plan.weekdays)
        .flat()
        .reduce((acc, code) => {
          acc[code] = (acc[code] || 0) + 1;
          return acc;
        }, {}),
    )
      .map(([code, n]) => `${getShift(code)?.name || code} ×${n}`)
      .join(" · ");
    return `<div class="plan-card ${state.selectedPlanId === plan.id ? "active" : ""}" role="button" tabindex="0" data-action="select-plan" data-id="${plan.id}">
      <div class="plan-card-top">
        <div style="min-width:0">
          <div class="plan-name">${esc(plan.name)}</div>
          <div class="plan-meta">${esc(scope)} · ${planSpecificityLabel(plan)}方案</div>
        </div>
        <span class="plan-coverage">覆盖 ${coverage} 人</span>
      </div>
      <div class="plan-badges">
        <span class="badge badge-green">启用</span>
        <span class="badge badge-gray">${esc(pattern)}</span>
      </div>
      <div class="inline" style="margin-top:6px">
        <button class="btn btn-ghost btn-sm" data-action="open-plan-editor" data-id="${plan.id}">${icon("edit")} 编辑</button>
        <button class="btn btn-ghost btn-sm" data-action="open-plan-day" data-id="${plan.id}" data-date="${state.month}-01">${icon("calendar")} 按日编辑</button>
      </div>
    </div>`;
  }

  function deptDepth(dept) {
    let depth = 0;
    let cur = dept;
    while (cur && cur.parentId) {
      depth += 1;
      cur = Data.getDept(db, cur.parentId);
    }
    return depth;
  }

  function renderScopeTree() {
    const depts = db.departments
      .filter((d) => d.companyId === state.companyId)
      .sort((a, b) => Data.deptPath(db, a.id).localeCompare(Data.deptPath(db, b.id)));
    const selectedDept = state.scopeFilter.startsWith("dept:")
      ? state.scopeFilter.slice(5)
      : null;
    const selectedEmp = state.selectedEmployeeId;
    const empCount = (deptId) => {
      const ids = new Set(Data.deptDescendants(db, deptId));
      return activeEmployees().filter((e) => ids.has(e.deptId)).length;
    };
    return `<div class="panel">
      <div class="panel-head"><div><h3>排班范围</h3><div class="sub">点击部门过滤月历；点击员工查看个人月历</div></div></div>
      <div class="panel-body tight">
        <div class="scope-tree">
          <button class="scope-row ${state.scopeFilter === "all" ? "active" : ""}" data-action="select-scope" data-scope="all">
            ${icon("building", "scope-caret")}<span class="scope-name">全公司</span><span class="scope-count">${activeEmployees().length}</span>
          </button>
          ${depts
            .map((dept) => {
              const depth = deptDepth(dept);
              return `<button class="scope-row scope-indent-${Math.min(depth, 2)} ${
                selectedDept === dept.id ? "active" : ""
              }" data-action="select-scope" data-scope="dept:${dept.id}">
                <span class="scope-caret placeholder"></span><span class="scope-name">${esc(dept.name)}</span><span class="scope-count">${empCount(
                  dept.id,
                )}</span>
              </button>`;
            })
            .join("")}
          ${
            selectedDept
              ? activeEmployees()
                  .filter((e) =>
                    new Set(Data.deptDescendants(db, selectedDept)).has(e.deptId),
                  )
                  .map(
                    (emp) => `<button class="scope-row scope-indent-2 ${
                      selectedEmp === emp.id ? "active" : ""
                    }" data-action="select-employee" data-employee="${emp.id}">
                      <span class="scope-caret placeholder"></span><span class="scope-name">${esc(
                        emp.name,
                      )}</span><span class="scope-count">${esc(emp.no)}</span>
                    </button>`,
                  )
                  .join("")
              : ""
          }
        </div>
        <div class="hint" style="padding:8px 6px 0">
          ${state.selectedPlanId === "all" ? "当前为合并视图，显示所有方案解析后的结果。" : "当前为单方案视图，日历显示方案模式；点击日期可编辑该日班次。"}
        </div>
      </div>
    </div>`;
  }

  function renderEmployeeList() {
    const search = (state.employeeSearch || "").trim().toLowerCase();
    let list = employeeListEmployees();
    if (search) {
      list = list.filter(
        (e) =>
          e.name.toLowerCase().includes(search) ||
          e.no.toLowerCase().includes(search),
      );
    }
    return `<div class="panel">
      <div class="panel-head">
        <div><h3>员工</h3><div class="sub">${list.length} 人 · 点击查看个人月历</div></div>
      </div>
      <div class="panel-body tight">
        <div class="search-compact" style="margin-bottom:6px">
          ${icon("search")}
          <input class="input" data-input="employee-search" value="${esc(
            state.employeeSearch || "",
          )}" placeholder="搜索姓名或工号" style="width:100%;height:30px" aria-label="搜索员工" />
        </div>
        <div class="employee-list">
          ${
            list.length
              ? list
                  .map((emp) => {
                    const manual = manualCountFor(emp.id);
                    const pending = db.pendingEmployees.includes(emp.id);
                    const resultCount = resultsForMonth().filter(
                      (r) => r.employeeId === emp.id && isExceptionResult(r),
                    ).length;
                    return `<button class="employee-row ${
                      state.selectedEmployeeId === emp.id ? "active" : ""
                    }" data-action="select-employee" data-employee="${emp.id}">
                      <span class="emp-avatar">${esc(emp.name.slice(0, 1))}</span>
                      <span class="emp-meta">
                        <span class="emp-name">${esc(emp.name)} <span class="muted small">${esc(
                          emp.no,
                        )}</span></span>
                        <span class="emp-sub">${esc(Data.deptPath(db, emp.deptId))}</span>
                      </span>
                      <span class="emp-tags">
                        ${pending ? `<span class="emp-tag pending">待同步</span>` : ""}
                        ${manual ? `<span class="emp-tag exception">例外 ${manual}</span>` : ""}
                        ${resultCount ? `<span class="emp-tag">异常 ${resultCount}</span>` : ""}
                      </span>
                    </button>`;
                  })
                  .join("")
              : `<div class="empty" style="padding:20px 8px"><div class="empty-icon">${icon(
                  "search",
                )}</div><h3 style="font-size:12px">没有匹配的员工</h3></div>`
          }
        </div>
      </div>
    </div>`;
  }

  function renderScheduleToolbar(conflictList) {
    const editable = isEditable();
    const planMode = state.scheduleView === "plan";
    return `<div class="schedule-toolbar">
      <div class="segmented" role="tablist" aria-label="排班视图">
        <button class="${planMode ? "active" : ""}" data-action="schedule-view" data-view="plan">${icon(
          "grid",
        )} 方案视图</button>
        <button class="${!planMode ? "active" : ""}" data-action="schedule-view" data-view="employee">${icon(
          "users",
        )} 员工明细</button>
      </div>
      ${
        !planMode
          ? `<select class="select" data-select="employee-dept" aria-label="按部门筛选" style="height:32px">
              ${deptOptions()
                .map(
                  (o) =>
                    `<option value="${o.value}" ${
                      (state.scopeFilter === "all" && o.value === "all") ||
                      (state.scopeFilter === `dept:${o.value}` && o.value !== "all")
                        ? "selected"
                        : ""
                    }>${esc(o.label)}</option>`,
                )
                .join("")}
            </select>`
          : `<span class="sub">${
              state.selectedPlanId === "all"
                ? "合并视图：显示每天谁上班"
                : `方案模式：${esc(selectedPlan()?.name || "")}`
            }</span>`
      }
      <span class="spacer"></span>
      <button class="btn btn-outline btn-sm" data-action="open-batch-fill" ${
        editable ? "" : "disabled title=\"本月已确认或锁定\""
      }>${icon("layers")} 批量填充</button>
      <button class="btn btn-outline btn-sm" data-action="open-copy-month" ${
        state.month === "2026-09" && editable ? "" : "disabled"
      }>${icon("copy")} 复制下月</button>
      <button class="btn btn-outline btn-sm" data-action="open-sync-people" ${
        editable ? "" : "disabled title=\"本月已确认或锁定\""
      }>${icon("sync")} 同步人员</button>
      <button class="btn btn-outline btn-sm" data-action="open-conflicts">${icon(
        "alert",
      )} 冲突 ${conflictList.length}</button>
    </div>`;
  }

  function renderCalendar() {
    const month = state.month;
    const dates = Data.dateList(month);
    const lead = Data.weekdayIndex(`${month}-01`);
    const cells = [];
    for (let i = 0; i < lead; i++) {
      cells.push(`<button class="cal-cell empty" disabled aria-hidden="true"></button>`);
    }
    for (const date of dates) cells.push(renderCalendarCell(date));
    while (cells.length % 7 !== 0) {
      cells.push(`<button class="cal-cell empty" disabled aria-hidden="true"></button>`);
    }
    return `<div class="calendar-wrap">
      <div class="cal-head">${WEEKDAYS.map(
        (d) => `<div class="cal-dow">周${d}</div>`,
      ).join("")}</div>
      <div class="calendar-scroll"><div class="calendar">${cells.join("")}</div></div>
      <div style="padding:9px 12px;border-top:1px solid var(--border)">${renderCalendarLegend()}</div>
    </div>`;
  }

  function renderCalendarCell(date) {
    const dt = Data.dayType(db, date);
    const holiday = Data.holidayOf(db, date);
    const cls = [
      "cal-cell",
      dt === "weekend" ? "weekend" : "",
      holiday?.dayType === "holiday" ? "holiday" : "",
      holiday?.dayType === "adjusted_workday" ? "adjusted" : "",
      state.selectedDate === date ? "selected" : "",
    ]
      .filter(Boolean)
      .join(" ");
    const action =
      state.scheduleView === "employee"
        ? "open-exception"
        : state.selectedPlanId === "all"
          ? "open-day-sheet"
          : "open-plan-day";
    const dataEmployee =
      state.scheduleView === "employee"
        ? ` data-employee="${state.selectedEmployeeId}"`
        : "";
    const content =
      state.scheduleView === "employee"
        ? renderEmployeeCellContent(date)
        : state.selectedPlanId === "all"
          ? renderMergedCellContent(date)
          : renderPlanCellContent(date);
    return `<button class="${cls}" data-action="${action}" data-date="${date}"${dataEmployee} aria-label="${dateCN(
      date,
    )} ${Data.dayTypeLabel(db, date)}">
      <div class="cal-date-row">
        <span class="cal-date">${dayNum(date)}</span>
        <span class="cal-dow-mobile">周${WEEKDAYS[Data.weekdayIndex(date)]}</span>
        ${dayTypeBadge(date)}
      </div>
      ${content}
    </button>`;
  }

  function renderMergedCellContent(date) {
    const employees = scopedEmployees();
    const counts = {};
    let rest = 0;
    let unscheduled = 0;
    let manual = 0;
    for (const emp of employees) {
      const entry = Data.rosterEntry(db, state.month, emp.id, date);
      if (!entry) {
        unscheduled += 1;
        continue;
      }
      if (entry.state === "rest") {
        rest += 1;
        continue;
      }
      for (const code of entry.shifts) counts[code] = (counts[code] || 0) + 1;
      if (entry.source === "manual") manual += 1;
    }
    const ordered = Object.keys(counts).sort(
      (a, b) => Data.toMinutes(getShift(a)?.start || "00:00") - Data.toMinutes(getShift(b)?.start || "00:00"),
    );
    const conflictCount = Data.conflicts(db, state.month).filter((c) => c.date === date).length;
    const chips = ordered
      .slice(0, 3)
      .map(
        (code) =>
          `<div class="cal-chip-row">${shiftChip(code)}<span class="cal-count">${counts[code]}人</span></div>`,
      )
      .join("");
    return `<div class="cal-chips">
        ${chips || `<span class="cal-empty-hint">${rest ? "休息" : "无人排班"}</span>`}
        ${ordered.length > 3 ? `<span class="cal-chip-more">+${ordered.length - 3} 个班次</span>` : ""}
      </div>
      <div class="cal-foot">
        <span>${manual ? `<span class="cal-exception">${icon("edit")}例外 ${manual}</span>` : ""}</span>
        <span>${conflictCount ? `<span class="cal-warning">${icon("alert")}冲突 ${conflictCount}</span>` : unscheduled ? `未排班 ${unscheduled}` : ""}</span>
      </div>`;
  }

  function renderPlanCellContent(date) {
    const plan = selectedPlan();
    if (!plan) return "";
    const shifts = Data.planShiftsForDate(db, plan, date);
    const employees = planEmployeesFor(plan);
    const manual = Object.values(db.exceptions).filter(
      (ex) =>
        Data.monthOf(ex.date) === state.month &&
        ex.date === date &&
        employees.some((e) => e.id === ex.employeeId),
    ).length;
    return `<div class="cal-chips">
        ${
          shifts.length
            ? shifts.map((code) => `<div class="cal-chip-row">${shiftChip(code)}</div>`).join("")
            : `<span class="cal-empty-hint">方案休息</span>`
        }
      </div>
      <div class="cal-foot">
        <span>${manual ? `<span class="cal-exception">${icon("edit")}例外 ${manual}</span>` : ""}</span>
        <span>${employees.length} 人范围</span>
      </div>`;
  }

  function renderEmployeeCellContent(date) {
    const emp = getEmployee(state.selectedEmployeeId);
    if (!emp) return "";
    const entry = Data.rosterEntry(db, state.month, emp.id, date);
    const result = resultsForMonth().find(
      (r) => r.employeeId === emp.id && r.date === date,
    );
    const pending = db.pendingEmployees.includes(emp.id);
    return `<div class="cal-chips">
        ${
          entry
            ? entry.state === "work"
              ? entry.shifts
                  .map((code) => `<div class="cal-chip-row">${shiftChip(code)}</div>`)
                  .join("")
              : `<span class="cal-empty-hint">休息</span>`
            : `<span class="cal-empty-hint">${pending ? "待同步" : "未排班"}</span>`
        }
      </div>
      <div class="cal-foot">
        <span>${entry?.source === "manual" ? `<span class="cal-exception">${icon("edit")}人工例外</span>` : ""}</span>
        <span>${result ? statusBadge(result.dayStatus) : ""}</span>
      </div>`;
  }

  function renderCalendarLegend() {
    const codes = Array.from(
      new Set(companyPlans().flatMap((p) => Object.values(p.weekdays).flat())),
    );
    return `<div class="legend">
      ${codes
        .map(
          (code) =>
            `<span class="legend-item">${shiftDot(code)}${esc(getShift(code)?.name || code)}</span>`,
        )
        .join("")}
      <span class="legend-item"><span class="legend-dot" style="background:var(--danger-soft);border:1px solid var(--danger-border)"></span>法定节假日</span>
      <span class="legend-item"><span class="legend-dot" style="background:var(--primary-soft);border:1px solid var(--primary-soft-2)"></span>调休上班</span>
      <span class="legend-item">${icon("edit")} 人工例外</span>
      <span class="legend-item">${icon("alert")} 时间重叠</span>
    </div>`;
  }

  function renderCalendarHint() {
    return `<div class="summary-strip">
      <span><strong>提示：</strong>${
        state.scheduleView === "plan"
          ? "点击日期查看当天谁上班；切换左侧方案可编辑方案模式。"
          : `正在查看 ${esc(getEmployee(state.selectedEmployeeId)?.name || "")} 的个人月历；点击日期新建或修改人工例外。`
      }</span>
      <span class="spacer"></span>
      <button class="btn btn-sm btn-outline" data-action="nav" data-page="results">${icon(
        "inbox",
      )} 查看考勤结果</button>
    </div>`;
  }

  function renderEmployeeCalendarSummary() {
    const emp = getEmployee(state.selectedEmployeeId);
    if (!emp) return "";
    const entries = Object.entries(db.roster[state.month]?.[emp.id] || {});
    const work = entries.filter(([, e]) => e.state === "work").length;
    const rest = entries.filter(([, e]) => e.state === "rest").length;
    const manual = entries.filter(([, e]) => e.source === "manual").length;
    const summary = summariesForMonth().find((s) => s.employeeId === emp.id);
    const exCount = resultsForMonth().filter(
      (r) => r.employeeId === emp.id && isExceptionResult(r),
    ).length;
    const pending = db.pendingEmployees.includes(emp.id);
    return `<div class="summary-strip">
      <span><strong>${esc(emp.name)}</strong> · ${esc(Data.deptPath(db, emp.deptId))} · 入职 ${esc(
        emp.hireDate,
      )}</span>
      <span class="sep"></span>
      <span>上班 <strong>${work}</strong> 天</span>
      <span>休息 <strong>${rest}</strong> 天</span>
      <span>人工例外 <strong>${manual}</strong> 条</span>
      <span>异常 <strong>${exCount}</strong> 条</span>
      ${
        summary
          ? `<span class="sep"></span><span>出勤 <strong>${summary.weekdayAttended + summary.weekendAttended}</strong> 天 · 加班 <strong>${(
              summary.otWeekdayHours +
              summary.otWeekendHours +
              summary.otHolidayHours
            ).toFixed(2)}</strong> h · 扣款 <strong class="danger-text">${money(
              summary.attendanceDeduct,
            )}</strong></span>`
          : ""
      }
      ${pending ? `<span class="badge badge-orange">待同步</span>` : ""}
      <span class="spacer"></span>
      <button class="btn btn-sm btn-outline" data-action="open-exception" data-employee="${emp.id}" data-date="${
        state.selectedDate || `${state.month}-01`
      }">${icon("edit")} 新建例外</button>
      <button class="btn btn-sm btn-outline" data-action="goto-employee-results" data-employee="${emp.id}">${icon(
        "inbox",
      )} 查看结果</button>
    </div>`;
  }

  function renderMiniCalendar(month, options = {}) {
    const big = options.big === true;
    const dates = Data.dateList(month);
    const lead = Data.weekdayIndex(`${month}-01`);
    const cells = [];
    for (let i = 0; i < lead; i++) cells.push(`<span></span>`);
    for (const date of dates) {
      const hasWork = Object.values(db.roster[month] || {}).some(
        (per) => per[date] && per[date].state === "work",
      );
      const holiday = Data.holidayOf(db, date);
      const cls = [
        big ? "mini-day" : "rail-day",
        hasWork ? "has-work" : "",
        holiday?.dayType === "holiday" ? "holiday" : "",
        holiday?.dayType === "adjusted_workday" ? "adjusted" : "",
        options.useSelected !== false && state.selectedDate === date ? "selected" : "",
      ]
        .filter(Boolean)
        .join(" ");
      cells.push(
        `<button class="${cls}" data-action="select-mini-date" data-date="${date}" title="${dateCN(
          date,
        )}${holiday ? ` · ${esc(holiday.name)}` : ""}${hasWork ? " · 有排班" : ""}">${dayNum(
          date,
        )}</button>`,
      );
    }
    return `<div class="${big ? "mini-calendar" : "rail-calendar"}">
      ${WEEKDAYS.map((d) => `<div class="${big ? "mini-dow" : "rail-dow"}">${d}</div>`).join("")}
      ${cells.join("")}
    </div>`;
  }

  /* ================================================================ shells B / C */

  function pageLabel(page = state.page) {
    return (
      {
        schedule: "排班工作台",
        import: "导入中心",
        results: "考勤结果",
        rules: "规则与节假日",
        shifts: "班次",
        cockpit: "考勤驾驶舱",
      }[page] || page
    );
  }

  function pageSub(page = state.page) {
    return (
      {
        schedule: "按月维护「谁在哪天上什么班」，方案保存即展开为员工日明细。",
        import: "上传或粘贴 → 列映射 → 预览校验 → 提交生效；同一月份与类型覆盖式刷新。",
        results: "异常优先的日结果与月汇总；从排班、打卡、OA 到结果四方对照。",
        rules: "公司默认规则 + 方案覆盖；节假日日历与变更影响提示。",
        shifts: "公司级可复用的班次模板；展开时快照进排班明细。",
        cockpit: "以异常和待办为入口，快速进入排班、导入与月结。",
      }[page] || ""
    );
  }

  function renderWorkbench(content) {
    const tabs = [
      { page: "schedule", label: "排班", icon: "calendar" },
      { page: "import", label: "导入", icon: "upload", badge: importAttention() },
      {
        page: "results",
        label: "结果",
        icon: "inbox",
        badge: exceptionResults().length,
      },
      { page: "rules", label: "规则", icon: "sliders" },
    ];
    const stats = Data.monthStats(db, state.month);
    const exCount = exceptionResults().length;
    const ms = monthState();
    return `<div class="workbench-head">
      <div class="workbench-head-top">
        <div>
          <div class="workbench-title">考勤工作台</div>
          <div class="sub">${esc(currentCompany().name)} · 月份与公司上下文在页签间保持</div>
        </div>
        ${monthStatusBadge()}
        <span class="spacer"></span>
        <div class="month-nav">
          <button data-action="month-prev" aria-label="上一个月" ${
            state.month === "2026-09" ? "disabled" : ""
          }>${icon("chevron-left")}</button>
          <strong>${monthCN(state.month)}</strong>
          <button data-action="month-next" aria-label="下一个月" ${
            state.month === "2026-10" ? "disabled" : ""
          }>${icon("chevron-right")}</button>
        </div>
      </div>
      <div class="workbench-tabs" role="tablist" aria-label="考勤工作台页签">
        ${tabs
          .map(
            (tab) =>
              `<button class="workbench-tab ${
                state.page === tab.page ? "active" : ""
              }" data-action="nav" data-page="${tab.page}" role="tab" aria-selected="${
                state.page === tab.page ? "true" : "false"
              }">${icon(tab.icon)}${tab.label}${
                tab.badge ? `<span class="tab-count">${tab.badge}</span>` : ""
              }</button>`,
          )
          .join("")}
      </div>
    </div>
    <div class="workbench-body">
      <aside class="workbench-rail">
        <div class="rail-card">
          <h4>${monthCN(state.month)}</h4>
          ${renderMiniCalendar(state.month)}
          <div class="rail-stat" style="margin-top:7px"><span>已排班人日</span><strong>${stats.workDays}</strong></div>
          <div class="rail-stat"><span>人工例外</span><strong>${stats.manual}</strong></div>
          <div class="rail-stat"><span>未排班人日</span><strong>${stats.unscheduled}</strong></div>
          <div class="rail-stat"><span>待处理异常</span><strong>${exCount}</strong></div>
        </div>
        <div class="rail-card">
          <h4>快捷操作</h4>
          <div class="rail-actions">
            <button class="btn btn-sm btn-ghost" data-action="open-sync-people" ${
              isEditable() ? "" : "disabled"
            }>${icon("sync")} 同步人员</button>
            <button class="btn btn-sm btn-ghost" data-action="open-copy-month" ${
              state.month === "2026-09" && isEditable() ? "" : "disabled"
            }>${icon("copy")} 复制下月</button>
            <button class="btn btn-sm btn-ghost" data-action="open-shifts-overlay">${icon(
              "clock",
            )} 班次管理</button>
            <button class="btn btn-sm btn-ghost" data-action="open-export">${icon(
              "download",
            )} 导出结果</button>
          </div>
        </div>
        <div class="rail-card">
          <h4>本月状态</h4>
          <div class="rail-stat"><span>状态</span><strong>${monthStatusBadge()}</strong></div>
          <div class="rail-stat"><span>计算时间</span><strong>${esc(
            ms.calculatedAt || "—",
          )}</strong></div>
          <div class="rail-stat"><span>导入批次</span><strong>${committedBatches().length} / 4</strong></div>
        </div>
      </aside>
      <section>${content}</section>
    </div>`;
  }

  function renderCMode(content) {
    return `<div class="cockpit-hero" style="padding:14px 18px;margin-bottom:14px;align-items:center">
      <div class="inline" style="min-width:0">
        <button class="btn btn-outline btn-sm" data-action="nav" data-page="cockpit">${icon(
          "arrow-left",
        )} 返回驾驶舱</button>
        <div>
          <h1 style="font-size:18px;margin:0">${esc(pageLabel())}</h1>
          <p style="margin:2px 0 0">${esc(pageSub())}</p>
        </div>
      </div>
      <div class="inline">
        <div class="month-nav">
          <button data-action="month-prev" aria-label="上一个月" ${
            state.month === "2026-09" ? "disabled" : ""
          }>${icon("chevron-left")}</button>
          <strong>${monthCN(state.month)}</strong>
          <button data-action="month-next" aria-label="下一个月" ${
            state.month === "2026-10" ? "disabled" : ""
          }>${icon("chevron-right")}</button>
        </div>
        ${monthStatusBadge()}
      </div>
    </div>
    ${content}`;
  }

  /* ================================================================ cockpit C */

  function renderCockpitPage() {
    if (state.companyId === "c2") {
      return pageHead("考勤驾驶舱", "当前公司暂无考勤数据") + renderCompanyEmpty();
    }
    return previewGuard(() => {
      const stats = Data.monthStats(db, state.month);
      const exList = exceptionResults();
      const summaries = summariesForMonth();
      const fullDays = summaries.reduce(
        (sum, s) => sum + s.weekdayFull + s.weekendFull,
        0,
      );
      const attended = summaries.reduce(
        (sum, s) => sum + s.weekdayAttended + s.weekendAttended,
        0,
      );
      const otHours = summaries.reduce(
        (sum, s) =>
          sum +
          s.otWeekdayHours +
          s.otWeekendHours +
          s.otHolidayHours,
        0,
      );
      const recent = (db.calcRuns[state.month] || []).slice(-3).reverse();
      return `<div class="cockpit-hero">
        <div>
          <div class="inline" style="margin-bottom:6px">${monthStatusBadge()}<span class="badge badge-blue">${esc(
            currentCompany().name,
          )}</span></div>
          <h1>${monthCN(state.month)}考勤驾驶舱</h1>
          <p>从异常与待办出发：先看需要处理什么，再进入排班、导入或月结。${
            monthState().isStale ? "当前结果已过期，重算后生效。" : ""
          }</p>
        </div>
        <div class="cockpit-actions">
          <button class="btn btn-outline" data-action="nav" data-page="schedule">${icon(
            "calendar",
          )} 排班工作台</button>
          <button class="btn btn-outline" data-action="open-import-wizard">${icon(
            "upload",
          )} 新建导入</button>
          <button class="btn btn-primary" data-action="open-recalc">${icon(
            "refresh",
          )} 重新计算</button>
        </div>
      </div>
      <div class="kpi-grid">
        <div class="kpi">
          <div class="kpi-label">${icon("users")} 在册员工</div>
          <div class="kpi-value">${stats.employees}<small>人</small></div>
          <div class="kpi-sub">在职 / 试用期</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">${icon("calendar")} 应出勤人日</div>
          <div class="kpi-value">${fullDays}<small>人日</small></div>
          <div class="kpi-sub">工作日 + 周末排班</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">${icon("check-circle")} 实际出勤</div>
          <div class="kpi-value">${attended.toFixed(1)}<small>人日</small></div>
          <div class="kpi-sub">含半天与未排班出勤</div>
        </div>
        <div class="kpi ${exList.length ? "danger" : ""}">
          <div class="kpi-label">${icon("inbox")} 异常待处理</div>
          <div class="kpi-value">${exList.length}<small>条</small></div>
          <div class="kpi-sub">旷工 / 缺卡 / 迟到 / 早退</div>
        </div>
        <div class="kpi">
          <div class="kpi-label">${icon("timer")} 加班合计</div>
          <div class="kpi-value">${otHours.toFixed(2)}<small>h</small></div>
          <div class="kpi-sub">三类加班抵扣后净值</div>
        </div>
      </div>
      <div class="cockpit-grid">
        <div class="stack">
          <div class="panel">
            <div class="panel-head">
              <div><h3>异常收件箱</h3><div class="sub">默认只看需要处理的日结果；点击查看四方对照</div></div>
              <button class="btn btn-sm btn-outline" data-action="nav" data-page="results">查看全部 ${icon(
                "arrow-right",
              )}</button>
            </div>
            <div class="inbox">
              ${
                exList.length
                  ? exList
                      .slice(0, 8)
                      .map((r) => {
                        const emp = getEmployee(r.employeeId);
                        const meta = statusMeta(r.dayStatus);
                        return `<button class="inbox-row" data-action="open-result" data-employee="${
                          r.employeeId
                        }" data-date="${r.date}">
                          <span class="emp-avatar">${esc((emp?.name || "").slice(0, 1))}</span>
                          <span class="inbox-main">
                            <span class="inbox-title">${esc(emp?.name || r.employeeId)} · ${dateCN(
                              r.date,
                            )} ${statusBadge(r.dayStatus)}</span>
                            <span class="inbox-sub">${esc(
                              Data.deptPath(db, emp?.deptId) || "",
                            )} · ${r.dayFlags.map(flagsLabel).slice(0, 3).join("、") || meta.label}</span>
                          </span>
                          <span class="inbox-side">${icon("chevron-right")}</span>
                        </button>`;
                      })
                      .join("")
                  : `<div class="empty" style="padding:28px 16px"><div class="empty-icon">${icon(
                      "check-circle",
                    )}</div><h3 style="font-size:12px">没有待处理异常</h3><p style="font-size:10.5px">所有日结果均为正常或休息。</p></div>`
              }
            </div>
          </div>
          <div class="panel">
            <div class="panel-head"><div><h3>快捷操作</h3><div class="sub">按任务进入，而不是按模块找页面</div></div></div>
            <div class="panel-body">
              <div class="quick-grid">
                <button class="quick-card" data-action="open-import-wizard"><span class="quick-icon">${icon(
                  "upload",
                )}</span><strong>导入打卡 / OA</strong><span>上传或粘贴，预览后覆盖本月批次</span></button>
                <button class="quick-card" data-action="nav" data-page="schedule"><span class="quick-icon">${icon(
                  "calendar",
                )}</span><strong>排班工作台</strong><span>方案视图 / 员工明细，人工例外优先</span></button>
                <button class="quick-card" data-action="nav" data-page="results"><span class="quick-icon">${icon(
                  "inbox",
                )}</span><strong>考勤结果</strong><span>异常收件箱、四方对照、月结与导出</span></button>
                <button class="quick-card" data-action="nav" data-page="rules"><span class="quick-icon">${icon(
                  "sliders",
                )}</span><strong>规则与节假日</strong><span>公司默认 + 方案覆盖，变更影响提示</span></button>
              </div>
            </div>
          </div>
        </div>
        <div class="stack">
          <div class="panel">
            <div class="panel-head"><div><h3>${monthCN(state.month)}</h3><div class="sub">${esc(
              currentCompany().name,
            )}</div></div>${monthStatusBadge()}</div>
            <div class="panel-body">
              ${renderMiniCalendar(state.month, { big: true })}
              <div style="margin-top:9px">
                <div class="rail-stat"><span>已排班人日</span><strong>${stats.workDays}</strong></div>
                <div class="rail-stat"><span>人工例外</span><strong>${stats.manual}</strong></div>
                <div class="rail-stat"><span>未排班人日</span><strong>${stats.unscheduled}</strong></div>
                <div class="rail-stat"><span>导入批次</span><strong>${committedBatches().length} / 4</strong></div>
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-head"><div><h3>导入批次</h3><div class="sub">只有生效批次参与计算</div></div></div>
            <div class="panel-body tight">
              ${["punch", "trip", "ot", "leave"]
                .map((type) => {
                  const batch = committedBatch(type);
                  const label = db.importSamples[type].label;
                  return `<div class="rail-stat" style="padding:5px 6px"><span>${esc(
                    label,
                  )}</span>${
                    batch
                      ? `<span class="badge badge-green">${batch.valid} 条 · ${esc(
                          batch.committedAt.slice(5, 16),
                        )}</span>`
                      : `<span class="badge badge-gray">未导入</span>`
                  }</div>`;
                })
                .join("")}
            </div>
          </div>
          <div class="panel">
            <div class="panel-head"><div><h3>最近计算</h3><div class="sub">重算需显式触发</div></div></div>
            <div class="calc-run-list">
              ${
                recent.length
                  ? recent
                      .map(
                        (run) => `<div class="calc-run ${run.status === "failed" ? "failed" : ""}">
                          <div class="run-icon">${icon(
                            run.status === "failed" ? "alert" : "check",
                          )}</div>
                          <div class="run-main"><div class="run-title">${esc(
                            run.note || run.trigger,
                          )}</div><div class="run-sub">${esc(
                            run.finishedAt,
                          )} · ${run.employees} 人 · ${run.days} 天</div></div>
                        </div>`,
                      )
                      .join("")
                  : `<div class="empty" style="padding:18px"><p style="font-size:10.5px">本月尚未计算</p></div>`
              }
            </div>
          </div>
        </div>
      </div>`;
    });
  }

  /* placeholder pages are implemented below */

  /* ================================================================ import */

  const IMPORT_TYPES = ["punch", "trip", "ot", "leave"];
  const IMPORT_ICON = { punch: "fingerprint", trip: "map-pin", ot: "timer", leave: "coffee" };

  function batchStatusBadge(status) {
    const map = {
      committed: { label: "生效中", cls: "badge-green" },
      preview: { label: "预览中", cls: "badge-orange" },
      superseded: { label: "已替代", cls: "badge-gray" },
      discarded: { label: "已丢弃", cls: "badge-gray" },
      revoked: { label: "已撤销", cls: "badge-red" },
    };
    const item = map[status] || { label: status, cls: "badge-gray" };
    return `<span class="badge ${item.cls}">${item.label}</span>`;
  }

  function batchesFor(type = state.importType, month = null) {
    return db.importBatches
      .filter(
        (b) =>
          b.companyId === state.companyId &&
          b.dataType === type &&
          (month === null || b.month === month),
      )
      .sort((a, b) => (b.committedAt || b.createdAt || "").localeCompare(a.committedAt || a.createdAt || ""));
  }

  function renderImportPage({ embedded } = {}) {
    if (state.companyId === "c2") {
      return embedded ? renderCompanyEmpty() : pageHead("导入中心", "当前公司暂无导入数据") + renderCompanyEmpty();
    }
    return previewGuard(() => {
      const head = embedded
        ? ""
        : pageHead(
            "导入中心",
            "打卡与三类 OA 申请分开导入；每个「公司 + 月份 + 数据类型」只有一个生效批次，提交即覆盖旧批次。",
            `<button class="btn btn-primary btn-sm" data-action="open-import-wizard">${icon(
              "upload",
            )} 新建导入</button>`,
          );
      const sample = db.importSamples[state.importType];
      const current = committedBatch(state.importType);
      const previews = batchesFor(state.importType).filter((b) => b.status === "preview");
      const history = batchesFor(state.importType).filter((b) => b.status !== "preview");
      return `${head}
        ${embedded ? "" : renderMonthBar()}
        ${renderImportBanners(current, previews)}
        <div class="import-type-tabs">${IMPORT_TYPES.map(
          (type) => renderImportTypeCard(type),
        ).join("")}</div>
        <div class="split-panel" style="grid-template-columns:minmax(0,1.55fr) minmax(300px,1fr)">
          <div class="stack">
            <div class="panel">
              <div class="panel-head">
                <div><h3>当前生效批次 · ${esc(sample.label)}</h3><div class="sub">${monthCN(
                  state.month,
                )} · 计算只读生效批次</div></div>
                <button class="btn btn-sm btn-primary" data-action="open-import-wizard" data-type="${
                  state.importType
                }">${icon("upload")} 新建导入</button>
              </div>
              <div class="panel-body">
                ${
                  current
                    ? renderCurrentBatch(current, sample)
                    : `<div class="empty" style="padding:28px 16px"><div class="empty-icon">${icon(
                        "upload",
                      )}</div><h3 style="font-size:12px">本月还没有生效的${esc(
                        sample.label,
                      )}批次</h3><p style="font-size:10.5px">上传或粘贴文件后先预览；确认无误再提交生效。</p></div>`
                }
              </div>
            </div>
            ${previews.length ? renderPreviewBatchPanel(previews, sample) : ""}
            <div class="panel">
              <div class="panel-head"><div><h3>批次历史</h3><div class="sub">被替代、丢弃与撤销的批次保留元数据，不参与计算</div></div></div>
              <div class="table-wrap">
                <table class="table">
                  <thead><tr><th>文件 / 来源</th><th>状态</th><th>源行</th><th>有效</th><th>跳过</th><th>错误 / 告警</th><th>操作人</th><th>时间</th><th></th></tr></thead>
                  <tbody>
                    ${
                      history.length
                        ? history
                            .map(
                              (batch) => `<tr>
                                <td><div class="cell-strong">${esc(
                                  batch.fileName || "粘贴导入",
                                )}</div><div class="cell-sub">${esc(
                                  batch.fileSize || "文本",
                                )} · ${batch.source === "paste" ? "粘贴" : "上传"}</div></td>
                                <td>${batchStatusBadge(batch.status)}</td>
                                <td>${batch.sourceRows}</td>
                                <td><strong>${batch.valid}</strong></td>
                                <td>${batch.skipped}</td>
                                <td>${batch.errors} / ${batch.warnings}</td>
                                <td>${esc(batch.operator)}</td>
                                <td>${esc(
                                  (batch.committedAt || batch.createdAt || "").slice(5, 16),
                                )}</td>
                                <td class="td-actions"><button class="btn btn-sm btn-ghost" data-action="open-batch-detail" data-id="${
                                  batch.id
                                }">查看</button></td>
                              </tr>`,
                            )
                            .join("")
                        : `<tr><td colspan="9"><div class="empty" style="padding:18px"><p style="font-size:10.5px">暂无历史批次</p></div></td></tr>`
                    }
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="stack">
            ${renderImportRulesCard(sample)}
            ${renderImportMappingCard(sample)}
          </div>
        </div>`;
    });
  }

  function renderImportBanners(current, previews) {
    const ms = monthState();
    const parts = [];
    if (ms.status === "confirmed" || ms.status === "locked") {
      parts.push(`<div class="banner warn">${icon("lock")}<div><strong>本月为「${
        ms.status === "locked" ? "已锁定" : "已确认"
      }」。</strong>仍可预览导入，但不能提交生效；请先在考勤结果撤销确认或解锁。</div></div>`);
    }
    if (previews.length) {
      parts.push(`<div class="banner info">${icon(
        "clock",
      )}<div><strong>${previews.length} 个预览批次待处理。</strong>预览批次 24 小时后过期，不参与计算；可提交、丢弃或查看错误报告。</div></div>`);
    }
    if (!current && !previews.length) {
      parts.push(`<div class="banner">${icon(
        "info",
      )}<div>本月还没有生效批次。导入按「上传 / 粘贴 → 列映射 → 预览校验 → 提交」进行；提交后旧批次被替代。</div></div>`);
    }
    return parts.join("");
  }

  function renderImportTypeCard(type) {
    const sample = db.importSamples[type];
    const current = committedBatch(type);
    const previewCount = batchesFor(type).filter((b) => b.status === "preview").length;
    return `<button class="import-type ${state.importType === type ? "active" : ""}" data-action="select-import-type" data-type="${type}">
      <div class="import-type-top">${icon(
        ["upload", "map-pin", "timer", "coffee"][IMPORT_TYPES.indexOf(type)],
      )} ${esc(sample.label)}</div>
      <div class="import-type-meta">${
        current
          ? `${esc(current.fileName || "粘贴导入")} · ${esc(
              current.committedAt.slice(5, 16),
            )}`
          : "本月未导入"
      }</div>
      <div class="import-type-stats">
        ${
          current
            ? `<span>有效 <strong>${current.valid}</strong></span><span>跳过 <strong>${current.skipped}</strong></span><span>告警 <strong>${current.warnings}</strong></span>`
            : `<span>样例 ${sample.stats.sourceRows} 行</span>`
        }
        ${previewCount ? `<span class="badge badge-orange">预览 ${previewCount}</span>` : ""}
      </div>
    </button>`;
  }

  function renderCurrentBatch(batch, sample) {
    return `<div class="file-chip" style="margin-bottom:12px">
      ${icon("file")}
      <div><strong>${esc(batch.fileName || "粘贴导入")}</strong><div class="sub">${esc(
        batch.fileSize || "文本",
      )} · SHA-256 已记录 · 映射模板已保存</div></div>
      ${batchStatusBadge(batch.status)}
    </div>
    <div class="preview-stats">
      <div class="preview-stat"><div class="label">源数据行</div><div class="value">${batch.sourceRows}</div></div>
      <div class="preview-stat"><div class="label">有效记录</div><div class="value ok">${batch.valid}</div></div>
      <div class="preview-stat"><div class="label">跳过记录</div><div class="value">${batch.skipped}</div></div>
      <div class="preview-stat"><div class="label">数据错误</div><div class="value bad">${batch.errors}</div></div>
      <div class="preview-stat"><div class="label">带告警</div><div class="value warn">${batch.warnings}</div></div>
    </div>
    <div class="kv-list" style="margin-bottom:12px">
      <span class="k">提交时间</span><span>${esc(batch.committedAt)}</span>
      <span class="k">操作人</span><span>${esc(batch.operator)}</span>
      <span class="k">覆盖范围</span><span>${esc(currentCompany().name)} · ${monthCN(
        batch.month,
      )} · ${esc(sample.label)}</span>
      <span class="k">参与计算</span><span>是；重算时读取本批次行</span>
    </div>
    <div class="inline">
      <button class="btn btn-outline btn-sm" data-action="open-batch-detail" data-id="${batch.id}">${icon(
        "eye",
      )} 查看批次详情</button>
      <button class="btn btn-ghost btn-sm danger-text" data-action="open-revoke" data-id="${
        batch.id
      }" ${isEditable() ? "" : "disabled title=\"已确认或锁定月份不可撤销\""}>${icon(
        "undo",
      )} 撤销本批次</button>
      <span class="sub">撤销后旧批次不会自动恢复；本月结果将标记过期。</span>
    </div>`;
  }

  function renderPreviewBatchPanel(previews, sample) {
    return `<div class="panel">
      <div class="panel-head"><div><h3>待处理的预览批次</h3><div class="sub">预览行已写入最终表，但计算不可见</div></div></div>
      <div class="batch-list">
        ${previews
          .map(
            (batch) => `<div class="batch-row">
              <div class="batch-file">
                <div class="batch-file-name">${icon("file")} ${esc(
                  batch.fileName || "粘贴导入",
                )} ${batchStatusBadge(batch.status)}</div>
                <div class="batch-file-sub">${monthCN(batch.month)} · ${esc(
                  batch.expiresAt || "",
                )} 过期 · ${esc(batch.operator)}</div>
              </div>
              <div class="batch-counts"><span>有效 <strong>${batch.valid}</strong></span><span>跳过 <strong>${
                batch.skipped
              }</strong></span><span>错误 <strong>${batch.errors}</strong></span></div>
              <div class="batch-actions">
                <button class="btn btn-sm btn-outline" data-action="open-batch-detail" data-id="${batch.id}">查看</button>
                <button class="btn btn-sm btn-primary" data-action="open-commit-batch" data-id="${
                  batch.id
                }" ${isEditable() ? "" : "disabled"}>提交</button>
                <button class="btn btn-sm btn-ghost danger-text" data-action="open-discard-batch" data-id="${
                  batch.id
                }">丢弃</button>
              </div>
            </div>`,
          )
          .join("")}
      </div>
    </div>`;
  }

  function renderImportRulesCard(sample) {
    return `<div class="panel">
      <div class="panel-head"><div><h3>导入规则</h3><div class="sub">${esc(sample.label)}</div></div></div>
      <div class="panel-body">
        <div class="kv-list">
          <span class="k">格式</span><span>CSV / TSV / XLSX（服务端解析）</span>
          <span class="k">编码</span><span>UTF-8（含 BOM）→ GB18030</span>
          <span class="k">上限</span><span>10 MB / 100,000 行</span>
          <span class="k">归月</span><span>${esc(
            {
              punch: "按考勤日期；跨天夜班归班次开始日",
              trip: "起止范围与目标月相交即纳入",
              ot: "按自然日拆分钟，单日封顶 480",
              leave: "休息范围或上班开始日与目标月相交",
            }[state.importType],
          )}</span>
          <span class="k">覆盖</span><span>提交新批次 → 旧生效批次置为已替代</span>
          <span class="k">留存</span><span>不保留原始文件字节；保留元数据与 raw_row</span>
        </div>
      </div>
    </div>`;
  }

  function renderImportMappingCard(sample) {
    return `<div class="panel">
      <div class="panel-head"><div><h3>最近一次映射</h3><div class="sub">按公司 + 数据类型记忆</div></div></div>
      <div class="panel-body tight">
        <table class="table mapping-table">
          <thead><tr><th>规范字段</th><th>源列</th></tr></thead>
          <tbody>
            ${sample.fields
              .slice(0, 7)
              .map(
                (f) => `<tr><td>${esc(f.label)} ${f.required ? '<span class="required-dot">*</span>' : ""}</td><td><span class="code">${esc(
                  f.column,
                )}</span></td></tr>`,
              )
              .join("")}
          </tbody>
        </table>
        <div class="hint" style="padding:7px 6px 0">已忽略 ${sample.ignored.length} 个无关列</div>
      </div>
    </div>`;
  }

  /* ---------------------------------------------------------------- import wizard */

  function defaultWizard(dataType = state.importType, month = state.month) {
    const sample = db.importSamples[dataType];
    const mapping = {};
    for (const f of sample.fields) mapping[f.key] = f.column;
    return {
      step: 1,
      dataType,
      month,
      source: "upload",
      fileName: "",
      pasted: "",
      mapping,
      sheetName: "",
    };
  }

  function openImportWizard(dataType = state.importType) {
    state.wizard = defaultWizard(dataType, state.month);
    state.overlay = { type: "import-wizard", key: String(Date.now()) };
    render();
  }

  function wizardSample(wiz = state.wizard) {
    return db.importSamples[wiz.dataType];
  }

  function wizardMissingRequired(wiz = state.wizard) {
    return wizardSample(wiz).fields.filter(
      (f) => f.required && (!wiz.mapping[f.key] || wiz.mapping[f.key] === "__ignore__"),
    );
  }

  function wizardCanCommit(wiz = state.wizard) {
    const ms = monthState(wiz.month);
    if (ms.status === "confirmed") return { ok: false, reason: "本月已确认，提交前需撤销确认" };
    if (ms.status === "locked") return { ok: false, reason: "本月已锁定，提交前需解锁" };
    const sample = wizardSample(wiz);
    if (!sample.stats.valid) return { ok: false, reason: "没有有效记录，不能提交" };
    if (wizardMissingRequired(wiz).length) return { ok: false, reason: "存在未映射的必填列" };
    return { ok: true, reason: "" };
  }

  function renderImportWizardOverlay() {
    const wiz = state.wizard || defaultWizard();
    const sample = wizardSample(wiz);
    const steps = ["上传 / 粘贴", "列映射", "预览校验"];
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="wizard" role="dialog" aria-modal="true" aria-labelledby="wizard-title">
        <div class="wizard-steps">
          ${steps
            .map(
              (label, i) => `<div class="wizard-step ${
                wiz.step === i + 1 ? "active" : wiz.step > i + 1 ? "done" : ""
              }"><span class="num">${wiz.step > i + 1 ? icon("check") : i + 1}</span>${label}</div>`,
            )
            .join("")}
          <span class="spacer"></span>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="wizard-body">
          ${wiz.step === 1 ? renderWizardStep1(wiz, sample) : ""}
          ${wiz.step === 2 ? renderWizardStep2(wiz, sample) : ""}
          ${wiz.step === 3 ? renderWizardStep3(wiz, sample) : ""}
        </div>
        <div class="wizard-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <span class="spacer"></span>
          ${
            wiz.step > 1
              ? `<button class="btn btn-outline" data-action="wizard-back">${icon(
                  "arrow-left",
                )} 上一步</button>`
              : ""
          }
          ${
            wiz.step < 3
              ? `<button class="btn btn-primary" data-action="wizard-next" ${
                  wiz.step === 2 && wizardMissingRequired(wiz).length ? "disabled" : ""
                }>下一步 ${icon("arrow-right")}</button>`
              : `<button class="btn btn-primary" data-action="wizard-commit" ${
                  wizardCanCommit(wiz).ok ? "" : "disabled"
                }>提交生效</button>`
          }
        </div>
      </div>`;
  }

  function renderWizardStep1(wiz, sample) {
    return `<h3>选择数据类型与来源</h3>
      <p class="lead">批次固定「公司 + 月份 + 数据类型」。原型使用 fixture 样例模拟解析结果；真实实现由服务端解析文件。</p>
      <div class="form-grid two">
        <div class="field"><label>数据类型</label>
          <div class="segmented" style="width:100%">
            ${IMPORT_TYPES.map(
              (type) => `<button class="${wiz.dataType === type ? "active" : ""}" data-action="wizard-type" data-type="${type}">${esc(
                db.importSamples[type].label,
              )}</button>`,
            ).join("")}
          </div>
        </div>
        <div class="field"><label>归属月份</label>
          <select class="select" data-select="wizard-month" style="width:100%">
            <option value="2026-09" ${wiz.month === "2026-09" ? "selected" : ""}>2026 年 9 月</option>
            <option value="2026-10" ${wiz.month === "2026-10" ? "selected" : ""}>2026 年 10 月</option>
          </select>
        </div>
      </div>
      <div class="or-divider">上传文件</div>
      <button class="dropzone" style="width:100%" data-action="wizard-choose-file">
        ${icon("upload")}
        <strong>${wiz.fileName ? esc(wiz.fileName) : "点击选择 CSV / TSV / XLSX"}</strong>
        <span class="sub">最大 10 MB / 100,000 行；不支持旧版 .xls</span>
      </button>
      <input type="file" id="wizard-file" data-input="wizard-file" accept=".csv,.tsv,.xlsx" class="sr-only" />
      <div class="or-divider">或者粘贴</div>
      <textarea class="input paste-area" data-input="wizard-paste" placeholder="粘贴包含表头的文本，支持 Tab / 逗号 / 竖线分隔">${esc(
        wiz.pasted,
      )}</textarea>
      <div class="inline" style="margin-top:8px">
        <button class="btn btn-outline btn-sm" data-action="wizard-use-sample">${icon(
          "file",
        )} 载入样例：${esc(sample.file)}</button>
        <span class="sub">样例统计：${sample.stats.sourceRows} 源行 · ${sample.stats.valid} 有效 · ${sample.stats.skipped} 跳过</span>
      </div>`;
  }

  function renderWizardStep2(wiz, sample) {
    const missing = wizardMissingRequired(wiz);
    return `<h3>列映射</h3>
      <p class="lead">系统按内置别名识别列；可手动改列。缺必填列或两列映射到同一字段时，预览会阻止继续。本次映射会保存为该公司的${
        sample.label
      }模板。</p>
      ${
        missing.length
          ? `<div class="banner danger">${icon("alert")}<div>缺少必填映射：${missing
              .map((f) => esc(f.label))
              .join("、")}</div></div>`
          : ""
      }
      <div class="table-wrap">
        <table class="table mapping-table">
          <thead><tr><th>规范字段</th><th>必填</th><th>识别到的源列</th><th>样例值</th></tr></thead>
          <tbody>
            ${sample.fields
              .map(
                (f) => `<tr>
                  <td><span class="cell-strong">${esc(f.label)}</span><div class="cell-sub">${esc(
                    f.key,
                  )}</div></td>
                  <td>${f.required ? '<span class="required-dot">*</span>' : '<span class="muted">—</span>'}</td>
                  <td><select class="select" data-select="mapping-field" data-field="${
                    f.key
                  }" aria-label="${esc(f.label)}源列">
                    <option value="__ignore__" ${
                      !wiz.mapping[f.key] || wiz.mapping[f.key] === "__ignore__" ? "selected" : ""
                    }>（忽略）</option>
                    ${sample.headers
                      .map(
                        (h) =>
                          `<option value="${esc(h)}" ${
                            wiz.mapping[f.key] === h ? "selected" : ""
                          }>${esc(h)}</option>`,
                      )
                      .join("")}
                  </select></td>
                  <td><span class="code">${esc(f.sample || "—")}</span></td>
                </tr>`,
              )
              .join("")}
          </tbody>
        </table>
      </div>
      <div class="hint" style="margin-top:8px">已忽略列（不参与导入，保留在原始行中）：</div>
      <div class="ignored-cols">${sample.ignored
        .map((c) => `<span class="ignored-chip">${esc(c)}</span>`)
        .join("")}</div>`;
  }

  function renderWizardStep3(wiz, sample) {
    const can = wizardCanCommit(wiz);
    const current = committedBatch(wiz.dataType, wiz.month);
    const stats = sample.stats;
    const delta = current ? stats.valid - current.valid : stats.valid;
    return `<h3>预览校验</h3>
      <p class="lead">预览批次已解析，但还不参与计算。确认统计、错误与覆盖影响后再提交。</p>
      <div class="preview-stats">
        <div class="preview-stat"><div class="label">源数据行</div><div class="value">${stats.sourceRows}</div></div>
        <div class="preview-stat"><div class="label">有效记录</div><div class="value ok">${stats.valid}</div></div>
        <div class="preview-stat"><div class="label">跳过记录</div><div class="value">${stats.skipped}</div></div>
        <div class="preview-stat"><div class="label">数据错误</div><div class="value bad">${stats.errors}</div></div>
        <div class="preview-stat"><div class="label">带告警</div><div class="value warn">${stats.warnings}</div></div>
      </div>
      <div class="impact-card">
        <strong>覆盖式刷新：</strong>提交后，本批次将成为 ${monthCN(wiz.month)} 的${esc(
          sample.label,
        )}生效批次。
        <div class="impact-compare">
          <span class="box">当前：${current ? `${current.valid} 条有效` : "无生效批次"}</span>
          <span>${icon("arrow-right")}</span>
          <span class="box">本次：${stats.valid} 条有效</span>
          <span class="box">净变化：${delta >= 0 ? "+" : ""}${delta} 条</span>
        </div>
        <div style="margin-top:5px">${current ? "旧批次将被置为「已替代」，不会逐行合并；撤销本次提交后，旧批次不会自动恢复。" : "提交后本月考勤结果会被标记为过期，需要显式重算。"}</div>
      </div>
      ${
        can.ok
          ? ""
          : `<div class="banner danger">${icon("alert")}<div><strong>暂不能提交：</strong>${esc(
              can.reason,
            )}</div></div>`
      }
      <div class="section-title">错误与告警 <span class="sub">前 8 条；完整报告可导出</span></div>
      <div class="table-wrap">
        <table class="table issues-table">
          <thead><tr><th>行</th><th>列</th><th>类型</th><th>代码</th><th>说明</th></tr></thead>
          <tbody>
            ${sample.issues
              .slice(0, 8)
              .map(
                (issue) => `<tr>
                  <td>${issue.row}</td>
                  <td>${esc(issue.column)}</td>
                  <td><span class="sev ${issue.severity}">${
                    issue.severity === "error" ? "错误" : issue.severity === "warning" ? "告警" : "跳过"
                  }</span></td>
                  <td><span class="code">${esc(issue.code)}</span></td>
                  <td>${esc(issue.message)}</td>
                </tr>`,
              )
              .join("")}
          </tbody>
        </table>
      </div>
      <div class="section-title">规范化行样例 <span class="sub">前 3 条</span></div>
      <div class="table-wrap">
        <table class="table sample-table">
          <thead><tr><th>#</th><th>匹配员工</th><th>关键字段</th><th>归属日期</th><th>结果</th></tr></thead>
          <tbody>
            ${sample.samples
              .map(
                (row, i) => `<tr><td>${i + 1}</td><td>${esc(row[0])}</td><td>${esc(
                  row.slice(1, -2).join(" · "),
                )}</td><td>${esc(row[row.length - 2] || "")}</td><td><span class="badge badge-green">${
                  row[row.length - 1]
                }</span></td></tr>`,
              )
              .join("")}
          </tbody>
        </table>
      </div>`;
  }

  /* ---------------------------------------------------------------- batch detail */

  function renderBatchDetailOverlay(o) {
    const batch = db.importBatches.find((b) => b.id === o.id);
    if (!batch) return "";
    const sample = db.importSamples[batch.dataType];
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card xl" role="dialog" aria-modal="true" aria-labelledby="batch-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="batch-title">批次详情 · ${esc(sample.label)}</h2><p class="modal-sub">${esc(
            batch.fileName || "粘贴导入",
          )} · ${monthCN(batch.month)} · ${esc(batch.operator)}</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="inline" style="margin-bottom:12px">${batchStatusBadge(batch.status)}<span class="badge badge-gray">${
            batch.source === "paste" ? "粘贴" : "上传"
          }</span><span class="sub">创建 ${esc(batch.createdAt)}${
            batch.committedAt ? ` · 提交 ${esc(batch.committedAt)}` : ""
          }</span></div>
          <div class="preview-stats">
            <div class="preview-stat"><div class="label">源数据行</div><div class="value">${batch.sourceRows}</div></div>
            <div class="preview-stat"><div class="label">有效记录</div><div class="value ok">${batch.valid}</div></div>
            <div class="preview-stat"><div class="label">跳过记录</div><div class="value">${batch.skipped}</div></div>
            <div class="preview-stat"><div class="label">数据错误</div><div class="value bad">${batch.errors}</div></div>
            <div class="preview-stat"><div class="label">带告警</div><div class="value warn">${batch.warnings}</div></div>
          </div>
          <div class="section-title">列映射快照</div>
          <div class="table-wrap"><table class="table mapping-table">
            <thead><tr><th>规范字段</th><th>源列</th><th>样例</th></tr></thead>
            <tbody>${sample.fields
              .map(
                (f) => `<tr><td>${esc(f.label)}</td><td><span class="code">${esc(
                  f.column,
                )}</span></td><td>${esc(f.sample || "—")}</td></tr>`,
              )
              .join("")}</tbody>
          </table></div>
          <div class="section-title">错误与告警</div>
          <div class="table-wrap"><table class="table issues-table">
            <thead><tr><th>行</th><th>列</th><th>类型</th><th>代码</th><th>说明</th></tr></thead>
            <tbody>${sample.issues
              .map(
                (issue) => `<tr><td>${issue.row}</td><td>${esc(
                  issue.column,
                )}</td><td><span class="sev ${issue.severity}">${
                  issue.severity === "error" ? "错误" : issue.severity === "warning" ? "告警" : "跳过"
                }</span></td><td><span class="code">${esc(issue.code)}</span></td><td>${esc(
                  issue.message,
                )}</td></tr>`,
              )
              .join("")}</tbody>
          </table></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">关闭</button>
          ${
            batch.status === "preview"
              ? `<button class="btn btn-ghost danger-text" data-action="open-discard-batch" data-id="${batch.id}">丢弃</button>
                 <button class="btn btn-primary" data-action="open-commit-batch" data-id="${batch.id}" ${
                   isEditable(batch.month) ? "" : "disabled"
                 }>提交生效</button>`
              : ""
          }
          ${
            batch.status === "committed" && isEditable(batch.month)
              ? `<button class="btn btn-outline danger-text" data-action="open-revoke" data-id="${batch.id}">撤销批次</button>`
              : ""
          }
        </div>
      </div>`;
  }
  /* ================================================================ results */

  const RESULT_STATUS_OPTIONS = [
    ["all", "全部状态"],
    ["normal", "正常"],
    ["late", "迟到"],
    ["early", "早退"],
    ["missing_punch", "缺卡"],
    ["absent", "旷工"],
    ["overtime", "OA 加班"],
    ["trip_out", "外出"],
    ["trip_business", "出差"],
    ["personal_leave", "事假"],
    ["paid_leave", "带薪假"],
    ["comp_leave", "补休"],
    ["unscheduled_attendance", "未排班出勤"],
    ["rest", "休息"],
  ];

  function resultsExist(month = state.month) {
    return resultsForMonth(month).length > 0;
  }

  function sumSummary(field) {
    return summariesForMonth().reduce((sum, s) => sum + (s[field] || 0), 0);
  }

  function resultOtMinutes(r) {
    return r.otWeekdayMinutes + r.otWeekendMinutes + r.otHolidayMinutes;
  }

  function resultExceptionsCount() {
    return exceptionResults().length;
  }

  function renderResultActions() {
    const ms = monthState();
    const editable = isEditable();
    const canConfirm = ms.status === "calculated" && !ms.isStale;
    const canLock = ms.status === "confirmed";
    const canUnlock = ms.status === "locked";
    const hasBatches = committedBatches().length > 0;
    return `<div class="actions">
      <button class="btn btn-outline btn-sm" data-action="open-recalc" ${
        editable && hasBatches ? "" : "disabled title=\"已确认/锁定，或本月没有生效导入批次\""
      }>${icon("refresh")} 重新计算</button>
      <button class="btn btn-outline btn-sm" data-action="open-confirm-month" ${
        canConfirm ? "" : "disabled title=\"需已计算且结果未过期\""
      }>${icon("check-circle")} 确认</button>
      <button class="btn btn-outline btn-sm" data-action="open-lock-month" ${
        canLock ? "" : "disabled title=\"需先确认\""
      }>${icon("lock")} 锁定</button>
      <button class="btn btn-outline btn-sm" data-action="open-unlock" ${
        canUnlock ? "" : "disabled title=\"仅锁定月份可解锁\""
      }>${icon("unlock")} 解锁</button>
      <button class="btn btn-primary btn-sm" data-action="open-export" ${
        resultsExist() ? "" : "disabled"
      }>${icon("download")} 导出</button>
    </div>`;
  }

  function renderResultsPage({ embedded } = {}) {
    if (state.companyId === "c2") {
      return embedded ? renderCompanyEmpty() : pageHead("考勤结果", "当前公司暂无考勤结果") + renderCompanyEmpty();
    }
    return previewGuard(() => {
      const head = embedded
        ? ""
        : pageHead(
            "考勤结果",
            "全量日结果（可一键切换异常优先），加上员工月汇总与计算记录；从排班、打卡、OA 到结果四方对照，人工调整保留原值与理由。",
            renderResultActions(),
          );
      const ms = monthState();
      return `${head}
        ${embedded ? "" : renderMonthBar()}
        ${embedded ? `<div class="month-bar" style="padding:9px 12px"><span class="sub">${monthCN(state.month)} · 结果层操作</span><span class="spacer"></span>${renderResultActions()}</div>` : ""}
        ${renderResultStatusTimeline()}
        ${renderResultKpis()}
        ${renderResultBanners()}
        ${
          !resultsExist()
            ? renderResultsEmpty()
            : `<div class="panel">
                <div class="panel-head" style="padding:8px 12px">
                  <div class="segmented" role="tablist" aria-label="结果视图">
                    ${[
                      ["days", "日结果"],
                      ["summary", "员工月汇总"],
                      ["runs", "计算记录"],
                    ]
                      .map(
                        ([key, label]) =>
                          `<button class="${state.resultTab === key ? "active" : ""}" data-action="result-tab" data-tab="${key}">${label}${
                            key === "days" ? ` · ${resultsForMonth().length}` : ""
                          }</button>`,
                      )
                      .join("")}
                  </div>
                  <span class="spacer"></span>
                  <span class="sub">${esc(ms.calculatedAt ? `最近计算 ${ms.calculatedAt}` : "尚未计算")}</span>
                </div>
                ${
                  state.resultTab === "days"
                    ? renderResultDaysTable()
                    : state.resultTab === "summary"
                      ? renderResultSummaryTable()
                      : renderCalcRuns()
                }
              </div>`
        }`;
    });
  }

  function renderResultStatusTimeline() {
    const ms = monthState();
    const order = ["draft", "calculated", "confirmed", "locked"];
    const currentIndex = order.indexOf(ms.status);
    const labels = ["草稿", "已计算", "已确认", "已锁定"];
    return `<div class="status-timeline">
      ${labels
        .map((label, i) => {
          const done = i < currentIndex;
          const current = i === currentIndex;
          const stale = current && ms.isStale && ms.status === "calculated";
          return `<div class="step ${done ? "done" : ""} ${current ? "current" : ""} ${
            stale ? "stale" : ""
          }"><span class="step-dot">${done ? icon("check") : i + 1}</span>${label}${
            stale ? " · 已过期" : ""
          }</div>`;
        })
        .join("")}
      <span class="spacer"></span>
      <span class="sub">${
        ms.status === "locked"
          ? `锁定于 ${esc(ms.lockedAt || "")}`
          : ms.status === "confirmed"
            ? `确认于 ${esc(ms.confirmedAt || "")}`
            : ms.calculatedAt
              ? `计算于 ${esc(ms.calculatedAt)}`
              : "尚未计算"
      }</span>
    </div>`;
  }

  function renderResultKpis() {
    const ex = resultExceptionsCount();
    const full = sumSummary("weekdayFull") + sumSummary("weekendFull");
    const attended = sumSummary("weekdayAttended") + sumSummary("weekendAttended");
    const ot = sumSummary("otWeekdayHours") + sumSummary("otWeekendHours") + sumSummary("otHolidayHours");
    const deduct = sumSummary("attendanceDeduct");
    return `<div class="kpi-grid">
      <div class="kpi">
        <div class="kpi-label">${icon("calendar")} 应出勤人日</div>
        <div class="kpi-value">${full}<small>人日</small></div>
        <div class="kpi-sub">满勤天数口径，请假不扣减</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">${icon("check-circle")} 实际出勤</div>
        <div class="kpi-value">${attended.toFixed(1)}<small>人日</small></div>
        <div class="kpi-sub">含半天、出差与未排班出勤</div>
      </div>
      <div class="kpi ${ex ? "danger" : ""}">
        <div class="kpi-label">${icon("alert")} 异常待处理</div>
        <div class="kpi-value">${ex}<small>条</small></div>
        <div class="kpi-sub">旷工 / 缺卡 / 迟到 / 早退</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">${icon("timer")} 加班合计</div>
        <div class="kpi-value">${ot.toFixed(2)}<small>h</small></div>
        <div class="kpi-sub">工作日 / 周末 / 节假日</div>
      </div>
      <div class="kpi">
        <div class="kpi-label">${icon("coins")} 扣款建议</div>
        <div class="kpi-value">${money(deduct)}<small>元</small></div>
        <div class="kpi-sub">负值表示扣减，不直接扣工资</div>
      </div>
    </div>`;
  }

  function renderResultBanners() {
    const ms = monthState();
    const parts = [];
    if (ms.isStale && ms.status !== "locked") {
      parts.push(`<div class="banner warn">${icon(
        "alert",
      )}<div><strong>结果已过期。</strong>当前结果基于上一次计算；排班、导入、规则或节假日已变化。重算后生效。</div><div class="banner-actions"><button class="btn btn-sm btn-outline" data-action="open-recalc" ${
        isEditable() ? "" : "disabled"
      }>重新计算</button></div></div>`);
    }
    if (ms.status === "confirmed") {
      parts.push(`<div class="banner success">${icon(
        "shield",
      )}<div><strong>本月已确认。</strong>确认后不可直接修改数据；如需修改，先撤销确认。</div><div class="banner-actions"><button class="btn btn-sm btn-outline" data-action="undo-confirm">撤销确认</button></div></div>`);
    }
    if (ms.status === "locked") {
      parts.push(`<div class="banner danger">${icon(
        "lock",
      )}<div><strong>本月已锁定。</strong>${ms.unlockReason ? `上次解锁理由：${esc(ms.unlockReason)}。` : ""}解锁必须填写理由，解锁后结果标记过期，需要重新计算。</div><div class="banner-actions"><button class="btn btn-sm btn-outline" data-action="open-snapshot">查看快照</button><button class="btn btn-sm btn-outline" data-action="open-unlock">解锁</button></div></div>`);
    }
    if (!committedBatches().length && resultsExist()) {
      parts.push(`<div class="banner">${icon(
        "info",
      )}<div>本月没有生效导入批次，但仍有计算结果；重算前请先导入打卡与 OA。</div></div>`);
    }
    return parts.join("");
  }

  function renderResultsEmpty() {
    const hasPlans = companyPlans().length > 0;
    return `<div class="empty" style="padding:56px 20px">
      <div class="empty-icon">${icon("inbox")}</div>
      <h3>${monthCN(state.month)} 还没有计算结果</h3>
      <p>${
        hasPlans
          ? "排班已存在。导入打卡与 OA 后点击重新计算，系统会生成日结果与员工月汇总。"
          : "先创建排班方案或复制上月，再导入数据并计算。"
      }</p>
      <div class="inline" style="justify-content:center">
        <button class="btn btn-primary" data-action="open-recalc" ${
          isEditable() ? "" : "disabled"
        }>${icon("refresh")} 重新计算</button>
        <button class="btn btn-outline" data-action="nav" data-page="import">${icon(
          "upload",
        )} 去导入</button>
        <button class="btn btn-outline" data-action="nav" data-page="schedule">${icon(
          "calendar",
        )} 去排班</button>
      </div>
    </div>`;
  }

  function filteredResults() {
    let list = resultsForMonth();
    if (state.resultFilter === "exceptions" && !state.resultAdjusted) {
      list = list.filter(isExceptionResult);
    }
    if (state.resultStatus !== "all") list = list.filter((r) => r.dayStatus === state.resultStatus);
    if (state.resultAdjusted) list = list.filter((r) => r.isAdjusted);
    if (state.resultDept !== "all") {
      const ids = new Set(Data.deptDescendants(db, state.resultDept));
      list = list.filter((r) => {
        const emp = getEmployee(r.employeeId);
        return emp && ids.has(emp.deptId);
      });
    }
    const search = (state.resultSearch || "").trim().toLowerCase();
    if (search) {
      list = list.filter((r) => {
        const emp = getEmployee(r.employeeId);
        return (
          r.employeeId.toLowerCase().includes(search) ||
          (emp && (emp.name.toLowerCase().includes(search) || emp.no.toLowerCase().includes(search)))
        );
      });
    }
    if (state.resultDate) list = list.filter((r) => r.date === state.resultDate);
    const severity = {
      absent: 0,
      missing_punch: 1,
      late: 2,
      early: 3,
      unscheduled_attendance: 4,
      personal_leave: 5,
      paid_leave: 6,
      comp_leave: 7,
      trip_out: 8,
      trip_business: 9,
      overtime: 10,
      normal: 11,
      rest: 12,
    };
    if (state.resultFilter === "exceptions") {
      list = list.slice().sort((a, b) => {
        const d = (severity[a.dayStatus] ?? 99) - (severity[b.dayStatus] ?? 99);
        return d !== 0 ? d : a.date.localeCompare(b.date);
      });
    } else {
      list = list.slice().sort((a, b) =>
        a.date === b.date ? a.employeeId.localeCompare(b.employeeId) : a.date.localeCompare(b.date),
      );
    }
    return list;
  }

  function renderResultDaysTable() {
    const list = filteredResults();
    const pageSize = 25;
    const totalPages = Math.max(1, Math.ceil(list.length / pageSize));
    const page = Math.min(state.resultPage, totalPages);
    const rows = list.slice((page - 1) * pageSize, page * pageSize);
    return `<div style="padding:12px 14px">
      <div class="result-toolbar">
        <label class="filter-toggle"><input type="checkbox" data-check="result-exceptions" ${
          state.resultFilter === "exceptions" ? "checked" : ""
        } /> 只看异常</label>
        <select class="select" data-select="result-dept" aria-label="部门筛选">
          ${deptOptions()
            .map(
              (o) =>
                `<option value="${o.value}" ${state.resultDept === o.value ? "selected" : ""}>${esc(
                  o.label,
                )}</option>`,
            )
            .join("")}
        </select>
        <select class="select" data-select="result-status" aria-label="状态筛选">
          ${RESULT_STATUS_OPTIONS.map(
            ([value, label]) =>
              `<option value="${value}" ${state.resultStatus === value ? "selected" : ""}>${esc(
                label,
              )}</option>`,
          ).join("")}
        </select>
        <div class="search-compact">${icon("search")}<input class="input" data-input="result-search" value="${esc(
          state.resultSearch,
        )}" placeholder="姓名 / 工号" aria-label="搜索员工" /></div>
        <input class="input" type="date" data-input="result-date" value="${esc(
          state.resultDate || "",
        )}" aria-label="按日期筛选" style="width:142px" />
        <label class="filter-toggle"><input type="checkbox" data-check="result-adjusted" ${
          state.resultAdjusted ? "checked" : ""
        } /> 仅已调整</label>
        ${
          state.resultDate
            ? `<span class="badge badge-blue">${dateCN(state.resultDate)} <button class="btn btn-ghost btn-sm" data-action="clear-result-date" aria-label="清除日期" style="height:18px;padding:0 2px">${icon(
                "x",
              )}</button></span>`
            : ""
        }
        <span class="spacer"></span>
        <span class="sub">${list.length} 条结果${state.resultFilter === "exceptions" ? "（异常优先）" : ""}</span>
      </div>
      ${
        rows.length
          ? `<div class="table-wrap"><table class="table result-table">
              <thead><tr>
                <th>员工</th><th>部门</th><th>日期</th><th>日类型</th><th>排班</th><th>状态</th>
                <th>打卡</th><th>OA</th><th>出勤</th><th>工时</th><th>加班</th><th>扣款</th><th></th>
              </tr></thead>
              <tbody>
                ${rows
                  .map((r) => {
                    const emp = getEmployee(r.employeeId);
                    const ot = resultOtMinutes(r);
                    const punch = resultPunchText(r);
                    return `<tr class="${isExceptionResult(r) ? "row-exception" : ""} ${
                      r.isAdjusted ? "row-adjusted" : ""
                    }" data-action="open-result" data-employee="${r.employeeId}" data-date="${r.date}">
                      <td><div class="cell-strong">${esc(emp?.name || r.employeeId)}</div><div class="cell-sub">${esc(
                        emp?.no || "",
                      )}</div></td>
                      <td>${esc(emp ? Data.deptPath(db, emp.deptId) : "")}</td>
                      <td><div class="cell-strong">${esc(r.date)}</div><div class="cell-sub">${weekdayCN(
                        r.date,
                      )}</div></td>
                      <td>${esc(r.dayTypeLabel)}</td>
                      <td>${
                        r.shifts.length
                          ? `<div class="inline">${r.shifts.map(shiftChipCode).join("")}</div>`
                          : `<span class="sub">${esc(r.rosterStateLabel)}</span>`
                      }</td>
                      <td>${statusBadge(r.dayStatus)}${
                        r.isAdjusted ? `<div class="adjust-mark">${icon("edit")}已调整</div>` : ""
                      }</td>
                      <td><span class="punch-inline">${punch}</span></td>
                      <td><div class="oa-inline">${renderOaTags(r)}</div></td>
                      <td>${r.attendanceFraction.toFixed(1)}</td>
                      <td>${hoursLabel(r.workedMinutes)}</td>
                      <td>${ot ? `${hoursLabel(ot)}h` : "—"}</td>
                      <td><span class="deduct ${r.deductionTotal ? "" : "zero"}">${
                        r.deductionTotal ? money(r.deductionTotal) : "0.00"
                      }</span></td>
                      <td>${icon("chevron-right")}</td>
                    </tr>`;
                  })
                  .join("")}
              </tbody>
            </table></div>
            <div class="table-foot">
              <span>第 ${page} / ${totalPages} 页 · 共 ${list.length} 条</span>
              <span class="spacer"></span>
              <div class="pagination">
                <button data-action="result-page" data-page="${page - 1}" ${
                  page <= 1 ? "disabled" : ""
                }>上一页</button>
                ${Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((n) => n === 1 || n === totalPages || Math.abs(n - page) <= 1)
                  .map(
                    (n, idx, arr) =>
                      `${idx && n - arr[idx - 1] > 1 ? `<span class="muted">…</span>` : ""}<button class="${
                        n === page ? "active" : ""
                      }" data-action="result-page" data-page="${n}">${n}</button>`,
                  )
                  .join("")}
                <button data-action="result-page" data-page="${page + 1}" ${
                  page >= totalPages ? "disabled" : ""
                }>下一页</button>
              </div>
            </div>`
          : `<div class="empty" style="padding:38px 20px"><div class="empty-icon">${icon(
              "check-circle",
            )}</div><h3 style="font-size:13px">没有匹配的结果</h3><p style="font-size:11px">试试关闭「只看异常」、清除筛选，或切换月份。</p></div>`
      }
    </div>`;
  }

  function resultPunchText(r) {
    const ins = r.shiftResults.filter((sr) => sr.inPunch).map((sr) => sr.inPunch);
    const outs = r.shiftResults.filter((sr) => sr.outPunch).map((sr) => sr.outPunch);
    const fmt = (p) => {
      if (!p) return "";
      return `${p.date !== r.date ? "次日 " : ""}${p.time}`;
    };
    if (!ins.length && !outs.length) return `<span class="sub">无打卡</span>`;
    const inTxt = ins.length ? fmt(ins[0]) : "—";
    const outTxt = outs.length ? fmt(outs[outs.length - 1]) : "—";
    return `${inTxt} / <span class="${r.lateMinutes ? "late" : ""}${r.earlyMinutes ? "early" : ""}">${outTxt}</span>`;
  }

  function renderOaTags(r) {
    const tags = [];
    if (r.trips.length) {
      tags.push(`<span class="oa-tag trip">${r.trips[0].kind === "business" ? "出差" : "外出"}</span>`);
    }
    if (r.leaves.length) {
      const kind = r.leaves[0].kind === "paid" ? "带薪假" : r.leaves[0].kind === "comp" ? "补休" : "事假";
      tags.push(`<span class="oa-tag leave">${kind} ${r.leaveDays}</span>`);
    }
    if (r.oaOtMinutes) {
      tags.push(`<span class="oa-tag ot">OT ${hoursLabel(r.oaOtMinutes)}h</span>`);
    }
    if (r.compOffsetMinutes) {
      tags.push(`<span class="oa-tag leave">补休抵 ${hoursLabel(r.compOffsetMinutes)}h</span>`);
    }
    return tags.join("") || `<span class="sub">—</span>`;
  }

  function renderResultSummaryTable() {
    const list = summariesForMonth();
    return `<div class="table-wrap">
      <table class="table result-table">
        <thead><tr>
          <th>员工</th><th>部门</th><th>应出勤</th><th>实际出勤</th><th>请假</th><th>出差</th>
          <th>加班</th><th>迟到 / 早退</th><th>缺卡 / 旷工</th><th>扣款建议</th><th>调整</th><th></th>
        </tr></thead>
        <tbody>
          ${list
            .map((s) => {
              return `<tr data-action="open-employee-summary" data-employee="${s.employeeId}">
                <td><div class="cell-strong">${esc(s.employeeName)}</div><div class="cell-sub">${esc(
                  s.employeeNo,
                )}</div></td>
                <td>${esc(s.deptName)}</td>
                <td><div class="cell-strong">${s.weekdayFull + s.weekendFull}</div><div class="cell-sub">工作 ${s.weekdayFull} · 周末 ${s.weekendFull}</div></td>
                <td><div class="cell-strong">${(s.weekdayAttended + s.weekendAttended).toFixed(1)}</div><div class="cell-sub">工作 ${s.weekdayAttended} · 周末 ${s.weekendAttended}</div></td>
                <td><div>${s.paidLeaveDays + s.unpaidLeaveDays + s.compLeaveDays}</div><div class="cell-sub">带薪 ${s.paidLeaveDays} · 事假 ${s.unpaidLeaveDays} · 补休 ${s.compLeaveDays}</div></td>
                <td>${s.tripDays}</td>
                <td><div>${(s.otWeekdayHours + s.otWeekendHours + s.otHolidayHours).toFixed(2)}h</div><div class="cell-sub">工 ${s.otWeekdayHours} · 周 ${s.otWeekendHours} · 节 ${s.otHolidayHours}</div></td>
                <td>${s.lateCount} / ${s.earlyCount}<div class="cell-sub">${s.lateMinutes} / ${s.earlyMinutes} 分钟</div></td>
                <td>${s.missingPunchCount} / ${s.absentDays}</td>
                <td><span class="deduct ${s.attendanceDeduct ? "" : "zero"}">${
                  s.attendanceDeduct ? money(s.attendanceDeduct) : "0.00"
                }</span></td>
                <td>${s.isAdjusted ? `<span class="badge badge-blue">有调整</span>` : `<span class="sub">—</span>`}</td>
                <td>${icon("chevron-right")}</td>
              </tr>`;
            })
            .join("")}
        </tbody>
      </table>
      <div class="table-foot">
        <span>${list.length} 名员工 · 薪酬回填 CSV 使用其中的应出勤、实际出勤、请假与三类加班列</span>
        <span class="spacer"></span>
        <button class="btn btn-sm btn-outline" data-action="open-export">${icon("download")} 导出薪酬回填 CSV</button>
      </div>
    </div>`;
  }

  function renderCalcRuns() {
    const runs = (db.calcRuns[state.month] || []).slice().reverse();
    const triggerLabel = {
      initial: "首次计算",
      manual: "手动重算",
      reimport: "导入后重算",
      roster_change: "排班变更后重算",
      rule_change: "规则变更后重算",
      holiday_change: "节假日变更后重算",
    };
    return `<div class="calc-run-list">
      ${
        runs.length
          ? runs
              .map(
                (run) => `<div class="calc-run ${run.status === "failed" ? "failed" : ""}">
                  <div class="run-icon">${icon(run.status === "failed" ? "alert" : "check")}</div>
                  <div class="run-main">
                    <div class="run-title">${esc(triggerLabel[run.trigger] || run.trigger)}${
                      run.note ? ` · ${esc(run.note)}` : ""
                    }</div>
                    <div class="run-sub">${esc(run.startedAt)} → ${esc(
                      run.finishedAt,
                    )} · ${run.employees} 人 · ${run.days} 天 · 算法 attendance-calc-v1</div>
                  </div>
                  <span class="badge ${run.status === "failed" ? "badge-red" : "badge-green"}">${
                    run.status === "failed" ? "失败" : "成功"
                  }</span>
                </div>`,
              )
              .join("")
          : `<div class="empty" style="padding:28px"><div class="empty-icon">${icon(
              "history",
            )}</div><h3 style="font-size:12px">本月还没有计算记录</h3></div>`
      }
      <div class="table-foot" style="border-top:1px solid var(--border)">
        <span>每次重算生成一条记录；计算失败整笔回滚，旧结果不变。</span>
        <span class="spacer"></span>
        <button class="btn btn-sm btn-outline" data-action="open-recalc" ${
          isEditable() ? "" : "disabled"
        }>${icon("refresh")} 重新计算</button>
      </div>
    </div>`;
  }

  function renderEmployeeSummaryOverlay(o) {
    const emp = getEmployee(o.employee);
    const summary = summariesForMonth().find((s) => s.employeeId === o.employee);
    const rows = resultsForMonth().filter((r) => r.employeeId === o.employee);
    if (!emp || !summary) return "";
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card xl" role="dialog" aria-modal="true" aria-labelledby="emp-summary-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="emp-summary-title">${esc(emp.name)} · 月汇总</h2><p class="modal-sub">${esc(
            Data.deptPath(db, emp.deptId),
          )} · ${esc(emp.no)} · ${monthCN(state.month)}</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:14px">
            <div class="kpi"><div class="kpi-label">应出勤</div><div class="kpi-value">${
              summary.weekdayFull + summary.weekendFull
            }<small>天</small></div><div class="kpi-sub">工作 ${summary.weekdayFull} · 周末 ${summary.weekendFull}</div></div>
            <div class="kpi"><div class="kpi-label">实际出勤</div><div class="kpi-value">${(
              summary.weekdayAttended + summary.weekendAttended
            ).toFixed(1)}<small>天</small></div><div class="kpi-sub">含出差与未排班出勤</div></div>
            <div class="kpi"><div class="kpi-label">加班</div><div class="kpi-value">${(
              summary.otWeekdayHours +
              summary.otWeekendHours +
              summary.otHolidayHours
            ).toFixed(2)}<small>h</small></div><div class="kpi-sub">补休抵扣后净值</div></div>
            <div class="kpi"><div class="kpi-label">扣款建议</div><div class="kpi-value danger-text">${money(
              summary.attendanceDeduct,
            )}<small>元</small></div><div class="kpi-sub">负值</div></div>
          </div>
          <div class="table-wrap"><table class="table result-table">
            <thead><tr><th>日期</th><th>日类型</th><th>排班</th><th>状态</th><th>出勤</th><th>工时</th><th>加班</th><th>扣款</th></tr></thead>
            <tbody>${rows
              .map(
                (r) => `<tr data-action="open-result" data-employee="${r.employeeId}" data-date="${
                  r.date
                }"><td>${esc(r.date)} ${weekdayCN(r.date)}</td><td>${esc(
                  r.dayTypeLabel,
                )}</td><td>${r.shifts.length ? r.shifts.map(shiftChipCode).join("") : esc(r.rosterStateLabel)}</td><td>${statusBadge(
                  r.dayStatus,
                )}</td><td>${r.attendanceFraction.toFixed(1)}</td><td>${hoursLabel(
                  r.workedMinutes,
                )}</td><td>${resultOtMinutes(r) ? hoursLabel(resultOtMinutes(r)) + "h" : "—"}</td><td>${
                  r.deductionTotal ? money(r.deductionTotal) : "0.00"
                }</td></tr>`,
              )
              .join("")}</tbody>
          </table></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">关闭</button>
          <button class="btn btn-primary" data-action="filter-employee-results" data-employee="${
            emp.id
          }">在日结果中查看</button>
        </div>
      </div>`;
  }
  /* ================================================================ rules & holidays */

  function ruleField(label, key, value, hint, type = "number", extra = "") {
    return `<div class="rule-field">
      <label for="rule-${key}">${esc(label)}</label>
      <input class="input" id="rule-${key}" type="${type}" data-rule-field="${key}" value="${esc(
        value,
      )}" ${extra} />
      <div class="hint">${esc(hint)}</div>
    </div>`;
  }

  function ruleSwitch(label, key, checked, hint) {
    return `<div class="rule-field">
      <label>${esc(label)}</label>
      <label class="switch">
        <input type="checkbox" role="switch" data-rule-check="${key}" ${checked ? "checked" : ""} />
        <span class="switch-track" aria-hidden="true"><span class="switch-thumb"></span></span>
        <span class="switch-label">${checked ? "开启" : "关闭"}</span>
      </label>
      <div class="hint">${esc(hint)}</div>
    </div>`;
  }

  function renderRulesPage({ embedded } = {}) {
    if (state.companyId === "c2") {
      return embedded ? renderCompanyEmpty() : pageHead("规则与节假日", "当前公司暂无考勤配置") + renderCompanyEmpty();
    }
    return previewGuard(() => {
      const head = embedded
        ? ""
        : pageHead(
            "规则与节假日",
            "公司默认规则 + 方案覆盖；节假日日历决定工作日 / 周末 / 法定节假日 / 调休上班。修改只影响草稿与已计算月份。",
            `<div class="actions">
              <button class="btn btn-outline btn-sm" data-action="open-holiday-form">${icon("plus")} 添加节假日</button>
              <button class="btn btn-primary btn-sm" data-action="save-rules">${icon("check")} 保存规则</button>
            </div>`,
          );
      return `${head}
        ${embedded ? "" : renderMonthBar()}
        ${embedded ? `<div class="month-bar" style="padding:9px 12px"><span class="sub">${monthCN(state.month)} · 公司级规则与日历</span><span class="spacer"></span><div class="actions"><button class="btn btn-outline btn-sm" data-action="open-shifts-overlay">${icon("clock")} 班次管理</button><button class="btn btn-outline btn-sm" data-action="open-holiday-form">${icon("plus")} 添加节假日</button><button class="btn btn-primary btn-sm" data-action="save-rules">${icon("check")} 保存规则</button></div></div>` : ""}
        ${renderRuleBanners()}
        <div class="rule-layout">
          <div>
            <div class="rule-section">
              <div class="rule-section-head"><h3>打卡归属窗口</h3><span class="sub">决定一张卡算上班还是下班</span></div>
              <div class="rule-section-body"><div class="rule-grid">
                ${ruleField("上班卡可提前（分钟）", "punch_window_min", db.rules.punch_window_min, "早于上班时间多久内的卡仍算本班上班卡")}
                ${ruleField("上班卡最晚归属（分钟）", "late_cap_min", db.rules.late_cap_min, "晚于上班时间多久内仍算本班上班卡")}
                ${ruleField("下班卡最早归属（分钟）", "early_cap_min", db.rules.early_cap_min, "早于下班时间多久内的卡仍算本班下班卡")}
              </div></div>
            </div>
            <div class="rule-section">
              <div class="rule-section-head"><h3>迟到与早退</h3><span class="sub">按班次计次数与分钟</span></div>
              <div class="rule-section-body"><div class="rule-grid">
                ${ruleField("迟到宽限（分钟）", "late_grace_min", db.rules.late_grace_min, "上班卡晚于该宽限才开始计迟到")}
                ${ruleField("早退宽限（分钟）", "early_grace_min", db.rules.early_grace_min, "下班卡早于该宽限才开始计早退")}
              </div></div>
            </div>
            <div class="rule-section">
              <div class="rule-section-head"><h3>加班</h3><span class="sub">只从当日最后一班产生打卡加班</span></div>
              <div class="rule-section-body"><div class="rule-grid">
                ${ruleField("单日加班上限（分钟）", "ot_max_min", db.rules.ot_max_min, "打卡与 OA 加班都受此上限约束")}
                ${ruleField("加班起算阈值（分钟）", "ot_threshold_min", db.rules.ot_threshold_min, "仅作用于打卡推算值；OA 审批值不折减")}
              </div></div>
            </div>
            <div class="rule-section">
              <div class="rule-section-head"><h3>午休与旷工</h3><span class="sub">午休卡缺失不影响工时</span></div>
              <div class="rule-section-body"><div class="rule-grid">
                ${ruleSwitch("班次配置午休段时要求 4 次卡", "break_punch_required", db.rules.break_punch_required, "缺午休卡计缺卡，但工时仍按上下班卡 − 休息扣除")}
                ${ruleField("午休卡识别容差（分钟）", "break_punch_tolerance_min", db.rules.break_punch_tolerance_min, "在午休开始/结束前后该范围内找卡")}
                ${ruleSwitch("排班日完全无卡计旷工", "absent_if_no_punch", db.rules.absent_if_no_punch, "关闭时改记缺卡（按 2 张计）")}
              </div></div>
            </div>
            <div class="rule-section">
              <div class="rule-section-head"><h3>扣款建议值</h3><span class="sub">负值写入月汇总；考勤模块不直接扣工资</span></div>
              <div class="rule-section-body"><div class="rule-grid">
                ${ruleField("旷工每日（元）", "absent_deduct_per_day", db.rules.absent_deduct_per_day, "按日计；旷工日不再计迟到/早退/缺卡")}
                ${ruleField("迟到每次（元）", "late_deduct_per_occurrence", db.rules.late_deduct_per_occurrence, "按班次计次数")}
                ${ruleField("早退每次（元）", "early_deduct_per_occurrence", db.rules.early_deduct_per_occurrence, "按班次计次数")}
                ${ruleField("缺卡每张（元）", "missing_punch_deduct_per_occurrence", db.rules.missing_punch_deduct_per_occurrence, "缺上班/下班/午休各计 1 张")}
              </div></div>
            </div>
            ${renderPlanOverrideSection()}
          </div>
          <div class="stack">
            ${renderRuleImpactPanel()}
            ${renderHolidaySection()}
          </div>
        </div>`;
    });
  }

  function renderRuleBanners() {
    const ms = monthState();
    if (ms.status === "confirmed" || ms.status === "locked") {
      return `<div class="banner info">${icon("shield")}<div><strong>${
        ms.status === "locked" ? "本月已锁定" : "本月已确认"
      }。</strong>规则与节假日仍可维护，但已确认/锁定月份的结果不会变化。</div></div>`;
    }
    return `<div class="banner">${icon(
      "info",
    )}<div>规则保存后不会自动重算；只把当前草稿 / 已计算月份标记为「结果过期」。重算时使用保存后的生效规则。</div></div>`;
  }

  function renderPlanOverrideSection() {
    const plans = companyPlans();
    return `<div class="rule-section">
      <div class="rule-section-head"><h3>方案级规则覆盖</h3><span class="sub">空值 = 继承公司默认；同名字段合并后生效</span></div>
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>方案</th><th>范围</th><th>覆盖字段</th><th>生效摘要</th><th></th></tr></thead>
          <tbody>
            ${plans
              .map((plan) => {
                const override = db.planRuleOverrides[plan.id] || {};
                const keys = Object.keys(override).filter(
                  (k) => override[k] !== null && override[k] !== undefined,
                );
                return `<tr>
                  <td class="cell-strong">${esc(plan.name)}</td>
                  <td>${esc(planScopeLabel(plan))}</td>
                  <td>${keys.length ? `<span class="badge badge-blue">${keys.length} 项</span>` : `<span class="sub">继承公司默认</span>`}</td>
                  <td class="cell-sub">${
                    keys.length
                      ? keys
                          .slice(0, 3)
                          .map((k) => `${RULE_LABELS[k] || k}=${override[k]}`)
                          .join(" · ")
                      : "—"
                  }</td>
                  <td class="td-actions"><button class="btn btn-sm btn-ghost" data-action="open-override-form" data-id="${
                    plan.id
                  }">${icon("edit")} 编辑</button></td>
                </tr>`;
              })
              .join("")}
          </tbody>
        </table>
      </div>
    </div>`;
  }

  const RULE_LABELS = {
    punch_window_min: "提前窗口",
    late_cap_min: "上班卡最晚",
    early_cap_min: "下班卡最早",
    ot_max_min: "加班上限",
    late_grace_min: "迟到宽限",
    early_grace_min: "早退宽限",
    ot_threshold_min: "加班起算",
    absent_if_no_punch: "无卡计旷工",
    break_punch_required: "午休 4 次卡",
    break_punch_tolerance_min: "午休卡容差",
    absent_deduct_per_day: "旷工扣款",
    late_deduct_per_occurrence: "迟到扣款",
    early_deduct_per_occurrence: "早退扣款",
    missing_punch_deduct_per_occurrence: "缺卡扣款",
  };

  function renderRuleImpactPanel() {
    const ms = monthState();
    const other = state.month === "2026-09" ? "2026-10" : "2026-09";
    const otherState = monthState(other);
    return `<div class="impact-panel">
      <h3>${icon("alert")} 修改影响</h3>
      <div>保存公司规则或方案覆盖后：</div>
      <div class="impact-list">
        <div class="impact-list-item"><span class="dot"></span><span>${monthCN(state.month)}：${
          ms.status === "locked"
            ? "已锁定，结果不变"
            : ms.status === "confirmed"
              ? "已确认，结果不变"
              : ms.status === "calculated"
                ? "已计算 → 标记为过期"
                : "草稿，等待计算"
        }</span></div>
        <div class="impact-list-item"><span class="dot"></span><span>${monthCN(other)}：${
          otherState.status === "locked" || otherState.status === "confirmed"
            ? "已确认/锁定，结果不变"
            : "草稿 / 已计算，按需重算"
        }</span></div>
        <div class="impact-list-item"><span class="dot"></span><span>已确认与锁定月份永不自动变化</span></div>
        <div class="impact-list-item"><span class="dot"></span><span>不自动重算；重算由用户在结果页显式触发</span></div>
      </div>
      <div style="margin-top:9px;font-size:10px;opacity:.8">方案覆盖示例：生产部早中班覆盖迟到宽限 10 分钟、加班起算 15 分钟、旷工扣款 150 元；财务部覆盖缺卡扣款 5 元。</div>
    </div>`;
  }

  function renderHolidaySection() {
    const month = state.holidayMonth;
    const holidays = (db.holidays[month] || []).slice().sort((a, b) => a.date.localeCompare(b.date));
    return `<div class="panel">
      <div class="panel-head">
        <div><h3>节假日日历</h3><div class="sub">公司级维护；调休上班 &gt; 法定节假日 &gt; 周末</div></div>
        <div class="inline">
          <div class="month-nav" style="height:26px">
            <button data-action="holiday-month-prev" aria-label="上一个月" ${
              month === "2026-09" ? "disabled" : ""
            }>${icon("chevron-left")}</button>
            <strong style="min-width:64px;font-size:11px">${monthLabel(month)}</strong>
            <button data-action="holiday-month-next" aria-label="下一个月" ${
              month === "2026-10" ? "disabled" : ""
            }>${icon("chevron-right")}</button>
          </div>
          <button class="btn btn-sm btn-outline" data-action="open-holiday-form">${icon("plus")} 添加</button>
        </div>
      </div>
      <div class="panel-body">
        ${renderMiniCalendar(month, { big: true, useSelected: false })}
        <div class="holiday-list" style="margin-top:10px;border:1px solid var(--border);border-radius:9px;overflow:hidden">
          ${
            holidays.length
              ? holidays
                  .map(
                    (h) => `<div class="holiday-row">
                      <span class="holiday-date">${esc(h.date.slice(5))}</span>
                      <span class="holiday-name"><strong>${esc(h.name)}</strong><div class="sub">${esc(
                        h.note || "",
                      )}</div></span>
                      <span class="holiday-type">${
                        h.dayType === "holiday"
                          ? `<span class="badge badge-red">法定节假日</span>`
                          : `<span class="badge badge-blue">调休上班</span>`
                      }</span>
                      <button class="btn btn-sm btn-ghost danger-text" data-action="delete-holiday" data-date="${
                        h.date
                      }" aria-label="删除 ${esc(h.name)}">${icon("trash")}</button>
                    </div>`,
                  )
                  .join("")
              : `<div class="empty" style="padding:18px"><p style="font-size:10.5px">本月没有节假日；周末按常规处理。</p></div>`
          }
        </div>
        <div class="inline" style="margin-top:9px">
          <button class="btn btn-sm btn-outline" data-action="copy-holidays">${icon("copy")} 复制上一年</button>
          <span class="sub">本期只做界面维护 + 复制上一年，不做 Excel 批量导入。</span>
        </div>
      </div>
    </div>`;
  }

  /* ---------------------------------------------------------------- shifts */

  const COLOR_HEX = {
    blue: "#2f6bfe",
    sky: "#0ea5e9",
    green: "#16a34a",
    amber: "#f59e0b",
    purple: "#a855f7",
    indigo: "#6366f1",
    pink: "#ec4899",
  };

  function shiftReferenceCounts(code) {
    let plans = 0;
    let enabledPlans = 0;
    let entries = 0;
    for (const plan of db.plans) {
      const used = Object.values(plan.weekdays || {}).flat().includes(code) ||
        Object.values(plan.dayOverrides || {}).flat().includes(code);
      if (used) {
        plans += 1;
        if (plan.status === "enabled") enabledPlans += 1;
      }
    }
    for (const month of Object.keys(db.roster || {})) {
      for (const emp of Object.values(db.roster[month] || {})) {
        for (const entry of Object.values(emp)) {
          if (entry.shifts && entry.shifts.includes(code)) entries += 1;
        }
      }
    }
    return { plans, enabledPlans, entries };
  }

  function renderShiftsPage({ embedded } = {}) {
    if (state.companyId === "c2") {
      return embedded ? renderCompanyEmpty() : pageHead("班次", "当前公司暂无班次") + renderCompanyEmpty();
    }
    return previewGuard(() => {
      const head = embedded
        ? ""
        : pageHead(
            "班次",
            "公司级可复用的上下班时间模板。展开时把名称、起止、跨天、午休段与休息扣除快照进排班明细；之后编辑班次不改写历史快照。",
            `<button class="btn btn-primary btn-sm" data-action="open-shift-form">${icon(
              "plus",
            )} 新建班次</button>`,
          );
      return `${head}
        ${embedded ? `<div class="month-bar" style="padding:9px 12px"><span class="sub">公司级班次模板 · 不随月份变化</span><span class="spacer"></span><button class="btn btn-primary btn-sm" data-action="open-shift-form">${icon("plus")} 新建班次</button></div>` : ""}
        <div class="panel">
          <div class="table-wrap">
            <table class="table">
              <thead><tr><th>编码</th><th>班次名称</th><th>上班</th><th>下班</th><th>跨天</th><th>午休段</th><th>休息扣除</th><th>颜色</th><th>被引用</th><th>状态</th><th>操作</th></tr></thead>
              <tbody>
                ${db.shifts
                  .map((shift) => {
                    const refs = shiftReferenceCounts(shift.code);
                    return `<tr>
                      <td><span class="shift-code shift-${SHIFT_CLASS[shift.code] || "ADM"}">${esc(
                        shift.code,
                      )}</span></td>
                      <td class="cell-strong">${esc(shift.name)}<div class="cell-sub">${esc(
                        shift.note || "",
                      )}</div></td>
                      <td>${esc(shift.start)}</td>
                      <td>${esc(shift.end)}</td>
                      <td>${shift.crossDay ? `<span class="badge badge-indigo">跨天</span>` : `<span class="sub">否</span>`}</td>
                      <td>${shift.breakStart ? `${shift.breakStart}–${shift.breakEnd}` : `<span class="sub">—</span>`}</td>
                      <td>${shift.restMinutes} 分钟</td>
                      <td><span class="color-dot" style="background:${
                        COLOR_HEX[shift.color] || "#2f6bfe"
                      }"></span></td>
                      <td><div>${refs.plans} 张方案</div><div class="cell-sub">${refs.entries} 条明细</div></td>
                      <td>${shift.active === false ? `<span class="badge badge-gray">停用</span>` : `<span class="badge badge-green">启用</span>`}</td>
                      <td class="td-actions">
                        <button class="btn btn-sm btn-ghost" data-action="open-shift-form" data-code="${
                          shift.code
                        }">${icon("edit")} 编辑</button>
                        <button class="btn btn-sm btn-ghost ${shift.active === false ? "" : "danger-text"}" data-action="toggle-shift" data-code="${
                          shift.code
                        }">${shift.active === false ? "启用" : "停用"}</button>
                      </td>
                    </tr>`;
                  })
                  .join("")}
              </tbody>
            </table>
          </div>
          <div class="table-foot">
            <span>停用：有启用方案引用时阻止；已有明细不阻止，历史显示快照。删除：被任意方案或明细引用时阻止。</span>
            <span class="spacer"></span>
            <span class="sub">仅班次有业务编码</span>
          </div>
        </div>`;
    });
  }

  function renderShiftFormOverlay(o) {
    const draft = state.draft;
    if (!draft) return "";
    const isEdit = !!draft.originalCode;
    const colors = Object.keys(COLOR_HEX);
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true" aria-labelledby="shift-form-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="shift-form-title">${isEdit ? "编辑班次" : "新建班次"}</h2><p class="modal-sub">公司内可复用；展开时快照进员工日排班明细</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          ${draft.error ? `<div class="banner danger">${icon("alert")}<div>${esc(draft.error)}</div></div>` : ""}
          <div class="form-grid two">
            <div class="field"><label>班次编码 <span class="required-dot">*</span></label><input class="input" data-form="code" value="${esc(
              draft.code,
            )}" ${isEdit ? "disabled" : ""} placeholder="如 EARLY" data-autofocus /></div>
            <div class="field"><label>班次名称 <span class="required-dot">*</span></label><input class="input" data-form="name" value="${esc(
              draft.name,
            )}" placeholder="如 早班" /></div>
            <div class="field"><label>上班时间</label><input class="input" type="time" data-form="start" value="${esc(
              draft.start,
            )}" /></div>
            <div class="field"><label>下班时间</label><input class="input" type="time" data-form="end" value="${esc(
              draft.end,
            )}" /></div>
            <div class="field"><label>跨天班次</label>${ruleSwitch("下班时间落在次日", "crossDay", !!draft.crossDay, "如 22:00–06:00；结束时间早于开始时间即视为跨天")}</div>
            <div class="field"><label>休息扣除（分钟）</label><input class="input" type="number" min="0" data-form="restMinutes" value="${esc(
              draft.restMinutes,
            )}" /></div>
            <div class="field"><label>午休开始</label><input class="input" type="time" data-form="breakStart" value="${esc(
              draft.breakStart || "",
            )}" /></div>
            <div class="field"><label>午休结束</label><input class="input" type="time" data-form="breakEnd" value="${esc(
              draft.breakEnd || "",
            )}" /></div>
          </div>
          <div class="field" style="margin-top:12px"><label>日历展示色</label>
            <div class="color-swatches">${colors
              .map(
                (c) => `<button class="color-swatch ${
                  draft.color === c ? "active" : ""
                }" style="background:${COLOR_HEX[c]}" data-action="shift-color" data-color="${c}" aria-label="${c}"></button>`,
              )
              .join("")}</div>
          </div>
          <div class="field" style="margin-top:12px"><label>备注</label><textarea class="input" data-form="note" rows="2">${esc(
            draft.note || "",
          )}</textarea></div>
          <div class="notice info" style="margin-top:12px">${icon(
            "info",
          )}<div>午休段与休息扣除只影响工时口径；填写午休段后，若开启「午休 4 次卡」，该班次一天需要 4 次卡。</div></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="save-shift">${isEdit ? "保存修改" : "创建班次"}</button>
        </div>
      </div>`;
  }

  function renderShiftsOverlay() {
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card xl" role="dialog" aria-modal="true" aria-labelledby="shifts-overlay-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="shifts-overlay-title">班次管理</h2><p class="modal-sub">公司级模板；编辑不影响已生成明细快照</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">${renderShiftsPage({ embedded: true })}</div>
      </div>`;
  }

  function renderHolidayFormOverlay() {
    const draft = state.draft || {};
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="holiday-form-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="holiday-form-title">添加节假日</h2><p class="modal-sub">公司级；同日只能有一条记录</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="form-grid two">
            <div class="field"><label>日期 <span class="required-dot">*</span></label><input class="input" type="date" data-form="date" value="${esc(
              draft.date || `${state.holidayMonth}-01`,
            )}" data-autofocus /></div>
            <div class="field"><label>名称 <span class="required-dot">*</span></label><input class="input" data-form="name" value="${esc(
              draft.name || "",
            )}" placeholder="如 中秋节 / 调休上班" /></div>
            <div class="field"><label>日期类型</label>
              <select class="select" data-form="dayType">
                <option value="holiday" ${
                  (draft.dayType || "holiday") === "holiday" ? "selected" : ""
                }>法定节假日</option>
                <option value="adjusted_workday" ${
                  draft.dayType === "adjusted_workday" ? "selected" : ""
                }>调休上班</option>
              </select>
            </div>
            <div class="field"><label>备注</label><input class="input" data-form="note" value="${esc(
              draft.note || "",
            )}" placeholder="可选" /></div>
          </div>
          <div class="notice info" style="margin-top:12px">${icon(
            "info",
          )}<div>调休上班日即使落在周末也按工作日；法定节假日优先于周末。修改只把草稿 / 已计算月份标记过期。</div></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="save-holiday">保存</button>
        </div>
      </div>`;
  }

  function renderOverrideFormOverlay(o) {
    const plan = Data.getPlan(db, o.id);
    if (!plan) return "";
    const override = db.planRuleOverrides[plan.id] || {};
    const fields = [
      ["late_grace_min", "迟到宽限（分钟）"],
      ["early_grace_min", "早退宽限（分钟）"],
      ["ot_threshold_min", "加班起算（分钟）"],
      ["ot_max_min", "单日加班上限（分钟）"],
      ["absent_deduct_per_day", "旷工每日（元）"],
      ["late_deduct_per_occurrence", "迟到每次（元）"],
      ["early_deduct_per_occurrence", "早退每次（元）"],
      ["missing_punch_deduct_per_occurrence", "缺卡每张（元）"],
    ];
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true" aria-labelledby="override-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="override-title">方案规则覆盖 · ${esc(
            plan.name,
          )}</h2><p class="modal-sub">留空表示继承公司默认；只覆盖填写字段</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="rule-grid">
            ${fields
              .map(
                ([key, label]) => `<div class="rule-field">
                  <label>${esc(label)}</label>
                  <input class="input" type="number" min="0" data-override="${key}" value="${
                    override[key] === undefined ? "" : esc(override[key])
                  }" placeholder="继承公司默认：${esc(db.rules[key])}" />
                  <div class="hint">${override[key] === undefined ? "当前继承公司默认" : "当前覆盖"}</div>
                </div>`,
              )
              .join("")}
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="save-override" data-id="${plan.id}">保存覆盖</button>
        </div>
      </div>`;
  }

  /* ================================================================ overlays */

  function renderOverlayRoot() {
    const root = document.getElementById("overlay-root");
    if (!root) return;
    let html = "";
    if (state.overlay) html += renderOverlay(state.overlay);
    if (state.toast) {
      html += `<div class="toast ${state.toast.type}">${icon(
        state.toast.type === "error" ? "alert" : "check",
      )}<span>${esc(state.toast.message)}</span></div>`;
    }
    root.innerHTML = html;
  }

  function renderOverlay(o) {
    const map = {
      "day-sheet": renderDaySheetOverlay,
      "day-bulk": renderDayBulkOverlay,
      "plan-day": renderPlanDayOverlay,
      exception: renderExceptionOverlay,
      "plan-editor": renderPlanEditorOverlay,
      "batch-fill": renderBatchFillOverlay,
      "copy-month": renderCopyMonthOverlay,
      "sync-people": renderSyncPeopleOverlay,
      conflicts: renderConflictsOverlay,
      "import-wizard": renderImportWizardOverlay,
      "batch-detail": renderBatchDetailOverlay,
      "result-drawer": renderResultDrawer,
      "adjust-form": renderAdjustFormOverlay,
      "employee-summary": renderEmployeeSummaryOverlay,
      "holiday-form": renderHolidayFormOverlay,
      "override-form": renderOverrideFormOverlay,
      "shift-form": renderShiftFormOverlay,
      "shifts-overlay": renderShiftsOverlay,
      "confirm-recalc": renderRecalcOverlay,
      "confirm-confirm": renderConfirmMonthOverlay,
      "confirm-lock": renderLockOverlay,
      unlock: renderUnlockOverlay,
      export: renderExportOverlay,
      snapshot: renderSnapshotOverlay,
      blocked: renderBlockedOverlay,
      confirm: renderGenericConfirmOverlay,
      flow: renderFlowOverlay,
      diff: renderDiffOverlay,
      questions: renderQuestionsOverlay,
    };
    return (map[o.type] || (() => ""))(o);
  }

  /* __APPEND__ */

  /* ================================================================ schedule overlays */

  function renderDaySheetOverlay(o) {
    const date = o.date;
    const employees = scopedEmployees();
    const byShift = {};
    const rest = [];
    const unscheduled = [];
    for (const emp of employees) {
      const entry = Data.rosterEntry(db, state.month, emp.id, date);
      if (!entry) {
        unscheduled.push(emp);
        continue;
      }
      if (entry.state === "rest") {
        rest.push({ emp, entry });
        continue;
      }
      for (const code of entry.shifts) {
        (byShift[code] || (byShift[code] = [])).push({ emp, entry });
      }
    }
    const codes = Object.keys(byShift).sort(
      (a, b) => Data.toMinutes(getShift(a)?.start || "00:00") - Data.toMinutes(getShift(b)?.start || "00:00"),
    );
    const totalWork = codes.reduce((sum, code) => sum + byShift[code].length, 0);
    const editable = isEditable();
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card xl" role="dialog" aria-modal="true" aria-labelledby="day-sheet-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="day-sheet-title">${dateCN(date)} · 谁上班</h2><p class="modal-sub">${esc(
            currentCompany().name,
          )} · ${Data.dayTypeLabel(db, date)} · 上班 ${totalWork} 人次 · 休息 ${rest.length} 人 · 未排班 ${unscheduled.length} 人</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          ${dayTypeBadge(date)}
          <div class="day-list" style="margin-top:10px">
            ${
              codes.length
                ? codes
                    .map(
                      (code) => `<div class="day-group">
                        <div class="day-group-head">${shiftChip(code, "lg")}<span>${esc(
                          getShift(code)?.name || code,
                        )}</span><span class="sub">${shiftTime(code)} · ${byShift[code].length} 人</span></div>
                        ${byShift[code]
                          .map(
                            ({ emp, entry }) => `<div class="day-person">
                              <span class="person-name">${esc(emp.name)}</span>
                              <span class="person-dept">${esc(Data.deptPath(db, emp.deptId))}</span>
                              <span class="person-source">${
                                entry.source === "manual" ? "人工例外" : "方案展开"
                              }</span>
                              <span class="person-shifts">${entry.shifts
                                .map((c) => shiftChip(c))
                                .join("")}</span>
                              <button class="btn btn-sm btn-ghost" data-action="open-exception" data-employee="${
                                emp.id
                              }" data-date="${date}" ${editable ? "" : "disabled"}>调整</button>
                            </div>`,
                          )
                          .join("")}
                      </div>`,
                    )
                    .join("")
                : `<div class="empty" style="padding:24px"><div class="empty-icon">${icon(
                    "coffee",
                  )}</div><h3 style="font-size:12px">这一天没有上班员工</h3><p style="font-size:10.5px">可能是休息日、节假日，或尚未同步人员。</p></div>`
            }
          </div>
          <div class="summary-strip" style="margin-top:12px;margin-bottom:0">
            <span>休息 <strong>${rest.length}</strong> 人</span>
            <span>未排班 <strong>${unscheduled.length}</strong> 人</span>
            <span class="sep"></span>
            <span class="sub">人工例外在方案重展开时永远保留。</span>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">关闭</button>
          <button class="btn btn-outline" data-action="open-day-bulk" data-date="${date}" ${
            editable ? "" : "disabled"
          }>${icon("users")} 批量设置该日</button>
          <button class="btn btn-primary" data-action="open-exception" data-date="${date}" data-employee="${
            employees[0]?.id || ""
          }" ${editable ? "" : "disabled"}>${icon("edit")} 新增人工例外</button>
        </div>
      </div>`;
  }

  function renderDayBulkOverlay(o) {
    const draft = state.draft || {};
    const employees = scopedEmployees();
    const selected = new Set(draft.employeeIds || []);
    const date = draft.date || o.date;
    const count = selected.size;
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true" aria-labelledby="day-bulk-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="day-bulk-title">批量设置 · ${dateCN(
            date,
          )}</h2><p class="modal-sub">为多名员工创建人工例外；单事务保存，全成或全败</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="inline" style="margin-bottom:8px">
            <span class="section-title" style="margin:0">选择员工</span>
            <span class="spacer"></span>
            <button class="btn btn-sm btn-ghost" data-action="bulk-select-all">全选</button>
            <button class="btn btn-sm btn-ghost" data-action="bulk-select-none">清空</button>
          </div>
          <div class="check-grid">
            ${employees
              .map((emp) => {
                const entry = Data.rosterEntry(db, state.month, emp.id, date);
                return `<label class="check-chip ${selected.has(emp.id) ? "on" : ""}">
                  <input type="checkbox" data-check="bulk-employee" value="${emp.id}" ${
                    selected.has(emp.id) ? "checked" : ""
                  } />
                  <span>${esc(emp.name)}</span>
                  <span class="sub">${entry ? (entry.state === "work" ? entry.shifts.join("/") : "休息") : "未排班"}</span>
                </label>`;
              })
              .join("")}
          </div>
          <div class="section-title">目标状态</div>
          <div class="segmented">
            <button class="${(draft.state || "work") === "work" ? "active" : ""}" data-action="bulk-state" data-state="work">${icon(
              "briefcase",
            )} 上班</button>
            <button class="${draft.state === "rest" ? "active" : ""}" data-action="bulk-state" data-state="rest">${icon(
              "coffee",
            )} 休息</button>
          </div>
          ${
            (draft.state || "work") === "work"
              ? `<div class="section-title">班次（可多选）</div>
                <div class="check-grid">
                  ${db.shifts
                    .map(
                      (shift) => `<button class="check-chip ${
                        (draft.shifts || []).includes(shift.code) ? "on" : ""
                      }" data-action="bulk-shift" data-code="${shift.code}">${shiftChip(
                        shift.code,
                      )}<span>${esc(shift.name)}</span><span class="sub">${shift.start}–${shift.end}</span></button>`,
                    )
                    .join("")}
                </div>`
              : ""
          }
          <div class="field" style="margin-top:12px"><label>备注</label><textarea class="input" data-form="note" rows="2" placeholder="例如：临时调班、设备检修">${esc(
            draft.note || "",
          )}</textarea></div>
          <div class="notice info" style="margin-top:10px">${icon(
            "info",
          )}<div>将为已选中的 <strong>${count}</strong> 名员工创建人工例外；原方案明细被覆盖，重展开不会覆盖这些记录。</div></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="save-day-bulk" ${
            count && (draft.state === "rest" || (draft.shifts || []).length) ? "" : "disabled"
          }>保存 ${count} 条例外</button>
        </div>
      </div>`;
  }

  function renderPlanDayOverlay(o) {
    const draft = state.draft || {};
    const plan = Data.getPlan(db, draft.planId || o.id) || selectedPlan() || companyPlans()[0];
    if (!plan) return "";
    const date = draft.date || o.date;
    const shifts = draft.shifts || Data.planShiftsForDate(db, plan, date);
    const employees = planEmployeesFor(plan);
    const conflictPairs = [];
    const selectedShifts = shifts.map((c) => getShift(c)).filter(Boolean);
    for (let i = 0; i < selectedShifts.length; i++) {
      for (let j = i + 1; j < selectedShifts.length; j++) {
        const a = Data.shiftSpan(date, selectedShifts[i]);
        const b = Data.shiftSpan(date, selectedShifts[j]);
        if (Math.min(a.end, b.end) - Math.max(a.start, b.start) > 0) {
          conflictPairs.push([selectedShifts[i].name, selectedShifts[j].name]);
        }
      }
    }
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="plan-day-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="plan-day-title">方案日编辑 · ${dateCN(
            date,
          )}</h2><p class="modal-sub">${esc(plan.name)} · 影响 ${employees.length} 名员工</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          ${dayTypeBadge(date)}
          <div class="section-title">当天班次 <span class="sub">可多选；不选即休息</span></div>
          <div class="check-grid">
            ${db.shifts
              .map(
                (shift) => `<button class="check-chip ${
                  shifts.includes(shift.code) ? "on" : ""
                }" data-action="plan-day-shift" data-code="${shift.code}">${shiftChip(
                  shift.code,
                )}<span>${esc(shift.name)}</span><span class="sub">${shift.start}–${shift.end}${
                  shift.crossDay ? " 次日" : ""
                }</span></button>`,
              )
              .join("")}
          </div>
          ${
            conflictPairs.length
              ? `<div class="banner warn" style="margin-top:10px">${icon(
                  "alert",
                )}<div>班次时间重叠：${conflictPairs
                  .map(([a, b]) => `${esc(a)} / ${esc(b)}`)
                  .join("、")}。仅警告，不阻止保存。</div></div>`
              : ""
          }
          <div class="notice info" style="margin-top:10px">${icon(
            "info",
          )}<div>保存后会重展开该方案范围；人工例外不受影响。${
            isEditable() ? "当前月份已计算时，结果会标记为过期。" : "当前月份已确认或锁定，无法编辑。"
          }</div></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-outline" data-action="save-plan-day" data-empty="1">设为休息</button>
          <button class="btn btn-primary" data-action="save-plan-day" ${
            isEditable() ? "" : "disabled"
          }>保存班次</button>
        </div>
      </div>`;
  }

  function renderExceptionOverlay(o) {
    const draft = state.draft || {};
    const emp = getEmployee(draft.employeeId || o.employee);
    if (!emp) return "";
    const date = draft.date || o.date;
    const entry = Data.rosterEntry(db, state.month, emp.id, date);
    const plan = entry?.planId ? Data.getPlan(db, entry.planId) : Data.resolvePlan(db, state.month, emp, date);
    const isManual = entry?.source === "manual";
    const stateValue = draft.state || (entry ? entry.state : "work");
    const shifts = draft.shifts || (entry ? entry.shifts.slice() : []);
    const selectedShifts = shifts.map((c) => getShift(c)).filter(Boolean);
    const conflicts = [];
    for (let i = 0; i < selectedShifts.length; i++) {
      for (let j = i + 1; j < selectedShifts.length; j++) {
        const a = Data.shiftSpan(date, selectedShifts[i]);
        const b = Data.shiftSpan(date, selectedShifts[j]);
        if (Math.min(a.end, b.end) - Math.max(a.start, b.start) > 0) {
          conflicts.push(`${selectedShifts[i].name} / ${selectedShifts[j].name}`);
        }
      }
    }
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true" aria-labelledby="exception-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="exception-title">人工例外 · ${esc(
            emp.name,
          )}</h2><p class="modal-sub">${dateCN(date)} · ${esc(Data.deptPath(db, emp.deptId))}</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          ${dayTypeBadge(date)}
          <div class="kv-list" style="margin:10px 0 14px">
            <span class="k">当前来源</span><span>${
              entry
                ? entry.source === "manual"
                  ? "人工例外"
                  : `方案展开 · ${esc(plan?.name || "")}`
                : "未排班"
            }</span>
            <span class="k">当前班次</span><span>${
              entry && entry.state === "work" ? entry.shifts.map((c) => getShift(c)?.name || c).join("、") : entry?.state === "rest" ? "休息" : "未排班"
            }</span>
            <span class="k">方案覆盖</span><span>${plan ? esc(plan.name) : "无方案覆盖"}</span>
          </div>
          <div class="segmented" style="margin-bottom:10px">
            <button class="${stateValue === "work" ? "active" : ""}" data-action="exception-state" data-state="work">${icon(
              "briefcase",
            )} 上班</button>
            <button class="${stateValue === "rest" ? "active" : ""}" data-action="exception-state" data-state="rest">${icon(
              "coffee",
            )} 休息</button>
          </div>
          ${
            stateValue === "work"
              ? `<div class="section-title">班次</div>
                <div class="check-grid">
                  ${db.shifts
                    .map(
                      (shift) => `<button class="check-chip ${
                        shifts.includes(shift.code) ? "on" : ""
                      }" data-action="exception-shift" data-code="${shift.code}">${shiftChip(
                        shift.code,
                      )}<span>${esc(shift.name)}</span><span class="sub">${shift.start}–${shift.end}${
                        shift.crossDay ? " 次日" : ""
                      }</span></button>`,
                    )
                    .join("")}
                </div>`
              : ""
          }
          ${
            conflicts.length
              ? `<div class="banner warn" style="margin-top:10px">${icon(
                  "alert",
                )}<div>所选班次时间重叠：${conflicts.map(esc).join("、")}。仅警告，不阻止保存。</div></div>`
              : ""
          }
          <div class="field" style="margin-top:12px"><label>备注</label><textarea class="input" data-form="note" rows="2" placeholder="例如：临时调班、设备检修、主管确认">${esc(
            draft.note !== undefined ? draft.note : entry?.note || "",
          )}</textarea></div>
          ${
            !isEditable()
              ? `<div class="banner warn" style="margin-top:10px">${icon(
                  "lock",
                )}<div>本月已确认或锁定，人工例外只读。请先在考勤结果撤销确认或解锁。</div></div>`
              : ""
          }
        </div>
        <div class="modal-foot">
          ${
            isManual
              ? `<button class="btn btn-ghost danger-text" data-action="delete-exception">${icon(
                  "trash",
                )} 删除例外</button>`
              : ""
          }
          <span class="spacer"></span>
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="save-exception" ${
            isEditable() && (stateValue === "rest" || shifts.length) ? "" : "disabled"
          }>保存例外</button>
        </div>
      </div>`;
  }

  function renderPlanEditorOverlay(o) {
    const draft = state.draft;
    if (!draft) return "";
    const isNew = !draft.id;
    const scopeType = draft.scopeType || "all";
    const targets = {
      dept: db.departments.filter((d) => d.companyId === state.companyId),
      position: db.positions,
      employee: companyEmployees().filter((e) => e.status !== "resigned"),
    }[scopeType] || [];
    const selectedScopes = new Set(draft.scopeIds || []);
    const coverage = activeEmployees().filter((emp) => {
      if (scopeType === "all") return true;
      if (scopeType === "dept") {
        return (draft.scopeIds || []).some((id) =>
          new Set(Data.deptDescendants(db, id)).has(emp.deptId),
        );
      }
      if (scopeType === "position") return (draft.scopeIds || []).includes(emp.positionId);
      return (draft.scopeIds || []).includes(emp.id);
    }).length;
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card lg" role="dialog" aria-modal="true" aria-labelledby="plan-editor-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="plan-editor-title">${isNew ? "新建排班方案" : "编辑排班方案"}</h2><p class="modal-sub">${monthCN(
            state.month,
          )} · 保存即展开；覆盖 ${coverage} 名员工</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          ${draft.error ? `<div class="banner danger">${icon("alert")}<div>${esc(draft.error)}</div></div>` : ""}
          <div class="form-grid two">
            <div class="field"><label>方案名称 <span class="required-dot">*</span></label><input class="input" data-form="name" value="${esc(
              draft.name || "",
            )}" placeholder="如 生产部早中班" data-autofocus /></div>
            <div class="field"><label>月份</label><input class="input" value="${monthCN(
              state.month,
            )}" disabled /></div>
          </div>
          <div class="section-title">适用范围</div>
          <div class="segmented">
            ${[
              ["all", "全公司"],
              ["dept", "按部门"],
              ["position", "按岗位"],
              ["employee", "按员工"],
            ]
              .map(
                ([key, label]) =>
                  `<button class="${scopeType === key ? "active" : ""}" data-action="plan-scope-type" data-scope-type="${key}">${label}</button>`,
              )
              .join("")}
          </div>
          ${
            scopeType !== "all"
              ? `<div class="check-grid" style="margin-top:9px">
                  ${targets
                    .map((item) => {
                      const value = item.id;
                      return `<label class="check-chip ${selectedScopes.has(value) ? "on" : ""}">
                        <input type="checkbox" data-check="plan-scope" value="${value}" ${
                          selectedScopes.has(value) ? "checked" : ""
                        } />
                        <span>${esc(item.name)}</span>
                      </label>`;
                    })
                    .join("")}
                </div>`
              : `<div class="notice info" style="margin-top:9px">${icon(
                  "info",
                )}<div>全公司方案是兜底方案；同月已有全公司方案时不能保存第二张（409）。</div></div>`
          }
          <div class="section-title">按星期模式 <span class="sub">没有班次的星期 = 休息；保存后仍按日期展开</span></div>
          <div class="weekday-grid">
            ${WEEKDAYS.map((label, wd) => {
              const codes = draft.weekdays?.[wd] || [];
              return `<div class="weekday-label">周${label}</div>
                <div class="weekday-shifts">${db.shifts
                  .map(
                    (shift) => `<button class="shift-toggle shift-${SHIFT_CLASS[shift.code] || "ADM"} ${
                      codes.includes(shift.code) ? "on" : ""
                    }" data-action="weekday-shift" data-wd="${wd}" data-code="${shift.code}">${esc(
                      shift.name,
                    )}</button>`,
                  )
                  .join("")}</div>`;
            }).join("")}
          </div>
          <div class="section-title">方案级规则覆盖 <span class="sub">留空继承公司默认</span></div>
          <div class="rule-grid">
            ${[
              ["late_grace_min", "迟到宽限（分钟）"],
              ["ot_threshold_min", "加班起算（分钟）"],
              ["absent_deduct_per_day", "旷工每日（元）"],
              ["missing_punch_deduct_per_occurrence", "缺卡每张（元）"],
            ]
              .map(
                ([key, label]) => `<div class="rule-field"><label>${esc(label)}</label><input class="input" type="number" min="0" data-plan-override="${key}" value="${
                  draft.overrides?.[key] === undefined ? "" : esc(draft.overrides[key])
                }" placeholder="继承 ${esc(db.rules[key])}" /></div>`,
              )
              .join("")}
          </div>
          <div class="field" style="margin-top:12px"><label>备注</label><textarea class="input" data-form="note" rows="2">${esc(
            draft.note || "",
          )}</textarea></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="save-plan">${isNew ? "保存并展开" : "保存并重新展开"}</button>
        </div>
      </div>`;
  }

  function batchFillPreview(draft) {
    const plan = Data.getPlan(db, draft.planId);
    if (!plan) return { days: 0, employees: 0, personDays: 0 };
    const mode = draft.mode || "workdays";
    if (mode === "clear") return { days: 0, employees: planEmployeesFor(plan).length, personDays: 0 };
    const weekdays = mode === "month" ? [0, 1, 2, 3, 4, 5, 6] : draft.weekdays || [];
    const dates = Data.dateList(state.month).filter((date) => {
      if (!weekdays.includes(Data.weekdayIndex(date))) return false;
      const h = Data.holidayOf(db, date);
      return !(h && h.dayType === "holiday");
    });
    const employees = planEmployeesFor(plan).length;
    return { days: dates.length, employees, personDays: dates.length * employees };
  }

  function renderBatchFillOverlay() {
    const draft = state.draft || {};
    const plan = Data.getPlan(db, draft.planId) || selectedPlan() || companyPlans()[0];
    const preview = batchFillPreview(draft);
    const mode = draft.mode || "workdays";
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true" aria-labelledby="batch-fill-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="batch-fill-title">批量填充</h2><p class="modal-sub">${monthCN(
            state.month,
          )} · 只写方案模式，保存后统一展开</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="field"><label>目标方案</label>
            <select class="select" data-select="batch-plan" style="width:100%">
              ${companyPlans()
                .map(
                  (p) =>
                    `<option value="${p.id}" ${plan?.id === p.id ? "selected" : ""}>${esc(
                      p.name,
                    )} · ${esc(planScopeLabel(p))}</option>`,
                )
                .join("")}
            </select>
          </div>
          <div class="section-title">填充方式</div>
          <div class="segmented">
            <button class="${mode === "workdays" ? "active" : ""}" data-action="batch-mode" data-mode="workdays">工作日填充</button>
            <button class="${mode === "month" ? "active" : ""}" data-action="batch-mode" data-mode="month">整月填充</button>
            <button class="${mode === "clear" ? "active" : ""}" data-action="batch-mode" data-mode="clear">整月清空</button>
          </div>
          ${
            mode === "workdays"
              ? `<div class="section-title">选择星期</div>
                <div class="check-grid">
                  ${WEEKDAYS.map(
                    (label, wd) => `<button class="check-chip ${
                      (draft.weekdays || []).includes(wd) ? "on" : ""
                    }" data-action="batch-weekday" data-wd="${wd}">周${label}</button>`,
                  ).join("")}
                </div>`
              : ""
          }
          ${
            mode !== "clear"
              ? `<div class="section-title">填充班次 <span class="sub">可多选；同一天可排多个班次</span></div>
                <div class="check-grid">
                  ${db.shifts
                    .map(
                      (shift) => `<button class="check-chip ${
                        (draft.shifts || []).includes(shift.code) ? "on" : ""
                      }" data-action="batch-shift" data-code="${shift.code}">${shiftChip(
                        shift.code,
                      )}<span>${esc(shift.name)}</span><span class="sub">${shift.start}–${shift.end}</span></button>`,
                    )
                    .join("")}
                </div>`
              : `<div class="banner warn" style="margin-top:10px">${icon(
                  "alert",
                )}<div>整月清空会删除该方案在所有星期的班次模式；人工例外不受影响。</div></div>`
          }
          <div class="section-title">预览</div>
          <div class="preview-stats" style="grid-template-columns:repeat(3,1fr)">
            <div class="preview-stat"><div class="label">影响日期</div><div class="value">${preview.days}</div></div>
            <div class="preview-stat"><div class="label">覆盖员工</div><div class="value">${preview.employees}</div></div>
            <div class="preview-stat"><div class="label">预计人日</div><div class="value ok">${preview.personDays}</div></div>
          </div>
          <div class="notice info">${icon(
            "info",
          )}<div>节假日（法定节假日）自动跳过；调休上班日按所选星期处理。保存后若月份已计算，结果标记为过期。</div></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="apply-batch-fill" ${
            plan && (mode === "clear" || (draft.shifts || []).length) ? "" : "disabled"
          }>应用到方案</button>
        </div>
      </div>`;
  }

  function renderCopyMonthOverlay() {
    const draft = state.draft || {};
    const sourceMonth = state.month;
    const targetMonth = sourceMonth === "2026-09" ? "2026-10" : null;
    const plan = Data.getPlan(db, draft.planId) || selectedPlan() || companyPlans()[0];
    if (!targetMonth) {
      return `<div class="modal-backdrop" data-action="close-overlay"></div>
        <div class="modal" role="dialog" aria-modal="true">
          <div class="modal-head"><div><h2 class="modal-title">复制到下月</h2><p class="modal-sub">只支持下一个自然月</p></div><button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon(
            "x",
          )}</button></div>
          <div class="modal-body"><div class="banner warn">${icon(
            "alert",
          )}<div>当前是 ${monthCN(sourceMonth)}，没有可复制到的下一个演示月份。请先切换到 2026 年 9 月。</div></div></div>
          <div class="modal-foot"><button class="btn btn-outline" data-action="close-overlay">知道了</button></div>
        </div>`;
    }
    const targetDays = Data.daysInMonth(targetMonth);
    const sourceDays = Data.daysInMonth(sourceMonth);
    const manualTotal = Object.values(db.exceptions).filter(
      (ex) => Data.monthOf(ex.date) === sourceMonth,
    ).length;
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true" aria-labelledby="copy-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="copy-title">复制到 ${monthCN(
            targetMonth,
          )}</h2><p class="modal-sub">复制方案定义并在目标月重新展开；不复制已展开明细</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="field"><label>复制哪张方案</label>
            <select class="select" data-select="copy-plan" style="width:100%">
              ${companyPlans()
                .map(
                  (p) =>
                    `<option value="${p.id}" ${plan?.id === p.id ? "selected" : ""}>${esc(
                      p.name,
                    )} · ${esc(planScopeLabel(p))}</option>`,
                )
                .join("")}
            </select>
          </div>
          <div class="kv-list" style="margin-top:12px">
            <span class="k">源月份</span><span>${monthCN(sourceMonth)} · ${sourceDays} 天</span>
            <span class="k">目标月份</span><span>${monthCN(targetMonth)} · ${targetDays} 天</span>
            <span class="k">范围</span><span>${esc(plan ? planScopeLabel(plan) : "")}</span>
            <span class="k">覆盖员工</span><span>${plan ? planEmployeesFor(plan).length : 0} 人</span>
            <span class="k">人工例外</span><span>${manualTotal} 条（默认不复制）</span>
          </div>
          ${
            targetDays > sourceDays
              ? `<div class="banner warn" style="margin-top:10px">${icon(
                  "alert",
                )}<div><strong>大小月提示：</strong>目标月多出 ${targetDays - sourceDays} 天（${targetMonth}-${
                  sourceDays + 1
                } 起），没有对应日期号，按休息处理，建议复制后补排。</div></div>`
              : targetDays < sourceDays
                ? `<div class="banner warn" style="margin-top:10px">${icon(
                    "alert",
                  )}<div>目标月比源月少 ${sourceDays - targetDays} 天；源月末尾的日期号将被丢弃。</div></div>`
                : ""
          }
          <label class="filter-toggle" style="margin-top:10px"><input type="checkbox" data-check="copy-exceptions" ${
            draft.copyExceptions ? "checked" : ""
          } /> 同时复制人工例外（仅目标月存在的日期号）</label>
          <div class="notice info" style="margin-top:10px">${icon(
            "info",
          )}<div>目标月同精确度范围已有启用方案时会阻止复制（409）。节假日不复制；目标月使用自己的节假日日历与当前公司规则。</div></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="copy-month" ${
            plan ? "" : "disabled"
          }>${icon("copy")} 复制并展开</button>
        </div>
      </div>`;
  }

  function renderSyncPeopleOverlay() {
    const current = db.roster[state.month] || {};
    const prospective = Data.buildRoster(db, {
      month: state.month,
      includePending: true,
    });
    const countEntries = (roster) =>
      Object.values(roster).reduce((sum, per) => sum + Object.keys(per).length, 0);
    const currentCount = countEntries(current);
    const prospectiveCount = countEntries(prospective);
    const added = Math.max(0, prospectiveCount - currentCount);
    const removed = Math.max(0, currentCount - prospectiveCount);
    const pending = db.pendingEmployees.map((id) => getEmployee(id)).filter(Boolean);
    const resigned = companyEmployees().filter(
      (e) => e.status === "resigned" && Data.employedInMonth(e, state.month),
    );
    const manual = Object.values(db.exceptions).filter(
      (ex) => Data.monthOf(ex.date) === state.month,
    ).length;
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true" aria-labelledby="sync-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="sync-title">同步人员</h2><p class="modal-sub">按当前部门 / 岗位重算整月；人工例外保留</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          ${
            !isEditable()
              ? `<div class="banner warn">${icon(
                  "lock",
                )}<div>本月已确认或锁定，不能同步人员。请先撤销确认或解锁。</div></div>`
              : ""
          }
          <div class="preview-stats" style="grid-template-columns:repeat(3,1fr)">
            <div class="preview-stat"><div class="label">新增人日</div><div class="value ok">+${added}</div></div>
            <div class="preview-stat"><div class="label">移除人日</div><div class="value bad">-${removed}</div></div>
            <div class="preview-stat"><div class="label">保留人工例外</div><div class="value">${manual}</div></div>
          </div>
          <div class="section-title">新增 / 待同步</div>
          ${
            pending.length
              ? pending
                  .map(
                    (emp) => `<div class="adjust-item">
                      <div class="adjust-item-head">${esc(emp.name)} <span class="badge badge-orange">待同步</span></div>
                      <div class="adjust-values"><span>部门：<b>${esc(
                        Data.deptPath(db, emp.deptId),
                      )}</b></span><span>入职：<b>${esc(emp.hireDate)}</b></span></div>
                    </div>`,
                  )
                  .join("")
              : `<div class="sub">没有新增人员。</div>`
          }
          <div class="section-title">已离职 / 超出范围</div>
          ${
            resigned.length
              ? resigned
                  .map(
                    (emp) => `<div class="adjust-item"><div class="adjust-item-head">${esc(
                      emp.name,
                    )} <span class="badge badge-gray">已离职</span></div><div class="adjust-values"><span>离职日期：<b>${esc(
                      emp.resignDate,
                    )}</b></span></div></div>`,
                  )
                  .join("")
              : `<div class="sub">没有需要移除的人员。</div>`
          }
          <div class="notice info" style="margin-top:10px">${icon(
            "info",
          )}<div>基础管理没有调岗历史；同步按当前部门 / 岗位重算整月。新增人员的入职前日期不会生成明细。同步后若结果已计算，会标记为过期。</div></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="sync-people" ${
            isEditable() ? "" : "disabled"
          }>确认同步</button>
        </div>
      </div>`;
  }

  function renderConflictsOverlay() {
    const conflictList = Data.conflicts(db, state.month);
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal lg" role="dialog" aria-modal="true" aria-labelledby="conflict-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="conflict-title">排班冲突预览</h2><p class="modal-sub">同一天多个班次时间重叠；仅警告，不阻止保存</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          ${
            conflictList.length
              ? conflictList
                  .map((c) => {
                    const a = getShift(c.a);
                    const b = getShift(c.b);
                    return `<div class="adjust-item">
                      <div class="adjust-item-head">${esc(employeeName(c.employeeId))} · ${dateCN(
                        c.date,
                      )}<span class="sub">${esc(Data.deptPath(db, getEmployee(c.employeeId)?.deptId) || "")}</span></div>
                      <div class="adjust-values"><span>${shiftChip(c.a)} ${esc(a?.start)}–${esc(
                        a?.end,
                      )}</span><span>${shiftChip(c.b)} ${esc(b?.start)}–${esc(b?.end)}</span><span class="danger-text">时间重叠</span></div>
                    </div>`;
                  })
                  .join("")
              : `<div class="empty" style="padding:24px"><div class="empty-icon">${icon(
                  "check-circle",
                )}</div><h3 style="font-size:12px">没有时间重叠</h3><p style="font-size:10.5px">同一天多个班次首尾相接是允许的。</p></div>`
          }
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">知道了</button>
          ${
            conflictList.length
              ? `<button class="btn btn-primary" data-action="locate-conflict" data-date="${conflictList[0].date}" data-employee="${conflictList[0].employeeId}">定位到第一条</button>`
              : ""
          }
        </div>
      </div>`;
  }

  /* ================================================================ result drawer & month actions */

  function findResult(employeeId, date) {
    return resultsForMonth().find(
      (r) => r.employeeId === employeeId && r.date === date,
    );
  }

  function renderResultDrawer(o) {
    const r = findResult(o.employee, o.date);
    if (!r) return "";
    const emp = getEmployee(r.employeeId);
    const activeAdj = db.adjustments.find(
      (a) =>
        a.employeeId === r.employeeId &&
        a.date === r.date &&
        a.status === "active",
    );
    const history = db.adjustments.filter(
      (a) => a.employeeId === r.employeeId && a.date === r.date,
    );
    const ot = resultOtMinutes(r);
    const editable = isEditable();
    return `<div class="drawer-backdrop" data-action="close-overlay"></div>
      <aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        <div class="drawer-head">
          <div>
            <h2 id="drawer-title">${esc(emp?.name || r.employeeId)} · ${dateCN(r.date)}</h2>
            <div class="sub">${esc(Data.deptPath(db, emp?.deptId) || "")} · ${esc(
              emp?.no || "",
            )} · ${esc(r.dayTypeLabel)} · ${statusBadge(r.dayStatus)}</div>
          </div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="drawer-body">
          <div class="four-way">
            <div class="four-card">
              <h4>${icon("calendar")} 排班</h4>
              <div class="four-line"><span class="k">状态</span><span class="v">${esc(
                r.rosterStateLabel,
              )}</span></div>
              <div class="four-line"><span class="k">来源</span><span class="v">${
                r.source === "manual"
                  ? "人工例外"
                  : r.planId
                    ? esc(Data.getPlan(db, r.planId)?.name || "方案展开")
                    : "未排班"
              }</span></div>
              <div class="four-line"><span class="k">班次</span><span class="v">${
                r.shifts.length ? r.shifts.map((c) => getShift(c)?.name || c).join("、") : "—"
              }</span></div>
              <div class="four-line"><span class="k">排班工时</span><span class="v">${hoursLabel(
                r.scheduledMinutes,
              )}h</span></div>
            </div>
            <div class="four-card">
              <h4>${icon("clock")} 打卡</h4>
              ${
                r.punches.length
                  ? r.punches
                      .map(
                        (p) => `<div class="four-line"><span class="k">${
                          p.date !== r.date ? "次日 " : ""
                        }${esc(p.time)}</span><span class="v">${esc(p.result || "")}</span></div>`,
                      )
                      .join("")
                  : `<div class="four-empty">无有效打卡</div>`
              }
              ${
                r.punches.length
                  ? `<div class="four-line"><span class="k">迟到 / 早退</span><span class="v ${
                      r.lateMinutes || r.earlyMinutes ? "warn" : ""
                    }">${r.lateMinutes} / ${r.earlyMinutes} 分钟</span></div>`
                  : ""
              }
            </div>
            <div class="four-card">
              <h4>${icon("file")} OA 申请</h4>
              ${
                r.trips.length
                  ? r.trips
                      .map(
                        (t) =>
                          `<div class="four-line"><span class="k">${
                            t.kind === "business" ? "出差" : "外出"
                          }</span><span class="v">${esc(t.start.slice(11))}–${esc(
                            t.end.slice(11),
                          )}</span></div><div class="four-line"><span class="k">审批</span><span class="v">${esc(
                            t.approvalNo || "",
                          )}</span></div>`,
                      )
                      .join("")
                  : ""
              }
              ${
                r.leaves.length
                  ? r.leaves
                      .map(
                        (l) =>
                          `<div class="four-line"><span class="k">${esc(
                            l.kind === "paid" ? "带薪假" : l.kind === "comp" ? "补休" : "事假",
                          )}</span><span class="v">${l.days} 天</span></div>`,
                      )
                      .join("")
                  : ""
              }
              ${
                r.oaOtMinutes
                  ? `<div class="four-line"><span class="k">OA 加班</span><span class="v">${hoursLabel(
                      r.oaOtMinutes,
                    )}h</span></div>`
                  : ""
              }
              ${!r.trips.length && !r.leaves.length && !r.oaOtMinutes ? `<div class="four-empty">无 OA 申请</div>` : ""}
            </div>
            <div class="four-card">
              <h4>${icon("check-circle")} 结果</h4>
              <div class="four-line"><span class="k">出勤比例</span><span class="v">${r.attendanceFraction.toFixed(
                1,
              )}</span></div>
              <div class="four-line"><span class="k">实际工时</span><span class="v">${hoursLabel(
                r.workedMinutes,
              )}h</span></div>
              <div class="four-line"><span class="k">加班</span><span class="v">${hoursLabel(
                ot,
              )}h</span></div>
              <div class="four-line"><span class="k">缺卡张数</span><span class="v">${r.missingPunchCount}</span></div>
              <div class="four-line"><span class="k">扣款</span><span class="v bad">${money(
                r.deductionTotal,
              )}</span></div>
            </div>
          </div>

          ${renderResultTimeline(r)}

          <div class="section-title">班次结果 <span class="sub">一天多班逐班保留</span></div>
          ${
            r.shiftResults.length
              ? `<div class="table-wrap shift-result-table"><table class="table">
                  <thead><tr><th>班次</th><th>排班</th><th>上班卡</th><th>下班卡</th><th>午休卡</th><th>排班工时</th><th>实际工时</th><th>迟到 / 早退</th><th>缺卡</th><th>加班</th></tr></thead>
                  <tbody>${r.shiftResults
                    .map((sr) => {
                      const shift = sr.shift;
                      const breakText =
                        sr.breakPunches && sr.breakPunches.length
                          ? sr.breakPunches.map((p) => p.time).join(" / ")
                          : shift.breakStart
                            ? "缺"
                            : "—";
                      return `<tr>
                        <td>${shiftChipCode(shift.code)}</td>
                        <td><div>${esc(shift.start)}–${esc(shift.end)}</div><div class="cell-sub">${shift.restMinutes} 分钟休息</div></td>
                        <td>${sr.inPunch ? `${sr.inPunch.date !== r.date ? "次日 " : ""}${esc(sr.inPunch.time)}` : `<span class="danger-text">缺</span>`}</td>
                        <td>${sr.outPunch ? `${sr.outPunch.date !== r.date ? "次日 " : ""}${esc(sr.outPunch.time)}` : `<span class="danger-text">缺</span>`}</td>
                        <td>${esc(breakText)}</td>
                        <td>${hoursLabel(sr.scheduledMinutes)}h</td>
                        <td>${hoursLabel(sr.workedMinutes)}h</td>
                        <td>${sr.lateMinutes} / ${sr.earlyMinutes} 分钟</td>
                        <td>${sr.missingPunchCount}</td>
                        <td>${sr.otMinutes ? hoursLabel(sr.otMinutes) + "h" : "—"}</td>
                      </tr>`;
                    })
                    .join("")}</tbody>
                </table></div>`
              : `<div class="notice">${icon(
                  "info",
                )}<div>当天没有排班班次；结果按未排班 / 休息日规则处理。</div></div>`
          }

          <div class="section-title">差异与标记 <span class="sub">flags 保留计算语义</span></div>
          <div class="flags">${
            r.dayFlags.length
              ? r.dayFlags.map(flagChip).join("")
              : `<span class="flag-chip">无异常标记</span>`
          }</div>

          <div class="section-title">扣款建议</div>
          <div class="deduction-box">
            <div class="deduction-item">旷工<strong>${money(r.absentDeductAmount)}</strong></div>
            <div class="deduction-item">迟到<strong>${money(r.lateDeductAmount)}</strong></div>
            <div class="deduction-item">早退<strong>${money(r.earlyDeductAmount)}</strong></div>
            <div class="deduction-item">缺卡<strong>${money(r.missingPunchDeductAmount)}</strong></div>
          </div>
          <div class="inline" style="margin-top:6px"><span class="sub">合计</span><strong class="deduct">${money(
            r.deductionTotal,
          )}</strong><span class="sub">元；负值表示扣减，不直接写薪酬表。</span></div>

          <div class="section-title">人工调整 <span class="sub">结果层覆盖，重算后按日重新应用</span></div>
          ${
            activeAdj
              ? `<div class="adjust-box">
                  <div class="inline"><span class="badge badge-blue">已调整</span><span class="sub">版本 ${activeAdj.version} · ${esc(
                    activeAdj.adjustedBy,
                  )} · ${esc(activeAdj.adjustedAt)}</span></div>
                  <div class="adjust-values"><span>原值：<b>${esc(
                    activeAdj.originalValues.dayStatus || "—",
                  )}</b> · 迟到 <b>${activeAdj.originalValues.lateMinutes ?? 0}</b> 分钟</span><span>调整后：<b>${esc(
                    activeAdj.adjustedValues.dayStatus || "—",
                  )}</b> · 迟到 <b>${activeAdj.adjustedValues.lateMinutes ?? 0}</b> 分钟</span></div>
                  <div style="margin-top:5px">理由：${esc(activeAdj.reason)}</div>
                </div>`
              : `<div class="notice">${icon(
                  "info",
                )}<div>当前没有人工调整。调整会保留原值、调整值与理由，并记录操作者。</div></div>`
          }
          ${
            history.length
              ? `<div class="adjust-history">${history
                  .slice()
                  .reverse()
                  .map(
                    (a) => `<div class="adjust-item">
                      <div class="adjust-item-head">版本 ${a.version} · ${
                        a.status === "active" ? "生效中" : a.status === "superseded" ? "已被替代" : "孤立"
                      }<span class="sub">${esc(a.adjustedBy)} · ${esc(a.adjustedAt)}</span></div>
                      <div style="margin-top:3px">${esc(a.reason)}</div>
                    </div>`,
                  )
                  .join("")}</div>`
              : ""
          }
        </div>
        <div class="drawer-foot">
          <button class="btn btn-outline" data-action="close-overlay">关闭</button>
          <button class="btn btn-primary" data-action="open-adjust" data-employee="${
            r.employeeId
          }" data-date="${r.date}" ${editable ? "" : "disabled title=\"已确认或锁定月份不可调整\""}>${icon(
            "edit",
          )} ${activeAdj ? "修改调整" : "人工调整"}</button>
        </div>
      </aside>`;
  }

  function renderResultTimeline(r) {
    const dayStart = Data.atMinutes(r.date, "00:00");
    const pct = (min) => Math.max(0, Math.min(100, (min / 1440) * 100));
    const clampMin = (abs) => Math.max(0, Math.min(1440, abs - dayStart));
    const shiftBlocks = r.shiftResults
      .map((sr) => {
        const start = clampMin(sr.span.start);
        const end = clampMin(sr.span.end);
        if (end <= 0 || start >= 1440) return "";
        const width = Math.max(0.8, pct(end) - pct(start));
        const cross = sr.span.end - dayStart > 1440;
        return `<div class="timeline-shift shift-${SHIFT_CLASS[sr.shift.code] || "ADM"}" style="left:${pct(
          start,
        )}%;width:${width}%">${esc(sr.shift.name)}${cross ? " →次日" : ""}</div>`;
      })
      .join("");
    const punchDots = r.punches
      .filter((p) => p.date === r.date)
      .map(
        (p) =>
          `<div class="timeline-punch" style="left:${pct(Data.toMinutes(p.time))}%" title="${esc(
            p.time,
          )} ${esc(p.result || "")}"></div>`,
      )
      .join("");
    const tripBands = r.trips
      .map((t) => {
        const startDate = t.start.slice(0, 10);
        const endDate = t.end.slice(0, 10);
        const start = startDate < r.date ? 0 : Data.toMinutes(t.start.slice(11, 16));
        const end = endDate > r.date ? 1440 : Data.toMinutes(t.end.slice(11, 16));
        if (end <= 0 || start >= 1440) return "";
        return `<div class="timeline-oa" style="left:${pct(start)}%;width:${Math.max(
          0.8,
          pct(end) - pct(start),
        )}%" title="外出 / 出差"></div>`;
      })
      .join("");
    const leaveBands = r.leaves
      .map((l) => {
        const leave = db.leaves.find((x) => x.approvalNo === l.approvalNo);
        if (!leave) return "";
        const startDate = leave.restStart.slice(0, 10);
        const endDate = leave.restEnd.slice(0, 10);
        const start = startDate < r.date ? 0 : Data.toMinutes(leave.restStart.slice(11, 16));
        const end = endDate > r.date ? 1440 : Data.toMinutes(leave.restEnd.slice(11, 16));
        if (end <= 0 || start >= 1440) return "";
        return `<div class="timeline-oa leave" style="left:${pct(start)}%;width:${Math.max(
          0.8,
          pct(end) - pct(start),
        )}%" title="请假"></div>`;
      })
      .join("");
    const otBands = db.overtime
      .filter((t) => t.employeeId === r.employeeId && Data.monthOf(t.start.slice(0, 10)) === state.month)
      .map((t) => {
        const startDate = t.start.slice(0, 10);
        const endDate = t.end.slice(0, 10);
        const start = startDate < r.date ? 0 : Data.toMinutes(t.start.slice(11, 16));
        const end = endDate > r.date ? 1440 : Data.toMinutes(t.end.slice(11, 16));
        if (end <= 0 || start >= 1440) return "";
        return `<div class="timeline-oa ot" style="left:${pct(start)}%;width:${Math.max(
          0.8,
          pct(end) - pct(start),
        )}%" title="OA 加班"></div>`;
      })
      .join("");
    return `<div class="timeline-panel">
      <h4>四方对照时间轴</h4>
      <div class="timeline-hours">${["00", "03", "06", "09", "12", "15", "18", "21", "24"].map(
        (h) => `<span>${h}:00</span>`,
      ).join("")}</div>
      <div class="timeline-track">
        <div class="timeline-grid"></div>
        ${shiftBlocks}
        ${tripBands}
        ${leaveBands}
        ${otBands}
        ${punchDots}
      </div>
      <div class="timeline-legend">
        <span class="legend-item"><span class="legend-dot" style="background:var(--primary)"></span>班次</span>
        <span class="legend-item"><span class="legend-dot" style="background:var(--fg);border-radius:50%"></span>打卡</span>
        <span class="legend-item"><span class="legend-dot" style="background:rgba(14,165,233,.5)"></span>外出 / 出差</span>
        <span class="legend-item"><span class="legend-dot" style="background:rgba(245,158,11,.5)"></span>请假</span>
        <span class="legend-item"><span class="legend-dot" style="background:rgba(168,85,247,.5)"></span>OA 加班</span>
        <span class="spacer"></span>
        ${
          r.punches.some((p) => p.date !== r.date)
            ? `<span class="sub">次日打卡：${r.punches
                .filter((p) => p.date !== r.date)
                .map((p) => `${p.date.slice(5)} ${p.time}`)
                .join("、")}</span>`
            : ""
        }
      </div>
    </div>`;
  }

  function renderAdjustFormOverlay() {
    const draft = state.draft || {};
    const r = findResult(draft.employeeId, draft.date);
    if (!r) return "";
    const emp = getEmployee(r.employeeId);
    const existing = db.adjustments.find(
      (a) => a.employeeId === r.employeeId && a.date === r.date && a.status === "active",
    );
    const v = draft.values || {};
    const field = (label, key, value, type = "number", extra = "") =>
      `<div class="field"><label>${esc(label)}</label><input class="input" type="${type}" data-form="${key}" value="${esc(
        value,
      )}" ${extra} /></div>`;
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal xl" role="dialog" aria-modal="true" aria-labelledby="adjust-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="adjust-title">人工调整 · ${esc(
            emp?.name || r.employeeId,
          )} · ${dateCN(r.date)}</h2><p class="modal-sub">只作用于结果层；重算后按员工与日期重新应用，原始计算值保留</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          ${draft.error ? `<div class="banner danger">${icon("alert")}<div>${esc(draft.error)}</div></div>` : ""}
          <div class="summary-strip" style="margin-bottom:12px">
            <span>原值：${statusBadge(r.dayStatus)} · 出勤 <strong>${r.attendanceFraction.toFixed(
              1,
            )}</strong> · 工时 <strong>${hoursLabel(r.workedMinutes)}h</strong> · 加班 <strong>${hoursLabel(
              resultOtMinutes(r),
            )}h</strong></span>
          </div>
          <div class="form-grid three">
            <div class="field"><label>日状态</label><select class="select" data-form="dayStatus">${RESULT_STATUS_OPTIONS.filter(
              ([k]) => k !== "all",
            )
              .map(
                ([key, label]) =>
                  `<option value="${key}" ${
                    (v.dayStatus || r.dayStatus) === key ? "selected" : ""
                  }>${label}</option>`,
              )
              .join("")}</select></div>
            ${field("出勤比例（0–1）", "attendanceFraction", v.attendanceFraction ?? r.attendanceFraction, "number", 'min="0" max="1" step="0.1"')}
            ${field("实际工时（分钟）", "workedMinutes", v.workedMinutes ?? r.workedMinutes, "number", 'min="0"')}
            ${field("工作日加班（分钟）", "otWeekdayMinutes", v.otWeekdayMinutes ?? r.otWeekdayMinutes, "number", 'min="0"')}
            ${field("周末加班（分钟）", "otWeekendMinutes", v.otWeekendMinutes ?? r.otWeekendMinutes, "number", 'min="0"')}
            ${field("节假日加班（分钟）", "otHolidayMinutes", v.otHolidayMinutes ?? r.otHolidayMinutes, "number", 'min="0"')}
            ${field("迟到（分钟）", "lateMinutes", v.lateMinutes ?? r.lateMinutes, "number", 'min="0"')}
            ${field("迟到次数", "lateCount", v.lateCount ?? r.lateCount, "number", 'min="0"')}
            ${field("早退（分钟）", "earlyMinutes", v.earlyMinutes ?? r.earlyMinutes, "number", 'min="0"')}
            ${field("早退次数", "earlyCount", v.earlyCount ?? r.earlyCount, "number", 'min="0"')}
            ${field("缺卡张数", "missingPunchCount", v.missingPunchCount ?? r.missingPunchCount, "number", 'min="0"')}
            ${field("请假天数", "leaveDays", v.leaveDays ?? r.leaveDays, "number", 'min="0" max="1" step="0.1"')}
          </div>
          <div class="field" style="margin-top:10px"><label>调整理由 <span class="required-dot">*</span></label><textarea class="input" data-form="reason" rows="2" placeholder="例如：门禁故障，主管已核实" data-autofocus>${esc(
            draft.reason || "",
          )}</textarea></div>
          <div class="field" style="margin-top:8px"><label>备注</label><textarea class="input" data-form="note" rows="2">${esc(
            v.note ?? r.note ?? "",
          )}</textarea></div>
          ${
            existing
              ? `<div class="notice info" style="margin-top:10px">${icon(
                  "history",
                )}<div>保存后生成版本 ${existing.version + 1}，当前版本保留为「已被替代」。</div></div>`
              : ""
          }
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="save-adjustment">保存调整</button>
        </div>
      </div>`;
  }

  function renderRecalcOverlay() {
    const batches = committedBatches();
    const ms = monthState();
    const can = isEditable() && batches.length > 0;
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="recalc-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="recalc-title">重新计算 ${monthCN(
            state.month,
          )}</h2><p class="modal-sub">重算会替换当月日结果、班次结果与月汇总</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          ${
            ms.status === "locked" || ms.status === "confirmed"
              ? `<div class="banner warn">${icon(
                  "lock",
                )}<div>本月为「${ms.status === "locked" ? "已锁定" : "已确认"}」，不能重算。请先解锁或撤销确认。</div></div>`
              : !batches.length
                ? `<div class="banner warn">${icon(
                    "alert",
                  )}<div>本月没有生效导入批次。重算会把所有排班日按无卡处理，产生大量旷工；请先导入打卡与 OA 申请。</div></div>`
                : ""
          }
          <div class="kv-list">
            <span class="k">生效批次</span><span>${batches.length} / 4 · ${
              batches.map((b) => db.importSamples[b.dataType].label).join("、") || "无"
            }</span>
            <span class="k">排班明细</span><span>${Data.monthStats(db, state.month).workDays} 人日</span>
            <span class="k">人工调整</span><span>${
              db.adjustments.filter(
                (a) => a.status === "active" && Data.monthOf(a.date) === state.month,
              ).length
            } 条 · 重算后按日重新应用</span>
            <span class="k">计算入口</span><span>算法 attendance-calc-v1；失败整笔回滚，旧结果不变</span>
          </div>
          <div class="notice info" style="margin-top:10px">${icon(
            "info",
          )}<div>重算使用当前规则快照、排班明细、生效导入批次与人工调整；相同输入与调整得到相同输出。</div></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="do-recalc" ${can ? "" : "disabled"}>${icon(
            "refresh",
          )} 开始重算</button>
        </div>
      </div>`;
  }

  function renderConfirmMonthOverlay() {
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="confirm-month-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="confirm-month-title">确认 ${monthCN(
            state.month,
          )}</h2><p class="modal-sub">确认后禁止修改排班、导入与人工例外</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="notice info">${icon(
            "info",
          )}<div>确认前提是「已计算且结果未过期」。确认后可锁定；锁定前仍可撤销确认回到已计算。</div></div>
          <div class="kv-list" style="margin-top:10px">
            <span class="k">计算结果</span><span>${resultsForMonth().length} 条日结果 · ${summariesForMonth().length} 名员工</span>
            <span class="k">计算时间</span><span>${esc(monthState().calculatedAt || "")}</span>
            <span class="k">异常</span><span>${exceptionResults().length} 条（确认不会自动处理）</span>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="do-confirm-month">${icon("check-circle")} 确认本月</button>
        </div>
      </div>`;
  }

  function renderLockOverlay() {
    const version = (db.snapshots[state.month] || []).length + 1;
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="lock-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="lock-title">锁定 ${monthCN(
            state.month,
          )}</h2><p class="modal-sub">锁定后生成月度快照，考勤数据不可编辑</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="banner warn">${icon(
            "lock",
          )}<div><strong>锁定不可直接撤销。</strong>解锁必须填写理由；解锁后状态回到已计算，结果标记过期，需要重新计算才能再次确认。</div></div>
          <div class="kv-list" style="margin-top:10px">
            <span class="k">快照版本</span><span>v${version}（每次锁定新增一条，解锁不删除）</span>
            <span class="k">快照内容</span><span>${resultsForMonth().length} 条日结果 · ${
              db.results[state.month]?.reduce((sum, r) => sum + r.shiftResults.length, 0) || 0
            } 条班次结果 · ${summariesForMonth().length} 条月汇总</span>
            <span class="k">人工调整</span><span>${
              db.adjustments.filter((a) => a.status === "active" && Data.monthOf(a.date) === state.month)
                .length
            } 条</span>
            <span class="k">导出契约</span><span>薪酬回填 14 列 + 考勤明细 CSV</span>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-primary" data-action="do-lock">${icon("lock")} 锁定并生成快照</button>
        </div>
      </div>`;
  }

  function renderUnlockOverlay() {
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="unlock-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="unlock-title">解锁 ${monthCN(
            state.month,
          )}</h2><p class="modal-sub">必须填写理由；解锁后需要重新计算</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="field"><label>解锁理由 <span class="required-dot">*</span></label><textarea class="input" data-form="reason" rows="3" placeholder="例如：工资核算前发现漏导入 9 月 18 日补卡" data-autofocus></textarea></div>
          <div class="notice warn" style="margin-top:10px">${icon(
            "alert",
          )}<div>锁定快照会保留，不会因为解锁而删除。解锁后状态回到「已计算」，结果标记过期。</div></div>
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn btn-danger" data-action="do-unlock">${icon("unlock")} 确认解锁</button>
        </div>
      </div>`;
  }

  function renderExportOverlay() {
    const summaries = summariesForMonth();
    const payrollRows = summaries.map((s) => [
      state.month,
      currentCompany().name,
      s.employeeNo,
      s.employeeName,
      s.deptName,
      s.weekdayFull,
      s.weekendFull,
      s.weekdayAttended,
      s.weekendAttended,
      s.paidLeaveDays,
      s.otWeekdayHours,
      s.otWeekendHours,
      s.otHolidayHours,
      s.attendanceDeduct,
    ]);
    const detailRows = resultsForMonth().map((r) => [
      r.date,
      employeeName(r.employeeId),
      getEmployee(r.employeeId)?.no || "",
      r.dayType,
      r.rosterState,
      r.dayStatus,
      r.attendanceFraction,
      r.workedMinutes,
      r.otWeekdayMinutes,
      r.otWeekendMinutes,
      r.otHolidayMinutes,
      r.deductionTotal,
    ]);
    const preview = [
      [
        "attendance_month",
        "company_name",
        "employee_no",
        "employee_name",
        "department_name",
        "weekday_full",
        "weekend_full",
        "weekday_attended",
        "weekend_attended",
        "paid_leave_days",
        "ot_weekday_hours",
        "ot_weekend_hours",
        "ot_holiday_hours",
        "attendance_deduct",
      ],
      ...payrollRows.slice(0, 4),
    ];
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card lg" role="dialog" aria-modal="true" aria-labelledby="export-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="export-title">导出 ${monthCN(
            state.month,
          )}</h2><p class="modal-sub">考勤结果是权威数据；薪酬模块只读导出，不写任何薪酬表</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="panel">
            <div class="panel-head"><div><h3>薪酬回填 CSV</h3><div class="sub">默认 14 列；天数 1 位小数，加班 2 位小数，扣款为负值</div></div>
              <button class="btn btn-primary btn-sm" data-action="download-payroll">${icon("download")} 下载</button>
            </div>
            <div class="table-wrap"><table class="table">
              <thead><tr>${preview[0].map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>
              <tbody>${preview
                .slice(1)
                .map(
                  (row) => `<tr>${row.map((cell) => `<td>${esc(cell)}</td>`).join("")}</tr>`,
                )
                .join("")}</tbody>
            </table></div>
            <div class="table-foot"><span>预览前 4 行 · 共 ${payrollRows.length} 行</span></div>
          </div>
          <div class="panel" style="margin-top:12px">
            <div class="panel-head"><div><h3>考勤明细 CSV</h3><div class="sub">月汇总全字段 + 日结果 + 班次结果，用于内部对账</div></div>
              <button class="btn btn-outline btn-sm" data-action="download-detail">${icon("download")} 下载</button>
            </div>
            <div class="panel-body"><div class="sub">日结果 ${detailRows.length} 行 · 列：日期、员工、工号、日类型、排班状态、日状态、出勤比例、工时、三类加班、扣款。</div></div>
          </div>
          <div class="notice info" style="margin-top:10px">${icon(
            "info",
          )}<div>导出不会改变月状态；锁定月份导出的是锁定快照对应的结果。</div></div>
        </div>
        <div class="modal-foot"><button class="btn btn-outline" data-action="close-overlay">关闭</button></div>
      </div>`;
  }

  function renderSnapshotOverlay() {
    const snapshots = db.snapshots[state.month] || [];
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card lg" role="dialog" aria-modal="true" aria-labelledby="snapshot-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="snapshot-title">月结快照 · ${monthCN(
            state.month,
          )}</h2><p class="modal-sub">每次锁定新增一条；解锁不删除历史版本</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          ${
            snapshots.length
              ? snapshots
                  .slice()
                  .reverse()
                  .map(
                    (snap) => `<div class="adjust-item">
                      <div class="adjust-item-head">版本 ${snap.version} · ${esc(
                        snap.lockedAt,
                      )}<span class="sub">${snap.dayResults} 条日结果 · ${snap.employees} 名员工</span></div>
                      <div class="adjust-values"><span>计算记录：<b>${esc(
                        snap.calcRunId,
                      )}</b></span><span>规则版本：<b>${esc(snap.rulesVersion || "sha256:demo")}</b></span></div>
                    </div>`,
                  )
                  .join("")
              : `<div class="empty" style="padding:24px"><div class="empty-icon">${icon(
                  "lock",
                )}</div><h3 style="font-size:12px">还没有月结快照</h3><p style="font-size:10.5px">确认后锁定本月会生成第一条快照。</p></div>`
          }
        </div>
        <div class="modal-foot"><button class="btn btn-outline" data-action="close-overlay">关闭</button></div>
      </div>`;
  }

  function renderGenericConfirmOverlay(o) {
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal sm" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="confirm-title">${esc(o.title || "确认操作")}</h2><p class="modal-sub">${esc(
            o.sub || "此操作会立即生效",
          )}</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="notice ${o.danger ? "danger" : "info"}">${icon(
            o.danger ? "alert" : "info",
          )}<div>${o.message || ""}</div></div>
          ${o.detail ? `<div class="hint" style="margin-top:9px">${o.detail}</div>` : ""}
        </div>
        <div class="modal-foot">
          <button class="btn btn-outline" data-action="close-overlay">取消</button>
          <button class="btn ${o.danger ? "btn-danger" : "btn-primary"}" data-action="${
            o.confirmAction || "noop"
          }" data-id="${esc(o.id || "")}" data-date="${esc(o.date || "")}" data-employee="${esc(
            o.employee || "",
          )}">${esc(o.confirmLabel || "确认")}</button>
        </div>
      </div>`;
  }

  function downloadCsv(filename, rows) {
    const csv = rows
      .map((row) =>
        row
          .map((cell) => `"${String(cell == null ? "" : cell).replace(/"/g, '""')}"`)
          .join(","),
      )
      .join("\r\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  /* ================================================================ guide overlays */

  function renderFlowOverlay() {
    const names = { A: "A · 模块独立", B: "B · 单工作台 + 页签", C: "C · 异常优先驾驶舱" };
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card lg" role="dialog" aria-modal="true" aria-labelledby="flow-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="flow-title">页面流程 · ${names[state.variant]}</h2><p class="modal-sub">讨论用流程图，不是最终信息架构</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">${renderFlowContent()}</div>
      </div>`;
  }

  function renderFlowContent() {
    if (state.variant === "A") {
      return `<div class="flow-section-title">侧边栏「考勤管理」五个独立入口</div>
        <div class="flow-grid">
          <div class="flow-node primary">排班工作台</div>
          <div class="flow-node soft">导入中心</div>
          <div class="flow-node soft">考勤结果</div>
          <div class="flow-node soft">规则与节假日</div>
          <div class="flow-node soft">班次</div>
        </div>
        <div class="flow-arrow">↓ 每个页面独立 URL，可被收藏 / 分享</div>
        <div class="flow-grid">
          <div class="flow-node">方案视图 / 员工明细</div>
          <div class="flow-node">上传 → 映射 → 预览 → 提交</div>
          <div class="flow-node">异常收件箱 → 日详情 → 调整</div>
          <div class="flow-node">公司默认 + 方案覆盖 + 节假日</div>
          <div class="flow-node">班次模板 CRUD</div>
        </div>
        <div class="flow-note">公司上下文在顶栏全局切换；月份在各页面内独立选择。适合把考勤当作五个并列模块维护。</div>`;
    }
    if (state.variant === "B") {
      return `<div class="flow-section-title">侧边栏单一入口「考勤管理」</div>
        <div class="flow-grid"><div class="flow-node primary">考勤工作台</div></div>
        <div class="flow-arrow">↓ 月份 / 公司 / 状态在页签间保持</div>
        <div class="flow-grid">
          <div class="flow-node soft">排班页签</div>
          <div class="flow-node soft">导入页签</div>
          <div class="flow-node soft">结果页签</div>
          <div class="flow-node soft">规则页签</div>
        </div>
        <div class="flow-arrow">↓ 左侧常驻轨道：月历、本月统计、快捷操作</div>
        <div class="flow-grid">
          <div class="flow-node">方案 / 员工月历</div>
          <div class="flow-node">批次向导 + 历史</div>
          <div class="flow-node">日结果 / 月汇总 / 计算记录</div>
          <div class="flow-node">规则、节假日、班次管理抽屉</div>
        </div>
        <div class="flow-note">适合以「一个月」为单位连续工作：排班 → 导入 → 结果 → 月结，不反复切换侧边栏。</div>`;
    }
    return `<div class="flow-section-title">侧边栏单一入口「考勤」</div>
      <div class="flow-grid"><div class="flow-node primary">考勤驾驶舱（默认落地）</div></div>
      <div class="flow-arrow">↓ 先看异常与待办，再进入模式</div>
      <div class="flow-grid">
        <div class="flow-node soft">排班模式（全屏日历）</div>
        <div class="flow-node soft">导入向导（全屏）</div>
        <div class="flow-node soft">结果收件箱</div>
        <div class="flow-node soft">规则 / 节假日 / 班次抽屉</div>
      </div>
      <div class="flow-arrow">↓ 每个模式顶部「返回驾驶舱」</div>
      <div class="flow-grid">
        <div class="flow-node">驾驶舱：异常数、月状态、导入健康度</div>
        <div class="flow-node">快捷卡：导入 / 排班 / 结果 / 规则</div>
        <div class="flow-node">月结：确认 → 锁定 → 快照</div>
      </div>
      <div class="flow-note">适合 HR 每天早上先打开一屏看「今天要处理什么」，而不是先找模块。</div>`;
  }

  function renderDiffOverlay() {
    const rows = [
      [
        "导航",
        "单个长页面 + 顶部页签；考勤与薪酬等模块混在同一面板",
        "A 五模块独立 / B 单工作台页签 / C 驾驶舱 + 模式；考勤独立成组",
        "先让用户选择「按模块」还是「按月份」工作，而不是预设一种",
      ],
      [
        "排班",
        "排班表 + 月历，方案与明细混在一起；没有方案/员工双视角",
        "方案视图看模式、员工明细看个人月历；保存即展开；人工例外显式标记",
        "回答「这天谁上班」与「这个人这个月怎么上」两个不同问题",
      ],
      [
        "批量操作",
        "工作日填充 / 整月填充 / 清空 / 复制下月，缺少预览",
        "批量填充带影响日期、覆盖员工、预计人日预览；复制下月提示大小月与例外",
        "批量操作前先看到影响面，减少误覆盖",
      ],
      [
        "导入",
        "内嵌文本框 + 「解析」「确认导入」，没有列映射与批次概念",
        "上传/粘贴 → 列映射 → 预览校验 → 提交；批次历史、覆盖影响、错误报告",
        "把覆盖式刷新做成可审计的批次，而不是一次不可追溯的点击",
      ],
      [
        "结果",
        "一张宽表 + 顶部按钮；没有异常收件箱与四方对照",
        "异常优先收件箱；日详情抽屉四方对照（排班/打卡/OA/结果）+ 时间轴",
        "HR 先处理异常，再核对全量；差异原因一眼可见",
      ],
      [
        "人工调整",
        "未体现",
        "结果层调整表单、原值/调整值/理由/操作者、版本历史，重算后重新应用",
        "调整可追溯，月结前可复核",
      ],
      [
        "月结",
        "只有「回填到工资计算」按钮，没有确认/锁定/快照",
        "草稿 → 已计算 → 已确认 → 已锁定；解锁需理由，锁定生成快照",
        "把「结果可用」与「结果不可变」分开，薪酬取数有明确边界",
      ],
      [
        "规则与节假日",
        "规则散落在多个输入区；节假日没有独立日历",
        "公司默认 + 方案覆盖的分组表单；节假日日历 + 修改影响提示",
        "修改前知道会影响哪些月份，避免静默改数",
      ],
      [
        "状态与可达性",
        "无加载/空/错误状态；窄屏与深色未覆盖",
        "全局状态切换、空数据引导、深色主题、窄屏预览、键盘与焦点样式",
        "把异常状态当作一等公民，而不是只做正常路径",
      ],
    ];
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card xl" role="dialog" aria-modal="true" aria-labelledby="diff-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="diff-title">与需求原型的差异</h2><p class="modal-sub">需求原型只作参考；已确定采用 B 模型（方案展开为员工日明细）</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="table-wrap"><table class="table diff-table">
            <thead><tr><th>维度</th><th>需求原型</th><th>本原型</th><th>为什么更好</th></tr></thead>
            <tbody>${rows
              .map(
                (row) =>
                  `<tr><td class="cell-strong">${esc(row[0])}</td><td>${esc(
                    row[1],
                  )}</td><td>${esc(row[2])}</td><td>${esc(row[3])}</td></tr>`,
              )
              .join("")}</tbody>
          </table></div>
        </div>
      </div>`;
  }

  function renderQuestionsOverlay() {
    const questions = [
      ["整体导航", "A 五个独立入口 / B 单工作台 + 页签 / C 驾驶舱 + 模式，选哪个？是否要混合（例如 A 的侧边栏 + B 的月份上下文）？", "查看三个方案的页面流程与左侧导航"],
      ["排班默认视图", "进入排班工作台时默认「方案视图」还是「员工明细」？是否需要一个并列双栏？", "在排班工作台切换右上角视图"],
      ["排班编辑入口", "左侧方案列表 + 右侧月历，还是全屏日历 + 右侧抽屉？一天多班用弹窗还是侧栏编辑？", "点击方案卡片 / 日历日期"],
      ["导入向导", "独立导入中心，还是工作台页签？上传/粘贴 → 映射 → 预览 → 提交四步是否足够？", "打开导入中心 → 新建导入"],
      ["结果页", "异常优先收件箱是否应作为默认？日详情抽屉宽度与四方对照信息量是否合适？", "考勤结果 → 点击异常行"],
      ["月结", "确认/锁定放在结果页，还是独立月结页或驾驶舱？锁定前是否需要更明显的复核清单？", "考勤结果顶部操作"],
      ["规则 / 节假日 / 班次", "三者是一个设置页、三个页签，还是班次独立入口？方案覆盖如何呈现？", "规则与节假日 / 班次"],
      ["状态与可达性", "深色、窄屏、键盘与加载/空/错误状态是否满足评审？还缺哪些真实状态？", "底部「状态」「窄屏」「深色」"],
    ];
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="overlay-card lg" role="dialog" aria-modal="true" aria-labelledby="questions-title">
        <div class="modal-head">
          <div><h2 class="modal-title" id="questions-title">讨论问题</h2><p class="modal-sub">请在看原型时逐条选择；答案会记录到 ticket #26 的 resolution</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="question-list">
            ${questions
              .map(
                ([title, question, hint], i) => `<div class="question-item">
                  <strong>${i + 1}. ${esc(title)}</strong>
                  <p>${esc(question)}</p>
                  <div class="answer-hint">${esc(hint)}</div>
                </div>`,
              )
              .join("")}
          </div>
        </div>
        <div class="modal-foot"><button class="btn btn-primary" data-action="close-overlay">继续评审</button></div>
      </div>`;
  }

  /* ================================================================ state mutations */

  function markStale(month = state.month) {
    const ms = db.months[month];
    if (ms && ["draft", "calculated"].includes(ms.status)) ms.isStale = true;
  }

  function markAllStale() {
    for (const month of Object.keys(db.months)) markStale(month);
  }

  function closeOverlay() {
    state.overlay = null;
    state.draft = null;
    state.wizard = null;
    state.companyMenuOpen = false;
    render();
  }

  function openOverlay(type, extra = {}) {
    state.overlay = { type, key: String(Date.now()), ...extra };
    render();
  }

  function openPlanEditor(id) {
    const plan = id ? Data.getPlan(db, id) : null;
    state.draft = plan
      ? {
          id: plan.id,
          name: plan.name,
          scopeType: plan.scopeType,
          scopeIds: plan.scopeIds.slice(),
          weekdays: Data.clone(plan.weekdays),
          dayOverrides: Data.clone(plan.dayOverrides || {}),
          note: plan.note || "",
          overrides: Data.clone(db.planRuleOverrides[plan.id] || {}),
          isNew: false,
          error: "",
        }
      : {
          id: "",
          name: "",
          scopeType: "dept",
          scopeIds: [],
          weekdays: { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] },
          dayOverrides: {},
          note: "",
          overrides: {},
          isNew: true,
          error: "",
        };
    openOverlay("plan-editor");
  }

  function openShiftForm(code) {
    const shift = code ? getShift(code) : null;
    state.draft = shift
      ? {
          originalCode: shift.code,
          code: shift.code,
          name: shift.name,
          start: shift.start,
          end: shift.end,
          crossDay: !!shift.crossDay,
          breakStart: shift.breakStart || "",
          breakEnd: shift.breakEnd || "",
          restMinutes: shift.restMinutes,
          color: shift.color || "blue",
          note: shift.note || "",
        }
      : {
          originalCode: "",
          code: "",
          name: "",
          start: "08:30",
          end: "17:30",
          crossDay: false,
          breakStart: "",
          breakEnd: "",
          restMinutes: 60,
          color: "blue",
          note: "",
        };
    openOverlay("shift-form");
  }

  function openException(employeeId, date) {
    const entry = Data.rosterEntry(db, state.month, employeeId, date);
    state.draft = {
      employeeId,
      date,
      state: entry ? entry.state : "work",
      shifts: entry ? entry.shifts.slice() : [],
      note: entry ? entry.note || "" : "",
    };
    openOverlay("exception");
  }

  function openDayBulk(date) {
    state.draft = {
      date,
      employeeIds: [],
      state: "work",
      shifts: ["EARLY"],
      note: "",
    };
    openOverlay("day-bulk");
  }

  function openPlanDay(id, date) {
    const plan = Data.getPlan(db, id) || selectedPlan() || companyPlans()[0];
    if (!plan) return;
    state.draft = {
      planId: plan.id,
      date: date || `${state.month}-01`,
      shifts: Data.planShiftsForDate(db, plan, date || `${state.month}-01`),
    };
    state.selectedPlanId = plan.id;
    state.scheduleView = "plan";
    openOverlay("plan-day");
  }

  function openBatchFill() {
    const plan = selectedPlan() || companyPlans()[0];
    if (!plan) return;
    const monday = `${state.month}-01`;
    const sampleShifts = Data.planShiftsForDate(db, plan, monday);
    state.draft = {
      planId: plan.id,
      mode: "workdays",
      weekdays: [0, 1, 2, 3, 4],
      shifts: sampleShifts.length ? sampleShifts : ["ADM"],
    };
    openOverlay("batch-fill");
  }

  function openCopyMonth() {
    const plan = selectedPlan() || companyPlans()[0];
    state.draft = { planId: plan ? plan.id : "", copyExceptions: false };
    openOverlay("copy-month");
  }

  function openAdjust(employeeId, date) {
    const r = findResult(employeeId, date);
    if (!r) {
      showToast("该日没有计算结果，无法调整", "error");
      return;
    }
    const existing = db.adjustments.find(
      (a) => a.employeeId === employeeId && a.date === date && a.status === "active",
    );
    state.draft = {
      employeeId,
      date,
      values: {
        dayStatus: r.dayStatus,
        attendanceFraction: r.attendanceFraction,
        workedMinutes: r.workedMinutes,
        otWeekdayMinutes: r.otWeekdayMinutes,
        otWeekendMinutes: r.otWeekendMinutes,
        otHolidayMinutes: r.otHolidayMinutes,
        lateMinutes: r.lateMinutes,
        lateCount: r.lateCount,
        earlyMinutes: r.earlyMinutes,
        earlyCount: r.earlyCount,
        missingPunchCount: r.missingPunchCount,
        leaveDays: r.leaveDays,
        note: r.note || "",
      },
      reason: existing ? existing.reason : "",
      error: "",
    };
    openOverlay("adjust-form");
  }

  function planScopeConflict(draft, exceptId) {
    const others = db.plans.filter(
      (p) =>
        p.month === state.month &&
        p.status === "enabled" &&
        p.id !== exceptId,
    );
    if (draft.scopeType === "all") return others.find((p) => p.scopeType === "all") || null;
    if (draft.scopeType === "dept") {
      const mine = new Set(draft.scopeIds.flatMap((id) => Data.deptDescendants(db, id)));
      return (
        others.find(
          (p) =>
            p.scopeType === "dept" &&
            p.scopeIds.some((id) =>
              Data.deptDescendants(db, id).some((child) => mine.has(child)),
            ),
        ) || null
      );
    }
    return (
      others.find(
        (p) =>
          p.scopeType === draft.scopeType &&
          p.scopeIds.some((id) => draft.scopeIds.includes(id)),
      ) || null
    );
  }

  function collectRuleForm() {
    const rules = { ...db.rules };
    document.querySelectorAll("[data-rule-field]").forEach((input) => {
      const key = input.dataset.ruleField;
      const value = Number(input.value);
      if (!Number.isFinite(value) || value < 0) {
        rules[key] = NaN;
      } else {
        rules[key] = value;
      }
    });
    document.querySelectorAll("[data-rule-check]").forEach((input) => {
      rules[input.dataset.ruleCheck] = input.checked;
    });
    return rules;
  }

  function saveRules() {
    const rules = collectRuleForm();
    const bad = Object.keys(rules).find((k) => typeof rules[k] === "number" && !Number.isFinite(rules[k]));
    if (bad) {
      showToast(`规则「${RULE_LABELS[bad] || bad}」必须是非负数字`, "error");
      return;
    }
    db.rules = rules;
    markAllStale();
    showToast("公司默认规则已保存；草稿与已计算月份已标记过期");
    render();
  }

  function savePlan() {
    const draft = state.draft;
    if (!draft) return;
    if (!isEditable()) {
      showToast("本月已确认或锁定，不能修改排班方案", "error");
      return;
    }
    const name = (document.querySelector('[data-form="name"]')?.value || "").trim();
    const note = (document.querySelector('[data-form="note"]')?.value || "").trim();
    if (!name) {
      draft.error = "请填写方案名称";
      render();
      return;
    }
    if (draft.scopeType !== "all" && !draft.scopeIds.length) {
      draft.error = "请至少选择一个范围对象";
      render();
      return;
    }
    const conflict = planScopeConflict(draft, draft.id);
    if (conflict) {
      draft.error = `同月同精确度范围已被「${conflict.name}」占用，请先编辑或归档该方案（409）`;
      render();
      return;
    }
    const overrides = {};
    document.querySelectorAll("[data-plan-override]").forEach((input) => {
      const key = input.dataset.planOverride;
      if (input.value !== "") {
        const value = Number(input.value);
        if (Number.isFinite(value) && value >= 0) overrides[key] = value;
      }
    });
    const id = draft.id || `plan-${Date.now()}`;
    const existingPlan = draft.id ? db.plans.find((p) => p.id === draft.id) : null;
    const plan = {
      id,
      companyId: state.companyId,
      month: state.month,
      name,
      scopeType: draft.scopeType,
      scopeIds: draft.scopeType === "all" ? [] : draft.scopeIds.slice(),
      status: existingPlan?.status || "enabled",
      copiedFromPlanId: existingPlan?.copiedFromPlanId || null,
      note,
      weekdays: draft.weekdays,
      dayOverrides: draft.dayOverrides || {},
    };
    if (draft.id) {
      const idx = db.plans.findIndex((p) => p.id === draft.id);
      if (idx >= 0) db.plans[idx] = plan;
      else db.plans.push(plan);
    } else {
      db.plans.push(plan);
    }
    if (Object.keys(overrides).length) db.planRuleOverrides[id] = overrides;
    else delete db.planRuleOverrides[id];
    Data.rebuildRoster(db);
    markStale();
    const coverage = planEmployeesFor(plan).length;
    closeOverlay();
    showToast(`方案已保存并展开：覆盖 ${coverage} 名员工`);
  }

  function saveShift() {
    const draft = state.draft;
    if (!draft) return;
    const value = (name) => (document.querySelector(`[data-form="${name}"]`)?.value || "").trim();
    const crossDay = !!document.querySelector('[data-rule-check="crossDay"]')?.checked;
    const code = draft.originalCode || value("code").toUpperCase();
    const name = value("name");
    const start = value("start");
    const end = value("end");
    const restMinutes = Number(value("restMinutes"));
    const breakStart = value("breakStart");
    const breakEnd = value("breakEnd");
    const error = (message) => {
      draft.error = message;
      render();
    };
    if (!code || !/^[A-Z0-9_-]{1,32}$/.test(code)) return error("编码必须为大写字母、数字、下划线或短横线，1–32 位");
    if (!draft.originalCode && db.shifts.some((s) => s.code === code)) return error("班次编码在公司内必须唯一");
    if (!name) return error("请填写班次名称");
    if (!start || !end) return error("请填写上下班时间");
    if (!crossDay && Data.toMinutes(end) <= Data.toMinutes(start)) return error("非跨天班次的结束时间必须晚于开始时间");
    if (crossDay && Data.toMinutes(end) > Data.toMinutes(start)) return error("跨天班次的结束时间应早于或等于开始时间（次日）");
    if (!Number.isFinite(restMinutes) || restMinutes < 0) return error("休息扣除必须是非负分钟数");
    if ((breakStart && !breakEnd) || (!breakStart && breakEnd)) return error("午休开始与结束必须同时填写或同时留空");
    const shift = {
      code,
      name,
      start,
      end,
      crossDay,
      breakStart: breakStart || null,
      breakEnd: breakEnd || null,
      restMinutes,
      color: draft.color,
      note: value("note"),
      active: draft.originalCode ? getShift(draft.originalCode)?.active !== false : true,
    };
    if (draft.originalCode) {
      const idx = db.shifts.findIndex((s) => s.code === draft.originalCode);
      db.shifts[idx] = shift;
    } else {
      db.shifts.push(shift);
    }
    closeOverlay();
    showToast(`班次「${name}」已保存；已生成明细的快照不变`);
  }

  function savePlanDay() {
    const draft = state.draft;
    if (!draft) return;
    if (!isEditable()) {
      showToast("本月已确认或锁定，不能修改方案日", "error");
      return;
    }
    const plan = Data.getPlan(db, draft.planId);
    if (!plan) return;
    const empty = !!(state.overlay && state.overlay.empty);
    const day = dayNum(draft.date);
    plan.dayOverrides = plan.dayOverrides || {};
    plan.dayOverrides[day] = empty ? [] : draft.shifts.slice();
    Data.rebuildRoster(db);
    markStale();
    closeOverlay();
    showToast(`已保存 ${dateCN(draft.date)} 的方案日${empty ? "（休息）" : ""}，并重新展开`);
  }

  function saveException() {
    const draft = state.draft;
    if (!draft) return;
    if (!isEditable()) {
      showToast("本月已确认或锁定，不能修改人工例外", "error");
      return;
    }
    const note = document.querySelector('[data-form="note"]')?.value || "";
    if (draft.state === "work" && !(draft.shifts || []).length) {
      showToast("上班状态至少选择一个班次", "error");
      return;
    }
    db.exceptions[`${draft.employeeId}|${draft.date}`] = {
      employeeId: draft.employeeId,
      date: draft.date,
      state: draft.state,
      shifts: draft.state === "work" ? draft.shifts.slice() : [],
      note,
    };
    Data.rebuildRoster(db);
    markStale();
    const emp = getEmployee(draft.employeeId);
    closeOverlay();
    showToast(`已保存 ${emp?.name || ""} ${dateCN(draft.date)} 的人工例外`);
  }

  function deleteException() {
    const draft = state.draft;
    if (!draft) return;
    if (!isEditable()) {
      showToast("本月已确认或锁定，不能删除人工例外", "error");
      return;
    }
    delete db.exceptions[`${draft.employeeId}|${draft.date}`];
    Data.rebuildRoster(db);
    markStale();
    closeOverlay();
    showToast("已删除人工例外；按当前方案恢复该日排班");
  }

  function saveDayBulk() {
    const draft = state.draft;
    if (!draft) return;
    if (!isEditable()) {
      showToast("本月已确认或锁定，不能修改人工例外", "error");
      return;
    }
    const note = document.querySelector('[data-form="note"]')?.value || "";
    if (draft.state === "work" && !(draft.shifts || []).length) {
      showToast("上班状态至少选择一个班次", "error");
      return;
    }
    for (const employeeId of draft.employeeIds || []) {
      db.exceptions[`${employeeId}|${draft.date}`] = {
        employeeId,
        date: draft.date,
        state: draft.state,
        shifts: draft.state === "work" ? draft.shifts.slice() : [],
        note,
      };
    }
    Data.rebuildRoster(db);
    markStale();
    const count = (draft.employeeIds || []).length;
    closeOverlay();
    showToast(`已为 ${count} 名员工保存人工例外`);
  }

  function applyBatchFill() {
    const draft = state.draft;
    if (!draft) return;
    if (!isEditable()) {
      showToast("本月已确认或锁定，不能批量填充", "error");
      return;
    }
    const plan = Data.getPlan(db, draft.planId);
    if (!plan) return;
    if (draft.mode === "clear") {
      plan.weekdays = { 0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] };
      plan.dayOverrides = {};
    } else {
      const shifts = draft.shifts.slice();
      const days = draft.mode === "month" ? [0, 1, 2, 3, 4, 5, 6] : draft.weekdays;
      for (const wd of days) plan.weekdays[wd] = shifts.slice();
    }
    Data.rebuildRoster(db);
    markStale();
    closeOverlay();
    showToast(draft.mode === "clear" ? "已清空方案模式" : "批量填充已应用到方案并重新展开");
  }

  function copyMonth() {
    const draft = state.draft;
    if (!draft) return;
    if (!isEditable()) {
      showToast("本月已确认或锁定，不能复制到下月", "error");
      return;
    }
    const plan = Data.getPlan(db, draft.planId);
    if (!plan) return;
    if (state.month !== "2026-09") {
      showToast("只支持复制到下一个自然月", "error");
      return;
    }
    const targetMonth = "2026-10";
    const targetDays = Data.daysInMonth(targetMonth);
    const existing = db.plans.find(
      (p) =>
        p.month === targetMonth &&
        p.status === "enabled" &&
        (p.scopeType === plan.scopeType) &&
        (plan.scopeType === "all" ||
          p.scopeIds.some((id) => plan.scopeIds.includes(id))),
    );
    if (existing) {
      showToast(`目标月已有同范围方案「${existing.name}」（409）`, "error");
      return;
    }
    const newPlan = Data.clone(plan);
    newPlan.id = `plan-${Date.now()}`;
    newPlan.month = targetMonth;
    newPlan.name = plan.name.includes("2026-09")
      ? plan.name.replace("2026-09", "2026-10")
      : `${plan.name}（10 月）`;
    newPlan.copiedFromPlanId = plan.id;
    newPlan.dayOverrides = {};
    for (const key of Object.keys(plan.dayOverrides || {})) {
      if (Number(key) <= targetDays) newPlan.dayOverrides[key] = Data.clone(plan.dayOverrides[key]);
    }
    db.plans.push(newPlan);
    if (db.planRuleOverrides[plan.id]) {
      db.planRuleOverrides[newPlan.id] = Data.clone(db.planRuleOverrides[plan.id]);
    }
    let copiedExceptions = 0;
    if (draft.copyExceptions) {
      for (const ex of Object.values(db.exceptions)) {
        if (Data.monthOf(ex.date) !== state.month) continue;
        const day = dayNum(ex.date);
        if (day > targetDays) continue;
        const emp = getEmployee(ex.employeeId);
        const targetDate = `${targetMonth}-${pad2(day)}`;
        if (!emp || !Data.employedOn(emp, targetDate)) continue;
        db.exceptions[`${ex.employeeId}|${targetDate}`] = {
          ...Data.clone(ex),
          date: targetDate,
        };
        copiedExceptions += 1;
      }
    }
    db.months[targetMonth].status = "draft";
    db.months[targetMonth].isStale = true;
    Data.rebuildRoster(db);
    state.month = targetMonth;
    state.selectedPlanId = newPlan.id;
    state.scheduleView = "plan";
    state.selectedDate = null;
    state.holidayMonth = targetMonth;
    closeOverlay();
    syncUrl();
    showToast(
      `已复制到 ${monthCN(targetMonth)}：${targetDays > 30 ? "目标月多出 1 天，按休息处理" : "日期已映射"}${
        copiedExceptions ? `，并复制 ${copiedExceptions} 条例外` : ""
      }`,
    );
  }

  function syncPeople() {
    if (!isEditable()) {
      showToast("本月已确认或锁定，不能同步人员", "error");
      return;
    }
    const count = db.pendingEmployees.length;
    db.pendingEmployees = [];
    Data.rebuildRoster(db);
    Data.buildPunches(db);
    markStale();
    closeOverlay();
    showToast(`人员已同步，新增 ${count} 名待同步员工；结果标记为过期`);
  }

  function saveHoliday() {
    const value = (name) => (document.querySelector(`[data-form="${name}"]`)?.value || "").trim();
    const date = value("date");
    const name = value("name");
    const dayType = value("dayType") || "holiday";
    if (!date || !name) {
      showToast("请填写日期与名称", "error");
      return;
    }
    const month = Data.monthOf(date);
    db.holidays[month] = db.holidays[month] || [];
    const idx = db.holidays[month].findIndex((h) => h.date === date);
    const item = { date, name, dayType, note: value("note") };
    if (idx >= 0) db.holidays[month][idx] = item;
    else db.holidays[month].push(item);
    state.holidayMonth = month;
    markAllStale();
    closeOverlay();
    showToast(`已保存 ${date} ${name}；草稿与已计算月份标记过期`);
  }

  function deleteHoliday(date) {
    const month = Data.monthOf(date);
    db.holidays[month] = (db.holidays[month] || []).filter((h) => h.date !== date);
    markAllStale();
    closeOverlay();
    showToast("节假日已删除；草稿与已计算月份标记过期");
  }

  function saveOverride(planId) {
    const plan = Data.getPlan(db, planId);
    if (!plan) return;
    const overrides = {};
    document.querySelectorAll("[data-override]").forEach((input) => {
      if (input.value !== "") {
        const value = Number(input.value);
        if (Number.isFinite(value) && value >= 0) overrides[input.dataset.override] = value;
      }
    });
    if (Object.keys(overrides).length) db.planRuleOverrides[planId] = overrides;
    else delete db.planRuleOverrides[planId];
    markStale();
    closeOverlay();
    showToast(`方案「${plan.name}」的规则覆盖已保存`);
  }

  function commitBatch(id) {
    const batch = db.importBatches.find((b) => b.id === id);
    if (!batch) return;
    if (batch.status !== "preview") {
      showToast("只有预览批次可以提交", "error");
      return;
    }
    if (!isEditable(batch.month)) {
      showToast("月份已确认或锁定，不能提交", "error");
      return;
    }
    for (const other of db.importBatches) {
      if (
        other.id !== batch.id &&
        other.companyId === batch.companyId &&
        other.dataType === batch.dataType &&
        other.month === batch.month &&
        other.status === "committed"
      ) {
        other.status = "superseded";
        other.supersededAt = nowLabel();
        other.supersededByBatchId = batch.id;
      }
    }
    batch.status = "committed";
    batch.committedAt = nowLabel();
    batch.expiresAt = null;
    markStale(batch.month);
    closeOverlay();
    // A committed preview becomes the new active batch; the page should show it.
    state.importType = batch.dataType;
    state.month = batch.month;
    showToast("批次已提交生效；本月结果标记为过期");
  }

  function commitWizard() {
    const wiz = state.wizard;
    if (!wiz) return;
    const can = wizardCanCommit(wiz);
    if (!can.ok) {
      showToast(can.reason, "error");
      return;
    }
    const sample = wizardSample(wiz);
    const old = committedBatch(wiz.dataType, wiz.month);
    if (old) {
      old.status = "superseded";
      old.supersededAt = nowLabel();
    }
    const batch = {
      id: `b-${wiz.dataType}-${Date.now()}`,
      companyId: state.companyId,
      dataType: wiz.dataType,
      month: wiz.month,
      status: "committed",
      source: wiz.source,
      fileName: wiz.fileName || "",
      fileSize: wiz.fileName ? "样例文件" : "粘贴文本",
      operator: "管理员",
      createdAt: nowLabel(),
      committedAt: nowLabel(),
      sourceRows: sample.stats.sourceRows,
      valid: sample.stats.valid,
      skipped: sample.stats.skipped,
      errors: sample.stats.errors,
      warnings: sample.stats.warnings,
    };
    db.importBatches.push(batch);
    markStale(wiz.month);
    state.month = wiz.month;
    state.importType = wiz.dataType;
    state.wizard = null;
    closeOverlay();
    setFlash(`批次已提交生效：${sample.label} ${sample.stats.valid} 条有效记录`);
    showToast("批次已提交生效；本月结果标记为过期");
  }

  function recalcMonth() {
    const ms = monthState();
    if (!isEditable() || !committedBatches().length) {
      showToast("当前月份不可重算，或没有生效导入批次", "error");
      return;
    }
    const res = Data.recalculate(db, state.month);
    db.results[state.month] = res.results;
    db.summaries[state.month] = res.summaries;
    ms.status = "calculated";
    ms.isStale = false;
    ms.calculatedAt = nowLabel();
    db.calcRuns[state.month] = db.calcRuns[state.month] || [];
    db.calcRuns[state.month].push({
      id: `calc-${Date.now()}`,
      trigger: "manual",
      status: "success",
      startedAt: nowLabel(),
      finishedAt: nowLabel(),
      employees: res.summaries.length,
      days: res.results.length,
      note: "手动重算",
    });
    state.overlay = null;
    showToast(`重算完成：${res.results.length} 条日结果 · ${res.summaries.length} 名员工`);
    render();
  }

  function saveAdjustment() {
    const draft = state.draft;
    if (!draft) return;
    if (!isEditable()) {
      showToast("本月已确认或锁定，不能调整", "error");
      return;
    }
    const get = (key) => document.querySelector(`[data-form="${key}"]`)?.value;
    const reason = (get("reason") || "").trim();
    if (!reason) {
      draft.error = "请填写调整理由";
      render();
      return;
    }
    const values = {
      dayStatus: get("dayStatus"),
      attendanceFraction: Number(get("attendanceFraction")),
      workedMinutes: Number(get("workedMinutes")),
      otWeekdayMinutes: Number(get("otWeekdayMinutes")),
      otWeekendMinutes: Number(get("otWeekendMinutes")),
      otHolidayMinutes: Number(get("otHolidayMinutes")),
      lateMinutes: Number(get("lateMinutes")),
      lateCount: Number(get("lateCount")),
      earlyMinutes: Number(get("earlyMinutes")),
      earlyCount: Number(get("earlyCount")),
      missingPunchCount: Number(get("missingPunchCount")),
      leaveDays: Number(get("leaveDays")),
      note: get("note") || "",
    };
    const r = findResult(draft.employeeId, draft.date);
    if (!r) return;
    const existing = db.adjustments.find(
      (a) =>
        a.employeeId === draft.employeeId &&
        a.date === draft.date &&
        a.status === "active",
    );
    if (existing) existing.status = "superseded";
    const version = (existing ? existing.version : 0) + 1;
    const originalValues = existing
      ? existing.originalValues
      : {
          dayStatus: r.dayStatus,
          attendanceFraction: r.attendanceFraction,
          workedMinutes: r.workedMinutes,
          otWeekdayMinutes: r.otWeekdayMinutes,
          otWeekendMinutes: r.otWeekendMinutes,
          otHolidayMinutes: r.otHolidayMinutes,
          lateMinutes: r.lateMinutes,
          lateCount: r.lateCount,
          earlyMinutes: r.earlyMinutes,
          earlyCount: r.earlyCount,
          missingPunchCount: r.missingPunchCount,
          leaveDays: r.leaveDays,
          note: r.note,
        };
    db.adjustments.push({
      id: `adj-${Date.now()}`,
      employeeId: draft.employeeId,
      date: draft.date,
      version,
      status: "active",
      originalValues,
      adjustedValues: values,
      reason,
      adjustedBy: "管理员",
      adjustedAt: nowLabel(),
    });
    const res = Data.recalculate(db, state.month);
    db.results[state.month] = res.results;
    db.summaries[state.month] = res.summaries;
    const employeeId = draft.employeeId;
    const date = draft.date;
    state.overlay = { type: "result-drawer", key: String(Date.now()), employee: employeeId, date };
    state.draft = null;
    showToast(`人工调整已保存（版本 ${version}），重算后按日重新应用`);
    render();
  }

  function doConfirmMonth() {
    const ms = monthState();
    if (ms.status !== "calculated" || ms.isStale) {
      showToast("需要已计算且结果未过期才能确认", "error");
      return;
    }
    ms.status = "confirmed";
    ms.confirmedAt = nowLabel();
    closeOverlay();
    showToast("本月已确认；数据修改已锁定，可继续锁定生成快照");
  }

  function undoConfirm() {
    const ms = monthState();
    if (ms.status !== "confirmed") return;
    ms.status = "calculated";
    ms.confirmedAt = null;
    closeOverlay();
    showToast("已撤销确认，回到已计算；可继续修改");
  }

  function doLock() {
    const ms = monthState();
    if (ms.status !== "confirmed") {
      showToast("需要先确认才能锁定", "error");
      return;
    }
    const version = (db.snapshots[state.month] || []).length + 1;
    ms.status = "locked";
    ms.lockedAt = nowLabel();
    ms.isStale = false;
    db.snapshots[state.month] = db.snapshots[state.month] || [];
    db.snapshots[state.month].push({
      version,
      lockedAt: ms.lockedAt,
      dayResults: resultsForMonth().length,
      employees: summariesForMonth().length,
      calcRunId: (db.calcRuns[state.month] || []).slice(-1)[0]?.id || "calc-demo",
      rulesVersion: "sha256:demo-rules-v1",
    });
    closeOverlay();
    showToast(`本月已锁定，生成快照 v${version}`);
  }

  function doUnlock() {
    const reason = (document.querySelector('[data-form="reason"]')?.value || "").trim();
    if (!reason) {
      showToast("解锁必须填写理由", "error");
      return;
    }
    const ms = monthState();
    if (ms.status !== "locked") return;
    ms.status = "calculated";
    ms.isStale = true;
    ms.unlockReason = reason;
    closeOverlay();
    showToast("已解锁，结果标记为过期；请重新计算后再确认");
  }

  function switchVariant(delta) {
    state.pageByVariant[state.variant] = state.page;
    const order = ["A", "B", "C"];
    let index = order.indexOf(state.variant);
    index = (index + delta + order.length) % order.length;
    state.variant = order[index];
    const fallback = state.variant === "C" ? "cockpit" : "schedule";
    let page = state.pageByVariant[state.variant] || fallback;
    const valid = {
      A: ["schedule", "import", "results", "rules", "shifts"],
      B: ["schedule", "import", "results", "rules", "shifts"],
      C: ["cockpit", "schedule", "import", "results", "rules"],
    };
    if (!valid[state.variant].includes(page)) page = fallback;
    state.page = page;
    state.overlay = null;
    state.draft = null;
    state.wizard = null;
    state.companyMenuOpen = false;
    state.mobileNav = false;
    state.preview = "normal";
    syncUrl();
    render();
  }

  function rerenderPreservingFocus() {
    const active = document.activeElement;
    const key = active?.getAttribute?.("data-input");
    const start = active?.selectionStart;
    const end = active?.selectionEnd;
    render();
    if (!key) return;
    const next = document.querySelector(`[data-input="${key}"]`);
    if (!next) return;
    next.focus();
    if (typeof start === "number" && next.setSelectionRange) {
      try {
        next.setSelectionRange(start, end);
      } catch (e) {
        /* ignore */
      }
    }
  }

  function renderBlockedOverlay(o) {
    return `<div class="modal-backdrop" data-action="close-overlay"></div>
      <div class="modal sm" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div><h2 class="modal-title">${esc(o.title || "操作被阻止")}</h2><p class="modal-sub">引用约束或月份状态不允许该操作</p></div>
          <button class="close-btn" data-action="close-overlay" aria-label="关闭">${icon("x")}</button>
        </div>
        <div class="modal-body">
          <div class="notice danger">${icon("alert")}<div>${esc(o.message || "")}</div></div>
        </div>
        <div class="modal-foot"><button class="btn btn-primary" data-action="close-overlay">知道了</button></div>
      </div>`;
  }

  /* ================================================================ events */

  document.addEventListener("click", (event) => {
    const actionEl = event.target.closest("[data-action]");
    if (!actionEl) {
      if (
        (state.companyMenuOpen && !event.target.closest(".company-switch-wrap")) ||
        (state.mobileNav && !event.target.closest(".sidebar") && !event.target.closest(".mobile-menu-btn"))
      ) {
        state.companyMenuOpen = false;
        state.mobileNav = false;
        render();
      }
      return;
    }
    const action = actionEl.dataset.action;
    const id = actionEl.dataset.id;
    const date = actionEl.dataset.date;
    const employee = actionEl.dataset.employee;

    switch (action) {
      case "stub":
        showToast(`${actionEl.dataset.label || "该功能"}已由基础管理实现，本原型聚焦考勤。`);
        break;
      case "nav": {
        const page = actionEl.dataset.page;
        state.page = page;
        state.pageByVariant[state.variant] = page;
        state.mobileNav = false;
        state.overlay = null;
        state.draft = null;
        state.wizard = null;
        state.flash = null;
        syncUrl();
        render();
        break;
      }
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
      case "select-company":
        state.companyId = actionEl.dataset.company;
        state.companyMenuOpen = false;
        state.overlay = null;
        state.resultPage = 1;
        state.scopeFilter = "all";
        state.selectedPlanId = "all";
        syncUrl();
        render();
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
      case "set-preview":
        state.preview = actionEl.dataset.preview;
        if (state.preview !== "normal") syncUrl();
        render();
        break;
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
      case "reset-prototype":
        window.location.href = `${window.location.pathname}?variant=${state.variant}&page=${
          state.variant === "C" ? "cockpit" : "schedule"
        }&month=2026-09&theme=${state.theme}`;
        break;
      case "close-overlay":
        closeOverlay();
        break;
      case "month-prev":
        if (state.month === "2026-10") {
          state.month = "2026-09";
          state.selectedDate = null;
          state.selectedPlanId = "all";
          state.resultDate = null;
          state.resultPage = 1;
          state.holidayMonth = "2026-09";
          state.overlay = null;
          syncUrl();
          render();
        }
        break;
      case "month-next":
        if (state.month === "2026-09") {
          state.month = "2026-10";
          state.selectedDate = null;
          state.selectedPlanId = "all";
          state.resultDate = null;
          state.resultPage = 1;
          state.holidayMonth = "2026-10";
          state.overlay = null;
          syncUrl();
          render();
        }
        break;
      case "holiday-month-prev":
        if (state.holidayMonth === "2026-10") {
          state.holidayMonth = "2026-09";
          render();
        }
        break;
      case "holiday-month-next":
        if (state.holidayMonth === "2026-09") {
          state.holidayMonth = "2026-10";
          render();
        }
        break;
      case "open-plan-editor":
        openPlanEditor(id);
        break;
      case "select-plan":
        state.selectedPlanId = id;
        state.scheduleView = "plan";
        state.overlay = null;
        render();
        break;
      case "select-scope":
        state.scopeFilter = actionEl.dataset.scope;
        state.scheduleView = "plan";
        render();
        break;
      case "select-employee":
        state.selectedEmployeeId = actionEl.dataset.employee;
        state.scheduleView = "employee";
        render();
        break;
      case "schedule-view":
        state.scheduleView = actionEl.dataset.view;
        if (state.scheduleView === "employee" && !state.selectedEmployeeId) {
          state.selectedEmployeeId = activeEmployees()[0]?.id || "";
        }
        render();
        break;
      case "open-day-sheet":
        state.selectedDate = date;
        openOverlay("day-sheet", { date });
        break;
      case "open-plan-day":
        openPlanDay(id || state.selectedPlanId, date);
        break;
      case "open-exception":
        openException(employee || state.selectedEmployeeId, date || state.selectedDate || `${state.month}-01`);
        break;
      case "open-day-bulk":
        openDayBulk(date);
        break;
      case "open-batch-fill":
        openBatchFill();
        break;
      case "open-copy-month":
        openCopyMonth();
        break;
      case "open-sync-people":
        openOverlay("sync-people");
        break;
      case "open-conflicts":
        openOverlay("conflicts");
        break;
      case "select-mini-date":
        state.selectedDate = actionEl.dataset.date;
        if (state.page === "results") {
          state.resultDate = actionEl.dataset.date;
          state.resultPage = 1;
        } else if (state.page !== "schedule") {
          state.page = "schedule";
          state.pageByVariant[state.variant] = "schedule";
          syncUrl();
        }
        render();
        break;
      case "goto-employee-results":
        state.page = "results";
        state.pageByVariant[state.variant] = "results";
        state.resultTab = "days";
        state.resultFilter = "all";
        state.resultSearch = employeeName(actionEl.dataset.employee);
        state.resultPage = 1;
        syncUrl();
        render();
        break;
      case "bulk-select-all":
        state.draft.employeeIds = scopedEmployees().map((e) => e.id);
        render();
        break;
      case "bulk-select-none":
        state.draft.employeeIds = [];
        render();
        break;
      case "bulk-state":
        state.draft.state = actionEl.dataset.state;
        render();
        break;
      case "bulk-shift": {
        const code = actionEl.dataset.code;
        const list = state.draft.shifts || [];
        state.draft.shifts = list.includes(code)
          ? list.filter((c) => c !== code)
          : [...list, code];
        render();
        break;
      }
      case "save-day-bulk":
        saveDayBulk();
        break;
      case "exception-state":
        state.draft.state = actionEl.dataset.state;
        render();
        break;
      case "exception-shift": {
        const code = actionEl.dataset.code;
        const list = state.draft.shifts || [];
        state.draft.shifts = list.includes(code)
          ? list.filter((c) => c !== code)
          : [...list, code];
        render();
        break;
      }
      case "save-exception":
        saveException();
        break;
      case "delete-exception":
        deleteException();
        break;
      case "plan-day-shift": {
        const code = actionEl.dataset.code;
        const list = state.draft.shifts || [];
        state.draft.shifts = list.includes(code)
          ? list.filter((c) => c !== code)
          : [...list, code];
        render();
        break;
      }
      case "save-plan-day":
        state.overlay = { ...state.overlay, empty: !!actionEl.dataset.empty };
        savePlanDay();
        break;
      case "plan-scope-type":
        state.draft.scopeType = actionEl.dataset.scopeType;
        state.draft.scopeIds = [];
        render();
        break;
      case "weekday-shift": {
        const wd = actionEl.dataset.wd;
        const code = actionEl.dataset.code;
        const list = state.draft.weekdays[wd] || [];
        state.draft.weekdays[wd] = list.includes(code)
          ? list.filter((c) => c !== code)
          : [...list, code];
        render();
        break;
      }
      case "save-plan":
        savePlan();
        break;
      case "batch-mode":
        state.draft.mode = actionEl.dataset.mode;
        render();
        break;
      case "batch-weekday": {
        const wd = Number(actionEl.dataset.wd);
        const list = state.draft.weekdays || [];
        state.draft.weekdays = list.includes(wd)
          ? list.filter((d) => d !== wd)
          : [...list, wd];
        render();
        break;
      }
      case "batch-shift": {
        const code = actionEl.dataset.code;
        const list = state.draft.shifts || [];
        state.draft.shifts = list.includes(code)
          ? list.filter((c) => c !== code)
          : [...list, code];
        render();
        break;
      }
      case "apply-batch-fill":
        applyBatchFill();
        break;
      case "copy-month":
        copyMonth();
        break;
      case "sync-people":
        syncPeople();
        break;
      case "locate-conflict":
        state.overlay = null;
        state.page = "schedule";
        state.pageByVariant[state.variant] = "schedule";
        state.scheduleView = "employee";
        state.selectedEmployeeId = employee;
        state.scopeFilter = "all";
        state.selectedDate = date;
        syncUrl();
        render();
        break;
      case "shift-color":
        state.draft.color = actionEl.dataset.color;
        render();
        break;
      case "open-shift-form":
        openShiftForm(actionEl.dataset.code || "");
        break;
      case "save-shift":
        saveShift();
        break;
      case "toggle-shift": {
        const code = actionEl.dataset.code;
        const shift = getShift(code);
        if (!shift) break;
        const refs = shiftReferenceCounts(code);
        if (shift.active === false) {
          shift.active = true;
          showToast(`班次「${shift.name}」已启用`);
          render();
        } else if (refs.enabledPlans > 0) {
          openOverlay("blocked", {
            title: "不能停用班次",
            message: `该班次被 ${refs.enabledPlans} 张启用方案引用。请先调整或归档这些方案，再停用班次。`,
          });
        } else {
          shift.active = false;
          showToast(`班次「${shift.name}」已停用；已有明细保留快照`);
          render();
        }
        break;
      }
      case "open-shifts-overlay":
        openOverlay("shifts-overlay");
        break;
      case "save-rules":
        saveRules();
        break;
      case "open-holiday-form":
        state.draft = {
          date: `${state.holidayMonth}-01`,
          name: "",
          dayType: "holiday",
          note: "",
        };
        openOverlay("holiday-form");
        break;
      case "save-holiday":
        saveHoliday();
        break;
      case "delete-holiday":
        openOverlay("confirm", {
          title: "删除节假日",
          message: `确认删除 ${esc(date)} 的节假日记录？删除后草稿与已计算月份会标记过期。`,
          confirmAction: "confirm-delete-holiday",
          confirmLabel: "删除",
          danger: true,
          date,
        });
        break;
      case "confirm-delete-holiday":
        deleteHoliday(actionEl.dataset.date || date);
        break;
      case "copy-holidays":
        openOverlay("confirm", {
          title: "复制上一年",
          message:
            "正式实现会把上一年的节假日按同月同日映射到当前年，冲突日期跳过并给出预览。原型只演示入口与确认流程。",
          confirmAction: "confirm-copy-holidays",
          confirmLabel: "知道了",
        });
        break;
      case "confirm-copy-holidays":
        closeOverlay();
        showToast("原型演示：已模拟复制上一年节假日；正式实现会提供日期映射预览");
        break;
      case "open-override-form":
        openOverlay("override-form", { id });
        break;
      case "save-override":
        saveOverride(id);
        break;
      case "select-import-type":
        state.importType = actionEl.dataset.type;
        render();
        break;
      case "open-import-wizard":
        openImportWizard(actionEl.dataset.type || state.importType);
        break;
      case "wizard-type":
        state.wizard.dataType = actionEl.dataset.type;
        state.wizard.fileName = "";
        state.wizard.pasted = "";
        state.wizard.mapping = {};
        for (const f of db.importSamples[state.wizard.dataType].fields) {
          state.wizard.mapping[f.key] = f.column;
        }
        render();
        break;
      case "wizard-next":
        if (state.wizard.step === 1) {
          if (!state.wizard.fileName && !state.wizard.pasted.trim()) {
            showToast("请选择样例文件，或粘贴一段带表头的文本", "error");
            break;
          }
          state.wizard.step = 2;
        } else if (state.wizard.step === 2) {
          const missing = wizardMissingRequired();
          if (missing.length) {
            showToast(`缺少必填映射：${missing.map((f) => f.label).join("、")}`, "error");
            break;
          }
          state.wizard.step = 3;
        }
        render();
        break;
      case "wizard-back":
        if (state.wizard.step > 1) state.wizard.step -= 1;
        render();
        break;
      case "wizard-use-sample":
        state.wizard.fileName = wizardSample().file;
        state.wizard.source = "upload";
        render();
        break;
      case "wizard-choose-file":
        document.getElementById("wizard-file")?.click();
        break;
      case "wizard-commit":
        commitWizard();
        break;
      case "open-batch-detail":
        openOverlay("batch-detail", { id });
        break;
      case "open-commit-batch": {
        const batch = db.importBatches.find((b) => b.id === id);
        if (!batch) break;
        openOverlay("confirm", {
          title: "提交导入批次",
          message: `提交后本批次将成为 ${monthCN(batch.month)} 的${esc(
            db.importSamples[batch.dataType].label,
          )}生效批次；旧批次被置为已替代，本月结果标记过期。`,
          confirmAction: "commit-batch",
          confirmLabel: "提交生效",
          id,
        });
        break;
      }
      case "commit-batch":
        commitBatch(id);
        break;
      case "open-discard-batch": {
        const batch = db.importBatches.find((b) => b.id === id);
        if (!batch) break;
        openOverlay("confirm", {
          title: "丢弃预览批次",
          message: "预览行、错误与 raw_row 将立即删除；该批次不再参与任何计算。",
          confirmAction: "discard-batch",
          confirmLabel: "丢弃",
          danger: true,
          id,
        });
        break;
      }
      case "discard-batch": {
        const batch = db.importBatches.find((b) => b.id === id);
        if (batch && batch.status === "preview") {
          batch.status = "discarded";
          batch.discardedAt = nowLabel();
          batch.discardReason = "user";
          closeOverlay();
          showToast("预览批次已丢弃");
        }
        break;
      }
      case "open-revoke": {
        const batch = db.importBatches.find((b) => b.id === id);
        if (!batch) break;
        openOverlay("confirm", {
          title: "撤销生效批次",
          message:
            "撤销会删除该批次的行、错误与 raw_row；旧批次不会自动恢复；本月结果标记过期。只允许在草稿或已计算月份操作。",
          confirmAction: "revoke-batch",
          confirmLabel: "撤销批次",
          danger: true,
          id,
        });
        break;
      }
      case "revoke-batch": {
        const batch = db.importBatches.find((b) => b.id === id);
        if (!batch || batch.status !== "committed") break;
        if (!isEditable(batch.month)) {
          showToast("月份已确认或锁定，不能撤销", "error");
          break;
        }
        batch.status = "revoked";
        batch.revokedAt = nowLabel();
        markStale(batch.month);
        closeOverlay();
        showToast("批次已撤销；本月结果标记过期");
        break;
      }
      case "open-result":
        state.selectedDate = date;
        openOverlay("result-drawer", { employee, date });
        break;
      case "open-employee-summary":
        openOverlay("employee-summary", { employee });
        break;
      case "filter-employee-results":
        state.overlay = null;
        state.draft = null;
        state.page = "results";
        state.pageByVariant[state.variant] = "results";
        state.resultTab = "days";
        state.resultFilter = "all";
        state.resultSearch = employeeName(actionEl.dataset.employee);
        state.resultPage = 1;
        syncUrl();
        render();
        break;
      case "clear-result-date":
        state.resultDate = null;
        render();
        break;
      case "result-tab":
        state.resultTab = actionEl.dataset.tab;
        state.resultPage = 1;
        render();
        break;
      case "result-page":
        state.resultPage = Number(actionEl.dataset.page) || 1;
        render();
        break;
      case "open-recalc":
        openOverlay("confirm-recalc");
        break;
      case "do-recalc":
        recalcMonth();
        break;
      case "open-confirm-month":
        openOverlay("confirm-confirm");
        break;
      case "do-confirm-month":
        doConfirmMonth();
        break;
      case "undo-confirm":
        state.overlay = null;
        undoConfirm();
        break;
      case "open-lock-month":
        openOverlay("confirm-lock");
        break;
      case "do-lock":
        doLock();
        break;
      case "open-unlock":
        openOverlay("unlock");
        break;
      case "do-unlock":
        doUnlock();
        break;
      case "open-export":
        openOverlay("export");
        break;
      case "open-snapshot":
        openOverlay("snapshot");
        break;
      case "download-payroll": {
        const rows = [
          [
            "attendance_month",
            "company_name",
            "employee_no",
            "employee_name",
            "department_name",
            "weekday_full",
            "weekend_full",
            "weekday_attended",
            "weekend_attended",
            "paid_leave_days",
            "ot_weekday_hours",
            "ot_weekend_hours",
            "ot_holiday_hours",
            "attendance_deduct",
          ],
          ...summariesForMonth().map((s) => [
            state.month,
            currentCompany().name,
            s.employeeNo,
            s.employeeName,
            s.deptName,
            s.weekdayFull,
            s.weekendFull,
            s.weekdayAttended,
            s.weekendAttended,
            s.paidLeaveDays,
            s.otWeekdayHours,
            s.otWeekendHours,
            s.otHolidayHours,
            s.attendanceDeduct,
          ]),
        ];
        downloadCsv(`attendance-payroll-${state.month}.csv`, rows);
        showToast("薪酬回填 CSV 已生成");
        break;
      }
      case "download-detail": {
        const rows = [
          [
            "date",
            "employee_name",
            "employee_no",
            "day_type",
            "roster_state",
            "day_status",
            "attendance_fraction",
            "worked_minutes",
            "ot_weekday_minutes",
            "ot_weekend_minutes",
            "ot_holiday_minutes",
            "deduction_total",
          ],
          ...resultsForMonth().map((r) => [
            r.date,
            employeeName(r.employeeId),
            getEmployee(r.employeeId)?.no || "",
            r.dayType,
            r.rosterState,
            r.dayStatus,
            r.attendanceFraction,
            r.workedMinutes,
            r.otWeekdayMinutes,
            r.otWeekendMinutes,
            r.otHolidayMinutes,
            r.deductionTotal,
          ]),
        ];
        downloadCsv(`attendance-detail-${state.month}.csv`, rows);
        showToast("考勤明细 CSV 已生成");
        break;
      }
      case "open-adjust":
        openAdjust(employee, date);
        break;
      case "save-adjustment":
        saveAdjustment();
        break;
      case "noop":
        closeOverlay();
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
      } else if (name === "employee-dept") {
        state.scopeFilter = value === "all" ? "all" : `dept:${value}`;
        state.scheduleView = "employee";
        render();
      } else if (name === "result-dept") {
        state.resultDept = value;
        state.resultPage = 1;
        render();
      } else if (name === "result-status") {
        state.resultStatus = value;
        state.resultPage = 1;
        render();
      } else if (name === "mapping-field") {
        state.wizard.mapping[target.dataset.field] = value;
        render();
      } else if (name === "wizard-month") {
        state.wizard.month = value;
        render();
      } else if (name === "batch-plan") {
        state.draft.planId = value;
        render();
      } else if (name === "copy-plan") {
        state.draft.planId = value;
        render();
      }
      return;
    }
    if (target.matches("[data-check]")) {
      const name = target.dataset.check;
      if (name === "result-exceptions") {
        state.resultFilter = target.checked ? "exceptions" : "all";
        state.resultPage = 1;
        render();
      } else if (name === "result-adjusted") {
        state.resultAdjusted = target.checked;
        state.resultPage = 1;
        render();
      } else if (name === "bulk-employee") {
        const list = new Set(state.draft.employeeIds || []);
        if (target.checked) list.add(target.value);
        else list.delete(target.value);
        state.draft.employeeIds = Array.from(list);
        render();
      } else if (name === "plan-scope") {
        const list = new Set(state.draft.scopeIds || []);
        if (target.checked) list.add(target.value);
        else list.delete(target.value);
        state.draft.scopeIds = Array.from(list);
        render();
      } else if (name === "copy-exceptions") {
        state.draft.copyExceptions = target.checked;
        render();
      }
      return;
    }
    if (target.matches('[data-input="wizard-file"]')) {
      const file = target.files && target.files[0];
      if (file) {
        state.wizard.fileName = file.name;
        state.wizard.source = "upload";
        render();
      }
    }
  });

  document.addEventListener("input", (event) => {
    const target = event.target;
    const name = target.getAttribute("data-input");
    if (name === "employee-search") {
      state.employeeSearch = target.value;
      rerenderPreservingFocus();
    } else if (name === "result-search") {
      state.resultSearch = target.value;
      state.resultPage = 1;
      rerenderPreservingFocus();
    } else if (name === "result-date") {
      state.resultDate = target.value || null;
      state.resultPage = 1;
      rerenderPreservingFocus();
    } else if (name === "wizard-paste") {
      state.wizard.pasted = target.value;
      state.wizard.source = "paste";
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
      if (
        ["input", "textarea", "select"].includes(tag) ||
        event.target.isContentEditable ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey
      ) {
        return;
      }
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

  /* __APPEND__ */

  parseUrl();
  render();
})();
