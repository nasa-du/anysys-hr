import { AxiosError } from "axios"

import type { ErrorDetail } from "@/client"

const FALLBACK_ERROR_MESSAGE = "出错了，请稍后重试。"

type ValidationItem = {
  loc?: Array<string | number>
  msg?: string
}

function getDetail(err: unknown): unknown {
  if (err instanceof AxiosError) {
    return (err.response?.data as { detail?: unknown } | undefined)?.detail
  }
  return undefined
}

/** Read a human-readable Chinese message from any API error shape. */
export function getErrorMessage(err: unknown): string {
  const detail = getDetail(err)

  if (typeof detail === "string" && detail) {
    return detail
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as ValidationItem
    if (typeof first.msg === "string" && first.msg) {
      return first.msg
    }
  }
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const message = (detail as { message?: unknown }).message
    if (typeof message === "string" && message) {
      return message
    }
  }
  return FALLBACK_ERROR_MESSAGE
}

/** Read the 409 domain error envelope, if the response has one. */
export function getErrorDetail(err: unknown): ErrorDetail | null {
  const detail = getDetail(err)
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const candidate = detail as Partial<ErrorDetail>
    if (
      typeof candidate.code === "string" &&
      typeof candidate.message === "string"
    ) {
      return candidate as ErrorDetail
    }
  }
  return null
}

/** Map 409 field_errors and 422 loc/msg pairs onto form field names. */
export function getFieldErrors(err: unknown): Record<string, string> {
  const detail = getDetail(err)

  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const fieldErrors = (detail as { field_errors?: unknown }).field_errors
    if (fieldErrors && typeof fieldErrors === "object") {
      return fieldErrors as Record<string, string>
    }
  }

  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {}
    for (const item of detail as ValidationItem[]) {
      const loc = item.loc ?? []
      const field = loc[loc.length - 1]
      if (
        typeof field === "string" &&
        typeof item.msg === "string" &&
        !(field in fieldErrors)
      ) {
        fieldErrors[field] = item.msg
      }
    }
    return fieldErrors
  }

  return {}
}
