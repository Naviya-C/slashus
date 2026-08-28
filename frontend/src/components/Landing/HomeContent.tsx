import Outcomes from "./Outcomes";
import LearningWorkspace from "./LearningWorkspace";
import UseCases from "./UseCases";
import TrustSection from "./TrustSection";
import FinalCta from "./FinalCta";
import Reveal from "./Reveal";
import type { ScrollDrive } from "../../Hooks/useScrollDrive";

type Props = {
    drive: ScrollDrive;
};

export default function HomeContent({ drive }: Props) {
    return (
        <>
            <Outcomes />
            <LearningWorkspace drive={drive} />
            <UseCases />
            <Reveal>
                <TrustSection />
            </Reveal>
            <Reveal>
                <FinalCta />
            </Reveal>
        </>
    );
}
