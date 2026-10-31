import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
} from "react";
import { useNavigate } from "react-router-dom";
import { jwtDecode } from "jwt-decode";
import { getUser } from "../services/api";
import { authService } from "../services/authService";

export const UserContext = createContext(null);

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const initialLoadDoneRef = useRef(false);
  const navigate = useNavigate();

  const handleLogout = useCallback(async () => {
    await authService.logout();
    setUser(null);
    navigate("/login");
  }, [navigate]);

  const finishInitialLoad = useCallback(() => {
    if (!initialLoadDoneRef.current) {
      initialLoadDoneRef.current = true;
      setIsLoading(false);
    }
  }, []);

  const refreshUser = useCallback(
    async (updatedUserData = null) => {
      if (updatedUserData) {
        setUser(updatedUserData);
        finishInitialLoad();
        return updatedUserData;
      }

      const token = localStorage.getItem("access_token");
      const isInitialLoad = !initialLoadDoneRef.current;

      if (!token) {
        setUser(null);
        finishInitialLoad();
        return null;
      }

      if (isInitialLoad) {
        setIsLoading(true);
      }

      try {
        const decoded = jwtDecode(token);
        const response = await getUser(decoded.user_id);
        setUser(response.data);
        return response.data;
      } catch (error) {
        console.error("Failed to refresh user:", error);
        if (error.response?.status === 401) {
          await handleLogout();
          return null;
        }
        // Transient errors must not clear an established session.
        setUser((current) => current);
        return null;
      } finally {
        finishInitialLoad();
      }
    },
    [handleLogout, finishInitialLoad]
  );

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const value = { user, isLoading, handleLogout, refreshUser };

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

const defaultUserContext = {
  user: null,
  isLoading: false,
  handleLogout: async () => {},
  refreshUser: async () => null,
};

export function useUser() {
  const context = useContext(UserContext);
  return context ?? defaultUserContext;
}
