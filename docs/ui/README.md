# UI engineering notes

The UI is a Next.js 15 App Router application in `apps/frontend`, using React 19, TypeScript, CSS modules, and global brand styles. Routes cover login, dashboard, workspaces, sources, knowledge, Ask DecisionVault, governance, business concepts, decisions, and the Decision Workspace.

Use the shared `lib/api.ts` client for authenticated browser requests. Preserve loading, empty, error, and unauthorized states; accessibility and responsive/collapsed navigation are review requirements. Run `npm run build` and provide screenshots for visual changes. Branding changes require explicit product approval and are outside routine engineering refactors.

