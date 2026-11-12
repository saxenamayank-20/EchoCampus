import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { homeFor, useAuth } from "./auth/AuthContext";
import RequireRole from "./auth/RequireRole";
import { SkeletonRows } from "./components/Feedback";
import Layout from "./components/Layout";
import { AllComplaints, CloseRequests, ManagerUpdates, UsersPage } from "./pages/admin/AdminPages";
import { LoginPage, NotFoundPage, RegisterPage, VerifyOtpPage } from "./pages/AuthPages";
import Queue from "./pages/manager/Queue";
import ManagerOverview from "./pages/manager/Overview";
import MyTickets from "./pages/student/MyTickets";
import Assistant from "./pages/student/Assistant";
import NewComplaint from "./pages/student/NewComplaint";
import Policies from "./pages/admin/Policies";
import AiUsage from "./pages/admin/AiUsage";
import TicketDetail from "./pages/TicketDetail";
import Account from "./pages/Account";
import Landing from "./pages/Landing";
import { ForgotPage, LoginCodePage } from "./pages/ForgotDetails";

// charts library is big, only load it when the admin opens the overview
const Overview = lazy(() => import("./pages/admin/Overview"));

// logged in -> your own dashboard, visitors -> the landing page
function Home() {
  const { user } = useAuth();
  return user ? <Navigate to={homeFor(user.role)} replace /> : <Landing />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify" element={<VerifyOtpPage />} />
      <Route path="/forgot" element={<ForgotPage />} />
      <Route path="/login-code" element={<LoginCodePage />} />

      {/* everything below needs a login, each group also needs the right role */}
      <Route element={<RequireRole />}>
        <Route element={<Layout />}>
          <Route path="/tickets/:ticketId" element={<TicketDetail />} />
          <Route path="/account" element={<Account />} />

          <Route element={<RequireRole roles={["student"]} />}>
            <Route path="/student/new" element={<NewComplaint />} />
            <Route path="/student/tickets" element={<MyTickets />} />
            <Route path="/student/assistant" element={<Assistant />} />
          </Route>

          <Route element={<RequireRole roles={["grievance_manager"]} />}>
            <Route path="/manager" element={<ManagerOverview />} />
            <Route path="/manager/queue" element={<Queue />} />
          </Route>

          <Route element={<RequireRole roles={["admin"]} />}>
            <Route path="/admin" element={<Suspense fallback={<SkeletonRows />}><Overview /></Suspense>} />
            <Route path="/admin/complaints" element={<AllComplaints />} />
            <Route path="/admin/close-requests" element={<CloseRequests />} />
            <Route path="/admin/updates" element={<ManagerUpdates />} />
            <Route path="/admin/users" element={<UsersPage />} />
            <Route path="/admin/policies" element={<Policies />} />
            <Route path="/admin/ai-usage" element={<AiUsage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
