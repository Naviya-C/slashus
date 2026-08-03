interface NavProp {
  name: string;
  onClick?: () => void;
};

const NavButton = (prop: NavProp) => {
  return (
    <button
      onClick={prop.onClick}
      className="
        relative inline-flex flex-col items-center
        text-gray-700 hover:text-black
        transition-colors
        cursor-pointer
      "
    >
      {/* visible label */}
      <span className="font-normal hover:font-bold peer">
        {prop.name}
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
        {prop.name}
      </span>
    </button>
  );
}



export default NavButton;