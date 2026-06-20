function Logo(){
    return(
        <div className="flex items-center gap-2">
            <img 
                src="src/assets/logo_black.svg" 
                alt="SLASHUS LOGO" 
                className="h-12"
            />
            <h3 className="text-xl font-bold">
                SLASHUS
            </h3>
        </div>
    );
}

export default Logo;