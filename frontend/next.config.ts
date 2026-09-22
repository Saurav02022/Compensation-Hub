import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The repository maintains its own AGENTS.md and CLAUDE.md at the root.
  agentRules: false,
};

export default nextConfig;
