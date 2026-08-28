import { useEffect, useMemo, useState } from "react";
import {
    ArrowLeft,
    AtSign,
    ChevronRight,
    Shield,
    SlidersHorizontal,
    Sparkles,
    User as UserIcon,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import questionImage from "../../assets/qGen.png";
import Logo from "../../components/Atomic/Logo";
import ThemeToggle from "../../components/Atomic/ThemeToggle";
import { useAuth } from "../../context/AuthContext";
import * as userApi from "./api";
import ProfileBanner from "./components/ProfileBanner";
import ProfileToast from "./components/ProfileToast";
import { ghostButtonClass } from "./styles";
import AccountTab from "./tabs/AccountTab";
import PreferencesTab from "./tabs/PreferencesTab";
import ProfileTab from "./tabs/ProfileTab";
import SecurityTab from "./tabs/SecurityTab";
import type { UserProfile } from "./types";
import { createProfile, getInitials, getProfileCompletion } from "./utils";

const TABS = [
    { id: "profile", label: "Profile", icon: UserIcon },
    { id: "account", label: "Account", icon: AtSign },
    { id: "security", label: "Security", icon: Shield },
    { id: "preferences", label: "Preferences", icon: SlidersHorizontal },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function ProfilePage() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [tab, setTab] = useState<TabId>("profile");
    const [profile, setProfile] = useState<UserProfile>(() =>
        createProfile(user),
    );
    const [toast, setToast] = useState("");

    useEffect(() => {
        let active = true;
        void userApi
            .fetchProfile()
            .then((loaded) => {
                if (active && loaded) setProfile(loaded);
            })
            .catch(() => undefined);
        return () => {
            active = false;
        };
    }, []);

    useEffect(() => {
        if (!toast) return;
        const timer = window.setTimeout(() => setToast(""), 2_600);
        return () => window.clearTimeout(timer);
    }, [toast]);

    const completion = useMemo(
        () => getProfileCompletion(profile),
        [profile],
    );

    function goBack() {
        if (window.history.length > 1) navigate(-1);
        else navigate("/chat");
    }

    return (
        <div className="min-h-dvh w-full overflow-x-hidden bg-[var(--bg)] text-[var(--tx)]">
            <ProfileAnimations />
            <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-[var(--bd)] bg-[color:var(--bg)]/90 px-3 backdrop-blur-xl sm:px-5">
                <div className="flex min-w-0 items-center gap-2 sm:gap-4">
                    <button
                        type="button"
                        onClick={goBack}
                        aria-label="Go back"
                        className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-[var(--bd)] text-[var(--tx2)] transition hover:-translate-x-0.5 hover:bg-[var(--sf2)] hover:text-[var(--tx)]"
                    >
                        <ArrowLeft size={19} />
                    </button>
                    <Logo size={34} />
                    <span className="hidden h-5 w-px bg-[var(--bd)] sm:block" />
                    <span className="hidden text-sm font-medium text-[var(--tx2)] sm:block">
                        Profile workspace
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <ThemeToggle />
                    <button
                        type="button"
                        onClick={() => navigate("/chat")}
                        className={ghostButtonClass}
                    >
                        <span className="hidden sm:inline">Open chat</span>
                        <ChevronRight size={16} />
                    </button>
                </div>
            </header>

            <div className="grid min-h-[calc(100dvh-4rem)] w-full lg:grid-cols-[17rem_minmax(0,1fr)]">
                <ProfileSidebar
                    profile={profile}
                    tab={tab}
                    completion={completion}
                    onTabChange={setTab}
                />
                <main className="min-w-0 w-full">
                    <ProfileBanner
                        profile={profile}
                        onChange={setProfile}
                        notify={setToast}
                    />
                    <MobileTabs tab={tab} onChange={setTab} />
                    <div
                        key={tab}
                        className="profile-enter w-full p-4 sm:p-6 lg:p-8 xl:p-10"
                    >
                        {tab === "profile" && (
                            <ProfileTab
                                profile={profile}
                                onSaved={setProfile}
                                notify={setToast}
                            />
                        )}
                        {tab === "account" && (
                            <AccountTab
                                profile={profile}
                                onSaved={setProfile}
                                notify={setToast}
                            />
                        )}
                        {tab === "security" && (
                            <SecurityTab notify={setToast} onLogout={logout} />
                        )}
                        {tab === "preferences" && (
                            <PreferencesTab notify={setToast} />
                        )}
                    </div>
                </main>
            </div>
            <ProfileToast message={toast} />
        </div>
    );
}

type ProfileNavigationProps = {
    tab: TabId;
    onChange: (tab: TabId) => void;
};

function MobileTabs({ tab, onChange }: ProfileNavigationProps) {
    return (
        <nav
            className="flex w-full gap-1 overflow-x-auto border-b border-[var(--bd)] bg-[var(--sf)] px-2 lg:hidden"
            aria-label="Profile settings"
        >
            {TABS.map(({ id, label, icon: Icon }) => (
                <button
                    key={id}
                    type="button"
                    onClick={() => onChange(id)}
                    aria-current={tab === id ? "page" : undefined}
                    className={`-mb-px flex shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm font-medium transition-colors ${
                        tab === id
                            ? "border-blue-500 text-blue-500"
                            : "border-transparent text-[var(--tx3)] hover:text-[var(--tx)]"
                    }`}
                >
                    <Icon size={16} />
                    {label}
                </button>
            ))}
        </nav>
    );
}

function ProfileSidebar({
    profile,
    tab,
    completion,
    onTabChange,
}: {
    profile: UserProfile;
    tab: TabId;
    completion: number;
    onTabChange: (tab: TabId) => void;
}) {
    return (
        <aside className="relative hidden overflow-hidden border-r border-[var(--bd)] bg-[var(--sf)] lg:flex lg:flex-col">
            <div className="pointer-events-none absolute -left-16 top-0 h-48 w-48 rounded-full bg-blue-500/10 blur-3xl" />
            <div className="relative p-5">
                <div className="flex items-center gap-3 rounded-2xl border border-[var(--bd)] bg-[var(--bg)] p-3">
                    <div className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-xl bg-gradient-to-br from-blue-600 to-cyan-400 font-semibold text-white">
                        {profile.avatarUrl ? (
                            <img
                                src={profile.avatarUrl}
                                alt=""
                                className="h-full w-full object-cover"
                            />
                        ) : (
                            getInitials(profile)
                        )}
                    </div>
                    <div className="min-w-0">
                        <p className="truncate text-sm font-semibold">
                            {profile.firstName || profile.username || "Your profile"}
                        </p>
                        <p className="truncate text-xs text-[var(--tx3)]">
                            {profile.email}
                        </p>
                    </div>
                </div>
                <nav className="mt-5 space-y-1" aria-label="Profile settings">
                    {TABS.map(({ id, label, icon: Icon }) => (
                        <button
                            key={id}
                            type="button"
                            onClick={() => onTabChange(id)}
                            aria-current={tab === id ? "page" : undefined}
                            className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-all ${
                                tab === id
                                    ? "bg-gradient-to-r from-blue-600 to-cyan-500 text-white shadow-md shadow-blue-500/15"
                                    : "text-[var(--tx2)] hover:translate-x-0.5 hover:bg-[var(--sf3)] hover:text-[var(--tx)]"
                            }`}
                        >
                            <Icon size={17} />
                            {label}
                        </button>
                    ))}
                </nav>
            </div>
            <div className="mt-auto p-5">
                <div className="relative overflow-hidden rounded-2xl border border-blue-500/20 bg-gradient-to-br from-blue-600/12 via-cyan-500/8 to-emerald-500/10 p-4">
                    <img
                        src={questionImage}
                        alt=""
                        className="profile-float pointer-events-none absolute -bottom-8 -right-8 w-32 opacity-20 dark:opacity-15"
                    />
                    <div className="relative">
                        <div className="flex items-center gap-2 text-sm font-semibold">
                            <Sparkles size={16} className="text-blue-500" />
                            Profile completion
                        </div>
                        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[var(--sf3)]">
                            <div
                                className="h-full rounded-full bg-gradient-to-r from-blue-600 via-cyan-400 to-emerald-400 transition-all duration-700"
                                style={{ width: `${completion}%` }}
                            />
                        </div>
                        <p className="mt-2 text-xs text-[var(--tx3)]">
                            {completion}% complete
                        </p>
                    </div>
                </div>
            </div>
        </aside>
    );
}

function ProfileAnimations() {
    return (
        <style>{`
            @keyframes profile-enter {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes profile-float {
                0%, 100% { transform: translate3d(0, 0, 0) rotate(-2deg); }
                50% { transform: translate3d(0, -8px, 0) rotate(1deg); }
            }
            .profile-enter { animation: profile-enter .35s ease-out both; }
            .profile-float { animation: profile-float 6s ease-in-out infinite; }
            @media (prefers-reduced-motion: reduce) {
                .profile-enter, .profile-float { animation: none; }
            }
        `}</style>
    );
}
