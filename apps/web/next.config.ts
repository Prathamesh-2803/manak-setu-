import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Silence the "multiple lockfiles / workspace root" dev-overlay warning
  // caused by a stray package-lock.json in the user's home directory.
  outputFileTracingRoot: path.join(__dirname),
};
export default nextConfig;
