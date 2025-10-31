# Commix

A bash script for automating GitHub contributions with realistic commit patterns. Commix creates backdated commits with random messages, naturally skips days, and pushes everything to your GitHub repository.

Built by [uthman](https://github.com/codetesla51)

## Features

- **Realistic Commit Patterns**: Generates commits with varying frequency, mimicking natural development activity
- **Random Commit Messages**: Uses a pool of realistic commit messages with randomized numbers
- **Natural Day Skipping**: 70% chance of committing each day, creating authentic-looking contribution graphs
- **Backdating Support**: Set any start date to fill in your contribution history
- **Customizable Commits**: Configure the number of days and maximum commits per day
- **Automatic Push**: Sets up remote and pushes all commits to GitHub automatically
- **Cross-platform Date Support**: Works on both Linux and macOS

## Prerequisites

- Git installed and configured
- GitHub account
- Bash shell

## Installation

### Quick Install (Global)

```bash
curl -sSL https://raw.githubusercontent.com/codetesla51/Commix/main/install.sh | bash
```

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/codetesla51/Commix.git
cd Commix
```

2. Make the script executable:
```bash
chmod +x commix.sh
```

3. Run the installer:
```bash
./install.sh
```

## Usage

### Basic Usage

```bash
commix
```

The script will guide you through an interactive setup:

1. Choose to use current directory or create a new one
2. Enter your GitHub repository name
3. Enter your GitHub username
4. Specify start date (format: YYYY-MM-DD)
5. Set number of days to generate commits
6. Set maximum commits per day
7. Confirm and let it run

### Important Notes

- Create a NEW, EMPTY repository on GitHub before running
- Do NOT initialize the repository with README, .gitignore, or license
- The repository must be completely empty for the push to work

### Example Workflow

```bash
# Run commix
commix

# Follow prompts:
# - Create new directory: test-repo
# - GitHub repository: test-repo
# - GitHub username: yourusername
# - Start date: 2023-01-01
# - Number of days: 90
# - Max commits per day: 8
```

## Configuration

The script uses the following default values if you press Enter without input:

- **Start date**: 2023-01-01
- **Number of days**: 30
- **Max commits per day**: 10

## How It Works

1. **Repository Setup**: Creates or uses an existing git repository
2. **Commit Generation**: For each day in the specified range:
   - 70% chance of creating commits for that day
   - Random number of commits (1 to max_commits)
   - Each commit gets a random message from the predefined pool
   - Commits are backdated to the specific day
3. **Remote Configuration**: Automatically sets up the GitHub remote
4. **Push**: Pushes all commits to the main branch

## Commit Messages

Commix uses realistic commit messages including:

- Update documentation and add examples
- Fix edge case in main logic
- Optimize performance for large datasets
- Implement error handling
- Add unit tests for core functions
- Refactor code for better maintainability
- Update dependencies to latest versions
- And more...

Each message is appended with a random number for uniqueness.

## Troubleshooting

### Push Failed

If the push fails, ensure:
- The repository exists on GitHub
- The repository is completely empty (no initial commit, README, or .gitignore)
- Your Git credentials are configured correctly
- You have write access to the repository

### Git Configuration Not Found

If you see a git configuration error, set your git user:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Invalid Date Format

Make sure to use the YYYY-MM-DD format for dates (e.g., 2023-01-01)

## Contributing

Contributions are welcome! Feel free to:

- Report bugs
- Suggest features
- Submit pull requests

## Author

Built by [uthman](https://github.com/codetesla51)

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.

---

**Use responsibly.**
