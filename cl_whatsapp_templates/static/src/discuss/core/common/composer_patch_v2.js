/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        console.log("[WhatsApp Templates] Composer patch v2 loaded!");
        this.orm = useService("orm");
        this._templateCommands = [];

        onMounted(async () => {
            await this._loadTemplateCommands();
        });
    },

    async _loadTemplateCommands() {
        try {
            // Fetch all templates with shortcuts
            const templates = await this.orm.call(
                "discuss.channel",
                "search_templates_by_command",
                [""] // Empty string returns all templates
            );

            console.log("[WhatsApp Templates] Loaded templates:", templates);

            // Store templates for command execution
            this._templateCommands = templates.filter(t => t.shortcut);

            // Extend native commands if suggestionService exists
            if (this.suggestionService) {
                this._registerTemplateCommands();
            } else {
                console.warn("[WhatsApp Templates] suggestionService not found, will try manual approach");
            }
        } catch (error) {
            console.error("[WhatsApp Templates] Error loading templates:", error);
        }
    },

    _registerTemplateCommands() {
        // Register each template as a command
        this._templateCommands.forEach(template => {
            const commandName = template.shortcut.replace('/', '');

            this.suggestionService.register({
                name: commandName,
                description: template.description || template.name,
                execute: async () => {
                    await this._executeTemplateCommand(template);
                }
            });
        });

        console.log(`[WhatsApp Templates] Registered ${this._templateCommands.length} commands`);
    },

    async _executeTemplateCommand(template) {
        console.log("[WhatsApp Templates] Executing template command:", template.name);

        try {
            // Get channel ID
            const channelId = this.props.thread?.id;

            let content;
            if (channelId) {
                // Get template with placeholders replaced
                const result = await this.orm.call(
                    "discuss.channel",
                    "get_template_content_for_channel",
                    [channelId, template.id]
                );

                content = result.error ? template.content : result.content;
            } else {
                content = template.content;
            }

            // Insert into composer
            if (this.props.composer?.text !== undefined) {
                this.props.composer.text = content;
            }

            console.log("[WhatsApp Templates] Template inserted:", content);
        } catch (error) {
            console.error("[WhatsApp Templates] Error executing template command:", error);
        }
    }
});
