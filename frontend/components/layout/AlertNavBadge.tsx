"use client";

import { useEffect, useState } from "react";
import { getAlertSession } from "@/lib/alertSessionClient";
import { getDemoAlertSessionId } from "@/lib/demoAlertSession";

export function AlertNavBadge() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      const sid = getDemoAlertSessionId();
      getAlertSession(sid)
        .then((s) => {
          if (!cancelled) setCount(s.unread_count);
        })
        .catch(() => {
          if (!cancelled) setCount(0);
        });
    };
    load();
    const t = window.setInterval(load, 8000);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, []);

  if (count <= 0) return null;
  return (
    <span className="ml-1 inline-flex min-w-[1.1rem] items-center justify-center rounded-full bg-amber-600 px-1 text-[10px] font-bold text-zinc-950">
      {count > 9 ? "9+" : count}
    </span>
  );
}
