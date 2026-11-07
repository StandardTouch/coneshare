import { Navigate } from 'react-router-dom';

/** Legacy route — merged into unified Roles admin. */
export function AdminRbacPage() {
  return <Navigate to="/admin/roles" replace />;
}
