/* Attendance IA prototype — seed data and a deliberately simplified evaluator.
 * NOT production code. The evaluator exists only to keep the four-way
 * comparison screen coherent; golden cases in docs/specs/attendance-golden-cases
 * remain the calculation contract. */
(() => {
  "use strict";

  /* ---------------------------------------------------------------- helpers */

  const pad = (n) => String(n).padStart(2, "0");
  const clone = (value) => JSON.parse(JSON.stringify(value));

  function parseDate(s) {
    const [y, m, d] = s.split("-").map(Number);
    return new Date(Date.UTC(y, m - 1, d));
  }
  function dateStr(dt) {
    return `${dt.getUTCFullYear()}-${pad(dt.getUTCMonth() + 1)}-${pad(dt.getUTCDate())}`;
  }
  function addDays(s, n) {
    const dt = parseDate(s);
    dt.setUTCDate(dt.getUTCDate() + n);
    return dateStr(dt);
  }
  function weekdayIndex(s) {
    return (parseDate(s).getUTCDay() + 6) % 7; // Mon=0 … Sun=6
  }
  function daysInMonth(month) {
    const [y, m] = month.split("-").map(Number);
    return new Date(Date.UTC(y, m, 0)).getUTCDate();
  }
  function dateList(month) {
    const n = daysInMonth(month);
    return Array.from({ length: n }, (_, i) => `${month}-${pad(i + 1)}`);
  }
  function monthOf(date) {
    return date.slice(0, 7);
  }
  function toMinutes(hhmm) {
    const [h, m] = hhmm.split(":").map(Number);
    return h * 60 + m;
  }
  function atMinutes(date, hhmm) {
    return Math.floor(parseDate(date).getTime() / 60000) + toMinutes(hhmm);
  }
  function round1(n) {
    return Math.round(n * 10) / 10;
  }
  function round2(n) {
    return Math.round(n * 100) / 100;
  }
  function overlaps(aStart, aEnd, bStart, bEnd) {
    return Math.max(0, Math.min(aEnd, bEnd) - Math.max(aStart, bStart));
  }

  /* ---------------------------------------------------------------- seed */

  const COMPANIES = [
    {
      id: "c1",
      code: "RX",
      name: "荣新矿业",
      active: true,
      note: "煤矿生产与洗选",
    },
    {
      id: "c2",
      code: "RXWL",
      name: "荣新物流",
      active: true,
      note: "物流运输与仓储（原型中暂无考勤数据）",
    },
  ];

  const DEPARTMENTS = [
    { id: "d1", companyId: "c1", name: "总部", parentId: null, order: 10 },
    { id: "d2", companyId: "c1", name: "生产部", parentId: "d1", order: 20 },
    { id: "d3", companyId: "c1", name: "财务部", parentId: "d1", order: 30 },
    { id: "d4", companyId: "c1", name: "技术部", parentId: "d1", order: 40 },
    { id: "d5", companyId: "c1", name: "行政部", parentId: "d1", order: 50 },
    { id: "d6", companyId: "c1", name: "一车间", parentId: "d2", order: 10 },
    { id: "d7", companyId: "c1", name: "二车间", parentId: "d2", order: 20 },
  ];

  const POSITIONS = [
    { id: "p-line", name: "生产线班长" },
    { id: "p-op", name: "操作工" },
    { id: "p-acc", name: "会计" },
    { id: "p-tech", name: "技术员" },
    { id: "p-admin", name: "行政专员" },
  ];

  const EMPLOYEES = [
    { id: "E101", no: "E101", name: "冯芷茵", deptId: "d6", positionId: "p-op", hireDate: "2020-04-11", resignDate: null, status: "active" },
    { id: "E102", no: "E102", name: "刘衍英", deptId: "d3", positionId: "p-acc", hireDate: "2018-09-03", resignDate: null, status: "active" },
    { id: "E103", no: "E103", name: "周玉琼", deptId: "d6", positionId: "p-op", hireDate: "2019-03-18", resignDate: null, status: "active" },
    { id: "E104", no: "E104", name: "胡国邵", deptId: "d6", positionId: "p-op", hireDate: "2017-06-01", resignDate: null, status: "active" },
    { id: "E105", no: "E105", name: "李金辉", deptId: "d7", positionId: "p-op", hireDate: "2021-11-08", resignDate: null, status: "active" },
    { id: "E106", no: "E106", name: "黄佳誉", deptId: "d4", positionId: "p-tech", hireDate: "2020-02-17", resignDate: null, status: "active" },
    { id: "E107", no: "E107", name: "梁林高", deptId: "d5", positionId: "p-admin", hireDate: "2016-05-23", resignDate: null, status: "active" },
    { id: "E108", no: "E108", name: "黄国锋", deptId: "d7", positionId: "p-line", hireDate: "2019-08-30", resignDate: null, status: "active" },
    { id: "E109", no: "E109", name: "申佳林", deptId: "d5", positionId: "p-admin", hireDate: "2015-10-12", resignDate: null, status: "active" },
    { id: "E110", no: "E110", name: "张伟", deptId: "d6", positionId: "p-op", hireDate: "2019-01-01", resignDate: null, status: "active" },
    { id: "E111", no: "E111", name: "张伟", deptId: "d3", positionId: "p-acc", hireDate: "2020-01-01", resignDate: null, status: "active" },
    { id: "E112", no: "E112", name: "王强", deptId: "d6", positionId: "p-op", hireDate: "2018-01-01", resignDate: "2026-08-31", status: "resigned" },
    { id: "E113", no: "E113", name: "李娜", deptId: "d7", positionId: "p-op", hireDate: "2026-09-15", resignDate: null, status: "probation" },
  ];

  const SHIFTS = [
    { code: "ADM", name: "行政班", start: "08:30", end: "17:30", crossDay: false, breakStart: null, breakEnd: null, restMinutes: 60, color: "blue", note: "职能与行政默认班次" },
    { code: "TEC", name: "技术员班", start: "08:00", end: "18:00", crossDay: false, breakStart: null, breakEnd: null, restMinutes: 60, color: "sky", note: "" },
    { code: "YL", name: "园林班", start: "07:30", end: "17:30", crossDay: false, breakStart: "11:30", breakEnd: "13:30", restMinutes: 120, color: "green", note: "午休 2 小时，需 4 次打卡" },
    { code: "EARLY", name: "早班", start: "06:00", end: "14:00", crossDay: false, breakStart: null, breakEnd: null, restMinutes: 60, color: "amber", note: "生产早班" },
    { code: "MID", name: "中班", start: "14:00", end: "22:00", crossDay: false, breakStart: null, breakEnd: null, restMinutes: 60, color: "purple", note: "生产中班" },
    { code: "NIGHT", name: "夜班", start: "22:00", end: "06:00", crossDay: true, breakStart: "02:00", breakEnd: "03:00", restMinutes: 60, color: "indigo", note: "跨天班次" },
    { code: "DAWN", name: "凌晨班", start: "02:00", end: "10:00", crossDay: false, breakStart: null, breakEnd: null, restMinutes: 60, color: "pink", note: "" },
  ];

  const PLANS = [
    {
      id: "plan-p2",
      companyId: "c1",
      month: "2026-09",
      name: "生产部早中班",
      scopeType: "dept",
      scopeIds: ["d2"],
      status: "enabled",
      note: "周二、周四双班；09-25 中秋休息，09-27 调休上班",
      weekdays: {
        0: ["EARLY"],
        1: ["EARLY", "MID"],
        2: ["EARLY"],
        3: ["EARLY", "MID"],
        4: ["EARLY"],
        5: [],
        6: [],
      },
      dayOverrides: { 25: [], 27: ["EARLY"] },
    },
    {
      id: "plan-p3",
      companyId: "c1",
      month: "2026-09",
      name: "技术部技术员班",
      scopeType: "dept",
      scopeIds: ["d4"],
      status: "enabled",
      note: "技术部固定技术员班",
      weekdays: { 0: ["TEC"], 1: ["TEC"], 2: ["TEC"], 3: ["TEC"], 4: ["TEC"], 5: [], 6: [] },
      dayOverrides: { 25: [], 27: ["TEC"] },
    },
    {
      id: "plan-p4",
      companyId: "c1",
      month: "2026-09",
      name: "财务部行政班",
      scopeType: "dept",
      scopeIds: ["d3"],
      status: "enabled",
      note: "财务部固定行政班",
      weekdays: { 0: ["ADM"], 1: ["ADM"], 2: ["ADM"], 3: ["ADM"], 4: ["ADM"], 5: [], 6: [] },
      dayOverrides: { 25: [], 27: ["ADM"] },
    },
    {
      id: "plan-p1",
      companyId: "c1",
      month: "2026-09",
      name: "2026-09 标准班",
      scopeType: "all",
      scopeIds: [],
      status: "enabled",
      note: "全公司兜底方案；行政部等未单独建方案的部门使用",
      weekdays: { 0: ["ADM"], 1: ["ADM"], 2: ["ADM"], 3: ["ADM"], 4: ["ADM"], 5: [], 6: [] },
      dayOverrides: { 25: [], 27: ["ADM"] },
    },
  ];

  const PLAN_RULE_OVERRIDES = {
    "plan-p2": {
      late_grace_min: 10,
      ot_threshold_min: 15,
      absent_deduct_per_day: 150,
      missing_punch_deduct_per_occurrence: 15,
    },
    "plan-p4": {
      missing_punch_deduct_per_occurrence: 5,
    },
  };

  const RULES = {
    punch_window_min: 120,
    late_cap_min: 240,
    early_cap_min: 240,
    ot_max_min: 600,
    late_grace_min: 5,
    early_grace_min: 5,
    ot_threshold_min: 30,
    absent_if_no_punch: true,
    break_punch_required: true,
    break_punch_tolerance_min: 60,
    absent_deduct_per_day: 100,
    late_deduct_per_occurrence: 20,
    early_deduct_per_occurrence: 20,
    missing_punch_deduct_per_occurrence: 10,
  };

  const HOLIDAYS = {
    "2026-09": [
      { date: "2026-09-25", name: "中秋节", dayType: "holiday", note: "法定节假日" },
      { date: "2026-09-27", name: "调休上班", dayType: "adjusted_workday", note: "原型示例：周日按工作日" },
    ],
    "2026-10": [
      { date: "2026-10-01", name: "国庆节", dayType: "holiday", note: "" },
      { date: "2026-10-02", name: "国庆节", dayType: "holiday", note: "" },
      { date: "2026-10-03", name: "国庆节", dayType: "holiday", note: "" },
      { date: "2026-10-04", name: "国庆节", dayType: "holiday", note: "" },
      { date: "2026-10-05", name: "国庆节", dayType: "holiday", note: "" },
      { date: "2026-10-06", name: "国庆节", dayType: "holiday", note: "" },
      { date: "2026-10-07", name: "国庆节", dayType: "holiday", note: "" },
      { date: "2026-10-10", name: "调休上班", dayType: "adjusted_workday", note: "原型示例" },
    ],
  };

  const MANUAL_EXCEPTIONS = {
    "E101|2026-09-18": { employeeId: "E101", date: "2026-09-18", state: "work", shifts: ["MID"], note: "临时调中班，已口头确认" },
    "E104|2026-09-10": { employeeId: "E104", date: "2026-09-10", state: "work", shifts: ["EARLY", "YL"], note: "技能培训顶岗（两班时间重叠）" },
    "E104|2026-09-22": { employeeId: "E104", date: "2026-09-22", state: "rest", shifts: [], note: "设备检修，安排休息" },
    "E105|2026-09-30": { employeeId: "E105", date: "2026-09-30", state: "work", shifts: ["NIGHT"], note: "月底盘点夜班" },
    "E106|2026-09-19": { employeeId: "E106", date: "2026-09-19", state: "work", shifts: ["TEC"], note: "系统上线值守" },
    "E110|2026-09-05": { employeeId: "E110", date: "2026-09-05", state: "work", shifts: ["EARLY"], note: "周六加班（已审批）" },
  };

  const TRIPS = [
    { id: "TRIP-001", employeeId: "E101", kind: "out", start: "2026-09-16 06:00", end: "2026-09-16 10:00", place: "高要城区", reason: "外出采购生产辅料", approvalNo: "AP-001", result: "审批通过" },
    { id: "TRIP-002", employeeId: "E106", kind: "business", start: "2026-09-17 08:00", end: "2026-09-17 18:00", place: "佛山", reason: "参加技术培训", approvalNo: "AP-002", result: "审批通过" },
    { id: "TRIP-003", employeeId: "E107", kind: "business", start: "2026-09-24 08:30", end: "2026-09-24 17:30", place: "佛山", reason: "外出办事", approvalNo: "AP-003", result: "审批通过" },
    { id: "TRIP-004", employeeId: "E104", kind: "out", start: "2026-09-22 09:00", end: "2026-09-22 12:00", place: "肇庆", reason: "设备检修外勤", approvalNo: "AP-004", result: "审批通过" },
  ];

  const OVERTIME = [
    { id: "OT-001", employeeId: "E108", start: "2026-09-14 18:10", end: "2026-09-14 21:40", declared: "3.5", reason: "赶货", approvalNo: "AP-OT-001", result: "审批通过", days: { "2026-09-14": 210 } },
    { id: "OT-002", employeeId: "E108", start: "2026-09-15 18:00", end: "2026-09-15 21:30", declared: "3", reason: "赶货", approvalNo: "AP-OT-002", result: "审批通过", days: { "2026-09-15": 210 } },
    { id: "OT-003", employeeId: "E103", start: "2026-09-13 08:00", end: "2026-09-13 16:00", declared: "8", reason: "设备检修", approvalNo: "AP-OT-003", result: "审批通过", days: { "2026-09-13": 480 } },
    { id: "OT-004", employeeId: "E108", start: "2026-09-20 08:00", end: "2026-09-20 12:00", declared: "4", reason: "周末巡检", approvalNo: "AP-OT-004", result: "审批通过", days: { "2026-09-20": 240 } },
    { id: "OT-005", employeeId: "E106", start: "2026-09-24 18:00", end: "2026-09-24 21:00", declared: "3", reason: "系统上线", approvalNo: "AP-OT-005", result: "审批通过", days: { "2026-09-24": 180 } },
  ];

  const LEAVES = [
    { id: "LEAVE-001", employeeId: "E101", kind: "unpaid", days: 2, restStart: "2026-09-27 08:30", restEnd: "2026-09-28 17:30", workStart: null, workEnd: null, reason: "家中有事", approvalNo: "AP-LV-001", result: "审批通过", typeRaw: "事假" },
    { id: "LEAVE-002", employeeId: "E102", kind: "paid", days: 0.5, restStart: "2026-09-18 08:30", restEnd: "2026-09-18 12:00", workStart: null, workEnd: null, reason: "上午产检", approvalNo: "AP-LV-002", result: "审批通过", typeRaw: "带薪假（需出示相关证明）" },
    { id: "LEAVE-003", employeeId: "E103", kind: "comp", days: 1, restStart: "2026-09-16 08:30", restEnd: "2026-09-16 17:30", workStart: "2026-09-13 08:00", workEnd: "2026-09-13 16:00", reason: "调休", approvalNo: "AP-LV-003", result: "审批通过", typeRaw: "调休" },
  ];

  const ADJUSTMENTS = [
    {
      id: "adj-1",
      employeeId: "E107",
      date: "2026-09-03",
      version: 1,
      status: "active",
      originalValues: { dayStatus: "late", lateMinutes: 10, lateCount: 1 },
      adjustedValues: { dayStatus: "normal", lateMinutes: 0, lateCount: 0 },
      reason: "门禁故障，主管已核实",
      adjustedBy: "管理员",
      adjustedAt: "2026-09-30 10:12",
    },
  ];

  const PUNCH_OVERRIDES = {
    "E101|2026-09-01": [
      { date: "2026-09-01", time: "05:58", result: "正常", device: "考勤机", address: "二号门" },
      { date: "2026-09-01", time: "14:00", result: "正常", device: "考勤机", address: "二号门" },
      { date: "2026-09-01", time: "22:05", result: "正常", device: "考勤机", address: "二号门" },
    ],
    "E103|2026-09-03": [
      { date: "2026-09-03", time: "05:58", result: "正常", device: "考勤机", address: "二号门" },
      { date: "2026-09-03", time: "14:00", result: "正常", device: "考勤机", address: "二号门" },
      { date: "2026-09-03", time: "22:05", result: "正常", device: "考勤机", address: "二号门" },
    ],
    "E102|2026-09-02": [
      { date: "2026-09-02", time: "08:20", result: "正常", device: "考勤机", address: "三号门" },
      { date: "2026-09-02", time: "17:35", result: "正常", device: "考勤机", address: "三号门" },
    ],
    "E107|2026-09-03": [
      { date: "2026-09-03", time: "08:45", result: "迟到", device: "考勤机", address: "一号门" },
      { date: "2026-09-03", time: "17:30", result: "正常", device: "考勤机", address: "一号门" },
    ],
    "E109|2026-09-03": [
      { date: "2026-09-03", time: "08:28", result: "正常", device: "考勤机", address: "一号门" },
      { date: "2026-09-03", time: "17:05", result: "早退", device: "考勤机", address: "一号门" },
    ],
    "E103|2026-09-04": [
      { date: "2026-09-04", time: "06:05", result: "正常", device: "考勤机", address: "二号门" },
    ],
    "E104|2026-09-07": [],
    "E105|2026-09-30": [
      { date: "2026-09-30", time: "21:55", result: "正常", device: "考勤机", address: "二号门" },
      { date: "2026-10-01", time: "06:05", result: "正常", device: "考勤机", address: "二号门" },
    ],
    "E106|2026-09-16": [
      { date: "2026-09-16", time: "07:50", result: "正常", device: "手机_8454664", address: "技术楼" },
      { date: "2026-09-16", time: "18:10", result: "正常", device: "手机_8454664", address: "技术楼" },
    ],
    "E106|2026-09-17": [],
    "E107|2026-09-24": [],
    "E101|2026-09-16": [],
    "E101|2026-09-18": [
      { date: "2026-09-18", time: "13:58", result: "正常", device: "考勤机", address: "二号门" },
      { date: "2026-09-18", time: "22:03", result: "正常", device: "考勤机", address: "二号门" },
    ],
    "E101|2026-09-27": [],
    "E101|2026-09-28": [],
    "E102|2026-09-18": [
      { date: "2026-09-18", time: "12:25", result: "正常", device: "考勤机", address: "三号门" },
      { date: "2026-09-18", time: "17:28", result: "正常", device: "考勤机", address: "三号门" },
    ],
    "E103|2026-09-16": [],
    "E104|2026-09-22": [],
    "E106|2026-09-24": [],
    "E109|2026-09-12": [
      { date: "2026-09-12", time: "09:00", result: "正常", device: "考勤机", address: "一号门" },
      { date: "2026-09-12", time: "12:05", result: "正常", device: "考勤机", address: "一号门" },
    ],
    "E109|2026-09-25": [
      { date: "2026-09-25", time: "09:00", result: "正常", device: "考勤机", address: "一号门" },
      { date: "2026-09-25", time: "12:05", result: "正常", device: "考勤机", address: "一号门" },
    ],
  };

  const IMPORT_BATCHES = [
    {
      id: "b-punch-1",
      companyId: "c1",
      dataType: "punch",
      month: "2026-09",
      status: "committed",
      source: "upload",
      fileName: "punch-2026-09.csv",
      fileSize: "3.2 KB",
      operator: "管理员",
      createdAt: "2026-09-30 17:58",
      committedAt: "2026-09-30 18:02",
      sourceRows: 37,
      valid: 27,
      skipped: 10,
      errors: 4,
      warnings: 5,
    },
    {
      id: "b-punch-0",
      companyId: "c1",
      dataType: "punch",
      month: "2026-09",
      status: "superseded",
      source: "upload",
      fileName: "punch-2026-09-v1.csv",
      fileSize: "2.9 KB",
      operator: "管理员",
      createdAt: "2026-09-28 09:12",
      committedAt: "2026-09-28 09:15",
      supersededAt: "2026-09-30 18:02",
      sourceRows: 33,
      valid: 24,
      skipped: 9,
      errors: 3,
      warnings: 4,
    },
    {
      id: "b-trip-1",
      companyId: "c1",
      dataType: "trip",
      month: "2026-09",
      status: "committed",
      source: "upload",
      fileName: "oa-trip-2026-09.csv",
      fileSize: "2.1 KB",
      operator: "管理员",
      createdAt: "2026-09-30 18:06",
      committedAt: "2026-09-30 18:07",
      sourceRows: 15,
      valid: 8,
      skipped: 9,
      errors: 5,
      warnings: 0,
    },
    {
      id: "b-ot-1",
      companyId: "c1",
      dataType: "ot",
      month: "2026-09",
      status: "committed",
      source: "upload",
      fileName: "oa-overtime-2026-09.csv",
      fileSize: "1.8 KB",
      operator: "管理员",
      createdAt: "2026-09-30 18:08",
      committedAt: "2026-09-30 18:09",
      sourceRows: 15,
      valid: 8,
      skipped: 7,
      errors: 3,
      warnings: 1,
    },
    {
      id: "b-leave-1",
      companyId: "c1",
      dataType: "leave",
      month: "2026-09",
      status: "committed",
      source: "upload",
      fileName: "oa-leave-2026-09.csv",
      fileSize: "2.4 KB",
      operator: "管理员",
      createdAt: "2026-09-30 18:10",
      committedAt: "2026-09-30 18:11",
      sourceRows: 19,
      valid: 8,
      skipped: 11,
      errors: 8,
      warnings: 1,
    },
    {
      id: "b-punch-preview",
      companyId: "c1",
      dataType: "punch",
      month: "2026-10",
      status: "preview",
      source: "paste",
      fileName: "",
      fileSize: "",
      operator: "管理员",
      createdAt: "2026-11-14 10:30",
      expiresAt: "2026-11-15 10:30",
      sourceRows: 120,
      valid: 98,
      skipped: 22,
      errors: 7,
      warnings: 11,
    },
  ];

  const IMPORT_SAMPLES = {
    punch: {
      label: "打卡",
      file: "punch-2026-09.csv",
      headers: [
        "工号", "姓名", "部门", "考勤日期", "打卡时间", "打卡结果",
        "打卡设备", "打卡地址", "考勤时间",
      ],
      fields: [
        { key: "employee_no", label: "工号", required: true, column: "工号", sample: "E101" },
        { key: "employee_name", label: "姓名", required: false, column: "姓名", sample: "冯芷茵" },
        { key: "department_raw", label: "部门", required: false, column: "部门", sample: "生产部" },
        { key: "attendance_date", label: "考勤日期", required: true, column: "考勤日期", sample: "2026-09-01" },
        { key: "punch_time", label: "打卡时间", required: true, column: "打卡时间", sample: "2026-09-01 08:18" },
        { key: "punch_result", label: "打卡结果", required: true, column: "打卡结果", sample: "正常" },
        { key: "device_raw", label: "打卡设备", required: false, column: "打卡设备", sample: "考勤机" },
        { key: "address_raw", label: "打卡地址", required: false, column: "打卡地址", sample: "一号门" },
        { key: "scheduled_time", label: "考勤时间", required: false, column: "考勤时间", sample: "2026-09-01 08:00" },
      ],
      ignored: ["审批编号", "备注", "打卡来源"],
      stats: { sourceRows: 37, valid: 27, skipped: 10, errors: 4, warnings: 5 },
      skipCounts: { invalid_punch: 3, not_in_month: 1, duplicate_punch: 2, unknown_employee: 1, out_of_employment: 2, missing_punch_time: 1 },
      warningCounts: { empty_result: 1, name_mismatch: 1, date_mismatch: 1, result_conflict: 1, unknown_result: 1 },
      issues: [
        { row: 2, column: "打卡结果", code: "invalid_punch", severity: "skip", message: "打卡结果=打卡无效，已跳过" },
        { row: 9, column: "打卡时间", code: "duplicate_punch", severity: "skip", message: "与第 8 行完全重复，保留首条" },
        { row: 10, column: "工号", code: "unknown_employee", severity: "error", message: "工号 E999 在当前公司不存在" },
        { row: 21, column: "考勤日期", code: "out_of_employment", severity: "skip", message: "王强已于 2026-08-31 离职" },
        { row: 24, column: "打卡时间", code: "missing_punch_time", severity: "error", message: "打卡时间为空；考勤时间不兜底" },
        { row: 30, column: "打卡结果", code: "result_conflict", severity: "warning", message: "同刻结果不一致（正常 / 外勤），保留首条并告警" },
        { row: 23, column: "姓名", code: "name_mismatch", severity: "warning", message: "工号匹配但姓名不一致：源=E101 陈敏" },
        { row: 17, column: "打卡结果", code: "empty_result", severity: "warning", message: "打卡结果为空，按有效卡导入并告警" },
      ],
      samples: [
        ["E101", "冯芷茵", "生产部", "2026-09-01", "2026-09-01 08:18", "正常"],
        ["E103", "周玉琼", "生产部", "2026-09-03", "2026-09-03 14:00", "正常"],
        ["E108", "黄国锋", "生产部", "2026-09-02", "2026-09-02 07:55", "正常"],
      ],
    },
    trip: {
      label: "外出/出差",
      file: "oa-trip-2026-09.csv",
      headers: ["序号", "数据id", "申请类型", "出差人部门", "出差人", "开始时间", "结束时间", "出差天数", "外出事由", "审批编号", "审批结果", "审批状态"],
      fields: [
        { key: "employee_name", label: "出差人", required: true, column: "出差人", sample: "冯芷茵;刘衍英" },
        { key: "department_raw", label: "出差人部门", required: false, column: "出差人部门", sample: "生产部" },
        { key: "start_at", label: "开始时间", required: true, column: "开始时间", sample: "2026-09-17 08:00" },
        { key: "end_at", label: "结束时间", required: true, column: "结束时间", sample: "2026-09-17 18:00" },
        { key: "days_declared", label: "出差天数", required: false, column: "出差天数", sample: "1" },
        { key: "reason", label: "外出事由", required: false, column: "外出事由", sample: "参加培训" },
        { key: "approval_result", label: "审批结果", required: true, column: "审批结果", sample: "审批通过" },
        { key: "approval_no", label: "审批编号", required: false, column: "审批编号", sample: "AP-002" },
      ],
      ignored: ["序号", "数据id", "用车类型", "是否需要报销油补", "出发地点", "来回公里数", "同行人", "附件", "图片"],
      stats: { sourceRows: 15, valid: 8, skipped: 9, errors: 5, warnings: 0 },
      skipCounts: { unknown_employee: 2, invalid_range: 1, missing_required: 2, pending: 1, terminated: 1, rejected: 1, duplicate_approval: 1 },
      warningCounts: {},
      issues: [
        { row: 3, column: "出差人", code: "unknown_employee", severity: "error", message: "「不存在」不在当前公司档案中；同行冯芷茵正常导入" },
        { row: 4, column: "审批结果", code: "pending", severity: "skip", message: "审批中，不计入考勤" },
        { row: 7, column: "结束时间", code: "not_in_month", severity: "warning", message: "跨月出差 09-28 至 10-02；10 月需再次导入" },
        { row: 10, column: "结束时间", code: "invalid_range", severity: "error", message: "结束时间早于开始时间" },
        { row: 11, column: "结束时间", code: "missing_required", severity: "error", message: "缺少结束时间" },
        { row: 14, column: "审批编号", code: "duplicate_approval", severity: "skip", message: "同审批编号 + 同员工重复，保留首条" },
      ],
      samples: [
        ["冯芷茵", "生产部", "2026-09-16 08:00", "2026-09-16 12:00", "审批通过"],
        ["冯芷茵;刘衍英", "生产部", "2026-09-17 08:00", "2026-09-17 18:00", "审批通过"],
        ["梁林高", "行政部", "2026-09-24 08:30", "2026-09-24 17:30", "审批通过"],
      ],
    },
    ot: {
      label: "加班单",
      file: "oa-overtime-2026-09.csv",
      headers: ["序号", "数据id", "部门", "加班开始时间", "加班结束时间", "加班时长（天/小时）", "加班原因", "审批编号", "审批结果", "审批状态"],
      fields: [
        { key: "employee_name", label: "创建人", required: true, column: "创建人", sample: "黄国锋" },
        { key: "department_raw", label: "部门", required: false, column: "部门", sample: "生产部" },
        { key: "start_at", label: "加班开始时间", required: true, column: "加班开始时间", sample: "2026-09-14 18:10" },
        { key: "end_at", label: "加班结束时间", required: true, column: "加班结束时间", sample: "2026-09-14 21:40" },
        { key: "declared_raw", label: "加班时长（天/小时）", required: false, column: "加班时长（天/小时）", sample: "3.5" },
        { key: "reason", label: "加班原因", required: false, column: "加班原因", sample: "赶货" },
        { key: "approval_result", label: "审批结果", required: true, column: "审批结果", sample: "审批通过" },
        { key: "approval_no", label: "审批编号", required: false, column: "审批编号", sample: "AP-OT-001" },
      ],
      ignored: ["序号", "数据id", "附件", "图片", "当前负责人", "历史审批人"],
      stats: { sourceRows: 15, valid: 8, skipped: 7, errors: 3, warnings: 1 },
      skipCounts: { unknown_employee: 1, invalid_range: 1, missing_required: 1, pending: 1, terminated: 1, rejected: 1, duplicate_approval: 1 },
      warningCounts: { amount_mismatch: 1 },
      issues: [
        { row: 2, column: "加班时长", code: "amount_mismatch", severity: "warning", message: "申请填报 6 小时，按起止时间计算 10 小时（封顶 8）" },
        { row: 6, column: "审批结果", code: "pending", severity: "skip", message: "审批中，不计入考勤" },
        { row: 9, column: "创建人", code: "unknown_employee", severity: "error", message: "王小明不在当前公司档案中" },
        { row: 11, column: "加班结束时间", code: "invalid_range", severity: "error", message: "开始时间等于结束时间" },
        { row: 12, column: "加班开始时间", code: "missing_required", severity: "error", message: "缺少开始时间" },
        { row: 14, column: "审批编号", code: "duplicate_approval", severity: "skip", message: "同审批编号 + 同员工重复" },
      ],
      samples: [
        ["黄国锋", "生产部", "2026-09-14 18:10", "2026-09-14 21:40", "审批通过"],
        ["周玉琼", "生产部", "2026-09-13 08:00", "2026-09-13 16:00", "审批通过"],
        ["黄佳誉", "技术部", "2026-09-24 18:00", "2026-09-24 21:00", "审批通过"],
      ],
    },
    leave: {
      label: "请假/补休",
      file: "oa-leave-2026-09.csv",
      headers: ["序号", "数据id", "标题", "部门", "请假类型", "请假天数", "休息开始时间", "休息结束时间", "上班开始时间", "结余补休天数", "审批编号", "审批结果", "审批状态"],
      fields: [
        { key: "employee_name", label: "创建人", required: true, column: "创建人", sample: "冯芷茵" },
        { key: "department_raw", label: "部门", required: false, column: "部门", sample: "生产部" },
        { key: "leave_type_raw", label: "请假类型", required: true, column: "请假类型", sample: "事假" },
        { key: "days", label: "请假天数", required: true, column: "请假天数", sample: "2" },
        { key: "rest_start_at", label: "休息开始时间", required: true, column: "休息开始时间", sample: "2026-09-27 08:30" },
        { key: "rest_end_at", label: "休息结束时间", required: true, column: "休息结束时间", sample: "2026-09-28 17:30" },
        { key: "work_start_at", label: "上班开始时间", required: false, column: "上班开始时间", sample: "" },
        { key: "approval_result", label: "审批结果", required: true, column: "审批结果", sample: "审批通过" },
        { key: "approval_no", label: "审批编号", required: false, column: "审批编号", sample: "AP-LV-001" },
      ],
      ignored: ["序号", "数据id", "标题", "岗位类别", "上班结束时间", "结余补休天数", "请假说明", "图片"],
      stats: { sourceRows: 19, valid: 8, skipped: 11, errors: 8, warnings: 1 },
      skipCounts: { unknown_employee: 1, duplicate_name: 1, out_of_employment: 2, missing_required: 1, invalid_range: 1, invalid_leave_type: 2, pending: 1, rejected: 1, duplicate_approval: 1 },
      warningCounts: { missing_work_start: 1 },
      issues: [
        { row: 5, column: "上班开始时间", code: "missing_work_start", severity: "warning", message: "补休缺少上班开始时间；导入但不抵扣加班" },
        { row: 6, column: "请假类型", code: "invalid_leave_type", severity: "error", message: "婚假未识别；不静默默认事假" },
        { row: 11, column: "创建人", code: "duplicate_name", severity: "error", message: "张伟在公司内重名（E110 / E111），请补工号" },
        { row: 12, column: "创建人", code: "out_of_employment", severity: "skip", message: "王强已于 2026-08-31 离职" },
        { row: 15, column: "请假天数", code: "invalid_range", severity: "error", message: "请假天数必须大于 0" },
        { row: 18, column: "审批编号", code: "duplicate_approval", severity: "skip", message: "同审批编号 + 同员工重复" },
      ],
      samples: [
        ["冯芷茵", "生产部", "事假 2 天", "2026-09-27 08:30", "2026-09-28 17:30", "审批通过"],
        ["刘衍英", "财务部", "带薪假 0.5 天", "2026-09-18 08:30", "2026-09-18 12:00", "审批通过"],
        ["周玉琼", "生产部", "调休 1 天", "2026-09-16 08:30", "2026-09-16 17:30", "审批通过"],
      ],
    },
  };

  /* ---------------------------------------------------------------- derive */

  function getDept(db, id) {
    return db.departments.find((d) => d.id === id) || null;
  }
  function deptDescendants(db, id) {
    const out = [id];
    let changed = true;
    while (changed) {
      changed = false;
      for (const dept of db.departments) {
        if (dept.parentId && out.includes(dept.parentId) && !out.includes(dept.id)) {
          out.push(dept.id);
          changed = true;
        }
      }
    }
    return out;
  }
  function deptPath(db, id, sep = " / ") {
    const names = [];
    let cur = getDept(db, id);
    while (cur) {
      names.unshift(cur.name);
      cur = cur.parentId ? getDept(db, cur.parentId) : null;
    }
    return names.join(sep);
  }
  function getEmployee(db, id) {
    return db.employees.find((e) => e.id === id) || null;
  }
  function getShift(db, code) {
    return db.shifts.find((s) => s.code === code) || null;
  }
  function getPlan(db, id) {
    return db.plans.find((p) => p.id === id) || null;
  }
  function employedOn(emp, date) {
    if (!emp) return false;
    if (emp.hireDate && date < emp.hireDate) return false;
    if (emp.resignDate && date > emp.resignDate) return false;
    return true;
  }
  function employedInMonth(emp, month) {
    const first = `${month}-01`;
    const last = `${month}-${pad(daysInMonth(month))}`;
    if (emp.hireDate && emp.hireDate > last) return false;
    if (emp.resignDate && emp.resignDate < first) return false;
    return true;
  }
  function holidayOf(db, date) {
    const list = db.holidays[monthOf(date)] || [];
    return list.find((h) => h.date === date) || null;
  }
  function dayType(db, date) {
    const h = holidayOf(db, date);
    if (h && h.dayType === "adjusted_workday") return "workday";
    if (h && h.dayType === "holiday") return "holiday";
    return weekdayIndex(date) >= 5 ? "weekend" : "workday";
  }
  function dayTypeLabel(db, date) {
    const h = holidayOf(db, date);
    if (h && h.dayType === "adjusted_workday") return "调休上班";
    if (h && h.dayType === "holiday") return "法定节假日";
    return weekdayIndex(date) >= 5 ? "周末" : "工作日";
  }

  function planCovers(db, plan, emp) {
    if (plan.scopeType === "all") return true;
    if (plan.scopeType === "dept") {
      const ids = new Set(plan.scopeIds.flatMap((id) => deptDescendants(db, id)));
      return ids.has(emp.deptId);
    }
    if (plan.scopeType === "position") return plan.scopeIds.includes(emp.positionId);
    if (plan.scopeType === "employee") return plan.scopeIds.includes(emp.id);
    return false;
  }
  const SPECIFICITY = { all: 0, dept: 1, position: 2, employee: 3 };

  function resolvePlan(db, month, emp, date) {
    const d = Number(date.slice(8, 10));
    const candidates = db.plans.filter(
      (p) =>
        p.companyId === emp.companyId &&
        p.month === month &&
        p.status === "enabled" &&
        d <= daysInMonth(month) &&
        planCovers(db, p, emp),
    );
    candidates.sort((a, b) => SPECIFICITY[b.scopeType] - SPECIFICITY[a.scopeType]);
    return candidates[0] || null;
  }

  function planShiftsForDate(db, plan, date) {
    const d = Number(date.slice(8, 10));
    if (plan.dayOverrides && Object.prototype.hasOwnProperty.call(plan.dayOverrides, d)) {
      return plan.dayOverrides[d].slice();
    }
    return (plan.weekdays[weekdayIndex(date)] || []).slice();
  }

  function buildRoster(db, options = {}) {
    const includePending = options.includePending === true;
    const month = options.month || "2026-09";
    const roster = {};
    for (const emp of db.employees) {
      if (!employedInMonth(emp, month)) continue;
      if (!includePending && (db.pendingEmployees || []).includes(emp.id)) continue;
      const perDate = {};
      for (const date of dateList(month)) {
        if (!employedOn(emp, date)) continue;
        const key = `${emp.id}|${date}`;
        const ex = db.exceptions[key];
        const plan = resolvePlan(db, month, emp, date);
        if (ex) {
          perDate[date] = {
            state: ex.state,
            shifts: ex.state === "work" ? ex.shifts.slice() : [],
            source: "manual",
            planId: plan ? plan.id : null,
            note: ex.note || "",
          };
        } else if (plan) {
          const shifts = planShiftsForDate(db, plan, date);
          perDate[date] = {
            state: shifts.length ? "work" : "rest",
            shifts,
            source: "plan",
            planId: plan.id,
            note: "",
          };
        }
      }
      if (Object.keys(perDate).length) roster[emp.id] = perDate;
    }
    return roster;
  }

  function rebuildRoster(db) {
    db.roster = { "2026-09": buildRoster(db, { month: "2026-09" }) };
    if (db.plans.some((p) => p.month === "2026-10" && p.status === "enabled")) {
      db.roster["2026-10"] = buildRoster(db, { month: "2026-10" });
    } else {
      db.roster["2026-10"] = {};
    }
  }

  function rosterEntry(db, month, empId, date) {
    return (db.roster[month] && db.roster[month][empId] && db.roster[month][empId][date]) || null;
  }

  function shiftSpan(date, shift) {
    return {
      start: atMinutes(date, shift.start),
      end: atMinutes(shift.crossDay ? addDays(date, 1) : date, shift.end),
    };
  }

  function defaultPunchTimes(date, shift) {
    const out = [];
    out.push({ date, time: shift.start });
    const outDate = shift.crossDay ? addDays(date, 1) : date;
    out.push({ date: outDate, time: shift.end });
    if (shift.breakStart) {
      const breakOnNextDay =
        shift.crossDay && toMinutes(shift.breakStart) < toMinutes(shift.start);
      const breakDate = breakOnNextDay ? addDays(date, 1) : date;
      out.push({ date: breakDate, time: shift.breakStart });
      out.push({ date: breakDate, time: shift.breakEnd });
    }
    return out;
  }

  function buildPunches(db) {
    const punches = {};
    const prospective = buildRoster(db, { month: "2026-09" });
    for (const emp of db.employees) {
      const perDate = prospective[emp.id] || {};
      for (const date of Object.keys(perDate)) {
        const key = `${emp.id}|${date}`;
        if (Object.prototype.hasOwnProperty.call(PUNCH_OVERRIDES, key)) {
          punches[key] = clone(PUNCH_OVERRIDES[key]);
          continue;
        }
        const entry = perDate[date];
        if (entry.state !== "work" || !entry.shifts.length) continue;
        const seen = new Set();
        const list = [];
        for (const code of entry.shifts) {
          const shift = getShift(db, code);
          if (!shift) continue;
          const times = defaultPunchTimes(date, shift);
          for (const t of times) {
            const id = `${t.date} ${t.time}`;
            if (seen.has(id)) continue;
            seen.add(id);
            list.push({
              date: t.date,
              time: t.time,
              result: "正常",
              device: "考勤机",
              address: shift.code === "TEC" ? "技术楼" : "一号门",
            });
          }
        }
        list.sort((a, b) => a._abs - b._abs);
        punches[key] = list;
      }
    }
    // Explicit empty overrides must survive even when the employee is pending.
    for (const key of Object.keys(PUNCH_OVERRIDES)) {
      if (!punches[key]) punches[key] = clone(PUNCH_OVERRIDES[key]);
    }
    db.punches = punches;
  }

  function effectiveRules(db, emp, planId) {
    const merged = Object.assign({}, db.rules);
    const override = planId ? db.planRuleOverrides[planId] : null;
    if (override) {
      for (const key of Object.keys(override)) {
        if (override[key] !== null && override[key] !== undefined) merged[key] = override[key];
      }
    }
    return merged;
  }

  function indexPunches(db) {
    const map = {};
    for (const key of Object.keys(db.punches || {})) {
      const list = db.punches[key] || [];
      map[key] = list
        .map((p) => ({
          ...p,
          abs: atMinutes(p.date, p.time),
          timeMinutes: toMinutes(p.time),
        }))
        .sort((a, b) => a.abs - b.abs);
    }
    return map;
  }

  function indexOvertime(db) {
    const map = {};
    for (const req of db.overtime) {
      if (req.result !== "审批通过") continue;
      for (const date of Object.keys(req.days || {})) {
        const key = `${req.employeeId}|${date}`;
        map[key] = (map[key] || 0) + req.days[date];
      }
    }
    for (const key of Object.keys(map)) map[key] = Math.min(480, map[key]);
    return map;
  }

  function tripCoversDate(trip, date) {
    const startDate = trip.start.slice(0, 10);
    const endDate = trip.end.slice(0, 10);
    return date >= startDate && date <= endDate;
  }

  function buildLeaveAllocations(db, month) {
    const alloc = {};
    for (const leave of db.leaves) {
      if (leave.result !== "审批通过") continue;
      const emp = getEmployee(db, leave.employeeId);
      if (!emp) continue;
      const startDate = leave.restStart.slice(0, 10);
      const endDate = leave.restEnd.slice(0, 10);
      const covered = [];
      let cur = startDate;
      let guard = 0;
      while (cur <= endDate && guard < 90) {
        guard += 1;
        if (employedOn(emp, cur)) {
          const m = monthOf(cur);
          const entry =
            (db.roster[m] && db.roster[m][emp.id] && db.roster[m][emp.id][cur]) || null;
          if (entry && entry.state === "work") covered.push(cur);
        }
        cur = addDays(cur, 1);
      }
      const perDay = covered.length ? Math.min(1, leave.days / covered.length) : 0;
      for (const d of covered) {
        if (monthOf(d) !== month) continue;
        const key = `${emp.id}|${d}`;
        const list = alloc[key] || (alloc[key] = []);
        list.push({ kind: leave.kind, days: perDay, approvalNo: leave.approvalNo, leaveId: leave.id });
      }
    }
    return alloc;
  }

  function indexAdjustments(db, month) {
    const map = {};
    for (const adj of db.adjustments) {
      if (adj.status !== "active") continue;
      if (monthOf(adj.date) !== month) continue;
      map[`${adj.employeeId}|${adj.date}`] = adj;
    }
    return map;
  }

  function findNextShiftStart(db, month, empId, date) {
    for (let i = 1; i <= 3; i++) {
      const next = addDays(date, i);
      const m = monthOf(next);
      const entry =
        db.roster[m] && db.roster[m][empId] && db.roster[m][empId][next];
      if (entry && entry.state === "work" && entry.shifts.length) {
        const shift = getShift(db, entry.shifts[0]);
        if (shift) return atMinutes(next, shift.start);
      }
      if (i > 1 && !db.roster[m]) continue;
    }
    return null;
  }

  function matchShift(db, date, shift, punches, nextStartAbs, isLast, rules, leaveDays) {
    const span = shiftSpan(date, shift);
    const inLo = span.start - rules.punch_window_min;
    const inHi = span.start + rules.late_cap_min;
    const outLo = span.end - rules.early_cap_min;
    let outHi = span.end;
    let otCap = 0;
    if (isLast) {
      otCap = rules.ot_max_min;
      if (nextStartAbs !== null) {
        otCap = Math.min(
          otCap,
          (nextStartAbs - span.end) - rules.punch_window_min - 1,
        );
      }
      otCap = Math.max(0, otCap);
      outHi = span.end + otCap;
    }
    const inPunch = punches.find((p) => p.abs >= inLo && p.abs <= inHi) || null;
    let outPunch = null;
    for (const p of punches) {
      if (p.abs >= outLo && p.abs <= outHi) outPunch = p;
    }
    const used = new Set([inPunch?.abs, outPunch?.abs].filter(Boolean));
    const breakPunches = [];
    let breakMissing = 0;
    if (shift.breakStart && shift.breakEnd && rules.break_punch_required) {
      const tol = rules.break_punch_tolerance_min;
      const breakOnNextDay =
        shift.crossDay && toMinutes(shift.breakStart) < toMinutes(shift.start);
      const breakDate = breakOnNextDay ? addDays(date, 1) : date;
      const bStart = atMinutes(breakDate, shift.breakStart);
      const bEnd = atMinutes(breakDate, shift.breakEnd);
      const candidates = punches.filter(
        (p) => p.abs >= bStart - tol && p.abs <= bEnd + tol && !used.has(p.abs),
      );
      const breakOut =
        candidates
          .filter((p) => p.abs <= bStart + tol)
          .sort((a, b) => Math.abs(a.abs - bStart) - Math.abs(b.abs - bStart))[0] || null;
      const breakIn =
        candidates
          .filter((p) => p.abs >= bEnd - tol)
          .sort((a, b) => Math.abs(a.abs - bEnd) - Math.abs(b.abs - bEnd))[0] || null;
      if (breakOut) {
        breakPunches.push(breakOut);
        used.add(breakOut.abs);
      } else breakMissing += 1;
      if (breakIn) {
        breakPunches.push(breakIn);
        used.add(breakIn.abs);
      } else breakMissing += 1;
    }
    const scheduledMinutes = Math.max(0, (span.end - span.start) - shift.restMinutes);
    let workedMinutes = 0;
    if (inPunch && outPunch) {
      const cappedOut = Math.min(outPunch.abs, span.end);
      workedMinutes = Math.max(
        0,
        (cappedOut - inPunch.abs) - shift.restMinutes,
      );
      workedMinutes = Math.max(0, Math.round(workedMinutes * (1 - leaveDays)));
    }
    const lateMinutes =
      inPunch && !leaveDays
        ? Math.max(0, (inPunch.abs - span.start) - rules.late_grace_min)
        : 0;
    const earlyMinutes =
      outPunch && !leaveDays
        ? Math.max(0, (span.end - outPunch.abs) - rules.early_grace_min)
        : 0;
    let missingPunchCount = 0;
    if (!inPunch) missingPunchCount += 1;
    if (!outPunch) missingPunchCount += 1;
    missingPunchCount += breakMissing;
    let otMinutes = 0;
    if (isLast && outPunch && !leaveDays) {
      const after = outPunch.abs - span.end;
      if (after >= rules.ot_threshold_min) otMinutes = Math.min(after, otCap);
    }
    return {
      shift,
      seq: 0,
      span,
      inPunch,
      outPunch,
      breakPunches,
      scheduledMinutes,
      workedMinutes,
      lateMinutes,
      earlyMinutes,
      missingPunchCount,
      otMinutes,
      hasEvidence: !!(inPunch || outPunch),
    };
  }

  function deductionsFor(rules, status, lateCount, earlyCount, missingCount) {
    const absent = status === "absent" ? rules.absent_deduct_per_day : 0;
    const late = lateCount * rules.late_deduct_per_occurrence;
    const early = earlyCount * rules.early_deduct_per_occurrence;
    const missing = missingCount * rules.missing_punch_deduct_per_occurrence;
    return {
      absent: -round2(absent),
      late: -round2(late),
      early: -round2(early),
      missing: -round2(missing),
      total: -round2(absent + late + early + missing),
    };
  }

  function leaveStatusFor(kind) {
    if (kind === "paid") return "paid_leave";
    if (kind === "comp") return "comp_leave";
    return "personal_leave";
  }

  function evaluateDay(db, month, emp, date, ctx) {
    const entry = rosterEntry(db, month, emp.id, date);
    const punches = ctx.punches[`${emp.id}|${date}`] || [];
    const key = `${emp.id}|${date}`;
    const leaveList = ctx.leaves[key] || [];
    const leaveDays = Math.min(1, leaveList.reduce((sum, l) => sum + l.days, 0));
    const leaveKind =
      leaveList.find((l) => l.kind === "paid")?.kind ||
      leaveList.find((l) => l.kind === "comp")?.kind ||
      leaveList.find((l) => l.kind === "unpaid")?.kind ||
      null;
    const trip = ctx.trips.find((t) => t.employeeId === emp.id && tripCoversDate(t, date)) || null;
    const oaOtMinutes = ctx.overtime[key] || 0;
    if (!entry && !punches.length && !trip && !oaOtMinutes && !leaveList.length) return null;

    const rules = effectiveRules(db, emp, entry ? entry.planId : null);
    const dt = dayType(db, date);
    const rosterState = entry ? entry.state : "unscheduled";
    const shifts = entry && entry.state === "work"
      ? entry.shifts.map((code) => getShift(db, code)).filter(Boolean)
      : [];
    const nextStartAbs = shifts.length
      ? findNextShiftStart(db, month, emp.id, date)
      : null;

    const shiftResults = [];
    let lateCount = 0;
    let lateMinutes = 0;
    let earlyCount = 0;
    let earlyMinutes = 0;
    let missingPunchCount = 0;
    let workedMinutes = 0;
    let scheduledMinutes = 0;
    let punchOtMinutes = 0;
    shifts.forEach((shift, index) => {
      const sr = matchShift(db, date, shift, punches, nextStartAbs, index === shifts.length - 1, rules, leaveDays);
      sr.seq = index;
      shiftResults.push(sr);
      lateMinutes += sr.lateMinutes;
      earlyMinutes += sr.earlyMinutes;
      if (sr.lateMinutes > 0) lateCount += 1;
      if (sr.earlyMinutes > 0) earlyCount += 1;
      missingPunchCount += sr.missingPunchCount;
      workedMinutes += sr.workedMinutes;
      scheduledMinutes += sr.scheduledMinutes;
      punchOtMinutes += sr.otMinutes;
    });

    let dayStatus = "normal";
    let attendanceFraction = 0;
    let dayFlags = [];
    let tripKind = null;
    let tripFraction = 0;
    let paidLeaveDays = 0;
    let unpaidLeaveDays = 0;
    let compLeaveDays = 0;
    for (const l of leaveList) {
      if (l.kind === "paid") paidLeaveDays += l.days;
      else if (l.kind === "comp") compLeaveDays += l.days;
      else unpaidLeaveDays += l.days;
    }
    if (leaveList.length > 1) dayFlags.push("multiple_leave_requests");

    const hasAnyPunch = punches.length > 0;
    const shiftHasEvidence = shiftResults.some((sr) => sr.hasEvidence);

    if (rosterState === "work") {
      if (leaveDays >= 1) {
        dayStatus = leaveStatusFor(leaveKind);
        attendanceFraction = 0;
        if (hasAnyPunch) dayFlags.push("punch_during_leave");
        dayFlags.push("leave");
        lateCount = lateMinutes = earlyCount = earlyMinutes = missingPunchCount = 0;
        workedMinutes = 0;
        for (const sr of shiftResults) sr.workedMinutes = 0;
      } else if (shiftHasEvidence || hasAnyPunch) {
        const credit = shiftResults.reduce(
          (sum, sr) => sum + (sr.hasEvidence ? sr.scheduledMinutes : 0),
          0,
        );
        const denom = shiftResults.reduce((sum, sr) => sum + sr.scheduledMinutes, 0);
        attendanceFraction = round1((denom ? credit / denom : 1) * (1 - leaveDays));
        if (missingPunchCount > 0) dayStatus = "missing_punch";
        else if (lateMinutes > 0) dayStatus = "late";
        else if (earlyMinutes > 0) dayStatus = "early";
        else dayStatus = "normal";
        if (lateMinutes > 0) dayFlags.push("late");
        if (earlyMinutes > 0) dayFlags.push("early");
        if (missingPunchCount > 0) dayFlags.push("missing_punch");
        if (shiftResults.some((sr) => sr.missingPunchCount > 0 && sr.breakPunches.length < 2 && sr.shift.breakStart)) {
          dayFlags.push("break_punch_missing");
        }
        if (leaveDays > 0) dayFlags.push("leave");
        if (trip) {
          tripKind = trip.kind;
          dayFlags.push("trip");
        }
      } else if (trip) {
        const totalSpan = shiftResults.reduce((sum, sr) => sum + (sr.span.end - sr.span.start), 0);
        const overlap = shiftResults.reduce((sum, sr) => {
          const tStart = atMinutes(trip.start.slice(0, 10), trip.start.slice(11, 16));
          const tEnd = atMinutes(trip.end.slice(0, 10), trip.end.slice(11, 16));
          return sum + overlaps(tStart, tEnd, sr.span.start, sr.span.end);
        }, 0);
        tripKind = trip.kind;
        tripFraction = totalSpan ? Math.min(1, overlap / totalSpan) : 0;
        attendanceFraction = round1(tripFraction * (1 - leaveDays));
        workedMinutes = Math.round(scheduledMinutes * tripFraction * (1 - leaveDays));
        dayStatus = trip.kind === "business" ? "trip_business" : "trip_out";
        dayFlags.push("trip");
        missingPunchCount = 0;
        lateCount = lateMinutes = earlyCount = earlyMinutes = 0;
      } else if (oaOtMinutes > 0) {
        dayStatus = "overtime";
        attendanceFraction = 1;
        workedMinutes = 0;
        dayFlags.push("overtime", "oa_ot_only");
        missingPunchCount = 0;
        lateCount = lateMinutes = earlyCount = earlyMinutes = 0;
      } else if (leaveDays > 0) {
        dayStatus = "missing_punch";
        attendanceFraction = 0;
        missingPunchCount = shifts.length * 2;
        lateCount = lateMinutes = earlyCount = earlyMinutes = 0;
        dayFlags.push("missing_punch", "leave");
      } else if (rules.absent_if_no_punch) {
        dayStatus = "absent";
        attendanceFraction = 0;
        missingPunchCount = 0;
        lateCount = lateMinutes = earlyCount = earlyMinutes = 0;
        dayFlags.push("absent", "no_valid_punch");
      } else {
        dayStatus = "missing_punch";
        attendanceFraction = 0;
        missingPunchCount = shifts.length * 2;
        lateCount = lateMinutes = earlyCount = earlyMinutes = 0;
        dayFlags.push("missing_punch");
      }
    } else {
      // rest / unscheduled
      if (hasAnyPunch) {
        dayStatus = "unscheduled_attendance";
        attendanceFraction = 1;
        dayFlags.push("unscheduled_attendance");
      } else if (oaOtMinutes > 0) {
        dayStatus = "overtime";
        attendanceFraction = 0;
        dayFlags.push("overtime", "oa_ot_only");
      } else if (trip) {
        dayStatus = "rest";
        tripKind = trip.kind;
        tripFraction = 0;
        dayFlags.push("trip");
      } else if (leaveList.length) {
        dayStatus = "rest";
        dayFlags.push("leave", "leave_on_non_workday");
      } else {
        dayStatus = "rest";
      }
    }

    if (trip && leaveList.length && tripKind) dayFlags.push("leave_trip_conflict");
    if (oaOtMinutes > 0 && leaveDays >= 1 && dayStatus !== "overtime") {
      dayFlags.push("leave_ot_conflict");
    }
    if (trip && !shiftResults.length && rosterState === "work") dayFlags.push("trip");

    const oaOt = Math.min(480, oaOtMinutes);
    let dayOtRaw;
    if (rosterState === "work") {
      dayOtRaw = Math.min(rules.ot_max_min, Math.max(punchOtMinutes, oaOt));
    } else {
      dayOtRaw = Math.min(rules.ot_max_min, oaOt);
    }
    let compOffset = 0;
    for (const leave of db.leaves) {
      if (leave.result !== "审批通过") continue;
      if (leave.employeeId !== emp.id) continue;
      if (leave.kind !== "comp") continue;
      if (!leave.workStart) continue;
      if (leave.workStart.slice(0, 10) !== date) continue;
      compOffset += leave.days * 480;
    }
    const appliedComp = Math.min(dayOtRaw, compOffset);
    const dayOtNet = dayOtRaw - appliedComp;
    if (compOffset > 0 && appliedComp === 0) dayFlags.push("comp_offset_no_ot");
    if (compOffset > appliedComp) dayFlags.push("comp_offset_unused");
    if (dayOtNet > 0) dayFlags.push("overtime");

    let otBucket = null;
    if (dt === "holiday") otBucket = "holiday";
    else if (dt === "workday" && rosterState === "work") otBucket = "weekday";
    else otBucket = "weekend";
    const ot = {
      otWeekdayMinutes: otBucket === "weekday" ? dayOtNet : 0,
      otWeekendMinutes: otBucket === "weekend" ? dayOtNet : 0,
      otHolidayMinutes: otBucket === "holiday" ? dayOtNet : 0,
    };
    if (dayStatus === "overtime" && oaOt > 0 && !shiftHasEvidence) {
      // OA-only overtime keeps the same bucket; status already set.
    }

    const deduct = deductionsFor(rules, dayStatus, lateCount, earlyCount, missingPunchCount);
    const flags = Array.from(new Set(dayFlags));
    return {
      employeeId: emp.id,
      date,
      dayType: dt,
      dayTypeLabel: dayTypeLabel(db, date),
      rosterState,
      rosterStateLabel: rosterState === "work" ? "上班" : rosterState === "rest" ? "休息" : "未排班",
      source: entry ? entry.source : "none",
      planId: entry ? entry.planId : null,
      shifts: entry ? entry.shifts.slice() : [],
      dayStatus,
      dayFlags: flags,
      attendanceFraction,
      scheduledMinutes,
      workedMinutes,
      lateMinutes,
      earlyMinutes,
      lateCount,
      earlyCount,
      missingPunchCount,
      leaveKind,
      leaveDays: round1(leaveDays),
      paidLeaveDays: round1(paidLeaveDays),
      unpaidLeaveDays: round1(unpaidLeaveDays),
      compLeaveDays: round1(compLeaveDays),
      tripKind,
      tripFraction: round1(tripFraction),
      otWeekdayMinutes: ot.otWeekdayMinutes,
      otWeekendMinutes: ot.otWeekendMinutes,
      otHolidayMinutes: ot.otHolidayMinutes,
      compOffsetMinutes: appliedComp,
      compOffsetUnusedMinutes: Math.max(0, compOffset - appliedComp),
      absentDeductAmount: deduct.absent,
      lateDeductAmount: deduct.late,
      earlyDeductAmount: deduct.early,
      missingPunchDeductAmount: deduct.missing,
      deductionTotal: deduct.total,
      isAdjusted: false,
      adjustmentId: null,
      note: entry ? entry.note : "",
      shiftResults,
      punches,
      trips: trip ? [trip] : [],
      leaves: leaveList,
      oaOtMinutes: oaOt,
      rules,
    };
  }

  function applyAdjustments(db, month, results) {
    const adjustments = indexAdjustments(db, month);
    for (const key of Object.keys(adjustments)) {
      const adj = adjustments[key];
      const r = results.find(
        (item) => item.employeeId === adj.employeeId && item.date === adj.date,
      );
      if (!r) continue;
      const values = adj.adjustedValues || {};
      r.isAdjusted = true;
      r.adjustmentId = adj.id;
      if (values.dayStatus) r.dayStatus = values.dayStatus;
      if (values.attendanceFraction !== undefined) r.attendanceFraction = values.attendanceFraction;
      if (values.workedMinutes !== undefined) r.workedMinutes = values.workedMinutes;
      if (values.otWeekdayMinutes !== undefined) r.otWeekdayMinutes = values.otWeekdayMinutes;
      if (values.otWeekendMinutes !== undefined) r.otWeekendMinutes = values.otWeekendMinutes;
      if (values.otHolidayMinutes !== undefined) r.otHolidayMinutes = values.otHolidayMinutes;
      if (values.lateMinutes !== undefined) r.lateMinutes = values.lateMinutes;
      if (values.lateCount !== undefined) r.lateCount = values.lateCount;
      if (values.earlyMinutes !== undefined) r.earlyMinutes = values.earlyMinutes;
      if (values.earlyCount !== undefined) r.earlyCount = values.earlyCount;
      if (values.missingPunchCount !== undefined) r.missingPunchCount = values.missingPunchCount;
      if (values.leaveDays !== undefined) r.leaveDays = values.leaveDays;
      if (values.note !== undefined) r.note = values.note;
      const deduct = deductionsFor(
        r.rules,
        r.dayStatus,
        r.lateCount,
        r.earlyCount,
        r.missingPunchCount,
      );
      r.absentDeductAmount = deduct.absent;
      r.lateDeductAmount = deduct.late;
      r.earlyDeductAmount = deduct.early;
      r.missingPunchDeductAmount = deduct.missing;
      r.deductionTotal = deduct.total;
      let flags = r.dayFlags.filter(
        (f) => !["late", "early", "missing_punch", "absent", "manual_adjustment"].includes(f),
      );
      if (r.dayStatus === "absent") flags.push("absent");
      if (r.lateMinutes > 0) flags.push("late");
      if (r.earlyMinutes > 0) flags.push("early");
      if (r.missingPunchCount > 0) flags.push("missing_punch");
      flags.push("manual_adjustment");
      r.dayFlags = Array.from(new Set(flags));
    }
  }

  function buildSummaries(db, month, results) {
    const byEmp = {};
    for (const r of results) {
      if (!byEmp[r.employeeId]) byEmp[r.employeeId] = [];
      byEmp[r.employeeId].push(r);
    }
    const summaries = [];
    for (const empId of Object.keys(byEmp)) {
      const rows = byEmp[empId];
      const emp = getEmployee(db, empId);
      if (!emp) continue;
      const s = {
        employeeId: empId,
        employeeNo: emp.no,
        employeeName: emp.name,
        deptName: deptPath(db, emp.deptId),
        weekdayFull: 0,
        weekendFull: 0,
        weekdayAttended: 0,
        weekendAttended: 0,
        paidLeaveDays: 0,
        unpaidLeaveDays: 0,
        compLeaveDays: 0,
        tripDays: 0,
        otWeekdayMinutes: 0,
        otWeekendMinutes: 0,
        otHolidayMinutes: 0,
        compLeaveUsedHours: 0,
        compOffsetUnusedMinutes: 0,
        lateCount: 0,
        lateMinutes: 0,
        earlyCount: 0,
        earlyMinutes: 0,
        missingPunchCount: 0,
        absentDays: 0,
        workedMinutes: 0,
        attendanceDeduct: 0,
        isAdjusted: false,
        days: rows.length,
      };
      for (const r of rows) {
        if (r.rosterState === "work" && r.dayType === "workday") s.weekdayFull += 1;
        if (r.rosterState === "work" && r.dayType === "weekend") s.weekendFull += 1;
        if (r.dayType === "workday") s.weekdayAttended += r.attendanceFraction;
        if (r.dayType === "weekend") s.weekendAttended += r.attendanceFraction;
        if (r.rosterState === "work") {
          s.paidLeaveDays += r.paidLeaveDays;
          s.unpaidLeaveDays += r.unpaidLeaveDays;
          s.compLeaveDays += r.compLeaveDays;
          s.tripDays += r.tripFraction;
        }
        s.otWeekdayMinutes += r.otWeekdayMinutes;
        s.otWeekendMinutes += r.otWeekendMinutes;
        s.otHolidayMinutes += r.otHolidayMinutes;
        s.compLeaveUsedHours += r.compOffsetMinutes / 60;
        s.compOffsetUnusedMinutes += r.compOffsetUnusedMinutes;
        s.lateCount += r.lateCount;
        s.lateMinutes += r.lateMinutes;
        s.earlyCount += r.earlyCount;
        s.earlyMinutes += r.earlyMinutes;
        s.missingPunchCount += r.missingPunchCount;
        if (r.dayStatus === "absent") s.absentDays += 1;
        s.workedMinutes += r.workedMinutes;
        s.attendanceDeduct += r.deductionTotal;
        if (r.isAdjusted) s.isAdjusted = true;
      }
      s.weekdayFull = round1(s.weekdayFull);
      s.weekendFull = round1(s.weekendFull);
      s.weekdayAttended = round1(s.weekdayAttended);
      s.weekendAttended = round1(s.weekendAttended);
      s.paidLeaveDays = round1(s.paidLeaveDays);
      s.unpaidLeaveDays = round1(s.unpaidLeaveDays);
      s.compLeaveDays = round1(s.compLeaveDays);
      s.tripDays = round1(s.tripDays);
      s.otWeekdayHours = round2(s.otWeekdayMinutes / 60);
      s.otWeekendHours = round2(s.otWeekendMinutes / 60);
      s.otHolidayHours = round2(s.otHolidayMinutes / 60);
      s.compLeaveUsedHours = round2(s.compLeaveUsedHours);
      s.attendanceDeduct = round2(s.attendanceDeduct);
      summaries.push(s);
    }
    summaries.sort((a, b) => a.employeeNo.localeCompare(b.employeeNo));
    return summaries;
  }

  function recalculate(db, month) {
    if (month !== "2026-09" && !(db.punches && Object.keys(db.punches).length)) {
      return { results: [], summaries: [] };
    }
    const employees = db.employees.filter((e) => e.companyId === "c1" && employedInMonth(e, month));
    const ctx = {
      punches: indexPunches(db),
      leaves: buildLeaveAllocations(db, month),
      overtime: indexOvertime(db),
      trips: db.trips.filter((t) => t.result === "审批通过"),
    };
    const results = [];
    for (const emp of employees) {
      for (const date of dateList(month)) {
        if (!employedOn(emp, date)) continue;
        const r = evaluateDay(db, month, emp, date, ctx);
        if (r) results.push(r);
      }
    }
    results.sort((a, b) => (a.date === b.date ? a.employeeId.localeCompare(b.employeeId) : a.date.localeCompare(b.date)));
    applyAdjustments(db, month, results);
    const summaries = buildSummaries(db, month, results);
    return { results, summaries };
  }

  /* ---------------------------------------------------------------- summary helpers */

  function monthStats(db, month) {
    const roster = db.roster[month] || {};
    let personDays = 0;
    let workDays = 0;
    let restDays = 0;
    let manual = 0;
    for (const empId of Object.keys(roster)) {
      for (const date of Object.keys(roster[empId])) {
        const entry = roster[empId][date];
        personDays += 1;
        if (entry.state === "work") workDays += 1;
        else restDays += 1;
        if (entry.source === "manual") manual += 1;
      }
    }
    const employees = db.employees.filter(
      (e) => e.companyId === "c1" && employedInMonth(e, month) && e.status !== "resigned",
    );
    let unscheduled = 0;
    for (const emp of employees) {
      for (const date of dateList(month)) {
        if (!employedOn(emp, date)) continue;
        if (!rosterEntry(db, month, emp.id, date)) unscheduled += 1;
      }
    }
    return { employees: employees.length, personDays, workDays, restDays, manual, unscheduled };
  }

  function conflicts(db, month) {
    const out = [];
    const roster = db.roster[month] || {};
    for (const empId of Object.keys(roster)) {
      for (const date of Object.keys(roster[empId])) {
        const entry = roster[empId][date];
        if (entry.state !== "work" || entry.shifts.length < 2) continue;
        const spans = entry.shifts
          .map((code) => ({ code, shift: getShift(db, code) }))
          .filter((x) => x.shift)
          .map((x) => ({ code: x.code, ...shiftSpan(date, x.shift) }));
        for (let i = 0; i < spans.length; i++) {
          for (let j = i + 1; j < spans.length; j++) {
            if (overlaps(spans[i].start, spans[i].end, spans[j].start, spans[j].end) > 0) {
              out.push({ employeeId: empId, date, a: spans[i].code, b: spans[j].code });
            }
          }
        }
      }
    }
    return out;
  }

  function planCoverage(db, month, planId) {
    const roster = db.roster[month] || {};
    const set = new Set();
    for (const empId of Object.keys(roster)) {
      for (const date of Object.keys(roster[empId])) {
        if (roster[empId][date].source === "plan" && roster[empId][date].planId === planId) {
          set.add(empId);
        }
      }
    }
    return set.size;
  }

  function createDb() {
    const db = {
      companies: clone(COMPANIES),
      departments: clone(DEPARTMENTS),
      positions: clone(POSITIONS),
      employees: clone(EMPLOYEES).map((e) => ({ ...e, companyId: "c1" })),
      shifts: clone(SHIFTS),
      plans: clone(PLANS),
      planRuleOverrides: clone(PLAN_RULE_OVERRIDES),
      rules: clone(RULES),
      holidays: clone(HOLIDAYS),
      exceptions: clone(MANUAL_EXCEPTIONS),
      trips: clone(TRIPS),
      overtime: clone(OVERTIME),
      leaves: clone(LEAVES),
      adjustments: clone(ADJUSTMENTS),
      importBatches: clone(IMPORT_BATCHES),
      importSamples: clone(IMPORT_SAMPLES),
      pendingEmployees: ["E113"],
      months: {
        "2026-09": {
          status: "calculated",
          isStale: false,
          calculatedAt: "2026-09-30 18:05",
          confirmedAt: null,
          lockedAt: null,
          unlockReason: null,
        },
        "2026-10": {
          status: "draft",
          isStale: true,
          calculatedAt: null,
          confirmedAt: null,
          lockedAt: null,
          unlockReason: null,
        },
      },
      calcRuns: {
        "2026-09": [
          { id: "calc-1", trigger: "initial", status: "success", startedAt: "2026-09-30 17:18", finishedAt: "2026-09-30 17:19", employees: 12, days: 246, note: "首次计算" },
          { id: "calc-2", trigger: "manual", status: "success", startedAt: "2026-09-30 18:04", finishedAt: "2026-09-30 18:05", employees: 12, days: 246, note: "人工重算：确认导入批次" },
          { id: "calc-3", trigger: "rule_change", status: "failed", startedAt: "2026-09-30 18:12", finishedAt: "2026-09-30 18:12", employees: 0, days: 0, note: "规则校验失败：迟到宽限不能大于最晚归属" },
        ],
        "2026-10": [],
      },
      snapshots: { "2026-09": [], "2026-10": [] },
      roster: {},
      results: {},
      summaries: {},
    };
    db.punches = {};
    rebuildRoster(db);
    buildPunches(db);
    const sep = recalculate(db, "2026-09");
    db.results["2026-09"] = sep.results;
    db.summaries["2026-09"] = sep.summaries;
    db.results["2026-10"] = [];
    db.summaries["2026-10"] = [];
    return db;
  }

  window.AttendanceData = {
    createDb,
    recalculate,
    rebuildRoster,
    buildRoster,
    buildPunches,
    rosterEntry,
    effectiveRules,
    monthStats,
    conflicts,
    planCoverage,
    resolvePlan,
    planShiftsForDate,
    planCovers,
    getDept,
    deptDescendants,
    deptPath,
    getEmployee,
    getShift,
    getPlan,
    employedOn,
    employedInMonth,
    holidayOf,
    dayType,
    dayTypeLabel,
    dateList,
    daysInMonth,
    weekdayIndex,
    monthOf,
    addDays,
    toMinutes,
    atMinutes,
    shiftSpan,
    round1,
    round2,
    clone,
  };
})();
