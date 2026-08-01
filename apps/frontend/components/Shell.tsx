"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";
import {useEffect, useState} from "react";
import {
  BookOpen,
  BrainCircuit,
  Building2,
  ChevronLeft,
  ChevronRight,
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
import styles from "@/components/Shell.module.css";

const STORAGE_KEY = "decisionvault.sidebar.collapsed";

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
  const [collapsed, setCollapsed] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setCollapsed(localStorage.getItem(STORAGE_KEY) === "true");
    setReady(true);
  }, []);

  function toggleSidebar() {
    setCollapsed((current) => {
      const next = !current;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }

  function logout() {
    localStorage.removeItem("dv_token");
    location.href = "/login";
  }

  const shellClassName = [
    "shell",
    "dv-shell",
    styles.shell,
    collapsed ? styles.shellCollapsed : "",
    !ready ? styles.shellLoading : "",
  ]
    .filter(Boolean)
    .join(" ");

  const sidebarClassName = [
    "sidebar",
    "dv-sidebar",
    styles.sidebar,
    collapsed ? styles.sidebarCollapsed : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={shellClassName}>
      <aside className={sidebarClassName}>
        <button
          type="button"
          className={styles.collapseButton}
          onClick={toggleSidebar}
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          title={collapsed ? "Expand navigation" : "Collapse navigation"}
        >
          {collapsed ? (
            <ChevronRight size={16} strokeWidth={1.8} />
          ) : (
            <ChevronLeft size={16} strokeWidth={1.8} />
          )}
        </button>

        <div className={styles.corporateBrand}>
          <DiscoverABrand compact />
        </div>

        <div className={`dv-sidebar-product ${styles.productBrand}`}>
          <ProductBrand />
        </div>

        <nav
          className={`nav dv-navigation ${styles.navigation}`}
          aria-label="Primary navigation"
        >
          {links.map(([href, label, Icon]) => {
            const active =
              path === href ||
              (href !== "/dashboard" && path.startsWith(`${href}/`));

            return (
              <Link
                key={href}
                href={href}
                className={[
                  active ? "dv-nav-active" : "",
                  styles.navigationLink,
                ]
                  .filter(Boolean)
                  .join(" ")}
                aria-label={label}
                title={collapsed ? label : undefined}
              >
                <Icon
                  className={styles.navigationIcon}
                  size={18}
                  strokeWidth={1.8}
                />
                <span className={styles.navigationLabel}>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className={`dv-sidebar-bottom ${styles.sidebarBottom}`}>
          <button
            className={`btn dv-signout ${styles.signout}`}
            onClick={logout}
            aria-label="Sign out"
            title={collapsed ? "Sign out" : undefined}
          >
            <LogOut size={16} strokeWidth={1.8} />
            <span className={styles.signoutLabel}>Sign out</span>
          </button>

          <div className={`dv-sidebar-meta ${styles.sidebarMeta}`}>
            <span className={styles.ownership}>
              Technology owned by DiscoverA.ai
            </span>
            <small className={styles.release}>Release 0.4.1.1</small>
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
