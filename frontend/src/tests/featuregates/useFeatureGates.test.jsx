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
  it('allows admin api keys, automations, and mcp setup when toggles are on', () => {
    useBranding.mockReturnValue({
      swaggerEnabled: true,
      apiKeysEnabled: true,
      automationEnabled: true,
      fileRequestsEnabled: true,
    });
    useUser.mockReturnValue({ user: { role: 'admin' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(true);
    expect(result.current.canAccessAutomations).toBe(true);
    expect(result.current.canAccessMcpSetup).toBe(true);
    expect(result.current.canAccessApiDocs).toBe(true);
    expect(result.current.canAccessFileRequests).toBe(true);
  });

  it('blocks members from admin features', () => {
    useBranding.mockReturnValue({
      swaggerEnabled: true,
      apiKeysEnabled: true,
      automationEnabled: true,
      fileRequestsEnabled: true,
    });
    useUser.mockReturnValue({ user: { role: 'member' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(false);
    expect(result.current.canAccessAutomations).toBe(false);
    expect(result.current.canAccessApiDocs).toBe(false);
    expect(result.current.canAccessFileRequests).toBe(true);
  });

  it('hides api docs for admin when swagger is disabled', () => {
    useBranding.mockReturnValue({
      swaggerEnabled: false,
      apiKeysEnabled: true,
      automationEnabled: true,
      fileRequestsEnabled: true,
    });
    useUser.mockReturnValue({ user: { role: 'admin' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiDocs).toBe(false);
    expect(result.current.canAccessApiKeys).toBe(true);
  });

  it('blocks admin api keys and automations when feature toggles are off', () => {
    useBranding.mockReturnValue({
      swaggerEnabled: true,
      apiKeysEnabled: false,
      automationEnabled: false,
      fileRequestsEnabled: false,
    });
    useUser.mockReturnValue({ user: { role: 'admin' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(false);
    expect(result.current.canAccessAutomations).toBe(false);
    expect(result.current.canAccessMcpSetup).toBe(false);
    expect(result.current.canAccessFileRequests).toBe(false);
  });
});
