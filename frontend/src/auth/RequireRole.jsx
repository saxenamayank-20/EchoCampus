import { Navigate, Outlet, useLocation } from "react-router-dom";
import { homeFor, useAuth } from "./AuthContext";

// route guard: not logged in -> login page, wrong role -> your own home page
export default function RequireRole({ roles }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return <Outlet />;
}
