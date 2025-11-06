/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";

console.log("[Canned Response Render] Patching Composer for placeholder rendering");

// Store original suggestion insert handler
const originalSuggestionPropsGetter = Composer.prototype.suggestionProps;

patch(Composer.prototype, {
    /**
     * Patch suggestionProps to wrap onSelect handler
     */
    get suggestionProps() {
        const props = originalSuggestionPropsGetter?.call(this) || super.suggestionProps;

        if (!props || !props.onSelect) {
            return props;
        }

        // Store original onSelect
        const originalOnSelect = props.onSelect;

        // Wrap onSelect to render placeholders
        props.onSelect = async (ev, option) => {
            console.log("[Canned Response Render] onSelect called with:", option);

            // Check if this is canned response with placeholders
            if (option.cannedResponse && option.label && option.label.includes('[')) {
                console.log("[Canned Response Render] Found placeholders, rendering...");

                try {
                    // Get channel ID
                    const channelId = this.props.thread?.id;

                    // Call backend to render
                    const rendered = await this.orm.call(
                        "mail.canned.response",
                        "render_substitution",
                        [option.cannedResponse.id],
                        { channel_id: channelId }
                    );

                    console.log("[Canned Response Render] Rendered:", rendered.substring(0, 100));

                    // Replace label
                    option.label = rendered;
                } catch (error) {
                    console.error("[Canned Response Render] Error:", error);
                }
            }

            // Call original handler
            return originalOnSelect(ev, option);
        };

        return props;
    },
});

console.log("[Canned Response Render] Patch applied successfully");
