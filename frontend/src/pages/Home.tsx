import FeatureCard from '../components/Feature/Features';
import Hero from '../components/Hero/Hero';
import Footer from '../components/Footer/footer';
import Navbar from '../components/Navbar/Navbar';
import DemoWindow from '../components/DemoWindow/DemoWindow';
import HowItWorks from '../components/HowItWork/HowWorks';


function Home(){
    return(
        <>
            <Navbar/>
            <Hero />
            <DemoWindow />
            <HowItWorks />
            <FeatureCard />
            <Footer />
        </>
    )
}

export default Home;