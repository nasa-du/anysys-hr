import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import {
  type ErrorDetail,
  type PositionPublic,
  PositionsService,
} from "@/client"
import { DeleteBlockedDialog } from "@/components/BasicManagement/shared/DeleteBlockedDialog"
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
import { getErrorDetail, getErrorMessage } from "@/lib/api-error"

interface DeletePositionDialogProps {
  position: PositionPublic | null
  onOpenChange: (open: boolean) => void
  onDeleted: (positionId: string) => void
}

export function DeletePositionDialog({
  position,
  onOpenChange,
  onDeleted,
}: DeletePositionDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)

  const mutation = useMutation({
    mutationFn: (positionId: string) =>
      PositionsService.deletePosition({ path: { position_id: positionId } }),
    onSuccess: () => {
      showSuccessToast("岗位删除成功")
      if (position) onDeleted(position.id)
      onOpenChange(false)
    },
    onError: (error) => {
      const detail = getErrorDetail(error)
      if (detail?.code === "referenced") {
        onOpenChange(false)
        setBlocked(detail)
        return
      }
      showErrorToast(getErrorMessage(error))
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["basic", "positions"] })
    },
  })

  return (
    <>
      <Dialog open={position !== null} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>删除岗位</DialogTitle>
            <DialogDescription>
              将永久删除岗位「{position?.position_name}
              」。任何员工（包括离职员工）引用该岗位时都无法删除。确定要继续吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              disabled={mutation.isPending}
              onClick={() => onOpenChange(false)}
            >
              取消
            </Button>
            <LoadingButton
              variant="destructive"
              loading={mutation.isPending}
              onClick={() => {
                if (position) mutation.mutate(position.id)
              }}
            >
              删除
            </LoadingButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <DeleteBlockedDialog
        open={blocked !== null}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) setBlocked(null)
        }}
        title="无法删除岗位"
        detail={blocked}
      />
    </>
  )
}
