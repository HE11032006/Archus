"use client";

import * as React from "react";
import { motion, type Variants } from "framer-motion";
import { cn } from "@/lib/utils";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring",
      stiffness: 100,
      damping: 10,
    },
  },
};

interface BentoGridShowcaseProps {
  integration: React.ReactNode;
  trackers: React.ReactNode;
  statistic: React.ReactNode;
  focus: React.ReactNode;
  productivity: React.ReactNode;
  shortcuts: React.ReactNode;
  className?: string;
}

export const BentoGridShowcase = ({
  integration,
  trackers,
  statistic,
  focus,
  productivity,
  shortcuts,
  className,
}: BentoGridShowcaseProps) => {
  return (
    <motion.section
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className={cn(
        "grid w-full grid-cols-1 gap-4 md:grid-cols-3 md:grid-rows-[minmax(200px,1fr)_minmax(220px,1fr)_minmax(160px,auto)] md:gap-5",
        "auto-rows-[minmax(200px,auto)]",
        className
      )}
    >
      <motion.div variants={itemVariants} className="min-h-[420px] md:col-span-1 md:row-span-3 md:min-h-0">
        {integration}
      </motion.div>
      <motion.div variants={itemVariants} className="md:col-span-1 md:row-span-1">
        {trackers}
      </motion.div>
      <motion.div variants={itemVariants} className="md:col-span-1 md:row-span-1">
        {statistic}
      </motion.div>
      <motion.div variants={itemVariants} className="md:col-span-1 md:row-span-1">
        {focus}
      </motion.div>
      <motion.div variants={itemVariants} className="md:col-span-1 md:row-span-1">
        {productivity}
      </motion.div>
      <motion.div variants={itemVariants} className="md:col-span-2 md:row-span-1">
        {shortcuts}
      </motion.div>
    </motion.section>
  );
};
