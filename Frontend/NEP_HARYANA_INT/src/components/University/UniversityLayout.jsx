import { useState } from "react";
import { Link, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext.jsx";
import {
  LogOut,
  User,
  Building2,
  ChevronRight,
  Shield,
} from "lucide-react";
import hshecLogo from "../../assets/hshec_logo.jpeg";

const ROLE_LABELS = {
  nodal_officer: "University Nodal Officer",
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
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Header */}
      <header className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-40 px-4 sm:px-6 h-14 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <img
            src={hshecLogo}
            alt="HSHEC"
            className="w-8 h-8 rounded object-contain bg-white p-0.5"
          />
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold tracking-tight text-white block leading-none">
              NEP Excellence Awards 2026
            </span>
            <ChevronRight size={14} className="text-slate-600 hidden sm:block" />
            <span className="text-[10px] text-blue-400 font-semibold uppercase tracking-wider hidden sm:block">
              University Portal
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-blue-500/20 border border-blue-400/30 flex items-center justify-center text-blue-300">
              <User size={14} />
            </div>
            <div className="hidden sm:block text-right">
              <p className="text-xs font-bold text-slate-200 leading-none">
                {user?.full_name || "University Officer"}
              </p>
              <p className="text-[10px] text-slate-400">{roleLabel}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            disabled={loggingOut}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-xs font-semibold transition-colors disabled:opacity-50"
            title="Sign out of institutional session"
          >
            <LogOut size={13} />
            <span className="hidden sm:inline">{loggingOut ? "Signing out..." : "Sign Out"}</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
};

export default UniversityLayout;
