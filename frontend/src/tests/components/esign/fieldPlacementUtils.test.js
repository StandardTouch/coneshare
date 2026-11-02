import { describe, it, expect } from 'vitest';
import {
  clientPointToFieldPercent,
  clampPercent,
  defaultFieldSize,
  signerOverlayColor,
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

  it('assigns stable overlay colors for ULID signer ids', () => {
    const ulid = '01M6BBPMBM7QFDG413TWMECWQH';
    expect(signerOverlayColor(ulid)).toBe(signerOverlayColor(ulid));
    expect(signerOverlayColor(ulid)).not.toBe(signerOverlayColor('01M6DR9ZF681SZEKXA8CJBX7F6'));
  });
});
