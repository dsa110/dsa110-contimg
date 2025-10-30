/**
 * Tests for MSTable component selection logic
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MSTable from './MSTable';
import type { MSListEntry } from '../api/types';

// Mock data
const mockMSData: MSListEntry[] = [
  {
    path: '/data/ms1.ms',
    has_calibrator: true,
    calibrator_name: '3C48',
    calibrator_quality: 'excellent',
    is_calibrated: false,
    is_imaged: false,
    start_time: '2024-01-01T00:00:00',
  },
  {
    path: '/data/ms2.ms',
    has_calibrator: false,
    is_calibrated: true,
    is_imaged: false,
    start_time: '2024-01-01T01:00:00',
  },
  {
    path: '/data/ms3.ms',
    has_calibrator: true,
    calibrator_name: '3C147',
    calibrator_quality: 'good',
    is_calibrated: false,
    is_imaged: false,
    start_time: '2024-01-01T02:00:00',
  },
];

describe('MSTable Selection Logic', () => {
  it('should call onSelectionChange when checkbox is clicked', () => {
    const onSelectionChange = vi.fn();
    const onMSClick = vi.fn();

    render(
      <MSTable
        data={mockMSData}
        selected={[]}
        onSelectionChange={onSelectionChange}
        onMSClick={onMSClick}
      />
    );

    const checkboxes = screen.getAllByRole('checkbox');
    // First checkbox is select-all, second is first MS
    const firstMSCheckbox = checkboxes[1];

    fireEvent.click(firstMSCheckbox);

    expect(onSelectionChange).toHaveBeenCalledWith(['/data/ms1.ms']);
    // onMSClick should NOT be called for checkbox clicks
    expect(onMSClick).not.toHaveBeenCalled();
  });

  it('should remove item when checkbox is unchecked', () => {
    const onSelectionChange = vi.fn();

    render(
      <MSTable
        data={mockMSData}
        selected={['/data/ms1.ms', '/data/ms2.ms']}
        onSelectionChange={onSelectionChange}
      />
    );

    const checkboxes = screen.getAllByRole('checkbox');
    // Find checkbox for ms1 (which is selected)
    const ms1Checkbox = checkboxes[1];

    fireEvent.click(ms1Checkbox);

    expect(onSelectionChange).toHaveBeenCalledWith(['/data/ms2.ms']);
  });

  it('should call onMSClick when row is clicked', () => {
    const onMSClick = vi.fn();
    const onSelectionChange = vi.fn();

    render(
      <MSTable
        data={mockMSData}
        selected={[]}
        onSelectionChange={onSelectionChange}
        onMSClick={onMSClick}
      />
    );

    const rows = screen.getAllByRole('row');
    // First row is header, second is first MS
    const firstMSRow = rows[1];

    fireEvent.click(firstMSRow);

    expect(onMSClick).toHaveBeenCalledWith(mockMSData[0]);
    // Row click should also update selection list
    expect(onSelectionChange).toHaveBeenCalledWith(['/data/ms1.ms']);
  });

  it('should select all when select-all checkbox is clicked', () => {
    const onSelectionChange = vi.fn();

    render(
      <MSTable
        data={mockMSData}
        selected={[]}
        onSelectionChange={onSelectionChange}
      />
    );

    const checkboxes = screen.getAllByRole('checkbox');
    const selectAllCheckbox = checkboxes[0];

    fireEvent.click(selectAllCheckbox);

    expect(onSelectionChange).toHaveBeenCalledWith([
      '/data/ms1.ms',
      '/data/ms2.ms',
      '/data/ms3.ms',
    ]);
  });
});

