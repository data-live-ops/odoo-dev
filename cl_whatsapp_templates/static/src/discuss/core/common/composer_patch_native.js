/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        console.log("[WhatsApp Templates] Native integration patch loaded!");
        this.orm = useService("orm");
        this.templateCommandsState = useState({
            commands: [],
            loaded: false
        });

        onMounted(async () => {
            await this._loadTemplateCommands();
        });
    },

    async _loadTemplateCommands() {
        try {
            const templates = await this.orm.call(
                "discuss.channel",
                "search_templates_by_command",
                [""]
            );

            // Transform templates to command format
            this.templateCommandsState.commands = templates
                .filter(t => t.shortcut)
                .map(t => ({
                    name: t.shortcut.replace('/', ''),
                    help: t.description || t.name,
                    template: t
                }));

            this.templateCommandsState.loaded = true;

            console.log(`[WhatsApp Templates] Loaded ${this.templateCommandsState.commands.length} template commands`);
        } catch (error) {
            console.error("[WhatsApp Templates] Error loading templates:", error);
        }
    },

    // Override getSuggestions to inject template commands
    get suggestions() {
        const originalSuggestions = super.suggestions || [];

        if (!this.templateCommandsState.loaded) {
            return originalSuggestions;
        }

        // Add template commands to suggestions
        const templateSuggestions = this.templateCommandsState.commands.map(cmd => ({
            label: cmd.name,
            classList: "o-mail-Composer-suggestion",
            partner: null,
            onSelect: async () => {
                await this._executeTemplateCommand(cmd.template);
            },
        }));

        console.log("[WhatsApp Templates] Injecting template suggestions:", templateSuggestions.length);

        return [...originalSuggestions, ...templateSuggestions];
    },

    async _executeTemplateCommand(template) {
        console.log("[WhatsApp Templates] Executing:", template.name);

        try {
            const channelId = this.props.thread?.id;
            let content;

            if (channelId) {
                const result = await this.orm.call(
                    "discuss.channel",
                    "get_template_content_for_channel",
                    [channelId, template.id]
                );
                content = result.error ? template.content : result.content;
            } else {
                content = template.content;
            }

            // Set composer text
            if (this.props.composer) {
                this.props.composer.text = content;
            }

            console.log("[WhatsApp Templates] Inserted:", content.substring(0, 50) + "...");
        } catch (error) {
            console.error("[WhatsApp Templates] Error:", error);
        }
    }
});
