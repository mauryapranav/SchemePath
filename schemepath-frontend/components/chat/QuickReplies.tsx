import React, { useState } from "react";

interface Props {
  options: string[];
  onSelect: (option: string) => void;
}

export default function QuickReplies({ options, onSelect }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  const handleSelect = (option: string) => {
    setSelected(option);
    onSelect(option);
  };

  if (!options || options.length === 0 || selected) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-2 animate-message-in">
      {options.map((option, idx) => (
        <button
          key={idx}
          onClick={() => handleSelect(option)}
          className="quick-reply-pill"
        >
          {option}
        </button>
      ))}
    </div>
  );
}
