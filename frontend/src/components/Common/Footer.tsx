export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t py-4 px-6">
      <p className="text-muted-foreground text-center text-sm">
        © {currentYear} AnySys。保留所有权利。
      </p>
    </footer>
  )
}
