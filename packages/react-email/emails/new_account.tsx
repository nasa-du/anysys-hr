import { Text } from "@react-email/components"
import { LinkButton } from "../ui/Button"
import { Callout, Detail } from "../ui/Callout"
import { Heading } from "../ui/Heading"
import { Layout } from "../ui/Layout"
import { Link } from "../ui/Link"

type NewAccountProps = {
  project_name: string
  username: string
  password: string
  link: string
}

export default function NewAccount({
  project_name = "{{ project_name }}",
  username = "{{ username }}",
  password = "{{ password }}",
  link = "{{ link }}",
}: NewAccountProps) {
  return (
    <Layout
      title={`${project_name} - 新账号`}
      preview={`你的 ${project_name} 账号已创建`}
      project_name={project_name}
    >
      <Heading>欢迎使用 {project_name}！</Heading>
      <Text style={bodyTextStyle}>你好，</Text>
      <Text style={bodyTextStyle}>
        你的账号已创建成功，可以直接使用。以下是你的登录信息：
      </Text>
      <Callout>
        <Detail label="用户名" value={username} />
        <Detail label="密码" value={password} />
      </Callout>
      <Text style={bodyTextStyle}>前往仪表盘开始使用：</Text>
      <LinkButton href={link}>前往仪表盘</LinkButton>
      <Text style={supportingTextStyle}>
        或将以下链接复制到浏览器中打开：
        <br />
        <Link href={link}>{link}</Link>
      </Text>
      <Text style={supportingTextStyle}>
        为了账号安全，请在首次登录后修改密码。
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
