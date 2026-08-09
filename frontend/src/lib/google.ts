const GSI_SRC = "https://accounts.google.com/gsi/client";

declare global {
	interface Window {
		google?: {
			accounts: {
				id: {
					initialize(config: {
						client_id: string;
						callback: (response: { credential: string }) => void;
						auto_select?: boolean;
						cancel_on_tap_outside?: boolean;
						use_fedcm_for_prompt?: boolean;
					}): void;
					renderButton(
						parent: HTMLElement,
						options: {
							type?: "standard" | "icon";
							theme?: "outline" | "filled_blue" | "filled_black";
							size?: "small" | "medium" | "large";
							text?: "signin_with" | "signup_with" | "continue_with" | "signin";
							shape?: "rectangular" | "pill" | "circle" | "square";
							width?: number;
							locale?: string;
							logo_alignment?: "left" | "center";
						},
					): void;
					disableAutoSelect(): void;
				};
			};
		};
	}
}

let loader: Promise<void> | null = null;

export function loadGoogleScript(): Promise<void> {
	if (loader) return loader;

	loader = new Promise<void>((resolve, reject) => {
		if (window.google?.accounts?.id) {
			resolve();
			return;
		}

		const existing = document.querySelector<HTMLScriptElement>(
			`script[src="${GSI_SRC}"]`,
		);
		if (existing) {
			existing.addEventListener("load", () => resolve());
			existing.addEventListener("error", () =>
				reject(new Error("failed to load Google Identity Services")),
			);
			return;
		}

		const script = document.createElement("script");
		script.src = GSI_SRC;
		script.async = true;
		script.defer = true;
		script.onload = () => resolve();
		script.onerror = () => {
			loader = null;
			reject(new Error("failed to load Google Identity Services"));
		};
		document.head.appendChild(script);
	});

	return loader;
}

export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as
	| string
	| undefined;

export function clearGoogleAutoSelect(): void {
	window.google?.accounts.id.disableAutoSelect();
}