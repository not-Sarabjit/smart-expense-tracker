import { useState, useEffect, useMemo } from "react";
import { updateMe } from "../api/users";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { extractErrorMessage } from "../utils/errorHandling";
import { formatMoney } from "../utils/formatters";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import type { UserPreferencesUpdatePayload } from "../types";

/** Currencies offered in the picker; the user's current code is always added if missing. */
const COMMON_CURRENCIES = [
  "INR", "USD", "EUR", "GBP", "AED", "AUD", "CAD", "CHF", "CNY", "JPY", "SGD", "ZAR",
];

const FALLBACK_TIMEZONES = [
  "Asia/Kolkata", "UTC", "Europe/London", "Europe/Berlin", "America/New_York",
  "America/Los_Angeles", "Asia/Dubai", "Asia/Singapore", "Asia/Tokyo", "Australia/Sydney",
];

/** All IANA zones the browser knows (Intl.supportedValuesOf), or a short fallback list. */
function availableTimezones(): string[] {
  const intl = Intl as unknown as { supportedValuesOf?: (key: string) => string[] };
  try {
    const zones = intl.supportedValuesOf?.("timeZone");
    // Some runtimes list only region zones; UTC is always a valid choice
    if (zones && zones.length > 0) return zones.includes("UTC") ? zones : ["UTC", ...zones];
  } catch {
    // fall through
  }
  return FALLBACK_TIMEZONES;
}

/** Adds `value` to `options` if it isn't there (so the current setting is always selectable). */
function withValue(options: string[], value: string | undefined): string[] {
  return value && !options.includes(value) ? [value, ...options] : options;
}

const inputClass =
  "w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500";
const labelClass = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1";

/**
 * SettingsPage — profile name plus currency and timezone preferences,
 * read from and saved to GET/PATCH /users/me.
 */
export default function SettingsPage() {
  const { user, loading, error: loadError, setUser } = useCurrentUser();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [currency, setCurrency] = useState("");
  const [timezone, setTimezone] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Populate the form whenever the loaded profile changes
  useEffect(() => {
    if (!user) return;
    setFirstName(user.first_name);
    setLastName(user.last_name ?? "");
    setCurrency(user.currency);
    setTimezone(user.timezone);
  }, [user]);

  const currencyOptions = useMemo(() => withValue(COMMON_CURRENCIES, currency), [currency]);
  const timezoneOptions = useMemo(() => withValue(availableTimezones(), timezone), [timezone]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!user) return;

    if (!firstName.trim()) {
      setSaveError("First name is required.");
      return;
    }

    // Send only what changed
    const payload: UserPreferencesUpdatePayload = {};
    if (firstName.trim() !== user.first_name) payload.first_name = firstName.trim();
    if (lastName.trim() !== (user.last_name ?? "")) payload.last_name = lastName.trim();
    if (currency !== user.currency) payload.currency = currency;
    if (timezone !== user.timezone) payload.timezone = timezone;

    setSaved(false);
    setSaveError(null);
    if (Object.keys(payload).length === 0) {
      setSaved(true);
      return;
    }

    setSaving(true);
    try {
      setUser(await updateMe(payload));
      setSaved(true);
    } catch (err) {
      setSaveError(extractErrorMessage(err, "Failed to save settings."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <main className="mx-auto max-w-2xl px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>

        {loading && !user && (
          <div className="flex justify-center py-10">
            <LoadingSpinner size={8} />
          </div>
        )}

        {!loading && loadError && !user && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 px-4 py-3 text-sm text-red-600 dark:text-red-400"
          >
            {loadError}
          </div>
        )}

        {user && (
          <form
            onSubmit={handleSubmit}
            noValidate
            className="rounded-2xl bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700 p-6 space-y-5"
          >
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Signed in as <span className="font-medium">{user.email}</span>
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="settings-first-name" className={labelClass}>
                  First name
                </label>
                <input
                  id="settings-first-name"
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label htmlFor="settings-last-name" className={labelClass}>
                  Last name
                </label>
                <input
                  id="settings-last-name"
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>

            <div>
              <label htmlFor="settings-currency" className={labelClass}>
                Currency
              </label>
              <select
                id="settings-currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className={inputClass}
              >
                {currencyOptions.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Amounts are shown like {formatMoney(1234.5, currency || "INR")}
              </p>
            </div>

            <div>
              <label htmlFor="settings-timezone" className={labelClass}>
                Timezone
              </label>
              <select
                id="settings-timezone"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className={inputClass}
              >
                {timezoneOptions.map((zone) => (
                  <option key={zone} value={zone}>
                    {zone}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Used to work out dates like “today” and “this month”.
              </p>
            </div>

            {saveError && (
              <p role="alert" className="text-sm text-red-600 dark:text-red-400">
                {saveError}
              </p>
            )}
            {saved && !saveError && (
              <p role="status" className="text-sm text-green-600 dark:text-green-400">
                Settings saved.
              </p>
            )}

            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 px-4 py-2 text-sm font-semibold text-white transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              {saving && <LoadingSpinner size={4} />}
              Save settings
            </button>
          </form>
        )}
      </main>
    </div>
  );
}
