import { Routes, Route, useLocation, Navigate } from "react-router-dom";
import NavbarV2 from "./components/NavbarV2/NavbarV2";
import Footer from "./components/Footer/Footer";
import Home from "./pages/Home/Home";
import AboutUs from "./pages/AboutUs/AboutUs";
import Institutions from "./pages/Institutions/Institutions";
import Notifications from "./pages/Notifications/Notifications";
import Schemes from "./components/Schemes/Schemes";
import ContactUs from "./pages/ContactUs/ContactUs";
import Signup from "./pages/Signup/Signup";
import Signin from "./pages/Signin/Signin";
import ForgotPassword from "./pages/ForgotPassword/ForgotPassword";
import ResetPassword from "./pages/ResetPassword/ResetPassword";
import CollegeDashboard from "./pages/CollegeDashboard/CollegeDashboard";
import CollegeAssessmentWorkspace from "./pages/Institution/CollegeAssessmentWorkspace";
import UniversityAssessmentWorkspace from "./pages/Institution/UniversityAssessmentWorkspace";

// New Admin Panel imports
import AdminLayout from "./components/Admin/AdminLayout";
import AdminOverview from "./pages/Admin/AdminOverview";
import CollegeManagement from "./pages/Admin/CollegeManagement";
import CollegeDetail from "./pages/Admin/CollegeDetail";
import Reports from "./pages/Admin/Reports";
import Settings from "./pages/Admin/Settings";
import Scoring from "./pages/Admin/Scoring";

import {
  ProtectedRoute,
  GuestRoute,
} from "./components/ProtectedRoute/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext.jsx";

// Modern Checker Dashboard imports (Phase W4)
import CheckerLayout from "./components/Checker/CheckerLayout";
import CheckerQueue from "./pages/Checker/CheckerQueue";
import CheckerAssessmentReview from "./pages/Checker/CheckerAssessmentReview";

// Screening Committee Dashboard imports (legacy)
import CommitteeLayout from "./components/Committee/CommitteeLayout";
import CommitteeOverview from "./pages/Committee/CommitteeOverview";
import CommitteeSubmissions from "./pages/Committee/CommitteeSubmissions";
import CommitteeReviewDetail from "./pages/Committee/CommitteeReviewDetail";

// University Dashboard imports (nodal_officer, university_admin)
import UniversityLayout from "./components/University/UniversityLayout";
import UniversityDashboard from "./pages/University/UniversityDashboard";

function App() {
  const location = useLocation();
  const isDashboard =
    location.pathname.startsWith("/institution/") ||
    location.pathname.startsWith("/admin") ||
    location.pathname.startsWith("/committee") ||
    location.pathname.startsWith("/checker") ||
    location.pathname.startsWith("/university");

  return (
    <AuthProvider>
      {!isDashboard && <NavbarV2 />}
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<AboutUs />} />
        <Route path="/institutions" element={<Institutions />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/schemes" element={
          <div style={{ paddingTop: '80px' }}>
            <Schemes />
          </div>
        } />
        <Route path="/contact" element={<ContactUs />} />

        {/* Guest Routes */}
        <Route
          path="/auth/signup"
          element={
            <GuestRoute>
              <Signup />
            </GuestRoute>
          }
        />
        <Route
          path="/auth/login"
          element={
            <GuestRoute>
              <Signin />
            </GuestRoute>
          }
        />
        <Route
          path="/auth/forgot-password"
          element={
            <GuestRoute>
              <ForgotPassword />
            </GuestRoute>
          }
        />
        <Route
          path="/auth/reset-password/:uid/:token"
          element={
            <GuestRoute>
              <ResetPassword />
            </GuestRoute>
          }
        />

        {/* Protected Routes - College Dashboard & Assessment Workspace */}
        <Route
          path="/institution/:institutionName/:institutionAisheCode/dashboard"
          element={
            <ProtectedRoute allowedRoles={["principal"]}>
              <CollegeDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/institution/:institutionName/:institutionAisheCode/assessment/:assessmentId"
          element={
            <ProtectedRoute allowedRoles={["principal"]}>
              <CollegeAssessmentWorkspace />
            </ProtectedRoute>
          }
        />
        <Route
          path="/institution/:institutionName/:institutionAisheCode/dashboard/forms/:formId"
          element={
            <ProtectedRoute allowedRoles={["principal"]}>
              <CollegeDashboard />
            </ProtectedRoute>
          }
        />


        {/* Protected Routes - DHE Admin Console */}
        <Route
          element={
            <ProtectedRoute allowedRoles={["admin"]}>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/admin" element={<AdminOverview />} />
          <Route path="/admin/reviews" element={<CollegeManagement onlySubmitted={true} />} />
          <Route path="/admin/colleges" element={<CollegeManagement />} />
          <Route path="/admin/colleges/:id" element={<CollegeDetail />} />
          <Route path="/admin/scoring" element={<Scoring />} />
          <Route path="/admin/reports" element={<Reports />} />
          <Route path="/admin/settings" element={<Settings />} />
        </Route>

        {/* Protected Routes - Modern Screening Committee / Checker Console (Phase W4) */}
        <Route
          element={
            <ProtectedRoute allowedRoles={["committee", "committee_chair", "admin"]}>
              <CheckerLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/checker" element={<Navigate to="/checker/queue" replace />} />
          <Route path="/checker/queue" element={<CheckerQueue />} />
          <Route path="/checker/assessment/:assessmentId" element={<CheckerAssessmentReview />} />

          {/* Seamless rewiring of /committee to modern assessment review workflow */}
          <Route path="/committee" element={<Navigate to="/checker/queue" replace />} />
          <Route path="/committee/queue" element={<CheckerQueue />} />
          <Route path="/committee/assessment/:assessmentId" element={<CheckerAssessmentReview />} />
          <Route path="/committee/submissions" element={<CheckerQueue />} />
          <Route path="/committee/history" element={<CheckerQueue />} />
        </Route>

        {/* Isolated Legacy Committee Questionnaire (Historical Route) */}
        <Route
          element={
            <ProtectedRoute allowedRoles={["committee", "committee_chair"]}>
              <CommitteeLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/legacy/committee/submissions/:id" element={<CommitteeReviewDetail />} />
          <Route path="/committee/submissions/:id" element={<CommitteeReviewDetail />} />
        </Route>

        {/* Protected Routes - University Console & Assessment Workspace (nodal_officer, university_admin) */}
        <Route
          element={
            <ProtectedRoute allowedRoles={["nodal_officer", "university_admin"]}>
              <UniversityLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/university" element={<UniversityDashboard />} />
          <Route path="/university/assessment/:assessmentId" element={<UniversityAssessmentWorkspace />} />
        </Route>

        {/* Redirects */}
        <Route
          path="/admin/dashboard"
          element={<Navigate to="/admin" replace />}
        />
        <Route
          path="/admin/dashbpard"
          element={<Navigate to="/admin" replace />}
        />
      </Routes>
      {!isDashboard && <Footer />}
    </AuthProvider>
  );
}

export default App;
