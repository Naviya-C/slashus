interface types{
    name:string
}

export default function NavButton({name}:types){
    return(
        <button
            className="
                text-gray-700
                hover:text-black hover:underline hover:font-bold
                transition
                cursor-pointer
            "
        >
            {name}
        </button>
    );
}