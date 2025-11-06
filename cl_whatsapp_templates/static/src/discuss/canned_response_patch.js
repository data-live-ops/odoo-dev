/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";

console.log("[Canned Response Variables] Patching Composer for variable support");

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        console.log("[Canned Response Variables] Composer patched");
    },

    /**
     * Override to add variable replacement for canned responses
     */
    async onClickCannedResponse(cannedResponse) {
        console.log("[Canned Response Variables] Canned response clicked:", cannedResponse);

        try {
            // Get channel ID for context
            const channelId = this.props.thread?.id;
            console.log("[Canned Response Variables] Channel ID:", channelId);

            // Call backend to get substitution with variables replaced
            const result = await this.orm.call(
                "mail.canned.response",
                "_get_substitution_with_variables",
                [cannedResponse.id],
                { channel_id: channelId }
            );

            console.log("[Canned Response Variables] Substitution with variables:", result);

            // Insert into composer
            if (this.props.composer) {
                // Replace current text with canned response
                const currentText = this.props.composer.text || "";

                // If text ends with shortcut (e.g., ":hello"), remove it
                const shortcutPattern = new RegExp(`:${cannedResponse.source}$`);
                const newText = currentText.replace(shortcutPattern, result);

                this.props.composer.text = newText;
            }

            // Update last_used
            await this.orm.write("mail.canned.response", [cannedResponse.id], {
                last_used: new Date().toISOString()
            });

            console.log("[Canned Response Variables] Canned response inserted successfully");
        } catch (error) {
            console.error("[Canned Response Variables] Error:", error);

            // Fallback to original behavior
            if (super.onClickCannedResponse) {
                await super.onClickCannedResponse(cannedResponse);
            }
        }
    },
});

console.log("[Canned Response Variables] Patch applied successfully");
