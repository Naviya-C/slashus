import AuthFB from "../Atomic/AuthFB";
import AuthGl from "../Atomic/AuthGl";
import AuthX from "../Atomic/AuthX";

function OAuth(){
    return(
        <div className="flex justify-center gap-4 mb-8">
            <AuthGl />
            <AuthFB />
            <AuthX />
        </div>
    );
}

export default OAuth;