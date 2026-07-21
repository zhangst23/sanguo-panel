# APIs Section Sidebar Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the `/apis` section into a sidebar-based layout where categories are listed on the left and content (API listings or details) is shown on the right.

**Architecture:** 
- Use a shared `layout.tsx` in `apps/web/src/app/apis/` to provide the persistent sidebar.
- Responsive design: Sidebar hides on mobile or becomes a drawer.
- The right-side content area will host the page children.

**Tech Stack:** Next.js 15, Tailwind CSS, shadcn/ui, Lucide React.

---

### Task 1: Create APIs Layout with Sidebar

**Files:**
- Create: `apps/web/src/app/apis/layout.tsx`
- Modify: `apps/web/src/app/apis/page.tsx`

**Interfaces:**
- Consumes: Category list (AI, SERP, E-commerce, Maps, Marketing).

- [ ] **Step 1: Implement `apis/layout.tsx`**
  Create a layout with a sidebar on the left and a main content area on the right. The sidebar should highlight the active category.
- [ ] **Step 2: Update `apis/page.tsx`**
  Remove the grid of categories since they are now in the sidebar. Instead, show a welcoming dashboard or a summary of featured APIs.
- [ ] **Step 3: Verify basic layout**
  Run: `pnpm --filter @api-outlet/web dev` and navigate to `/apis`.

### Task 2: Refine Category and Detail Pages for New Layout

**Files:**
- Modify: `apps/web/src/app/apis/[category]/page.tsx`
- Modify: `apps/web/src/app/apis/[category]/[id]/page.tsx`

**Interfaces:**
- Consumes: Sidebar layout from parent.

- [ ] **Step 1: Adjust `apis/[category]/page.tsx`**
  Remove redundant breadcrumbs or headers that are now handled or superseded by the sidebar. Ensure the grid of APIs looks good in the narrower content area.
- [ ] **Step 2: Adjust `apis/[category]/[id]/page.tsx`**
  Ensure the API detail page fits well within the new layout structure.
- [ ] **Step 3: Final verification**
  Navigate through various categories and API details to ensure consistent layout and navigation.
