import { zodResolver } from "@hookform/resolvers/zod"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { LoadingButton } from "@/components/ui/loading-button"
import { Textarea } from "@/components/ui/textarea"
import { getErrorMessage } from "@/lib/api-error"

import { useLockMonth, useUnlockMonth } from "./queries"

type DialogProps = {
  companyId: string
  month: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

const unlockSchema = z.object({
  reason: z
    .string()
    .refine((value) => value.trim() !== "", "请填写解锁理由")
    .refine(
      (value) => value.trim().length <= 500,
      "解锁理由不能超过 500 个字符",
    ),
})

type UnlockFormData = z.infer<typeof unlockSchema>

/**
 * Unlocking is the only month transition that requires a reason. The reason is
 * stored on the month and shown in the locked banner and audit trail.
 */
export function UnlockMonthDialog({
  companyId,
  month,
  open,
  onOpenChange,
}: DialogProps) {
  const unlockMonth = useUnlockMonth(companyId, month)
  const [serverError, setServerError] = useState<string | null>(null)
  const form = useForm<UnlockFormData>({
    resolver: zodResolver(unlockSchema),
    mode: "onBlur",
    defaultValues: { reason: "" },
  })

  useEffect(() => {
    if (open) {
      form.reset({ reason: "" })
      setServerError(null)
    }
  }, [open, form])

  const submit = (data: UnlockFormData) => {
    setServerError(null)
    unlockMonth.mutate(data.reason.trim(), {
      onSuccess: () => onOpenChange(false),
      onError: (error) => setServerError(getErrorMessage(error)),
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="unlock-month-dialog">
        <DialogHeader>
          <DialogTitle>解锁 {month}</DialogTitle>
          <DialogDescription>
            解锁后月份回到「已计算」并标记为过期；快照会保留，必须重新计算后才能再次确认。
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form className="space-y-4" onSubmit={form.handleSubmit(submit)}>
            <FormField
              control={form.control}
              name="reason"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>解锁理由</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      data-testid="unlock-reason-input"
                      placeholder="例如：工资复核发现排班错误"
                      maxLength={500}
                      rows={3}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            {serverError && (
              <Alert variant="destructive" data-testid="unlock-error">
                <AlertDescription>{serverError}</AlertDescription>
              </Alert>
            )}
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                取消
              </Button>
              <LoadingButton
                type="submit"
                loading={unlockMonth.isPending}
                data-testid="unlock-submit"
              >
                确认解锁
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

/** Locking freezes the current confirmed results into a new snapshot. */
export function LockMonthDialog({
  companyId,
  month,
  open,
  onOpenChange,
}: DialogProps) {
  const lockMonth = useLockMonth(companyId, month)
  const [serverError, setServerError] = useState<string | null>(null)

  useEffect(() => {
    if (open) setServerError(null)
  }, [open])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="lock-month-dialog">
        <DialogHeader>
          <DialogTitle>锁定 {month}</DialogTitle>
          <DialogDescription>
            锁定会生成一份不可变快照，之后排班、导入和人工调整都会被阻止；如需修改，必须填写理由解锁并重新计算。
          </DialogDescription>
        </DialogHeader>
        {serverError && (
          <Alert variant="destructive" data-testid="lock-error">
            <AlertDescription>{serverError}</AlertDescription>
          </Alert>
        )}
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            取消
          </Button>
          <LoadingButton
            type="button"
            loading={lockMonth.isPending}
            data-testid="lock-submit"
            onClick={() =>
              lockMonth.mutate(undefined, {
                onSuccess: () => onOpenChange(false),
                onError: (error) => setServerError(getErrorMessage(error)),
              })
            }
          >
            确认锁定
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
