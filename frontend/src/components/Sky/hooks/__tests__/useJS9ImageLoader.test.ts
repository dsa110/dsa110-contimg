/**
 * Unit Tests for useJS9ImageLoader Hook
 * 
 * Tests:
 * 1. Image loading when path changes
 * 2. Loading state management
 * 3. Error handling
 * 4. Image cleanup before loading new image
 * 5. Cache busting
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useJS9ImageLoader } from '../useJS9ImageLoader';

// Setup window.JS9 for tests
(global as any).window = {
  JS9: {},
};

// Mock logger
vi.mock('../../../../utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock JS9 utilities
vi.mock('../../../../utils/js9', () => ({
  isJS9Available: vi.fn(() => true),
  findDisplay: vi.fn(() => null),
}));

// Mock JS9Service
const { mockJS9Service } = vi.hoisted(() => {
  return {
    mockJS9Service: {
      isAvailable: vi.fn(() => true),
      closeImage: vi.fn(),
      loadImage: vi.fn(),
      resizeDisplay: vi.fn(),
      setDisplay: vi.fn(),
    },
  };
});

vi.mock('../../../../services/js9', () => ({
  js9Service: mockJS9Service,
}));

// Mock JS9Context
const mockGetDisplaySafe = vi.fn(() => null);

vi.mock('../../../../contexts/JS9Context', () => ({
  useJS9Safe: vi.fn(() => ({
    isJS9Ready: true,
    getDisplay: mockGetDisplaySafe,
  })),
}));

describe('useJS9ImageLoader', () => {
  const mockTimeoutRef = { current: null as NodeJS.Timeout | null };
  let container: HTMLElement;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockTimeoutRef.current = null;
    mockJS9Service.isAvailable.mockReturnValue(true);
    mockGetDisplaySafe.mockReturnValue(null);
    (global as any).window.JS9 = {};
    
    // Create a div with the displayId for the hook to find
    container = document.createElement('div');
    container.id = 'testDisplay';
    document.body.appendChild(container);
  });

  afterEach(() => {
    // Clean up the div
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
    }
  });

  afterEach(() => {
    vi.useRealTimers();
  });


  it('should return loading=false initially when no image path', () => {
    const { result } = renderHook(() =>
      useJS9ImageLoader({
        imagePath: null,
        displayId: 'testDisplay',
        initialized: true,
        isJS9Ready: true,
        timeoutRef: mockTimeoutRef,
        getDisplaySafe: mockGetDisplaySafe,
      })
    );

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should set loading=true when image path provided', () => {
    const { result } = renderHook(() =>
      useJS9ImageLoader({
        imagePath: '/test/image.fits',
        displayId: 'testDisplay',
        initialized: true,
        isJS9Ready: true,
        timeoutRef: mockTimeoutRef,
        getDisplaySafe: mockGetDisplaySafe,
      })
    );

    // Advance timers to trigger the setTimeout in the hook
    vi.advanceTimersByTime(100);
    
    expect(result.current.loading).toBe(true);
  });

  it('should not load when not initialized', () => {
    const { result } = renderHook(() =>
      useJS9ImageLoader({
        imagePath: '/test/image.fits',
        displayId: 'testDisplay',
        initialized: false,
        isJS9Ready: true,
        timeoutRef: mockTimeoutRef,
        getDisplaySafe: mockGetDisplaySafe,
      })
    );

    expect(result.current.loading).toBe(false);
    expect(mockJS9Service.loadImage).not.toHaveBeenCalled();
  });

  it('should not load when JS9 not ready', () => {
    mockJS9Service.isAvailable.mockReturnValue(false);
    
    const { result } = renderHook(() =>
      useJS9ImageLoader({
        imagePath: '/test/image.fits',
        displayId: 'testDisplay',
        initialized: true,
        isJS9Ready: false,
        timeoutRef: mockTimeoutRef,
        getDisplaySafe: mockGetDisplaySafe,
      })
    );

    expect(result.current.loading).toBe(false);
    expect(mockJS9Service.loadImage).not.toHaveBeenCalled();
  });

  it('should close existing image before loading new one', () => {
    const existingDisplay = { id: 'testDisplay', im: { id: 'oldImage' } };
    mockGetDisplaySafe.mockReturnValue(existingDisplay);

    renderHook(() =>
      useJS9ImageLoader({
        imagePath: '/test/image.fits',
        displayId: 'testDisplay',
        initialized: true,
        isJS9Ready: true,
        timeoutRef: mockTimeoutRef,
        getDisplaySafe: mockGetDisplaySafe,
      })
    );

    // Advance timers to trigger the setTimeout in the hook
    vi.advanceTimersByTime(200);

    expect(mockJS9Service.closeImage).toHaveBeenCalledWith('oldImage');
  });

  it('should handle load errors', () => {
    mockJS9Service.loadImage.mockImplementation((path: string, options: any) => {
      // Call onerror synchronously to simulate immediate error
      if (options && options.onerror) {
        options.onerror(new Error('Load failed'));
      }
    });

    const { result } = renderHook(() =>
      useJS9ImageLoader({
        imagePath: '/test/image.fits',
        displayId: 'testDisplay',
        initialized: true,
        isJS9Ready: true,
        timeoutRef: mockTimeoutRef,
        getDisplaySafe: mockGetDisplaySafe,
      })
    );

    // Advance timers to trigger loadImage call (first setTimeout)
    act(() => {
      vi.advanceTimersByTime(200);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.loading).toBe(false);
  });

  it('should reset state when imagePath cleared', () => {
    const { result, rerender } = renderHook(
      ({ imagePath }) =>
        useJS9ImageLoader({
          imagePath,
          displayId: 'testDisplay',
          initialized: true,
          isJS9Ready: true,
          timeoutRef: mockTimeoutRef,
          getDisplaySafe: mockGetDisplaySafe,
        }),
      { initialProps: { imagePath: '/test/image.fits' } }
    );

    rerender({ imagePath: null });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should add cache buster to image URL', () => {
    renderHook(() =>
      useJS9ImageLoader({
        imagePath: '/test/image.fits',
        displayId: 'testDisplay',
        initialized: true,
        isJS9Ready: true,
        timeoutRef: mockTimeoutRef,
        getDisplaySafe: mockGetDisplaySafe,
      })
    );

    // Advance timers to trigger the nested setTimeout calls in the hook
    vi.advanceTimersByTime(200);

    expect(mockJS9Service.loadImage).toHaveBeenCalled();
    const callArgs = mockJS9Service.loadImage.mock.calls[0];
    expect(callArgs[0]).toContain('/test/image.fits');
    expect(callArgs[0]).toMatch(/[?&]t=\d+/);
  });
});

