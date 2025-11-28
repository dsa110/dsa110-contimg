/**
 * Unit tests for throttle and debounce utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { throttle, debounce } from "../throttle";

describe("throttle", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should call function immediately on first call", () => {
    const func = vi.fn();
    const throttled = throttle(func, 100);

    throttled("arg1");

    expect(func).toHaveBeenCalledTimes(1);
    expect(func).toHaveBeenCalledWith("arg1");
  });

  it("should throttle rapid calls", () => {
    const func = vi.fn();
    const throttled = throttle(func, 100);

    throttled("call1");
    throttled("call2");
    throttled("call3");

    expect(func).toHaveBeenCalledTimes(1);
    expect(func).toHaveBeenCalledWith("call1");

    // Advance time past delay
    vi.advanceTimersByTime(100);

    expect(func).toHaveBeenCalledTimes(2);
    expect(func).toHaveBeenCalledWith("call3");
  });

  it("should schedule delayed call when called within delay period", () => {
    const func = vi.fn();
    const throttled = throttle(func, 100);

    throttled("call1");
    vi.advanceTimersByTime(50); // Within delay
    throttled("call2");

    expect(func).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(50); // Complete delay
    expect(func).toHaveBeenCalledTimes(2);
    expect(func).toHaveBeenCalledWith("call2");
  });

  it("should preserve function context", () => {
    const obj = {
      value: 42,
      method: function (this: { value: number }) {
        return this.value;
      },
    };

    const methodSpy = vi.fn(obj.method.bind(obj));
    const throttled = throttle(methodSpy, 100);
    throttled();

    expect(methodSpy).toHaveBeenCalled();
    expect(methodSpy.mock.results[0].value).toBe(42);
  });

  it("should handle multiple arguments", () => {
    const func = vi.fn();
    const throttled = throttle(func, 100);

    throttled("arg1", "arg2", "arg3");

    expect(func).toHaveBeenCalledWith("arg1", "arg2", "arg3");
  });

  it("should cancel pending timeout when new call arrives", () => {
    const func = vi.fn();
    const throttled = throttle(func, 100);

    throttled("call1");
    expect(func).toHaveBeenCalledTimes(1);
    expect(func).toHaveBeenCalledWith("call1");

    vi.advanceTimersByTime(50); // Within delay period
    throttled("call2"); // Should cancel call1's pending call and schedule call2

    // call1 already executed, call2 is scheduled
    expect(func).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(50); // Complete delay for call2
    expect(func).toHaveBeenCalledTimes(2);
    expect(func).toHaveBeenCalledWith("call2");
  });
});

describe("debounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should not call function immediately", () => {
    const func = vi.fn();
    const debounced = debounce(func, 100);

    debounced("arg1");

    expect(func).not.toHaveBeenCalled();
  });

  it("should call function after delay", () => {
    const func = vi.fn();
    const debounced = debounce(func, 100);

    debounced("arg1");
    vi.advanceTimersByTime(100);

    expect(func).toHaveBeenCalledTimes(1);
    expect(func).toHaveBeenCalledWith("arg1");
  });

  it("should reset delay on each call", () => {
    const func = vi.fn();
    const debounced = debounce(func, 100);

    debounced("call1");
    vi.advanceTimersByTime(50);
    debounced("call2");
    vi.advanceTimersByTime(50);
    debounced("call3");
    vi.advanceTimersByTime(50);

    expect(func).not.toHaveBeenCalled();

    vi.advanceTimersByTime(50); // Complete delay from call3
    expect(func).toHaveBeenCalledTimes(1);
    expect(func).toHaveBeenCalledWith("call3");
  });

  it("should preserve function context", () => {
    const obj = {
      value: 42,
      method: function (this: { value: number }) {
        return this.value;
      },
    };

    const methodSpy = vi.fn(obj.method.bind(obj));
    const debounced = debounce(methodSpy, 100);
    debounced();
    vi.advanceTimersByTime(100);

    expect(methodSpy).toHaveBeenCalled();
    expect(methodSpy.mock.results[0].value).toBe(42);
  });

  it("should handle multiple arguments", () => {
    const func = vi.fn();
    const debounced = debounce(func, 100);

    debounced("arg1", "arg2", "arg3");
    vi.advanceTimersByTime(100);

    expect(func).toHaveBeenCalledWith("arg1", "arg2", "arg3");
  });

  it("should cancel previous timeout on new call", () => {
    const func = vi.fn();
    const debounced = debounce(func, 100);

    debounced("call1");
    vi.advanceTimersByTime(50);
    debounced("call2");
    vi.advanceTimersByTime(50);
    debounced("call3");
    vi.advanceTimersByTime(100);

    expect(func).toHaveBeenCalledTimes(1);
    expect(func).toHaveBeenCalledWith("call3");
  });
});
