import { Text } from "@react-email/components"
import { Callout, Detail } from "../ui/Callout"
import { Heading } from "../ui/Heading"
import { Layout } from "../ui/Layout"

type TestEmailProps = {
  project_name: string
  email: string
}

export default function TestEmail({
  project_name = "{{ project_name }}",
  email = "{{ email }}",
}: TestEmailProps) {
  return (
    <Layout
      title={`${project_name} - 测试邮件`}
      preview={`${project_name} 邮件发送配置正常`}
      project_name={project_name}
    >
      <Heading>测试邮件</Heading>
      <Text style={bodyTextStyle}>你好，</Text>
      <Text style={bodyTextStyle}>
        这是一封来自 {project_name}{" "}
        的测试邮件。如果你能看到这封邮件，说明邮件发送配置正确。
      </Text>
      <Callout>
        <Detail label="收件人" value={email} />
      </Callout>
      <Text style={supportingTextStyle}>
        如果你没有预期收到这封邮件，可以忽略它。
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
