/**
 * CASAnalysisPlugin Unit Tests - OPTIMIZED VERSION
 * 
 * Tests:
 * 1. Component rendering and initialization
 * 2. Task selection and execution
 * 3. Region handling
 * 4. Batch mode functionality
 * 5. Contour overlay integration
 * 6. API error handling
 * 7. Export functionality
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import CASAnalysisPlugin from './CASAnalysisPlugin';

declare global {
  interface Window {
    JS9: any;
  }
}

// Mock API client
const mockApiClient = {
  post: vi.fn(),
};

vi.mock('../../../api/client', () => ({
  apiClient: mockApiClient,
}));

// Mock logger
vi.mock('../../../utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock ContourOverlay
vi.mock('./ContourOverlay', () => ({
  default: () => null,
}));

describe('CASAnalysisPlugin', () => {
  let mockJS9: any;
  let mockDisplay: any;
  let mockImage: any;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    mockImage = {
      id: 'test-image-1',
      file: '/test/image.fits',
    };

    mockDisplay = {
      id: 'skyViewDisplay',
      display: 'skyViewDisplay',
      divID: 'skyViewDisplay',
      im: mockImage,
    };

    mockJS9 = {
      displays: [mockDisplay],
      GetImageData: vi.fn(() => ({ file: '/test/image.fits' })),
      GetFITSheader: vi.fn(() => ({ FILENAME: '/test/image.fits' })),
      GetRegions: vi.fn(() => []),
      AddAnalysis: vi.fn(),
      Load: vi.fn(),
    };

    (window as any).JS9 = mockJS9;
  });

  afterEach(() => {
    vi.useRealTimers();
    delete (window as any).JS9;
  });

  describe('Component Rendering', () => {
    it('should render without crashing', () => {
      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      expect(screen.getByLabelText(/CASA Task/i)).toBeInTheDocument();
    });

    it('should display all task options', async () => {
      const user = userEvent.setup();
      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      const select = screen.getByLabelText(/CASA Task/i);
      await user.click(select);

      expect(screen.getByText('Image Statistics')).toBeInTheDocument();
      expect(screen.getByText('Source Fitting')).toBeInTheDocument();
      expect(screen.getByText('Contour Generation')).toBeInTheDocument();
      expect(screen.getByText('Spectral Flux')).toBeInTheDocument();
      expect(screen.getByText('Pixel Extraction')).toBeInTheDocument();
      expect(screen.getByText('Image Header')).toBeInTheDocument();
      expect(screen.getByText('Image Math')).toBeInTheDocument();
    });

    it('should disable run button when no image path', () => {
      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath={null} />);
      
      const button = screen.getByText('Run Analysis');
      expect(button).toBeDisabled();
    });
  });

  describe('Task Execution', () => {
    it('should execute analysis when run button clicked', async () => {
      const mockResponse = {
        data: {
          success: true,
          task: 'imstat',
          result: { DATA: { mean: 0.001, std: 0.0005 } },
          execution_time_sec: 0.234,
        },
      };

      mockApiClient.post.mockResolvedValue(mockResponse);

      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      const user = userEvent.setup();
      const button = screen.getByText('Run Analysis');
      await user.click(button);

      await waitFor(() => {
        expect(mockApiClient.post).toHaveBeenCalledWith(
          '/api/visualization/js9/analysis',
          expect.objectContaining({
            task: 'imstat',
            image_path: '/test/image.fits',
          })
        );
      });
    });

    it('should handle API errors gracefully', async () => {
      mockApiClient.post.mockRejectedValue(new Error('API Error'));

      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      const user = userEvent.setup();
      const button = screen.getByText('Run Analysis');
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });
    });

    it('should show loading state during execution', async () => {
      let resolvePromise: (value: any) => void;
      const promise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      mockApiClient.post.mockReturnValue(promise);

      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      const user = userEvent.setup();
      const button = screen.getByText('Run Analysis');
      await user.click(button);

      expect(screen.getByText(/Executing CASA task/i)).toBeInTheDocument();

      resolvePromise!({
        data: {
          success: true,
          task: 'imstat',
          result: {},
        },
      });

      await waitFor(() => {
        expect(screen.queryByText(/Executing CASA task/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Region Handling', () => {
    it('should detect region from JS9', () => {
      mockJS9.GetRegions.mockReturnValue([
        {
          shape: 'circle',
          x: 100,
          y: 200,
          r: 50,
        },
      ]);

      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);

      // Component should attempt to get region
      expect(mockJS9.GetRegions).toHaveBeenCalled();
    });

    it('should toggle region usage', async () => {
      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      const user = userEvent.setup();
      const switchElement = screen.getByLabelText(/Use Region/i);
      expect(switchElement).toBeChecked(); // Default is true

      await user.click(switchElement);
      expect(switchElement).not.toBeChecked();
    });

    it('should include region in API call when useRegion is enabled', async () => {
      mockJS9.GetRegions.mockReturnValue([
        {
          shape: 'circle',
          x: 100,
          y: 200,
          r: 50,
        },
      ]);

      mockApiClient.post.mockResolvedValue({
        data: { success: true, task: 'imstat', result: {} },
      });

      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      // Wait for region to be detected
      await vi.advanceTimersByTimeAsync(1000);

      const user = userEvent.setup();
      const button = screen.getByText('Run Analysis');
      await user.click(button);

      await waitFor(() => {
        expect(mockApiClient.post).toHaveBeenCalledWith(
          '/api/visualization/js9/analysis',
          expect.objectContaining({
            region: expect.objectContaining({
              shape: 'circle',
              x: 100,
              y: 200,
              r: 50,
            }),
          })
        );
      });
    });
  });

  describe('Batch Mode', () => {
    it('should enable batch mode toggle', async () => {
      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      const batchSwitch = screen.getByLabelText(/Batch Mode/i);
      expect(batchSwitch).not.toBeChecked();

      await userEvent.click(batchSwitch);
      expect(batchSwitch).toBeChecked();
    });

    it('should detect multiple regions in batch mode', async () => {
      mockJS9.GetRegions.mockReturnValue([
        { shape: 'circle', x: 100, y: 100, r: 20 },
        { shape: 'box', x: 200, y: 200, width: 30, height: 30 },
      ]);

      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      const user = userEvent.setup();
      const batchSwitch = screen.getByLabelText(/Batch Mode/i);
      await user.click(batchSwitch);

      await waitFor(() => {
        expect(screen.getByText(/Analyze 2 Regions/i)).toBeInTheDocument();
      });
    });

    it('should execute batch analysis', async () => {
      mockJS9.GetRegions.mockReturnValue([
        { shape: 'circle', x: 100, y: 100, r: 20 },
        { shape: 'circle', x: 200, y: 200, r: 30 },
      ]);

      mockApiClient.post.mockResolvedValue({
        data: {
          success: true,
          task: 'imstat',
          result: {},
          execution_time_sec: 0.1,
        },
      });

      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      const user = userEvent.setup();
      const batchSwitch = screen.getByLabelText(/Batch Mode/i);
      await user.click(batchSwitch);

      await waitFor(() => {
        const batchButton = screen.getByText(/Analyze 2 Regions/i);
        expect(batchButton).toBeInTheDocument();
      });

      const batchButton = screen.getByText(/Analyze 2 Regions/i);
      await userEvent.click(batchButton);

      await waitFor(() => {
        // Should make 2 API calls (one per region)
        expect(mockApiClient.post).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Contour Overlay', () => {
    it('should show contour toggle after imview task', async () => {
      mockApiClient.post.mockResolvedValue({
        data: {
          success: true,
          task: 'imview',
          result: {
            contour_paths: [{ level: 0.1, paths: [] }],
          },
        },
      });

      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      const user = userEvent.setup();
      // Select imview task
      const select = screen.getByLabelText(/CASA Task/i);
      await user.click(select);
      await user.click(screen.getByText('Contour Generation'));

      const button = screen.getByText('Run Analysis');
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByLabelText(/Show Contours/i)).toBeInTheDocument();
      });
    });
  });

  describe('Export Functionality', () => {
    it('should export results as JSON', async () => {
      const mockResult = {
        success: true,
        task: 'imstat',
        result: { DATA: { mean: 0.001 } },
      };

      mockApiClient.post.mockResolvedValue({ data: mockResult });

      // Mock URL.createObjectURL and document.createElement
      const mockCreateObjectURL = vi.fn(() => 'blob:url');
      const mockRevokeObjectURL = vi.fn();
      const mockClick = vi.fn();
      const mockRemove = vi.fn();

      global.URL.createObjectURL = mockCreateObjectURL;
      global.URL.revokeObjectURL = mockRevokeObjectURL;

      const mockLink = {
        href: '',
        download: '',
        click: mockClick,
        remove: mockRemove,
      };

      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any);
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as any);
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => mockLink as any);

      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      
      const user = userEvent.setup();
      const button = screen.getByText('Run Analysis');
      await user.click(button);

      await waitFor(() => {
        const exportButton = screen.getByText('Export JSON');
        expect(exportButton).toBeInTheDocument();
      });

      const user = userEvent.setup();
      const exportButton = screen.getByText('Export JSON');
      await user.click(exportButton);

      expect(mockCreateObjectURL).toHaveBeenCalled();
      expect(mockClick).toHaveBeenCalled();
    });
  });

  describe('JS9 Integration', () => {
    it('should register analysis tasks with JS9', async () => {
      render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);

      await waitFor(() => {
        expect(mockJS9.AddAnalysis).toHaveBeenCalled();
      });

      // Should register all 7 tasks
      const calls = mockJS9.AddAnalysis.mock.calls;
      expect(calls.length).toBeGreaterThanOrEqual(7);
    });

    it('should handle missing JS9 gracefully', () => {
      delete (window as any).JS9;

      expect(() => {
        render(<CASAnalysisPlugin displayId="skyViewDisplay" imagePath="/test/image.fits" />);
      }).not.toThrow();
    });
  });
});

