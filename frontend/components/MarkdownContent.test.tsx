import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MarkdownContent, parseInlineMarkdown } from "./MarkdownContent";

describe("MarkdownContent", () => {
  it("renders headers and bold text correctly", () => {
    const markdown = "### Safe Shipping Route\n- Wave height: **1.8 m**\n- Wind speed: **22.0 km/h**";
    const html = renderToStaticMarkup(<MarkdownContent content={markdown} />);

    expect(html).toContain("<h3");
    expect(html).toContain("Safe Shipping Route");
    expect(html).toContain("<ul");
    expect(html).toContain("<li");
    expect(html).toContain("<strong");
    expect(html).toContain("1.8 m");
  });

  it("renders headings at various levels", () => {
    const markdown = "# Title\n## Subtitle\n### Section\n#### Notice";
    const html = renderToStaticMarkup(<MarkdownContent content={markdown} />);

    expect(html).toContain("<h1");
    expect(html).toContain("Title");
    expect(html).toContain("<h2");
    expect(html).toContain("Subtitle");
    expect(html).toContain("<h3");
    expect(html).toContain("Section");
    expect(html).toContain("<h4");
    expect(html).toContain("Notice");
  });

  it("handles inline code and links", () => {
    const markdown = "Check `INCOIS` data at [portal](https://incois.gov.in).";
    const html = renderToStaticMarkup(<MarkdownContent content={markdown} />);

    expect(html).toContain("<code");
    expect(html).toContain("INCOIS");
    expect(html).toContain("<a");
    expect(html).toContain('href="https://incois.gov.in"');
    expect(html).toContain("portal");
  });
});
