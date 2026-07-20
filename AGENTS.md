# PaperLens - Agent Instructions

## Project Overview

AI-driven academic paper review assistant. Current phase: P2.5 completed (PDF upload, parsing, Evidence extraction). Next: P3 (LLM review), P4 (metrics), P5 (Excel analysis), P6 (report export).

## Skill Usage Rules

This project uses 7 CodeArts skills installed at `.codeartsdoer/skills/`. **Every code change must follow the appropriate skill workflow.**

### Skill Dependency Chain

```
dev-process-framework → page-mockup → fullstack-testing → function-detail → sdd-workflow
                                                                                   ↓
                                                                            bug-fix-reporter
```

### When to Use Each Skill

| Scenario | Skill | Action |
|----------|-------|--------|
| New feature or requirement change | `dev-process-framework` | Update `ProjectDocs/systemDesign/01~06` first |
| New or changed UI page | `page-mockup` | Update `ProjectDocs/systemDesign/07-页面设计.md` |
| New or changed test design | `fullstack-testing` | Update `ProjectDocs/systemDesign/08-测试设计.md` |
| Feature ready for development | `function-detail` | Generate/update `ProjectDocs/specs_SDD/PaperLens/` |
| Development progress tracking | `sdd-workflow` | Update `ProjectDocs/sprint/{feature}.md` |
| Bug fix completed | `bug-fix-reporter` | Create report in `ProjectDocs/bugfix-report/` |
| Install/update skills | `dev-eco-setup` | Run `python .codeartsdoer/skills/dev-eco-setup/scripts/fetch_skills.py` |

### Mandatory Workflow

1. **Before coding**: Check if `ProjectDocs/systemDesign/` or `ProjectDocs/specs_SDD/` needs updates
2. **During coding**: Follow the design docs in `specs_SDD/PaperLens/design/`
3. **After coding**: Update sprint progress in `ProjectDocs/sprint/`
4. **Bug fixes**: Always generate a bugfix report via `bug-fix-reporter`
5. **Test changes**: Update `08-测试设计.md` and write/update the required tests; execute them only in the acceptance phase

### Document Locations

```
ProjectDocs/
├── systemDesign/          # Design documents (01-08)
│   ├── 01-需求细化与决策发现.md
│   ├── 02-架构设计.md
│   ├── 03-数据模型设计.md
│   ├── 04-API接口设计.md
│   ├── 05-实施计划.md
│   ├── 06-需求规格说明.md
│   ├── 07-页面设计.md
│   └── 08-测试设计.md
├── specs_SDD/PaperLens/   # SDD document system
│   ├── spec.md
│   ├── tasks.md
│   └── design/
├── sprint/                # Sprint progress tracking
│   ├── 论文上传与解析.md
│   ├── 证据提取与检索.md
│   └── 前端展示.md
└── bugfix-report/         # Bug fix reports (auto-generated)
```

## Code Style

- Backend: Python, FastAPI, SQLAlchemy, Alembic
- Frontend: Vue 3, TypeScript, Vite, Vitest
- No comments unless explicitly requested
- Relevant lightweight tests must pass before completing a task; do not require exhaustive coverage for this personal project

## Testing

- CodeArts implementation prompts must require writing or updating tests but must explicitly prohibit running test, build, migration round-trip, Docker rebuild, or HTTP smoke commands.
- Test execution is centralized in the acceptance phase after CodeArts finishes the implementation turn.
- Default acceptance uses only changed-module targeted tests, one critical smoke flow, and the production build when frontend code changes.
- For each new feature, prefer 1 normal case, 1 important failure case, and at most 1 concurrency or recovery case when that risk actually exists. Avoid exhaustive parameter combinations, repeated fault-injection matrices, coverage targets, and large generated samples.
- Keep the existing regression suite as optional reusable assets. Run the full backend/frontend suite only for final release, or after high-risk authentication, migration-chain, or shared-infrastructure changes.
- Docker backend: `docker compose exec -T backend python -m pytest -q -rs`
- Frontend: `cd frontend && npm test -- --run`
- Build: `cd frontend && npm run build`
- Test DB isolation: `paperlens_test` database, `PAPERLENS_REQUIRE_TEST_DB=true` in Docker

## Documentation Attribution

- All project documentation, progress logs, Sprint records, bug-fix reports, and prompt archives must attribute implementation, review, correction, and verification to CodeArts（码道）only.
- Do not mention other AI assistants or agents in project-document content or filenames.
- New reports and historical-document updates must continue using the same CodeArts-only attribution.

## Constraints

- Do NOT modify `.arts/` or `.codeartsdoer/` directories
- Do NOT commit secrets, API keys, or credentials
- Do NOT implement FAISS, LLM, metrics extraction, Excel analysis, or report export until P3+
- Do NOT run `docker compose down -v` or delete database volumes
- Do NOT git commit unless explicitly requested
