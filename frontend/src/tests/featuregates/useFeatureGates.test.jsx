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
  it('allows admin api keys when feature flags are on', () => {
    useBranding.mockReturnValue({
      mcpEnabled: true,
      apiKeysEnabled: true,
      automationEnabled: true,
    });
    useUser.mockReturnValue({ user: { role: 'admin' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(true);
    expect(result.current.canAccessAutomations).toBe(true);
    expect(result.current.canAccessMcpSetup).toBe(true);
  });

  it('blocks members from api keys and automations', () => {
    useBranding.mockReturnValue({
      mcpEnabled: true,
      apiKeysEnabled: true,
      automationEnabled: true,
    });
    useUser.mockReturnValue({ user: { role: 'member' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(false);
    expect(result.current.canAccessAutomations).toBe(false);
  });

  it('hides mcp setup when mcp is disabled', () => {
    useBranding.mockReturnValue({
      mcpEnabled: false,
      apiKeysEnabled: true,
      automationEnabled: true,
    });
    useUser.mockReturnValue({ user: { role: 'admin' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(true);
    expect(result.current.canAccessMcpSetup).toBe(false);
  });
});
