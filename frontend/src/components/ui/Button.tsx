"use client";

import clsx from "clsx";

export default function Button({
  children,
  className,
  onClick,
  disabled,
  variant = "primary",
}: {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "ghost";
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "rounded-lg px-4 py-2 text-sm font-medium transition focus:outline-none",
        disabled && "opacity-60 cursor-not-allowed",
        variant === "primary" && "bg-violet-600 hover:bg-violet-500 text-white",
        variant === "secondary" &&
          "bg-white/10 hover:bg-white/20 text-white border border-white/10",
        variant === "ghost" &&
          "text-gray-300 hover:text-white hover:bg-white/5",
        className
      )}
    >
      {children}
    </button>
  );
}
