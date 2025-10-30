/**
 * Tests for ControlPage selection state management
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useState } from 'react';

// Test selection logic in isolation
describe('ControlPage Selection State Logic', () => {
  describe('onSelectionChange handler', () => {
    it('should set selectedMS to newly added item when selection grows', () => {
      const { result } = renderHook(() => {
        const [selectedMSList, setSelectedMSList] = useState<string[]>([]);
        const [selectedMS, setSelectedMS] = useState('');
        
        const onSelectionChange = (paths: string[]) => {
          const prevList = selectedMSList;
          setSelectedMSList(paths);
          
          if (paths.length > 0) {
            if (paths.length > prevList.length) {
              const newItem = paths.find(p => !prevList.includes(p));
              if (newItem) {
                setSelectedMS(newItem);
              } else {
                setSelectedMS(paths[0]);
              }
            }
          } else {
            setSelectedMS('');
          }
        };
        
        return { selectedMSList, selectedMS, onSelectionChange, setSelectedMSList };
      });

      act(() => {
        result.current.onSelectionChange(['/data/ms1.ms']);
      });

      expect(result.current.selectedMSList).toEqual(['/data/ms1.ms']);
      expect(result.current.selectedMS).toBe('/data/ms1.ms');
    });

    it('should clear selectedMS when item is removed and no items remain', () => {
      const { result } = renderHook(() => {
        const [selectedMSList, setSelectedMSList] = useState<string[]>(['/data/ms1.ms']);
        const [selectedMS, setSelectedMS] = useState('/data/ms1.ms');
        
        const onSelectionChange = (paths: string[]) => {
          const prevList = selectedMSList;
          setSelectedMSList(paths);
          
          if (paths.length > 0) {
            if (paths.length < prevList.length) {
              setSelectedMS(prev => {
                if (paths.includes(prev)) {
                  return prev;
                }
                return paths.length > 0 ? paths[0] : '';
              });
            }
          } else {
            setSelectedMS('');
          }
        };
        
        return { selectedMSList, selectedMS, onSelectionChange };
      });

      act(() => {
        result.current.onSelectionChange([]);
      });

      expect(result.current.selectedMSList).toEqual([]);
      expect(result.current.selectedMS).toBe('');
    });

    it('should keep selectedMS when it is still in selection after removal', () => {
      const { result } = renderHook(() => {
        const [selectedMSList, setSelectedMSList] = useState<string[]>(['/data/ms1.ms', '/data/ms2.ms']);
        const [selectedMS, setSelectedMS] = useState('/data/ms1.ms');
        
        const onSelectionChange = (paths: string[]) => {
          const prevList = selectedMSList;
          setSelectedMSList(paths);
          
          if (paths.length > 0) {
            if (paths.length < prevList.length) {
              setSelectedMS(prev => {
                if (paths.includes(prev)) {
                  return prev;
                }
                return paths.length > 0 ? paths[0] : '';
              });
            }
          } else {
            setSelectedMS('');
          }
        };
        
        return { selectedMSList, selectedMS, onSelectionChange };
      });

      // Remove ms2, keep ms1
      act(() => {
        result.current.onSelectionChange(['/data/ms1.ms']);
      });

      expect(result.current.selectedMSList).toEqual(['/data/ms1.ms']);
      expect(result.current.selectedMS).toBe('/data/ms1.ms'); // Should stay the same
    });

    it('should update selectedMS when current selection is removed', () => {
      const { result } = renderHook(() => {
        const [selectedMSList, setSelectedMSList] = useState<string[]>(['/data/ms1.ms', '/data/ms2.ms']);
        const [selectedMS, setSelectedMS] = useState('/data/ms1.ms');
        
        const onSelectionChange = (paths: string[]) => {
          const prevList = selectedMSList;
          setSelectedMSList(paths);
          
          if (paths.length > 0) {
            if (paths.length < prevList.length) {
              setSelectedMS(prev => {
                if (paths.includes(prev)) {
                  return prev;
                }
                return paths.length > 0 ? paths[0] : '';
              });
            }
          } else {
            setSelectedMS('');
          }
        };
        
        return { selectedMSList, selectedMS, onSelectionChange };
      });

      // Remove ms1 (current selectedMS), keep ms2
      act(() => {
        result.current.onSelectionChange(['/data/ms2.ms']);
      });

      expect(result.current.selectedMSList).toEqual(['/data/ms2.ms']);
      expect(result.current.selectedMS).toBe('/data/ms2.ms'); // Should switch to ms2
    });
  });
});

