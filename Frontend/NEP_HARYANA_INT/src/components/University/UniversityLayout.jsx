import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import {
  LayoutDashboard,
  LogOut,
  User,
  Building2,
  ChevronRight,
} from "lucide-react";
import hshecLogo from "../../assets/hshec_logo.jpeg";

const ROLE_LABELS = {
  nodal_officer: "Nodal Officer",
  university_admin: "University Administrator",
};

const UniversityLayout = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      navigate("/auth/login", { replace: true });
    } finally {
      setLoggingOut(false);
    }
  };

  const roleLabel = ROLE_LABELS[user?.role] || user?.role || "University User";

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Header */}
      <header
        style={{
          background: "linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)",
          color: "#f8fafc",
          padding: "0 24px",
          height: "56px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 100,
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <img
            src={hshecLogo}
            alt="HSHEC"
            style={{ height: "32px", width: "32px", objectFit: "contain", borderRadius: "6px" }}
          />
          <span style={{ fontWeight: 700, fontSize: "14px", letterSpacing: "0.01em" }}>
            NEP Excellence Awards 2026
          </span>
          <ChevronRight size={14} style={{ opacity: 0.4 }} />
          <span style={{ fontSize: "12px", color: "#93c5fd", fontWeight: 600 }}>
            University Portal
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div
              style={{
                width: "30px",
                height: "30px",
                background: "rgba(59,130,246,0.2)",
                border: "1px solid rgba(59,130,246,0.4)",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <User size={14} color="#93c5fd" />
            </div>
            <div>
              <p style={{ fontSize: "11px", fontWeight: 700, margin: 0, color: "#f1f5f9" }}>
                {user?.full_name || "User"}
              </p>
              <p style={{ fontSize: "10px", color: "#94a3b8", margin: 0 }}>{roleLabel}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            disabled={loggingOut}
            style={{
              background: "rgba(239,68,68,0.15)",
              border: "1px solid rgba(239,68,68,0.3)",
              color: "#fca5a5",
              borderRadius: "8px",
              padding: "6px 12px",
              fontSize: "11px",
              fontWeight: 700,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <LogOut size={12} />
            {loggingOut ? "Signing out..." : "Sign Out"}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ paddingTop: "56px", flex: 1 }}>
        <Outlet />
      </main>
    </div>
  );
};

export default UniversityLayout;
