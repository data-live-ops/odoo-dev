/** @odoo-module **/

import { patch } from "@web/core/utils/patch";

console.log("[Canned Response Render] Module loading...");

// Delay patch until UseSuggestion is loaded
(async () => {
    try {
        // Import UseSuggestion dynamically
        const { UseSuggestion } = await odoo.loader.modules.get("@mail/core/common/suggestion_hook");

        console.log("[Canned Response Render] UseSuggestion loaded:", UseSuggestion);

        // Patch UseSuggestion.insert
        patch(UseSuggestion.prototype, {
            async insert(option) {
                console.log("[Canned Response Render] Insert called with:", option);

                // Check if this is a canned response with placeholders
                if (option.cannedResponse && option.label && option.label.includes('[')) {
                    console.log("[Canned Response Render] Found placeholders in:", option.cannedResponse.source);

                    try {
                        // Get channel ID from thread
                        const channelId = this.thread?.id;
                        console.log("[Canned Response Render] Channel ID:", channelId);

                        // Call backend to render placeholders
                        const orm = this.env.services.orm;
                        const rendered = await orm.call(
                            "mail.canned.response",
                            "render_substitution",
                            [option.cannedResponse.id],
                            { channel_id: channelId }
                        );

                        console.log("[Canned Response Render] Rendered:", rendered.substring(0, 100));

                        // Update label with rendered text
                        option.label = rendered;
                    } catch (error) {
                        console.error("[Canned Response Render] Error:", error);
                        // Continue with original text on error
                    }
                }

                // Call original insert
                return super.insert(option);
            },
        });

        console.log("[Canned Response Render] Patch applied successfully!");
    } catch (error) {
        console.error("[Canned Response Render] Failed to patch:", error);
    }
})();
