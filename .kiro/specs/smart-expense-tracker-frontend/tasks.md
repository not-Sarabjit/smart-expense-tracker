# Implementation Plan: Smart Expense Tracker Frontend

## Overview

Build a React 18 + TypeScript + Vite SPA that communicates with the FastAPI backend at `http://localhost:3000/api/v1`. The implementation proceeds in layers: project scaffold → shared infrastructure → auth → layout → dashboard → category management → integration and polish. Each layer builds on the previous and is validated with automated tests before moving on.

## Tasks

- [x] 1. Scaffold the Vite + React + TypeScript project
  - [x] 1.1 Initialise the Vite project in the `frontend/` directory with the React-TypeScript template
    - Run `npm create vite@latest frontend -- --template react-ts` at the workspace root
    - Verify `frontend/` directory is created with `src/`, `index.html`, `vite.config.ts`, and `package.json`
    - _Requirements: 1.1_
  - [x] 1.2 Install runtime dependencies and configure Tailwind CSS
    - Install `tailwindcss`, `postcss`, `autoprefixer` as dev dependencies and run `npx tailwindcss init -p` to generate `tailwind.config.ts` and `postcss.config.js`
    - Set the `content` array in `tailwind.config.ts` to `["./index.html", "./src/**/*.{ts,tsx}"]`
    - Add `@tailwind base`, `@tailwind components`, and `@tailwind utilities` to `src/index.css`
    - Install `recharts`, `axios`, and `react-router-dom` as runtime dependencies
    - _Requirements: 1.2, 1.3, 1.4_
  - [x] 1.3 Set Vite dev server port to 3000 and configure path aliases
    - In `vite.config.ts`, add `server: { port: 3000 }` and a `@/` path alias pointing to `src/`
    - _Requirements: 1.2_

- [x] 2. Build the shared API layer and TypeScript types
  - [x] 2.1 Create shared TypeScript interfaces in `src/types/index.ts`
    - Define `User`, `Category`, `Transaction`, `MonthlySummary`, `AuthTokenResponse`, `TransactionCreatePayload`, `TransactionUpdatePayload`, `CategoryCreatePayload`, `CategoryUpdatePayload`, `TransactionType`, and `CategoryType` as specified in the design
    - _Requirements: 1.5, 8.2, 9.3, 11.3_
  - [x] 2.2 Create the Axios instance with interceptors in `src/api/client.ts`
    - Export a single `apiClient` with `baseURL: "http://localhost:3000/api/v1"`
    - Add a request interceptor that reads `localStorage.getItem("access_token")` and attaches `Authorization: Bearer <token>` when present; sends without the header when absent
    - Add a response interceptor that, on any 401 response, removes `access_token` from `localStorage` and sets `window.location.href = "/login"`
    - _Requirements: 1.5, 1.6, 1.7, 3.5_
  - [ ]* 2.3 Write property test for JWT Attachment Invariant
    - **Property 1: JWT Attachment Invariant**
    - **Validates: Requirements 1.6, 1.7**
    - Generate arbitrary request configs with `localStorage` in two states (token present / absent); assert `Authorization` header presence matches expectation in both branches
    - Tag: `// Feature: smart-expense-tracker-frontend, Property 1: JWT Attachment Invariant`
  - [x] 2.4 Create API module files: `src/api/auth.ts`, `src/api/transactions.ts`, `src/api/categories.ts`
    - `auth.ts`: export `login(email, password)` → `POST /auth/login` and `register(payload)` → `POST /auth/register`
    - `transactions.ts`: export `getTransactions(params)`, `createTransaction(payload)`, `updateTransaction(id, payload)`, `deleteTransaction(id)`, `getSummary(year, month)`
    - `categories.ts`: export `getCategories()`, `createCategory(payload)`, `updateCategory(id, payload)`, `deleteCategory(id)`
    - _Requirements: 2.4, 2.5, 8.1, 9.4, 9.6, 10.4, 11.5, 11.7, 11.10_
  - [x] 2.5 Create `src/utils/formatters.ts` and `src/utils/errorHandling.ts`
    - `formatters.ts`: export `formatCurrency(amount: number, symbol?: string): string` that always produces exactly two decimal places; export `formatDate(isoString: string): string` for "MMM D, YYYY" output
    - `errorHandling.ts`: implement `extractErrorMessage(err, fallback)` as defined in the design
    - _Requirements: 5.7, 8.2, 12.2_
  - [ ]* 2.6 Write property test for Monetary Formatting Invariant
    - **Property 7: Monetary Formatting Invariant**
    - **Validates: Requirements 5.7**
    - Generate arbitrary positive numbers (including edge cases like 0.1, 1000000, 0.999) and assert `formatCurrency(n)` output matches `/\.\d{2}$/`
    - Tag: `// Feature: smart-expense-tracker-frontend, Property 7: Monetary Formatting Invariant`
  - [x] 2.7 Create `src/utils/theme.ts`
    - Export `applyTheme(theme: "dark" | "light")` that toggles the `dark` CSS class on `document.documentElement` and persists to `localStorage["theme"]`
    - Export `readTheme()` that returns the stored theme defaulting to `"light"`
    - _Requirements: 4.7, 4.8, 4.9, 13.3, 13.4_
  - [ ]* 2.8 Write property test for Dark Mode Theme Persistence Round-Trip
    - **Property 8: Dark Mode Theme Persistence Round-Trip**
    - **Validates: Requirements 4.7, 4.8, 13.3, 13.4**
    - Generate arbitrary sequences of toggle calls and assert that after each call the `dark` class on `<html>` and `localStorage["theme"]` remain consistent
    - Tag: `// Feature: smart-expense-tracker-frontend, Property 8: Dark Mode Theme Persistence Round-Trip`

- [x] 3. Checkpoint — Verify shared infrastructure
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement Authentication
  - [x] 4.1 Create the `useAuth` custom hook in `src/hooks/useAuth.ts`
    - Expose `login(email, password)`, `register(payload)`, `logout()`, `isAuthenticated(): boolean`
    - `login`: calls `auth.login`, stores `access_token` and serialised `User` in `localStorage`; throws on error
    - `register`: calls `auth.register`, then auto-calls `login` with same credentials; throws on error
    - `logout`: removes `access_token` and `user_profile` from `localStorage`
    - _Requirements: 2.4, 2.5, 2.6, 2.10, 3.4_
  - [x] 4.2 Build `AuthPage` at `src/pages/AuthPage.tsx`
    - Toggle between Login and Sign-Up modes
    - Login form: `email` + `password` fields with inline empty-field validation
    - Sign-Up form: `first_name`, `last_name`, `email`, `password` fields with inline empty-field validation
    - On submit: call the appropriate `useAuth` method; on success navigate to `/dashboard`; on API error display `detail` below the submit button
    - While in-flight: disable the submit button and render a `LoadingSpinner` inside it
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_
  - [ ]* 4.3 Write property test for Auth Form Submission Gate
    - **Property 2: Auth Form Submission Gate**
    - **Validates: Requirements 2.9**
    - Generate arbitrary form states where at least one required field is empty or whitespace-only; assert the submit handler never calls the API client
    - Tag: `// Feature: smart-expense-tracker-frontend, Property 2: Auth Form Submission Gate`
  - [x] 4.4 Build `ProtectedRoute` at `src/components/layout/ProtectedRoute.tsx`
    - Checks `localStorage.getItem("access_token")`; renders `<Navigate to="/login" replace />` if absent; renders `<Outlet />` if present
    - Add the inverse guard in `App.tsx`: if the user is authenticated and navigates to `/login`, redirect to `/dashboard`
    - _Requirements: 3.1, 3.2, 3.3_
  - [ ]* 4.5 Write property test for ProtectedRoute Redirection Invariant
    - **Property 3: ProtectedRoute Redirection Invariant**
    - **Validates: Requirements 3.1, 3.2, 3.3**
    - Generate arbitrary protected route paths and assert resulting rendered route is `/login` when unauthenticated; assert `/login` path redirects to `/dashboard` when authenticated
    - Tag: `// Feature: smart-expense-tracker-frontend, Property 3: ProtectedRoute Redirection Invariant`
  - [ ]* 4.6 Write property test for 401 Global Logout Invariant
    - **Property 4: 401 Global Logout Invariant**
    - **Validates: Requirements 3.5**
    - Mock Axios responses with status 401 and assert that after the interceptor runs: `localStorage` does not contain `access_token`, and `window.location.href` is `/login`
    - Tag: `// Feature: smart-expense-tracker-frontend, Property 4: 401 Global Logout Invariant`
  - [x] 4.7 Wire up React Router in `src/App.tsx` and bootstrap theme in `src/main.tsx`
    - Define routes: `/login` → `AuthPage`, protected group wrapping `/dashboard` → `DashboardPage` and `/categories` → `CategoriesPage`, catch-all redirect to `/dashboard`
    - In `main.tsx`: call `applyTheme(readTheme())` before `ReactDOM.createRoot(...).render(...)` to apply persisted theme before first render
    - _Requirements: 3.1, 4.9, 13.4_

- [x] 5. Checkpoint — Verify auth and routing
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Build shared UI primitives
  - [x] 6.1 Create `src/components/ui/LoadingSpinner.tsx`
    - Renders an accessible animated spinner; accepts an optional `size` prop
    - _Requirements: 2.8, 5.5, 7.3, 12.1_
  - [x] 6.2 Create `src/components/ui/EmptyState.tsx`
    - Accepts a `message: string` prop and renders a centred message container
    - _Requirements: 7.3, 7.4, 8.5, 11.14, 12.3_
  - [x] 6.3 Create `src/components/ui/ConfirmModal.tsx`
    - Accepts `open`, `message`, `loading`, `error`, `onConfirm`, `onCancel` props as defined in the design
    - Disables the Confirm button while `loading` is true; shows a `LoadingSpinner` inside it
    - Displays `error` inline if present
    - _Requirements: 10.2, 10.3, 10.6, 10.7, 11.9_

- [x] 7. Build the Navbar
  - [x] 7.1 Create `src/components/layout/Navbar.tsx`
    - Display the logged-in user's `first_name` and `last_name` read from `localStorage["user_profile"]`; fall back to empty string if absent
    - Render links to `/dashboard` and `/categories`, a Logout button, and a dark/light mode toggle (sun/moon icon)
    - Logout: call `useAuth().logout()` then `navigate("/login")`
    - Dark mode toggle: call `applyTheme(...)` to flip the current theme
    - Responsive: below `md` breakpoint hide links and toggle behind a hamburger `<button>`; toggle `menuOpen` state on click
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11_

- [x] 8. Build Dashboard components
  - [x] 8.1 Create the `useDashboardSummary` hook in `src/hooks/useDashboardSummary.ts`
    - Accepts `{ year, month, isAllTime }` and fetches `GET /transactions/summary?year=<year>&month=<month>` (skipped when `isAllTime` is true)
    - Returns `{ summary, loading, error, refetch }`
    - _Requirements: 5.2_
  - [x] 8.2 Create `src/components/dashboard/SummaryCards.tsx`
    - Renders three cards: Total Income (green), Total Expenses (red), Net Balance (blue or red based on sign)
    - Displays `LoadingSpinner` in each card body while `loading`; shows error banner spanning all three when `error` is set
    - Uses `formatCurrency` for all amounts
    - _Requirements: 5.1, 5.3, 5.4, 5.5, 5.6, 5.7_
  - [ ]* 8.3 Write property test for Summary Card Net Balance Colour Invariant
    - **Property 10: Summary Card Net Balance Colour Invariant**
    - **Validates: Requirements 5.4**
    - Generate arbitrary `MonthlySummary` objects with positive, negative, and zero `net` values; assert rendered Net Balance card uses red CSS classes for `net < 0` and blue for `net >= 0`
    - Tag: `// Feature: smart-expense-tracker-frontend, Property 10: Summary Card Net Balance Colour Invariant`
  - [x] 8.4 Create `src/components/dashboard/MonthPicker.tsx`
    - Implements the `MonthPickerProps` interface from the design
    - Formats month/year using `Intl.DateTimeFormat`
    - Disables the "next" button when the selected month equals the current calendar month
    - Disables both prev/next when `isAllTime` is true
    - Renders an "All Time" toggle button
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_
  - [ ]* 8.5 Write property test for Month Navigation Boundary Invariant
    - **Property 9: Month Navigation Boundary Invariant**
    - **Validates: Requirements 6.6**
    - Generate arbitrary `(year, month)` pairs; assert the "next" button `disabled` attribute matches whether the pair equals the current calendar month
    - Tag: `// Feature: smart-expense-tracker-frontend, Property 9: Month Navigation Boundary Invariant`
  - [x] 8.6 Create the `useTransactions` hook in `src/hooks/useTransactions.ts`
    - Accepts `{ year, month, isAllTime }` and fetches `GET /transactions` with appropriate `start_date`, `end_date`, `sort_by`, and `sort_order` parameters
    - Returns `{ transactions, loading, error, refetch }`
    - _Requirements: 8.1, 8.6_
  - [x] 8.7 Create `src/components/dashboard/BarChartWidget.tsx`
    - Uses Recharts `BarChart` with two bars: green for `totalIncome`, red for `totalExpense`
    - Renders labelled X and Y axes
    - Renders `EmptyState` when both values are zero
    - _Requirements: 7.1, 7.3, 7.6_
  - [x] 8.8 Create `src/components/dashboard/DonutChartWidget.tsx`
    - Uses Recharts `PieChart` with `innerRadius`
    - Accepts `transactions: Transaction[]`; filters to `type === "expense"`, groups by `category_id`, sums amounts
    - Renders a legend with category names
    - Renders `EmptyState` when there are no expense transactions
    - _Requirements: 7.2, 7.4, 7.5, 7.6_
  - [x] 8.9 Create `src/components/dashboard/TransactionList.tsx`
    - Implements the `TransactionListProps` interface from the design
    - Each row: date ("MMM D, YYYY"), description or "—", category name resolved from `categories` prop, amount
    - Colour-codes amount by type: green for income, red for expense
    - Renders skeleton rows (`LoadingSpinner`) while `loading`; `EmptyState` with "No transactions found for this period." when empty; inline error when `error` is set
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.7, 8.8_
  - [ ]* 8.10 Write property test for Transaction Amount Display Invariant
    - **Property 5: Transaction Amount Display Invariant**
    - **Validates: Requirements 8.3, 13.5**
    - Generate arbitrary `Transaction` arrays with random `type` values; render `TransactionList` and assert each row's amount element carries the correct green/red CSS class
    - Tag: `// Feature: smart-expense-tracker-frontend, Property 5: Transaction Amount Display Invariant`

- [x] 9. Build Transaction Form and deletion flow
  - [x] 9.1 Create `src/components/transactions/TransactionForm.tsx`
    - Implements the `TransactionFormProps` interface from the design
    - Fields: `amount` (numeric, 0.01–9,999,999,999.99), `date` (max = today), `type` dropdown, `category` dropdown (filtered by type, clears on type change), `description` (optional, max 255)
    - In create mode: all fields empty, date defaults to today
    - In edit mode: pre-populates all fields, shows Delete button
    - On type change: filters categories and clears category selection
    - Sends `POST /transactions` (create) or `PUT /transactions/{id}` (edit)
    - Handles 422 field-level errors and non-422 errors separately
    - Disables submit and shows `LoadingSpinner` in button while in-flight
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10, 9.11, 9.12, 9.13_
  - [ ]* 9.2 Write property test for Category Dropdown Filter Invariant
    - **Property 6: Category Dropdown Filter Invariant**
    - **Validates: Requirements 9.11**
    - Generate arbitrary `Category[]` arrays and random `type` selections; assert all rendered category dropdown options have `category_type === selectedType`
    - Tag: `// Feature: smart-expense-tracker-frontend, Property 6: Category Dropdown Filter Invariant`
  - [x] 9.3 Wire delete flow into `TransactionForm` and `TransactionList`
    - Delete button in `TransactionForm` (edit mode) and on each row in `TransactionList` opens `ConfirmModal`
    - On Confirm: send `DELETE /transactions/{id}`; on 204 close both modal and form (if open) and call `refetch`
    - While in-flight: disable Confirm button with `LoadingSpinner`
    - On error: display inline error in `ConfirmModal` without closing it
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 10. Assemble DashboardPage
  - [x] 10.1 Build `src/pages/DashboardPage.tsx`
    - Top-level state: `selectedYear`, `selectedMonth`, `isAllTime`; defaults to current calendar month/year on mount
    - Uses `useDashboardSummary`, `useTransactions`, and `useCategories` hooks
    - Renders `MonthPicker`, `SummaryCards` (hidden when `isAllTime`), `BarChartWidget`, `DonutChartWidget`, `TransactionList`, and an "Add Transaction" FAB/button
    - FAB opens `TransactionForm` in create mode; clicking a transaction row opens `TransactionForm` in edit mode; clicking delete opens `ConfirmModal`
    - On any successful mutation: calls all three `refetch` functions
    - _Requirements: 5.1–5.7, 6.1–6.8, 7.1–7.6, 8.1–8.8, 9.1–9.13, 10.1–10.7_

- [x] 11. Checkpoint — Verify Dashboard end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Build Category Management
  - [x] 12.1 Create the `useCategories` hook in `src/hooks/useCategories.ts`
    - Fetches `GET /categories/` on mount
    - Returns `{ categories, loading, error, refetch }`
    - _Requirements: 11.2_
  - [x] 12.2 Build `src/pages/CategoriesPage.tsx`
    - Inline create form at the top with `name` (max 100 chars, required) and `category_type` dropdown (required)
    - Category list: each row shows name, type badge (green for income, red for expense), Edit button, Delete button
    - Edit button opens an inline/modal edit form pre-populated with current values; submits `PUT /categories/{id}`
    - Delete button opens `ConfirmModal` with the cascade-warning message; on Confirm sends `DELETE /categories/{id}`
    - 409 error → display "A category with this name already exists." adjacent to the name field
    - Other errors → generic inline error at the top of the page
    - Empty list → `EmptyState` with "No categories yet. Create your first category above."
    - On any successful mutation: call `refetch`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 11.10, 11.11, 11.12, 11.13, 11.14_

- [x] 13. Polish: responsive layout and theming
  - [x] 13.1 Apply responsive Tailwind classes across all pages and components
    - All layouts must render without horizontal overflow from 320 px to 1920 px
    - Use `sm:`, `md:`, `lg:` breakpoint prefixes; verify Navbar collapses correctly at `md`
    - _Requirements: 4.10, 4.11, 13.1_
  - [x] 13.2 Apply dark mode Tailwind variants throughout all components
    - Use `dark:` variant classes on all backgrounds, text, and border colours
    - Verify WCAG AA contrast (4.5:1 minimum for normal text) in dark mode
    - Apply semantic colour palette consistently: `text-green-600 dark:text-green-400` for income, `text-red-500 dark:text-red-400` for expenses, `text-blue-600 dark:text-blue-400` for net balance
    - _Requirements: 13.2, 13.3, 13.4, 13.5_

- [x] 14. Final checkpoint — Full test suite
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Property tests use `fast-check` with `{ numRuns: 100 }` and must include the tag comment referencing the property number
- Unit and integration tests use Vitest + React Testing Library with `jsdom` environment
- The `useCategories` hook is shared between `DashboardPage` (category name resolution) and `CategoriesPage`
- All monetary amounts must go through `formatCurrency` — never format inline
- The `extractErrorMessage` utility must be used for all API error display — never access `err.response.data.detail` directly in components
- The `user_profile` key in `localStorage` must be kept in sync with the `access_token` key — both are set at login and removed at logout/401

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["2.1"] },
    { "id": 3, "tasks": ["2.2", "2.5", "2.7"] },
    { "id": 4, "tasks": ["2.3", "2.4", "2.6", "2.8"] },
    { "id": 5, "tasks": ["4.1", "6.1", "6.2", "6.3"] },
    { "id": 6, "tasks": ["4.2", "4.4", "7.1"] },
    { "id": 7, "tasks": ["4.3", "4.5", "4.6", "4.7"] },
    { "id": 8, "tasks": ["8.1", "8.4", "8.6", "12.1"] },
    { "id": 9, "tasks": ["8.2", "8.7", "8.8", "8.9", "9.1"] },
    { "id": 10, "tasks": ["8.3", "8.5", "8.10", "9.2", "9.3"] },
    { "id": 11, "tasks": ["10.1", "12.2"] },
    { "id": 12, "tasks": ["13.1", "13.2"] }
  ]
}
```
