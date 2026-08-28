import Hero from "../components/Hero/Hero";
import Footer from "../components/Footer/footer";
import Navbar from "../components/Navbar/Navbar";
import HomeContent from "../components/Landing/HomeContent";
import { useWindowScrollDrive } from "../Hooks/useScrollDrive";

function Home() {
    const drive = useWindowScrollDrive();

    return (
        <>
            {/* Reading progress. Runs back down when you scroll up. */}
            <div
                className="fixed inset-x-0 top-0 z-[60] h-[3px]"
                aria-hidden="true"
            >
                <div
                    className="h-full bg-gradient-to-r from-blue-600 via-cyan-500 to-emerald-400"
                    style={{
                        width: `${drive.progress * 100}%`,
                        transition: "width 80ms linear",
                    }}
                />
            </div>

            <Navbar />
            <Hero drive={drive} />
            <HomeContent drive={drive} />
            <Footer />
        </>
    );
}

export default Home;
