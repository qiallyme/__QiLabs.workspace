import os
from pathlib import Path

REPO_ROOT = Path("c:/_QiOne_MonoRepo_v2")

files_to_create = [
    ("apps/qione/middleware.ts", "export function middleware() {}"),
    ("apps/qione/README.md", "# QiOne\nPrimary authenticated operating app."),
    ("apps/qione/public/favicon.ico", ""),
    ("apps/qione/src/app/(public)/login/page.tsx", "export default function LoginPage() { return <div>Login</div> }"),
    ("apps/qione/src/app/(app)/page.tsx", "export default function DashboardHome() { return <div>Dashboard Home</div> }"),
    ("apps/qione/src/app/(app)/dashboard/page.tsx", "export default function DashboardPage() { return <div>Dashboard</div> }"),
    ("apps/qione/src/app/(app)/ai/page.tsx", "export default function AIPage() { return <div>AI</div> }"),
    ("apps/qione/src/app/(app)/documents/page.tsx", "export default function DocumentsPage() { return <div>Documents</div> }"),
    ("apps/qione/src/app/(app)/chronicle/page.tsx", "export default function ChroniclePage() { return <div>Chronicle</div> }"),
    ("apps/qione/src/app/(app)/notes/page.tsx", "export default function NotesPage() { return <div>Notes</div> }"),
    ("apps/qione/src/app/(app)/objects/page.tsx", "export default function ObjectsPage() { return <div>Objects</div> }"),
    ("apps/qione/src/app/(app)/forms/page.tsx", "export default function FormsPage() { return <div>Forms</div> }"),
    ("apps/qione/src/app/(app)/contracts/page.tsx", "export default function ContractsPage() { return <div>Contracts</div> }"),
    ("apps/qione/src/app/(app)/tax/page.tsx", "export default function TaxPage() { return <div>Tax</div> }"),
    ("apps/qione/src/app/(app)/care/page.tsx", "export default function CarePage() { return <div>Care</div> }"),
    ("apps/qione/src/app/(app)/settings/page.tsx", "export default function SettingsPage() { return <div>Settings</div> }"),
    ("apps/qione/src/app/(app)/admin/page.tsx", "export default function AdminPage() { return <div>Admin</div> }"),
    ("apps/qione/src/components/layout/AppShell.tsx", "export const AppShell = ({ children }) => <div>{children}</div>"),
    ("apps/qione/src/components/layout/Sidebar.tsx", "export const Sidebar = () => <aside>Sidebar</aside>"),
    ("apps/qione/src/components/layout/Topbar.tsx", "export const Topbar = () => <header>Topbar</header>"),
    ("apps/qione/src/components/ui/button.tsx", "export const Button = () => <button>Button</button>"),
    ("apps/qione/src/components/ui/card.tsx", "export const Card = () => <div>Card</div>"),
    ("apps/qione/src/components/ui/dialog.tsx", "export const Dialog = () => <div>Dialog</div>"),
    ("apps/qione/src/components/ui/input.tsx", "export const Input = () => <input />"),
    ("apps/qially-web/.env.example", "NEXT_PUBLIC_SUPABASE_URL=\nNEXT_PUBLIC_SUPABASE_ANON_KEY="),
]

def create_stubs():
    for rel_path, content in files_to_create:
        full_path = REPO_ROOT / rel_path
        if not full_path.exists():
            print(f"Creating stub: {rel_path}")
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            print(f"Skipping existing: {rel_path}")

if __name__ == "__main__":
    create_stubs()
    print("Stub creation complete.")
