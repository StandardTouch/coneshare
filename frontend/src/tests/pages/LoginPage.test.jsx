import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import LoginPage from "../../pages/LoginPage";
import { UserProvider } from "../../contexts/UserProvider";
import { authService } from "../../services/authService";
import { getUser } from "../../services/api";
import "../../i18n";

vi.mock("jwt-decode", () => ({
  jwtDecode: vi.fn(() => ({ user_id: 1 })),
}));

vi.mock("../../services/authService");

vi.mock("../../services/api", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getUser: vi.fn(),
  };
});

// Mock useNavigate from react-router
const mockedNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockedNavigate,
  };
});

describe("LoginPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    authService.getPublicSettings.mockResolvedValue({ enable_public_signup: false });
    getUser.mockResolvedValue({ data: { id: 1, email: "test@example.com" } });
  });

  const renderComponent = () => {
    return render(
      <MemoryRouter initialEntries={["/login"]}>
        <UserProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<div>Homepage</div>} />
          </Routes>
        </UserProvider>
      </MemoryRouter>
    );
  };

  it("renders the login form correctly", () => {
    renderComponent();
    expect(
      screen.getByRole("heading", { name: /Sign In/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign In/i })).toBeInTheDocument();
  });

  it("calls authService.login and navigates to home on successful login", async () => {
    authService.login.mockImplementation(async () => {
      localStorage.setItem("access_token", "token");
    });
    renderComponent();

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign In/i }));

    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith(
        "test@example.com",
        "password123"
      );
    });

    await waitFor(() => {
      expect(mockedNavigate).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("displays an error message on failed login", async () => {
    authService.login.mockRejectedValue(new Error("Invalid credentials"));
    renderComponent();

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "wrong@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "wrongpassword" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign In/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Invalid credentials. Please try again.")
      ).toBeInTheDocument();
    });

    expect(mockedNavigate).not.toHaveBeenCalled();
  });

  it("shows signup link when public signup is enabled", async () => {
    authService.getPublicSettings.mockResolvedValue({ enable_public_signup: true });
    renderComponent();

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument();
    });
  });

  it("hides signup link when public signup is disabled", async () => {
    authService.getPublicSettings.mockResolvedValue({ enable_public_signup: false });
    renderComponent();

    await waitFor(() => {
      expect(screen.queryByRole('link', { name: /sign up/i })).not.toBeInTheDocument();
    });
  });

  it("disables the submit button while loading", async () => {
    // Create a promise that we can resolve later to simulate a long request
    let resolveLogin;
    const loginPromise = new Promise((resolve) => {
      resolveLogin = resolve;
    });
    authService.login.mockImplementation(() => loginPromise);

    renderComponent();

    fireEvent.change(screen.getByLabelText(/Email address/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "password123" },
    });

    const submitButton = screen.getByRole("button", { name: /Sign In/i });
    fireEvent.click(submitButton);

    // After clicking, button should be disabled and show "Signing In..."
    await waitFor(() => {
      expect(submitButton).toBeDisabled();
      expect(screen.getByText("Signing In...")).toBeInTheDocument();
    });

    // Resolve the promise to finish the login process
    resolveLogin({});
    localStorage.setItem("access_token", "token");

    // Wait for the UI to update after login completes
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled();
    });
  });
});
