import fs from "fs";
import path from "path";

export function loadApiContract() {
  const contractPath = path.resolve(process.cwd(), "../../shared/api-contract.json");
  if (!fs.existsSync(contractPath)) {
    throw new Error(`Shared api-contract.json not found at: ${contractPath}`);
  }

  return JSON.parse(fs.readFileSync(contractPath, "utf-8"));
}
