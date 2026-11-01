import { describe, it, expect } from "vitest";
import { getSafeRedirectTarget } from "../../utils/authRedirect";

describe("getSafeRedirectTarget", () => {
  it("returns pathname with search and hash", () => {
    expect(
      getSafeRedirectTarget({
        pathname: "/sign/abc123",
        search: "?foo=1",
        hash: "#section",
      })
    ).toBe("/sign/abc123?foo=1#section");
  });

  it("rejects protocol-relative paths", () => {
    expect(getSafeRedirectTarget({ pathname: "//evil.com" })).toBe("/");
  });

  it("falls back to home when from is missing", () => {
    expect(getSafeRedirectTarget(null)).toBe("/");
  });
});
