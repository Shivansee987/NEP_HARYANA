import { createContext, useContext, useState, useEffect } from "react";
import { getCurrentUser, loginCollege, registerCollege, registerUniversity, logoutCollege, getAccessToken } from "../api/auth";

const AuthContext = createContext(null);


export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async () => {
    if (!getAccessToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const data = await getCurrentUser();
      setUser(data);
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();

    const handleSessionExpired = () => {
      setUser(null);
    };

    window.addEventListener("auth-session-expired", handleSessionExpired);
    return () => {
      window.removeEventListener("auth-session-expired", handleSessionExpired);
    };
  }, []);

  useEffect(() => {
    if (!user) return;

    let timeoutId;

    const resetTimer = () => {
      if (timeoutId) clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        console.warn("User session timed out due to 10 minutes of inactivity.");
        logout();
      }, 10 * 60 * 1000); // 10 minutes = 600,000 ms
    };

    resetTimer();

    const events = ["mousedown", "mousemove", "keypress", "scroll", "touchstart"];
    events.forEach((evt) => {
      window.addEventListener(evt, resetTimer);
    });

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      events.forEach((evt) => {
        window.removeEventListener(evt, resetTimer);
      });
    };
  }, [user]);

  const login = async (credentials) => {
    try {
      const res = await loginCollege(credentials);
      setUser(res.user);
      return res;
    } catch (err) {
      setUser(null);
      throw err;
    }
  };

  const register = async (userData) => {
    try {
      const res = await registerCollege(userData);
      setUser(res.user);
      return res;
    } catch (err) {
      setUser(null);
      throw err;
    }
  };

  const registerUniversityAccount = async (userData) => {
    try {
      const res = await registerUniversity(userData);
      setUser(res.user);
      return res;
    } catch (err) {
      setUser(null);
      throw err;
    }
  };

  const logout = async () => {
    try {
      await logoutCollege();
    } catch (err) {
      console.error("Logout request failed:", err);
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, registerUniversityAccount, logout, fetchUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
