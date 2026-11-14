import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"

import { AttendanceHolidaysService } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { Skeleton } from "@/components/ui/skeleton"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorDetail, getErrorMessage } from "@/lib/api-error"
import { invalidateRuleHolidayQueries } from "./queries"

interface HolidayCopyDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  companyId: string
  targetYear: number
}

export function HolidayCopyDialog({
  open,
  onOpenChange,
  companyId,
  targetYear,
}: HolidayCopyDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [sourceYear, setSourceYear] = useState(targetYear - 1)
  const [overwrite, setOverwrite] = useState(false)
  const [conflictMessage, setConflictMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setSourceYear(targetYear - 1)
    setOverwrite(false)
    setConflictMessage(null)
  }, [open, targetYear])

  const previewQuery = useQuery({
    queryKey: [
      "attendance",
      "holidays",
      "copy-preview",
      companyId,
      sourceYear,
      targetYear,
    ],
    enabled: open && Number.isInteger(sourceYear),
    queryFn: async () => {
      const response = await AttendanceHolidaysService.previewCopyYear({
        query: { company_id: companyId },
        body: {
          source_year: sourceYear,
          target_year: targetYear,
          overwrite: false,
        },
      })
      return response.data
    },
  })

  const mutation = useMutation({
    mutationFn: async () =>
      AttendanceHolidaysService.copyYear({
        query: { company_id: companyId },
        body: {
          source_year: sourceYear,
          target_year: targetYear,
          overwrite,
        },
      }),
    onSuccess: (response) => {
      showSuccessToast(
        `复制完成：新增 ${response.data.created}，更新 ${response.data.updated}，跳过 ${response.data.skipped}`,
      )
      onOpenChange(false)
      invalidateRuleHolidayQueries(queryClient)
    },
    onError: (error) => {
      const detail = getErrorDetail(error)
      if (detail?.code === "holiday_conflict") {
        setConflictMessage(detail.message)
        return
      }
      showErrorToast(getErrorMessage(error))
    },
  })

  const preview = previewQuery.data
  const creates = preview?.creates ?? []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>复制上一年节假日</DialogTitle>
          <DialogDescription>
            按同月同日把来源年份的节假日映射到目标年份；2 月 29
            日在非闰年会跳过。冲突日期默认不覆盖。
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="copy-source-year">
              来源年份
            </label>
            <Input
              id="copy-source-year"
              type="number"
              min={1900}
              max={9999}
              value={sourceYear}
              onChange={(event) => {
                setConflictMessage(null)
                setSourceYear(event.target.valueAsNumber)
              }}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="copy-target-year">
              目标年份
            </label>
            <Input
              id="copy-target-year"
              type="number"
              value={targetYear}
              disabled
            />
          </div>
        </div>

        <div
          className="rounded-md border p-3 text-sm"
          data-testid="copy-preview"
        >
          {!Number.isInteger(sourceYear) ? (
            <p className="text-destructive">请输入有效的来源年份。</p>
          ) : previewQuery.isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : previewQuery.isError ? (
            <p className="text-destructive">
              {getErrorMessage(previewQuery.error)}
            </p>
          ) : preview ? (
            <div className="space-y-3">
              <p>
                将新增{" "}
                <span className="font-medium text-foreground">
                  {preview.create_count}
                </span>{" "}
                条，目标年份已存在{" "}
                <span className="font-medium text-foreground">
                  {preview.conflict_count}
                </span>{" "}
                条冲突日期
                {preview.conflict_count > 0 && "（勾选覆盖后更新）"}。
              </p>
              {creates.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">
                    将新增
                  </p>
                  <ul className="max-h-32 space-y-1 overflow-y-auto text-xs text-muted-foreground">
                    {creates.map((item) => (
                      <li key={item.date}>
                        {item.date} · {item.name}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {preview.conflicts.length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">
                    冲突日期
                  </p>
                  <ul className="max-h-40 space-y-1 overflow-y-auto text-xs text-muted-foreground">
                    {preview.conflicts.map((conflict) => (
                      <li key={conflict.date}>
                        {conflict.date}：来源「{conflict.name}」→ 现有「
                        {conflict.existing_name}」
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : null}
        </div>

        <label
          className="flex items-center gap-2 text-sm"
          htmlFor="holiday-copy-overwrite"
        >
          <Checkbox
            id="holiday-copy-overwrite"
            checked={overwrite}
            onCheckedChange={(checked) => {
              setOverwrite(checked === true)
              setConflictMessage(null)
            }}
            aria-label="覆盖目标年份中的冲突日期"
          />
          覆盖目标年份中的冲突日期
        </label>

        {conflictMessage && (
          <p className="text-sm text-destructive" data-testid="copy-conflict">
            {conflictMessage}
          </p>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            disabled={mutation.isPending}
            onClick={() => onOpenChange(false)}
          >
            取消
          </Button>
          <LoadingButton
            loading={mutation.isPending}
            disabled={!Number.isInteger(sourceYear)}
            onClick={() => mutation.mutate()}
          >
            {overwrite ? "覆盖并复制" : "复制"}
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
