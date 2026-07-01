import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const stylesheet = readFileSync(resolve(__dirname, "../styles/app.css"), "utf8");

function ruleBody(selector: string) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = stylesheet.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`));
  return match?.[1] ?? "";
}

describe("chat layout styles", () => {
  it("keeps the transcript as the only flexible chat workspace row", () => {
    expect(ruleBody(".chat-workspace")).toContain(
      "grid-template-rows: minmax(0, 1fr) auto auto;"
    );
  });
});
