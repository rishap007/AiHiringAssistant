import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hunar Hiring Assistant",
  description: "Recruiter workspace for Hunar voice screening and outreach",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <body className="min-h-full bg-muted/30 text-foreground">
        <div className="flex min-h-screen">
          <header className="flex items-center justify-between border-b bg-background px-4 py-3 md:hidden">
            <div>
              <p className="font-semibold">Hunar</p>
              <p className="text-xs text-muted-foreground">Hiring workspace</p>
            </div>
            <nav className="flex gap-1" aria-label="Mobile navigation">
              <Link className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted" href="/hiring-assistant">
                Hiring
              </Link>
              <Link className="rounded-md px-3 py-2 text-sm font-medium hover:bg-muted" href="/people-search">
                Search
              </Link>
            </nav>
          </header>
          <aside className="hidden w-64 shrink-0 border-r bg-background p-6 md:block">
            <div className="mb-8">
              <p className="text-lg font-semibold">Hunar</p>
              <p className="text-sm text-muted-foreground">Hiring workspace</p>
            </div>
            <nav className="space-y-1" aria-label="Primary navigation">
              <Link className="block rounded-md px-3 py-2 text-sm font-medium hover:bg-muted" href="/hiring-assistant">
                Hiring Assistant
              </Link>
              <Link className="block rounded-md px-3 py-2 text-sm font-medium hover:bg-muted" href="/people-search">
                People Search
              </Link>
            </nav>
          </aside>
          <main className="min-w-0 flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
