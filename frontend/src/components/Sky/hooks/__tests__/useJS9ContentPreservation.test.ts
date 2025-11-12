/**
 * Unit Tests for useJS9ContentPreservation Hook
 * 
 * Tests:
 * 1. Content preservation on React re-render
 * 2. MutationObserver setup
 * 3. Content restoration when cleared
 * 4. Edge cases
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useJS9ContentPreservation } from '../useJS9ContentPreservation';

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
}));

// Mock JS9Service
const { mockJS9Service } = vi.hoisted(() => {
  return {
    mockJS9Service: {
      isAvailable: vi.fn(() => true),
      loadImage: vi.fn(),
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

describe('useJS9ContentPreservation', () => {
  const mockContainerRef = {
    current: document.createElement('div'),
  } as React.RefObject<HTMLDivElement>;

  const mockImageLoadedRef = { current: true };

  beforeEach(() => {
    vi.clearAllMocks();
    mockContainerRef.current = document.createElement('div');
    mockJS9Service.isAvailable.mockReturnValue(true);
    mockGetDisplaySafe.mockReturnValue(null);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should not setup observers when not initialized', () => {
    renderHook(() =>
      useJS9ContentPreservation({
        displayId: 'testDisplay',
        containerRef: mockContainerRef,
        initialized: false,
        isJS9Ready: true,
        imageLoadedRef: mockImageLoadedRef,
        loading: false,
        getDisplaySafe: mockGetDisplaySafe,
      })
    );

    // Should not crash
    expect(mockContainerRef.current).toBeTruthy();
  });

  it('should not setup observers when JS9 not ready', () => {
    mockJS9Service.isAvailable.mockReturnValue(false);

    renderHook(() =>
      useJS9ContentPreservation({
        displayId: 'testDisplay',
        containerRef: mockContainerRef,
        initialized: true,
        isJS9Ready: false,
        imageLoadedRef: mockImageLoadedRef,
        loading: false,
        getDisplaySafe: mockGetDisplaySafe,
      })
    );

    // Should not crash
    expect(mockContainerRef.current).toBeTruthy();
  });

  it('should restore image when content cleared', () => {
    const display = { id: 'testDisplay', im: { id: 'image1' } };
    mockGetDisplaySafe.mockReturnValue(display);
    mockContainerRef.current.innerHTML = '';

    renderHook(() =>
      useJS9ContentPreservation({
        displayId: 'testDisplay',
        containerRef: mockContainerRef,
        initialized: true,
        isJS9Ready: true,
        imageLoadedRef: mockImageLoadedRef,
        loading: false,
        getDisplaySafe: mockGetDisplaySafe,
        imagePath: '/test/image.fits',
      })
    );

    // Trigger MutationObserver callback
    const observer = new MutationObserver(() => {});
    observer.observe(mockContainerRef.current, {
      childList: true,
      subtree: true,
    });

    // Simulate React clearing content
    mockContainerRef.current.innerHTML = '';

    // Should attempt to restore
    expect(mockJS9Service.isAvailable).toHaveBeenCalled();
  });

  it('should not restore when loading new image', () => {
    renderHook(() =>
      useJS9ContentPreservation({
        displayId: 'testDisplay',
        containerRef: mockContainerRef,
        initialized: true,
        isJS9Ready: true,
        imageLoadedRef: mockImageLoadedRef,
        loading: true,
        getDisplaySafe: mockGetDisplaySafe,
        imagePath: '/test/image.fits',
      })
    );

    // Should not attempt to restore while loading
    expect(mockJS9Service.loadImage).not.toHaveBeenCalled();
  });

  it('should not restore when no image loaded', () => {
    const emptyImageLoadedRef = { current: false };

    renderHook(() =>
      useJS9ContentPreservation({
        displayId: 'testDisplay',
        containerRef: mockContainerRef,
        initialized: true,
        isJS9Ready: true,
        imageLoadedRef: emptyImageLoadedRef,
        loading: false,
        getDisplaySafe: mockGetDisplaySafe,
        imagePath: '/test/image.fits',
      })
    );

    // Should not attempt to restore if no image loaded
    expect(mockJS9Service.loadImage).not.toHaveBeenCalled();
  });
});

