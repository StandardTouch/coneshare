import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import RequireAuth from "../../../components/auth/RequireAuth";
import { UserContext } from "../../../contexts/UserProvider";

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("RequireAuth", () => {
  const renderWithUser = (user, isLoading = false, initialPath = "/") => {
    return render(
      <MemoryRouter initialEntries={[initialPath]}>
        <UserContext.Provider value={{ user, isLoading }}>
          <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route
              path="/"
              element={
                <RequireAuth>
                  <div>Protected Content</div>
                </RequireAuth>
              }
            />
            <Route
              path="/admin"
              element={
                <RequireAuth adminOnly>
                  <div>Admin Content</div>
                </RequireAuth>
              }
            />
          </Routes>
        </UserContext.Provider>
      </MemoryRouter>
    );
  };

  it("shows loading spinner when isLoading is true", () => {
    renderWithUser(null, true);
    const spinner = document.querySelector(".animate-spin");
    expect(spinner).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("redirects to login when user is null and not loading", () => {
    renderWithUser(null, false);
    expect(screen.getByText("Login Page")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders children when user is authenticated", () => {
    const mockUser = { id: 1, email: "test@example.com", role: "user" };
    renderWithUser(mockUser, false);
    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });

  it("redirects non-admin users when adminOnly is true", () => {
    const mockUser = { id: 1, email: "test@example.com", role: "user" };
    render(
      <MemoryRouter initialEntries={["/admin"]}>
        <UserContext.Provider value={{ user: mockUser, isLoading: false }}>
          <Routes>
            <Route path="/" element={<div>Home Page</div>} />
            <Route
              path="/admin"
              element={
                <RequireAuth adminOnly>
                  <div>Admin Content</div>
                </RequireAuth>
              }
            />
          </Routes>
        </UserContext.Provider>
      </MemoryRouter>
    );
    expect(screen.getByText("Home Page")).toBeInTheDocument();
    expect(screen.queryByText("Admin Content")).not.toBeInTheDocument();
  });

  it("allows admin users to access admin-only routes", () => {
    const mockAdminUser = { id: 1, email: "admin@example.com", role: "admin" };
    render(
      <MemoryRouter initialEntries={["/admin"]}>
        <UserContext.Provider value={{ user: mockAdminUser, isLoading: false }}>
          <Routes>
            <Route path="/" element={<div>Home Page</div>} />
            <Route
              path="/admin"
              element={
                <RequireAuth adminOnly>
                  <div>Admin Content</div>
                </RequireAuth>
              }
            />
          </Routes>
        </UserContext.Provider>
      </MemoryRouter>
    );
    expect(screen.getByText("Admin Content")).toBeInTheDocument();
    expect(screen.queryByText("Home Page")).not.toBeInTheDocument();
  });
});
