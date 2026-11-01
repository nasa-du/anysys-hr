import { getErrorMessage } from "@/lib/api-error"

export const handleError = function (this: (msg: string) => void, err: Error) {
  this(getErrorMessage(err))
}

export const getInitials = (name: string): string => {
  return name
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase()
}
