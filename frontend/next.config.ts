import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The repository maintains its own AGENTS.md and CLAUDE.md at the root.
  agentRules: false,
  // Produces a self-contained server for the container image.
  output: "standalone",
};

export default nextConfig;
