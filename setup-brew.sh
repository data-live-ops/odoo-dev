#!/bin/bash
# Setup Homebrew PATH

echo "Setting up Homebrew PATH..."

# Add Homebrew to PATH
echo >> ~/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

echo "✅ Homebrew PATH configured!"
echo "📝 To apply in current terminal, run:"
echo "   source ~/.zprofile"
echo ""
echo "Or just close and reopen your terminal."
