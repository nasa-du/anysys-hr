import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import {
  type CostCenterPublic,
  CostCentersService,
  type ErrorDetail,
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

interface DeleteCostCenterDialogProps {
  costCenter: CostCenterPublic | null
  onOpenChange: (open: boolean) => void
  onDeleted: (costCenterId: string) => void
}

export function DeleteCostCenterDialog({
  costCenter,
  onOpenChange,
  onDeleted,
}: DeleteCostCenterDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [blocked, setBlocked] = useState<ErrorDetail | null>(null)

  const mutation = useMutation({
    mutationFn: (costCenterId: string) =>
      CostCentersService.deleteCostCenter({
        path: { cost_center_id: costCenterId },
      }),
    onSuccess: () => {
      showSuccessToast("成本中心删除成功")
      if (costCenter) onDeleted(costCenter.id)
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
      queryClient.invalidateQueries({ queryKey: ["basic", "cost-centers"] })
    },
  })

  return (
    <>
      <Dialog open={costCenter !== null} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>删除成本中心</DialogTitle>
            <DialogDescription>
              将永久删除成本中心「{costCenter?.cost_org_name}
              」。存在下级成本中心或员工引用时无法删除。确定要继续吗？此操作无法撤销。
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
                if (costCenter) mutation.mutate(costCenter.id)
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
        title="无法删除成本中心"
        detail={blocked}
      />
    </>
  )
}
