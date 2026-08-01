// Atomic/NavButton.tsx
type Props = {
  name: string;
  onClick?: () => void;
};

function NavButton({ name, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="
        relative inline-flex flex-col items-center
        text-gray-700 hover:text-black
        transition-colors
        cursor-pointer
      "
    >
      {/* visible label */}
      <span className="font-normal hover:font-bold peer">
        {name}
      </span>

      {/* invisible bold twin — locks the width */}
      <span
        aria-hidden
        className="
          font-bold
          h-0 overflow-hidden
          select-none pointer-events-none
        "
      >
        {name}
      </span>
    </button>
  );
}

export default NavButton;