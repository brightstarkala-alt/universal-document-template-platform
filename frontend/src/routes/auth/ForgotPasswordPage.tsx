import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

export function ForgotPasswordPage() {
  const { requestPasswordReset } = useAuth();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const { error: resetError } = await requestPasswordReset(email);

    setIsSubmitting(false);
    if (resetError) {
      setError(resetError);
      return;
    }
    setIsSubmitted(true);
  };

  return (
    <div className="flex h-full w-full items-center justify-center">
      <div className="w-full max-w-sm space-y-4 rounded-lg border border-gray-200 p-6">
        <h1 className="text-xl font-semibold text-gray-900">Reset your password</h1>

        {isSubmitted ? (
          <p className="text-sm text-gray-600">
            If an account exists for {email}, a password reset link has been sent.
          </p>
        ) : (
          <form onSubmit={(event) => void handleSubmit(event)} className="space-y-4">
            {error && (
              <p role="alert" className="text-sm text-red-600">
                {error}
              </p>
            )}

            <div className="space-y-1">
              <label htmlFor="email" className="text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {isSubmitting ? "Sending…" : "Send reset link"}
            </button>
          </form>
        )}

        <p className="text-center text-sm text-gray-500">
          <Link to="/login" className="underline">
            Back to log in
          </Link>
        </p>
      </div>
    </div>
  );
}
