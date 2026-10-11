import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import hshecLogo from "../../assets/hshec_logo.jpeg";
import { getDashboardPathForUser } from "../../api/auth";
import { useAuth } from "../../context/AuthContext.jsx";
import "./NavbarV2.css";

function NavbarV2() {
  const navigate = useNavigate();
  const { user: savedUser } = useAuth();
  const [activeNav, setActiveNav] = useState("Home");
  const [fontSize, setFontSize] = useState(16);
  const [highContrast, setHighContrast] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState(null);

  const navItems = [
    {
      name: "Home",
      path: "/",
      scrollId: null,
    },
    {
      name: "About",
      path: "/about",
      scrollId: null,
    },
    {
      name: "Institutions",
      path: "/institutions",
      scrollId: null,
    },
    {
      name: "Notifications",
      path: "/notifications",
      scrollId: null,
    },
    {
      name: "Schemes",
      path: "/schemes",
      scrollId: null,
    },
    {
      name: "Contact",
      path: "/contact",
      scrollId: null,
    },
  ];

  const handleFontSize = (action) => {
    let newSize = fontSize;
    if (action === "increase" && fontSize < 22) newSize = fontSize + 1;
    if (action === "decrease" && fontSize > 12) newSize = fontSize - 1;
    if (action === "reset") newSize = 16;
    setFontSize(newSize);
    document.documentElement.style.fontSize = `${newSize}px`;
  };

  const toggleContrast = () => {
    setHighContrast(!highContrast);
    document.body.classList.toggle("high-contrast");
  };

  const handlePortalLoginClick = () => {
    if (savedUser) {
      navigate(getDashboardPathForUser(savedUser));
    } else {
      navigate("/auth/login");
    }
  };

  const performScroll = (elementId) => {
    if (!elementId) return;
    const element = document.getElementById(elementId);
    if (element) {
      const offset = 160; // Offset for the tall 3-tier navbar
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - offset;

      window.scrollTo({
        top: offsetPosition,
        behavior: "smooth",
      });
    } else {
      navigate(`/#${elementId}`);
      setTimeout(() => {
        const el = document.getElementById(elementId);
        if (el) {
          const offset = 160;
          const elementPosition = el.getBoundingClientRect().top;
          const offsetPosition = elementPosition + window.pageYOffset - offset;
          window.scrollTo({
            top: offsetPosition,
            behavior: "smooth",
          });
        }
      }, 150);
    }
  };

  const handleNavClick = (e, item) => {
    setActiveNav(item.name);
    setIsMenuOpen(false);
    setActiveDropdown(null);

    if (item.name === "Home") {
      e.preventDefault();
      navigate("/");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else if (item.path) {
      e.preventDefault();
      navigate(item.path);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else if (item.scrollId) {
      e.preventDefault();
      performScroll(item.scrollId);
    }
  };

  const handleSubmenuClick = (e, subitem) => {
    e.preventDefault();
    setIsMenuOpen(false);
    setActiveDropdown(null);
    if (subitem.path) {
      navigate(subitem.path);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else if (subitem.scrollId) {
      performScroll(subitem.scrollId);
    }
  };

  return (
    <header className={`navbar-v2 ${highContrast ? "high-contrast" : ""}`}>
      {/* ===== TIER 1: Utility & Accessibility Bar ===== */}
      <div className="v2-utility-bar">
        <div className="v2-utility-container">
          <div className="v2-utility-left">
            <span className="v2-state-indicator">
              Government of Haryana | हरियाणा सरकार
            </span>
          </div>
          <div className="v2-utility-right">
            <a href="#main-content" className="v2-utility-item skip-link">
              Skip to Main Content
            </a>
            <span className="v2-utility-divider">|</span>
            <div className="v2-utility-item text-size-controls">
              <button
                onClick={() => handleFontSize("decrease")}
                className="v2-size-btn"
                aria-label="Decrease text size"
              >
                A-
              </button>
              <button
                onClick={() => handleFontSize("reset")}
                className="v2-size-btn"
                aria-label="Reset text size"
              >
                A
              </button>
              <button
                onClick={() => handleFontSize("increase")}
                className="v2-size-btn"
                aria-label="Increase text size"
              >
                A+
              </button>
            </div>
            <span className="v2-utility-divider">|</span>
            <button
              className="v2-utility-item contrast-btn"
              onClick={toggleContrast}
              aria-label="Toggle contrast mode"
            >
              {highContrast ? "Standard" : "High Contrast"}
            </button>
            <span className="v2-utility-divider">|</span>
            <div className="v2-language-switcher">
              <button className="v2-lang-btn active">English</button>
              <button className="v2-lang-btn">हिन्दी</button>
            </div>
          </div>
        </div>
      </div>

      {/* ===== TIER 2: Branding & Search / Login ===== */}
      <div className="v2-header-bar">
        <div className="v2-header-container">
          <div className="v2-header-left" onClick={() => navigate("/")}>
            <img
              src={hshecLogo}
              alt="Haryana State Higher Education Council Logo"
              className="v2-brand-logo"
            />
            <div className="v2-brand-text">
              <h1 className="v2-brand-title">
                Haryana State Higher Education Council
              </h1>
              <p className="v2-brand-subtitle">
                हरियाणा राज्य उच्च शिक्षा परिषद् · Department of Higher Education
              </p>
            </div>
          </div>

          <div className="v2-header-right">
            <div className="v2-search-box">
              <span className="v2-search-icon">
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </span>
              <input
                type="text"
                placeholder="Search the portal..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search"
              />
            </div>
            {savedUser ? (
              <button
                onClick={handlePortalLoginClick}
                className="v2-login-btn"
              >
                Portal Dashboard
              </button>
            ) : (
              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <button
                  onClick={() => navigate("/auth/login")}
                  className="v2-login-btn"
                  style={{ background: "#600b0b", color: "#fff", borderColor: "#600b0b" }}
                  title="University & College Applicant Portal"
                >
                  Applicant Login
                </button>
                <button
                  onClick={() => navigate("/auth/admin/login")}
                  className="v2-login-btn"
                  style={{ background: "#eaded2", color: "#600b0b", borderColor: "#600b0b" }}
                  title="State Admin & Committee Review Portal"
                >
                  Admin Login
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ===== TIER 3: Navigation Menu ===== */}
      <nav className="v2-nav-bar">
        <div className="v2-nav-container">
          <div
            className={`v2-nav-hamburger ${isMenuOpen ? "open" : ""}`}
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label="Toggle navigation menu"
            aria-expanded={isMenuOpen}
          >
            <span></span>
            <span></span>
            <span></span>
          </div>

          <ul className={`v2-nav-list ${isMenuOpen ? "open" : ""}`}>
            {navItems.map((item) => {
              const isActive = activeNav === item.name;
              return (
                <li
                  key={item.name}
                  className={`v2-nav-item ${isActive ? "active" : ""}`}
                >
                  <a
                    href={item.path || "#"}
                    className="v2-nav-link"
                    onClick={(e) => handleNavClick(e, item)}
                  >
                    {item.name}
                  </a>
                </li>
              );
            })}
          </ul>
        </div>
      </nav>
    </header>
  );
}

export default NavbarV2;
