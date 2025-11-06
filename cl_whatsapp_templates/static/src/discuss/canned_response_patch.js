/** @odoo-module **/

import { SuggestionService } from "@mail/core/common/suggestion_service";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

console.log("[Canned Response Variables] Patching SuggestionService for variable support");

patch(SuggestionService.prototype, {
    /**
     * Override to add variable replacement for canned responses
     */
    async fetchSuggestions(search, { thread, abortSignal }) {
        console.log("[Canned Response Variables] Fetching suggestions for:", search.delimiter);

        // Call parent method first
        await super.fetchSuggestions(search, { thread, abortSignal });

        // Only process canned responses
        if (search.delimiter !== ":") {
            return;
        }

        // Get canned responses from store
        const cannedResponseStore = this.store["mail.canned.response"];
        if (!cannedResponseStore || !cannedResponseStore.records) {
            console.log("[Canned Response Variables] No canned response store found");
            return;
        }

        const cannedResponses = Object.values(cannedResponseStore.records);

        if (cannedResponses.length === 0) {
            console.log("[Canned Response Variables] No canned responses found");
            return;
        }

        console.log(`[Canned Response Variables] Processing ${cannedResponses.length} canned responses`);

        // Replace variables in each canned response substitution
        for (const cannedResponse of cannedResponses) {
            try {
                // Check if substitution contains variables
                if (!cannedResponse.substitution.includes('{{')) {
                    continue;
                }

                console.log(`[Canned Response Variables] Found variables in: ${cannedResponse.source}`);

                // Get channel ID
                const channelId = thread?.id;

                // Call backend to replace variables
                const result = await rpc("/web/dataset/call_kw/mail.canned.response/_get_substitution_with_variables", {
                    model: "mail.canned.response",
                    method: "_get_substitution_with_variables",
                    args: [cannedResponse.id],
                    kwargs: {
                        channel_id: channelId
                    },
                }, { signal: abortSignal });

                // Update substitution in store
                cannedResponse.substitution = result;

                console.log(`[Canned Response Variables] ✓ Replaced variables in ${cannedResponse.source}`);
            } catch (error) {
                if (error.name === 'AbortError') {
                    throw error;
                }
                console.error(`[Canned Response Variables] Error processing ${cannedResponse.source}:`, error);
                // Keep original substitution on error
            }
        }
    },
});

console.log("[Canned Response Variables] Patch applied successfully");
