# API Categories and Details Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a comprehensive API catalog browsing experience with category-based listing and detailed API documentation pages.

**Architecture:** 
- Next.js 15 App Router structure.
- `/apis` for category overview.
- `/apis/[category]` for endpoint listing within a category.
- `/apis/[category]/[slug]` for specific API documentation.
- Shared components for consistent layout and styling.

**Tech Stack:** Next.js 15, Tailwind CSS, shadcn/ui, Lucide React.

---

### Task 1: Update Navigation and Create APIs Landing Page

**Files:**
- Modify: `apps/web/src/components/navbar.tsx`
- Create: `apps/web/src/app/apis/page.tsx`

**Interfaces:**
- Consumes: Categories data from `api.get("/providers/categories")`.

- [ ] **Step 1: Add "APIs" link to Navbar**
  Update `Navbar` to include the new route.
- [ ] **Step 2: Implement `/apis` landing page**
  Create a grid of category cards with icons (AI, SERP, E-commerce, Maps, Marketing).
- [ ] **Step 3: Verify navigation**
  Run: `npm run dev` in `apps/web` and navigate to `/apis`.

### Task 2: Implement API Category Listing Page

**Files:**
- Create: `apps/web/src/app/apis/[category]/page.tsx`

**Interfaces:**
- Consumes: Providers and their endpoints for a specific category.

- [ ] **Step 1: Create the category listing component**
  Fetch providers for the category and display their endpoints.
- [ ] **Step 2: Add Breadcrumbs**
  Use `Link` to allow navigation back to `/apis`.
- [ ] **Step 3: Verify listing**
  Navigate to `/apis/ai` and ensure endpoints are listed correctly.

### Task 3: Implement API Detail Page

**Files:**
- Create: `apps/web/src/app/apis/[category]/[slug]/page.tsx`

**Interfaces:**
- Consumes: Endpoint details, provider pricing, and documentation.

- [ ] **Step 1: Create the detail view**
  Show HTTP method, path, full URL, pricing, and a code example.
- [ ] **Step 2: Add "Try it out" or "Integration" section**
  Show how to call the API using the platform's unified gateway.
- [ ] **Step 3: Final verification**
  Click an API from the list and verify the detail page loads correctly.
