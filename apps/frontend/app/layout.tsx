import type {Metadata} from "next";
import "./globals.css";
import "./branding.css";

export const metadata: Metadata = {
  title: {
    default: "DecisionVault | DiscoverA.ai",
    template: "%s | DecisionVault by DiscoverA.ai",
  },
  description:
    "Enterprise Decision Intelligence technology developed and owned by DiscoverA.ai.",
  applicationName: "DecisionVault",
  authors: [{name: "DiscoverA.ai"}],
  creator: "DiscoverA.ai",
  publisher: "DiscoverA.ai",
  robots: {
    index: false,
    follow: false,
    nocache: true,
  },
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="app">{children}</div>
      </body>
    </html>
  );
}
