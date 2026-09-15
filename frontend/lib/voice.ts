// Browser-based voice input/output (Web Speech API) -- not real SMS/IVR/
// telephony, which isn't free at any real scale. This only works while a
// browser tab with mic access is open; no backend involvement.
//
// Uses globalThis rather than window: window === globalThis in a real
// browser, and this project's test environment has no window at all
// (no jsdom), so globalThis is what's actually testable without adding one.

interface MinimalSpeechRecognition {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: { results: { [i: number]: { [j: number]: { transcript: string } } } }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

interface MinimalSpeechSynthesis {
  cancel(): void;
  speak(utterance: unknown): void;
}

function getGlobal(): Record<string, unknown> {
  return globalThis as unknown as Record<string, unknown>;
}

function getSpeechRecognitionCtor(): (new () => MinimalSpeechRecognition) | undefined {
  const g = getGlobal();
  return (g.SpeechRecognition ?? g.webkitSpeechRecognition) as
    | (new () => MinimalSpeechRecognition)
    | undefined;
}

export function isSpeechRecognitionSupported(): boolean {
  return Boolean(getSpeechRecognitionCtor());
}

export function isSpeechSynthesisSupported(): boolean {
  return Boolean(getGlobal().speechSynthesis);
}

/**
 * Starts listening for a single utterance. Calls onResult with the
 * transcribed text once recognition ends, or onError if the browser
 * doesn't support it / recognition fails. Returns a stop function.
 */
export function startListening(onResult: (text: string) => void, onError: () => void): () => void {
  const SpeechRecognitionCtor = getSpeechRecognitionCtor();
  if (!SpeechRecognitionCtor) {
    onError();
    return () => {};
  }

  const recognition = new SpeechRecognitionCtor();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onresult = (event) => {
    const transcript = event.results[0]?.[0]?.transcript;
    if (transcript) onResult(transcript);
  };
  recognition.onerror = onError;
  recognition.start();
  return () => recognition.stop();
}

export function speak(text: string): void {
  const synthesis = getGlobal().speechSynthesis as MinimalSpeechSynthesis | undefined;
  const UtteranceCtor = getGlobal().SpeechSynthesisUtterance as (new (text: string) => unknown) | undefined;
  if (!synthesis || !UtteranceCtor) return;
  synthesis.cancel();
  synthesis.speak(new UtteranceCtor(text));
}
