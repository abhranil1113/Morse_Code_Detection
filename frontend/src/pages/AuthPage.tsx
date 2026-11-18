import React, { useState } from "react";
import { api } from "../services/api";
import { User } from "../types";

interface AuthPageProps {
  onAuthSuccess: (user: User) => void;
}

export const AuthPage: React.FC<AuthPageProps> = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (!email.trim() || !password) {
      setError("Please fill in all required fields.");
      return;
    }

    setLoading(true);

    try {
      if (isLogin) {
        await api.login(email.trim(), password);
        const currentUser = await api.getCurrentUser();
        onAuthSuccess(currentUser);
      } else {
        const effectiveUsername = username.trim() || email.split("@")[0] || "User";
        await api.register(email.trim(), effectiveUsername, password);
        // Do not auto-login: require explicit sign in with the newly created account
        setSuccessMessage("Account created successfully! Please enter your password to sign in.");
        setIsLogin(true);
        setPassword("");
      }
    } catch (err: any) {
      setError(err.message || (isLogin ? "Invalid email or password." : "Registration failed."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#090d16",
        backgroundImage: "radial-gradient(circle at 50% 20%, #1e293b 0%, #090d16 80%)",
        color: "#f8fafc",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      {/* Brand Header */}
      <div style={{ textAlign: "center", marginBottom: "28px", maxWidth: "480px" }}>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: "56px",
            height: "56px",
            borderRadius: "16px",
            backgroundColor: "#1e293b",
            border: "1px solid #334155",
            boxShadow: "0 8px 20px rgba(56, 189, 248, 0.15)",
            fontSize: "28px",
            marginBottom: "12px",
          }}
        >
          👁️
        </div>
        <h1
          style={{
            margin: "0 0 6px 0",
            fontSize: "30px",
            fontWeight: 800,
            letterSpacing: "-0.5px",
            background: "linear-gradient(135deg, #ffffff 30%, #38bdf8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          EyeSpeak AI
        </h1>
        <p style={{ margin: 0, fontSize: "14px", color: "#94a3b8", lineHeight: "1.5" }}>
          Real-Time Assistive Communication Platform
        </p>
      </div>

      {/* Main Auth Card */}
      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          backgroundColor: "#111827",
          border: "1px solid #1f2937",
          borderRadius: "16px",
          padding: "32px",
          boxShadow: "0 20px 40px rgba(0, 0, 0, 0.6)",
        }}
      >
        {/* Tab Switcher */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            backgroundColor: "#030712",
            borderRadius: "10px",
            padding: "4px",
            marginBottom: "24px",
            border: "1px solid #1f2937",
          }}
        >
          <button
            type="button"
            onClick={() => {
              setIsLogin(true);
              setError(null);
              setSuccessMessage(null);
            }}
            style={{
              padding: "9px 0",
              border: "none",
              borderRadius: "8px",
              backgroundColor: isLogin ? "#2563eb" : "transparent",
              color: isLogin ? "#ffffff" : "#9ca3af",
              fontSize: "14px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setIsLogin(false);
              setError(null);
              setSuccessMessage(null);
            }}
            style={{
              padding: "9px 0",
              border: "none",
              borderRadius: "8px",
              backgroundColor: !isLogin ? "#2563eb" : "transparent",
              color: !isLogin ? "#ffffff" : "#9ca3af",
              fontSize: "14px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            Create Account
          </button>
        </div>

        {/* Form Title & Subtitle */}
        <div style={{ marginBottom: "20px" }}>
          <h2 style={{ margin: "0 0 4px 0", fontSize: "18px", fontWeight: 700, color: "#f9fafb" }}>
            {isLogin ? "Welcome back" : "Get started with EyeSpeak"}
          </h2>
          <p style={{ margin: 0, fontSize: "13px", color: "#6b7280" }}>
            {isLogin
              ? "Sign in to access your assistive communication rooms"
              : "Register to start translating eye blinks into words"}
          </p>
        </div>

        {/* Success Alert */}
        {successMessage && (
          <div
            style={{
              padding: "11px 14px",
              backgroundColor: "rgba(16, 185, 129, 0.12)",
              border: "1px solid #10b981",
              borderRadius: "8px",
              color: "#6ee7b7",
              fontSize: "13px",
              marginBottom: "18px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <span>✅</span>
            <span>{successMessage}</span>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div
            style={{
              padding: "11px 14px",
              backgroundColor: "rgba(239, 68, 68, 0.12)",
              border: "1px solid #ef4444",
              borderRadius: "8px",
              color: "#fca5a5",
              fontSize: "13px",
              marginBottom: "18px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Auth Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {!isLogin && (
            <div>
              <label
                htmlFor="auth-username"
                style={{ display: "block", fontSize: "13px", color: "#9ca3af", marginBottom: "6px", fontWeight: 500 }}
              >
                Full Name / Username
              </label>
              <input
                id="auth-username"
                type="text"
                required={!isLogin}
                placeholder="e.g. Alex Rivera"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: "1px solid #374151",
                  backgroundColor: "#030712",
                  color: "#f9fafb",
                  fontSize: "14px",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>
          )}

          <div>
            <label
              htmlFor="auth-email"
              style={{ display: "block", fontSize: "13px", color: "#9ca3af", marginBottom: "6px", fontWeight: 500 }}
            >
              Email Address
            </label>
            <input
              id="auth-email"
              type="email"
              required
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: "8px",
                border: "1px solid #374151",
                backgroundColor: "#030712",
                color: "#f9fafb",
                fontSize: "14px",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div>
            <label
              htmlFor="auth-password"
              style={{ display: "block", fontSize: "13px", color: "#9ca3af", marginBottom: "6px", fontWeight: 500 }}
            >
              Password
            </label>
            <input
              id="auth-password"
              type="password"
              required
              placeholder={isLogin ? "Enter your password" : "At least 4 characters"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: "8px",
                border: "1px solid #374151",
                backgroundColor: "#030712",
                color: "#f9fafb",
                fontSize: "14px",
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: "8px",
              padding: "12px",
              borderRadius: "8px",
              border: "none",
              backgroundColor: loading ? "#1d4ed8" : "#2563eb",
              color: "#ffffff",
              fontSize: "14px",
              fontWeight: 600,
              cursor: loading ? "wait" : "pointer",
              transition: "background-color 0.15s ease",
              boxShadow: "0 4px 14px rgba(37, 99, 235, 0.4)",
            }}
          >
            {loading ? "Processing..." : isLogin ? "Sign In →" : "Create Account →"}
          </button>
        </form>

        {/* Feature Highlights Footer */}
        <div
          style={{
            marginTop: "24px",
            paddingTop: "18px",
            borderTop: "1px solid #1f2937",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "8px",
            fontSize: "11px",
            color: "#6b7280",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>⚡</span>
            <span>Real-Time AI Vision</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>👁️</span>
            <span>Morse Blink Decoder</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>🔒</span>
            <span>Secure JWT Sessions</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>💬</span>
            <span>Live Chat Rooms</span>
          </div>
        </div>
      </div>
    </div>
  );
};
