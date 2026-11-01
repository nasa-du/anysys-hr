import { z } from "zod"

export const emailSchema = z.email({ message: "请输入有效的邮箱地址" })

export const passwordSchema = z
  .string()
  .min(1, { message: "请输入密码" })
  .min(8, { message: "密码至少需要 8 个字符" })

export const confirmPasswordSchema = z
  .string()
  .min(1, { message: "请再次输入密码" })
