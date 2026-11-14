import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { AttendanceRosterService, type PersonnelSyncPreview } from "@/client"
import {
  ErrorState,
  LoadingState,
} from "@/components/Attendance/shared/StateViews"
import { Button } from "@/components/ui/button"
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
import {
  invalidateRosterQueries,
  rosterSyncPreviewQueryKey,
} from "./roster-queries"

export function SyncPersonnelDialog({
  open,
  companyId,
  month,
  editable,
  onClose,
  onSynced,
}: {
  open: boolean
  companyId: string
  month: string
  editable: boolean
  onClose: () => void
  onSynced: () => void
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const previewQuery = useQuery({
    queryKey: rosterSyncPreviewQueryKey(companyId, month),
    enabled: open,
    queryFn: async () => {
      const response = await AttendanceRosterService.syncPreview({
        query: { company_id: companyId, month },
      })
      return response.data
    },
  })

  const syncMutation = useMutation({
    mutationFn: async () =>
      (
        await AttendanceRosterService.syncPersonnel({
          body: { company_id: companyId, month },
        })
      ).data,
    onSuccess: (result) => {
      showSuccessToast(
        `人员已同步：员工 +${result.added} / -${result.removed} / ~${result.changed}，明细 +${result.entries_added} / ~${result.entries_updated} / -${result.entries_deleted}`,
      )
      invalidateRosterQueries(queryClient)
      onSynced()
    },
  })

  const preview = previewQuery.data
  const busy = syncMutation.isPending

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        className="max-h-[90vh] overflow-y-auto sm:max-w-xl"
        data-testid="sync-personnel-dialog"
      >
        <DialogHeader>
          <DialogTitle>同步人员</DialogTitle>
          <DialogDescription>
            按当前部门和岗位重算整月；人工例外永不覆盖。同步只把已计算月份标记为过期，不会自动重算。
          </DialogDescription>
        </DialogHeader>

        {!editable && (
          <div
            role="status"
            className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            本月已确认或锁定，不能同步人员。请先取消确认或解锁。
          </div>
        )}

        {previewQuery.isLoading ? (
          <LoadingState rows={3} />
        ) : previewQuery.error ? (
          <ErrorState
            message={getErrorMessage(previewQuery.error)}
            onRetry={() => void previewQuery.refetch()}
          />
        ) : preview ? (
          <SyncPreviewBody preview={preview} />
        ) : null}

        {syncMutation.error && (
          <div
            role="alert"
            className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            {getErrorMessage(syncMutation.error)}
          </div>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            关闭
          </Button>
          <LoadingButton
            type="button"
            loading={busy}
            disabled={!editable || !preview}
            onClick={() => syncMutation.mutate()}
          >
            确认同步
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function SyncPreviewBody({
  preview,
}: {
  preview: PersonnelSyncPreview
}) {
  return (
    <div className="space-y-3">
      <div>
        <div className="mb-1 text-sm font-medium">员工变化</div>
        <div className="grid grid-cols-3 gap-2">
          <Tile
            label="新增"
            value={preview.added}
            tone="good"
            testId="sync-added"
          />
          <Tile
            label="移除"
            value={preview.removed}
            tone="bad"
            testId="sync-removed"
          />
          <Tile
            label="变更"
            value={preview.changed}
            tone="warn"
            testId="sync-changed"
          />
        </div>
      </div>
      <div>
        <div className="mb-1 text-sm font-medium">排班明细变化</div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Tile
            label="新增"
            value={preview.entries_added}
            tone="good"
            testId="sync-entries-added"
          />
          <Tile
            label="更新"
            value={preview.entries_updated}
            tone="warn"
            testId="sync-entries-updated"
          />
          <Tile
            label="删除"
            value={preview.entries_deleted}
            tone="bad"
            testId="sync-entries-deleted"
          />
          <Tile
            label="人工保留"
            value={preview.manual_preserved}
            tone="muted"
            testId="sync-manual-preserved"
          />
        </div>
      </div>
      <div className="rounded-md border border-dashed px-3 py-2 text-xs text-muted-foreground">
        基础管理没有调岗历史：同步按员工当前部门和岗位重算整月；新增人员入职前的日期不会生成明细；离职后日期会被移除。
      </div>
    </div>
  )
}

function Tile({
  label,
  value,
  tone,
  testId,
}: {
  label: string
  value: number
  tone: "good" | "warn" | "bad" | "muted"
  testId?: string
}) {
  const toneClass =
    tone === "good"
      ? "text-emerald-700 dark:text-emerald-300"
      : tone === "warn"
        ? "text-amber-700 dark:text-amber-300"
        : tone === "bad"
          ? "text-destructive"
          : "text-muted-foreground"
  return (
    <div className="rounded-lg border px-3 py-2" data-testid={testId}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`text-xl font-semibold ${toneClass}`}>{value}</div>
    </div>
  )
}
