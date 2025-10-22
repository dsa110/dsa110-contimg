# Contributing to the dsa110-contimg Knowledge Graph

This project uses a Graphiti knowledge graph to maintain a long-term, queryable memory of design decisions, domain facts, and feature states. All contributors are encouraged to interact with and enrich the graph as part of their development workflow.

## Daily Workflow

To ensure the knowledge graph remains a valuable and up-to-date asset, please adhere to the following daily practices:

*   **Daily Kickoff:** At the start of each development session, add a short `[Plan]` episode to the graph summarizing your goals for the day. This can be done via the `add_memory` tool.
*   **Continuous Capture:** As you work, use `add_memory` to record key decisions, new requirements, and important facts. Prefix the episode name with `[Decision]`, `[Requirement]`, etc., to clearly identify its type.
*   **Memory-driven Development:** Before starting new work, use the `search_memory_nodes` and `search_memory_facts` tools to retrieve relevant context and recall earlier decisions. This helps to avoid redundant work and ensures consistency.
*   **Daily Wrap-up:** At the end of each session, add a concise `[Summary]` episode documenting what was accomplished, any trade-offs that were made, and any open questions or follow-up actions.

## Git Hook: Commit Summaries to Knowledge Graph

This repository is configured with a post-commit hook that automatically records each commit to the `dsa110-contimg` knowledge graph.

*   **Path:** `.githooks/post-commit`
*   **Activation:** The hook is activated via the git config `core.hooksPath=.githooks`.
*   **Functionality:** The hook creates a "Commit <hash>" episode in the graph for each commit, including the branch and commit message. This process is non-blocking and will not prevent you from committing if it fails.

By following these practices, we can collectively build and maintain a rich, contextual history of the project that will accelerate future development and onboarding.
