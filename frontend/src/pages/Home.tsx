import Hero from "../components/Hero/Hero";
import Footer from "../components/Footer/footer";
import Navbar from "../components/Navbar/Navbar";
import HomeContent from "../components/Landing/HomeContent";

function Home() {
    return (
        <>
            <Navbar />
            <Hero />
            <HomeContent />
            <Footer />
        </>
    );
}

export default Home;
