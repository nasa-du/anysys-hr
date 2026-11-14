import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  ChevronLeft,
  ChevronRight,
  Copy,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { AttendanceHolidaysService, type HolidayPublic } from "@/client"
import {
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage } from "@/lib/api-error"
import { HOLIDAY_DAY_TYPE_LABELS } from "@/lib/enums"
import { HolidayCopyDialog } from "./HolidayCopyDialog"
import { HolidayFormDialog } from "./HolidayFormDialog"
import { holidaysQueryKey, invalidateRuleHolidayQueries } from "./queries"

const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"]

function shiftMonth(month: string, delta: number): string {
  const year = Number(month.slice(0, 4))
  const monthIndex = Number(month.slice(5, 7)) - 1 + delta
  const date = new Date(year, monthIndex, 1)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`
}

function monthLabel(month: string): string {
  return `${month.slice(0, 4)} 年 ${Number(month.slice(5, 7))} 月`
}

function calendarCells(month: string): Array<number | null> {
  const year = Number(month.slice(0, 4))
  const monthNumber = Number(month.slice(5, 7))
  const days = new Date(year, monthNumber, 0).getDate()
  const firstWeekday = new Date(year, monthNumber - 1, 1).getDay()
  return [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: days }, (_, index) => index + 1),
  ]
}

export function HolidayCalendar({
  companyId,
  month,
}: {
  companyId: string
  month: string
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [holidayMonth, setHolidayMonth] = useState(month)
  const [formOpen, setFormOpen] = useState(false)
  const [editingHoliday, setEditingHoliday] = useState<HolidayPublic | null>(
    null,
  )
  const [defaultDate, setDefaultDate] = useState(`${month}-01`)
  const [deletingHoliday, setDeletingHoliday] = useState<HolidayPublic | null>(
    null,
  )
  const [copyOpen, setCopyOpen] = useState(false)

  useEffect(() => {
    setHolidayMonth(month)
  }, [month])

  const holidayYear = Number(holidayMonth.slice(0, 4))

  const holidaysQuery = useQuery({
    queryKey: holidaysQueryKey(companyId, holidayYear),
    queryFn: async () => {
      const response = await AttendanceHolidaysService.readHolidays({
        query: {
          company_id: companyId,
          year: holidayYear,
          skip: 0,
          limit: 500,
        },
      })
      return response.data
    },
  })

  const holidays = holidaysQuery.data?.data ?? []
  const holidaysByDate = useMemo(
    () => new Map(holidays.map((holiday) => [holiday.date, holiday])),
    [holidays],
  )
  const monthHolidays = holidays.filter((holiday) =>
    holiday.date.startsWith(holidayMonth),
  )

  const deleteMutation = useMutation({
    mutationFn: async (holidayId: string) =>
      AttendanceHolidaysService.deleteHoliday({
        path: { holiday_id: holidayId },
      }),
    onSuccess: () => {
      showSuccessToast("节假日删除成功")
      setDeletingHoliday(null)
      invalidateRuleHolidayQueries(queryClient)
    },
    onError: (error) => {
      showErrorToast(getErrorMessage(error))
    },
  })

  const openCreate = (date: string) => {
    setEditingHoliday(null)
    setDefaultDate(date)
    setFormOpen(true)
  }

  const openDay = (date: string) => {
    const holiday = holidaysByDate.get(date)
    if (holiday) {
      openEdit(holiday)
    } else {
      openCreate(date)
    }
  }

  const openEdit = (holiday: HolidayPublic) => {
    setEditingHoliday(holiday)
    setDefaultDate(holiday.date)
    setFormOpen(true)
  }

  const cells = calendarCells(holidayMonth)

  return (
    <Card data-testid="holiday-calendar">
      <CardHeader className="border-b">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg">节假日日历</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              公司级维护；调休上班优先于周末，法定节假日优先于周末。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setEditingHoliday(null)
                setDefaultDate(`${holidayMonth}-01`)
                setFormOpen(true)
              }}
            >
              <Plus className="mr-1 size-4" />
              添加节假日
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setCopyOpen(true)}
            >
              <Copy className="mr-1 size-4" />
              复制上一年
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-6">
        <div className="flex items-center justify-between">
          <Button
            size="sm"
            variant="ghost"
            aria-label="上一个月"
            onClick={() => setHolidayMonth((value) => shiftMonth(value, -1))}
          >
            <ChevronLeft className="size-4" />
          </Button>
          <span className="text-sm font-medium">
            {monthLabel(holidayMonth)}
          </span>
          <Button
            size="sm"
            variant="ghost"
            aria-label="下一个月"
            onClick={() => setHolidayMonth((value) => shiftMonth(value, 1))}
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>

        {holidaysQuery.isLoading ? (
          <LoadingState rows={5} />
        ) : holidaysQuery.isError ? (
          <ErrorState
            message={getErrorMessage(holidaysQuery.error)}
            onRetry={() => {
              void holidaysQuery.refetch()
            }}
          />
        ) : (
          <>
            <div className="grid grid-cols-7 gap-1 text-center text-xs text-muted-foreground">
              {WEEKDAYS.map((weekday) => (
                <div key={weekday} className="py-1">
                  {weekday}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {cells.map((day, index) => {
                if (day === null) {
                  return <div key={`blank-${index}`} />
                }
                const date = `${holidayMonth}-${String(day).padStart(2, "0")}`
                const holiday = holidaysByDate.get(date)
                const className = holiday
                  ? holiday.day_type === "holiday"
                    ? "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-100"
                    : "border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-100"
                  : "hover:bg-muted/60"
                return (
                  <button
                    key={date}
                    type="button"
                    onClick={() => openDay(date)}
                    aria-label={
                      holiday ? `${date} ${holiday.name}` : `${date} 添加节假日`
                    }
                    className={`flex min-h-12 flex-col items-center justify-start rounded-md border border-transparent p-1 text-xs transition-colors ${className}`}
                  >
                    <span className="font-medium">{day}</span>
                    {holiday && (
                      <span className="line-clamp-1 max-w-full opacity-80">
                        {holiday.name}
                      </span>
                    )}
                  </button>
                )
              })}
            </div>

            <div className="space-y-2">
              <h3 className="text-sm font-semibold">
                {monthLabel(holidayMonth)}的节假日
              </h3>
              {monthHolidays.length === 0 ? (
                <p
                  className="rounded-md border border-dashed px-3 py-6 text-center text-sm text-muted-foreground"
                  data-testid="holiday-empty"
                >
                  本月没有节假日；周末按常规处理。
                </p>
              ) : (
                <div className="divide-y rounded-lg border">
                  {monthHolidays.map((holiday) => (
                    <div
                      key={holiday.id}
                      className="flex flex-wrap items-center gap-2 px-3 py-2"
                    >
                      <span className="w-14 font-mono text-sm">
                        {holiday.date.slice(5)}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-medium">
                          {holiday.name}
                        </div>
                        {holiday.note && (
                          <div className="truncate text-xs text-muted-foreground">
                            {holiday.note}
                          </div>
                        )}
                      </div>
                      <Badge
                        variant={
                          holiday.day_type === "holiday"
                            ? "destructive"
                            : "default"
                        }
                      >
                        {HOLIDAY_DAY_TYPE_LABELS[holiday.day_type]}
                      </Badge>
                      <Button
                        size="sm"
                        variant="ghost"
                        aria-label={`编辑 ${holiday.name}`}
                        onClick={() => openEdit(holiday)}
                      >
                        <Pencil className="size-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive"
                        aria-label={`删除 ${holiday.name}`}
                        onClick={() => setDeletingHoliday(holiday)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>

      <HolidayFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        companyId={companyId}
        holiday={editingHoliday}
        defaultDate={defaultDate}
      />
      <HolidayCopyDialog
        open={copyOpen}
        onOpenChange={setCopyOpen}
        companyId={companyId}
        targetYear={holidayYear}
      />

      <Dialog
        open={deletingHoliday !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingHoliday(null)
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>删除节假日</DialogTitle>
            <DialogDescription>
              确认删除 {deletingHoliday?.date} 的「{deletingHoliday?.name}
              」？草稿与已计算月份会标记为过期，已确认/锁定月份的结果不变。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              disabled={deleteMutation.isPending}
              onClick={() => setDeletingHoliday(null)}
            >
              取消
            </Button>
            <LoadingButton
              variant="destructive"
              loading={deleteMutation.isPending}
              onClick={() => {
                if (deletingHoliday) deleteMutation.mutate(deletingHoliday.id)
              }}
            >
              删除
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
