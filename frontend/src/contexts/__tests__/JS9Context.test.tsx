/**
 * Unit tests for JS9Context Provider and hooks
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, renderHook, act, waitFor } from '@testing-library/react';
import { JS9Provider, useJS9, useJS9Safe } from '../JS9Context';
import * as js9Utils from '../../utils/js9';

// Mock JS9 utilities
vi.mock('../../utils/js9', () => ({
  isJS9Available: vi.fn(),
  findDisplay: vi.fn(),
  getDisplayImageId: vi.fn(),
}));

// Mock window.JS9
const mockJS9 = {
  displays: [] as any[],
  Load: vi.fn(),
  LoadImage: vi.fn(),
};

describe('JS9Context', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (window as any).JS9 = { ...mockJS9 };
    mockJS9.displays = [];
  });

  afterEach(() => {
    delete (window as any).JS9;
  });

  describe('useJS9', () => {
    it('should throw error when used outside provider', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      expect(() => {
        renderHook(() => useJS9());
      }).toThrow('useJS9 must be used within JS9Provider');
      
      consoleSpy.mockRestore();
    });

    it('should return context value when used inside provider', () => {
      vi.mocked(js9Utils.isJS9Available).mockReturnValue(true);
      
      const { result } = renderHook(() => useJS9(), {
        wrapper: JS9Provider,
      });
      
      expect(result.current).toBeDefined();
      expect(result.current.isJS9Ready).toBe(true);
      expect(result.current.getDisplay).toBeDefined();
      expect(result.current.getImageId).toBeDefined();
    });
  });

  describe('useJS9Safe', () => {
    it('should return null when used outside provider', () => {
      const { result } = renderHook(() => useJS9Safe());
      
      expect(result.current).toBeNull();
    });

    it('should return context value when used inside provider', () => {
      vi.mocked(js9Utils.isJS9Available).mockReturnValue(true);
      
      const { result } = renderHook(() => useJS9Safe(), {
        wrapper: JS9Provider,
      });
      
      expect(result.current).not.toBeNull();
      expect(result.current?.isJS9Ready).toBe(true);
    });
  });

  describe('JS9Provider', () => {
    it('should initialize JS9 as ready when available', async () => {
      vi.mocked(js9Utils.isJS9Available).mockReturnValue(true);
      
      const { result } = renderHook(() => useJS9(), {
        wrapper: JS9Provider,
      });
      
      await waitFor(() => {
        expect(result.current.isJS9Ready).toBe(true);
        expect(result.current.isJS9Initializing).toBe(false);
        expect(result.current.js9Error).toBeNull();
      });
    });

    it('should poll for JS9 availability when not immediately available', async () => {
      vi.mocked(js9Utils.isJS9Available)
        .mockReturnValueOnce(false)
        .mockReturnValueOnce(false)
        .mockReturnValueOnce(true);
      
      vi.useFakeTimers();
      
      const { result } = renderHook(() => useJS9(), {
        wrapper: JS9Provider,
      });
      
      expect(result.current.isJS9Initializing).toBe(true);
      expect(result.current.isJS9Ready).toBe(false);
      
      // Advance timers to trigger polling (100ms intervals)
      act(() => {
        vi.advanceTimersByTime(200);
      });
      
      // After 200ms, should have checked twice and found JS9
      expect(result.current.isJS9Ready).toBe(true);
      expect(result.current.isJS9Initializing).toBe(false);
      
      vi.useRealTimers();
    });

    it('should set error after timeout if JS9 never loads', async () => {
      vi.mocked(js9Utils.isJS9Available).mockReturnValue(false);
      vi.useFakeTimers();
      
      const { result } = renderHook(() => useJS9(), {
        wrapper: JS9Provider,
      });
      
      act(() => {
        vi.advanceTimersByTime(10000);
      });
      
      // After 10 second timeout, should have error
      expect(result.current.js9Error).toBeTruthy();
      expect(result.current.isJS9Initializing).toBe(false);
      expect(result.current.isJS9Ready).toBe(false);
      
      vi.useRealTimers();
    });

    it('should provide getDisplay function', () => {
      vi.mocked(js9Utils.isJS9Available).mockReturnValue(true);
      const mockDisplay = { id: 'test-display' };
      vi.mocked(js9Utils.findDisplay).mockReturnValue(mockDisplay);
      
      const { result } = renderHook(() => useJS9(), {
        wrapper: JS9Provider,
      });
      
      const display = result.current.getDisplay('test-display');
      expect(display).toBe(mockDisplay);
      expect(js9Utils.findDisplay).toHaveBeenCalledWith('test-display');
    });

    it('should return null from getDisplay when JS9 not available', () => {
      vi.mocked(js9Utils.isJS9Available).mockReturnValue(false);
      
      const { result } = renderHook(() => useJS9(), {
        wrapper: JS9Provider,
      });
      
      const display = result.current.getDisplay('test-display');
      expect(display).toBeNull();
      expect(js9Utils.findDisplay).not.toHaveBeenCalled();
    });

    it('should provide getImageId function', () => {
      vi.mocked(js9Utils.isJS9Available).mockReturnValue(true);
      vi.mocked(js9Utils.getDisplayImageId).mockReturnValue('image-123');
      
      const { result } = renderHook(() => useJS9(), {
        wrapper: JS9Provider,
      });
      
      const imageId = result.current.getImageId('test-display');
      expect(imageId).toBe('image-123');
      expect(js9Utils.getDisplayImageId).toHaveBeenCalledWith('test-display');
    });

    it('should provide hasImage function', () => {
      vi.mocked(js9Utils.isJS9Available).mockReturnValue(true);
      const displayWithImage = { id: 'display-with-image', im: { id: 'image-123' } };
      const displayWithoutImage = { id: 'display-without-image' };
      vi.mocked(js9Utils.findDisplay)
        .mockReturnValueOnce(displayWithImage)
        .mockReturnValueOnce(displayWithoutImage);
      
      const { result } = renderHook(() => useJS9(), {
        wrapper: JS9Provider,
      });
      
      expect(result.current.hasImage('display-with-image')).toBe(true);
      expect(result.current.hasImage('display-without-image')).toBe(false);
    });

    it('should provide getDisplayState function', () => {
      vi.mocked(js9Utils.isJS9Available).mockReturnValue(true);
      const mockDisplay = { id: 'test-display', im: { id: 'image-123' } };
      vi.mocked(js9Utils.findDisplay).mockReturnValue(mockDisplay);
      vi.mocked(js9Utils.getDisplayImageId).mockReturnValue('image-123');
      
      const { result } = renderHook(() => useJS9(), {
        wrapper: JS9Provider,
      });
      
      const state = result.current.getDisplayState('test-display');
      expect(state).toBeDefined();
      expect(state?.displayId).toBe('test-display');
      expect(state?.imageId).toBe('image-123');
    });

    it('should provide getAllDisplays function', () => {
      vi.mocked(js9Utils.isJS9Available).mockReturnValue(true);
      const display1 = { id: 'display1', im: { id: 'image1' } };
      const display2 = { id: 'display2' };
      mockJS9.displays = [display1, display2];
      (window as any).JS9 = { ...mockJS9 };
      
      vi.mocked(js9Utils.findDisplay)
        .mockReturnValueOnce(display1)
        .mockReturnValueOnce(display2);
      vi.mocked(js9Utils.getDisplayImageId)
        .mockReturnValueOnce('image1')
        .mockReturnValueOnce(null);
      
      const { result } = renderHook(() => useJS9(), {
        wrapper: JS9Provider,
      });
      
      const displays = result.current.getAllDisplays();
      expect(displays).toHaveLength(2);
      expect(displays[0].displayId).toBe('display1');
      expect(displays[1].displayId).toBe('display2');
    });

    it('should render children', () => {
      const TestComponent = () => <div>Test Content</div>;
      
      const { getByText } = render(
        <JS9Provider>
          <TestComponent />
        </JS9Provider>
      );
      
      expect(getByText('Test Content')).toBeInTheDocument();
    });
  });
});

