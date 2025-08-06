import React from "react";

type TooltipButtonProps = {
  label: string;
  onClick?: () => void;
  isAdmin: boolean;
  adminOnlyMessage?: string;
  className?: string;
  type?: "button" | "submit" | "reset";
};

const TooltipButton: React.FC<TooltipButtonProps> = ({
  label,
  onClick,
  isAdmin,
  adminOnlyMessage = "Only admins can perform this action",
  className = "",
  type = "button",
}) => {
  return (
    <div className="relative group inline-block">
      <button
        type={type}
        disabled={!isAdmin}
        onClick={isAdmin ? onClick : undefined}
        className={`px-4 py-2 rounded-md text-white transition-colors duration-200 ${
          isAdmin ? "bg-blue-600 hover:bg-blue-700" : "bg-gray-400 cursor-not-allowed"
        } ${className}`}
      >
        {label}
      </button>

      {!isAdmin && (
        <div className="absolute left-1/2 -translate-x-1/2 top-full mt-2 hidden group-hover:block z-10 bg-black text-white text-xs rounded px-2 py-1 whitespace-nowrap shadow-md">
          {adminOnlyMessage}
        </div>
      )}
    </div>
  );
};

export default TooltipButton;
