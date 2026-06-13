function Logo(){
    return(
        <div className="flex items-center gap-2">
            <img 
                src="src/assets/logo_black.svg" 
                alt="SLUSHUS LOGO" 
                className="h-12"
            />
            <h3 className="text-xl font-bold">
                SLUSHUS
            </h3>
        </div>
    );
}

export default Logo;