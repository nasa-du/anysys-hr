import { Text } from "@react-email/components"
import { LinkButton } from "../ui/Button"
import { Heading } from "../ui/Heading"
import { Layout } from "../ui/Layout"
import { Link } from "../ui/Link"

type ResetPasswordProps = {
  project_name: string
  username: string
  link: string
  valid_hours: string
}

export default function ResetPassword({
  project_name = "{{ project_name }}",
  username = "{{ username }}",
  link = "{{ link }}",
  valid_hours = "{{ valid_hours }}",
}: ResetPasswordProps) {
  return (
    <Layout
      title={`${project_name} - 重置密码`}
      preview={`重置你的 ${project_name} 密码`}
      project_name={project_name}
    >
      <Heading>重置密码</Heading>
      <Text style={bodyTextStyle}>你好 {username}，</Text>
      <Text style={bodyTextStyle}>
        我们收到了重置你的 {project_name}{" "}
        账号密码的请求。点击下方按钮设置新密码：
      </Text>
      <LinkButton href={link}>重置密码</LinkButton>
      <Text style={supportingTextStyle}>
        或将以下链接复制到浏览器中打开：
        <br />
        <Link href={link}>{link}</Link>
      </Text>
      <Text style={supportingTextStyle}>
        该链接将在 {valid_hours} 小时后失效。
      </Text>
      <Text style={supportingTextStyle}>
        如果这不是你本人的操作，可以忽略这封邮件。
      </Text>
    </Layout>
  )
}

const bodyTextStyle = {
  color: "#334155",
  fontSize: "15px",
  lineHeight: "26px",
  margin: "0 0 18px",
}

const supportingTextStyle = {
  color: "#64748b",
  fontSize: "14px",
  lineHeight: "23px",
  margin: "0 0 16px",
}
