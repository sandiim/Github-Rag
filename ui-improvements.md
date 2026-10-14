# Frontend UI improvements — implementation handoff

Status: proposed design direction; not yet implemented. The user requested a more professional interface for the existing single-user GitHub repository chat application. This document captures the recommendations for a future agent, not a decision to change application behavior.

## Goal

Make the existing repository library and cited-chat workflow feel like a focused developer workspace: easy to scan, calm to read, and clear about indexing and generation state. Preserve the current workflows, API contracts, streaming behavior, and inline commit-pinned citation links.

## Current UI

- React and TypeScript components are under `frontend/src/features/repositories/` and `frontend/src/features/chat/`; `frontend/src/App.tsx` connects them.
- `frontend/src/styles.css` contains most styling in a compact, largely global stylesheet. The two-column layout works but has limited hierarchy and only a basic small-screen rule.
- The sidebar lists saved repositories and contains the add form, ingestion status, retry, and rebuild controls. The chat area shows a repository header, saved messages, inline citations, a streaming/waiting indicator, and a composer.
- The interface already has accessible labels and status roles in several places. Keep those semantics and improve keyboard and responsive behavior rather than replacing them with purely visual controls.

## Recommended direction

A restrained dark developer-tool style is the current recommendation, **not yet a confirmed user choice**. If the user prefers a light documentation-style interface, adapt the same layout and behavior to that palette. Choose the theme before implementation; do not introduce a theme switcher as part of this pass.

Use a small, consistent set of CSS custom properties for background/surface/text/accent/status colors, spacing, radii, and type scale. Prefer the existing React/CSS setup; no UI library or new dependency is needed for this visual pass.

## Proposed changes

### 1. Repository sidebar

- Establish clear hierarchy: product name, repository list, and a prominent “Add repository” action/form.
- Make the selected repository unmistakable without relying on color alone; keep names readable when long and show a compact status label or icon with text.
- Place indexing progress, retry, and rebuild actions in a predictable context for the selected repository. Do not bury failures in a transient toast.
- On narrow screens, allow the repository list and chat to remain navigable without a permanently wide sidebar. Select a simple responsive pattern, such as a collapsible sidebar, and ensure keyboard access.

### 2. Chat workspace

- Give the selected repository a concise header with name, readiness/indexing state, and the existing rebuild action where appropriate.
- Increase reading comfort: a constrained text width, consistent paragraph spacing, clearer distinction between user and assistant turns, and typography suitable for longer answers.
- Keep source links adjacent to the paragraph they support. Style them as recognizable, keyboard-focusable file/line references; do not move them back to a footer list.
- Retain provisional streamed text, citation checkpoints, and the waiting animation. The animation should be quiet, not distracting, and continue to respect reduced-motion preferences.
- Anchor the composer visually to the conversation, with a clear send action and understandable disabled state while a response is active or the repository is not ready.

### 3. States and feedback

- Design intentional empty states for no repositories and for a selected repository with no messages. Explain the next action in each state.
- Make queued, running, ready, and failed ingestion states easy to distinguish with text, not color alone. Keep progress and Retry visible when relevant.
- Present errors near the affected action when practical, with readable text and a recovery path. Avoid adding alerts for routine successful actions.
- Preserve visible status feedback during retrieval, generation pauses, and conversation loading.

### 4. Accessibility and responsiveness

- Preserve semantic landmarks, labels, status announcements, and meaningful button text. Ensure all controls work by keyboard and have an obvious focus indicator.
- Check text and control contrast, click/tap targets, long repository names, long file paths, and narrow viewport layout.
- Respect `prefers-reduced-motion`; do not make motion necessary to understand state.
- Avoid a layout where the message list or composer becomes unusable when the browser is zoomed or the viewport is short.

## Suggested implementation order

1. Decide dark versus light palette with the user; establish CSS tokens and the desktop/mobile page shell.
2. Restyle repository navigation and its add/index/retry/rebuild states.
3. Restyle the chat header, message reading area, citations, and composer.
4. Polish empty/loading/error states and responsive behavior.
5. Test behavior and accessibility; adjust based on a real-browser review.

Keep component responsibilities separate. `App.tsx` should continue orchestrating state and API calls; presentation changes should live primarily in the feature components and CSS. Refactor a component only when needed to support the approved layout. Do not change backend code, ingestion rules, or citation contracts as part of this visual milestone.

## Acceptance checks for the next agent

- Existing add/select/rebuild/retry/chat flows still work; no citation or streaming regression.
- Desktop and narrow-screen layouts keep repository navigation, conversation, and composer usable.
- Loading, indexing, failure, and empty states are understandable without relying on color or animation.
- Keyboard navigation and focus visibility are checked; reduced-motion behavior remains intact.
- Run `cd frontend; npm test -- --run` and `cd frontend; npm run build`; report actual results. Inspect the result in a browser if available, since automated tests alone cannot confirm visual quality.

## Open decision

The user has not yet chosen between the recommended dark developer-tool style and a lighter documentation-style interface. Confirm this before committing to palette and typography. Everything else in this document is a proposal for the next agent to review with the user, not a claim that the redesign is already built.
