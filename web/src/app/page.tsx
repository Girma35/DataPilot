"use client";

import { useAuth } from "@/context/AuthContext";
import { UserWorkflowPanel } from "@/components/UserWorkflowPanel";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";

function AuthErrorBanner() {
  const searchParams = useSearchParams();
  const err = searchParams.get("error");

  const message = useMemo(() => {
    if (!err) return null;
    const map: Record<string, string> = {
      invalid_state: "Login session expired. Try signing in again.",
      no_code: "Auth0 did not return an authorization code.",
      token_exchange_failed: "Could not exchange the code for tokens. Check Auth0 application settings and client secret.",
      callback_error: "Unexpected error during sign-in.",
    };
    return map[err] ?? `Sign-in error: ${err}`;
  }, [err]);

  if (!message) return null;

  return (
    <div
      role="alert"
      className="mb-6 w-full rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100"
    >
      {message}
    </div>
  );
}

export default function Home() {
  const { user, isAuthenticated, login, logout, isLoading } = useAuth();

  return (
    <div className="flex min-h-full flex-col bg-zinc-50 font-sans dark:bg-black">
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-6 py-16 sm:px-8">
        <p className="text-sm font-medium uppercase tracking-wider text-zinc-500">DataPilot</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
          {isAuthenticated ? `Signed in as ${user?.name || user?.email || user?.sub}` : "Sign in to run the workflow"}
        </h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-zinc-600 dark:text-zinc-400">
          After Auth0 login, this app proxies your access token to the FastAPI backend: health check, read-only SQL, and optional
          Slack/Discord alerts.
        </p>

        <Suspense fallback={null}>
          <AuthErrorBanner />
        </Suspense>

        <div className="mt-8 flex flex-wrap gap-3">
          {isLoading ? (
            <span className="text-sm text-zinc-500">Loading session…</span>
          ) : isAuthenticated ? (
            <button
              type="button"
              onClick={logout}
              className="rounded-full border border-zinc-300 px-5 py-2.5 text-sm font-medium text-zinc-900 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-100 dark:hover:bg-zinc-900"
            >
              Sign out
            </button>
          ) : (
            <button
              type="button"
              onClick={login}
              className="rounded-full bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-black dark:hover:bg-zinc-200"
            >
              Sign in with Auth0
            </button>
          )}
        </div>

        {isAuthenticated && !isLoading ? <UserWorkflowPanel /> : null}
      </main>
    </div>
  );
}
