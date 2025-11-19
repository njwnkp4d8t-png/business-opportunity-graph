# Credentials Quick Start

> This guide has been moved under `docs/credentials/` to keep the project root tidy.

## Setup in 3 Steps

### Step 1: Create `.env` File

```bash
# Copy the example
cp docs/credentials/.env.example .env
```

### Step 2: Edit `.env` with Your Credentials

```bash
# Open in your editor
notepad .env    # Windows
nano .env       # Linux/Mac
```

**Fill in these critical values:**

```bash
# PostgreSQL (if you're using it)
POSTGRES_PASSWORD=your_password_here

# Neo4j (if you're using it)
NEO4J_PASSWORD=your_password_here

# OpenAI (if you're using LLM features)
OPENAI_API_KEY=sk-your-key-here

# Application secret (generate random!)
SECRET_KEY=run_command_below_to_generate
```

### Step 3: Generate Secure Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Copy the output and paste into .env
```

## Verify It Works

### Test Configuration

```bash
# Run the config test
python config.py
```

You should see:

```text
Testing Configuration
====================================
Config(
    environment=development
    postgres_password=****word
    neo4j_password=****word
    ...
)
```

### Use in Your Code

```python
from config import get_config

config = get_config()

# Access credentials
print(config.postgres_host)
print(config.neo4j_uri)
# Passwords are loaded but never printed!
```

## Docker Usage

```bash
# Make sure .env exists with your credentials
cp docs/credentials/.env.example .env
# Edit .env

# (Example) Run something that reads config.py
docker run --env-file .env your-image-name
```

## Security Reminders

1. **`.env` is in `.gitignore`** - Already done.
2. **Never commit `.env`** - Git will ignore it.
3. **Use strong passwords in production** - Weak is OK for local dev only.
4. **Keep `.env.example` updated** - Template for the team.

## Common Credentials

### Local Development (Weak passwords OK)

```bash
POSTGRES_PASSWORD=postgres
NEO4J_PASSWORD=password
SECRET_KEY=dev-secret-key-change-in-production
ENVIRONMENT=development
DEBUG=true
```

### Production (Must be strong!)

```bash
POSTGRES_PASSWORD=<generate strong random password>
NEO4J_PASSWORD=<generate strong random password>
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
ENVIRONMENT=production
DEBUG=false
```

## Troubleshooting

**"Config not loading my .env file"**

- Make sure `.env` is in the project root.
- Check file is named exactly `.env` (not `.env.txt`).
- Verify no spaces around `=` in `.env`.

**"Database connection failed"**

- Check credentials in `.env`.
- Verify database is running.
- Check host/port are correct.

**"Permission denied on .env"**

```bash
# Linux/Mac only
chmod 600 .env
```

## Full Documentation

- `SECURITY.md` - Complete security guide (if present).
- `config.py` - Python configuration module.
- `docs/credentials/.env.example` - All available variables.

