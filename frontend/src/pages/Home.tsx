import FeatureCard from '../components/Card/FeaturedCard';
import Hero from '../components/Hero/Hero';
import Footer from '../components/Footer/footer';
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
                reverse = {false}
            />
            <FeatureCard 
                title='Quizzers'
                description='Create intelligent, interactive quizzes from your resources in seconds.Evaluate understanding, reinforce key concepts, and support effective learning through personalized assessments.'
                image='null'
                reverse = {true}
            />
            <FeatureCard 
                title='Papers'
                description='Create professional question papers, marking schemes, and automated grading systems in seconds.Simplify assessment creation and evaluation while maintaining quality and consistency.'
                image='null'
                reverse = {false}
            />
            <FeatureCard 
                title='Auto Marking'
                description='Intelligently summarize your educational resources into clear and concise insights.Extract key concepts, important information, and essential takeaways with ease.Save time while improving comprehension and knowledge retention.Transform complex content into accessible and actionable learning materials.'
                image='null'
                reverse = {true}
            />
            <Footer />
        </>
    )
}

export default Home;