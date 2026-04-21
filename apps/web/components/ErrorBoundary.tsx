"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import { useTranslations } from "next-intl";

interface Props {
  children: ReactNode;
  /** Optional override for the i18n key used for the heading. */
  headingKey?: string;
}

interface State {
  error: Error | null;
}

/**
 * Client-side error boundary. Catches render/lifecycle errors in child
 * components and shows a localized fallback with a manual retry that
 * re-mounts the subtree. Does NOT catch errors in event handlers or
 * asynchronous code — those paths surface their own in-component alerts.
 */
class ErrorBoundaryInner extends Component<
  Props & { fallbackHeading: string; fallbackBody: string; retryLabel: string },
  State
> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (typeof console !== "undefined") {
      // eslint-disable-next-line no-console
      console.error("ErrorBoundary caught", error, info.componentStack);
    }
  }

  handleReset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        <div
          role="alert"
          className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200"
        >
          <p className="font-medium">{this.props.fallbackHeading}</p>
          <p className="mt-1 text-xs opacity-80">{this.props.fallbackBody}</p>
          <button
            type="button"
            onClick={this.handleReset}
            className="mt-2 rounded border border-red-300 px-3 py-1 text-xs hover:bg-red-100 focus-visible:outline-2 focus-visible:outline-red-600 dark:border-red-800 dark:hover:bg-red-900/40"
          >
            {this.props.retryLabel}
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

/** Convenience wrapper that pulls localized strings. */
export function ErrorBoundary({ children, headingKey }: Props) {
  const t = useTranslations();
  return (
    <ErrorBoundaryInner
      fallbackHeading={t(headingKey ?? "errors.sectionCrashTitle")}
      fallbackBody={t("errors.sectionCrashBody")}
      retryLabel={t("errors.retry")}
    >
      {children}
    </ErrorBoundaryInner>
  );
}
