import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import Home from "../app/page";
import SignIn from "../app/sign-in/page";
import SignUp from "../app/sign-up/page";

describe("public marketing and account entry pages", () => {
  it("offers sign-in, sign-up, and real demo navigation", () => {
    const markup = renderToStaticMarkup(<Home />);

    expect(markup).toContain('href="/sign-in"');
    expect(markup).toContain('href="/sign-up"');
    expect(markup).toContain('href="/demo"');
    expect(markup).toContain("Try demo account");
    expect(markup).toContain("Connected");
    expect(markup).toContain("CockroachDB Cloud");
    expect(markup).toContain("No diagnosis or treatment advice");
    expect(markup).not.toMatch(/synthetic/i);
  });

  it("keeps local account entry honest and routes into synthetic demo mode", () => {
    const signIn = renderToStaticMarkup(<SignIn />);
    const signUp = renderToStaticMarkup(<SignUp />);

    for (const markup of [signIn, signUp]) {
      expect(markup).toContain('href="/demo"');
      expect(markup).toContain("Amazon Cognito");
      expect(markup).toContain("does not create real user accounts");
      expect(markup).not.toMatch(/synthetic/i);
    }
  });
});
