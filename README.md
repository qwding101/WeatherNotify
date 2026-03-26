# WeatherNotify

## Overview
Automatically fetches weather forecast data from the Central Weather Administration (CWA) of Taiwan every day and sends an email notification with the results.

### Schedule
| Trigger | Time | Days | Forecast Target |
|---------|------|------|-----------------|
| Night | 23:00 (Taiwan Time) | Sun–Thu | **Next day** 08:00–19:00 |
| Morning | 07:00 (Taiwan Time) | Mon–Fri | **Same day** 08:00–19:00 |

### Notification Content
Each email includes temperature and precipitation probability statistics for the target time window (08:00–19:00):
- Maximum value and time of occurrence
- Minimum value and time of occurrence
- Average value

## Setup Instructions

### Step 1: Register for a CWA API key
1. Create an account in [https://opendata.cwa.gov.tw](https://opendata.cwa.gov.tw).
2. After logging in, go to "Member Center" → "Get Authorization Code"
3. Copy your API Key (format: `CWA-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

### Step 2: Generate a Gmail App password
1. Go to Gmail → Account Settings → Security
2. Enable **2-Step Verification** if not already enabled
3. Search for **"App Passwords"** and generate a new 16-character password
4. Copy the password immediately (it will only be shown once) and remove all spaces. The final format should be 16 consecutive characters: `xxxxxxxxxxxxxxxx`

### Step 3: Create a GitHub repository and upload files
1. Log in to GitHub and create a new repository (Public or Private)
2. Upload the following two files:
   - `weather_fetch.py`
   - `.github/workflows/weather_notify.yml`

### Step 4: Configure GitHub secrets
Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**, and add the following four secrets:

| Secret Name | Value |
|-------------|-------|
| `CWA_API_KEY` | Your CWA API Key |
| `EMAIL_SENDER` | Your Gmail address |
| `EMAIL_APP_PASSWORD` | 16-character App Password (no spaces) |
| `EMAIL_RECEIVER` | The Gmail address to receive notifications |

### Step 5: Manual test
Go to **Actions** → **Weather Notify** → **Run workflow** → Enter `morning` or `night` → Click **Run workflow**


## Temporarily disabling the schedule
If you need to pause the automation:
1. Go to **Actions** → **Weather Notify**
2. Click the **"⋯"** button on the right
3. Select **"Disable workflow"**

To re-enable, click **"Enable workflow"** from the same location.


## Email notification example
(TBA)


## Data source
[Central Weather Administration Open Data Platform](https://opendata.cwa.gov.tw)
Dataset ID: `F-D0047-061` — Township-level 3-day weather forecast for Taipei City


## Acknowledgements
This project was collaboratively developed by the repository owner and Claude AI.
