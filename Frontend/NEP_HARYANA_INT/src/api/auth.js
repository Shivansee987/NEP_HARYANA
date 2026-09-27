const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  `http://${window.location.hostname}:8000/api`
).replace(/\/$/, "");

let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb);
}

function onRefreshed() {
  refreshSubscribers.forEach((cb) => cb());
  refreshSubscribers = [];
}

// Token storage utilities
export function getAccessToken() {
  return sessionStorage.getItem("nep_haryana_access_token");
}

export function setAccessToken(token) {
  if (token) {
    sessionStorage.setItem("nep_haryana_access_token", token);
  } else {
    sessionStorage.removeItem("nep_haryana_access_token");
  }
}

export function getRefreshToken() {
  return sessionStorage.getItem("nep_haryana_refresh_token");
}

export function setRefreshToken(token) {
  if (token) {
    sessionStorage.setItem("nep_haryana_refresh_token", token);
  } else {
    sessionStorage.removeItem("nep_haryana_refresh_token");
  }
}

export async function request(path, options = {}) {
  const headers = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
  };

  const accessToken = getAccessToken();
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  // Only refresh on 401 (token expired/missing). 403 is a permission denial
  // and must surface to the UI immediately — do NOT enter the refresh loop.
  if (
    response.status === 401 &&
    path !== "/auth/refresh/" &&
    path !== "/auth/login/" &&
    path !== "/auth/signup/"
  ) {
    const rToken = getRefreshToken();
    if (!rToken) {
      window.dispatchEvent(new Event("auth-session-expired"));
      throw new Error("No refresh token available");
    }

    if (!isRefreshing) {
      isRefreshing = true;
      try {
        await refreshSession();
        isRefreshing = false;
        onRefreshed();
      } catch (err) {
        isRefreshing = false;
        refreshSubscribers = [];
        setAccessToken(null);
        setRefreshToken(null);
        window.dispatchEvent(new Event("auth-session-expired"));
        throw err;
      }
    }

    return new Promise((resolve, reject) => {
      subscribeTokenRefresh(() => {
        request(path, options).then(resolve).catch(reject);
      });
    });
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const fallbackMessage = "Request failed.";
    const firstMessage =
      data?.detail ||
      Object.values(data || {})?.flat?.()?.[0] ||
      fallbackMessage;
    throw new Error(firstMessage);
  }

  return data;
}

export async function registerCollege(payload) {
  const data = await request("/auth/signup/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (data.tokens) {
    setAccessToken(data.tokens.access);
    setRefreshToken(data.tokens.refresh);
  }
  return data;
}

export function fetchColleges() {
  return request("/colleges/");
}

export async function loginCollege(payload) {
  const data = await request("/auth/login/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (data.tokens) {
    setAccessToken(data.tokens.access);
    setRefreshToken(data.tokens.refresh);
  }
  return data;
}

export async function refreshSession() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("No refresh token found.");
  }
  const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    setAccessToken(null);
    setRefreshToken(null);
    throw new Error("Session expired.");
  }

  const data = await response.json();
  if (data.tokens) {
    setAccessToken(data.tokens.access);
    setRefreshToken(data.tokens.refresh);
  }
  return data;
}

export async function logoutCollege() {
  const refreshToken = getRefreshToken();
  try {
    await request("/auth/logout/", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch (e) {
    // Keep proceeding to clear local tokens even if request fails
  } finally {
    setAccessToken(null);
    setRefreshToken(null);
  }
}

export function getCurrentUser() {
  return request("/auth/me/");
}

export function requestPasswordReset(payload) {
  return request("/auth/forgot-password/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function confirmPasswordReset(payload) {
  return request("/auth/reset-password/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getDashboardPathForUser(user) {
  const role = String(user?.role || "").toLowerCase();

  if (role === "principal") {
    const nameSlug = String(user?.college_name || "college")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)+/g, "");
    const codeSlug = String(user?.aishe_code || "code")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)+/g, "");
    return `/institution/${nameSlug}/${codeSlug}/dashboard`;
  }

  if (role === "admin") {
    return "/admin";
  }

  // Both committee members and the committee chair use the committee console.
  // The backend enforces chair-level authority (certification, assignment) separately.
  if (role === "committee" || role === "committee_chair") {
    return "/checker/queue";
  }

  // University roles: nodal officers and university admins use the university console.
  if (role === "nodal_officer" || role === "university_admin") {
    return "/university";
  }

  // Safe fallback — home page, not /admin, to avoid infinite redirect loops.
  return "/";
}
