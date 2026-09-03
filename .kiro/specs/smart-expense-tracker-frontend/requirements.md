# Requirements Document

## Introduction

The Smart Expense Tracker Frontend is a React + TypeScript single-page application that provides users with a clean, responsive interface to track their personal income and expenses. It communicates with an existing FastAPI backend via a REST API, supporting JWT-based authentication, full transaction and category CRUD, and a dashboard with charts and monthly summaries.

## Glossary

- **App**: The React + TypeScript + Vite frontend application running at `http://localhost:3000`.
- **API**: The FastAPI backend reachable at `http://localhost:3000/api/v1`.
- **AuthService**: The frontend module that manages JWT tokens and provides authenticated Axios requests.
- **Router**: The client-side React Router that controls which page is rendered.
- **Dashboard**: The main authenticated page showing financial summaries, charts, and recent transactions.
- **TransactionForm**: The modal/form component used to create or edit a transaction.
- **CategoryManager**: The page/section used to create, edit, and delete categories.
- **Token**: The JWT access token returned by the API on login, stored in `localStorage`.
- **ProtectedRoute**: A React Router wrapper that redirects unauthenticated users to the login page.
- **Summary**: The API response `{ total_income, total_expense, net }` scoped to a given month and year.
- **MonthPicker**: The UI control on the Dashboard for navigating between months.
- **LoadingState**: A visual indicator (spinner or skeleton) shown while an API call is in progress.
- **EmptyState**: A message or illustration shown when a data list is empty.
- **DarkMode**: The dark colour theme toggled by the user and persisted in `localStorage`.

---

## Requirements

### Requirement 1: Project Bootstrap and Configuration

**User Story:** As a developer, I want the Vite project configured correctly, so that the app runs on port 3000 with Tailwind CSS, Recharts, and Axios available.

#### Acceptance Criteria

1. THE App SHALL be bootstrapped with Vite, React, and TypeScript, with the frontend source code located in a `frontend/` directory at the workspace root.
2. THE App SHALL run on port 3000 as configured via the `server.port` field in `vite.config.ts`.
3. THE App SHALL include Tailwind CSS installed as a PostCSS plugin, with a `tailwind.config.ts` file that includes the `./src/**/*.{ts,tsx}` content glob, and `@tailwind base`, `@tailwind components`, and `@tailwind utilities` directives imported in the global stylesheet.
4. THE App SHALL declare `recharts`, `axios`, and `react-router-dom` as runtime dependencies in `package.json`.
5. THE App SHALL export a single Axios instance (`apiClient`) from a shared module (e.g. `src/api/client.ts`) configured with `baseURL` set to `http://localhost:3000/api/v1`.
6. WHEN the Token key `access_token` exists in `localStorage`, THE `apiClient` request interceptor SHALL attach the header `Authorization: Bearer <token>` to every outgoing request.
7. WHEN the Token key `access_token` does not exist in `localStorage`, THE `apiClient` request interceptor SHALL send the request without an `Authorization` header.

---

### Requirement 2: Authentication — Login and Registration

**User Story:** As a new or returning user, I want a single auth page where I can log in or register, so that I can securely access my expense data.

#### Acceptance Criteria

1. THE App SHALL render a single Auth page at the `/login` route containing both a Login form and a Sign-Up form toggled by a UI control (e.g. tab or link).
2. WHEN the user selects the Login form, THE App SHALL display fields for `email` and `password`.
3. WHEN the user selects the Sign-Up form, THE App SHALL display fields for `first_name`, `last_name`, `email`, and `password`.
4. WHEN the user submits the Login form with a non-empty email that matches the RFC 5322 format and a non-empty password, THE AuthService SHALL send `POST /auth/login` and store the returned `access_token` in `localStorage` under the key `access_token`.
5. WHEN the user submits the Sign-Up form with all required fields non-empty and the email matching the RFC 5322 format, THE AuthService SHALL send `POST /auth/register` and, on a 201 response, automatically call `POST /auth/login` with the same `email` and `password` credentials.
6. WHEN login or registration succeeds, THE Router SHALL redirect the user to `/dashboard`.
7. IF the API returns an error during login or registration, THEN THE App SHALL display the `detail` field from the error response body as an inline error message below the form's submit button, without navigating away.
8. WHILE an auth API call is in progress, THE App SHALL disable the submit button and render a LoadingState indicator inside or adjacent to the submit button.
9. WHEN the user attempts to submit the Login or Sign-Up form and any required field is empty, THE App SHALL display an inline validation message adjacent to each empty field without sending an API request.
10. IF the automatic login call following a successful registration returns an error, THEN THE App SHALL display that error message inline on the form and remain on the `/login` page.

---

### Requirement 3: Protected Routes and Session Management

**User Story:** As an authenticated user, I want my session to be protected, so that unauthenticated users cannot access my data pages.

#### Acceptance Criteria

1. THE Router SHALL wrap all routes except `/login` in a ProtectedRoute component that checks for the presence of the `access_token` key in `localStorage`.
2. WHEN an unauthenticated user (no `access_token` in `localStorage`) navigates to any protected route, THE Router SHALL immediately redirect them to `/login`.
3. WHEN an authenticated user (valid `access_token` in `localStorage`) navigates to `/login`, THE Router SHALL immediately redirect them to `/dashboard`.
4. WHEN the user clicks the Logout button, THE AuthService SHALL remove the `access_token` key from `localStorage` and THE Router SHALL redirect to `/login`.
5. IF the API returns an HTTP 401 response on any request, THEN THE `apiClient` response interceptor SHALL remove the `access_token` key from `localStorage` and redirect the browser to `/login`.

---

### Requirement 4: Navigation and Layout

**User Story:** As an authenticated user, I want a consistent navigation bar, so that I can access all major sections of the app and see who is logged in.

#### Acceptance Criteria

1. THE App SHALL render a top navigation bar on all pages that require authentication.
2. THE App SHALL display the logged-in user's `first_name` and `last_name` (retrieved from the stored user profile) in the navigation bar.
3. THE App SHALL include a link to `/dashboard` labelled "Dashboard" in the navigation bar.
4. THE App SHALL include a link to `/categories` labelled "Categories" in the navigation bar.
5. THE App SHALL include a Logout button in the navigation bar that triggers the logout flow defined in Requirement 3.
6. THE App SHALL include a dark/light mode toggle button (with a visible sun/moon icon or equivalent) in the navigation bar.
7. WHEN the user activates the dark mode toggle, THE App SHALL add the `dark` CSS class to the root `<html>` element and persist the value `"dark"` to `localStorage` under the key `theme`.
8. WHEN the user deactivates the dark mode toggle (switching back to light mode), THE App SHALL remove the `dark` CSS class from the root `<html>` element and persist the value `"light"` to `localStorage` under the key `theme`.
9. WHEN the App loads, IF `localStorage` contains the key `theme` with value `"dark"`, THEN THE App SHALL apply dark mode immediately; otherwise THE App SHALL default to light mode.
10. WHILE the viewport width is less than 768 px, THE App SHALL hide the navigation links and dark mode toggle behind a hamburger menu button.
11. WHEN the user clicks the hamburger menu button, THE App SHALL toggle the navigation links and dark mode toggle between visible and hidden states.

---

### Requirement 5: Dashboard — Monthly Summary Cards

**User Story:** As a user, I want to see my financial summary for the selected month, so that I can quickly understand my income, expenses, and net balance.

#### Acceptance Criteria

1. THE Dashboard SHALL display three summary cards: Total Income, Total Expenses, and Net Balance.
2. WHEN the Dashboard loads or the selected month changes, THE Dashboard SHALL fetch `GET /transactions/summary?year=<year>&month=<month>` for the currently selected month.
3. THE Dashboard SHALL display Total Income in green, Total Expenses in red, and Net Balance in blue.
4. IF the net value returned by the API is less than zero, THEN THE Dashboard SHALL display the Net Balance amount in red instead of blue.
5. WHILE the summary API call is in progress, THE Dashboard SHALL render a LoadingState indicator within each of the three summary cards in place of the amount values.
6. IF the summary API call returns an error response, THEN THE Dashboard SHALL display a single inline error message spanning all three cards in place of the amount values.
7. THE Dashboard SHALL display all monetary amounts with exactly two decimal places and the user's currency symbol (defaulting to `$`).

---

### Requirement 6: Dashboard — Month Navigation

**User Story:** As a user, I want to navigate between months on the Dashboard, so that I can review my finances for any past month.

#### Acceptance Criteria

1. THE Dashboard SHALL include a MonthPicker displaying the currently selected month and year in the format "MMMM YYYY" (e.g. "June 2025").
2. THE MonthPicker SHALL include a "previous month" (`<`) button and a "next month" (`>`) button flanking the month/year label.
3. WHEN the user clicks the "previous month" button, THE Dashboard SHALL decrement the selected month by one calendar month and re-fetch the summary, chart, and transaction data.
4. WHEN the user clicks the "next month" button, THE Dashboard SHALL increment the selected month by one calendar month and re-fetch the summary, chart, and transaction data.
5. THE Dashboard SHALL default to the current calendar month on first load, determined by the client's local date.
6. THE MonthPicker "next month" button SHALL be disabled when the selected month equals the current calendar month.
7. THE MonthPicker SHALL include an "All Time" toggle button. IF the user activates the "All Time" toggle, THEN THE Dashboard SHALL hide the three summary cards, disable the previous/next month buttons, and re-fetch transactions without any date filtering.
8. IF the user deactivates the "All Time" toggle, THEN THE Dashboard SHALL restore the previously selected month, re-enable the previous/next month buttons, show the summary cards, and re-fetch data for the restored month.

---

### Requirement 7: Dashboard — Charts

**User Story:** As a user, I want visual charts of my finances, so that I can understand my spending patterns at a glance.

#### Acceptance Criteria

1. THE Dashboard SHALL render a Recharts `BarChart` with two bars per chart: one for Total Income (green) and one for Total Expenses (red), using the summary data for the selected month.
2. THE Dashboard SHALL render a Recharts `PieChart` (donut style) where each slice represents one expense category, with the slice size proportional to that category's total expense amount relative to all expense transactions in the selected period.
3. WHEN there are no transactions for the selected period, THE Dashboard SHALL display an EmptyState message in place of the bar chart.
4. WHEN there are no expense transactions for the selected period, THE Dashboard SHALL display an EmptyState message in place of the donut chart.
5. WHEN the selected month changes or the "All Time" toggle state changes, THE Dashboard SHALL re-render both charts with the updated data.
6. THE bar chart SHALL include labelled X and Y axes, and the donut chart SHALL include a legend displaying each category name alongside its colour.

---

### Requirement 8: Dashboard — Recent Transactions List

**User Story:** As a user, I want to see my recent transactions on the Dashboard, so that I can review activity without navigating away.

#### Acceptance Criteria

1. WHEN the Dashboard loads or the selected month changes, THE Dashboard SHALL fetch `GET /transactions` with `start_date` set to the first day of the selected month and `end_date` set to the last day of the selected month, and `sort_by=date&sort_order=desc`.
2. THE Dashboard SHALL display each transaction row with: date (formatted as "MMM D, YYYY"), description (or a dash if absent), category name (resolved from the loaded categories list), and amount.
3. THE Dashboard SHALL colour-code each transaction's amount: green text for `type === "income"`, red text for `type === "expense"`.
4. THE Dashboard SHALL render the transaction list sorted by date descending (newest first), relying on the API's `sort_order=desc` parameter.
5. WHEN there are no transactions for the selected period, THE Dashboard SHALL display an EmptyState component with the message "No transactions found for this period."
6. WHEN the "All Time" toggle is active, THE Dashboard SHALL fetch `GET /transactions` with `sort_by=date&sort_order=desc` and no `start_date` or `end_date` parameters.
7. WHILE the transactions fetch is in progress, THE Dashboard SHALL render a LoadingState in place of the transaction list.
8. IF the transactions fetch returns an error, THE Dashboard SHALL display an inline error message in place of the transaction list.

---

### Requirement 9: Transaction Management — Create and Edit

**User Story:** As a user, I want to add and edit transactions through a form, so that I can keep my financial records up to date.

#### Acceptance Criteria

1. THE Dashboard SHALL display an "Add Transaction" floating action button (FAB) or header button that is always visible while the Dashboard is rendered.
2. WHEN the user clicks "Add Transaction", THE TransactionForm SHALL open as a modal dialog with all fields empty and the `date` field defaulting to today's date.
3. THE TransactionForm SHALL include fields for: `amount` (numeric input, must be between 0.01 and 9,999,999,999.99), `date` (date picker, maximum value = today's date), `type` (dropdown with options "income" and "expense"), `category` (dropdown), and `description` (optional text input, maximum 255 characters).
4. WHEN the user submits the TransactionForm with all required fields valid, THE App SHALL send `POST /transactions` with the JSON body `{ "amount": <number>, "date": "<YYYY-MM-DD>", "type": "<income|expense>", "category_id": <id>, "description": <string|null> }`.
5. WHEN the user clicks on an existing transaction row, THE TransactionForm SHALL open as a modal dialog pre-populated with that transaction's current `amount`, `date`, `type`, `category_id`, and `description`.
6. WHEN the user submits the TransactionForm while editing an existing transaction, THE App SHALL send `PUT /transactions/{id}` with only the fields that have changed (using `exclude_unset` semantics).
7. WHEN a create or update operation returns a success response, THE App SHALL close the modal and re-fetch the Dashboard summary, chart, and transaction data.
8. IF the API returns a 422 validation error, THEN THE TransactionForm SHALL display the validation error message(s) below the affected field(s) without closing the modal.
9. IF the API returns a non-422 error (e.g. 500 or network failure), THEN THE TransactionForm SHALL display a generic error message at the top of the modal without closing it.
10. WHILE a create or update API call is in progress, THE TransactionForm SHALL disable the submit button and render a LoadingState indicator inside the button.
11. WHEN the user changes the `type` dropdown value, THE TransactionForm SHALL filter the category dropdown to show only categories whose `category_type` matches the newly selected type, and SHALL clear any previously selected category value.
12. IF the `GET /categories/` call fails when the TransactionForm opens, THEN THE TransactionForm SHALL display an error message and disable the category dropdown and submit button.
13. WHEN the user selects a `type` and no categories of that type exist, THE TransactionForm SHALL display a message in the category dropdown area indicating no categories are available and SHALL disable the submit button.

---

### Requirement 10: Transaction Management — Delete

**User Story:** As a user, I want to delete transactions I created by mistake, so that my records remain accurate.

#### Acceptance Criteria

1. THE App SHALL display a Delete button both on each transaction row in the Dashboard list and within the TransactionForm when it is open in edit mode.
2. WHEN the user clicks a Delete button, THE App SHALL open a confirmation modal dialog with a message asking the user to confirm deletion and two buttons: "Confirm" and "Cancel".
3. WHEN the user clicks "Cancel" in the confirmation modal, THE App SHALL close the modal without sending any API request and without modifying the transaction list.
4. WHEN the user clicks "Confirm" in the confirmation modal, THE App SHALL send `DELETE /transactions/{id}`.
5. WHEN the deletion API call returns a 204 response, THE App SHALL close both the confirmation modal and the TransactionForm (if open) and re-fetch the Dashboard summary, chart, and transaction data.
6. WHILE the deletion API call is in progress, THE App SHALL disable the "Confirm" button in the confirmation modal and render a LoadingState indicator inside it.
7. IF the deletion API call returns an error response, THEN THE App SHALL display an inline error message within the confirmation modal without closing it and without modifying the local transaction list.

---

### Requirement 11: Category Management

**User Story:** As a user, I want to manage my income and expense categories, so that I can organise my transactions meaningfully.

#### Acceptance Criteria

1. THE App SHALL render a Categories page at the `/categories` route, accessible via the navigation bar link.
2. WHEN the Categories page loads, THE App SHALL fetch and display all user categories via `GET /categories/`.
3. THE App SHALL display each category as a card or row showing its `name` and a `category_type` badge styled distinctly for "income" (e.g. green badge) versus "expense" (e.g. red badge).
4. THE CategoryManager SHALL include a form with a `name` text input (maximum 100 characters, required) and a `category_type` dropdown (options: "income", "expense", required) for creating a new category.
5. WHEN the user submits the create form with a non-empty `name` (≤ 100 characters) and a selected `category_type`, THE App SHALL send `POST /categories/create_category` with `{ "name": "<name>", "category_type": "<type>" }`.
6. WHEN the user clicks an "Edit" button on a category row, THE App SHALL open an edit form (inline or modal) pre-populated with that category's current `name` and `category_type`.
7. WHEN the user submits the edit form, THE App SHALL send `PUT /categories/{id}` with the updated `name` and/or `category_type` fields.
8. THE App SHALL display a Delete button for each category row.
9. WHEN the user clicks the Delete button on a category, THE App SHALL display a confirmation dialog with the message "Deleting this category may affect existing transactions linked to it. Are you sure?" and "Confirm" / "Cancel" buttons.
10. WHEN the user clicks "Confirm" in the category delete dialog, THE App SHALL send `DELETE /categories/{id}`.
11. WHEN any category CRUD operation returns a success response, THE App SHALL re-fetch and re-render the full category list.
12. IF a category API call returns a 409 conflict error (duplicate name), THEN THE App SHALL display the message "A category with this name already exists." adjacent to the `name` field.
13. IF a category API call returns any other error response, THEN THE App SHALL display a generic inline error message at the top of the Categories page.
14. WHEN the category list is empty, THE App SHALL display an EmptyState component with the message "No categories yet. Create your first category above."

---

### Requirement 12: UI/UX — Loading, Error, and Empty States

**User Story:** As a user, I want clear feedback during loading, errors, and empty data states, so that I always know the current status of the application.

#### Acceptance Criteria

1. WHILE any API call is in progress, THE App SHALL render a LoadingState (as defined in the Glossary — a spinner or skeleton) within the section of the UI that is awaiting data, replacing the content area of that section.
2. IF any API call returns an HTTP error response or a network error, THEN THE App SHALL display a human-readable error message (not a raw status code or exception stack trace) within the same section of the UI that initiated the request.
3. WHEN a data list (transactions or categories) contains zero items, THE App SHALL render an EmptyState component in place of the list, containing at minimum a brief descriptive message specific to the list type (e.g. "No transactions found" vs "No categories yet").
4. WHEN a create, update, or delete operation returns a success response, THE App SHALL immediately re-fetch the affected data and replace any previously displayed data with the newly fetched results before removing the LoadingState.

---

### Requirement 13: UI/UX — Responsive Design and Theming

**User Story:** As a user, I want the app to look good on both mobile and desktop and support dark mode, so that I can use it on any device in any environment.

#### Acceptance Criteria

1. THE App SHALL implement a responsive layout using Tailwind CSS utility classes that renders without horizontal scrolling or overflow on viewport widths from 320 px to 1920 px.
2. THE App SHALL include a visible toggle control (sun/moon icon or equivalent label) that switches between light mode and dark mode.
3. WHEN the user activates dark mode, THE App SHALL apply Tailwind's `dark` variant classes such that all pages render with a dark background and foreground text that meets WCAG AA contrast ratio (minimum 4.5:1 for normal text).
4. WHEN the App initialises, IF `localStorage` contains `theme: "dark"`, THEN THE App SHALL activate dark mode immediately before first render; otherwise THE App SHALL default to light mode.
5. THE App SHALL use the following semantic colour assignments consistently across all pages: green (`text-green-600` / `dark:text-green-400`) for income amounts, red (`text-red-500` / `dark:text-red-400`) for expense amounts, and blue (`text-blue-600` / `dark:text-blue-400`) for net balance amounts.

---

## Backend Flag

> ⚠️ **Backend change required — Default Category Seeding**: The backend currently does not seed default categories when a new user registers. To improve new-user experience, the backend should create a default set of categories (e.g. Salary, Food, Transport, Entertainment, Utilities, Healthcare) for each new user upon first registration (`POST /auth/register`). This is a backend-only change and is flagged here for the backend team.
