# Repository Structure

Purpose: The authoritative, current folder-and-file map of AI OS.
Last Updated: 2026-08-26
Status: Active
Related Documents: [[Architecture]], [[Naming_Convention]], [[ADR-0005_Project_Knowledge_Separation]]

---

## Where This Tree Starts
The vault (`AI-OS/`, below) is one folder inside a wider repository. The repo root also holds two non-vault siblings, and neither appeared in this "authoritative" map until 2026-08-26:

```
/home/nost/AI-OS/            <- git repository root
├── .env                     Secrets for the TaskRunner services (gitignored)
├── AI-OS/                   <- the Obsidian vault, mapped below
├── AI-OSmcp/                Read-only Notion MCP server (TypeScript, Docker)
└── server-stack/            docker-compose: Jellyfin, Nextcloud, Portainer
```

## Current Tree (vault only, as of Sprint 029)

```
AI-OS/
├── README.md
├── Suggestions.md
├── 00_System/
│   ├── README.md
│   ├── Home.md
│   ├── Dashboard.md
│   ├── Roadmap.md
│   ├── Changelog.md
│   ├── Glossary.md
│   ├── Repository_Audit.md
│   ├── Design_Review.md
│   └── Commands/
│       ├── README.md
│       ├── Command_Index.md
│       └── Quick_Start.md
├── 01_Architecture/
│   ├── README.md
│   ├── Vision.md
│   ├── Principles.md
│   ├── Architecture.md
│   ├── Repository_Structure.md
│   ├── Naming_Convention.md
│   ├── Development_Workflow.md
│   ├── Future_Integration.md
│   ├── ADR/
│   │   ├── README.md
│   │   ├── ADR-0001_Naming_Disambiguation.md
│   │   ├── ADR-0002_Git_Workflow_Conventions.md
│   │   ├── ADR-0003_Execution_Engine_Placement.md
│   │   ├── ADR-0004_Template_Framework_Placement.md
│   │   ├── ADR-0005_Project_Knowledge_Separation.md
│   │   ├── ADR-0006_Project_Folder_Naming.md
│   │   └── ADR-0007_Code_Capabilities.md
│   ├── Execution/
│   │   ├── README.md
│   │   ├── Execution_Philosophy.md
│   │   ├── Execution_Lifecycle.md
│   │   ├── Task_Specification.md
│   │   ├── Quality_Assurance.md
│   │   ├── Learning_Loop.md
│   │   ├── Runtime_State.md
│   └── Templates/
│       ├── README.md
│       ├── Template_Philosophy.md
│       ├── Template_Structure.md
│       ├── Template_Metadata.md
│       ├── Template_Variables.md
│       ├── Template_Validation.md
│       ├── Template_Versioning.md
│       ├── Template_Reuse.md
│       ├── Template_Lifecycle.md
│       └── Template_Quality_Standards.md
├── 02_Systems/
│   ├── README.md
│   ├── Content/
│   │   ├── README.md
│   │   └── Knowledge/
│   │       ├── README.md
│   │       ├── Storytelling_Fundamentals.md
│   │       ├── Narrative_Structure.md
│   │       ├── Hook_Principles.md
│   │       ├── Suspense_And_Curiosity.md
│   │       ├── Pacing.md
│   │       ├── Emotional_Engagement.md
│   │       ├── Reader_Retention.md
│   │       ├── Writing_Style.md
│   │       ├── Clarity.md
│   │       ├── Editing_Principles.md
│   │       └── Horror/
│   │           ├── README.md
│   │           ├── Horror_Hook_Techniques.md
│   │           ├── Horror_Pacing_Model.md
│   │           ├── Escalation_Techniques.md
│   │           ├── Curiosity_Psychology.md
│   │           ├── Open_Loops.md
│   │           ├── Fear_Of_The_Unknown.md
│   │           ├── Dread_And_Anticipation.md
│   │           ├── Body_Horror.md
│   │           ├── Existential_Horror.md
│   │           └── First_Person_Horror_Technique.md
│   ├── Research/README.md
│   ├── Analytics/
│   │   ├── README.md
│   │   ├── Analytics_Philosophy.md
│   │   ├── Metrics_Framework.md
│   │   ├── Success_Criteria.md
│   │   ├── Failure_Analysis.md
│   │   ├── Viral_Analysis.md
│   │   ├── Experiment_Tracking.md
│   │   ├── Learning_Extraction.md
│   │   ├── Knowledge_Promotion_Rules.md
│   │   ├── Review_Process.md
│   │   ├── Review_Cadences.md
│   │   └── Continuous_Improvement_Cycle.md
│   ├── Automation/
│   │   ├── README.md
│   │   ├── vault_status.py            aggregates every Status: header into Dashboard.md
│   │   └── TaskRunner/
│   │       ├── README.md
│   │       ├── System_Prompt.md          the worker's system prompt, versioned as Markdown
│   │       ├── aios_runner.py            the headless worker (systemd: aios-worker)
│   │       ├── dispatch_task.py          CLI entry point
│   │       ├── telegram_bridge.py        Telegram entry point (systemd: aios-telegram)
│   │       ├── scripts/
│   │       │   ├── cloud_backup.py       daily rclone backup (systemd: aios-backup.timer)
│   │       │   └── send_telegram_notification.py
│   │       ├── tasks/                    inbox/completed/logs — runtime, gitignored
│   │       └── backups/                  local archives — runtime, gitignored
│   ├── AI/README.md
│   └── Architecture/README.md
├── 03_Capabilities/
│   ├── README.md
│   ├── Story_Ideation.md
│   ├── Story_Validation.md
│   ├── Originality_Check.md
│   ├── Story_Drafting.md
│   ├── Hook_Writing.md
│   ├── Retention_Beat_Scripting.md
│   ├── Cliffhanger_Creation.md
│   ├── Ending_Design.md
│   ├── Story_Editing.md
│   ├── TTS_Optimization.md
│   ├── CapCut_Production_Formatting.md
│   ├── Multi_Platform_Caption_Generation.md
│   ├── Metadata_Generation.md
│   ├── Series_Planning.md
│   ├── Veo_Prompt_Design.md
│   ├── Generation_Mode_Selection.md
│   ├── Watermark_Tier_Management.md
│   └── AI-Bridge/                        code capability, PARKED — see its README
│       ├── README.md
│       ├── CLAUDE.md
│       ├── bridge.mjs
│       ├── server.mjs
│       ├── roundtable.mjs
│       ├── Dockerfile
│       ├── docker-compose.yml
│       └── space/                        session transcripts
├── 04_Agents/
│   ├── README.md
│   ├── Vault_Architect.md
│   ├── Content_Producer.md
│   ├── Research_Analyst.md
│   └── Business_Development.md
├── 05_Workflows/
│   ├── README.md
│   ├── Workflow_Philosophy.md
│   ├── Workflow_Structure.md
│   ├── Workflow_Lifecycle.md
│   ├── Workflow_Composition.md
│   ├── Workflow_Inputs_And_Outputs.md
│   ├── Workflow_Validation.md
│   ├── Workflow_Error_Handling.md
│   ├── Workflow_Review.md
│   ├── Workflow_Versioning.md
├── 06_Assets/README.md
├── 07_Context/
│   ├── README.md
│   ├── Context_Philosophy.md
│   ├── Context_Resolution.md
│   ├── Dependency_Rules.md
│   ├── Loading_Strategy.md
│   ├── Context_Budget.md
│   ├── Knowledge_Promotion.md
├── 08_Research/README.md
├── 09_Analytics/
│   ├── README.md
│   ├── Hook_Database.md
│   ├── Ending_Database.md
│   ├── Retention_Database.md
│   └── Promotion_Candidates.md
├── 10_Projects/
│   ├── README.md
│   ├── SocialMediaContent/
│   │   ├── README.md
│   │   ├── Reddit_Story_Workflow.md
│   │   ├── AI_Video_Production.md
│   │   ├── Story_Tracker.md
│   │   ├── Reddit_Story_Production.md
│   │   └── Templates/
│   │       ├── README.md
│   │       └── Publishing_Checklist.md
│   ├── MoneyMaking/
│   │   ├── README.md
│   │   ├── Income_Portfolio.md
│   │   ├── Candidate_Options.md
│   │   ├── Perplexity_Research_Prompt.md
│   │   └── German_Legal_Basics.md
│   ├── ContentAgency/
│   │   └── README.md
│   ├── QuickTurnaroundGigs/
│   │   ├── README.md
│   │   ├── Research_And_Briefing_Gigs.md
│   │   ├── Fulfillment_Workflow.md
│   │   └── Real_Time_Problem_Arbitrage.md
│   ├── TemplateSales/
│   │   ├── README.md
│   │   ├── _infra/
│   │   │   ├── AI-CONTEXT.md             authoritative product/launch state
│   │   │   ├── LAUNCH-ORDER.md
│   │   │   ├── pack_builder.py           builds every product's prompt-pack PDF
│   │   │   └── packs/                    per-product PDF configs (pricing, retention)
│   │   ├── Micro-SaaS-Moat-Blueprint/    $29 — built, unpublished
│   │   ├── Pricing-Teardown/             $29 — built, unpublished
│   │   └── Retention-Engineering/        $39 — built, unpublished
│   ├── FundingApplications/
│   │   ├── README.md
│   │   └── Funding_Opportunities.md
│   ├── Personal/
│   │   ├── README.md
│   │   ├── Reading_List.md
│   │   ├── Supplement_Stack.md
│   │   └── Substance_History.md
│   ├── CyberSecurityLearning/
│   │   └── README.md
│   ├── GetClean/
│   │   └── README.md
│   └── LocalArbitrage/
│       ├── README.md
│       ├── Valuation_Method.md
│       ├── Transaction_Log.md
│       └── Legal_Reality.md
└── 99_Archive/
    ├── README.md
    └── HorrorProject/
        ├── README.md
        ├── Horror_Story_System.md
        ├── Horror_Story_Production.md
        └── Stories/
            ├── README.md
            └── The_Doorbell_Camera.md
```

## Folder Responsibilities

| Folder | Responsibility |
|---|---|
| `00_System/` | Navigation, status, roadmap, changelog, glossary, command layer (`Commands/`) |
| `01_Architecture/` | Vision, principles, structural documentation, ADRs, and cross-cutting engine subsystems (`ADR/`, `Execution/`, `Templates/`) — see [[ADR-0003_Execution_Engine_Placement|ADR-0003]], [[ADR-0004_Template_Framework_Placement|ADR-0004]] |
| `02_Systems/` | Reusable knowledge/methodology only, as of Sprint 018 — Content (`Knowledge/` incl. `Knowledge/Horror/`), Analytics, Automation (all populated); Research, AI, Architecture (dormant since Sprint 001). No project execution lives here — see [[ADR-0005_Project_Knowledge_Separation|ADR-0005]] |
| `03_Capabilities/` | Reusable named capabilities — 17 defined, shared across every project that needs them |
| `04_Agents/` | AI agent definitions — 4 scoped roles as of Sprint 024, manual/chat-triggered only |
| `05_Workflows/` | Workflow *framework* only — production workflow instances now live with their project in `10_Projects/` |
| `06_Assets/` | Non-Markdown files (images, exports, actual template files) |
| `07_Context/` | Standing context for agents/workflows, plus the Context Engine |
| `08_Research/` | Research notes and findings |
| `09_Analytics/` | Metrics, reports, performance data — structures built Sprint 012, no real entries yet |
| `10_Projects/` | Active initiatives, now including project-specific execution moved from `02_Systems/`/`05_Workflows/` — 6 projects as of Sprint 020 |
| `99_Archive/` | Deprecated/superseded material — first real content 2026-08-13 (HorrorProject) |

`01_Architecture/` subfolders are an evolving category, not a fixed pair — see [[ADR-0003_Execution_Engine_Placement|ADR-0003]] and [[ADR-0004_Template_Framework_Placement|ADR-0004]] for the rule governing where future cross-cutting subsystems land. The `02_Systems/` vs. `10_Projects/` boundary (knowledge vs. execution) is governed by [[ADR-0005_Project_Knowledge_Separation|ADR-0005]].

This table must stay in sync with the actual folder contents. Adding a top-level folder or changing a folder's responsibility requires an ADR.
