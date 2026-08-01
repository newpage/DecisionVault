"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";
import {
  BookOpen,
  BrainCircuit,
  Building2,
  FileUp,
  Gauge,
  LogOut,
  Network,
  Scale,
  ShieldCheck,
} from "lucide-react";
import BrandFooter from "@/components/BrandFooter";
import DiscoverABrand from "@/components/DiscoverABrand";
import ProductBrand from "@/components/ProductBrand";

const links = [
  ["/dashboard", "Dashboard", Gauge],
  ["/decisions", "Decision Center", Scale],
  ["/knowledge", "Knowledge Cards", BookOpen],
  ["/sources", "Evidence Sources", FileUp],
  ["/concepts", "Business Concepts", Network],
  ["/ask", "Ask DecisionVault", BrainCircuit],
  ["/governance", "Governance", ShieldCheck],
  ["/workspaces", "Workspaces", Building2],
] as const;

export default function Shell({
  children,
}: {
  children: React.ReactNode;
}) {
  const path = usePathname();

  function logout() {
    localStorage.removeItem("dv_token");
    location.href = "/login";
  }

  return (
    <div className="shell dv-shell">
      <aside className="sidebar dv-sidebar">
        <DiscoverABrand compact />
        <div className="dv-sidebar-product">
          <ProductBrand />
        </div>

        <nav className="nav dv-navigation">
          {links.map(([href, label, Icon]) => {
            const active =
              path === href ||
              (href !== "/dashboard" && path.startsWith(`${href}/`));

            return (
              <Link
                key={href}
                href={href}
                className={active ? "dv-nav-active" : undefined}
              >
                <Icon size={17} strokeWidth={1.8} />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="dv-sidebar-bottom">
          <button className="btn dv-signout" onClick={logout}>
            <LogOut size={15} strokeWidth={1.8} />
            Sign out
          </button>
          <div className="dv-sidebar-meta">
            <span>Technology owned by DiscoverA.ai</span>
            <small>Release 0.4.1</small>
          </div>
        </div>
      </aside>

      <div className="dv-content-column">
        <main className="main dv-main">{children}</main>
        <BrandFooter />
      </div>
    </div>
  );
}
