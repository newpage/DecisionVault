"use client";

import {useState} from "react";
import BrandFooter from "@/components/BrandFooter";
import DiscoverABrand from "@/components/DiscoverABrand";
import ProductBrand from "@/components/ProductBrand";
import {API} from "@/lib/api";

export default function Login() {
  const [tenant, setTenant] = useState(
    process.env.NEXT_PUBLIC_DEMO_TENANT || "acme"
  );
  const [email, setEmail] = useState(
    process.env.NEXT_PUBLIC_DEMO_EMAIL || "demo@decisionvault.ai"
  );
  const [password, setPassword] = useState("DecisionVault!");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");

    const response = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({tenant, email, password}),
    });

    if (!response.ok) {
      setError("Unable to sign in");
      return;
    }

    const data = await response.json();
    localStorage.setItem("dv_token", data.access_token);
    location.href = "/dashboard";
  }

  return (
    <div className="dv-login-page">
      <section className="dv-login-story">
        <DiscoverABrand />
        <div className="dv-login-message">
          <ProductBrand
            large
            trademark
            tagline="A DiscoverA.ai Technology"
          />
          <h1>Govern knowledge. Build trust. Make better decisions.</h1>
          <p>
            Turn enterprise evidence into transparent, accountable, and
            defensible decisions.
          </p>
        </div>
        <span className="dv-login-ownership">
          Technology developed and owned by DiscoverA.ai.
        </span>
      </section>

      <section className="dv-login-form-panel">
        <form className="card dv-login-card" onSubmit={submit}>
          <div>
            <div className="eyebrow">Secure access</div>
            <h2>Welcome back</h2>
            <p className="muted">
              Sign in to DecisionVault.
            </p>
          </div>

          <div className="list">
            <label className="dv-field">
              <span>Tenant</span>
              <input
                className="input"
                value={tenant}
                onChange={(event) => setTenant(event.target.value)}
                autoComplete="organization"
              />
            </label>

            <label className="dv-field">
              <span>Email</span>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
              />
            </label>

            <label className="dv-field">
              <span>Password</span>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
              />
            </label>

            {error ? <div className="danger">{error}</div> : null}

            <button className="btn primary dv-login-button">
              Sign in
            </button>
          </div>
        </form>
      </section>

      <BrandFooter />
    </div>
  );
}
