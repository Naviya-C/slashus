import logo from '../../assets/logo_black.svg'


function Logo(){
    return(
        <div className="flex items-center gap-2">
            <img 
                src = {logo} 
                alt="SLASHUS LOGO" 
                className="h-12 rounded-xl"
            />
            <h3 className="text-xl font-bold">
                SLASH<span className = 'text-blue-500'>US</span>
            </h3>
        </div>
    );
}

export default Logo;