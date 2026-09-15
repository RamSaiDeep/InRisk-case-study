import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, POLICY, api } from "./api";
import type { LocationResponse, PriceResponse } from "./types";
import { Footer, Header } from "./components/Shell";
import { Hero, HowItWorks } from "./components/Hero";
import { Policy } from "./components/Policy";

// One input, one output. A visitor gives a pincode; everything else - the
// rooftop, the tariff, the bands, the loadings - is the submitted contract,
// held fixed, so the only thing that varies on screen is the location.

export type Status =
  | { name: "idle" }
  | { name: "working"; step: 0 | 1 | 2; progress: number; message: string }
  | { name: "error"; message: string; retryable: boolean }
  | { name: "ready"; location: LocationResponse; result: PriceResponse };

function describe(error: unknown, pincode: string): string {
  if (!(error instanceof ApiError)) return "Something went wrong. Please try again.";
  switch (error.kind) {
    case "pincode_not_found":
      return `Pincode ${pincode} isn't in the India Post boundary set. Check the six digits.`;
    case "upstream_error":
      return "A data provider didn't answer. Please try again in a moment.";
    case "job_not_found":
      return "The server restarted while the data was downloading. Please try again.";
    default:
      return error.message;
  }
}

/** Locate, fetch, price - each step starts when the one before it lands. */
function usePolicy(pincode: string | null): Status {
  const located = useQuery({
    queryKey: ["location", pincode],
    queryFn: () => api.resolveLocation(pincode!),
    enabled: Boolean(pincode),
  });
  const data = useQuery({
    queryKey: ["data", pincode],
    queryFn: () => api.requestData(pincode!, POLICY.startYear, POLICY.endYear),
    enabled: located.isSuccess,
  });
  const jobId = data.data?.status === "fetching" ? data.data.job_id : null;
  const job = useQuery({
    queryKey: ["job", pincode, jobId],
    queryFn: () => api.jobStatus(jobId!),
    enabled: Boolean(jobId),
    // The pull takes a minute; a visitor who switches tabs meanwhile should
    // come back to a priced policy, not a stalled bar.
    refetchIntervalInBackground: true,
    refetchInterval: (query) =>
      query.state.data?.status === "done" || query.state.data?.status === "error" ? false : 1000,
  });
  const fetched = data.data?.status === "ready" || job.data?.status === "done";
  const priced = useQuery({
    queryKey: ["price", pincode],
    queryFn: ({ signal }) =>
      api.price(pincode!, POLICY.startYear, POLICY.endYear, POLICY.inputs, signal),
    enabled: fetched,
  });

  if (!pincode) return { name: "idle" };
  const failure = located.error ?? data.error ?? job.error ?? priced.error;
  if (failure)
    return {
      name: "error",
      message: describe(failure, pincode),
      retryable: !(failure instanceof ApiError && failure.kind === "pincode_not_found"),
    };
  if (job.data?.status === "error")
    return {
      name: "error",
      message: job.data.error ?? "The irradiance download failed.",
      retryable: true,
    };
  if (located.data && priced.data)
    return { name: "ready", location: located.data, result: priced.data };
  if (!located.data)
    return { name: "working", step: 0, progress: 0, message: `Locating pincode ${pincode}` };
  if (!fetched)
    return {
      name: "working",
      step: 1,
      progress: job.data?.progress ?? 0,
      message: job.data?.message ?? "Requesting twenty years of daily irradiance",
    };
  return { name: "working", step: 2, progress: 1, message: "Pricing the policy" };
}

function pincodeFromUrl(): string | null {
  const value = new URLSearchParams(window.location.search).get("pincode");
  return value && /^\d{6}$/.test(value) ? value : null;
}

export function App() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState(() => pincodeFromUrl() ?? "");
  const [active, setActive] = useState<string | null>(pincodeFromUrl);
  const status = usePolicy(active);

  const submit = (pincode: string) => {
    setDraft(pincode);
    if (pincode === active) {
      if (status.name === "error")
        queryClient.resetQueries({ predicate: (query) => query.queryKey[1] === pincode });
      return;
    }
    setActive(pincode);
    // A shareable address: the link opens straight onto this pincode's policy.
    window.history.replaceState(null, "", `?pincode=${pincode}`);
  };

  // Bring the policy into view once, when it first arrives for a pincode.
  const results = useRef<HTMLDivElement>(null);
  const shown = useRef<string | null>(null);
  useEffect(() => {
    if (status.name !== "ready" || shown.current === active) return;
    shown.current = active;
    results.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [status.name, active]);

  return (
    <div className="page">
      <Header />
      <main className="container">
        <Hero
          draft={draft}
          onDraft={setDraft}
          onSubmit={submit}
          status={status}
          active={active}
        />
        <div ref={results} className="results-anchor">
          {status.name === "ready" && (
            <Policy location={status.location} result={status.result} />
          )}
        </div>
        <HowItWorks />
      </main>
      <Footer />
    </div>
  );
}
