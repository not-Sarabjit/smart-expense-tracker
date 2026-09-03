import { describe, it, expect, beforeEach } from 'vitest';
import { applyTheme, readTheme } from './theme';

describe('applyTheme', () => {
  beforeEach(() => {
    // Reset state before each test
    document.documentElement.classList.remove('dark');
    localStorage.clear();
  });

  it('adds the dark class to <html> when theme is "dark"', () => {
    applyTheme('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('removes the dark class from <html> when theme is "light"', () => {
    document.documentElement.classList.add('dark');
    applyTheme('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('persists "dark" to localStorage when applying dark theme', () => {
    applyTheme('dark');
    expect(localStorage.getItem('theme')).toBe('dark');
  });

  it('persists "light" to localStorage when applying light theme', () => {
    applyTheme('light');
    expect(localStorage.getItem('theme')).toBe('light');
  });

  it('keeps class and localStorage consistent after toggling dark → light', () => {
    applyTheme('dark');
    applyTheme('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorage.getItem('theme')).toBe('light');
  });

  it('keeps class and localStorage consistent after toggling light → dark', () => {
    applyTheme('light');
    applyTheme('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorage.getItem('theme')).toBe('dark');
  });
});

describe('readTheme', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns "light" when localStorage has no theme key', () => {
    expect(readTheme()).toBe('light');
  });

  it('returns "dark" when localStorage["theme"] is "dark"', () => {
    localStorage.setItem('theme', 'dark');
    expect(readTheme()).toBe('dark');
  });

  it('returns "light" when localStorage["theme"] is "light"', () => {
    localStorage.setItem('theme', 'light');
    expect(readTheme()).toBe('light');
  });

  it('returns "light" for an unrecognised stored value', () => {
    localStorage.setItem('theme', 'blue');
    expect(readTheme()).toBe('light');
  });
});
