# 📜 OPUS PROTOCOL V1.1 — "UI-Ease Sprint"

**Mission** — add four usability features (README quick-flip, Streamlit agent toggles, save/load configs, plugin manifest loader).  
If a ledger ticket already exists, update it; otherwise create a new row.

## 1 · Tickets to ensure

| Short code | Deliverable | KPI / Gate | Effort |
|------------|-------------|------------|--------|
| U-01 | README quick-flip doc block | copy-paste table present in README | 0.25 d |
| U-02 | Streamlit sidebar agent toggles | toggle shows & persists state | 0.5 d |
| U-03 | /titan save / load CLI & Slack | config file created & applied | 0.5 d |
| U-04 | Plugin manifest auto-loader | new manifest.yaml agent appears in UI | 0.75 d |

## 2 · Ledger-row schema (reference)

```yaml
id: <auto or next free>
wave: "UX / Ease-of-Use"
owner: "Builder"
deliverable: "<see above>"
kpi: "<see above>"
effort: "<see above>"
status: "⬜ queued"
notes: ""
```

## 3 · Tasks for Opus

1. Scan ledger (`/ledger/snapshot`) for any rows whose deliverable matches U-01…U-04.
2. If missing, POST `/ledger/new_row` with the schema above (fill next free id).
3. If present but not 🟢, leave row as-is.
4. Respond with:

```yaml
tickets:
  - id: <id>           # one entry per ticket
    code: "U-01"
    status: "existing" | "created"
    url: "<row-url-or-None>"
builder_guidance:
  - code: "U-01"
    branch: "builder/U-01-readme-flip"
    tests:
      - "README includes 'Turn features on' table"
  - code: "U-02"
    branch: "builder/U-02-sidebar-toggles"
    tests:
      - "POST /agents/tiny/disable returns 200"
  - code: "U-03"
    branch: "builder/U-03-save-load-cli"
    tests:
      - "CLI command '/titan save config.yaml' works"
      - "Slack '/titan load' command works"
  - code: "U-04"
    branch: "builder/U-04-plugin-manifest"
    tests:
      - "manifest.yaml agent appears in UI"
      - "Plugin auto-loads on startup"
```

## 4 · Success definition

**HTTP 200 with YAML above** → builder-swarm immediately scaffolds branches.  
CI will fail if tests or SBOM scan break.

## 5 · Example invocation

```bash
/opus Execute OPUS PROTOCOL V1.1 — "UI-Ease Sprint"
```

---

## 📋 Manual pipe-check cheatsheet

| Pipe | Your quick check |
|------|------------------|
| Ledger row appears | `curl /ledger/row/<id>` |
| Builder scaffold PR | `gh pr list -l auto-build` |
| SBOM passes | see green check on PR |
| Mini-soak PNG | PR comment "latency.png (25 VU)" |
| Guardian alert none | Grafana "Queue depth" stays green |

**Paste the protocol, let Opus create/verify tickets, and the rest self-propagates.** 