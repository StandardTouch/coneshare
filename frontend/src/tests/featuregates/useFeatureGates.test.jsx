import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useFeatureGates } from '../../featuregates/useFeatureGates';

vi.mock('../../contexts/BrandingProvider', () => ({
  useBranding: vi.fn(),
}));

vi.mock('../../contexts/UserProvider', () => ({
  useUser: vi.fn(),
}));

import { useBranding } from '../../contexts/BrandingProvider';
import { useUser } from '../../contexts/UserProvider';

describe('useFeatureGates', () => {
  it('allows admin api keys, automations, and mcp setup without feature toggles', () => {
    useBranding.mockReturnValue({ swaggerEnabled: true });
    useUser.mockReturnValue({ user: { role: 'admin' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(true);
    expect(result.current.canAccessAutomations).toBe(true);
    expect(result.current.canAccessMcpSetup).toBe(true);
    expect(result.current.canAccessApiDocs).toBe(true);
  });

  it('blocks members from admin features', () => {
    useBranding.mockReturnValue({ swaggerEnabled: true });
    useUser.mockReturnValue({ user: { role: 'member' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(false);
    expect(result.current.canAccessAutomations).toBe(false);
    expect(result.current.canAccessApiDocs).toBe(false);
  });

  it('hides api docs for admin when swagger is disabled', () => {
    useBranding.mockReturnValue({ swaggerEnabled: false });
    useUser.mockReturnValue({ user: { role: 'admin' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiDocs).toBe(false);
    expect(result.current.canAccessApiKeys).toBe(true);
  });
});
