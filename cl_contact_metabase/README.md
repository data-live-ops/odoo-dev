# Colearn Contact Metabase Integration

## Overview

This module provides a seamless integration between Metabase analytics platform and Odoo contacts. It allows you to import and synchronize contact data from Metabase questions/cards into your Odoo contacts database, maintaining relationships and additional metadata.

## Key Features
### 1. Metabase Configuration
- Connection settings for Metabase API
- Session token management
- Question ID configuration for different data types
### 2. Contact Integration
- Extended res.partner model with Metabase fields
- Student-specific fields (grade, curriculum, lead stage)
- Subscription tracking
- Parent-child relationship management
### 3. Import Functionality
- Wizard for importing contacts from Metabase
- Options to import students, parents, or both
- Update existing contacts or create new ones
- Automatic linking of parents to students
### 4. User Interface
- Metabase tab in contact form
- "Sync from Metabase" button for individual contacts
- Search filters for Metabase-related fields
- Menu structure under Contacts > Metabase

## Technical Information

- **Odoo Version**: Compatible with Odoo 18
- **Dependencies**: Base, Contacts modules
- **External Dependencies**: Python `requests` library
- **Models**:
  - `metabase.config`: Stores Metabase connection settings
  - Extended `res.partner`: Adds Metabase-related fields to contacts
  - `import.metabase.contacts`: Wizard for importing contacts

## Configuration

1. Go to Contacts > Metabase > Configuration
2. Create a new Metabase configuration with your credentials
3. Configure the question IDs for different data types
4. Test the connection to ensure everything is working properly

## How to Use

### 1. Install the module
- The module will appear in the Apps list as "Colearn Contact Metabase Integration"
### 2. Configure Metabase connection
- Go to Contacts > Metabase > Configuration
- Create a new configuration with your Metabase credentials
- Test the connection
### 3. Import contacts
- Go to Contacts > Metabase > Import Contacts
- Select which types of contacts to import
- Run the import process
### 4. View and manage contacts
- Metabase data will appear in a dedicated tab in contact forms
- Use the search filters to find contacts by Metabase attributes
- Sync individual contacts as needed