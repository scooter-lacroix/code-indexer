# Product Guidelines

## Prose Style
-   **Tone:** Professional & Technical.
-   **Focus:** Precision, efficiency, and architectural details suitable for an enterprise-grade backend tool.
-   **Communication:** Interactions should be direct and grounded in technical reality, avoiding unnecessary fluff. Documentation should be rigorous and assume a knowledgeable user base.

## User Experience & Data Presentation
-   **Interaction Model:** Interactive & Navigable. The system should facilitate easy drill-down into search results, version histories, and file structures.
-   **Navigation:** Enable seamless movement between high-level search summaries and deep-dive file analysis.

## Visual Identity (CLI & Documentation)
-   **Aesthetic:** Functional Minimalist.
-   **Structure:** Heavily structured using clear formatting (tables, lists, indentation) to organize complex data.
-   **Styling:** Use ANSI colors strategically to distinguish data types (e.g., file paths vs. code snippets), statuses (e.g., success vs. error), and scores. While using colors, maintain a restrained, professional palette that enhances readability without becoming "icon-rich" or overly decorative.

## Error Handling & Reliability
-   **Primary Strategy:** Graceful Degradation. The system uses the new internal engine (merging Zoekt and ported features) as the **primary** method. It must attempt to silently fallback to alternative search methods (e.g., pure ripgrep or Elasticsearch if configured/relevant) upon failure. Non-intrusive notifications should inform the user of this fallback without interrupting the workflow.
-   **Escalation:** Interactive Recovery. If automatic fallback is impossible or the situation is ambiguous, the system should strictly escalate to an interactive prompt, presenting the user with clear options for resolution.
