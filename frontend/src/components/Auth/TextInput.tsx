interface TextInputProps {
    id: string;
    label: string;
    type?: string;
    value: string,
    name: string,
    required?: boolean,
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

function TextInput({
    id,
    label,
    type = "text",
    name,
    value,
    required=false,
    onChange
}: TextInputProps) {
    return (
        <div className="relative">
            <input
                id={id}
                type={type}
                name={name}
                value={value}
                required={required}
                onChange={onChange}
                placeholder=" "
                className="
                    peer
                    w-full
                    h-12
                    px-4
                    rounded-xl
                    border
                    border-slate-300
                    outline-none
                    focus:border-indigo-500
                    focus:ring-2
                    focus:ring-indigo-100
                "
            />

            <label
                htmlFor={id}
                className="
                    absolute
                    left-3
                    top-3
                    bg-white
                    px-1
                    text-slate-500
                    transition-all
                    pointer-events-none

                    peer-focus:-top-2
                    peer-focus:text-xs
                    peer-focus:text-indigo-500

                    peer-[:not(:placeholder-shown)]:-top-2
                    peer-[:not(:placeholder-shown)]:text-xs
                "
            >
                {label}
            </label>
        </div>
    );
}

export default TextInput;