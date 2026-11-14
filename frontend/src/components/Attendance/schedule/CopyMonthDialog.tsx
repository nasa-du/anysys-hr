import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"

import {
  AttendanceSchedulePlansService,
  type PlanCopyPreview,
  type SchedulePlanPublic,
} from "@/client"
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
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { getErrorMessage } from "@/lib/api-error"
import { PreviewBody } from "./PreviewDialog"
import { nextMonth } from "./plan-utils"
import { invalidatePlanQueries } from "./queries"

export function CopyMonthDialog({
  open,
  month,
  plan,
  onClose,
  onCopied,
}: {
  open: boolean
  month: string
  plan: SchedulePlanPublic | null
  onClose: () => void
  onCopied: (newPlanId: string) => void
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [includeManual, setIncludeManual] = useState(false)
  const [confirmOverwrite, setConfirmOverwrite] = useState(false)
  const [preview, setPreview] = useState<PlanCopyPreview | null>(null)
  const targetMonth = nextMonth(month)

  useEffect(() => {
    if (open) {
      setIncludeManual(false)
      setConfirmOverwrite(false)
      setPreview(null)
    }
  }, [open])

  const needsOverwrite = (preview?.updated ?? 0) + (preview?.deleted ?? 0) > 0

  const previewMutation = useMutation({
    mutationFn: async () => {
      if (!plan) throw new Error("请选择排班方案")
      const response = await AttendanceSchedulePlansService.copyPreview({
        path: { plan_id: plan.id },
        body: {
          target_month: targetMonth,
          include_manual_exceptions: includeManual,
          confirm_overwrite: false,
        },
      })
      return response.data
    },
    onSuccess: setPreview,
    onError: (error) => showErrorToast(getErrorMessage(error)),
  })

  const copyMutation = useMutation({
    mutationFn: async () => {
      if (!plan) throw new Error("请选择排班方案")
      const response = await AttendanceSchedulePlansService.copySchedulePlan({
        path: { plan_id: plan.id },
        body: {
          target_month: targetMonth,
          include_manual_exceptions: includeManual,
          confirm_overwrite: needsOverwrite ? confirmOverwrite : false,
        },
      })
      return response.data
    },
    onSuccess: (created) => {
      showSuccessToast(`已复制到 ${targetMonth} 并重新展开`)
      invalidatePlanQueries(queryClient)
      onCopied(created.id)
    },
    onError: (error) => showErrorToast(getErrorMessage(error)),
  })

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        className="max-h-[90vh] overflow-y-auto sm:max-w-2xl"
        data-testid="copy-month-dialog"
      >
        <DialogHeader>
          <DialogTitle>复制下月</DialogTitle>
          <DialogDescription>
            只支持下一个自然月：{month} → {targetMonth}
            。复制方案定义并按日期号映射， 目标月重新展开；人工例外默认不复制。
          </DialogDescription>
        </DialogHeader>

        {preview ? (
          <div className="space-y-4">
            <PreviewBody data={{ ...preview, affected_employees: undefined }} />
            {needsOverwrite && (
              <label
                htmlFor="copy-confirm-overwrite"
                className="flex items-start gap-2 rounded-md border px-3 py-2 text-sm"
              >
                <Checkbox
                  id="copy-confirm-overwrite"
                  checked={confirmOverwrite}
                  onCheckedChange={(checked) =>
                    setConfirmOverwrite(checked === true)
                  }
                  aria-label="确认覆盖目标月份的方案排班明细"
                />
                <span>
                  目标月份已有 {preview.updated + preview.deleted}{" "}
                  条方案排班明细将被覆盖，请确认覆盖后复制。
                </span>
              </label>
            )}
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setPreview(null)}
              >
                返回修改
              </Button>
              <LoadingButton
                type="button"
                loading={copyMutation.isPending}
                disabled={
                  !preview.can_apply || (needsOverwrite && !confirmOverwrite)
                }
                onClick={() => copyMutation.mutate()}
              >
                确认复制并展开
              </LoadingButton>
            </DialogFooter>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-md border px-3 py-2 text-sm">
              <div>
                源月份 {month} · 目标月份 {targetMonth}
              </div>
              <div className="text-muted-foreground">
                目标月不复制节假日；使用自己的节假日日历与当前公司规则。
              </div>
            </div>
            <label
              htmlFor="copy-include-manual"
              className="flex items-center gap-2 text-sm"
            >
              <Checkbox
                id="copy-include-manual"
                checked={includeManual}
                onCheckedChange={(checked) =>
                  setIncludeManual(checked === true)
                }
                aria-label="同时复制人工例外"
              />
              同时复制人工例外（仅目标月存在的日期号）
            </label>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                取消
              </Button>
              <LoadingButton
                type="button"
                loading={previewMutation.isPending}
                disabled={!plan}
                onClick={() => previewMutation.mutate()}
              >
                预览复制
              </LoadingButton>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
