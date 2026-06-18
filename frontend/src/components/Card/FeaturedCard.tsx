type FeatureCardProps = {
    title: string,
    description: string,
    image: string,
    reverse: boolean
}

function FeatureCard({
    title,
    description,
    image,
    reverse = false
}: FeatureCardProps){
    return(
        <div className={`
                flex flex-col items-center gap-12
                md:flex-row
                mx-60
                pt-5
                ${reverse ? "md:flex-row-reverse" : ""}
            `}
        >
            <div className="w-full md:w-1/2">
                <img src={image} />
            </div>
            <div className="w-full md:w-1/2 px-15 pb-10 h-120 rounded-4xl shadow-md">
                <h2 className="text-3xl font-bold flex justify-center items-center">{title}</h2>
                <p className="mt-4 text-lg text-gray-600 pt-2">{description}</p>
            </div>
        </div>
    );
}

export default FeatureCard;