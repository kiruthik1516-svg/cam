"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { apiUrl } from "@/lib/api/config";
import { ShieldCheck, User, Lock, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const formData = new URLSearchParams();
      formData.append("username", username.trim());
      formData.append("password", password);

      const res = await fetch(apiUrl("/api/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        credentials: "include",
        body: formData.toString(),
      });

      if (!res.ok) {
        let msg = "Invalid credentials";
        try {
          const errData = await res.json();
          if (errData.detail) msg = errData.detail;
        } catch {
          // fallback
        }
        throw new Error(msg);
      }

      const data = await res.json();
      // Store token, username, and role in localStorage for RBAC session
      localStorage.setItem("sentinel_token", data.access_token);
      localStorage.setItem("sentinel_username", data.username || username.trim());
      localStorage.setItem("sentinel_role", data.role || "admin");
      if (data.user_id) {
        localStorage.setItem("sentinel_user_id", data.user_id);
      }
      
      // Redirect to dashboard
      router.push("/");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unknown authentication error occurred.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-black/95 p-4">
      <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:32px_32px]" />
      
      <Card className="z-10 w-full max-w-md border-border/50 bg-background/60 shadow-2xl backdrop-blur-xl">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-3">
            <div className="rounded-full bg-primary/10 p-3 ring-1 ring-primary/30">
              <ShieldCheck className="h-7 w-7 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">SENTINEL</CardTitle>
          <CardDescription className="text-xs text-muted-foreground">
            Facial Recognition & Surveillance Operations Console
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleLogin}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-xs font-semibold flex items-center gap-1.5">
                <User className="h-3.5 w-3.5 text-muted-foreground" /> Username / Operator ID
              </Label>
              <Input
                id="username"
                type="text"
                placeholder="admin"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
                className="bg-black/40 font-mono text-sm"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-xs font-semibold flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5 text-muted-foreground" /> Access Secret
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="bg-black/40 text-sm"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-2.5 text-xs font-medium text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="rounded-lg border border-border/40 bg-muted/20 p-2.5 text-[11px] text-muted-foreground">
              <span className="font-semibold text-foreground">Role Permissions:</span>
              <ul className="mt-1 list-disc pl-4 space-y-0.5 font-mono text-[10px]">
                <li><span className="text-primary font-semibold">admin:</span> Full system management, user accounts & edge keys</li>
                <li><span className="text-info font-semibold">operator:</span> Vector enrollment, camera thresholds & alert handling</li>
                <li><span className="text-emerald-400 font-semibold">viewer:</span> Read-only monitoring & event observation</li>
              </ul>
            </div>
          </CardContent>
          <CardFooter>
            <Button 
              className="w-full font-semibold shadow-md" 
              type="submit" 
              disabled={loading}
            >
              {loading ? "Authenticating..." : "Establish Connection"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
