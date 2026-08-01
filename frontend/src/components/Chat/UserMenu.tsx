import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lock, LogOut, Settings, User } from "lucide-react";

import { useAuth } from "../../context/AuthContext";

function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function onPointerDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (!user) return null;

  // Optional chaining on [0]: firstName is NOT NULL in the schema, but an
  // empty string satisfies that and would throw on index access.
  const initial = (user.firstName?.[0] ?? "?").toUpperCase();

  async function handleLogout() {
    setOpen(false);
    await logout();
    navigate("/login", { replace: true });
  }

  const items = [
	{ label: "Profile", icon: User, onClick: () => navigate("/profile") },
	{ label: "Settings", icon: Settings, onClick: () => navigate("/settings") },
	{ label: "Privacy", icon: Lock, onClick: () => navigate("/privacy") },
  ];

  return (
    <div className="relative" ref={ref}>
		<button
			type="button"
			onClick={() => setOpen((v) => !v)}
			aria-expanded={open}
			aria-haspopup="menu"
			className="
				flex items-center gap-3 rounded-full
				py-1 pl-4 pr-1
				transition-colors hover:bg-neutral-800
				hover:cursor-pointer
			"
    >
        <span className="text-m text-neutral-300 ">
          	Hi, {user.firstName}
        </span>

        <span
			className="
				flex h-9 w-9 shrink-0 items-center justify-center
				rounded-full bg-red-500 text-sm font-semibold text-white
			"
        >
          {initial}
        </span>
      </button>

      {open && (
        <div
			role="menu"
			className="
				absolute right-0 z-50 mt-2 w-56
				overflow-hidden rounded-xl
				border border-neutral-800 bg-neutral-900
				shadow-xl shadow-black/40
			"
        >

          <div className="border-b border-neutral-800 px-4 py-3">
            <p className="truncate text-sm text-neutral-100">
              	{user.firstName} {user.lastName}
            </p>
            <p className="truncate text-xs text-neutral-500">{user.email}</p>
          </div>

          <div className="py-1">
            {items.map(({ label, icon: Icon, onClick }) => (
              <button
					key={label}
					role="menuitem"
					type="button"
					onClick={() => {
						setOpen(false);
						onClick();
					}}
					className="
						flex w-full items-center gap-3 px-4 py-2.5
						text-left text-sm text-neutral-300
						transition-colors hover:bg-neutral-800 hover:text-neutral-100
						hover:cursor-pointer
					"
              >
                <Icon size={16} />
                {label}
              </button>
            ))}
          </div>

          <div className="border-t border-neutral-800 py-1">
            <button
				role="menuitem"
				type="button"
				onClick={handleLogout}
				className="
					flex w-full items-center gap-3 px-4 py-2.5
					text-left text-sm text-red-400
					transition-colors hover:bg-red-500/10
					hover:cursor-pointer
				"
            >
              <LogOut size={16} />
              Log out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default UserMenu;