/**
 * New Confluence Source Modal Component
 * Form for creating a new Confluence source connection
 */

import { ExternalLink, Folder, Globe, Key, Loader2, Mail } from "lucide-react";
import { useId, useState } from "react";
import { useToast } from "@/features/shared/hooks/useToast";
import { Button, Input, Label } from "../../ui/primitives";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../ui/primitives/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../ui/primitives/select";
import { cn, glassCard } from "../../ui/primitives/styles";
import { useCreateSource } from "../hooks/useConfluenceQueries";
import type { CreateSourceRequest } from "../types";

interface NewConfluenceSourceModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

const deletionStrategies = [
  {
    value: "weekly_reconciliation",
    label: "Weekly Reconciliation",
    description: "Check for deleted pages once per week",
  },
  { value: "every_sync", label: "Every Sync", description: "Check every sync (slower but more accurate)" },
  { value: "on_demand", label: "On Demand", description: "Only check when manually triggered" },
];

// Form validation patterns
const URL_PATTERN = /^https:\/\/.+\.atlassian\.net\/wiki\/?$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SPACE_KEY_PATTERN = /^[A-Z0-9]+$/;

export const NewConfluenceSourceModal: React.FC<NewConfluenceSourceModalProps> = ({
  open,
  onOpenChange,
  onSuccess,
}) => {
  const { showToast } = useToast();
  const createMutation = useCreateSource();

  // Form IDs
  const urlId = useId();
  const emailId = useId();
  const tokenId = useId();
  const spaceKeyId = useId();
  const strategyId = useId();

  // Form state
  const [baseUrl, setBaseUrl] = useState("");
  const [email, setEmail] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [spaceKey, setSpaceKey] = useState("");
  const [deletionStrategy, setDeletionStrategy] = useState("weekly_reconciliation");

  // Validation state
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showUrlWarning, setShowUrlWarning] = useState(false);

  const resetForm = () => {
    setBaseUrl("");
    setEmail("");
    setApiToken("");
    setSpaceKey("");
    setDeletionStrategy("weekly_reconciliation");
    setErrors({});
    setShowUrlWarning(false);
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    // URL validation
    if (!baseUrl) {
      newErrors.baseUrl = "Confluence URL is required";
    } else if (!baseUrl.startsWith("https://")) {
      newErrors.baseUrl = "URL must start with https://";
    } else if (!URL_PATTERN.test(baseUrl)) {
      setShowUrlWarning(true);
    }

    // Email validation
    if (!email) {
      newErrors.email = "Email is required";
    } else if (!EMAIL_PATTERN.test(email)) {
      newErrors.email = "Please enter a valid email address";
    }

    // API Token validation
    if (!apiToken) {
      newErrors.apiToken = "API token is required";
    } else if (apiToken.length < 10) {
      newErrors.apiToken = "API token seems too short";
    }

    // Space Key validation
    if (!spaceKey) {
      newErrors.spaceKey = "Space key is required";
    } else if (!SPACE_KEY_PATTERN.test(spaceKey)) {
      newErrors.spaceKey = "Space key must be uppercase letters and numbers only";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    try {
      const request: CreateSourceRequest = {
        base_url: baseUrl.replace(/\/$/, ""), // Remove trailing slash
        email,
        api_token: apiToken,
        space_key: spaceKey.toUpperCase(),
        deletion_strategy: deletionStrategy,
      };

      await createMutation.mutateAsync(request);
      resetForm();
      onSuccess();
      onOpenChange(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to create Confluence source";
      showToast(message, "error");
    }
  };

  const isSubmitting = createMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Add Confluence Source</DialogTitle>
          <DialogDescription>Connect your Confluence Cloud space to search its content.</DialogDescription>
        </DialogHeader>

        <div className="space-y-6 mt-4">
          {/* Confluence URL */}
          <div className="space-y-2">
            <Label htmlFor={urlId} className="text-sm font-medium text-gray-900 dark:text-white/90">
              Confluence Cloud URL
            </Label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Globe className="h-5 w-5 text-cyan-500" />
              </div>
              <Input
                id={urlId}
                type="url"
                placeholder="https://your-company.atlassian.net/wiki"
                value={baseUrl}
                onChange={(e) => {
                  setBaseUrl(e.target.value);
                  setShowUrlWarning(false);
                  if (errors.baseUrl) setErrors((prev) => ({ ...prev, baseUrl: "" }));
                }}
                disabled={isSubmitting}
                className={cn(
                  "pl-10 h-12",
                  glassCard.blur.md,
                  glassCard.transparency.medium,
                  "border-gray-300/60 dark:border-gray-600/60 focus:border-cyan-400/70",
                  errors.baseUrl && "border-red-400/70",
                )}
              />
            </div>
            {errors.baseUrl && <p className="text-sm text-red-500">{errors.baseUrl}</p>}
            {showUrlWarning && !errors.baseUrl && (
              <p className="text-sm text-yellow-500">
                URL doesn't match typical Confluence Cloud format (*.atlassian.net/wiki)
              </p>
            )}
          </div>

          {/* Email */}
          <div className="space-y-2">
            <Label htmlFor={emailId} className="text-sm font-medium text-gray-900 dark:text-white/90">
              Atlassian Email
            </Label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Mail className="h-5 w-5 text-cyan-500" />
              </div>
              <Input
                id={emailId}
                type="email"
                placeholder="your-email@company.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (errors.email) setErrors((prev) => ({ ...prev, email: "" }));
                }}
                disabled={isSubmitting}
                className={cn(
                  "pl-10 h-12",
                  glassCard.blur.md,
                  glassCard.transparency.medium,
                  "border-gray-300/60 dark:border-gray-600/60 focus:border-cyan-400/70",
                  errors.email && "border-red-400/70",
                )}
              />
            </div>
            {errors.email && <p className="text-sm text-red-500">{errors.email}</p>}
          </div>

          {/* API Token */}
          <div className="space-y-2">
            <Label htmlFor={tokenId} className="text-sm font-medium text-gray-900 dark:text-white/90">
              API Token
            </Label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Key className="h-5 w-5 text-cyan-500" />
              </div>
              <Input
                id={tokenId}
                type="password"
                placeholder="Enter your Atlassian API token"
                value={apiToken}
                onChange={(e) => {
                  setApiToken(e.target.value);
                  if (errors.apiToken) setErrors((prev) => ({ ...prev, apiToken: "" }));
                }}
                disabled={isSubmitting}
                className={cn(
                  "pl-10 h-12",
                  glassCard.blur.md,
                  glassCard.transparency.medium,
                  "border-gray-300/60 dark:border-gray-600/60 focus:border-cyan-400/70",
                  errors.apiToken && "border-red-400/70",
                )}
              />
            </div>
            {errors.apiToken && <p className="text-sm text-red-500">{errors.apiToken}</p>}
            <a
              href="https://id.atlassian.com/manage-profile/security/api-tokens"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-cyan-600 dark:text-cyan-400 hover:underline"
            >
              <ExternalLink className="w-3 h-3" />
              Generate token at id.atlassian.com
            </a>
          </div>

          {/* Space Key */}
          <div className="space-y-2">
            <Label htmlFor={spaceKeyId} className="text-sm font-medium text-gray-900 dark:text-white/90">
              Space Key
            </Label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Folder className="h-5 w-5 text-cyan-500" />
              </div>
              <Input
                id={spaceKeyId}
                type="text"
                placeholder="DEVDOCS"
                value={spaceKey}
                onChange={(e) => {
                  setSpaceKey(e.target.value.toUpperCase());
                  if (errors.spaceKey) setErrors((prev) => ({ ...prev, spaceKey: "" }));
                }}
                disabled={isSubmitting}
                className={cn(
                  "pl-10 h-12 uppercase",
                  glassCard.blur.md,
                  glassCard.transparency.medium,
                  "border-gray-300/60 dark:border-gray-600/60 focus:border-cyan-400/70",
                  errors.spaceKey && "border-red-400/70",
                )}
              />
            </div>
            {errors.spaceKey && <p className="text-sm text-red-500">{errors.spaceKey}</p>}
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Find your space key in the Confluence URL (e.g., /spaces/DEVDOCS/...)
            </p>
          </div>

          {/* Deletion Strategy */}
          <div className="space-y-2">
            <Label htmlFor={strategyId} className="text-sm font-medium text-gray-900 dark:text-white/90">
              Deletion Detection
            </Label>
            <Select value={deletionStrategy} onValueChange={setDeletionStrategy} disabled={isSubmitting}>
              <SelectTrigger
                className={cn(
                  "h-12",
                  glassCard.blur.md,
                  glassCard.transparency.medium,
                  "border-gray-300/60 dark:border-gray-600/60",
                )}
              >
                <SelectValue placeholder="Select deletion strategy" />
              </SelectTrigger>
              <SelectContent>
                {deletionStrategies.map((strategy) => (
                  <SelectItem key={strategy.value} value={strategy.value}>
                    <div className="flex flex-col">
                      <span>{strategy.label}</span>
                      <span className="text-xs text-gray-500">{strategy.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Submit Button */}
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className={cn(
              "w-full h-12 bg-gradient-to-r from-cyan-500 to-cyan-600",
              "hover:from-cyan-600 hover:to-cyan-700",
              "backdrop-blur-md border border-cyan-400/50",
              "shadow-[0_0_20px_rgba(6,182,212,0.25)] hover:shadow-[0_0_30px_rgba(6,182,212,0.35)]",
              "transition-all duration-200",
            )}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creating Source...
              </>
            ) : (
              <>
                <Folder className="w-4 h-4 mr-2" />
                Add Confluence Source
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
