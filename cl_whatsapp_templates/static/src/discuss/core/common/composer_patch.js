/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted, onWillUnmount } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        console.log("[WhatsApp Templates] Composer patch loaded!");
        this.orm = useService("orm");
        this.templateState = useState({
            suggestions: [],
            showSuggestions: false,
            selectedIndex: 0,
            searchCommand: "",
        });

        onMounted(() => {
            console.log("[WhatsApp Templates] Composer mounted, setting up template command");
            this._setupTemplateCommand();
        });

        onWillUnmount(() => {
            this._cleanupTemplateCommand();
        });
    },

    _setupTemplateCommand() {
        // Get the textarea element
        const textarea = this.composerRef?.el?.querySelector("textarea");
        if (!textarea) return;

        // Store original handlers
        this._originalKeyDown = textarea.onkeydown;
        this._originalInput = textarea.oninput;

        // Add our handlers
        textarea.addEventListener("keydown", this._onTemplateKeyDown.bind(this));
        textarea.addEventListener("input", this._onTemplateInput.bind(this));
    },

    _cleanupTemplateCommand() {
        const textarea = this.composerRef?.el?.querySelector("textarea");
        if (!textarea) return;

        textarea.removeEventListener("keydown", this._onTemplateKeyDown.bind(this));
        textarea.removeEventListener("input", this._onTemplateInput.bind(this));
    },

    async _onTemplateInput(ev) {
        const textarea = ev.target;
        const cursorPos = textarea.selectionStart;
        const textBeforeCursor = textarea.value.substring(0, cursorPos);

        console.log("[WhatsApp Templates] Input event:", textBeforeCursor);

        // Check if we have a slash command
        const slashMatch = textBeforeCursor.match(/\/(\w*)$/);

        if (slashMatch) {
            const command = slashMatch[1];
            console.log("[WhatsApp Templates] Slash command detected:", command);
            this.templateState.searchCommand = command;
            await this._searchTemplates(command);
        } else {
            this.templateState.showSuggestions = false;
            this.templateState.suggestions = [];
        }
    },

    async _onTemplateKeyDown(ev) {
        if (!this.templateState.showSuggestions) return;

        const { suggestions, selectedIndex } = this.templateState;

        switch (ev.key) {
            case "ArrowDown":
                ev.preventDefault();
                this.templateState.selectedIndex =
                    (selectedIndex + 1) % suggestions.length;
                break;

            case "ArrowUp":
                ev.preventDefault();
                this.templateState.selectedIndex =
                    (selectedIndex - 1 + suggestions.length) % suggestions.length;
                break;

            case "Enter":
            case "Tab":
                if (suggestions.length > 0) {
                    ev.preventDefault();
                    await this._insertTemplate(suggestions[selectedIndex]);
                }
                break;

            case "Escape":
                ev.preventDefault();
                this.templateState.showSuggestions = false;
                break;
        }
    },

    async _searchTemplates(command) {
        try {
            const templates = await this.orm.call(
                "discuss.channel",
                "search_templates_by_command",
                [command]
            );

            this.templateState.suggestions = templates;
            this.templateState.showSuggestions = templates.length > 0;
            this.templateState.selectedIndex = 0;
        } catch (error) {
            console.error("Error searching templates:", error);
            this.templateState.showSuggestions = false;
        }
    },

    async _insertTemplate(template) {
        const textarea = this.composerRef?.el?.querySelector("textarea");
        if (!textarea) return;

        try {
            // Get template content with placeholders replaced
            const channelId = this.props.composer?.thread?.id;
            if (!channelId) {
                // Fallback: use raw content
                this._replaceSlashCommand(textarea, template.content);
                return;
            }

            const result = await this.orm.call(
                "discuss.channel",
                "get_template_content_for_channel",
                [channelId, template.id]
            );

            if (result.error) {
                console.error("Error getting template content:", result.error);
                this._replaceSlashCommand(textarea, template.content);
            } else {
                this._replaceSlashCommand(textarea, result.content);
            }
        } catch (error) {
            console.error("Error inserting template:", error);
            // Fallback: insert raw template
            this._replaceSlashCommand(textarea, template.content);
        }

        // Hide suggestions
        this.templateState.showSuggestions = false;
        this.templateState.suggestions = [];
    },

    _replaceSlashCommand(textarea, content) {
        const cursorPos = textarea.selectionStart;
        const textBeforeCursor = textarea.value.substring(0, cursorPos);
        const textAfterCursor = textarea.value.substring(cursorPos);

        // Find and replace the /command with template content
        const slashMatch = textBeforeCursor.match(/\/\w*$/);
        if (slashMatch) {
            const commandStart = cursorPos - slashMatch[0].length;
            const newValue =
                textarea.value.substring(0, commandStart) +
                content +
                textAfterCursor;

            textarea.value = newValue;

            // Set cursor position after inserted content
            const newCursorPos = commandStart + content.length;
            textarea.setSelectionRange(newCursorPos, newCursorPos);

            // Trigger input event to update the composer state
            textarea.dispatchEvent(new Event("input", { bubbles: true }));
        }
    },
});
