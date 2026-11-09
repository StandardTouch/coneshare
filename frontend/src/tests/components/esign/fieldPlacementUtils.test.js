import { describe, it, expect } from 'vitest';
import {
  clientPointToFieldPercent,
  clampPercent,
  defaultFieldSize,
  fieldOriginFromClient,
  fieldSizeFromCorner,
  placeFieldAtClient,
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

  it('keeps a pointer at the page edge instead of pulling it back', () => {
    const rect = { left: 0, top: 0, width: 1000, height: 1000 };
    const result = clientPointToFieldPercent(rect, 1000, 1000);
    expect(result.x).toBeCloseTo(100);
    expect(result.y).toBeCloseTo(100);
  });

  it('centers a new field on the drop point and keeps it on the page', () => {
    const rect = { left: 0, top: 0, width: 1000, height: 1000 };
    const placed = placeFieldAtClient(rect, 500, 500, { width: 30, height: 8 });
    expect(placed.x).toBeCloseTo(35);
    expect(placed.y).toBeCloseTo(46);

    const edge = placeFieldAtClient(rect, 990, 990, { width: 30, height: 8 });
    expect(edge.x).toBeCloseTo(70);
    expect(edge.y).toBeCloseTo(92);
    expect(edge.x + edge.width).toBeLessThanOrEqual(100);
    expect(edge.y + edge.height).toBeLessThanOrEqual(100);
  });

  it('moves a field by its top-left and resizes from the opposite corner', () => {
    const rect = { left: 0, top: 0, width: 200, height: 400 };
    const moved = fieldOriginFromClient(rect, 50, 80, 30, 8);
    expect(moved.x).toBeCloseTo(25);
    expect(moved.y).toBeCloseTo(20);

    const resized = fieldSizeFromCorner({ x: 10, y: 10 }, rect, 80, 160);
    expect(resized.x).toBeCloseTo(10);
    expect(resized.y).toBeCloseTo(10);
    expect(resized.width).toBeCloseTo(30);
    expect(resized.height).toBeCloseTo(30);
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
