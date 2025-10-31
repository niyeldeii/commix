#!/bin/bash

set -e

SCRIPT_NAME="commit.sh"
INSTALL_NAME="commix"

echo "Installing Commix..."

# Detect OS and set install directory
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    INSTALL_DIR="$HOME/.local/bin"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    INSTALL_DIR="$HOME/.local/bin"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows Git Bash or Cygwin
    INSTALL_DIR="$HOME/bin"
else
    # Default fallback
    INSTALL_DIR="$HOME/.local/bin"
fi

# Create install directory if it doesn't exist
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Creating $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
fi

# Check if script exists in current directory
if [ ! -f "$SCRIPT_NAME" ]; then
    echo "Error: $SCRIPT_NAME not found in current directory"
    echo "Please run this installer from the Commix directory"
    exit 1
fi

# Copy script to install directory
echo "Copying $SCRIPT_NAME to $INSTALL_DIR/$INSTALL_NAME..."
cp "$SCRIPT_NAME" "$INSTALL_DIR/$INSTALL_NAME"

# Make it executable (works on Unix-like systems)
chmod +x "$INSTALL_DIR/$INSTALL_NAME"

# Check if install directory is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "Warning: $INSTALL_DIR is not in your PATH"
    
    # Detect shell and provide appropriate instructions
    if [ -n "$BASH_VERSION" ]; then
        SHELL_RC="~/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="~/.zshrc"
    else
        SHELL_RC="~/.profile"
    fi
    
    echo "Add this line to your $SHELL_RC:"
    echo ""
    echo "export PATH=\"$INSTALL_DIR:\$PATH\""
    echo ""
    echo "Then run: source $SHELL_RC"
else
    echo ""
    echo "Installation complete!"
    echo "You can now run 'commix' from anywhere"
fi

echo ""
echo "Done!"
