import React from "react";

interface StatusBadgeProps {
  label: string;
  status: "active" | "inactive" | "warning";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ label, status }) => {
  const colors = {
    active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    inactive: "bg-rose-500/20 text-rose-400 border-rose-500/30",
    warning: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  };

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "4px 10px",
        borderRadius: "9999px",
        fontSize: "12px",
        fontWeight: 600,
        border: "1px solid",
      }}
      className={colors[status]}
    >
      <span
        style={{
          width: "8px",
          height: "8px",
          borderRadius: "50%",
          marginRight: "6px",
          backgroundColor: status === "active" ? "#10b981" : status === "warning" ? "#f59e0b" : "#ef4444",
        }}
      />
      {label}
    </span>
  );
};
