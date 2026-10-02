import { describe, it, expect } from 'vitest';
import axios from 'axios';
import { extractErrorMessage, NETWORK_ERROR_MESSAGE } from './errorHandling';

function makeAxiosError(detail: unknown, status = 400) {
  const err = new axios.AxiosError('Request failed');
  err.response = {
    data: { detail },
    status,
    statusText: 'Bad Request',
    headers: {},
    config: {} as never,
  };
  return err;
}

describe('extractErrorMessage', () => {
  it('returns the detail string from an Axios error', () => {
    const err = makeAxiosError('Invalid credentials.');
    expect(extractErrorMessage(err)).toBe('Invalid credentials.');
  });

  it('joins FastAPI array detail messages with comma-space', () => {
    const detail = [
      { msg: 'field required', loc: ['body', 'email'], type: 'missing' },
      { msg: 'value is not a valid email', loc: ['body', 'email'], type: 'value_error' },
    ];
    const err = makeAxiosError(detail);
    expect(extractErrorMessage(err)).toBe('field required, value is not a valid email');
  });

  it('returns the fallback for a plain Error (non-Axios)', () => {
    expect(extractErrorMessage(new Error('oops'))).toBe('Something went wrong.');
  });

  it('returns a custom fallback when provided', () => {
    expect(extractErrorMessage(new Error('oops'), 'Custom fallback.')).toBe('Custom fallback.');
  });

  it('returns fallback when detail is undefined', () => {
    const err = makeAxiosError(undefined);
    expect(extractErrorMessage(err)).toBe('Something went wrong.');
  });

  it('returns fallback for null input', () => {
    expect(extractErrorMessage(null)).toBe('Something went wrong.');
  });

  it("returns the message from a domain (AppException) error body", () => {
    const err = new axios.AxiosError("Request failed");
    err.response = {
      data: { error: true, message: "Category is used by 3 transaction(s).", status_code: 409 },
      status: 409,
      statusText: "Conflict",
      headers: {},
      config: {} as never,
    };
    expect(extractErrorMessage(err)).toBe("Category is used by 3 transaction(s).");
  });

  it("returns a network message when there is no response", () => {
    const err = new axios.AxiosError("Network Error");
    expect(extractErrorMessage(err)).toBe(NETWORK_ERROR_MESSAGE);
  });
});
