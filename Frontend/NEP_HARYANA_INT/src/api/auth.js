export const API_BASE_URL = (
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
    const err = new Error(firstMessage);
    err.code = data?.code || data?.reason;
    err.reason = data?.reason || data?.code;
    err.account_already_verified = Boolean(data?.account_already_verified || data?.already_verified);
    err.already_verified = Boolean(data?.already_verified || data?.account_already_verified);
    err.email = data?.email;
    err.status = response.status;
    err.data = data;
    throw err;
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

export function fetchUniversities() {
  return request("/auth/universities/");
}

export async function verifyUniversityAishe(aisheCode, options = {}) {
  // If an object is passed: { aisheCode, name, universityId }
  if (typeof aisheCode === "object" && aisheCode !== null) {
    const params = new URLSearchParams();
    if (aisheCode.aisheCode || aisheCode.aishe_code) {
      params.append("aishe_code", (aisheCode.aisheCode || aisheCode.aishe_code).trim());
    }
    if (aisheCode.name || aisheCode.universityName) {
      params.append("name", (aisheCode.name || aisheCode.universityName).trim());
    }
    if (aisheCode.universityId || aisheCode.id) {
      params.append("university_id", aisheCode.universityId || aisheCode.id);
    }
    return request(`/auth/university/lookup/?${params.toString()}`);
  }

  const code = encodeURIComponent(String(aisheCode || "").trim());
  let url = `/auth/university/lookup/?aishe_code=${code}`;
  if (typeof options === "string" && options.trim()) {
    url += `&name=${encodeURIComponent(options.trim())}`;
  } else if (options && typeof options === "object") {
    if (options.name || options.universityName) {
      url += `&name=${encodeURIComponent((options.name || options.universityName).trim())}`;
    }
    if (options.universityId || options.id) {
      url += `&university_id=${encodeURIComponent(options.universityId || options.id)}`;
    }
  }
  return request(url);
}

export async function verifyCollegeAishe(aisheCode) {
  const code = encodeURIComponent(String(aisheCode || "").trim());
  return request(`/auth/college/lookup/?aishe_code=${code}`);
}

export async function sendPhoneOtp(phoneNumber) {
  return request("/auth/otp/send/", {
    method: "POST",
    body: JSON.stringify({ phone_number: phoneNumber }),
  });
}

export async function verifyPhoneOtp(phoneNumber, otp) {
  return request("/auth/otp/verify/", {
    method: "POST",
    body: JSON.stringify({ phone_number: phoneNumber, otp }),
  });
}

export async function registerUniversity(payload) {
  const data = await request("/auth/university/register/", {
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
  return request("/auth/colleges/");
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

export function verifyAccountActivation(token) {
  return request(`/auth/activate/verify/?token=${encodeURIComponent(token)}`, {
    method: "GET",
  });
}

export function confirmAccountActivation(payload) {
  return request("/auth/activate/confirm/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyEmailToken(token) {
  return request(`/auth/verify-email/?token=${encodeURIComponent(token)}`, {
    method: "GET",
  });
}

export async function confirmEmailVerification(token) {
  return request("/auth/verify-email/confirm/", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export async function resendEmailVerification(email) {
  return request("/auth/resend-verification/", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function verifyEmailOtp(email, otp) {
  return request("/auth/verify-email/otp/", {
    method: "POST",
    body: JSON.stringify({ email, otp }),
  });
}

export async function resendEmailOtp(email) {
  return request("/auth/verify-email/otp/resend/", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function requestEmailOtp(email) {
  return request("/auth/verify-email/otp/request/", {
    method: "POST",
    body: JSON.stringify({ email }),
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

  if (role === "admin" || role === "head_admin" || role === "sub_admin" || role === "state_admin" || role === "council_admin") {
    return "/admin";
  }

  // Screening Committee members and chairs use the checker console.
  if (role === "committee" || role === "committee_chair") {
    return "/checker/queue";
  }

  // Empowered Committee roles have their own landing page (the checker console does not admit them, and
  // sending them there caused a redirect loop / blank page).
  if (role === "empowered_committee" || role === "empowered_committee_chair") {
    return "/empowered";
  }


  // University roles: nodal officers and university admins use the university console.
  if (role === "nodal_officer" || role === "university_admin") {
    return "/university";
  }

  // Safe fallback — home page, not /admin, to avoid infinite redirect loops.
  return "/";
}

