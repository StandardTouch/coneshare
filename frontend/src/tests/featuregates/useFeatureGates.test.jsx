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
  it('allows api keys, automations, and mcp setup when toggles are on', () => {
    useBranding.mockReturnValue({
      swaggerEnabled: true,
      apiKeysEnabled: true,
      automationEnabled: true,
      fileRequestsEnabled: true,
      documentsEnabled: true,
      trashEnabled: true,
      signatureEnabled: true,
      esignEnabled: true,
    });
    useUser.mockReturnValue({ user: { role: 'admin' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(true);
    expect(result.current.canAccessAutomations).toBe(true);
    expect(result.current.canAccessMcpSetup).toBe(true);
    expect(result.current.canAccessApiDocs).toBe(true);
    expect(result.current.canAccessFileRequests).toBe(true);
    expect(result.current.canAccessDocuments).toBe(true);
    expect(result.current.canAccessTrash).toBe(true);
  });

  it('allows members with role-based feature flags when enabled', () => {
    useBranding.mockReturnValue({
      swaggerEnabled: true,
      apiKeysEnabled: true,
      automationEnabled: true,
      fileRequestsEnabled: true,
      documentsEnabled: true,
      trashEnabled: true,
      signatureEnabled: true,
      esignEnabled: false,
    });
    useUser.mockReturnValue({ user: { role: 'member' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(true);
    expect(result.current.canAccessAutomations).toBe(true);
    expect(result.current.canAccessApiDocs).toBe(true);
    expect(result.current.canAccessFileRequests).toBe(true);
    expect(result.current.canAccessSignatures).toBe(false);
  });

  it('hides api docs when swagger is disabled', () => {
    useBranding.mockReturnValue({
      swaggerEnabled: false,
      apiKeysEnabled: true,
      automationEnabled: true,
      fileRequestsEnabled: true,
      documentsEnabled: true,
      trashEnabled: true,
      signatureEnabled: true,
      esignEnabled: true,
    });
    useUser.mockReturnValue({ user: { role: 'admin' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiDocs).toBe(false);
    expect(result.current.canAccessApiKeys).toBe(true);
  });

  it('blocks features when toggles are off', () => {
    useBranding.mockReturnValue({
      swaggerEnabled: true,
      apiKeysEnabled: false,
      automationEnabled: false,
      fileRequestsEnabled: false,
      documentsEnabled: false,
      trashEnabled: false,
      esignEnabled: true,
    });
    useUser.mockReturnValue({ user: { role: 'admin' } });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessApiKeys).toBe(false);
    expect(result.current.canAccessAutomations).toBe(false);
    expect(result.current.canAccessMcpSetup).toBe(false);
    expect(result.current.canAccessFileRequests).toBe(false);
    expect(result.current.canAccessDocuments).toBe(false);
    expect(result.current.canAccessTrash).toBe(false);
  });

  it('blocks gated nav features when user is not authenticated', () => {
    useBranding.mockReturnValue({
      swaggerEnabled: true,
      apiKeysEnabled: true,
      automationEnabled: true,
      fileRequestsEnabled: true,
      documentsEnabled: true,
      trashEnabled: true,
      esignEnabled: true,
    });
    useUser.mockReturnValue({ user: null });

    const { result } = renderHook(() => useFeatureGates());
    expect(result.current.canAccessDocuments).toBe(false);
    expect(result.current.canAccessAutomations).toBe(false);
  });
});
