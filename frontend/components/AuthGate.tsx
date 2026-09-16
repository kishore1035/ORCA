// frontend/components/AuthGate.tsx
"use client";
import { useState, FormEvent } from "react";
import { signup, login } from "@/lib/chatClient";
import { AuthResponse } from "@/lib/types";

interface AuthGateProps {
  onAuthenticated: (auth: AuthResponse) => void;
  onSkip?: () => void;
}

export function AuthGate({ onAuthenticated, onSkip }: AuthGateProps) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const auth = mode === "login" ? await login(email, password) : await signup(email, password);
      onAuthenticated(auth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex items-center justify-center h-screen">
      <form onSubmit={handleSubmit} className="w-full max-w-sm border rounded p-6 space-y-3">
        <h1 className="text-lg font-semibold">ORCA</h1>
        <div className="flex gap-2 text-sm">
          <button
            type="button"
            onClick={() => setMode("login")}
            className={mode === "login" ? "font-semibold underline" : "text-slate-500"}
          >
            Log in
          </button>
          <button
            type="button"
            onClick={() => setMode("signup")}
            className={mode === "signup" ? "font-semibold underline" : "text-slate-500"}
          >
            Sign up
          </button>
        </div>
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
        <input
          type="password"
          required
          minLength={8}
          placeholder="Password (min 8 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          {mode === "login" ? "Log in" : "Sign up"}
        </button>
        {onSkip && (
          <button
            type="button"
            onClick={onSkip}
            className="w-full text-sm text-slate-500 hover:text-black hover:underline"
          >
            Continue without an account
          </button>
        )}
      </form>
    </div>
  );
}
