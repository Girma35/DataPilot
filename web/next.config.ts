import path from "path";
import fs from "fs";
import { config as loadEnv } from "dotenv";
import type { NextConfig } from "next";

// Next only loads .env* from web/; repo keeps Auth0 vars in ../.env
const repoEnvPath = path.resolve(process.cwd(), "..", ".env");
if (fs.existsSync(repoEnvPath)) {
  loadEnv({ path: repoEnvPath, quiet: true });
}

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
