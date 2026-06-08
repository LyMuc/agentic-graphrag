# Chainlit frontend baseline

This directory is based on the official Chainlit `2.11.1` frontend:

- Tag: `2.11.1`
- Commit: `dd14df53709c6c1389faa82b406c8bfa8e9b61bc`
- React client: `@chainlit/react-client@0.4.2`

Application-specific changes are intentionally limited to:

- `src/components/LeftSidebar/`
- Project API methods in `src/api/index.ts`
- Project types in `src/types/projects.ts`
- Standalone build configuration

Build the production bundle with:

```powershell
cd frontend
npx.cmd pnpm@9.15.9 install --frozen-lockfile
npx.cmd pnpm@9.15.9 build
```

The bundle is written to `public/chainlit-build` and loaded through
`UI.custom_build` in `.chainlit/config.toml`.

Before upgrading Chainlit, rebase these changes onto the matching upstream
frontend tag and run type-check, Vitest, production build, and sidebar smoke
tests.
