"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

/**
 * Navigation link that reads the current pathname client-side and sets
 * ``aria-current="page"`` when matched. Works with static export — the
 * server renders the link without the attribute and the client hydrates
 * the correct state. No layout shift because the class is purely visual.
 */
export function NavLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const active =
    pathname === href ||
    pathname === `${href}/` ||
    (href !== "/" && pathname?.startsWith(`${href}/`));
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={
        active
          ? "font-medium underline underline-offset-4 decoration-2"
          : "hover:underline focus-visible:underline focus-visible:outline-2 focus-visible:outline-blue-500 focus-visible:outline-offset-2"
      }
    >
      {children}
    </Link>
  );
}
