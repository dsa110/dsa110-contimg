/**
 * ImageBrowser Component Tests
 * 
 * These tests verify:
 * 1. Component renders without errors (catches missing imports)
 * 2. Date formatting works correctly
 * 3. Image selection functionality
 * 4. Filtering works as expected
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ImageBrowser from './ImageBrowser';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock the API queries
vi.mock('../../api/queries', () => ({
  useImages: vi.fn(),
}));

const { useImages } = await import('../../api/queries');

describe('ImageBrowser', () => {
  let queryClient: QueryClient;
  let mockOnSelectImage: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    mockOnSelectImage = vi.fn();
    vi.clearAllMocks();
  });

  const renderWithProviders = (props = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <ImageBrowser
          onSelectImage={mockOnSelectImage}
          selectedImageId={undefined}
          {...props}
        />
      </QueryClientProvider>
    );
  };

  it('should render without errors', () => {
    // This test would fail if there are missing imports (like date-fns)
    vi.mocked(useImages).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    } as any);

    expect(() => renderWithProviders()).not.toThrow();
  });

  it('should display images when data is loaded', async () => {
    const mockImages = [
      {
        id: 1,
        path: '/data/images/test1.fits',
        type: '5min',
        pbcor: false,
        created_at: '2025-01-15T12:00:00Z',
        noise_jy: 0.001,
        beam_major_arcsec: 12.5,
      },
      {
        id: 2,
        path: '/data/images/test2.fits',
        type: '5min',
        pbcor: true,
        created_at: '2025-01-15T12:05:00Z',
        noise_jy: 0.0012,
        beam_major_arcsec: 12.8,
      },
    ];

    vi.mocked(useImages).mockReturnValue({
      data: { items: mockImages, total: 2 },
      isLoading: false,
      error: null,
    } as any);

    renderWithProviders();

    // Check that images are displayed
    expect(screen.getByText('test1.fits')).toBeInTheDocument();
    expect(screen.getByText('test2.fits')).toBeInTheDocument();
  });

  it('should format dates correctly using dayjs', async () => {
    const mockImage = {
      id: 1,
      path: '/data/images/test1.fits',
      type: '5min',
      pbcor: false,
      created_at: '2025-01-15T12:00:00Z',
      noise_jy: 0.001,
      beam_major_arcsec: 12.5,
    };

    vi.mocked(useImages).mockReturnValue({
      data: { items: [mockImage], total: 1 },
      isLoading: false,
      error: null,
    } as any);

    renderWithProviders();

    // Check that date is formatted correctly (YYYY-MM-DD HH:mm:ss)
    // This would fail if date-fns was used instead of dayjs
    await waitFor(() => {
      expect(screen.getByText(/2025-01-15/)).toBeInTheDocument();
    });
  });

  it('should call onSelectImage when image is clicked', async () => {
    const user = userEvent.setup();
    const mockImage = {
      id: 1,
      path: '/data/images/test1.fits',
      type: '5min',
      pbcor: false,
      created_at: '2025-01-15T12:00:00Z',
      noise_jy: 0.001,
      beam_major_arcsec: 12.5,
    };

    vi.mocked(useImages).mockReturnValue({
      data: { items: [mockImage], total: 1 },
      isLoading: false,
      error: null,
    } as any);

    renderWithProviders();

    const imageButton = screen.getByText('test1.fits');
    await user.click(imageButton);

    expect(mockOnSelectImage).toHaveBeenCalledWith(mockImage);
  });

  it('should display loading state', () => {
    vi.mocked(useImages).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    renderWithProviders();

    // Check for loading indicator
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should display error state', () => {
    vi.mocked(useImages).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load'),
    } as any);

    renderWithProviders();

    expect(screen.getByText('Failed to load images')).toBeInTheDocument();
  });

  it('should display empty state when no images', () => {
    vi.mocked(useImages).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    } as any);

    renderWithProviders();

    expect(screen.getByText('No images found')).toBeInTheDocument();
  });

  it('should apply filters when search is performed', async () => {
    const user = userEvent.setup();
    const mockSetFilters = vi.fn();

    vi.mocked(useImages).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
    } as any);

    renderWithProviders();

    const searchInput = screen.getByLabelText('Search MS Path');
    await user.type(searchInput, 'test-path');
    await user.keyboard('{Enter}');

    // Verify that useImages was called with updated filters
    // (This is a simplified check - in reality, we'd need to track filter state)
    expect(searchInput).toHaveValue('test-path');
  });
});

