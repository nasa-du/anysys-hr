import type { ReactNode } from "react"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { type AttendanceImportDataType, LEAVE_KIND_LABELS } from "@/lib/enums"
import { overtimeDaysText, sampleDateTime, sampleText } from "./import-format"

type SampleRow = Record<string, unknown>

type SampleColumn = {
  label: string
  render: (row: SampleRow) => ReactNode
}

const SAMPLE_COLUMNS: Record<AttendanceImportDataType, SampleColumn[]> = {
  punch: [
    { label: "行", render: (row) => sampleText(row, "source_row_number") },
    { label: "工号", render: (row) => sampleText(row, "employee_no") },
    { label: "姓名", render: (row) => sampleText(row, "employee_name") },
    { label: "考勤日期", render: (row) => sampleText(row, "attendance_date") },
    { label: "打卡时间", render: (row) => sampleDateTime(row.punch_time) },
    { label: "结果", render: (row) => sampleText(row, "punch_result") },
  ],
  trip: [
    { label: "行", render: (row) => sampleText(row, "source_row_number") },
    { label: "拆分", render: (row) => sampleText(row, "split_index") },
    { label: "姓名", render: (row) => sampleText(row, "employee_name") },
    { label: "审批编号", render: (row) => sampleText(row, "approval_no") },
    { label: "开始", render: (row) => sampleDateTime(row.start_at) },
    { label: "结束", render: (row) => sampleDateTime(row.end_at) },
  ],
  ot: [
    { label: "行", render: (row) => sampleText(row, "source_row_number") },
    { label: "姓名", render: (row) => sampleText(row, "employee_name") },
    { label: "审批编号", render: (row) => sampleText(row, "approval_no") },
    { label: "开始", render: (row) => sampleDateTime(row.start_at) },
    { label: "结束", render: (row) => sampleDateTime(row.end_at) },
    { label: "按日分钟", render: (row) => overtimeDaysText(row.days) },
  ],
  leave: [
    { label: "行", render: (row) => sampleText(row, "source_row_number") },
    { label: "姓名", render: (row) => sampleText(row, "employee_name") },
    { label: "审批编号", render: (row) => sampleText(row, "approval_no") },
    { label: "类型", render: (row) => sampleText(row, "leave_type") },
    {
      label: "归类",
      render: (row) => {
        const kind = row.leave_kind
        return typeof kind === "string" && kind in LEAVE_KIND_LABELS
          ? LEAVE_KIND_LABELS[kind as keyof typeof LEAVE_KIND_LABELS]
          : sampleText(row, "leave_kind")
      },
    },
    { label: "天数", render: (row) => sampleText(row, "days") },
    { label: "休息开始", render: (row) => sampleDateTime(row.rest_start_at) },
    { label: "休息结束", render: (row) => sampleDateTime(row.rest_end_at) },
  ],
}

export function SampleTable({
  dataType,
  samples,
}: {
  dataType: AttendanceImportDataType
  samples: SampleRow[]
}) {
  if (samples.length === 0) {
    return <p className="text-sm text-muted-foreground">没有有效记录样例。</p>
  }
  const columns = SAMPLE_COLUMNS[dataType]
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead key={column.label}>{column.label}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {samples.map((sample, index) => (
            <TableRow key={`${String(sample.source_row_number)}-${index}`}>
              {columns.map((column) => (
                <TableCell key={column.label}>
                  {column.render(sample)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
