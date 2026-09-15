import { describe, it, expect, vi, afterEach } from "vitest";
import { isSpeechRecognitionSupported, isSpeechSynthesisSupported, startListening, speak } from "./voice";

describe("isSpeechRecognitionSupported", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns false when neither constructor exists", () => {
    expect(isSpeechRecognitionSupported()).toBe(false);
  });

  it("returns true when webkitSpeechRecognition exists", () => {
    vi.stubGlobal("webkitSpeechRecognition", class {});
    expect(isSpeechRecognitionSupported()).toBe(true);
  });
});

describe("startListening", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("calls onError immediately when unsupported", () => {
    const onResult = vi.fn();
    const onError = vi.fn();
    startListening(onResult, onError);
    expect(onError).toHaveBeenCalledOnce();
    expect(onResult).not.toHaveBeenCalled();
  });

  it("calls onResult with the transcript when recognition succeeds", () => {
    let capturedInstance: { onresult: ((e: unknown) => void) | null; start: () => void } | undefined;
    class FakeRecognition {
      lang = "";
      interimResults = false;
      maxAlternatives = 1;
      onresult: ((e: unknown) => void) | null = null;
      onerror: (() => void) | null = null;
      onend: (() => void) | null = null;
      start() {
        capturedInstance = this;
      }
      stop() {}
    }
    vi.stubGlobal("webkitSpeechRecognition", FakeRecognition);

    const onResult = vi.fn();
    startListening(onResult, vi.fn());
    capturedInstance?.onresult?.({ results: { 0: { 0: { transcript: "is it safe" } } } });

    expect(onResult).toHaveBeenCalledWith("is it safe");
  });
});

describe("speak", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("does nothing when speechSynthesis is unsupported", () => {
    expect(() => speak("hello")).not.toThrow();
  });

  it("cancels any current utterance and speaks the new one", () => {
    const cancel = vi.fn();
    const speakFn = vi.fn();
    vi.stubGlobal("speechSynthesis", { cancel, speak: speakFn });
    vi.stubGlobal(
      "SpeechSynthesisUtterance",
      class {
        constructor(public text: string) {}
      }
    );

    speak("the answer");

    expect(cancel).toHaveBeenCalledOnce();
    expect(speakFn).toHaveBeenCalledOnce();
  });
});
