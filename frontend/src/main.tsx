import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";

import "./i18n";
import "./index.css";
import { Layout } from "./components/Layout";
import { EmptyState } from "./pages/EmptyState";
import { PersonDetail } from "./pages/PersonDetail";
import { PersonForm, ProfileForm } from "./pages/PersonForm";
import { Profile } from "./pages/Profile";
import { Settings } from "./pages/Settings";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<EmptyState />} />
            <Route path="people/new" element={<PersonForm />} />
            <Route path="people/:id" element={<PersonDetail />} />
            <Route path="people/:id/edit" element={<PersonForm />} />
            <Route path="me" element={<Profile />} />
            <Route path="me/edit" element={<ProfileForm />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
