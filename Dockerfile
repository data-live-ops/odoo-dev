# Use official Odoo 18.0 image as base
FROM odoo:18.0

# Switch to root to install additional packages
USER root

# Install additional Python dependencies
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    phonenumbers \
    geoip2

# Create directories for custom addons
RUN mkdir -p /mnt/custom-addons /mnt/enterprise-addons

# Fix permissions
RUN chown -R odoo:odoo /mnt/custom-addons /mnt/enterprise-addons

# Switch back to odoo user
USER odoo

# Set working directory
WORKDIR /

# Expose Odoo port
EXPOSE 8069 8072
