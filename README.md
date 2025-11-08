# 📞 DialAI - Automated Phone Call System

A modern web application built with **FastAPI** and **Twilio** that automates phone calls with AI-powered natural language commands.

## ✨ Features

- 📋 **Batch Phone Number Input**: Paste numbers or upload `.txt`/`.csv` files
- 🧠 **Smart Number Parsing**: Automatically matches numbers to verified numbers in your Twilio account
- ✅ **Verification Status Checker**: Check if phone numbers are verified before calling
- 🤖 **AI Command Interface**: Use natural language like "Call 9876543210" or "Start calling all numbers"
- 📊 **Call Logging**: Track all calls with status, timestamps, and error messages
- 🧹 **Log Cleanup**: Clean up error messages in call logs with one click
- 🎨 **Modern UI**: Beautiful, responsive web interface
- 🔊 **Customizable Messages**: Customize what receivers hear via environment variables
- 🔒 **Secure Configuration**: Environment-based credentials management

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Twilio account (get one at [twilio.com/try-twilio](https://www.twilio.com/try-twilio))
- Gemini API key OR OpenAI API key (for AI commands)

### Installation

1. **Clone or download this project**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your credentials:
   ```env
   # Required: Twilio Configuration
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_phone_number
   
   # Required: AI Configuration (choose one)
   GEMINI_API_KEY=your_gemini_api_key
   # OR use OpenAI instead:
   # OPENAI_API_KEY=your_openai_api_key
   
   # Optional: Customize Call Message
   CALL_MESSAGE=Hello, this is a test call from the DialAI app.
   CALL_VOICE=alice
   CALL_LANGUAGE=en
   ```

4. **Run the application:**
   ```bash
   uvicorn main:app --reload
   ```

5. **Open in browser:**
   ```
   http://127.0.0.1:8000
   ```

## 📖 Usage

### Making Calls

1. **Enter Phone Numbers:**
   - Paste numbers in the text area (comma or newline separated)
   - **With country code** (recommended): `+919895431875, +18001234567`
   - **Without country code**: The app will try to match verified numbers automatically
   - Or upload a `.txt` or `.csv` file with numbers

2. **Check Verification (Optional):**
   - Click "✓ Check Verification Status" to verify if numbers are ready to call
   - Shows which numbers are verified and which need verification

3. **Start Calling:**
   - Click "🚀 Start Calling" to initiate batch calls
   - Each call will play your custom message (default: "Hello, this is a test call from the DialAI app.")

### AI Commands

Use natural language commands in the AI Command section:

- **Single Call:** `"Call 9876543210"`
- **Batch Call:** `"Start calling all numbers"`
- **Alternative:** `"Make a call to 1800123456"`

The AI will parse your command and execute the appropriate action.

### Viewing Logs

- Click "📜 View Call Logs" to see all call history
- Logs include: phone number, status, timestamp, call SID, and errors
- Logs are automatically saved to `calls.json`
- Click "🧹 Cleanup Errors" to clean up verbose error messages
- Auto-refreshes every 30 seconds

## 📁 Project Structure

```
dialai/
├── main.py              # FastAPI application
├── templates/
│   ├── index.html       # Home page
│   └── logs.html        # Call logs page
├── static/
│   └── style.css        # Styling
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create from .env.example)
├── calls.json           # Call logs storage
└── README.md           # This file
```

## 🔧 API Endpoints

### Web Pages
- `GET /` - Home page with phone input and AI commands
- `GET /logs` - Call logs page with detailed history

### API Endpoints
- `POST /call` - Initiate calls (form data: `numbers`, `file`)
- `POST /ai-command` - Handle AI commands (form data: `command`, `numbers`)
- `GET /api/logs` - JSON API for call logs
- `GET /api/check-verification/{phone_number}` - Check if a number is verified
- `POST /api/cleanup-logs` - Clean up error messages in logs

## 🔐 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID | Yes |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token | Yes |
| `TWILIO_PHONE_NUMBER` | Your Twilio phone number | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes* |
| `OPENAI_API_KEY` | OpenAI API key | Yes* |
| `CALL_MESSAGE` | Message to play to receiver (default: "Hello, this is a test call from the DialAI app.") | No |
| `CALL_VOICE` | Voice to use (default: "alice"). Options: `alice`, `man`, `woman`, or any `polly.*` voice (e.g., `polly.Joanna`) | No |
| `CALL_LANGUAGE` | Language code (default: "en"). Examples: `en` (English), `es` (Spanish), `hi` (Hindi), `fr` (French) | No |

*Either Gemini or OpenAI API key is required for AI commands.

## ⚠️ Important Notes

### Twilio Setup Requirements

1. **Twilio Phone Number (FROM number - Source)**:
   - ✅ **Required**: You MUST use a phone number **purchased from Twilio** in your `TWILIO_PHONE_NUMBER` environment variable
   - 📞 Get a number: Go to [Twilio Console → Phone Numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/search)
   - 💡 Trial accounts get a free number, or you can purchase one
   - ✅ **Important**: Twilio-purchased numbers are **automatically verified** - no SMS verification needed! They're already linked to your account.

2. **Verified Numbers (TO numbers - Destination - Trial Accounts Only)**:
   - ⚠️ **Trial Accounts**: You can only call numbers you've verified in Twilio
   - ✅ Verify destination numbers: Go to [Twilio Console → Verified Caller IDs](https://console.twilio.com/us1/develop/phone-numbers/manage/verified)
   - 📝 **Note**: This is for numbers you want to **call TO**, not your Twilio number (which is already verified)
   - 🔓 **Upgraded Accounts**: Can call any number without verification

3. **Phone Number Format**: 
   - **Recommended**: Include country code (e.g., `+18001234567` for US, `+919895431875` for India)
   - Format: `+[country code][number]`
   - **Smart Parsing**: If you enter numbers without country code, the app will:
     - Check your verified numbers in Twilio
     - Match by last 10 digits
     - Use the correct country code from verified numbers
     - Default to `+1` for US/Canada if no match found

4. **Rate Limits & Costs**: 
   - Be aware of Twilio rate limits and costs
   - Check your [Twilio Console](https://console.twilio.com/) for usage and billing

5. **Legal Compliance**: 
   - Only call numbers you have permission to call
   - Comply with local telemarketing and spam laws
   - This tool is for testing and educational purposes only

## 🐛 Troubleshooting

### "Twilio credentials not configured"
- Check that your `.env` file exists and contains valid Twilio credentials
- Ensure variable names match exactly (case-sensitive)

### "The source phone number provided is not yet verified"
- ❌ **Problem**: Your `TWILIO_PHONE_NUMBER` is not a Twilio number
- ✅ **Solution**: 
  1. Go to [Twilio Console → Phone Numbers](https://console.twilio.com/us1/develop/phone-numbers/manage/search)
  2. Get a phone number from Twilio (trial accounts get one free)
  3. Update your `.env` file with the Twilio number in `TWILIO_PHONE_NUMBER`
  4. Format: `+1234567890` (include country code with `+`)

### "Unable to create record: [number] is not yet verified"
- ❌ **Problem**: You're trying to call a number that isn't verified (trial accounts only)
- ✅ **Solution**: 
  1. Go to [Twilio Console → Verified Caller IDs](https://console.twilio.com/us1/develop/phone-numbers/manage/verified)
  2. Click "Add a new Caller ID"
  3. Enter the phone number you want to call
  4. Verify it via phone call or SMS
  5. Once verified, you can call that number

### "No valid phone numbers provided"
- Ensure numbers are at least 10 digits
- Check that numbers are properly formatted (comma or newline separated)
- Include country code: `+[country][number]` (e.g., `+18001234567`)

### AI commands not working
- Verify your Gemini or OpenAI API key is set correctly
- Check that you have API credits/quota available
- The app will fall back to simple regex parsing if AI is unavailable

### Calls failing (general)
- Verify your Twilio phone number is correct and from Twilio
- Check that destination numbers include country code
- For trial accounts, ensure destination numbers are verified in Twilio Console
- Use the "Check Verification Status" button to verify numbers before calling
- Check your Twilio account balance and limits

### Wrong country code being used
- **Problem**: App adds `+1` (US) but your number is from another country (e.g., India `+91`)
- **Solution**: 
  1. Enter numbers with country code: `+919895431875` instead of `9895431875`
  2. Or verify the number in Twilio first - the app will auto-match verified numbers
  3. The app checks your verified numbers and uses the correct country code automatically

## 💡 Tips & Best Practices

### Phone Number Entry
- **Best**: Always include country code: `+919895431875`
- **Good**: Enter without country code - app will match verified numbers
- **Avoid**: Mixing formats in the same batch

### Customizing Call Messages
```env
# Business call example
CALL_MESSAGE=Thank you for your interest. This is an automated call from our company.
CALL_VOICE=polly.Joanna

# Multi-language example (Hindi)
CALL_MESSAGE=नमस्ते, यह DialAI ऐप से एक परीक्षण कॉल है।
CALL_LANGUAGE=hi
CALL_VOICE=alice
```

### Verification Workflow
1. Add numbers to Verified Caller IDs in Twilio Console
2. Use "Check Verification Status" button to confirm
3. Enter numbers (with or without country code)
4. Start calling!

## 📝 License

This project is for educational and testing purposes only. Use responsibly and in compliance with applicable laws and regulations.

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Voice calls powered by [Twilio](https://www.twilio.com/)
- AI commands powered by [Google Gemini](https://ai.google.dev/) or [OpenAI](https://openai.com/)

---

**Built with ❤️ using FastAPI, Twilio, and AI APIs**

#
