import AccuracyCard from "./AccuracyCard";
import FeatureItem from "./FeatureItem";
import SectionHeader from "./SectionHeader";
import { FEATURES } from "./features.data";

export default function Features() {
  return (
    <section className="bg-[#f7f7f7] py-24">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeader />

        <div className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <AccuracyCard />

          <div className="space-y-10">
            {FEATURES.map((feature) => (
              <FeatureItem
                key={feature.title}
                feature={feature}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}