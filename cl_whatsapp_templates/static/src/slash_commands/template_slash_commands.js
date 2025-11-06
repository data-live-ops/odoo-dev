/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

console.log("[WhatsApp Templates] Module loading...");

// Try to get mail_slash_commands registry
try {
    const mailSlashCommandRegistry = registry.category("mail_slash_commands");
    console.log("[WhatsApp Templates] Mail slash command registry found:", mailSlashCommandRegistry);

    // Load templates and register commands immediately
    (async () => {
        try {
            console.log("[WhatsApp Templates] Fetching templates...");

            // Fetch templates from backend
            const templates = await rpc("/web/dataset/call_kw/discuss.channel/search_templates_by_command", {
                model: "discuss.channel",
                method: "search_templates_by_command",
                args: [""],
                kwargs: {},
            });

            console.log(`[WhatsApp Templates] Fetched ${templates.length} templates:`, templates);

            // Register each template as slash command
            templates.forEach((template) => {
                if (!template.shortcut) {
                    console.warn(`[WhatsApp Templates] Template ${template.name} has no shortcut, skipping`);
                    return;
                }

                const commandName = template.shortcut.replace("/", "");
                console.log(`[WhatsApp Templates] Registering command: ${commandName}`);

                mailSlashCommandRegistry.add(commandName, {
                    name: template.shortcut,
                    description: template.description || template.name,
                    isAvailable: () => true, // Show in all contexts
                });

                console.log(`[WhatsApp Templates] ✓ Registered: ${template.shortcut}`);
            });

            console.log(`[WhatsApp Templates] Successfully registered ${templates.length} commands`);
        } catch (error) {
            console.error("[WhatsApp Templates] Error loading templates:", error);
        }
    })();

} catch (error) {
    console.error("[WhatsApp Templates] mail_slash_commands registry not found:", error);
    console.log("[WhatsApp Templates] Available registries:", Array.from(registry.categories.keys()));
}

console.log("[WhatsApp Templates] Module loaded");
