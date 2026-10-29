import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { homeFor, useAuth } from "./auth/AuthContext";
import RequireRole from "./auth/RequireRole";
import { SkeletonRows } from "./components/Feedback";
import Layout from "./components/Layout";
import { AllComplaints, CloseRequests, ManagerUpdates, UsersPage } from "./pages/admin/AdminPages";
import { LoginPage, NotFoundPage, RegisterPage, VerifyOtpPage } from "./pages/AuthPages";
import Queue from "./pages/manager/Queue";
import MyTickets from "./pages/student/MyTickets";
import NewComplaint from "./pages/student/NewComplaint";
import TicketDetail from "./pages/TicketDetail";

// charts library is big, only load it when the admin opens the overview
const Overview = lazy(() => import("./pages/admin/Overview"));

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify" element={<VerifyOtpPage />} />

      {/* everything below needs a login, each group also needs the right role */}
      <Route element={<RequireRole />}>
        <Route element={<Layout />}>
          <Route path="/tickets/:ticketId" element={<TicketDetail />} />

          <Route element={<RequireRole roles={["student"]} />}>
            <Route path="/student/new" element={<NewComplaint />} />
            <Route path="/student/tickets" element={<MyTickets />} />
          </Route>

          <Route element={<RequireRole roles={["grievance_manager"]} />}>
            <Route path="/manager/queue" element={<Queue />} />
          </Route>

          <Route element={<RequireRole roles={["admin"]} />}>
            <Route path="/admin" element={<Suspense fallback={<SkeletonRows />}><Overview /></Suspense>} />
            <Route path="/admin/complaints" element={<AllComplaints />} />
            <Route path="/admin/close-requests" element={<CloseRequests />} />
            <Route path="/admin/updates" element={<ManagerUpdates />} />
            <Route path="/admin/users" element={<UsersPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
