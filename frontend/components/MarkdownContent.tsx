// frontend/components/MarkdownContent.tsx
"use client";

import React from "react";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

/**
 * Parses inline markdown: **bold**, *italic*, `code`, [text](url).
 */
export function parseInlineMarkdown(text: string): React.ReactNode[] {
  if (!text) return [];

  // Match inline tokens: code, bold, italic, link
  const tokenRegex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, idx) => {
    if (!part) return null;

    // Inline code: `code`
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 font-mono text-[11px] text-slate-800"
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold: **text**
    if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
      return (
        <strong key={idx} className="font-semibold text-slate-950">
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Italic: *text*
    if (part.startsWith("*") && part.endsWith("*") && part.length >= 2) {
      return (
        <em key={idx} className="italic text-slate-800">
          {part.slice(1, -1)}
        </em>
      );
    }

    // Link: [text](url)
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return (
        <a
          key={idx}
          href={linkMatch[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sky-600 hover:text-sky-800 underline underline-offset-2 font-medium"
        >
          {linkMatch[1]}
        </a>
      );
    }

    return <React.Fragment key={idx}>{part}</React.Fragment>;
  });
}

type Block =
  | { type: "h1" | "h2" | "h3" | "h4"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "blockquote"; text: string }
  | { type: "hr" }
  | { type: "p"; text: string };

/**
 * Tokenizes markdown text into structured blocks (README preview style).
 */
function parseBlocks(content: string): Block[] {
  const lines = content.split(/\r?\n/);
  const blocks: Block[] = [];
  let currentList: string[] | null = null;
  let currentParagraph: string[] = [];

  function flushParagraph() {
    if (currentParagraph.length > 0) {
      blocks.push({ type: "p", text: currentParagraph.join(" ") });
      currentParagraph = [];
    }
  }

  function flushList() {
    if (currentList && currentList.length > 0) {
      blocks.push({ type: "ul", items: currentList });
      currentList = null;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    // Horizontal rule
    if (line === "---" || line === "***" || line === "___") {
      flushParagraph();
      flushList();
      blocks.push({ type: "hr" });
      continue;
    }

    // Headings
    if (line.startsWith("#### ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "h4", text: line.slice(5) });
      continue;
    }
    if (line.startsWith("### ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "h3", text: line.slice(4) });
      continue;
    }
    if (line.startsWith("## ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "h2", text: line.slice(3) });
      continue;
    }
    if (line.startsWith("# ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "h1", text: line.slice(2) });
      continue;
    }

    // Blockquote
    if (line.startsWith("> ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "blockquote", text: line.slice(2) });
      continue;
    }

    // Unordered list item (- or *)
    const listMatch = line.match(/^[-*]\s+(.*)$/);
    if (listMatch) {
      flushParagraph();
      if (!currentList) currentList = [];
      currentList.push(listMatch[1]);
      continue;
    }

    // Regular line inside a paragraph
    flushList();
    currentParagraph.push(line);
  }

  flushParagraph();
  flushList();

  return blocks;
}

export function MarkdownContent({ content, className = "" }: MarkdownContentProps) {
  if (!content) return null;

  const blocks = parseBlocks(content);

  return (
    <div className={`readme-preview text-slate-800 space-y-2.5 ${className}`}>
      {blocks.map((block, i) => {
        switch (block.type) {
          case "h1":
            return (
              <h1
                key={i}
                className="text-lg sm:text-xl font-extrabold text-slate-900 mt-3.5 mb-1.5 pb-1 border-b border-slate-200 tracking-tight"
              >
                {parseInlineMarkdown(block.text)}
              </h1>
            );
          case "h2":
            return (
              <h2
                key={i}
                className="text-base sm:text-lg font-bold text-slate-900 mt-3 mb-1.5 pb-0.5 border-b border-slate-100 tracking-tight"
              >
                {parseInlineMarkdown(block.text)}
              </h2>
            );
          case "h3":
            return (
              <h3
                key={i}
                className="text-sm sm:text-base font-bold text-slate-900 mt-2.5 mb-1 flex items-center gap-1.5 tracking-tight"
              >
                {parseInlineMarkdown(block.text)}
              </h3>
            );
          case "h4":
            return (
              <h4
                key={i}
                className="text-xs sm:text-sm font-bold text-slate-800 mt-2 mb-0.5 flex items-center gap-1.5 text-sky-950 uppercase tracking-wide"
              >
                {parseInlineMarkdown(block.text)}
              </h4>
            );
          case "ul":
            return (
              <ul
                key={i}
                className="my-1.5 space-y-1 pl-4 list-disc marker:text-slate-400 text-xs sm:text-sm leading-relaxed"
              >
                {block.items.map((item, itemIdx) => (
                  <li key={itemIdx} className="text-slate-700">
                    {parseInlineMarkdown(item)}
                  </li>
                ))}
              </ul>
            );
          case "blockquote":
            return (
              <blockquote
                key={i}
                className="pl-3 border-l-2 border-sky-400 bg-sky-50/50 py-1 px-2 rounded-r-lg text-xs sm:text-sm text-slate-700 italic my-2"
              >
                {parseInlineMarkdown(block.text)}
              </blockquote>
            );
          case "hr":
            return <hr key={i} className="my-3 border-slate-200" />;
          case "p":
            return (
              <p
                key={i}
                className="text-xs sm:text-sm text-slate-700 leading-relaxed font-normal"
              >
                {parseInlineMarkdown(block.text)}
              </p>
            );
          default:
            return null;
        }
      })}
    </div>
  );
}
