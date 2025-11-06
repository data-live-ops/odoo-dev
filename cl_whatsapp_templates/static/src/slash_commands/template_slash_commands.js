/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const mailSlashCommandRegistry = registry.category("mail_slash_commands");

// Function to load and register all template commands
async function registerTemplateCommands() {
    try {
        // Fetch all templates from backend
        const templates = await rpc("/web/dataset/call_kw", {
            model: "discuss.channel",
            method: "search_templates_by_command",
            args: [""], // Empty string returns all templates
            kwargs: {}
        });

        console.log("[WhatsApp Templates] Registering slash commands:", templates);

        // Register each template as a slash command
        templates.forEach(template => {
            if (!template.shortcut) return;

            const commandName = template.shortcut.replace('/', '');

            mailSlashCommandRegistry.add(commandName, {
                name: template.shortcut,
                description: template.description || template.name,

                // This function is called when command is selected
                execute: async (channel, body) => {
                    console.log(`[WhatsApp Templates] Executing ${commandName} for channel ${channel.id}`);

                    // Send the command to server for processing
                    // The server will handle template insertion and placeholder replacement
                    return {
                        body: template.shortcut, // Send slash command to server
                        template_id: template.id
                    };
                },

                // Show command in all channels/chats
                isAvailable: (channel) => true,
            });
        });

        console.log(`[WhatsApp Templates] Registered ${templates.length} slash commands`);
    } catch (error) {
        console.error("[WhatsApp Templates] Failed to register commands:", error);
    }
}

// Register commands when module loads
registerTemplateCommands();
