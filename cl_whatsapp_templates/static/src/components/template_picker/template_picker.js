/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Template Picker Component
 *
 * Simple component to select and insert WhatsApp templates
 * into the message composer.
 */
export class TemplatePicker extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            templates: [],
            selectedCategory: null,
            searchTerm: "",
        });

        this.loadTemplates();
    }

    async loadTemplates() {
        const domain = [["active", "=", true]];
        if (this.state.selectedCategory) {
            domain.push(["category", "=", this.state.selectedCategory]);
        }

        const templates = await this.orm.searchRead(
            "whatsapp.template",
            domain,
            ["id", "name", "content", "category", "description", "shortcut"],
            { order: "sequence, name" }
        );

        this.state.templates = templates;
    }

    async onTemplateSelect(templateId) {
        // Trigger callback to insert template
        if (this.props.onSelect) {
            const template = this.state.templates.find(t => t.id === templateId);
            this.props.onSelect(template);
        }
    }

    onCategoryChange(category) {
        this.state.selectedCategory = category === "all" ? null : category;
        this.loadTemplates();
    }

    getFilteredTemplates() {
        if (!this.state.searchTerm) {
            return this.state.templates;
        }

        const term = this.state.searchTerm.toLowerCase();
        return this.state.templates.filter(
            t => t.name.toLowerCase().includes(term) ||
                 t.content.toLowerCase().includes(term) ||
                 (t.shortcut && t.shortcut.toLowerCase().includes(term))
        );
    }
}

TemplatePicker.template = "cl_whatsapp_templates.TemplatePicker";
TemplatePicker.props = {
    onSelect: { type: Function, optional: true },
};

registry.category("components").add("TemplatePicker", TemplatePicker);
