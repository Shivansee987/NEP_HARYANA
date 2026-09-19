import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  School,
  ClipboardList,
  History,
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
    { name: 'Overview', path: '/committee', icon: LayoutDashboard },
    { name: 'Assigned Submissions', path: '/committee/submissions', icon: ClipboardList },
    { name: 'Review History', path: '/committee/history', icon: History },
  ];

  return (
    <div className="peer fixed inset-y-0 left-0 w-20 hover:w-64 bg-white text-slate-800 flex flex-col z-20 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border-r border-slate-100 transition-all duration-300 ease-in-out group overflow-hidden">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-4 border-b border-slate-100 bg-slate-50/30">
        <div className="flex items-center space-x-3 w-full">
          <div className="w-10 h-10 rounded-xl bg-white border border-slate-200/60 flex items-center justify-center shadow-sm shrink-0 overflow-hidden p-1 transition-transform duration-300 group-hover:scale-105">
            <img src={hshecLogo} alt="HSHEC Logo" className="w-full h-full object-contain" />
          </div>
          <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap min-w-0">
            <h1 className="text-xs font-bold tracking-tight text-slate-800 leading-none">HSHEC NEP</h1>
            <span className="text-[9px] text-orange-600 font-bold uppercase tracking-wider block mt-0.5">
              {user?.role === 'committee_chair' ? 'Screening Committee (Chair)' : 'Screening Committee'}
            </span>
          </div>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1.5">
        <span className="px-3.5 text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-2.5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
          Committee Panel
        </span>
        <ul className="space-y-1">
          {links.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.path ||
              (link.path !== '/committee' && location.pathname.startsWith(link.path));
            return (
              <li key={link.path}>
                <Link
                  to={link.path}
                  className={`flex items-center gap-3 px-3.5 py-3 rounded-xl transition-all duration-300 text-sm font-medium relative group/item ${isActive
                      ? 'bg-gradient-to-r from-orange-500 to-amber-600 text-white shadow-md shadow-orange-500/20 font-semibold'
                      : 'text-slate-600 hover:bg-orange-50/50 hover:text-orange-600'
                    }`}
                >
                  <Icon className={`w-5 h-5 shrink-0 transition-transform duration-300 group-hover/item:scale-110 ${isActive ? 'text-white' : 'text-slate-400 group-hover/item:text-orange-600'
                    }`} />
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

      {/* Profile Footer */}
      <div className="p-4 border-t border-slate-100 bg-slate-50/40 backdrop-blur-md">
        <div className="flex items-center space-x-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-orange-100 to-amber-50 border border-orange-200/50 flex items-center justify-center text-orange-600 font-bold shadow-sm shrink-0">
            <UserCheck className="w-5 h-5 text-orange-600" />
          </div>
          <div className="min-w-0 flex-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
            <p className="text-xs font-semibold text-slate-800 truncate">{user?.full_name || "Committee Officer"}</p>
            <p className="text-[10px] text-orange-600 font-semibold truncate">
              {user?.role === 'committee_chair' ? 'Committee Chair' : 'Evaluator'}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold text-slate-500 hover:text-red-600 hover:bg-red-50 border border-transparent hover:border-red-100 rounded-lg transition-all duration-300 cursor-pointer"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          <span className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
            Lock Panel
          </span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
