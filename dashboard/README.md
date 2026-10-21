# Central Dashboard

A browser-only dashboard for exploring the Central repository. The UI is a compact, dark, slightly neon workspace with responsive navigation for:

- Repository overview and path/type counts
- Individual agent workspaces, including their personal documents, goal registers, inboxes, event journals, decisions and collections
- Goal horizons, status and prerequisite relationships
- Explicit event and shared-ledger timelines alongside recent repository commits
- Architecture/specification discovery
- Creative/project artifact discovery
- Searchable repository file tree and in-place document reading

## Deployment

The workflow at `.github/workflows/deploy-central-dashboard.yml` publishes the contents of this directory to GitHub Pages on changes to the dashboard or workflow, and supports manual runs. The expected URL is:

`https://daynek.github.io/Central/`

GitHub Pages must be available for the repository and Actions must be permitted to deploy it. Check the repository's Actions tab for the deployment job and its output URL. If GitHub Pages is disabled or restricted by repository/organization settings, enable it in Settings → Pages and rerun the workflow.

## Data model and limits

The dashboard discovers paths from GitHub's recursive Git tree API, reads text files from the configured public branch, and parses Markdown, JSON and JSONL for display. It caches loaded files in page memory until refresh. It reads repository content at runtime, so it reflects changes on the branch without bundling a separate copy of the documents.

The history view distinguishes explicit event/ledger records from commit metadata. Event counts are not a measure of all agent activity, and correlations are not causal explanations. The current commit panel is a recent-commit index, not a full historical diff analytics engine.

This is a **public-data frontend**. Do not embed credentials or private information in the page. A private repository requires a server-side authenticated backend with authorization and per-agent access controls; putting a GitHub token in browser JavaScript would expose it to every visitor. The dashboard does not itself authenticate agents or turn shared-repository folders into private storage.

The document renderer escapes source text before applying basic Markdown formatting. It is intentionally dependency-free and does not execute HTML or scripts found in repository documents.
