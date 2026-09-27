import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  School,
  Award,
  FileSpreadsheet,
  Settings as SettingsIcon,
  LogOut,
  UserCheck
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext.jsx';
import hshecLogo from '../../assets/hshec_logo.jpeg';

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/auth/login');
    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  const links = [
    { name: 'Overview', path: '/admin', icon: LayoutDashboard },
    { name: 'Review Applications', path: '/admin/reviews', icon: UserCheck },
    { name: 'College List', path: '/admin/colleges', icon: School },
    { name: 'Scoring & Comparison', path: '/admin/scoring', icon: Award },
    { name: 'Reports', path: '/admin/reports', icon: FileSpreadsheet },
    { name: 'Settings', path: '/admin/settings', icon: SettingsIcon },
  ];

  return (
    <div className="peer fixed inset-y-0 left-0 w-20 hover:w-64 bg-white text-slate-800 flex flex-col z-50 shadow-xs hover:shadow-2xl border-r border-[#ebdcd0] transition-all duration-300 ease-in-out group overflow-hidden">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-4 border-b border-slate-100 bg-[#fdfaf6]">
        <div className="flex items-center space-x-3 w-full">
          <div className="w-10 h-10 rounded-xl bg-white border border-[#ebdcd0] flex items-center justify-center shadow-xs shrink-0 overflow-hidden p-1 transition-transform duration-300 group-hover:scale-105">
            <img src={hshecLogo} alt="HSHEC Logo" className="w-full h-full object-contain" />
          </div>
          <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap min-w-0">
            <h1 className="text-xs font-bold tracking-tight text-slate-800 leading-none">HSHEC NEP</h1>
            <span className="text-[9px] text-[#600b0b] font-bold uppercase tracking-wider block mt-0.5">Excellence Awards</span>
          </div>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1.5">
        <span className="px-3.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-2.5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
          Evaluation Console
        </span>
        <ul className="space-y-1">
          {links.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.path ||
              (link.path !== '/admin' && location.pathname.startsWith(link.path));
            return (
              <li key={link.path}>
                <Link
                  to={link.path}
                  className={`flex items-center gap-3 px-3.5 py-3 rounded-xl transition-all duration-300 text-sm font-medium relative group/item ${isActive
                      ? 'bg-[#600b0b] text-white shadow-xs border-l-4 border-[#c29b68] font-semibold'
                      : 'text-slate-600 hover:bg-[#eaded2]/50 hover:text-slate-900'
                    }`}
                >
                  <Icon className={`w-5 h-5 shrink-0 transition-transform duration-300 group-hover/item:scale-110 ${isActive ? 'text-white' : 'text-slate-500 group-hover/item:text-[#600b0b]'
                    }`} />
                  <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
                    {link.name}
                  </span>
                  {/* Subtle hover/active indicator */}
                  {isActive && (
                    <span className="absolute right-3 w-1.5 h-1.5 rounded-full bg-white opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Admin Profile Footer */}
      <div className="p-4 border-t border-slate-100 bg-[#fdfaf6]">
        <div className="flex items-center space-x-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-[#eaded2] border border-[#ebdcd0] flex items-center justify-center text-[#600b0b] font-bold shadow-xs shrink-0">
            <UserCheck className="w-5 h-5 text-[#600b0b]" />
          </div>
          <div className="min-w-0 flex-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
            <p className="text-xs font-semibold text-slate-800 truncate">{user?.full_name || "Admin Officer"}</p>
            <p className="text-[10px] text-[#600b0b] font-semibold truncate">{user?.role === "admin" ? "DHE Admin" : "Evaluator"}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold text-slate-500 hover:text-red-700 hover:bg-red-50 border border-transparent hover:border-red-100 rounded-lg transition-all duration-300 cursor-pointer"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
            Lock Console
          </span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
