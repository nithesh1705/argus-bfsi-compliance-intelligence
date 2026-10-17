import { useEffect } from "react";
import { useLocation } from "react-router-dom";

interface RouteTitle {
  pattern: RegExp;
  title: string;
}

const ROUTE_TITLES: RouteTitle[] = [
  { pattern: /^\/login/, title: "ARGUS | Login" },
  { pattern: /^\/ai-investigation/, title: "ARGUS | AI-Investigation" },
  { pattern: /^\/calls/, title: "ARGUS | Calls" },
  { pattern: /^\/cases/, title: "ARGUS | Cases" },
  { pattern: /^\/rm-analytics/, title: "ARGUS | RM Analytics" },
  { pattern: /^\/regulations/, title: "ARGUS | Regulations" },
  { pattern: /^\/observability/, title: "ARGUS | Observability" },
  { pattern: /^\/settings/, title: "ARGUS | Settings" },
  { pattern: /^\/admin\/manage/, title: "ARGUS | Master Data CRUD" },
  { pattern: /^\/$/, title: "ARGUS | Dashboard" },
];

export function usePageTitle(): void {
  const location = useLocation();

  useEffect(() => {
    const matched = ROUTE_TITLES.find(({ pattern }) => pattern.test(location.pathname));
    document.title = matched ? matched.title : "ARGUS | Dashboard";
  }, [location.pathname]);
}
