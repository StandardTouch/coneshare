import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import LoginPage from "../../../pages/LoginPage";
import RequireAuth from "../../../components/auth/RequireAuth";
import { UserProvider } from "../../../contexts/UserProvider";
import { authService } from "../../../services/authService";
import { getUser } from "../../../services/api";
import "../../../i18n";

vi.mock("jwt-decode", () => ({
  jwtDecode: vi.fn(() => ({ user_id: 42 })),
}));

vi.mock("../../../services/authService");
vi.mock("../../../services/api", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getUser: vi.fn(),
  };
});

vi.mock("../../../contexts/BrandingProvider", () => ({
  useBranding: () => ({
    brandName: "Test Brand",
    brandLogoUrl: null,
    brandWebsiteUrl: null,
    termsUrl: "/terms",
    privacyPolicyUrl: "/privacy",
  }),
}));

describe("Auth login flow", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    authService.getPublicSettings.mockResolvedValue({ enable_public_signup: false });
  });

  const mockUser = { id: 42, email: "test@example.com", role: "user" };

  const renderApp = (initialEntries = ["/login"]) => {
    return render(
      <MemoryRouter initialEntries={initialEntries}>
        <UserProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/documents"
              element={
                <RequireAuth>
                  <div>Documents Page</div>
                </RequireAuth>
              }
            />
            <Route
              path="/sign/:token"
              element={
                <RequireAuth>
                  <div>Signing Page</div>
                </RequireAuth>
              }
            />
          </Routes>
        </UserProvider>
      </MemoryRouter>
    );
  };

  it("logs in and lands on a protected route without redirect loop", async () => {
    authService.login.mockImplementation(async () => {
      localStorage.setItem("access_token", "access.jwt.token");
      localStorage.setItem("refresh_token", "refresh.token");
    });
    getUser.mockResolvedValue({ data: mockUser });

    renderApp([
      {
        pathname: "/login",
        state: { from: { pathname: "/documents", search: "", hash: "" } },
      },
    ]);

    await userEvent.type(screen.getByLabelText(/Email address/i), "test@example.com");
    await userEvent.type(screen.getByLabelText(/Password/i), "password123");
    await userEvent.click(screen.getByRole("button", { name: /Sign In/i }));

    await waitFor(() => {
      expect(screen.getByText("Documents Page")).toBeInTheDocument();
    });
    expect(screen.queryByText("Login Page")).not.toBeInTheDocument();
  });

  it("returns to /sign/:token after login", async () => {
    authService.login.mockImplementation(async () => {
      localStorage.setItem("access_token", "access.jwt.token");
    });
    getUser.mockResolvedValue({ data: mockUser });

    renderApp([
      {
        pathname: "/login",
        state: {
          from: { pathname: "/sign/my-token", search: "?x=1", hash: "" },
        },
      },
    ]);

    await userEvent.type(screen.getByLabelText(/Email address/i), "test@example.com");
    await userEvent.type(screen.getByLabelText(/Password/i), "password123");
    await userEvent.click(screen.getByRole("button", { name: /Sign In/i }));

    await waitFor(() => {
      expect(screen.getByText("Signing Page")).toBeInTheDocument();
    });
  });
});
