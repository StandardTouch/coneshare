import { useEffect, useRef } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import RequireAuth from "../../components/auth/RequireAuth";
import { UserProvider, useUser } from "../../contexts/UserProvider";
import { getUser } from "../../services/api";

vi.mock("jwt-decode", () => ({
  jwtDecode: vi.fn(() => ({ user_id: 7 })),
}));

vi.mock("../../services/api", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getUser: vi.fn(),
  };
});

function TrackedProtectedPage({ onRefreshUser }) {
  const mountCountRef = useRef(0);
  const { refreshUser } = useUser();

  useEffect(() => {
    mountCountRef.current += 1;
  }, []);

  useEffect(() => {
    onRefreshUser?.(refreshUser, mountCountRef);
  }, [onRefreshUser, refreshUser]);

  return <div data-testid="protected-page">Protected Content</div>;
}

describe("UserProvider refreshUser", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    localStorage.setItem("access_token", "token");
  });

  it("keeps protected content mounted during background refreshUser", async () => {
    const mockUser = { id: 7, email: "user@example.com", role: "user" };
    getUser.mockResolvedValue({ data: mockUser });

    let refreshUserFn;
    let mountCountRef;

    render(
      <MemoryRouter initialEntries={["/"]}>
        <UserProvider>
          <RequireAuth>
            <TrackedProtectedPage
              onRefreshUser={(refreshUser, mountRef) => {
                refreshUserFn = refreshUser;
                mountCountRef = mountRef;
              }}
            />
          </RequireAuth>
        </UserProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId("protected-page")).toBeInTheDocument();
    });

    expect(mountCountRef.current).toBe(1);
    expect(document.querySelector(".animate-spin")).not.toBeInTheDocument();

    getUser.mockResolvedValueOnce({
      data: { ...mockUser, storage_used_mb: 99 },
    });

    await refreshUserFn();

    expect(screen.getByTestId("protected-page")).toBeInTheDocument();
    expect(document.querySelector(".animate-spin")).not.toBeInTheDocument();
    expect(mountCountRef.current).toBe(1);
  });

  it("preserves user on non-401 refresh failure", async () => {
    const mockUser = { id: 7, email: "user@example.com", role: "user" };
    getUser.mockResolvedValueOnce({ data: mockUser });

    let refreshUserFn;

    render(
      <MemoryRouter initialEntries={["/"]}>
        <UserProvider>
          <RequireAuth>
            <TrackedProtectedPage
              onRefreshUser={(refreshUser) => {
                refreshUserFn = refreshUser;
              }}
            />
          </RequireAuth>
        </UserProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId("protected-page")).toBeInTheDocument();
    });

    getUser.mockRejectedValueOnce({ response: { status: 503 } });

    await refreshUserFn();

    expect(screen.getByTestId("protected-page")).toBeInTheDocument();
    expect(screen.queryByText("Login Page")).not.toBeInTheDocument();
  });
});
