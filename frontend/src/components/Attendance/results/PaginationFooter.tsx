import { ChevronLeft, ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"

type PaginationFooterProps = {
  count: number
  skip: number
  pageSize: number
  onSkipChange: (skip: number) => void
  countTestId?: string
}

/** Shared result-table pagination footer; the API returns count before paging. */
export function PaginationFooter({
  count,
  skip,
  pageSize,
  onSkipChange,
  countTestId,
}: PaginationFooterProps) {
  const start = count === 0 ? 0 : skip + 1
  const end = Math.min(skip + pageSize, count)

  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <span className="text-sm text-muted-foreground" data-testid={countTestId}>
        第 {start}–{end} 条 / 共 {count} 条
      </span>
      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={skip <= 0}
          onClick={() => onSkipChange(Math.max(0, skip - pageSize))}
        >
          <ChevronLeft className="mr-1 size-4" />
          上一页
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={end >= count}
          onClick={() => onSkipChange(skip + pageSize)}
        >
          下一页
          <ChevronRight className="ml-1 size-4" />
        </Button>
      </div>
    </div>
  )
}
