import { describe, it, expect } from 'vitest';
import {
  clientPointToFieldPercent,
  clampPercent,
  defaultFieldSize,
} from '../../../components/esign/fieldPlacementUtils';

describe('fieldPlacementUtils', () => {
  it('maps client coordinates to percentage of page rect', () => {
    const rect = { left: 100, top: 50, width: 200, height: 400 };
    const result = clientPointToFieldPercent(rect, 150, 150);
    expect(result.x).toBeCloseTo(25);
    expect(result.y).toBeCloseTo(25);
  });

  it('clamps percent values', () => {
    expect(clampPercent(150, 90)).toBe(90);
    expect(clampPercent(-5, 90)).toBe(0);
  });

  it('returns default sizes by field type', () => {
    expect(defaultFieldSize('initials').width).toBe(15);
    expect(defaultFieldSize('signature').width).toBe(30);
  });
});
