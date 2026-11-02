import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi.json",
  output: "./src/client",

  plugins: [
    { name: "@hey-api/client-axios", throwOnError: true },
    { name: "@hey-api/typescript", case: "preserve" },
    {
      name: "@hey-api/sdk",
      operations: {
        // NOTE: this doesn't allow tree-shaking
        strategy: "byTags",
        methods: "static",
        containerName: "{{name}}Service",
        // Strip every tag prefix before the operation segment, including
        // multi-word tags such as ``cost-centers-``.
        methodName: (name: string): string =>
          name.replace(/^([a-z0-9]+-)+(?=[a-z0-9]+_)/, ""),
      },
    },
  ],
})
