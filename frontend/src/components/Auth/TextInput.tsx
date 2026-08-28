import type { ChangeEventHandler } from "react";

interface TextInputProps {
    id: string;
    label: string;
    type?: string;
    name: string;
    required?: boolean;
    value?: string;
    minLength?: number;
    autoComplete?: string;
    onChange?: ChangeEventHandler<HTMLInputElement>;
}

const TextInput = (props: TextInputProps) => {
    return (
        <div className="relative">
            <input
                id={props.id}
                type={props.type}
                name={props.name}
                required={props.required}
                value={props.value}
                minLength={props.minLength}
                autoComplete={props.autoComplete}
                onChange={props.onChange}
                placeholder=" "
                className="
                    peer
                    w-full
                    h-12
                    px-4
                    rounded-xl
                    border
                    border-slate-300
                    bg-white
                    text-neutral-900
                    outline-none
                    transition-colors
                    focus:border-indigo-500
                    focus:ring-2
                    focus:ring-indigo-100
                    dark:border-neutral-700
                    dark:bg-neutral-900
                    dark:text-neutral-100
                    dark:focus:border-indigo-400
                    dark:focus:ring-indigo-500/20
                "
            />

            <label
                htmlFor={props.id}
                className="
                    absolute
                    left-3
                    top-3
                    bg-white
                    px-1
                    text-slate-500
                    transition-all
                    pointer-events-none
                    dark:bg-neutral-900
                    dark:text-neutral-400

                    peer-focus:-top-2
                    peer-focus:text-xs
                    peer-focus:text-indigo-500
                    dark:peer-focus:text-indigo-400

                    peer-[:not(:placeholder-shown)]:-top-2
                    peer-[:not(:placeholder-shown)]:text-xs
                "
            >
                {props.label}
            </label>
        </div>
    );
};

export default TextInput;
