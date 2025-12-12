/**
 * Changelog Modal Component
 * Displays release notes for new Archon versions
 */

import { ExternalLink, Rocket, Sparkles, Zap } from "lucide-react";
import { Button } from "../../ui/primitives/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "../../ui/primitives/dialog";
import { cn } from "../../ui/primitives/styles";

interface ChangelogModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  version?: string;
}

const CHANGELOG_V020 = {
  version: "0.2.0",
  headline: "Confluence Cloud Integration",
  features: [
    {
      icon: Sparkles,
      title: "Confluence Cloud Integration",
      description:
        "Sync your Confluence spaces directly into the RAG knowledge base. Search documentation alongside web crawls and uploads.",
    },
    {
      icon: Zap,
      title: "Incremental Smart Sync",
      description: "CQL-based queries fetch only modified pages. 90% bandwidth savings compared to full re-crawls.",
    },
    {
      icon: Rocket,
      title: "Advanced Search with Metadata",
      description:
        "Filter by Confluence space, find pages with JIRA links, and navigate page hierarchies with breadcrumbs.",
    },
  ],
  improvements: [
    "Multi-LLM Provider Support (OpenRouter, Anthropic, Grok)",
    "Migration Tracking System with UI alerts",
    "Version Checking with GitHub release monitoring",
    "Enhanced Web Crawling with domain filtering",
  ],
  docsUrl: "https://github.com/coleam00/Archon/blob/main/docs/bmad/confluence-user-communication-plan.md",
};

export const ChangelogModal: React.FC<ChangelogModalProps> = ({ open, onOpenChange, version = "0.2.0" }) => {
  const changelog = version === "0.2.0" ? CHANGELOG_V020 : CHANGELOG_V020;

  const handleDismiss = () => {
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-cyan-500" />
            What's New in v{changelog.version}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {/* Headline Feature */}
          <div
            className={cn(
              "p-4 rounded-lg",
              "bg-gradient-to-r from-cyan-500/10 to-fuchsia-500/10",
              "border border-cyan-500/20 dark:border-cyan-400/20",
            )}
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white/90 mb-1">{changelog.headline}</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              The headline feature of this release brings powerful documentation integration.
            </p>
          </div>

          {/* Key Features */}
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
              Key Features
            </h4>
            {changelog.features.map((feature) => (
              <div key={feature.title} className="flex gap-3">
                <div
                  className={cn(
                    "flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center",
                    "bg-cyan-500/10 dark:bg-cyan-500/20",
                  )}
                >
                  <feature.icon className="w-5 h-5 text-cyan-500" />
                </div>
                <div>
                  <h5 className="font-medium text-gray-900 dark:text-white/90">{feature.title}</h5>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{feature.description}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Improvements List */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
              Improvements
            </h4>
            <ul className="space-y-1">
              {changelog.improvements.map((improvement) => (
                <li key={improvement} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <span className="text-cyan-500 mt-1">•</span>
                  {improvement}
                </li>
              ))}
            </ul>
          </div>

          {/* Documentation Link */}
          <a
            href={changelog.docsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={cn("flex items-center gap-2 text-sm", "text-cyan-600 dark:text-cyan-400 hover:underline")}
          >
            <ExternalLink className="w-4 h-4" />
            View full documentation
          </a>
        </div>

        <DialogFooter>
          <Button
            onClick={handleDismiss}
            className={cn(
              "w-full sm:w-auto",
              "bg-gradient-to-r from-cyan-500 to-cyan-600",
              "hover:from-cyan-600 hover:to-cyan-700",
              "shadow-[0_0_15px_rgba(6,182,212,0.2)]",
            )}
          >
            Got it, thanks!
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
