/** @odoo-module **/

import { UseSuggestion } from "@mail/core/common/suggestion_hook";
import { patch } from "@web/core/utils/patch";

console.log("[Canned Response Render] Patching UseSuggestion class for placeholder rendering");

patch(UseSuggestion.prototype, {
    /**
     * Override insert to render placeholders before insertion
     */
    async insert(option) {
        console.log("[Canned Response Render] Inserting option:", option);

        // Check if this is a canned response with placeholders
        if (option.cannedResponse && option.label && option.label.includes('[')) {
            console.log("[Canned Response Render] Found placeholders in:", option.cannedResponse.source);

            try {
                // Get channel ID
                const channelId = this.thread?.id;
                console.log("[Canned Response Render] Rendering for channel:", channelId);

                // Call backend to render placeholders
                const rendered = await this.env.services.orm.call(
                    "mail.canned.response",
                    "render_substitution",
                    [option.cannedResponse.id],
                    { channel_id: channelId }
                );

                console.log("[Canned Response Render] Rendered text:", rendered.substring(0, 100));

                // Replace label with rendered text
                option.label = rendered;
            } catch (error) {
                console.error("[Canned Response Render] Error rendering:", error);
                // Continue with original label on error
            }
        }

        // Call parent insert
        return super.insert(option);
    },
});

console.log("[Canned Response Render] Patch applied successfully");
