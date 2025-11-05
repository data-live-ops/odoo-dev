/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");

        // State to hold template commands
        this.templateCommands = useState({
            loaded: false,
            commands: []
        });

        // Load templates on component initialization
        onWillStart(async () => {
            await this._loadTemplateCommands();
        });
    },

    async _loadTemplateCommands() {
        try {
            console.log("[WhatsApp Templates] Loading template commands...");

            const templates = await this.orm.call(
                "discuss.channel",
                "search_templates_by_command",
                [""]
            );

            // Store template commands
            this.templateCommands.commands = templates.filter(t => t.shortcut);
            this.templateCommands.loaded = true;

            console.log(`[WhatsApp Templates] Loaded ${this.templateCommands.commands.length} commands:`,
                this.templateCommands.commands.map(t => t.shortcut));
        } catch (error) {
            console.error("[WhatsApp Templates] Failed to load commands:", error);
        }
    },

    // Override or extend the suggestions getter
    get commandSuggestions() {
        // Get original suggestions (help, leave, etc.)
        const originalSuggestions = super.commandSuggestions || [];

        console.log("[WhatsApp Templates] Original suggestions:", originalSuggestions);

        if (!this.templateCommands.loaded) {
            return originalSuggestions;
        }

        // Convert templates to command suggestions format
        const templateSuggestions = this.templateCommands.commands.map(template => {
            const commandName = template.shortcut.replace('/', '');

            return {
                name: commandName,
                description: template.description || template.name,
                execute: async () => {
                    await this._executeTemplateCommand(template);
                }
            };
        });

        console.log("[WhatsApp Templates] Adding template suggestions:", templateSuggestions.length);

        // Combine original and template suggestions
        return [...originalSuggestions, ...templateSuggestions];
    },

    async _executeTemplateCommand(template) {
        console.log("[WhatsApp Templates] Executing template:", template.name);

        try {
            // Get channel ID
            const channelId = this.props.thread?.id;
            let content = template.content;

            // Try to get personalized content
            if (channelId) {
                try {
                    const result = await this.orm.call(
                        "discuss.channel",
                        "get_template_content_for_channel",
                        [channelId, template.id]
                    );

                    if (!result.error) {
                        content = result.content;
                    }
                } catch (error) {
                    console.warn("[WhatsApp Templates] Failed to get personalized content:", error);
                }
            }

            // Insert content into composer
            // Try different methods to set composer text
            if (this.props.composer) {
                if (this.props.composer.text !== undefined) {
                    this.props.composer.text = content;
                } else if (this.props.composer.message) {
                    this.props.composer.message.body = content;
                }
            }

            // Also try direct textarea manipulation as fallback
            const textarea = document.querySelector('.o-mail-Composer textarea');
            if (textarea) {
                textarea.value = content;
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
            }

            console.log("[WhatsApp Templates] Template inserted successfully");
        } catch (error) {
            console.error("[WhatsApp Templates] Error executing template:", error);
        }
    }
});
