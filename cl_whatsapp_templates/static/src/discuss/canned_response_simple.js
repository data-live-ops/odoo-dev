/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        console.log("[Canned Response Render] Patching Composer for placeholder rendering ✅");

        onMounted(() => {
            // Wrap the suggestion insert handler post-mount
            if (this.suggestion && this.suggestion.insert) {
                const originalInsert = this.suggestion.insert.bind(this.suggestion);
                this.suggestion.insert = async (option) => {
                    console.log("[Canned Response Render] Insert intercepted:", option);

                    if (option.cannedResponse && option.label && option.label.includes('[')) {
                        // Try multiple ways to get thread/channel ID
                        const channelId = this.thread?.id || this.props.thread?.id || this.composer?.thread?.id;

                        console.log("[Canned Response Render] Debug - this.thread:", this.thread);
                        console.log("[Canned Response Render] Debug - this.props.thread:", this.props.thread);
                        console.log("[Canned Response Render] Debug - channelId:", channelId);

                        try {
                            console.log("[Canned Response Render] Calling RPC for channel:", channelId);

                            const rendered = await this.orm.call(
                                "mail.canned.response",
                                "render_substitution",
                                [option.cannedResponse.id],
                                { channel_id: channelId }
                            );

                            console.log("[Canned Response Render] RPC rendered:", rendered.substring(0, 100));
                            option.label = rendered;  // Update label for insertion
                        } catch (error) {
                            console.error("[Canned Response Render] RPC error:", error);
                            // Fallback: insert original
                        }
                    }

                    // Call original to perform insertion
                    return originalInsert(option);
                };
                console.log("[Canned Response Render] Insert wrapper applied ✅");
            } else {
                console.warn("[Canned Response Render] Suggestion hook not ready—retrying on next mount");
                // Self-heal: Re-apply on re-mount (e.g., thread switch)
                setTimeout(() => this.setupSuggestionsWrapper(), 0);
            }
        });
    },

    setupSuggestionsWrapper() {
        // Helper for re-mounts
        if (!this.suggestion || !this.suggestion.insert) {
            return;
        }

        const originalInsert = this.suggestion.insert.bind(this.suggestion);
        this.suggestion.insert = async (option) => {
            if (option.cannedResponse && option.label && option.label.includes('[')) {
                // Try multiple ways to get thread/channel ID
                const channelId = this.thread?.id || this.props.thread?.id || this.composer?.thread?.id;

                try {
                    const rendered = await this.orm.call(
                        "mail.canned.response",
                        "render_substitution",
                        [option.cannedResponse.id],
                        { channel_id: channelId }
                    );
                    option.label = rendered;
                } catch (error) {
                    console.error("[Canned Response Render] RPC error:", error);
                }
            }
            return originalInsert(option);
        };
    },
});

console.log("[Canned Response Render] Patch applied successfully");
