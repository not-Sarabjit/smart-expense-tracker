import { describe, it, expect } from 'vitest';
import { formatCurrency, formatDate } from './formatters';

describe('formatCurrency', () => {
  it('formats zero with two decimal places', () => {
    expect(formatCurrency(0)).toBe('$0.00');
  });

  it('formats a whole number with two decimal places', () => {
    expect(formatCurrency(100)).toBe('$100.00');
  });

  it('formats a number with one decimal with two decimal places', () => {
    expect(formatCurrency(9.5)).toBe('$9.50');
  });

  it('formats a number with two decimals correctly', () => {
    expect(formatCurrency(1234.56)).toBe('$1,234.56');
  });

  it('rounds to two decimal places', () => {
    // 0.999 rounds to 1.00
    expect(formatCurrency(0.999)).toBe('$1.00');
  });

  it('formats large numbers with comma separators', () => {
    expect(formatCurrency(1000000)).toBe('$1,000,000.00');
  });

  it('always ends with a decimal point followed by exactly two digits', () => {
    const values = [0.1, 0.01, 99.9, 1000.5, 0.005];
    for (const v of values) {
      expect(formatCurrency(v)).toMatch(/\.\d{2}$/);
    }
  });

  it('uses a custom currency symbol when provided', () => {
    expect(formatCurrency(50, '€')).toBe('€50.00');
  });
});

describe('formatDate', () => {
  it('formats a YYYY-MM-DD string as "MMM D, YYYY"', () => {
    expect(formatDate('2025-06-05')).toBe('Jun 5, 2025');
  });

  it('formats the first day of the year correctly', () => {
    expect(formatDate('2024-01-01')).toBe('Jan 1, 2024');
  });

  it('formats December 31 correctly', () => {
    expect(formatDate('2023-12-31')).toBe('Dec 31, 2023');
  });

  it('does not shift dates due to timezone offset', () => {
    // "2025-03-15" should always be Mar 15, not Mar 14 in any timezone
    expect(formatDate('2025-03-15')).toBe('Mar 15, 2025');
  });
});
