import type { ReactNode } from "react"

import type { SchedulePlanConflict } from "@/client"
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
import { SCHEDULE_SCOPE_TYPE_LABELS } from "@/lib/enums"

export interface PlanPreviewData {
  can_apply: boolean
  affected_employees?: number
  added: number
  updated: number
  deleted: number
  manual_preserved: number
  conflicts?: SchedulePlanConflict[]
  warnings?: string[]
}

export function PreviewCounts({ data }: { data: PlanPreviewData }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <CountTile label="新增" value={data.added} tone="good" />
      <CountTile label="更新" value={data.updated} tone="warn" />
      <CountTile label="删除" value={data.deleted} tone="bad" />
      <CountTile label="人工保留" value={data.manual_preserved} tone="muted" />
    </div>
  )
}

function CountTile({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: "good" | "warn" | "bad" | "muted"
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
    <div className="rounded-lg border px-3 py-2">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`text-xl font-semibold ${toneClass}`}>{value}</div>
    </div>
  )
}

export function PreviewBody({
  data,
  extra,
}: {
  data: PlanPreviewData
  extra?: ReactNode
}) {
  const conflicts = data.conflicts ?? []
  const warnings = data.warnings ?? []
  return (
    <>
      {typeof data.affected_employees === "number" && (
        <p className="text-sm text-muted-foreground">
          影响员工 {data.affected_employees} 人；人工例外永不覆盖。
        </p>
      )}
      <PreviewCounts data={data} />

      {conflicts.length > 0 && (
        <div
          role="alert"
          data-testid="preview-conflicts"
          className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          <div className="font-medium">同精确度范围冲突，无法保存：</div>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {conflicts.map((conflict) => (
              <li key={`${conflict.plan_id}-${conflict.scope_id}`}>
                {SCHEDULE_SCOPE_TYPE_LABELS[conflict.scope_type]} ·{" "}
                {conflict.plan_name}
              </li>
            ))}
          </ul>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100">
          <ul className="list-disc space-y-1 pl-5">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {extra}
    </>
  )
}

export function PreviewDialog({
  open,
  title,
  description,
  data,
  busy,
  confirmLabel,
  onConfirm,
  onClose,
  confirmDisabled = false,
  extra,
}: {
  open: boolean
  title: string
  description?: string
  data: PlanPreviewData
  busy?: boolean
  confirmLabel: string
  onConfirm: () => void
  onClose: () => void
  confirmDisabled?: boolean
  extra?: ReactNode
}) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <PreviewBody data={data} extra={extra} />
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            取消
          </Button>
          <LoadingButton
            type="button"
            loading={busy}
            disabled={!data.can_apply || confirmDisabled}
            onClick={onConfirm}
          >
            {confirmLabel}
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  destructive = false,
  busy,
  onConfirm,
  onClose,
  children,
}: {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  destructive?: boolean
  busy?: boolean
  onConfirm: () => void
  onClose: () => void
  children?: ReactNode
}) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {children}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            取消
          </Button>
          <LoadingButton
            type="button"
            loading={busy}
            variant={destructive ? "destructive" : "default"}
            onClick={onConfirm}
          >
            {confirmLabel}
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
