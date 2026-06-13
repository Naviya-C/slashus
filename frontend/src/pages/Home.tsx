import FeatureCard from '../components/Card/FeaturedCard';
import Hero from '../components/Hero/Hero';
import Navbar from '../components/Navbar/Navbar';


function Home(){
    return(
        <>
            <Navbar/>
            <Hero />
            <FeatureCard 
                title='Summarize'
                description='Intelligently summarize your educational resources into clear and concise insights.Extract key concepts, important information, and essential takeaways with ease.Save time while improving comprehension and knowledge retention.Transform complex content into accessible and actionable learning materials.'
                image='null'
            />
        </>
    )
}

export default Home;