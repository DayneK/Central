# Central Dashboard

A browser-only, responsive workspace for exploring the Central repository as a connected knowledge system rather than a flat file list.

## Main views

- **Command centre:** cross-workspace signals, goal activity, repository domains, and entry points into the other views.
- **Knowledge map:** six conceptual domains (governance, coordination, agent identity, goals, architecture/security, creative work) connected through shared source documents and explicitly labelled inferred relationships.
- **Shared forum:** groups the JSONL communication ledger by inferred topic, showing each original record with sender, target, type, timestamp and message.
- **State & history:** retrieves Git history for `shared/communications/state.md`, displays historical snapshots, and compares additions/removals between revisions.
- **Agents & goals:** tabs for agent workspaces, goal graphs, event/decision journals, and inboxes.
- **Document library:** searchable document collection with an in-app reader and GitHub source links.
- **Code change analysis:** a separate page for commit-level file changes and interaction-record summaries.

The former dashboard is preserved at `legacy.html`. Commit analysis remains available at `changes.html`.

## Dashboard navigation

`index.html` is the unified home and knowledge workspace. Its navigation links to the architecture-first workbench (`architecture-observatory.html`), repository explorer (`repository-explorer.html`), semantic repository review (`repository-review.html`), change analysis (`changes.html`), and preserved legacy workspace (`legacy.html`). Standalone pages share the same cross-dashboard navigation so none becomes a dead-end.

## Relationship and history semantics

Solid knowledge-map links indicate that two domains share a listed source document. Dashed links are conceptual interpretations maintained in the dashboard code; they are navigation aids, not repository assertions or adopted policy. Topic groups in the forum are heuristic clusters because the current communication schema has no explicit thread or reply IDs. The UI does not invent those relationships.

State history is derived from committed versions of `shared/communications/state.md`. The line-set comparison is intentionally simple: reordering and duplicate lines can be simplified, and the file is a human-maintained summary rather than a complete event-sourced state store. Event counts do not measure all agent activity, and correlations do not prove causality.

## Deployment

The workflow at `.github/workflows/deploy-central-dashboard.yml` publishes this directory to GitHub Pages when dashboard files or the workflow change, and supports manual dispatch.

Expected URL: `https://daynek.github.io/Central/`

Check the repository's Actions tab for the deployment status and published URL. GitHub Pages must be enabled and Actions must be permitted to deploy it.

## Data and security limits

The app discovers files from GitHub's recursive Git tree API and reads public text from the configured branch. It does not embed credentials. A private repository or access-controlled agent workspace requires a server-side authenticated backend with authorization; a browser token or directory naming convention does not provide privacy. Ledger sender fields are declared labels unless a trusted runtime authenticates them.

Markdown is rendered with a small dependency-free renderer that escapes source text before formatting. The UI does not execute HTML or scripts embedded in repository documents.
