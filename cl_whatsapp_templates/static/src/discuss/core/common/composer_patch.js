import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState, onMounted, onPatched, onWillUnmount } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        console.log("[WhatsApp Templates] Composer patch loaded! ✅");
        this.orm = useService("orm");
        this.templateState = useState({
            suggestions: [],
            showSuggestions: false,
            selectedIndex: 0,
            searchCommand: "",
        });
        this._boundKeyDown = this._onTemplateKeyDown.bind(this);
        this._boundInput = this._onTemplateInput.bind(this);

        onMounted(() => {
            console.log("[WhatsApp Templates] Composer mounted, setting up template command ✅");
            // Delay for OWL ref timing
            setTimeout(() => this._setupTemplateCommand(), 0);
        });

        // Fallback: Re-check on patches (e.g., if re-rendered)
        onPatched(() => {
            if (!this._listenersAttached) {
                setTimeout(() => this._setupTemplateCommand(), 0);
            }
        });

        onWillUnmount(() => {
            this._cleanupTemplateCommand();
        });
    },

    _setupTemplateCommand() {
        if (this._listenersAttached) return;  // Prevent duplicates

        const textarea = this.inputRef?.el;
        if (textarea) {
            console.log("[WhatsApp Templates] Textarea found via ref! Attaching direct listeners. ✅", textarea);
            textarea.addEventListener("input", this._boundInput, true);
            textarea.addEventListener("keydown", this._boundKeyDown, true);
            this._boundInput({ target: textarea });  // Initial scan
            this._listenersAttached = true;
            return;
        }

        // Fallback
        console.warn("[WhatsApp Templates] Ref not ready, using document fallback.");
        document.addEventListener("input", this._boundInput, true);
        document.addEventListener("keydown", this._boundKeyDown, true);
        this._boundInput({ target: document.activeElement });  // Initial scan
        this._listenersAttached = true;
    },

    _cleanupTemplateCommand() {
        console.log("[WhatsApp Templates] Cleaning up event listeners");
        const textarea = this.inputRef?.el;
        if (textarea && this._listenersAttached) {
            textarea.removeEventListener("input", this._boundInput, true);
            textarea.removeEventListener("keydown", this._boundKeyDown, true);
        } else {
            document.removeEventListener("input", this._boundInput, true);
            document.removeEventListener("keydown", this._boundKeyDown, true);
        }
        this._listenersAttached = false;
        this.templateState.showSuggestions = false;
        this.templateState.suggestions = [];
    },

    async _onTemplateInput(ev) {
        // Only process if this is a textarea in *this* composer (scoped check)
        if (ev.target.tagName !== 'TEXTAREA') return;
        if (!ev.target.closest('.o-mail-Composer')) return;
        const textarea = ev.target;
        const cursorPos = textarea.selectionStart;
        const textBeforeCursor = textarea.value.substring(0, cursorPos);

        // Check if we have a slash command
        const slashMatch = textBeforeCursor.match(/\/(\w*)$/);
        if (slashMatch) {
            const command = slashMatch[1];
            console.log(`[WhatsApp Templates] Slash detected! Command: "${command}" (length: ${command.length})`);
            this.templateState.searchCommand = command;
            await this._searchTemplates(command);
        } else {
            // Hide suggestions if no slash command
            if (this.templateState.showSuggestions) {
                console.log("[WhatsApp Templates] No slash command, hiding suggestions");
            }
            this.templateState.showSuggestions = false;
            this.templateState.suggestions = [];
        }
    },

    async _onTemplateKeyDown(ev) {
        // Only process if this is a textarea in *this* composer (scoped check)
        if (ev.target.tagName !== 'TEXTAREA') return;
        if (!ev.target.closest('.o-mail-Composer')) return;
        if (!this.templateState.showSuggestions) return;
        const { suggestions, selectedIndex } = this.templateState;
        if (suggestions.length === 0) return; // Safety: skip if no suggestions

        switch (ev.key) {
            case "ArrowDown":
                ev.preventDefault();
                this.templateState.selectedIndex = (selectedIndex + 1) % suggestions.length;
                this._updateSelectedItem();
                break;
            case "ArrowUp":
                ev.preventDefault();
                this.templateState.selectedIndex = (selectedIndex - 1 + suggestions.length) % suggestions.length;
                this._updateSelectedItem();
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
                this._hideDropdown();
                break;
        }
    },

    async _searchTemplates(command) {
        try {
            // Call method on discuss.channel model (where the method is defined)
            const templates = await this.orm.call(
                "discuss.channel",
                "search_templates_by_command",
                [command]
            );
            this.templateState.suggestions = templates;
            this.templateState.showSuggestions = templates.length > 0;
            this.templateState.selectedIndex = 0;
            console.log(`[WhatsApp Templates] Found ${templates.length} templates for '${command}'`);
            console.log(`[WhatsApp Templates] showSuggestions = ${this.templateState.showSuggestions}`);
            console.log(`[WhatsApp Templates] Templates:`, templates);

            // Manually render dropdown (workaround for template inheritance issue)
            if (templates.length > 0) {
                this._renderDropdown(templates);
            } else {
                this._hideDropdown();
            }
        } catch (error) {
            console.error("Error searching templates:", error);
            this.templateState.showSuggestions = false;
            this.templateState.suggestions = [];
            this._hideDropdown();
        }
    },

    _renderDropdown(templates) {
        console.log("[WhatsApp Templates] _renderDropdown called with", templates.length, "templates");

        // Remove existing dropdown if any
        this._hideDropdown();

        // Find composer container
        console.log("[WhatsApp Templates] Looking for composer...");
        const composer = document.querySelector('.o-mail-Composer textarea')?.closest('.o-mail-Composer');
        console.log("[WhatsApp Templates] Composer found:", composer);

        if (!composer) {
            console.warn("[WhatsApp Templates] Composer not found for dropdown");
            return;
        }

        // Create dropdown element
        console.log("[WhatsApp Templates] Creating dropdown element...");
        const dropdown = document.createElement('div');
        dropdown.className = 'o_template_suggestions';
        dropdown.id = 'whatsapp_template_dropdown';
        dropdown.style.border = '2px solid red'; // Debug: make it visible

        // Create suggestions list
        const list = document.createElement('div');
        list.className = 'o_template_suggestions_list';

        templates.forEach((template, index) => {
            const item = document.createElement('div');
            item.className = 'o_template_suggestion_item';
            if (index === this.templateState.selectedIndex) {
                item.classList.add('o_template_suggestion_selected');
            }

            item.innerHTML = `
                <div class="o_template_suggestion_header">
                    <span class="o_template_suggestion_name">${template.name}</span>
                    ${template.shortcut ? `<span class="o_template_suggestion_shortcut">${template.shortcut}</span>` : ''}
                </div>
                ${template.description ? `<div class="o_template_suggestion_description">${template.description}</div>` : ''}
                <div class="o_template_suggestion_preview">${template.content}</div>
            `;

            // Add click handler
            item.addEventListener('click', () => this._insertTemplate(template));
            item.addEventListener('mouseenter', () => {
                this.templateState.selectedIndex = index;
                this._updateSelectedItem();
            });

            list.appendChild(item);
        });

        dropdown.appendChild(list);

        // Create footer
        const footer = document.createElement('div');
        footer.className = 'o_template_suggestions_footer';
        footer.innerHTML = `
            <small class="text-muted">
                <i class="fa fa-arrow-up"></i> <i class="fa fa-arrow-down"></i> to navigate,
                <i class="fa fa-level-down"></i> to select,
                <i class="fa fa-times"></i> to cancel
            </small>
        `;
        dropdown.appendChild(footer);

        // Append to composer
        console.log("[WhatsApp Templates] Appending dropdown to composer...");
        composer.appendChild(dropdown);
        console.log("[WhatsApp Templates] Dropdown rendered with", templates.length, "items");
        console.log("[WhatsApp Templates] Dropdown element:", dropdown);
        console.log("[WhatsApp Templates] Dropdown parent:", dropdown.parentElement);
    },

    _hideDropdown() {
        const existing = document.getElementById('whatsapp_template_dropdown');
        if (existing) {
            existing.remove();
            console.log("[WhatsApp Templates] Dropdown hidden");
        }
    },

    _updateSelectedItem() {
        const items = document.querySelectorAll('.o_template_suggestion_item');
        items.forEach((item, index) => {
            if (index === this.templateState.selectedIndex) {
                item.classList.add('o_template_suggestion_selected');
            } else {
                item.classList.remove('o_template_suggestion_selected');
            }
        });
    },

    async _insertTemplate(template) {
        // Get currently focused textarea (should be this one)
        const textarea = document.activeElement;
        if (!textarea || textarea.tagName !== 'TEXTAREA' || !textarea.closest('.o-mail-Composer')) {
            console.warn("[WhatsApp Templates] No valid textarea focused");
            return;
        }

        console.log("[WhatsApp Templates] Inserting template:", template.name);
        try {
            // Get template content with placeholders replaced
            const channelId = this.props.thread?.id;  // Fixed: Direct prop access
            if (!channelId) {
                console.log("[WhatsApp Templates] No channelId, using raw content");
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
                console.log("[WhatsApp Templates] Template content received:", result.content);
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
        this.templateState.selectedIndex = 0;
        this._hideDropdown();
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
            console.log("[WhatsApp Templates] Template inserted, cursor at:", newCursorPos);
        }
    },
});