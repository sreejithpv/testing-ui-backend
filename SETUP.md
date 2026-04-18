# Setup Instructions

## Environment Variables & Secrets

This project uses environment variables to keep sensitive credentials secure.

### Step 1: Create `.env` file

1. Copy the template file:
   ```bash
   cd backend
   cp .env.example .env
   ```

2. Open `.env` and fill in your API credentials:
   ```env
   ALPACA_API_KEY=your_actual_api_key
   ALPACA_SECRET_KEY=your_actual_secret_key
   POLYGON_API_KEY=your_polygon_key (optional)
   ```

### Step 2: Get your API keys

#### For Alpaca Markets (Free)
1. Go to https://alpaca.markets
2. Sign up for a free account
3. Navigate to Paper Trading → API Keys → Generate
4. Copy your **API Key** and **Secret Key** to `.env`

#### For Polygon.io (Optional)
1. Go to https://polygon.io (now Massive.com)
2. Sign up for a free account
3. Navigate to Dashboard → API Keys
4. Copy your key to `.env`

### Step 3: Install dependencies

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Security Best Practices

- ✅ `.env` is in `.gitignore` — it will NOT be committed
- ✅ Sensitive keys are loaded from environment variables, not hardcoded
- ✅ `.env.example` is safe to commit (it only has placeholders)
- ✅ Each developer has their own `.env` file with their own credentials

### For Production

If deploying to production, set environment variables in your hosting platform:
- **Heroku**: Use `.env` files in Config Vars
- **AWS Lambda/EC2**: Use AWS Secrets Manager or environment variables
- **Docker**: Pass environment variables at runtime
- **GitHub Actions**: Use GitHub Secrets

Never commit your `.env` file! Always use environment variables or secrets management.
