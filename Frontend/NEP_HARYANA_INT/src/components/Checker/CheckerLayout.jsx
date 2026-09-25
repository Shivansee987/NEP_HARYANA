import React from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ClipboardList,
  FileCheck2,
  LogOut,
  UserCheck,
  Building2,
  GraduationCap,
  ShieldCheck,
  ChevronRight,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext.jsx";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import Footer from "../Admin/Footer";

export default function CheckerLayout({ title = "Screening Committee Review Console" }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      navigate("/auth/login");
    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  const isAssessing = location.pathname.includes("/assessment/");
  const assessmentIdMatch = location.pathname.match(/\/assessment\/([^/]+)/);
  const activeAssessmentId = assessmentIdMatch ? assessmentIdMatch[1] : null;

  const links = [
    {
      name: "Review Queue",
      path: "/checker/queue",
      icon: ClipboardList,
      exact: false,
    },
  ];

  if (activeAssessmentId) {
    links.push({
      name: "Active Assessment",
      path: `/checker/assessment/${activeAssessmentId}`,
      icon: FileCheck2,
      exact: true,
    });
  }

  const roleTitle = user?.role === "committee_chair" ? "Screening Committee Chair" : "Screening Committee Reviewer";

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
      {/* Persistent Left Sidebar */}
      <aside className="peer fixed inset-y-0 left-0 w-20 hover:w-64 bg-white text-slate-800 flex flex-col z-30 shadow-[0_4px_24px_rgba(0,0,0,0.06)] border-r border-slate-200/80 transition-all duration-300 ease-in-out group overflow-hidden">
        {/* Brand Header */}
        <div className="h-16 flex items-center px-4 border-b border-slate-100 bg-slate-50/60">
          <div className="flex items-center space-x-3 w-full">
            <div className="w-10 h-10 rounded-xl bg-white border border-slate-200/80 flex items-center justify-center shadow-xs shrink-0 overflow-hidden p-1 transition-transform duration-300 group-hover:scale-105">
              <img src={hshecLogo} alt="HSHEC Logo" className="w-full h-full object-contain" />
            </div>
            <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap min-w-0">
              <h1 className="text-xs font-bold tracking-tight text-slate-800 leading-none">HSHEC NEP 2026</h1>
              <span className="text-[10px] text-amber-700 font-bold uppercase tracking-wider block mt-0.5">
                Review Portal
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1.5">
          <span className="px-3.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-2.5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
            Checker Workflow
          </span>
          <ul className="space-y-1">
            {links.map((link) => {
              const Icon = link.icon;
              const isActive = location.pathname === link.path || (!link.exact && location.pathname.startsWith(link.path));
              return (
                <li key={link.path}>
                  <Link
                    to={link.path}
                    className={`flex items-center gap-3 px-3.5 py-3 rounded-xl transition-all duration-200 text-sm font-medium relative group/item ${
                      isActive
                        ? "bg-gradient-to-r from-amber-600 to-orange-600 text-white shadow-md shadow-orange-600/20 font-semibold"
                        : "text-slate-600 hover:bg-amber-50/60 hover:text-amber-700"
                    }`}
                  >
                    <Icon className={`w-5 h-5 shrink-0 transition-transform duration-200 group-hover/item:scale-110 ${isActive ? "text-white" : "text-slate-400 group-hover/item:text-amber-700"}`} />
                    <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
                      {link.name}
                    </span>
                    {isActive && (
                      <span className="absolute right-3 w-1.5 h-1.5 rounded-full bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Reviewer Profile Footer */}
        <div className="p-3.5 border-t border-slate-100 bg-slate-50/60 backdrop-blur-xs">
          <div className="flex items-center space-x-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100/80 border border-amber-200 flex items-center justify-center text-amber-700 font-bold shadow-xs shrink-0">
              <UserCheck className="w-5 h-5 text-amber-700" />
            </div>
            <div className="min-w-0 flex-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
              <p className="text-xs font-bold text-slate-800 truncate">{user?.full_name || "Screening Reviewer"}</p>
              <p className="text-[10px] text-amber-700 font-medium truncate">{roleTitle}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold text-slate-500 hover:text-red-700 hover:bg-red-50 border border-transparent hover:border-red-100 rounded-lg transition-all cursor-pointer"
          >
            <LogOut className="w-4 h-4 shrink-0" />
            <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="pl-20 transition-all duration-300 ease-in-out flex-1 flex flex-col">
        {/* Top Header Bar */}
        <header className="h-16 bg-white border-b border-slate-200/80 sticky top-0 z-20 px-6 flex items-center justify-between shadow-2xs">
          <div className="flex items-center gap-2.5">
            <span className="text-xs font-semibold text-slate-400">NEP 2026</span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <h2 className="text-sm font-bold text-slate-800 tracking-tight">{title}</h2>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-amber-50/80 border border-amber-200/60 rounded-full text-xs font-semibold text-amber-800">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
              <span>{roleTitle}</span>
            </div>
            <div className="text-right text-xs">
              <span className="text-slate-400 block text-[10px]">Logged in as</span>
              <span className="font-semibold text-slate-700">{user?.email}</span>
            </div>
          </div>
        </header>

        {/* Page Content View */}
        <main className="p-6 sm:p-8 flex-1">
          <Outlet />
        </main>

        <Footer />
      </div>
    </div>
  );
}
