import { useQuery, useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useEffect } from "react";

import { api, resetSession, setUnauthorizedHandler } from "../api";
import { Login } from "../pages/Login";

/** Shows the login page until someone is logged in, and again if the session ends. */
export function AuthGate({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { data: user, isPending } = useQuery({
    queryKey: ["auth", "user"],
    queryFn: api.currentUser,
    staleTime: Infinity,
    retry: false,
  });

  useEffect(() => {
    setUnauthorizedHandler(() => {
      // Session expired or logged out elsewhere: drop all cached data and show the login page.
      resetSession(queryClient, null);
    });
  }, [queryClient]);

  if (isPending) return null;
  if (!user) return <Login />;
  return <>{children}</>;
}
